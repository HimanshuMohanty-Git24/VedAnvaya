"""The Atharvavedic ``DevataAscription`` namespace must hold ascriptions and nothing else.

Whitney prints the Bṛhatsarvānukramaṇī excerpt as one period-delimited run with no field
markers, so the ascription sits in the same line as the verse count, the pāda addresses and
the metre. The first harvest took the whole run: the graph asserted that the
deity-ascription of AVS 18.4 was ``ekonanavati`` -- eighty-nine -- on 90 passages, that AVS
18.3's was ``saptatis tryadhikā`` -- seventy-three -- on 74, and that AVS 19.38's was
``a-d``, a reference to verse quarters. One real ascription stood as three nodes because the
scan broke the middle of ``bahu``.

Two audits sampled the value space and missed all of it, so nothing here samples. Every
test enumerates all 324 values, and the numeral test in particular is written against an
independent morpheme vocabulary rather than against the builder's own numeral table -- a
test that imported the table would only ever agree with itself.

Everything skips when the generated layer is absent: it is deliberately not in Git. The
live test is additionally gated on ``VEDAGRAPH_LIVE_NEO4J``.
"""

from __future__ import annotations

import difflib
import functools
import importlib.util
import io
import json
import os
import pathlib
import re
import sys
import unicodedata
import warnings
from typing import Any

import pytest
import yaml

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "data" / "registry" / "devata_ascriptions_av.yaml"
CHANDAS_REGISTRY = PROJECT_ROOT / "data" / "registry" / "chandas_av.yaml"
RISHI_REGISTRY = PROJECT_ROOT / "data" / "registry" / "rishis_av.yaml"
KNOWLEDGE = PROJECT_ROOT / "data" / "knowledge" / "atharvaveda_deterministic_v1"
CORPUS = PROJECT_ROOT / "data" / "canonical" / "atharvaveda_saunaka_digital_working_v1"

pytestmark = pytest.mark.skipif(
    not REGISTRY.exists() or not (KNOWLEDGE / "knowledge_assertions.jsonl").exists(),
    reason="the Atharvavedic anukramaṇī knowledge layer is not generated",
)

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)


# --------------------------------------------------------------------------- fixtures
@functools.cache
def _document() -> dict[str, Any]:
    return dict(yaml.safe_load(REGISTRY.read_text(encoding="utf-8")))


@functools.cache
def _entities() -> tuple[dict[str, Any], ...]:
    return tuple(_document()["entities"])


@functools.cache
def _labels() -> tuple[str, ...]:
    return tuple(str(entity["preferred_label"]) for entity in _entities())


@functools.cache
def _assertions() -> tuple[dict[str, Any], ...]:
    return tuple(
        json.loads(line)
        for line in (KNOWLEDGE / "knowledge_assertions.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    )


@functools.cache
def _ascriptions() -> tuple[dict[str, Any], ...]:
    return tuple(
        row for row in _assertions() if row["predicate"] == "HAS_DEVATA_ASCRIPTION"
    )


@functools.cache
def _builder() -> Any:
    """Import ``scripts/build_atharvaveda_anukramani.py`` by path.

    ``scripts/`` is not a package. The script rebinds ``sys.stdout`` at import time so that
    an IAST rejection reason cannot kill the build on a cp1252 console, and under pytest's
    capture that would detach the stream the capture plugin holds -- so a throwaway stdout
    is installed for the import and the real one put back, as
    ``tests/domain/test_v3_layers.py`` does.
    """
    path = PROJECT_ROOT / "scripts" / "build_atharvaveda_anukramani.py"
    spec = importlib.util.spec_from_file_location("_vedagraph_av_anukramani", path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    saved = sys.stdout
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    # Registered before execution because ``Bracket`` is a dataclass, and
    # ``dataclasses`` resolves its string annotations through ``sys.modules``.
    sys.modules[spec.name] = module
    try:
        with warnings.catch_warnings():
            spec.loader.exec_module(module)
    finally:
        sys.stdout = saved
    return module


# --------------------------------------------------------------------------- numerals
#: Sanskrit numeral morphemes, written out independently of the builder's lookup table so
#: that this test can disagree with the builder. Units, tens, the multiplicative and
#: subtractive joiners, and the count-word stems the Anukramaṇī uses (``-ṛca-`` "of N
#: verses", ``-ka-``). HOS orthography prints ``ç`` for ``ś`` and ``ṅ`` for the anusvāra in
#: ``viṅçati``, so both spellings are listed.
NUMERAL_MORPHEMES: frozenset[str] = frozenset(
    {
        "eka", "ekā", "ek", "dvi", "dvy", "dva", "dvā", "dve", "tri", "try", "tṛ",
        "traya", "trayo", "ādaça", "ādaśa",
        "catur", "catus", "catuç", "catvāri", "catasr", "pañca", "pan̄ca", "ṣaṣ", "ṣaṭ",
        "ṣaḍ", "ṣoḍa", "ṣoḍaça", "ṣoḍaśa",
        "sapta", "aṣṭa", "aṣṭā", "nava", "daça", "daśa", "viṅçati", "viṅça",
        "viṃśati", "triṅçat", "triṅça", "triṃśat", "catvāriṅçat", "pañcāçat", "pañcāça",
        "ṣaṣṭi", "saptati", "açīti", "aśīti", "navati", "çata", "śata", "sahasra",
        # joiners and count-word stems
        "adhika", "adhikā", "ūna", "ona", "vāi", "ca", "vihita", "vihitam", "ṛca", "rca",
        "ṛcam", "vacanāni", "sūktānām", "paryāya", "paryāyāḥ", "tri­guṇāni", "triguṇāni",
        "tathā", "param", "ham",
    }
)
#: Endings a printed count word takes. Stripped before morpheme decomposition.
COUNT_ENDINGS: tuple[str, ...] = (
    "ṛcam", "ṛca", "rcam", "kam", "ka", "am", "aḥ", "as", "āḥ", "ā", "aṁ", "a", "i", "ī",
    "s", "ḥ", "at", "ti", "m",
)
#: The tradition's own "having X as deity" suffixes. A value carrying one is an ascription
#: whatever numeral morpheme it also contains -- ``dvidevatyam`` is "two-deitied".
DEVATA_SUFFIX = re.compile(r"devat|d[āa]ivat|devy|d[āa]ivy")
#: A pāda reference: a bare or hyphenated run of verse-quarter letters.
PADA_REFERENCE = re.compile(r"^[a-h](?:\s*[-,]\s*[a-h])*$")


def _decomposes_into_numerals(word: str) -> bool:
    """True when ``word`` is built only from numeral morphemes and count endings."""
    for ending in ("", *COUNT_ENDINGS):
        stem = word[: len(word) - len(ending)] if ending else word
        if not stem:
            continue
        if _covered(stem):
            return True
    return False


def _covered(stem: str) -> bool:
    if not stem:
        return True
    return any(
        stem.startswith(morpheme) and _covered(stem[len(morpheme) :])
        for morpheme in NUMERAL_MORPHEMES
    )


#: The retroflex diacritics this scan mis-sets. Folded before the numeral test so that
#: `ṣaḑṛcam` -- `ṣaḍṛcam`, six -- cannot hide in the deity namespace behind a wrong
#: cedilla. Declared here rather than imported so the test can disagree with the builder.
LETTER_SHAPES = str.maketrans({"ḑ": "ḍ", "ṱ": "ṭ", "ș": "ṣ", "ț": "ṭ"})


def _is_numeral(value: str) -> bool:
    if DEVATA_SUFFIX.search(value):
        return False
    for candidate in (value, value.translate(LETTER_SHAPES)):
        words = [word for word in re.split(r"[\s,]+", candidate.strip(" .[]")) if word]
        if words and all(_decomposes_into_numerals(word) for word in words):
            return True
    return False


def test_the_numeral_detector_recognises_the_numerals_that_reached_the_graph() -> None:
    """The detector is checked before it is trusted, on the values the audit found.

    Without this, a numeral test that flags nothing proves nothing.
    """
    for numeral in (
        "ekonanavati",          # 89, stood on 90 AVS 18.4 passages
        "saptatis tryadhikā",   # 73, stood on 74 AVS 18.3 passages
        "catasraḥ",
        "catasras",
        "dve",
        "pan̄carcam",
        "ṣaḍṛcam",
        "ṣoḍaçarcam",
        "caturviṅçarcaṁ trayaṁ sūktānām",
        "dvyadhikaṁ vihitam",
        "tṛcam",
        "ekādaça",
        "ṣaṣṭiḥ",
        # The same numerals as the scan sets them, with the wrong retroflex diacritic.
        "ṣaḑṛcam",
        "ṣoḑaçarcam",
    ):
        assert _is_numeral(numeral), f"{numeral!r} should read as a numeral"
    for ascription in (
        "āgneyam",
        "mantroktadevatyam",
        "dvidevatyam",
        "ekavṛṣadevatyam",
        "trivṛddevatyam",
        "vānaspatyam",
        "sāumyam",
        "yamadevatyam mantroktabahudevatyaṁ ca",
    ):
        assert not _is_numeral(ascription), f"{ascription!r} is an ascription, not a numeral"


def test_no_ascription_value_is_a_sanskrit_numeral() -> None:
    offenders = sorted(value for value in _labels() if _is_numeral(value))
    assert offenders == [], (
        f"{len(offenders)} DevataAscription entities are printed verse counts, not "
        f"ascriptions: {offenders}"
    )


def test_no_ascription_assertion_names_a_numeral() -> None:
    """The registry and the assertions are checked separately, on purpose.

    A previous class of defect in this repository was a clean-looking registry beside
    assertions that disagreed with it, with only one of the two ever measured.
    """
    labels = {str(row["source_label"]) for row in _ascriptions()}
    offenders = sorted(label for label in labels if _is_numeral(label))
    assert offenders == [], f"HAS_DEVATA_ASCRIPTION edges carry numerals: {offenders}"


# --------------------------------------------------------------------------- pāda letters
def test_no_ascription_value_is_a_bare_pada_reference() -> None:
    offenders = sorted(value for value in _labels() if PADA_REFERENCE.match(value))
    assert offenders == [], (
        f"pāda references stand in the ascription namespace: {offenders}. `a-d` at "
        "AVS 19.38 addresses verse quarters a through d; it names no deity."
    )


def test_no_ascription_assertion_names_a_pada_reference() -> None:
    offenders = sorted(
        {
            str(row["source_label"])
            for row in _ascriptions()
            if PADA_REFERENCE.match(str(row["source_label"]).strip())
        }
    )
    assert offenders == [], f"HAS_DEVATA_ASCRIPTION edges carry pāda references: {offenders}"


# --------------------------------------------------------------------------- OCR siblings
#: Letter-shape confusions this scan actually makes, as (printed defect -> true reading).
#: Every one is evidenced in the pinned ``Page:`` snapshot: a broken final ``m`` set as
#: ``tn`` or ``vi``, ``f`` for ``p``, ``h`` for ``k``, ``t`` for ``n``, ``bh`` collapsed to
#: ``hh``, and the three ways the scan sets ``devatya``/``bahu``.
SCAN_CONFUSIONS: tuple[tuple[str, str], ...] = (
    ("tn", "m"),
    ("vi", "m"),
    ("f", "p"),
    ("h", "k"),
    ("t", "n"),
    ("g", "gn"),  # the `n` lost from the `gn` conjunct: `āindrāgam` for `āindrāgnam`
    ("uhh", "ubh"),
    ("dtvaty", "devaty"),
    ("drvaty", "devaty"),
    ("dcvaty", "devaty"),
    ("ddivat", "devat"),
    ("bahti", "bahu"),
    ("baku", "bahu"),
    ("bahu", "bahti"),
)


def _repairs(value: str) -> set[str]:
    """Every string reachable from ``value`` by applying one scan confusion once."""
    out: set[str] = set()
    for defect, reading in SCAN_CONFUSIONS:
        start = 0
        while (index := value.find(defect, start)) >= 0:
            out.add(value[:index] + reading + value[index + len(defect) :])
            start = index + 1
    out.discard(value)
    return out


def test_the_sibling_detector_recognises_the_split_the_audit_found() -> None:
    """Checked before trusted, on the three-way split of the AVS 18 ascription."""
    printed = "yamadevatyam mantroktabahudevatyaṁ ca"
    for variant in (
        "yamadevatyam mantroktabahtidevatyaṁ ca",
        "yamadevatyam mantroktabakudevatyaṁ ca",
    ):
        assert printed in _repairs(variant), f"{variant!r} should repair to {printed!r}"
    assert "mantroktadevatyam" in _repairs("mantroktadevatyatn")
    assert "vānaspatyam" in _repairs("vānasfatyam")


def test_no_two_ascriptions_are_scan_variants_of_one_another() -> None:
    """No value may be one scan confusion away from another value in the same namespace.

    This is the test the three-way ``bahu``/``bahti``/``baku`` split needed. It is a
    neighbour test rather than an edit-distance threshold on purpose: distance alone
    condemns legitimately distinct pairs -- ``vārṣabham`` (vṛṣabha) beside ``ārṣabham``
    (ṛṣabha), ``sārasvatam`` beside ``sārasvatyam``, ``devatyam`` beside ``dāivatam`` --
    and this codebase does not merge on a signal that is not identity.
    """
    known = set(_labels())
    collisions = sorted(
        (value, sorted(_repairs(value) & known))
        for value in known
        if _repairs(value) & known
    )
    assert collisions == [], (
        "these ascription entities are scan variants of one another and should be one "
        f"node with the variants in `source_variants`: {collisions}"
    )


def test_the_three_way_split_is_one_node_that_records_its_variants() -> None:
    printed = "yamadevatyam mantroktabahudevatyaṁ ca"
    matches = [entity for entity in _entities() if entity["preferred_label"] == printed]
    assert len(matches) == 1, f"{printed!r} should be exactly one entity"
    merged = sorted(matches[0]["ocr_variants_merged"])
    assert merged == [
        "yamadevatyam mantroktabahtidevatyaṁ ca",
        "yamadevatyam mantroktabakudevatyaṁ ca",
    ], merged
    # 136 + 90 + 61 passages were scattered across the three nodes.
    passages = [
        row for row in _ascriptions() if row["source_label"].startswith("yamadevatyam mantrokta")
    ]
    assert len({row["object_key"] for row in passages}) == 1, "still split across nodes"
    assert len(passages) == 287, len(passages)


def test_every_merged_variant_is_reachable_from_the_printed_label() -> None:
    """A merge must be justifiable as one scan confusion, not as a free-text correction."""
    for entity in _entities():
        printed = str(entity["preferred_label"])
        for variant in entity["ocr_variants_merged"]:
            assert printed in _repairs(str(variant)), (
                f"{variant!r} was merged onto {printed!r} but no recorded scan confusion "
                "connects them; that is an emendation, not a merge"
            )


# --------------------------------------------------------------------------- rejections
def test_the_registry_records_its_rejections_with_reasons() -> None:
    rejections = _document().get("rejections")
    assert rejections, "the registry must carry a `rejections` block"
    for row in rejections:
        assert set(row) == {"rejected_value", "reason", "printed_at", "occurrences"}, row
        assert row["reason"], row
        assert row["printed_at"], row


def test_the_values_the_audit_found_are_recorded_as_rejected() -> None:
    """A recorded rejection is what stops the value being re-added."""
    rejected = {str(row["rejected_value"]): str(row["reason"]) for row in _document()["rejections"]}
    assert rejected.get("ekonanavati", "") or _numeral_is_gated("ekonanavati")
    assert rejected.get("saptatis tryadhikā") == "head_token_is_verse_count"
    assert rejected.get("a-d") == "head_token_is_pada_reference"
    assert rejected.get("Atharvan") == "head_token_without_separator_not_a_devata"


def _numeral_is_gated(value: str) -> bool:
    """A numeral may be recorded as routed to the verse gate rather than as a rejection.

    ``ekonanavati`` = 89 equals our own independent mantra count for AVS 18.4, which is
    what proves it is a verse count and not a deity, so the builder spends it on the
    alignment gate. Either record satisfies "the rejection is on file".
    """
    for line in (CORPUS / "traditional_metadata_provenance.jsonl").read_text(
        encoding="utf-8"
    ).splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        for rejection in record.get("rejected_from_devata_slot") or []:
            if rejection["value"] == value:
                return True
    return False


def test_no_rejected_value_is_also_an_entity() -> None:
    rejected = {str(row["rejected_value"]) for row in _document()["rejections"]}
    assert rejected & set(_labels()) == set(), rejected & set(_labels())


def test_the_numerals_the_audit_found_are_gone_from_the_assertions() -> None:
    labels = {str(row["source_label"]) for row in _ascriptions()}
    for gone in ("ekonanavati", "saptatis tryadhikā", "a-d", "Atharvan", "dve", "catasraḥ"):
        assert gone not in labels, f"{gone!r} is still asserted as a deity ascription"


# --------------------------------------------------------------------------- closure
def test_every_ascription_assertion_lands_on_a_registry_entity() -> None:
    keys = {str(entity["entity_key"]) for entity in _entities()}
    orphans = sorted({str(row["object_key"]) for row in _ascriptions()} - keys)
    assert orphans == [], orphans


def test_the_namespace_is_not_the_rigvedic_deity_set() -> None:
    """The design decision this whole layer rests on, pinned so a merge cannot pass.

    ``āgneyam`` is "belonging to Agni", not "Agni". Unioning these with
    ``data/registry/devatas.yaml`` would add hundreds of adjectives to the deity census.
    """
    deities = yaml.safe_load(
        (PROJECT_ROOT / "data" / "registry" / "devatas.yaml").read_text(encoding="utf-8")
    )["entities"]
    deity_labels = {str(row["preferred_label"]) for row in deities}
    assert set(_labels()) & deity_labels == set()
    for entity in _entities():
        assert entity["entity_type"] == "DEVATA_ASCRIPTION"
        assert entity["is_ascription_descriptor"] is True
        assert str(entity["entity_key"]).startswith("VG:ASCRIPTION:AV:")


# --------------------------------------------------------------------------- the parser
def test_the_builder_refuses_the_apparatus_it_used_to_emit() -> None:
    """Pin the parse decision itself, so the fix cannot be undone upstream of the artifact."""
    builder = _builder()
    for token, reason in (
        ("ekonanavati", "head_token_is_verse_count"),
        ("saptatis tryadhikā", "head_token_is_verse_count"),
        ("catasraḥ", "head_token_is_verse_count"),
        ("dve", "head_token_is_verse_count"),
        ("caturviṅçarcaṁ trayaṁ sūktānām", "head_token_is_verse_count_note"),
        ("dvyadhikaṁ vihitam", "head_token_is_verse_count_note"),
        ("a-d", "head_token_is_pada_reference"),
        ("b-c", "head_token_is_pada_reference"),
        ("a", "head_token_is_pada_reference"),
        ("ānuṣṭuhham", "head_token_is_corrupt_metre"),
        ("ekāvasānam", "head_token_is_metrical_apparatus"),
        ("viparītapādalakṣmyā", "head_token_is_metrical_apparatus"),
    ):
        item = builder.Bracket(
            kanda=1, hymn=1, volume=1, page=1, bombay=None, raw="", terminator=""
        )
        assert builder.classify_head_part(item, token) is False, token
        assert item.rejected_from_devata_slot == [{"value": token, "reason": reason}], (
            token,
            item.rejected_from_devata_slot,
        )
    for ascription in ("āgneyam", "mantroktadevatyam", "vānaspatyam", "lākṣikam", "yājñikam"):
        item = builder.Bracket(
            kanda=1, hymn=1, volume=1, page=1, bombay=None, raw="", terminator=""
        )
        assert builder.classify_head_part(item, ascription) is True, ascription
        assert item.rejected_from_devata_slot == []


def test_the_scan_letter_shapes_are_folded_before_the_lexicons_see_them() -> None:
    """``ṣaḑṛcam`` is ``ṣaḍṛcam`` = 6, and ``ānuṣṱubham`` is a metre.

    Both reached the deity namespace only because a retroflex was printed with the wrong
    diacritic, so neither the numeral table nor the metre stems could match.
    """
    builder = _builder()
    assert builder.strip_markup("ṣaḑṛcam") == "ṣaḍṛcam"
    assert builder.strip_markup("ānuṣṱubham") == "ānuṣṭubham"
    assert builder.numeral("ṣaḍṛcam") == 6
    assert builder.numeral("pan̄carcam") == 5
    assert builder.METRE_STEM.search("ānuṣṭubham") is not None
    assert builder.METRE_STEM.search("āṣṭikam") is not None


# --------------------------------------------------------------------------- live graph
# --------------------------------------------------------------------------- chandas
# The same scan defects split the Chandas namespace, and there they were spotted by eye,
# which is the sampling failure mode this file exists to replace. These tests enumerate all
# 541 metre values. They are deliberately narrower than an edit-distance threshold: metre
# values differ *legitimately* by one character all the time -- `3-p.` versus `5-p.` is the
# whole content of the specification, and `ārcī` (of the ṛc) versus `ārṣī` (of the ṛṣi) are
# two different metres -- so only defect classes with no other reading are tested.


@functools.cache
def _chandas() -> tuple[dict[str, Any], ...]:
    doc = yaml.safe_load(CHANDAS_REGISTRY.read_text(encoding="utf-8"))
    return tuple(doc["entities"])


@functools.cache
def _chandas_labels() -> tuple[str, ...]:
    return tuple(str(entity["preferred_label"]) for entity in _chandas())


#: The avagraha -- the mark of an elided initial `a` -- is ONE printed glyph. Written as
#: escapes rather than literals so the intent survives a copy-paste and so the file needs
#: no ambiguous-character suppressions.
AVAGRAHA = "’"  # RIGHT SINGLE QUOTATION MARK, the form this corpus settles on  # noqa: RUF001
AVAGRAHA_CONFUSABLES = (
    "‘"  # LEFT SINGLE QUOTATION MARK  # noqa: RUF001
    "'"  # APOSTROPHE
    "ʼ"  # MODIFIER LETTER APOSTROPHE  # noqa: RUF001
    "′"  # PRIME  # noqa: RUF001
)
#: Diacritics the scan mis-sets: comma-below, cedilla and circumflex-below where the dot
#: belongs, a tilde where a macron belongs, and the cedilla shaken loose from its own `c`.
MIS_SET_DIACRITICS = (
    "ḑ"  # d WITH CEDILLA, for d WITH DOT BELOW
    "ṱ"  # t WITH CIRCUMFLEX BELOW, for t WITH DOT BELOW
    "ș"  # s WITH COMMA BELOW
    "ț"  # t WITH COMMA BELOW
    "ĩ"  # i WITH TILDE, for i WITH MACRON
    "ã"  # a WITH TILDE, for a WITH MACRON
    "¸"  # free-standing CEDILLA  # noqa: RUF001
)
FOOTNOTE_MARKERS = "*†‡"

#: Near-pairs in the Chandas namespace that are one diacritic apart and are NOT merged,
#: each with the reason. Listing them is the point: a *new* diacritic pair must fail this
#: test, and a refusal has to be on the record to stop someone merging it later.
CHANDAS_NEAR_PAIRS_NOT_MERGED: dict[frozenset[str], str] = {
    frozenset({"jagati", "jagatī"}): (
        "printed, not scanned: `jagati` stands in two independent brackets (iv. 30 and "
        "xiv. 1), and a spelling that recurs across brackets is the page's"
    ),
    frozenset({"parabṛhatī triṣṭubh", "parābṛhatī triṣṭubh"}): (
        "two decisions: `para-` and `parā-` are both real prefixes, so choosing one is a "
        "philological call and not a repair"
    ),
    frozenset({"purauṣṇih", "purāuṣṇih"}): (
        "two decisions: `purauṣṇih` is the guṇa of puro+uṣṇih and `purāuṣṇih` the vrddhi; "
        "both are formable, and neither is demonstrably the defect"
    ),
}


def _diacritic_neighbours(labels: tuple[str, ...]) -> list[tuple[str, str]]:
    """Pairs differing in exactly one character that shares its base letter."""
    out: list[tuple[str, str]] = []
    for index, first in enumerate(labels):
        for second in labels[index + 1 :]:
            if len(first) != len(second):
                continue
            diff = [i for i, (a, b) in enumerate(zip(first, second, strict=True)) if a != b]
            if len(diff) != 1:
                continue
            a, b = first[diff[0]], second[diff[0]]
            if unicodedata.normalize("NFD", a)[0] == unicodedata.normalize("NFD", b)[0]:
                out.append(tuple(sorted((first, second))))  # type: ignore[arg-type]
    return sorted(set(out))


def test_the_avagraha_is_one_codepoint_in_every_av_registry() -> None:
    """One printed glyph must not be three nodes.

    ``puro <avagraha>nuṣṭubh`` stood as three separate Chandas nodes -- one per codepoint,
    U+2019, U+2018 and U+0027 -- and ``bhurik prājāpatyā <avagraha>nuṣṭubh`` as two.
    Every occurrence in all three registries was inspected and none of them is a quotation
    mark, so this is decidable rather than a judgement.
    """
    for path in (CHANDAS_REGISTRY, REGISTRY, RISHI_REGISTRY):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        offenders = sorted(
            str(entity["preferred_label"])
            for entity in document["entities"]
            if set(str(entity["preferred_label"])) & set(AVAGRAHA_CONFUSABLES)
        )
        assert offenders == [], (path.name, offenders)


def test_no_av_registry_value_carries_a_mis_set_diacritic() -> None:
    for path in (CHANDAS_REGISTRY, REGISTRY, RISHI_REGISTRY):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        offenders = sorted(
            str(entity["preferred_label"])
            for entity in document["entities"]
            if set(str(entity["preferred_label"])) & set(MIS_SET_DIACRITICS)
        )
        assert offenders == [], (path.name, offenders)


def test_no_av_registry_value_carries_a_footnote_marker() -> None:
    """A footnote marker is never part of a name, and it split five values from their own
    clean siblings -- ``triṣṭubh*`` from ``triṣṭubh``, ``jagatī *`` from ``jagatī``."""
    for path in (CHANDAS_REGISTRY, REGISTRY, RISHI_REGISTRY):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        offenders = sorted(
            str(entity["preferred_label"])
            for entity in document["entities"]
            if set(str(entity["preferred_label"])) & set(FOOTNOTE_MARKERS)
        )
        assert offenders == [], (path.name, offenders)


def test_no_chandas_value_has_a_broken_bh_ligature() -> None:
    """``bhurik triṣṭubhh`` for ``bhurik triṣṭubh``.

    Narrow on purpose. A general doubled-letter rule would be a disaster here: 59 metre
    values carry a legitimate sandhi geminate -- ``kakummatī``, ``uṣṇiggarbhā``,
    ``triṣṭubbṛhatī``, ``nicṛjjagatī`` -- and folding those would destroy real metre names.
    """
    offenders = sorted(value for value in _chandas_labels() if "bhh" in value)
    assert offenders == [], offenders


def test_every_chandas_diacritic_near_pair_is_merged_or_refused_with_a_reason() -> None:
    unexplained = [
        pair
        for pair in _diacritic_neighbours(_chandas_labels())
        if frozenset(pair) not in CHANDAS_NEAR_PAIRS_NOT_MERGED
    ]
    assert unexplained == [], (
        "these metre values differ by one diacritic and are neither merged nor recorded as "
        f"a deliberate refusal: {unexplained}"
    )


def test_the_chandas_pairs_spotted_by_eye_are_now_single_nodes() -> None:
    """The two the coordinator found by inspection, plus the third the enumeration found."""
    labels = set(_chandas_labels())
    left, ascii_quote = AVAGRAHA_CONFUSABLES[0], AVAGRAHA_CONFUSABLES[1]
    for gone in (
        "bhurik triṣṭubhh",
        f"bhurik prājāpatyā {left}nuṣṭubh",
        f"puro {left}nuṣṭubh",
        f"puro {ascii_quote}nuṣṭubh",
        f"puro- {left}nuṣṭubh",
    ):
        assert gone not in labels, f"{gone!r} is still its own Chandas node"
    assert "bhurik triṣṭubh" in labels
    assert f"puro {AVAGRAHA}nuṣṭubh" in labels
    assert f"bhurik prājāpatyā {AVAGRAHA}nuṣṭubh" in labels


def test_every_merged_chandas_variant_is_one_mechanical_change_from_its_target() -> None:
    """A merge must be a repair, not an emendation: at most one edit, and never two."""
    for entity in _chandas():
        printed = str(entity["preferred_label"])
        for variant in entity.get("ocr_variants_merged") or []:
            ops = [
                op
                for op in difflib.SequenceMatcher(None, str(variant), printed).get_opcodes()
                if op[0] != "equal"
            ]
            assert len(ops) == 1, (variant, printed, ops)
            _tag, i1, i2, j1, j2 = ops[0]
            assert max(i2 - i1, j2 - j1) == 1, (variant, printed, ops)


def test_the_refused_chandas_near_pairs_are_still_both_present() -> None:
    """A refusal has to be observable. If one side vanished, the reason went stale."""
    labels = set(_chandas_labels())
    for pair, reason in CHANDAS_NEAR_PAIRS_NOT_MERGED.items():
        assert pair <= labels, (pair, reason)
        assert reason


@pytest.mark.live
@_LIVE
def test_live_no_devata_ascription_node_is_apparatus() -> None:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    try:
        with driver.session() as session:
            values = [
                str(record["v"])
                for record in session.run(
                    "MATCH (a:DevataAscription) "
                    "RETURN coalesce(a.preferred_label, a.label, a.name) AS v"
                )
                if record["v"] is not None
            ]
    finally:
        driver.close()
    if not values:
        pytest.skip("no :DevataAscription nodes are projected")
    assert sorted(value for value in values if _is_numeral(value)) == []
    assert sorted(value for value in values if PADA_REFERENCE.match(value)) == []
    known = set(_labels())
    assert sorted(set(values) - known) == [], "the graph holds values the registry does not"
