""" "This passage names this entity" -- Sanskrit-grounded, uncapped, across four Vedas.

This layer exists because the V1 concept layer answers a different question than the one
the domain graph needs, and answering both with one edge type made each answer worse.

``ABOUT_CONCEPT`` asks *what is this passage about?* That is a selective judgement, so it
is capped at four concepts per passage and it admits English-translation evidence to
improve recall. Both choices are right for aboutness and wrong for coverage, and both were
measured biting hard:

* the cap is binding, not theoretical -- the maximum concepts on any passage is exactly 4,
  and 19.9% of passages have no concept edge at all;
* 21,246 of 47,542 concept assertions (44.7%) rest on **no Sanskrit evidence whatsoever**.
  They fired on a word in Griffith or Whitney, at confidence 0.42. That is a defensible
  claim about a nineteenth-century translator's vocabulary and a poor one about the verse.

So this module asks the other question -- *which entities does this passage name?* -- and
answers it under different rules:

**Sanskrit only.** A mention is a claim about the text. An English match is a claim about
the translator, and there is no amount of it that makes the first claim. This also removes
the Sāmaveda's structural disadvantage in reverse: the Sāmaveda has no translations at all,
so it was the one Veda whose concept coverage was already honest.

**Uncapped in practice.** A passage naming barley, cattle, ghee and a chariot names four
things, and dropping one because a fifth scored higher is a loss with no upside when the
question is coverage. The bound in :mod:`vedagraph.domain.guards` is there to catch a
runaway lexicon, not to select among good matches.

**Theonym ambiguity is recorded, not resolved.** ``agniḥ`` means both "fire" and "Agni",
and Vedic Sanskrit has no second word for the impersonal element. A token matcher cannot
decide which is meant, so an edge whose every matched alias is also a deity's name is
flagged ``theonym_ambiguous`` rather than silently asserted as the impersonal reading.
Measured over the V1 concept layer this is 562 assertions of 47,542 (1.2%) -- small, and
concentrated exactly where it would mislead most: 123 on ``AGNI-FIRE``, 124 on
``BRAHMAN-FORMULATION``, 96 on ``SOMA-DRINK``.

Every measured constant this module relies on -- the sandhi length floor, the audited
suppression list, the alias folding -- is imported from :mod:`vedagraph.enrich.concepts`
rather than restated. Those numbers were established against this corpus by measurement,
and a second copy of them would be a second thing to keep true.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Final

from vedagraph.domain.ontology import DOMAIN_MODEL_VERSION, QualityTier
from vedagraph.enrich.concepts import (
    MIN_SANDHI_ALIAS_CHARS,
    SANDHI_MATCH_VEDAS,
    SANDHI_SUPPRESSED_ALIASES,
    fold_alias,
)
from vedagraph.enrich.corpus import Corpus, MantraRecord
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    RunReport,
    TrustClass,
    run_id,
    stable_id,
)
from vedagraph.enrich.records import ConceptRow
from vedagraph.enrich.surfaces import render_for_display

#: Additional sandhi-path suppressions measured against the V2 lexicon, layered on top of
#: :data:`~vedagraph.enrich.concepts.SANDHI_SUPPRESSED_ALIASES` rather than added to it.
#:
#: Kept separate for one reason: the V1 list was measured for the V1 build and the V1
#: concept artifact must stay reproducible from the V1 constants. Editing that dict in
#: place would silently mean the shipped ``concept_assertions.jsonl`` could no longer be
#: rebuilt from the code that claims to build it.
#:
#: Each entry clears the six-character floor and still sits inside a Samavedic word meaning
#: something else. All five are exact and safe on the token path, which is where suppression
#: leaves them -- deleting the aliases outright would give up 17 correct Rigvedic and
#: Atharvavedic mentions to remove 23 Samavedic ones, which is the trade this list exists to
#: avoid. The first is the worst: it moved fourteen Samavedic passages from the formulation
#: entity to the priest entity, so the leak was between two entities of *this same lexicon*.
V2_SANDHI_SUPPRESSED_ALIASES: Final[dict[str, str]] = {
    # One entry, two independent measurements, deliberately merged. This key was listed
    # twice -- once for the V2 lexicon and once by the V3 ritual specialist, who
    # re-measured it without reference to the first -- and because a later dict literal
    # key silently overwrites an earlier one, the V2 rationale was being discarded at
    # import. The suppression itself never changed; only the reason for it was lost, which
    # is exactly the evidence someone would need before daring to remove the suppression.
    "brahmā": (
        "inside brahmāṇi and brahmaṇaḥ, which are aliases of "
        "VG:CONCEPT:BRAHMAN-FORMULATION: 18 Samavedic substring hits against 4 genuine "
        "token hits, so the priest entity took fourteen passages from the formulation "
        "one. Independently re-measured by the V3 ritual specialist at 64 substring hits "
        "inside brahmāṇi ('prayers', neuter plural) in the one Veda where the substring "
        "pass runs -- two measurements, same conclusion"
    ),
    "āyasam": "inside viśvadhāyasam and bhūridhāyasam ('all-nourishing'): 2 hits, 0 genuine",
    "āyasaḥ": "inside jyāyasaḥ ('greater') and viśvadhāyasaḥ",
    "dhānāḥ": (
        "inside dadhānāḥ ('holding') and yātudhānāḥ ('sorcerers'), the second an alias of "
        "a different entity in this lexicon"
    ),
    "avīnām": "inside kavīnām, 'of the poets'",
    # ---- V3 -------------------------------------------------------------------------
    # Each measured against the corpus by the specialist who needed it, with the host word
    # named. The first is the most instructive: it was already live on
    # VG:CONCEPT:YAKSMA-DISEASE, so this is an existing defect being closed rather than a
    # new risk being avoided.
    "amīvāḥ": (
        "inside anamīvāḥ ('free from disease'), whose sense is the exact opposite; 5 of "
        "15 sandhi hits are the negation or a word-boundary glue"
    ),
    "rapaso": "inside nārīrapaso, the glue of nā́rīr apáso ('women, active ones')",
    "apacit": ("inside apacitiṃ ('requital', RV 4.28.4) and inside a Yajurvedic glue at VSM 12.97"),
    "arāyam": "7 of 8 sandhi hits are word-boundary glue rather than the sprite",
    "sarasvatyām": (
        "inside the glue of sárasvatyā plus an m-initial word -- AVS 5.7.5 sarasvatyā "
        "manoyujā, VSM 21.46 and 21.47 sarasvatyā meṣasya -- all three of which are the "
        "goddess. Without this the new River entity acquires three goddess passages and "
        "falls to 40% precision, which is why the specialist made the node conditional "
        "on this suppression"
    ),
}

_STAGE: Final = "domain-mentions"
_METHOD_ROOT: Final = "domain-mention-v1"
_PATH_TOKEN: Final = "sanskrit-token"
_PATH_SANDHI: Final = "sanskrit-sandhi"

#: A whole-word Sanskrit match. The strongest claim this layer makes, and the only one
#: available outside the Sāmaveda.
_TOKEN_SCORE: Final = 0.90

#: A substring match on the boundary-free surface, Sāmaveda only. Materially weaker: the
#: surface has no word boundaries, so a hit may span two words. Scored well below the
#: token path and carrying its path in the method, so it can be filtered out wholesale.
_SANDHI_SCORE: Final = 0.60

#: Context tokens kept either side of a hit, so the quote is evidence rather than the verse.
_CONTEXT_TOKENS: Final = 2
_SANDHI_CONTEXT_CHARS: Final = 25


@dataclass(frozen=True)
class MentionIndex:
    """The lexicon inverted for matching, plus the theonym set.

    ``token`` maps a folded alias to its entity. It is one-to-one because the registry
    loader refuses an alias claimed by two entities; that validation is what makes a plain
    dict correct here rather than a dict-of-lists with a tie-break nobody would keep
    deterministic.
    """

    token: dict[str, str]
    sandhi: tuple[tuple[str, str], ...]
    #: Folded aliases that are also a Devatā label form. Not excluded -- recorded.
    theonyms: frozenset[str]

    @property
    def counts(self) -> dict[str, int]:
        return {
            "token_aliases": len(self.token),
            "sandhi_aliases": len(self.sandhi),
            "theonym_aliases": len(self.theonyms),
        }


def devata_label_forms(devata_labels: Iterable[str]) -> frozenset[str]:
    """Folded forms of every Devatā label, including each word of a compound label.

    ``pavamānaḥ somaḥ`` contributes ``pavamanah``, ``somah`` and the whole string, because
    a concept alias colliding with either word of a compound deity label is ambiguous in
    the same way as one colliding with the whole.
    """
    forms: set[str] = set()
    for label in devata_labels:
        whole = fold_alias(label)
        if whole:
            forms.add(whole)
        for part in label.replace("-", " ").split():
            folded = fold_alias(part)
            if folded:
                forms.add(folded)
    return frozenset(forms)


def build_index(entities: Sequence[ConceptRow], devata_labels: Iterable[str] = ()) -> MentionIndex:
    """Invert the lexicon, and mark which aliases are also deity names."""
    theonym_forms = devata_label_forms(devata_labels)
    token: dict[str, str] = {}
    sandhi: list[tuple[str, str]] = []
    theonyms: set[str] = set()
    for entity in entities:
        for alias in entity.aliases_sa:
            folded = fold_alias(alias)
            if not folded:
                continue
            token[folded] = entity.concept_id
            if folded in theonym_forms:
                theonyms.add(folded)
            if (
                len(folded) >= MIN_SANDHI_ALIAS_CHARS
                and alias not in SANDHI_SUPPRESSED_ALIASES
                and alias not in V2_SANDHI_SUPPRESSED_ALIASES
            ):
                sandhi.append((folded, entity.concept_id))
    return MentionIndex(token=token, sandhi=tuple(sorted(sandhi)), theonyms=frozenset(theonyms))


@dataclass
class MentionRow:
    """One (passage, entity) mention with the aliases and text that support it."""

    passage_key: str
    veda: str
    entity_key: str
    matched_aliases: tuple[str, ...]
    paths: tuple[str, ...]
    theonym_ambiguous: bool
    provenance: Provenance

    @property
    def mention_id(self) -> str:
        return stable_id("DOMAIN-MENTION", self.passage_key, self.entity_key)

    def as_row(self) -> dict[str, Any]:
        return {
            "mention_id": self.mention_id,
            "passage_key": self.passage_key,
            "veda": self.veda,
            "entity_key": self.entity_key,
            "matched_aliases": list(self.matched_aliases),
            "alias_count": len(self.matched_aliases),
            "paths": list(self.paths),
            "theonym_ambiguous": self.theonym_ambiguous,
            "quality_tier": str(QualityTier.TIER_B),
            "domain_model_version": DOMAIN_MODEL_VERSION,
            **self.provenance.as_edge_properties(),
        }


@dataclass
class _Hit:
    aliases: set[str] = field(default_factory=set)
    quote: str = ""
    surface: str = ""

    def add(self, alias: str, quote: str, surface: str) -> None:
        self.aliases.add(alias)
        if not self.quote:
            self.quote = quote
            self.surface = surface


def _token_hits(mantra: MantraRecord, index: MentionIndex) -> dict[str, _Hit]:
    tokens = mantra.surfaces.tokens
    found: dict[str, _Hit] = {}
    for position, token in enumerate(tokens):
        entity_key = index.token.get(token)
        if entity_key is None:
            continue
        window = tokens[max(0, position - _CONTEXT_TOKENS) : position + _CONTEXT_TOKENS + 1]
        found.setdefault(entity_key, _Hit()).add(token, " ".join(window), "script_folded")
    return found


def _sandhi_hits(mantra: MantraRecord, index: MentionIndex, already: set[str]) -> dict[str, _Hit]:
    """Substring pass over the boundary-free surface, Sāmaveda only.

    Restricted to entities the token pass missed, so the two Sanskrit paths never both
    claim one mention: an entity reached by both is reached by the stronger one, and
    reporting the weaker alongside it would misdescribe the evidence.
    """
    text = mantra.surfaces.sandhi_insensitive
    found: dict[str, _Hit] = {}
    for alias, entity_key in index.sandhi:
        if entity_key in already:
            continue
        position = text.find(alias)
        if position < 0:
            continue
        quote = text[
            max(0, position - _SANDHI_CONTEXT_CHARS) : position + len(alias) + _SANDHI_CONTEXT_CHARS
        ]
        found.setdefault(entity_key, _Hit()).add(alias, quote, "sandhi_insensitive")
    return found


def extract_mentions(
    corpus: Corpus,
    entities: Sequence[ConceptRow],
    devata_labels: Iterable[str] = (),
    *,
    max_per_passage: int = 24,
    max_edges: int = 400_000,
) -> tuple[list[MentionRow], RunReport]:
    """Find every entity each mantra names, on Sanskrit evidence only.

    The caps are runaway guards, not selectors. ``max_per_passage`` is set well above the
    observed maximum so that it does not silently choose between good matches the way the
    concept layer's cap of four does; if it ever binds, the report says so and that is a
    signal the lexicon has grown a bad alias rather than that the passage is rich.
    """
    index = build_index(entities, devata_labels)
    identity = run_id(_STAGE, len(corpus.mantras), len(entities), len(index.token))
    report = RunReport(stage=_STAGE)
    rows: list[MentionRow] = []
    per_veda: dict[str, int] = {}
    covered: dict[str, set[str]] = {}
    path_counts: dict[str, int] = {_PATH_TOKEN: 0, _PATH_SANDHI: 0}
    theonym_total = 0

    for mantra in corpus.mantras:
        per_veda[mantra.veda] = per_veda.get(mantra.veda, 0) + 1
        token_hits = _token_hits(mantra, index)
        sandhi_hits = (
            _sandhi_hits(mantra, index, set(token_hits))
            if mantra.veda in SANDHI_MATCH_VEDAS
            else {}
        )
        if not token_hits and not sandhi_hits:
            continue

        built: list[MentionRow] = []
        for entity_key, hit in sorted(token_hits.items()):
            built.append(
                _build_row(mantra, entity_key, hit, _PATH_TOKEN, _TOKEN_SCORE, index, identity)
            )
        for entity_key, hit in sorted(sandhi_hits.items()):
            built.append(
                _build_row(mantra, entity_key, hit, _PATH_SANDHI, _SANDHI_SCORE, index, identity)
            )

        if len(built) > max_per_passage:
            report.cap("mentions_per_passage", len(built) - max_per_passage)
            report.cap(f"mentions_per_passage:{mantra.veda}", len(built) - max_per_passage)
            # Deterministic: highest score first, then entity key. Never input order.
            built.sort(key=lambda row: (-row.provenance.score, row.entity_key))
            built = built[:max_per_passage]

        for row in built:
            rows.append(row)
            covered.setdefault(mantra.veda, set()).add(mantra.passage_key)
            for path in row.paths:
                path_counts[path] += 1
            if row.theonym_ambiguous:
                theonym_total += 1

    rows.sort(key=lambda row: (row.passage_key, row.entity_key))
    if len(rows) > max_edges:
        report.cap("global_mention_cap", len(rows) - max_edges)
        rows = rows[:max_edges]

    report.produced = len(rows)
    report.notes = {
        "entities": len(entities),
        "aliases": index.counts,
        "mentions_by_path": dict(sorted(path_counts.items())),
        "theonym_ambiguous": theonym_total,
        "coverage_by_veda": {
            veda: {
                "mantras": per_veda[veda],
                "with_mention": len(covered.get(veda, set())),
                "coverage": round(len(covered.get(veda, set())) / per_veda[veda], 4),
            }
            for veda in sorted(per_veda)
        },
        "distinct_entities_used": len({row.entity_key for row in rows}),
    }
    return rows, report


def _build_row(
    mantra: MantraRecord,
    entity_key: str,
    hit: _Hit,
    path: str,
    base_score: float,
    index: MentionIndex,
    identity: str,
) -> MentionRow:
    aliases = tuple(sorted(hit.aliases))
    # An entity reached only through aliases that are also deity names cannot be
    # distinguished from a mention of the deity. Recorded on the edge, not resolved.
    ambiguous = bool(aliases) and all(alias in index.theonyms for alias in aliases)
    provenance = Provenance(
        trust=TrustClass.DETERMINISTIC_DERIVED,
        method=f"{_METHOD_ROOT}:{path}",
        score=base_score,
        evidence=(
            EvidenceSpan(
                locator=mantra.passage_key,
                surface=hit.surface,
                # Rendered on the way out: the folded surface carries private-use
                # sentinels that render as nothing, which would publish `tasya` for
                # `ṛtasya` -- a different Sanskrit word, in evidence that looks checkable.
                quote=render_for_display(hit.quote),
            ),
        ),
        state=AssertionState.ACCEPTED,
        run_id=identity,
        notes="matched aliases: " + ", ".join(render_for_display(alias) for alias in aliases),
    )
    return MentionRow(
        passage_key=mantra.passage_key,
        veda=mantra.veda,
        entity_key=entity_key,
        matched_aliases=tuple(render_for_display(alias) for alias in aliases),
        paths=(path,),
        theonym_ambiguous=ambiguous,
        provenance=provenance,
    )
