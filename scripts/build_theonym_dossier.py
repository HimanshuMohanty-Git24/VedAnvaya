"""Assemble, per deity, everything needed to adjudicate its theonym forms.

Three facts about this corpus decide the shape of the whole theonym layer, and none of
them is a matter of taste.

**The Rigveda is manually annotated and the other three Vedas are not.**
``data/knowledge/rigveda_lexical_v1/tokens.jsonl`` carries the University of Zurich
morphosyntactic annotation of every one of 164,758 Rigvedic tokens -- lemma, case, gender,
number, part of speech -- with per-token provenance. So for the Rigveda a theonym mention
does not have to be guessed from a string: a scholarly source states that this token's
lemma is ``indra-``. The Samaveda, Yajurveda and Atharvaveda have no such layer, so there
the only available claim is a surface match. Those are different claims and this module
keeps them apart, because presenting them as one would make the Rigveda's precision look
like the corpus's precision.

**The attested paradigm is not the grammatical paradigm.** The annotation records what the
text actually spells, which includes forms a paradigm table would not predict
(``indram-indram``, a dual with an editorial ``=``) and excludes forms it would. Taking the
form inventory from the annotation rather than from a generator is therefore both more
complete and more honest, and it is why the SV/YV/AV matcher below is seeded from
Rigvedic attestation.

**Some Anukramani devata labels are ordinary common nouns.** ``VG:DEVATA:RATHAH`` is the
deified chariot and ``ratha`` is "a chariot", 471 annotated tokens of it; ``VG:DEVATA:KAH``
is Prajapati-as-"Who?" and ``ka`` is the interrogative pronoun, 468 tokens. Lemma identity
alone would assert the deity Chariot on 466 passages about chariots. That is the failure
this dossier exists to make visible *before* anything is written: every candidate arrives
with its ambiguity exposed and nothing is accepted by default.

Usage::

    python scripts/build_theonym_dossier.py --targets data/registry/theonym_targets.yaml \
        --out data/registry/theonym_dossier.json
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import os
import pathlib
import sys
import unicodedata
from collections.abc import Iterable
from typing import Any, Final

import orjson
import yaml

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.enrich.concepts import fold_alias  # noqa: E402
from vedagraph.enrich.corpus import VEDAS, Corpus, load_corpus  # noqa: E402
from vedagraph.enrich.surfaces import render_for_display  # noqa: E402

TOKENS_PATH = pathlib.Path("data") / "knowledge" / "rigveda_lexical_v1" / "tokens.jsonl"
DEVATA_REGISTRY = pathlib.Path("data") / "registry" / "devatas.yaml"

#: Host tokens listed per candidate form, so a containment error is visible rather than
#: inferred from a ratio.
_MAX_HOSTS = 10

#: Example passage keys kept per form.
_MAX_EXAMPLES = 3

#: Vocalic r and l are written by the annotation as a base letter plus COMBINING RING
#: BELOW, and by the registry and the corpus surfaces as a precomposed character. See
#: :func:`fold_annotation`.
_RING_BELOW_FOLDS = (("r̥", "ṛ"), ("l̥", "ḷ"))


#: Vowels as the folded surface spells them. Used only to derive a search prefix; see
#: :func:`search_prefix`. Vocalic r and l are absent on purpose -- the fold replaces them
#: with private-use sentinels, and a sentinel is never a stem's final letter in a way that
#: inflection removes.
_FOLDED_FINAL_VOWELS: Final[frozenset[str]] = frozenset("aāiīuūeo")

#: A search prefix shorter than this is not used for substring discovery. Two-character
#: stems -- ``ap`` for the waters, ``ka`` for Prajapati-as-"Who?" -- occur inside several
#: thousand unrelated words, and a prefix that short finds vocabulary rather than forms.
MIN_SEARCH_PREFIX = 3


def fold_annotation(text: str) -> str:
    """Fold a VedaWeb lemma or surface onto the corpus search surface.

    Three normalizations have to happen and only one of them is :func:`fold_alias`.

    The annotation writes vocalic r as ``r`` plus COMBINING RING BELOW where the registry
    and the corpus surfaces use the precomposed character; ignoring that silently loses
    every deity and concept whose name contains it -- brhaspati, prthivi, rbhu, nirrti,
    rta, amrta, mrtyu.

    And a hyphen in a lemma is a morpheme boundary, not punctuation. ``fold_alias``
    normalizes punctuation to a space, so the dual lemma ``indra-vayu`` folded to
    ``"indra vayu"`` *with a space* -- a string no single corpus token can ever equal, so
    that deity's entire discovery channel was dead rather than merely lossy. Hyphens are
    removed before folding.
    """
    decomposed = unicodedata.normalize("NFD", text.replace("-", ""))
    for source, target in _RING_BELOW_FOLDS:
        decomposed = decomposed.replace(source, target)
    return fold_alias(unicodedata.normalize("NFC", decomposed))


def _drop_final_vowel(folded_stem: str) -> str:
    """The stem minus one final vowel. The fallback rule; see :func:`search_prefix`."""
    if folded_stem and folded_stem[-1] in _FOLDED_FINAL_VOWELS:
        return folded_stem[:-1]
    return folded_stem


def _longest_common_prefix(values: Iterable[str]) -> str:
    items = [value for value in values if value]
    if not items:
        return ""
    return os.path.commonprefix(items)


def search_prefix(folded_stem: str, attested: Iterable[str] = ()) -> str:
    """The invariant part of a stem, for substring discovery.

    This function has been wrong twice, in two different ways, and both were caught by
    adjudicators reading the corpus rather than the packet. The history is kept because it
    is the argument for the current rule.

    **First it tested ``stem in token``.** That is wrong for every stem ending in a vowel,
    because inflection replaces the vowel: ``sarasvatī`` does not occur inside
    ``sarasvatyai`` ("hail to Sarasvatī!", 19 non-Rigvedic mantras), ``pavamāna`` does not
    occur inside ``pavamāno`` (21), ``mitrāvaruṇa`` does not occur inside ``mitrāvaruṇāv``.

    **Then it dropped one final vowel.** That fixes the vowel stems and does nothing at all
    for a **consonant stem**, which is 13 of the 51 candidates here. The worst case is the
    one it was supposed to fix: the goddess Sarasvatī is lemmatised under the consonant
    stem ``sárasvant-``, her forms use the weak stem ``sarasvat-`` with the nasal dropped,
    so ``sarasvant`` prefixes none of them and the rule was a no-op. It found 2 corpus
    tokens against 46 that exist.

    **So the prefix is now taken from the data.** The longest common prefix of the forms
    the annotation actually attests is, by construction, a prefix of all of them -- for
    ``sárasvant-`` it is ``sarasv``, which finds all 46 tokens with no noise. Where that
    LCP falls below :data:`MIN_SEARCH_PREFIX` the vowel rule is used instead, because two
    stems have a two-character LCP and would *regress* under the LCP alone: ``uṣas`` gives
    ``uṣ`` and ``vāc`` gives ``vā``, costing 44 and 78 candidate forms respectively.

    A shorter prefix buys noise as well as recall, and the noise is not always obvious:
    ``aśvin-`` yields ``aśv``, which also prefixes ``aśva-`` "horse" -- a different entity
    in this same registry. That is why everything this returns is a *candidate* an
    adjudicator has to accept, and why the dossier reports the prefix it used.
    """
    lcp = _longest_common_prefix(attested)
    if len(lcp) >= MIN_SEARCH_PREFIX:
        return lcp
    return _drop_final_vowel(folded_stem)


def load_annotation() -> dict[str, dict[str, Any]]:
    """Index the Rigvedic annotation by folded normalized lemma.

    Returns, per lemma: the accented lemma labels it appears under, the passages it
    occurs in, and every attested (surface, case, number, gender) with a count. The
    accented labels matter: neuter *brahman* (the formulation) and masculine *brahman*
    (the priest) share one normalized lemma and are two different entities, and the V2
    pass leaked fourteen passages between exactly that pair.
    """
    index: dict[str, dict[str, Any]] = {}
    path = PROJECT_ROOT / TOKENS_PATH
    if not path.exists():
        raise SystemExit(f"annotation not found: {path}")
    with path.open("rb") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            record = orjson.loads(raw)
            key = fold_annotation(record.get("normalized_lemma") or "")
            entry = index.setdefault(
                key,
                {
                    "normalized_lemma": record.get("normalized_lemma"),
                    "lemma_labels": collections.Counter(),
                    "passages": set(),
                    "forms": collections.Counter(),
                    "tokens": 0,
                },
            )
            entry["tokens"] += 1
            entry["lemma_labels"][record.get("lemma")] += 1
            entry["passages"].add(record["passage_key"])
            features = record.get("morphological_features") or {}
            entry["forms"][
                (
                    record.get("surface_form"),
                    features.get("case"),
                    features.get("number"),
                    features.get("gender"),
                    record.get("lemma"),
                )
            ] += 1
    return index


def corpus_index(corpus: Corpus) -> tuple[dict[str, dict[str, int]], dict[str, list[str]]]:
    """Folded token -> per-Veda mantra count, and folded token -> sample passage keys."""
    counts: dict[str, dict[str, int]] = collections.defaultdict(lambda: dict.fromkeys(VEDAS, 0))
    samples: dict[str, list[str]] = collections.defaultdict(list)
    for mantra in corpus.mantras:
        for token in set(mantra.surfaces.tokens):
            counts[token][mantra.veda] += 1
            if len(samples[token]) < _MAX_EXAMPLES:
                samples[token].append(mantra.passage_key)
    return dict(counts), dict(samples)


def _hosts(folded_form: str, tokens: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    """Tokens that merely *contain* this form, with counts. The containment view."""
    hosts = [
        {
            "host": render_for_display(token),
            "per_veda": per_veda,
            "total": sum(per_veda.values()),
        }
        for token, per_veda in tokens.items()
        if folded_form in token and token != folded_form
    ]
    hosts.sort(key=lambda host: -int(host["total"]))
    return hosts[:_MAX_HOSTS]


def build_deity(
    entity_key: str,
    label: str,
    lemma_stem: str,
    annotation: dict[str, dict[str, Any]],
    tokens: dict[str, dict[str, int]],
    samples: dict[str, list[str]],
    other_stems: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One deity's complete adjudication dossier."""
    stem_folded = fold_annotation(lemma_stem)
    ann = annotation.get(stem_folded)
    attested = [fold_annotation(str(surface)) for (surface, *_rest) in ann["forms"]] if ann else []
    prefix = search_prefix(stem_folded, attested)
    prefix_usable = len(prefix) >= MIN_SEARCH_PREFIX
    other_stems = other_stems or {}
    forms: list[dict[str, Any]] = []
    seen: set[str] = set()

    if ann:
        for (surface, case, number, gender, lemma_label), count in ann["forms"].most_common():
            folded = fold_annotation(surface or "")
            if not folded:
                continue
            per_veda = tokens.get(folded, dict.fromkeys(VEDAS, 0))
            forms.append(
                {
                    "surface": surface,
                    "folded": folded,
                    "source": "RV_ANNOTATION",
                    # Present on every form so a consumer can rely on the key. An
                    # annotated form is an inflection of the stem by construction.
                    "position": "INFLECTION",
                    "lemma_label": lemma_label,
                    "case": case,
                    "number": number,
                    "gender": gender,
                    "rv_annotated_tokens": count,
                    "corpus_mantras": dict(per_veda),
                    "corpus_total": sum(per_veda.values()),
                    "non_rv_mantras": sum(per_veda[veda] for veda in ("SV", "YV", "AV")),
                    "hosts": _hosts(folded, tokens),
                    "examples": samples.get(folded, []),
                }
            )
            seen.add(folded)

    # Forms the other three Vedas spell that the Rigveda does not attest. These decide
    # non-Rigvedic recall, and they are exactly the ones no annotation can vouch for --
    # so they are listed under their own source marker rather than mixed in.
    for token, per_veda in tokens.items():
        if token in seen or not prefix_usable or prefix not in token:
            continue
        non_rv = sum(per_veda[veda] for veda in ("SV", "YV", "AV"))
        if non_rv == 0:
            continue
        forms.append(
            {
                "surface": render_for_display(token),
                "folded": token,
                "source": "CORPUS_ONLY",
                # Where the prefix sits in the token. The cheapest signal an adjudicator
                # has: INITIAL is an inflection or a compound whose first member is the
                # theonym, FINAL is usually a Samavedic fusion of a preceding word onto
                # it, and INTERNAL outside the Samaveda is usually coincidence.
                "position": (
                    "EXACT"
                    if token == prefix
                    else "INITIAL"
                    if token.startswith(prefix)
                    else "FINAL"
                    if token.endswith(prefix)
                    else "INTERNAL"
                ),
                "lemma_label": None,
                "case": None,
                "number": None,
                "gender": None,
                "rv_annotated_tokens": 0,
                "corpus_mantras": dict(per_veda),
                "corpus_total": sum(per_veda.values()),
                "non_rv_mantras": non_rv,
                "hosts": _hosts(token, tokens),
                "examples": samples.get(token, []),
            }
        )

    forms.sort(key=lambda form: (-int(form["corpus_total"]), str(form["folded"])))
    return {
        "entity_key": entity_key,
        # Deities whose own lemma stem this prefix is a prefix of. A shortened prefix can
        # walk straight into another registered entity and arrive wearing the most
        # trustworthy position value, INITIAL, at a volume that looks like importance:
        # aśvin- yields the prefix `aśv`, which also prefixes aśva- "horse", and the horse
        # forms then outnumber anything the adjudicator was expecting. Flagged here rather
        # than left for an adjudicator to notice.
        "prefix_overlaps_deities": sorted(
            other_key
            for other_key, other_stem in other_stems.items()
            if other_key != entity_key and other_stem.startswith(prefix) and prefix
        ),
        "registry_label": label,
        "lemma_stem": lemma_stem,
        "stem_folded": stem_folded,
        "search_prefix": prefix,
        # False means substring discovery was skipped entirely for this deity, so its
        # candidate list is annotation-attested forms only. A finding, not a silent limit.
        "search_prefix_usable": prefix_usable,
        "rv_annotation_present": ann is not None,
        "rv_annotated_tokens": ann["tokens"] if ann else 0,
        "rv_annotated_passages": len(ann["passages"]) if ann else 0,
        "rv_lemma_labels": dict(ann["lemma_labels"]) if ann else {},
        "distinct_forms": len(forms),
        "vocative_forms": sum(1 for form in forms if form["case"] == "VOC"),
        "forms": forms,
    }


def load_targets(path: pathlib.Path) -> list[tuple[str, str]]:
    """Read the (entity_key, lemma_stem) target list authored by the architect."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [(row["entity_key"], row["lemma_stem"]) for row in document["targets"]]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--print", action="store_true", dest="do_print")
    args = parser.parse_args()

    registry = yaml.safe_load((PROJECT_ROOT / DEVATA_REGISTRY).read_text(encoding="utf-8"))
    labels = {row["entity_key"]: row["preferred_label"] for row in registry["entities"]}
    targets = load_targets(args.targets)
    print(f"targets: {len(targets)}")
    annotation = load_annotation()
    print(f"rv annotation lemmas: {len(annotation)}")
    corpus = load_corpus(PROJECT_ROOT)
    counts = corpus.counts()
    print("corpus: " + "  ".join(f"{veda}={counts.get(veda, 0)}" for veda in VEDAS))
    tokens, samples = corpus_index(corpus)
    print(f"folded corpus tokens: {len(tokens)}")

    other_stems = {key: fold_annotation(stem) for key, stem in targets}
    dossiers = [
        build_deity(key, labels.get(key, key), stem, annotation, tokens, samples, other_stems)
        for key, stem in targets
    ]
    payload = {
        "annotation_source": "VEDAWEB.ZURICH MANUAL_SCHOLARLY_ANNOTATION (Rigveda only)",
        "corpus_counts": counts,
        "deities": dossiers,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out}")

    for dossier in dossiers:
        marker = "annotated" if dossier["rv_annotation_present"] else "NO RV ANNOTATION"
        print(
            f"  {dossier['entity_key']:34} {dossier['distinct_forms']:4d} forms  "
            f"{dossier['vocative_forms']:3d} voc  "
            f"rv_tokens={dossier['rv_annotated_tokens']:5d}  {marker}"
        )
        if args.do_print:
            for form in dossier["forms"][:25]:
                per = "/".join(
                    f"{veda}={form['corpus_mantras'][veda]}"
                    for veda in VEDAS
                    if form["corpus_mantras"][veda]
                )
                print(
                    f"      {form['surface']:<22} {form['case']!s:<5}/"
                    f"{form['number']!s:<3} {form['source']:<14} {per}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
