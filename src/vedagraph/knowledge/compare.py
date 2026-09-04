"""Cross-source comparison of traditional metadata. Nothing here overrides anything.

Two independent comparisons, deliberately kept apart:

VHP
    A small reviewed sample of received Ṛṣi/Devatā/Chandas for five Maṇḍala 1 Sūktas,
    written in Devanagari. It is the same *kind* of claim as the Anukramaṇī, so the two
    are compared claim to claim and a disagreement is recorded as a disagreement.

VedaWeb ``hymnAddressee``
    A modern editorial statement of whom a hymn addresses, in English and German. This
    is **not** an Anukramaṇī devatā and is never ingested as ``HAS_DEVATA``. It is only
    surveyed, so that a future ``MODERN_SCHOLARLY_ADDRESSEE`` predicate has evidence.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from vedagraph.identity import uuid_for_urn
from vedagraph.knowledge.build import CorpusIndex
from vedagraph.knowledge.normalize import ascii_key, normalize_label
from vedagraph.models import TraditionalMetadataAssertion
from vedagraph.models.enums import MetadataAgreement, MetadataPredicate, ScopeOrigin
from vedagraph.models.knowledge import MetadataComparison, MetadataSourceAssertion
from vedagraph.storage.jsonl import read_jsonl
from vedagraph.transliteration.indic import DevanagariToIAST

_DEDICATION = re.compile(
    r'<div xml:id="b(?P<book>\d+)_h(?P<hymn>\d+)" ana="[^"]*" type="hymn">\s*'
    r'<div type="dedication">\s*<div type="addressee">\s*'
    r'<p xml:lang="deu">(?P<deu>[^<]*)</p>\s*<p xml:lang="eng">(?P<eng>[^<]*)</p>',
    re.DOTALL,
)


def compare_with_vhp(
    corpus_dir: Path,
    source_assertions: list[MetadataSourceAssertion],
    corpus: CorpusIndex,
) -> list[MetadataComparison]:
    """Compare the reviewed VHP sample against the Anukramaṇī, sūkta by sūkta."""
    transliterator = DevanagariToIAST()
    sukta_by_id = {entity_id: address for address, entity_id in corpus.sukta_ids.items()}

    vhp: dict[tuple[tuple[int, int], MetadataPredicate], list[str]] = defaultdict(list)
    path = corpus_dir / "traditional_metadata.jsonl"
    if path.exists():
        for record in read_jsonl(path, TraditionalMetadataAssertion):
            address = sukta_by_id.get(record.scope.passage_id)
            if address is not None:
                vhp[(address, record.predicate)].append(record.value)

    wsc: dict[tuple[tuple[int, int], MetadataPredicate], list[MetadataSourceAssertion]] = (
        defaultdict(list)
    )
    for assertion in source_assertions:
        parts = assertion.subject_key.split(":")
        wsc[((int(parts[3][1:]), int(parts[4][1:])), assertion.predicate)].append(assertion)

    comparisons: list[MetadataComparison] = []
    for (address, predicate), values in sorted(vhp.items(), key=lambda item: item[0][0]):
        matched = wsc.get((address, predicate), [])
        left = sorted(values)
        left_comparable = sorted({normalize_label(transliterator.transliterate(v)) for v in left})
        right = sorted({item.raw_value for item in matched})
        right_comparable = sorted({normalize_label(item.raw_value) for item in matched})
        scoped = any(item.scope_origin is not ScopeOrigin.SUKTA_WIDE for item in matched)
        agreement, note = _classify(left_comparable, right_comparable, scoped=scoped)
        citation = f"RV {address[0]}.{address[1]}"
        comparisons.append(
            MetadataComparison(
                comparison_id=uuid_for_urn(
                    f"urn:vedagraph:comparison:vhp-wsc2023:{citation}:{predicate.value}"
                ),
                subject_key=corpus.sukta_keys[address],
                citation=citation,
                predicate=predicate,
                left_source_id="VHP",
                right_source_id="WSC2023",
                left_values=left,
                right_values=right,
                left_comparable=left_comparable,
                right_comparable=right_comparable,
                agreement=agreement,
                notes=note,
            )
        )
    comparisons.sort(key=lambda item: (item.subject_key, item.predicate))
    return comparisons


def _stem_tokens(value: str) -> frozenset[str]:
    """A word-order- and final-sandhi-insensitive comparison surface for one label.

    Two documented rules, applied to each folded token: a final ``H`` (the nominative
    visarga, written or not) is dropped, and a final ``O`` is mapped to ``A`` because
    ``-aḥ`` is written ``-o`` before a voiced sound. This surface exists only to
    classify a disagreement; it never merges two entities.
    """
    tokens = set()
    for token in ascii_key(value).split("-"):
        if not token:
            continue
        token = token[:-1] if token.endswith("H") else token
        token = f"{token[:-1]}A" if token.endswith("O") else token
        tokens.add(token)
    return frozenset(tokens)


def _classify(
    left: list[str], right: list[str], *, scoped: bool
) -> tuple[MetadataAgreement, str | None]:
    if not left or not right:
        return MetadataAgreement.UNCOMPARABLE, "one source states nothing for this scope"
    if set(left) == set(right):
        return MetadataAgreement.AGREE_EXACT, None
    folded_left = {ascii_key(value) for value in left}
    folded_right = {ascii_key(value) for value in right}
    if folded_left == folded_right:
        return (
            MetadataAgreement.AGREE_NORMALIZED,
            "identical after transliteration and diacritic folding",
        )
    left_stems = frozenset().union(*(_stem_tokens(value) for value in left))
    right_stems = frozenset().union(*(_stem_tokens(value) for value in right))
    if left_stems == right_stems:
        return (
            MetadataAgreement.LABEL_DIFFERENCE,
            "the same name elements in a different order or final-sandhi form; compared on "
            "the sorted stem-token surface, not merged",
        )
    if folded_left & folded_right:
        if scoped:
            return (
                MetadataAgreement.SCOPE_DIFFERENCE,
                "the Anukramaṇī scopes some labels to numbered verses; VHP states one hymn-wide "
                "claim",
            )
        return MetadataAgreement.LABEL_DIFFERENCE, "the sources share some labels but not all"
    return (
        MetadataAgreement.SOURCE_CONFLICT,
        "no label is shared after transliteration and folding; neither source is preferred",
    )


def vedaweb_addressees(tei_paths: list[Path]) -> dict[tuple[int, int], tuple[str, str]]:
    """Hymn-level ``(english, german)`` addressee strings from pinned VedaWeb TEI.

    Read for reporting only. This is a different annotation concept from an Anukramaṇī
    devatā and never becomes a knowledge assertion.
    """
    found: dict[tuple[int, int], tuple[str, str]] = {}
    for path in sorted(tei_paths):
        text = path.read_text(encoding="utf-8")
        for match in _DEDICATION.finditer(text):
            address = (int(match.group("book")), int(match.group("hymn")))
            found[address] = (match.group("eng").strip(), match.group("deu").strip())
    return found
