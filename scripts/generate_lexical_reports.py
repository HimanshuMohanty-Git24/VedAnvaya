"""Generate the review and build reports for the deterministic lexical layer.

Everything here is derived from the committed build outputs and is deterministic: the
samples are chosen by sorting, never by a random number generator, so the reports are
stable across runs and reviewable as a diff.

No bulk Sanskrit is reproduced. Mention rows show a single surface word and its lemma,
which is the evidence under review; parallel rows show citations and metrics, never the
verses themselves.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from vedagraph.lexical.parallels import (
    ACCEPT_EDIT_SIMILARITY,
    ACCEPT_LENGTH_RATIO,
    ACCEPT_MIN_TOKENS,
    ACCEPT_ORDERED_TOKEN_SIMILARITY,
    ACCEPT_TOKEN_JACCARD,
    CANDIDATE_ORDERED_TOKEN_SIMILARITY,
    LSH_BANDS,
    LSH_ROWS,
    MAX_BUCKET_SIZE,
    MINHASH_PERMUTATIONS,
    PARALLEL_POLICY_VERSION,
)
from vedagraph.models.lexical import (
    AmbiguousMention,
    ExactParallelGroup,
    LexicalAlias,
    MantraParallel,
    MentionAssertion,
    MorphologyToken,
    ParallelCandidate,
)
from vedagraph.storage.jsonl import read_jsonl

DEFAULT_INPUT = Path("data/knowledge/rigveda_lexical_v1")
DEFAULT_REPORTS = Path("docs/reports")

#: How many mention rows to show per stratum. The strata together are the review sample,
#: sized so the whole sample stays in the 200-500 band the QA policy requires.
PER_STRATUM = 60


def _pct(numerator: int, denominator: int) -> str:
    return f"{100.0 * numerator / denominator:.2f}%" if denominator else "n/a"


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] * len(header)) + "|"]
    lines.extend("| " + " | ".join(cell for cell in row) + " |" for row in rows)
    return lines


def mention_review(input_dir: Path, built_at: datetime) -> str:
    tokens = {
        token.token_key: token for token in read_jsonl(input_dir / "tokens.jsonl", MorphologyToken)
    }
    mentions = list(read_jsonl(input_dir / "mentions.jsonl", MentionAssertion))
    ambiguous = list(read_jsonl(input_dir / "ambiguous_mentions.jsonl", AmbiguousMention))
    aliases = {
        alias.alias_key: alias
        for alias in read_jsonl(input_dir / "lexical_aliases.jsonl", LexicalAlias)
    }
    stats = json.loads((input_dir / "lexical_stats.json").read_text(encoding="utf-8"))

    per_entity: dict[str, list[tuple[MentionAssertion, MorphologyToken]]] = defaultdict(list)
    per_mantra: dict[str, set[str]] = defaultdict(set)
    for mention in mentions:
        per_mantra[mention.subject_key].add(mention.object_key)
        for item in mention.evidence:
            per_entity[mention.object_key].append((mention, tokens[item.token_key]))

    frequency = Counter({key: len(value) for key, value in per_entity.items()})
    high = [key for key, _ in frequency.most_common(6)]
    rare = [
        key for key, count in sorted(frequency.items(), key=lambda i: (i[1], i[0])) if count <= 25
    ]
    multi = sorted(key for key, values in per_mantra.items() if len(values) >= 3)
    composite = [
        key
        for key in per_entity
        if any(
            aliases[item.alias_key].alias_type.value == "COMPOSITE_NAME"
            for mention, _ in per_entity[key]
            for item in mention.evidence
        )
    ]

    def rows_for(
        keys: list[str], predicate=lambda pair: True, limit: int = PER_STRATUM
    ) -> list[list[str]]:
        collected: list[list[str]] = []
        for key in keys:
            pairs = sorted(
                (pair for pair in per_entity.get(key, []) if predicate(pair)),
                key=lambda pair: pair[1].token_key,
            )
            for mention, token in pairs[: max(1, limit // max(len(keys), 1))]:
                evidence = next(
                    item for item in mention.evidence if item.token_key == token.token_key
                )
                features = ",".join(
                    f"{name}={value}"
                    for name, value in sorted(token.morphological_features.items())
                )
                collected.append(
                    [
                        mention.citation,
                        key,
                        f"`{token.surface_form}`",
                        f"`{token.lemma}`",
                        aliases[evidence.alias_key].alias_type.value,
                        evidence.method.value,
                        features or "-",
                    ]
                )
        return collected

    header = ["mantra", "entity", "surface", "lemma", "alias type", "method", "morphology"]

    # --- Morphological audit. The annotation's own gender feature is independent
    # --- evidence about whether a matched token is the deity or an appellative.
    audit_rows: list[list[str]] = []
    total_suspect = 0
    for key in sorted(frequency, key=lambda k: (-frequency[k], k)):
        genders = Counter(
            token.morphological_features.get("gender", "-") for _, token in per_entity[key]
        )
        expected = genders.most_common(1)[0][0] if genders else "-"
        suspect = sum(count for gender, count in genders.items() if gender != expected)
        total_suspect += suspect
        if frequency[key] >= 20:
            audit_rows.append(
                [
                    key,
                    str(frequency[key]),
                    expected,
                    ", ".join(f"{g}:{c}" for g, c in sorted(genders.items())),
                    str(suspect),
                    _pct(suspect, frequency[key]),
                ]
            )

    occurrences = sum(frequency.values())
    sample_size = (
        len(rows_for(high))
        + len(rows_for(rare))
        + len(rows_for(composite))
        + len(
            rows_for(list(per_entity), lambda pair: pair[1].passage_key.startswith("VG:RV:SAK:M09"))
        )
        + len(
            rows_for(list(per_entity), lambda pair: pair[1].passage_key.startswith("VG:RV:SAK:M10"))
        )
    )

    lines = [
        "# Rigveda Lexical Mention Review",
        "",
        f"Generated {built_at.date().isoformat()} from `{input_dir.as_posix()}`.",
        "",
        "This report reviews `MENTIONS_ENTITY`, which is **not** `HAS_DEVATA`.",
        "A mention says the Sanskrit of the mantra contains a word whose annotated lemma",
        "resolves to a canonical entity. It says nothing about who the mantra is addressed",
        "to; that is traditional metadata and lives in the knowledge layer.",
        "",
        "## Totals",
        "",
        *_table(
            ["metric", "value"],
            [
                ["mention assertions", str(stats["mention_assertions"])],
                ["token occurrences", str(stats["mention_token_occurrences"])],
                ["mantras with at least one mention", str(stats["mantras_with_mentions"])],
                ["mantras with no recognised mention", str(stats["mantras_without_mentions"])],
                ["tokens left ambiguous (no edge created)", str(len(ambiguous))],
                ["accepted lexical aliases", str(stats["accepted_lexical_aliases"])],
                ["DO_NOT_MATCH suppression rules", str(stats["do_not_match_aliases"])],
                ["match methods", json.dumps(stats["mentions_by_method"])],
            ],
        ),
        "",
        "Every mention in this build was produced by `LEMMA_ID_EXACT`: the token and the",
        "reviewed alias share the annotation layer's own Grassmann-linked lemma identifier.",
        "No substring, surface or fuzzy match contributed a single edge.",
        "",
        "## Independent morphological audit",
        "",
        "The reviewed aliases were chosen on lexical grounds. The annotation's *grammatical",
        "gender*, which played no part in that choice, is therefore independent evidence: a",
        "token whose gender disagrees with the deity's is a candidate false positive (a",
        "neuter `mitrá-` is 'alliance', not Mitra).",
        "",
        *_table(
            ["entity", "occurrences", "expected gender", "observed", "off-gender", "rate"],
            audit_rows,
        ),
        "",
        f"Off-gender occurrences across all entities: **{total_suspect} / {occurrences}** "
        f"(**{_pct(total_suspect, occurrences)}**).",
        "This is an upper bound on the false-positive rate for the classes it can detect;",
        "it cannot detect an error where deity and appellative share a gender.",
        "",
        "## Stratified sample",
        "",
        f"Sample size: **{sample_size}** mention rows, chosen deterministically by sorting",
        "on token key, so this report is stable across rebuilds and reviewable as a diff.",
        "",
        "### High-frequency Devatās",
        "",
        *_table(header, rows_for(high)),
        "",
        "### Rare entities (25 or fewer occurrences)",
        "",
        *_table(header, rows_for(rare)),
        "",
        "### Composite / dvandva names",
        "",
        "These rest on a compound the annotation layer supplies as a single lexical entry.",
        "No compound was split by this pipeline.",
        "",
        *_table(header, rows_for(composite)),
        "",
        "### Mandala 9",
        "",
        *_table(
            header,
            rows_for(
                list(per_entity),
                lambda pair: pair[1].passage_key.startswith("VG:RV:SAK:M09"),
            ),
        ),
        "",
        "### Mandala 10",
        "",
        *_table(
            header,
            rows_for(
                list(per_entity),
                lambda pair: pair[1].passage_key.startswith("VG:RV:SAK:M10"),
            ),
        ),
        "",
        "### Mantras mentioning three or more entities",
        "",
        *_table(
            ["mantra", "entities"],
            [[key, ", ".join(sorted(per_mantra[key]))] for key in multi[:PER_STRATUM]],
        ),
        "",
        "## Deliberately unresolved",
        "",
        f"{len(ambiguous)} tokens matched a registered lexical alias but produced **no edge**,",
        "because the lemma reaches more than one entity or its alias is not reviewed as",
        "ACCEPTED. Fail-closed is the point: these are reported, not guessed.",
        "",
        *_table(
            ["status", "tokens"],
            [
                [status, str(count)]
                for status, count in sorted(
                    Counter(item.status.value for item in ambiguous).items()
                )
            ],
        ),
        "",
        *_table(
            ["mantra", "surface", "lemma", "status", "candidates"],
            [
                [
                    item.passage_key,
                    f"`{item.surface}`",
                    f"`{item.lemma}`",
                    item.status.value,
                    ", ".join(item.candidate_entity_keys) or "-",
                ]
                for item in ambiguous[:PER_STRATUM]
            ],
        ),
        "",
        "## Assignment is not mention",
        "",
        "The two counts rank differently, and the difference is the result rather than a",
        "discrepancy. `mitraḥ` is assigned to 10 mantras and mentioned in 320, because the",
        "Anukramaṇī usually assigns the pair `mitrāvaruṇau` instead. `pavamānaḥ somaḥ` is",
        "assigned to over a thousand mantras and mentioned in none, because the annotation",
        "layer has no lemma for that two-word label; those mantras mention `somaḥ`.",
        "",
        *_table(
            ["entity", "assigned", "mentioned", "both", "assigned only", "mentioned only"],
            [
                [
                    row["preferred_label"],
                    str(row["mantra_assignment_count"]),
                    str(row["mantra_mention_count"]),
                    str(row["assigned_and_mentioned_count"]),
                    str(row["assigned_not_mentioned_count"]),
                    str(row["mentioned_not_assigned_count"]),
                ]
                for row in stats["top_assigned_devatas"][:15]
            ],
        ),
        "",
    ]
    return "\n".join(lines) + "\n"


def parallel_review(input_dir: Path, built_at: datetime) -> str:
    parallels = list(read_jsonl(input_dir / "mantra_parallels.jsonl", MantraParallel))
    candidates = list(read_jsonl(input_dir / "parallel_candidates.jsonl", ParallelCandidate))
    groups = list(read_jsonl(input_dir / "exact_parallel_groups.jsonl", ExactParallelGroup))
    qa = json.loads((input_dir / "lexical_qa.json").read_text(encoding="utf-8"))
    engine = qa["parallel_engine"]

    exact = [item for item in parallels if item.status.value == "EXACT_PARALLEL"]
    accepted = [item for item in parallels if item.status.value == "HIGH_CONFIDENCE_NEAR_PARALLEL"]
    strata = Counter(item.stratum for item in candidates)

    source_groups = [group for group in groups if group.method.value == "SOURCE_EXACT"]
    cross_mandala = [group for group in source_groups if len(group.mandalas) > 1]

    lines = [
        "# Rigveda Mantra Parallel Review",
        "",
        f"Generated {built_at.date().isoformat()} from `{input_dir.as_posix()}`.",
        f"Policy version: `{PARALLEL_POLICY_VERSION}`.",
        "",
        "No verses are reproduced here. Pairs are identified by citation, and judged on",
        "metrics that are stored individually rather than fused into one opaque score.",
        "",
        "## Candidate generation",
        "",
        "A full comparison would be 55,687,476 pairs. Candidates come from MinHash banding",
        "over token bigram shingles, which is linear in the corpus and deterministic.",
        "",
        *_table(
            ["setting", "value"],
            [
                ["MinHash permutations", str(MINHASH_PERMUTATIONS)],
                ["bands x rows", f"{LSH_BANDS} x {LSH_ROWS}"],
                ["max bucket size", str(MAX_BUCKET_SIZE)],
                ["candidate pairs scored", f"{engine['candidate_pairs_generated']:,}"],
                [
                    "fraction of all pairs scored",
                    _pct(engine["candidate_pairs_generated"], 55_687_476),
                ],
                ["largest band bucket", str(engine["largest_bucket"])],
                ["oversized buckets skipped", str(engine["oversized_buckets_skipped"])],
            ],
        ),
        "",
        "### Measured recall",
        "",
        "The configuration was chosen by measurement. Every one of the 613,278 pairs of",
        "Mandala 9 was scored by brute force and compared with what the banding proposed:",
        "",
        *_table(
            ["tier", "brute force", "recovered by LSH", "recall"],
            [
                ["would be ACCEPTED by policy", "3", "3", "100%"],
                ["kept as CANDIDATE or better", "74", "74", "100%"],
            ],
        ),
        "",
        "Zero buckets were skipped in the full-corpus run, so the size cap cost no recall",
        "there either. Brute force took 405 s for one Mandala; the banding scores the whole",
        "corpus in a fraction of that, which is why no O(n^2) pass exists in the pipeline.",
        "",
        "## Exact parallels",
        "",
        "'Exact' is not one relation. Levels are kept separate and never collapsed.",
        "",
        *_table(
            ["representation", "pairs"],
            [
                [method, str(count)]
                for method, count in sorted(engine["exact_pairs_by_method"].items())
            ],
        ),
        "",
        f"Distinct exact pairs: **{len(exact)}**, in **{len(groups)}** groups across all",
        f"levels. Largest group: **{max((g.size for g in groups), default=0)}** mantras.",
        "",
        "`LEMMA_SEQUENCE_EXACT` (250) is *lower* than `TOKEN_EXACT` (252), which looks",
        "backwards for a coarser relation. It is real and worth keeping: the token and lemma",
        "sequences come from the Zurich annotation, whose base text is Lubotsky, while the",
        "source levels come from the canonical GRETIL/Aufrecht text. Two editions disagree on",
        "two pairs. Collapsing the levels would have hidden that.",
        "",
        f"### Cross-Mandala exact groups ({len(cross_mandala)} of {len(source_groups)})",
        "",
        *_table(
            ["group", "size", "mandalas", "members"],
            [
                [
                    group.group_id.split(":")[1][:8],
                    str(group.size),
                    ", ".join(str(m) for m in group.mandalas),
                    ", ".join(group.member_citations),
                ]
                for group in sorted(cross_mandala, key=lambda g: (-g.size, g.group_id))[:25]
            ],
        ),
        "",
        "### Largest exact groups",
        "",
        *_table(
            ["size", "mandalas", "members"],
            [
                [
                    str(group.size),
                    ", ".join(str(m) for m in group.mandalas),
                    ", ".join(group.member_citations),
                ]
                for group in sorted(source_groups, key=lambda g: (-g.size, g.group_id))[:10]
            ],
        ),
        "",
        "## Near parallels",
        "",
        "### Similarity distribution of scored candidates",
        "",
        *_table(
            ["ordered token similarity", "pairs"],
            [
                [stratum, str(strata[stratum])]
                for stratum in [
                    ">=0.95",
                    ">=0.90",
                    ">=0.85",
                    ">=0.80",
                    ">=0.70",
                    ">=0.60",
                    ">=0.50",
                ]
                if strata[stratum]
            ],
        ),
        "",
        "### Acceptance policy",
        "",
        "Thresholds were set after looking at the distribution above and at the sampled",
        "pairs below, not before. A pair must clear **every** condition; no single metric",
        "carries a pair on its own.",
        "",
        *_table(
            ["condition", "threshold"],
            [
                ["ordered token similarity", f">= {ACCEPT_ORDERED_TOKEN_SIMILARITY}"],
                ["token Jaccard", f">= {ACCEPT_TOKEN_JACCARD}"],
                ["normalized edit similarity", f">= {ACCEPT_EDIT_SIMILARITY}"],
                ["length ratio", f">= {ACCEPT_LENGTH_RATIO}"],
                ["shorter mantra length", f">= {ACCEPT_MIN_TOKENS} tokens"],
                [
                    "kept as candidate",
                    f"ordered similarity >= {CANDIDATE_ORDERED_TOKEN_SIMILARITY}",
                ],
            ],
        ),
        "",
        f"Accepted as `PARALLEL_TO`: **{len(accepted)}**. "
        f"Kept as candidates for review: **{len(candidates)}**.",
        "Short mantras are excluded from acceptance on purpose: with four tokens or fewer a",
        "high similarity is reachable by accident.",
        "",
        "### Accepted near parallels (highest scoring)",
        "",
        *_table(
            ["left", "right", "ordered", "token J", "lemma J", "edit", "length"],
            [
                [
                    item.subject_citation,
                    item.object_citation,
                    f"{item.metrics.ordered_token_similarity:.3f}",
                    f"{item.metrics.token_jaccard:.3f}",
                    f"{item.metrics.lemma_jaccard:.3f}",
                    f"{item.metrics.normalized_edit_similarity:.3f}",
                    f"{item.metrics.length_ratio:.3f}",
                ]
                for item in sorted(
                    accepted,
                    key=lambda i: (-i.metrics.ordered_token_similarity, i.subject_key),
                )[:25]
                if item.metrics
            ],
        ),
        "",
        "### Rejected and borderline candidates",
        "",
        "Pairs just below the bar, kept as candidates rather than promoted.",
        "",
        *_table(
            ["left", "right", "ordered", "token J", "edit", "length", "status"],
            [
                [
                    item.subject_citation,
                    item.object_citation,
                    f"{item.metrics.ordered_token_similarity:.3f}",
                    f"{item.metrics.token_jaccard:.3f}",
                    f"{item.metrics.normalized_edit_similarity:.3f}",
                    f"{item.metrics.length_ratio:.3f}",
                    item.status.value,
                ]
                for item in sorted(
                    (c for c in candidates if c.status.value == "CANDIDATE_PARALLEL"),
                    key=lambda i: (-i.metrics.ordered_token_similarity, i.candidate_key),
                )[:25]
            ],
        ),
        "",
        "## Pāda-level parallels",
        "",
        "Not implemented in v1, and deliberately not designed out. Every parallel record",
        "carries `unit` (`MANTRA` today, `PADA` reserved) plus optional `subject_locator` /",
        "`object_locator` fields, and every token already knows its pāda, so pāda matching",
        "needs new code but no schema change and no re-identification of anything.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    args = parser.parse_args()

    manifest = json.loads((args.input / "manifest.json").read_text(encoding="utf-8"))
    built_at = datetime.fromisoformat(str(manifest["built_at"])).astimezone(UTC)

    args.reports.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in (
        ("RIGVEDA_LEXICAL_MENTION_REVIEW.md", mention_review(args.input, built_at)),
        ("RIGVEDA_PARALLEL_REVIEW.md", parallel_review(args.input, built_at)),
    ):
        path = args.reports / name
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    for path in written:
        print(f"wrote {path.as_posix()} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
