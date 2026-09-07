"""Cross-Veda QA gate regression tests (Agent F).

Two jobs:

1. Pin identity. The namespace UUID and a handful of known canonical_key -> UUID mappings
   are asserted literally, so any future change to ``identity.py`` or the URN scheme that
   would move an entity's identity fails here loudly instead of silently reissuing 10,552
   Rigveda UUIDs.
2. Pin work-agnosticism. ``validate_corpus`` used to hardcode the Rigveda's three-level
   Mandala/Sukta/Mantra shape. A two-level work raised ``KeyError: 'mandala'`` outright and
   a two-level work's mantras were all reported as wrongly parented. Both are asserted
   fixed here, against synthetic corpora that need no build artifacts on disk.
"""

from __future__ import annotations

import pathlib
import unicodedata
from uuid import UUID, uuid5

import pytest

from vedagraph.config.registry import load_sources, load_text_versions
from vedagraph.identity import (
    VEDAGRAPH_NAMESPACE_UUID,
    avs_mantra_identity,
    rv_mandala_identity,
    rv_mantra_identity,
    rv_sukta_identity,
    uuid_for_urn,
    vsm_mantra_identity,
)
from vedagraph.models import (
    Passage,
    Source,
    SourceArtifact,
    SourceAssertion,
    TextVersion,
    Work,
)
from vedagraph.models.enums import EntityType, QASeverity
from vedagraph.normalize import (
    ComparisonForm,
    comparison_form,
    has_vedic_accents,
    normalize_nfc,
    strip_vedic_accents,
)
from vedagraph.qa import CorpusRecords, validate_corpus
from vedagraph.qa.checks import (
    declared_levels,
    verify_content_addressed_snapshots,
    verify_registry_checksums,
    verify_snapshot_namespaces,
    verify_text_version_registration,
)

# --------------------------------------------------------------------------------------
# 1. Identity is frozen
# --------------------------------------------------------------------------------------

#: Changing this value would reissue every entity UUID in the corpus. It is a protocol
#: constant, not a tunable.
PINNED_NAMESPACE = "7c8cde94-2bc0-50e2-8819-568ae65a3ec4"

#: Known-good triples read out of the committed data/canonical/rigveda_full_v1 release.
#: These are the actual stored values, not recomputations, so this pins the identity of the
#: shipped corpus rather than merely asserting that the code agrees with itself.
PINNED_RV_IDENTITY = [
    (
        rv_mandala_identity,
        (1,),
        "VG:RV:SAK:M01",
        "urn:vedagraph:section:rigveda:shakala:mandala:1",
        "a82305ce-7bb9-58f1-8ee9-aebeec8d61e6",
    ),
    (
        rv_sukta_identity,
        (1, 1),
        "VG:RV:SAK:M01:S001",
        "urn:vedagraph:hymn:rigveda:shakala:mandala:1:sukta:1",
        "3fa0cb27-3fa8-522f-879b-35f23a196f10",
    ),
    (
        rv_mantra_identity,
        (1, 1, 1),
        "VG:RV:SAK:M01:S001:V001",
        "urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1",
        "141a362f-1690-5244-831d-e0304db2fdc8",
    ),
    (
        rv_mantra_identity,
        (10, 191, 4),
        "VG:RV:SAK:M10:S191:V004",
        "urn:vedagraph:mantra:rigveda:shakala:mandala:10:sukta:191:mantra:4",
        "d2c4af74-048b-5764-8f49-dccb792e4678",
    ),
]


def test_namespace_uuid_is_permanent() -> None:
    assert str(VEDAGRAPH_NAMESPACE_UUID) == PINNED_NAMESPACE


def test_uuid_for_urn_is_plain_uuid5_over_the_namespace() -> None:
    """No salting, no versioning, no normalization of the URN before hashing."""
    urn = "urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1"
    assert uuid_for_urn(urn) == uuid5(UUID(PINNED_NAMESPACE), urn)


def test_uuid_for_urn_refuses_a_foreign_namespace() -> None:
    with pytest.raises(ValueError, match="urn:vedagraph:"):
        uuid_for_urn("urn:example:mantra:1")


@pytest.mark.parametrize(("builder", "args", "key", "urn", "entity_id"), PINNED_RV_IDENTITY)
def test_pinned_rigveda_identity_never_moves(
    builder, args: tuple[int, ...], key: str, urn: str, entity_id: str
) -> None:
    built_key, built_urn, built_uuid = builder(*args)
    assert built_key == key
    assert built_urn == urn
    assert str(built_uuid) == entity_id
    # and the UUID must still be derivable from the URN alone
    assert str(uuid_for_urn(urn)) == entity_id


def test_every_level_of_the_rigveda_round_trips_key_urn_and_uuid() -> None:
    for identity in (
        rv_mandala_identity(10),
        rv_sukta_identity(10, 191),
        rv_mantra_identity(10, 191, 4),
    ):
        key, urn, entity_id = identity
        assert key.startswith("VG:RV:SAK:")
        assert urn.startswith("urn:vedagraph:")
        assert uuid_for_urn(urn) == entity_id


def test_the_four_vedas_do_not_collide_in_key_or_uuid_space() -> None:
    identities = [
        rv_mantra_identity(1, 1, 1),
        vsm_mantra_identity(1, 1),
        avs_mantra_identity(1, 1, 1),
    ]
    assert len({key for key, _, _ in identities}) == 3
    assert len({urn for _, urn, _ in identities}) == 3
    assert len({entity_id for _, _, entity_id in identities}) == 3


# --------------------------------------------------------------------------------------
# 2. The QA gate is work-agnostic
# --------------------------------------------------------------------------------------

RV_WORK = Work(
    work_id="VG:WORK:RV:SAK",
    abbreviation="RV",
    veda="Rigveda",
    work_name="Rigveda Samhita",
    recension="Shakala",
    hierarchy=["Mandala", "Sukta", "Mantra"],
    citation_pattern="RV {mandala}.{sukta}.{mantra}",
)
VSM_WORK = Work(
    work_id="VG:WORK:YV:VSM",
    abbreviation="VSM",
    veda="Shukla Yajurveda",
    work_name="Vajasaneyi Samhita",
    recension="Madhyandina",
    hierarchy=["Adhyaya", "Mantra"],
    citation_pattern="VSM {adhyaya}.{mantra}",
)
SV_WORK = Work(
    work_id="VG:WORK:SV:KAU",
    abbreviation="SV",
    veda="Samaveda",
    work_name="Samaveda Samhita",
    recension="Kauthuma",
    hierarchy=["Collection", "Prapathaka", "Ardha", "Dasati", "Verse"],
    citation_pattern="edition-specific",
)


def _records(passages: list[Passage]) -> CorpusRecords:
    return CorpusRecords(
        passages=passages,
        texts=[],
        translations=[],
        metadata=[],
        sources=[],
        citations=[],
        audio_recordings=[],
        audio_segments=[],
        source_assertions=[],
    )


def _passage(
    key: str,
    urn: str,
    entity_type: EntityType,
    work_id: str,
    hierarchy: dict[str, int | str],
    citation: str,
    parent_key: str | None,
    sequence: int,
) -> Passage:
    return Passage(
        entity_id=uuid_for_urn(urn),
        canonical_key=key,
        canonical_urn=urn,
        entity_type=entity_type,
        work_id=work_id,
        hierarchy=hierarchy,
        canonical_citation=citation,
        parent_key=parent_key,
        sequence_in_parent=sequence,
    )


def _vsm_corpus() -> list[Passage]:
    """A minimal, valid two-level Vajasaneyi Samhita corpus."""
    adhyaya_urn = "urn:vedagraph:section:yajurveda:vajasaneyi-madhyandina:adhyaya:1"
    passages = [
        _passage(
            "VG:YV:VSM:A01",
            adhyaya_urn,
            EntityType.SECTION,
            "VG:WORK:YV:VSM",
            {"adhyaya": 1},
            "VSM 1",
            None,
            1,
        )
    ]
    for mantra in (1, 2, 3):
        key, urn, _ = vsm_mantra_identity(1, mantra)
        passages.append(
            _passage(
                key,
                urn,
                EntityType.MANTRA,
                "VG:WORK:YV:VSM",
                {"adhyaya": 1, "mantra": mantra},
                f"VSM 1.{mantra}",
                "VG:YV:VSM:A01",
                mantra,
            )
        )
    return passages


def test_validate_corpus_does_not_crash_on_a_two_level_work() -> None:
    """Regression: this raised ``KeyError: 'mandala'`` and never reached a QA verdict.

    The mantra-count reconciliation loop indexed ``hierarchy["mandala"]`` for every MANTRA
    without checking that the key existed, so the whole gate was unrunnable for any work
    that is not the Rigveda.
    """
    issues = validate_corpus(_records(_vsm_corpus()), works=[RV_WORK, VSM_WORK])
    assert [issue for issue in issues if issue.check_id == "stable_uuid_deterministic"] == []


def test_a_two_level_work_reports_no_structural_error() -> None:
    """Regression: every VSM mantra was reported as needing a Sukta/HYMN parent."""
    issues = validate_corpus(_records(_vsm_corpus()), works=[RV_WORK, VSM_WORK])
    structural = [
        issue
        for issue in issues
        if issue.check_id in {"valid_parents", "declared_work_hierarchy", "valid_hierarchy"}
        and issue.severity == QASeverity.ERROR
    ]
    assert structural == [], [issue.message for issue in structural]


def test_a_mantra_parented_to_the_wrong_depth_is_still_caught() -> None:
    """The relaxed rule must not become a rule that accepts anything."""
    passages = _vsm_corpus()
    key, urn, _ = vsm_mantra_identity(2, 1)
    passages.append(
        _passage(
            key,
            urn,
            EntityType.MANTRA,
            "VG:WORK:YV:VSM",
            {"adhyaya": 2, "mantra": 1},
            "VSM 2.1",
            "VG:YV:VSM:A01",  # wrong adhyaya: hierarchy prefix does not match
            1,
        )
    )
    issues = validate_corpus(_records(passages), works=[RV_WORK, VSM_WORK])
    assert [issue for issue in issues if issue.check_id == "valid_parents"]


def test_a_top_level_passage_declaring_a_parent_is_caught() -> None:
    passages = _vsm_corpus()
    passages[0] = passages[0].model_copy(update={"parent_key": "VG:WORK:YV:VSM"})
    issues = validate_corpus(_records(passages), works=[RV_WORK, VSM_WORK])
    assert [issue for issue in issues if issue.check_id == "valid_parents"]


def test_hierarchy_keys_must_be_the_declared_levels_of_the_work() -> None:
    """A work drifting from its registry-declared hierarchy must fail loudly."""
    key, urn, _ = vsm_mantra_identity(1, 9)
    rogue = _passage(
        key,
        urn,
        EntityType.MANTRA,
        "VG:WORK:YV:VSM",
        {"mandala": 1, "sukta": 1, "mantra": 9},  # Rigveda-shaped keys on a VSM passage
        "VSM 1.9",
        "VG:YV:VSM:A01",
        9,
    )
    issues = validate_corpus(_records([*_vsm_corpus(), rogue]), works=[RV_WORK, VSM_WORK])
    assert [issue for issue in issues if issue.check_id == "declared_work_hierarchy"]


def test_a_level_a_division_does_not_have_is_omitted_and_accepted() -> None:
    """The successor to a test that asserted the opposite, and the inversion is the point.

    This used to be ``test_a_zero_hierarchy_level_is_reported_as_absent_not_rejected``,
    on the premise that "Samaveda encodes a level that does not exist in a division as a
    literal 0" and that rejecting it would invalidate 65 real verses. That encoding is
    gone: it made the rejected edition's flattening choice part of every Samaveda passage,
    and it made "the text has no ardha here" indistinguishable from "the edition declined
    to number it". A level a division does not have is now OMITTED, so a passage's
    hierarchy is an outermost-anchored SUBSEQUENCE of the work's declared levels rather
    than a prefix of them.

    The Mahanamnya collection is the extreme case: its verses carry only
    ``{collection, verse}`` against five declared levels, and hang directly off the
    collection container with three declared levels skipped.
    """
    container_urn = "urn:vedagraph:section:samaveda:kauthuma:mahanamnya"
    verse_urn = "urn:vedagraph:mantra:samaveda:kauthuma:mahanamnya:verse:1"
    passages = [
        _passage(
            "VG:SV:KAU:MAHANAMNYA",
            container_urn,
            EntityType.STRUCTURAL_CONTAINER,
            "VG:WORK:SV:KAU",
            {"collection": "MAHANAMNYA"},
            "SV MAHANAMNYA",
            None,
            1,
        ),
        _passage(
            "VG:SV:KAU:MAHANAMNYA:V01",
            verse_urn,
            EntityType.MANTRA,
            "VG:WORK:SV:KAU",
            {"collection": "MAHANAMNYA", "verse": 1},
            "SV MAHANAMNYA 1",
            "VG:SV:KAU:MAHANAMNYA",  # three declared levels skipped, none of them present
            1,
        ),
    ]
    issues = validate_corpus(_records(passages), works=[SV_WORK])
    # Structural checks only: this corpus carries no text, so non_empty_sanskrit fires and
    # is correct to fire.
    structural = [
        issue
        for issue in issues
        if issue.severity == QASeverity.ERROR
        and issue.check_id in {"valid_hierarchy", "valid_parents", "declared_work_hierarchy"}
    ]
    assert structural == [], [issue.message for issue in structural]


def test_a_zero_or_negative_hierarchy_level_is_an_error() -> None:
    """Zero is now as invalid as a negative, and for the same reason.

    A level a division does not have must be omitted. Tolerating 0 would leave the
    superseded flattened address representable.
    """
    for bad_value in (0, -1):
        passages = [
            _passage(
                "VG:SV:KAU:UTTARA",
                "urn:vedagraph:section:samaveda:kauthuma:uttara",
                EntityType.STRUCTURAL_CONTAINER,
                "VG:WORK:SV:KAU",
                {"collection": "UTTARA"},
                "SV UTTARA",
                None,
                1,
            ),
            _passage(
                "VG:SV:KAU:UTTARA:P01:R01:D01:V02",
                "urn:vedagraph:mantra:samaveda:kauthuma:uttara"
                ":prapathaka:1:ardha:1:dasati:1:verse:2",
                EntityType.MANTRA,
                "VG:WORK:SV:KAU",
                {
                    "collection": "UTTARA",
                    "prapathaka": bad_value,
                    "ardha": 1,
                    "dasati": 1,
                    "verse": 2,
                },
                "SV UTTARA 1.1.1.2",
                "VG:SV:KAU:UTTARA",
                2,
            ),
        ]
        issues = validate_corpus(_records(passages), works=[SV_WORK])
        assert [
            issue
            for issue in issues
            if issue.check_id == "valid_hierarchy" and issue.severity == QASeverity.ERROR
        ], f"value {bad_value} must be an ERROR"


def test_a_forged_entity_id_is_caught_by_the_uuid_check() -> None:
    """``stable_uuid_deterministic`` did not exist before; identity drift was invisible."""
    passages = _vsm_corpus()
    passages[1] = passages[1].model_copy(update={"entity_id": uuid_for_urn("urn:vedagraph:x")})
    issues = validate_corpus(_records(passages), works=[RV_WORK, VSM_WORK])
    assert [issue for issue in issues if issue.check_id == "stable_uuid_deterministic"]


def test_declared_levels_lowercases_the_registry_hierarchy() -> None:
    assert declared_levels([VSM_WORK]) == {"VG:WORK:YV:VSM": ["adhyaya", "mantra"]}


def test_an_undeclared_work_is_reported_rather_than_skipped_silently() -> None:
    issues = validate_corpus(_records(_vsm_corpus()), works=[RV_WORK])
    assert [
        issue
        for issue in issues
        if issue.check_id == "declared_work_hierarchy" and issue.severity == QASeverity.WARNING
    ]


# --------------------------------------------------------------------------------------
# 3. Normalization invariants that the four-Veda sources actually depend on
# --------------------------------------------------------------------------------------

UDATTA = "॑"
ANUDATTA = "॒"
VEDIC_ANUSVARA_BAHIRGOMUKHA = "ᳪ"  # category Lo: a letter, not a tone mark
VEDIC_TIRYAK = "᳭"  # category Mn: a combining tone mark


def test_nfc_is_idempotent_and_never_mutates_the_caller_s_string() -> None:
    for text in ("अग्निम" + UDATTA, "agniḿ", "kl̥pta"):
        once = normalize_nfc(text)
        assert normalize_nfc(once) == once
        assert unicodedata.is_normalized("NFC", once)


def test_stripping_accents_removes_tone_marks_and_keeps_every_letter() -> None:
    accented = "म" + UDATTA
    assert has_vedic_accents(accented)
    assert strip_vedic_accents(accented) == "म"


def test_a_vedic_extension_letter_survives_accent_stripping() -> None:
    """U+1CEA is a letter (Lo). Removing it would delete text, not an accent."""
    assert unicodedata.category(VEDIC_ANUSVARA_BAHIRGOMUKHA) == "Lo"
    assert VEDIC_ANUSVARA_BAHIRGOMUKHA in strip_vedic_accents("म" + VEDIC_ANUSVARA_BAHIRGOMUKHA)


def test_a_vedic_extension_combining_mark_is_stripped() -> None:
    assert unicodedata.category(VEDIC_TIRYAK) == "Mn"
    assert VEDIC_TIRYAK not in strip_vedic_accents("म" + VEDIC_TIRYAK)


def test_transliterated_udatta_is_recognised_as_an_accent() -> None:
    """Regression: indic-transliteration renders udatta as U+032D.

    While U+032D was missing from the tone-mark set, ``has_vedic_accents`` returned False
    for udatta-accented transliterated text -- denying an accent that was present -- and an
    accented and an unaccented reading compared equal in Devanagari but unequal once
    transliterated.
    """
    pytest.importorskip("indic_transliteration")
    from vedagraph.transliteration.indic import DevanagariToIAST

    translit = DevanagariToIAST()
    accented = translit.transliterate("अग्निम" + UDATTA)
    plain = translit.transliterate("अग्निम")
    assert has_vedic_accents(accented)
    form = ComparisonForm.ACCENT_STRIPPED_COMPARISON
    assert comparison_form(accented, form) == comparison_form(plain, form)


def test_transliterated_anudatta_is_recognised_as_an_accent() -> None:
    pytest.importorskip("indic_transliteration")
    from vedagraph.transliteration.indic import DevanagariToIAST

    translit = DevanagariToIAST()
    accented = translit.transliterate("अग्निम" + ANUDATTA)
    assert has_vedic_accents(accented)


def test_the_search_surface_is_idempotent_for_uppercase_input() -> None:
    """Regression: folding ran before casefolding, so an upper-case transcription variant
    folded only on a second pass, making the surface non-idempotent."""
    form = ComparisonForm.SEARCH_NORMALIZED
    for text in ("R̥", "R̥̄", "ṚTA", "r̥"):
        once = comparison_form(text, form)
        assert comparison_form(once, form) == once, text


def test_case_variants_of_one_sound_agree_on_the_search_surface() -> None:
    form = ComparisonForm.SEARCH_NORMALIZED
    assert comparison_form("R̥", form) == comparison_form("r̥", form)


def test_source_original_is_never_replaced_by_a_derived_form() -> None:
    """``SOURCE_ORIGINAL`` must be the identity function; every other form is derived."""
    for text in ("म" + UDATTA, "  spaced  ||", "kl̥pta"):
        assert comparison_form(text, ComparisonForm.SOURCE_ORIGINAL) == text


# --------------------------------------------------------------------------------------
# 4. Devanagari folding (the three new Vedas are Devanagari-primary)
# --------------------------------------------------------------------------------------

A8F3 = "ꣳ"  # DEVANAGARI SIGN CANDRABINDU VIRAMA: one spelling of the anusvara
CEA = "ᳪ"  # VEDIC SIGN ANUSVARA BAHIRGOMUKHA
CED = "᳭"  # VEDIC SIGN TIRYAK
ANUSVARA_SIGN = "ं"
VISARGA = "ः"  # noqa: RUF001
KA = "क"


def test_the_two_devanagari_anusvara_spellings_fold_together() -> None:
    """Regression: the fold table had no Devanagari rules at all.

    The two Vajasaneyi layers spell one nasal incompatibly -- U+A8F3 in the unaccented layer,
    U+1CEA+U+0902+U+1CED in the accented one -- so 132 of 135 cross-layer comparisons came
    back UNCLASSIFIED for a purely mechanical reason.
    """
    form = ComparisonForm.SEARCH_NORMALIZED
    assert comparison_form(KA + A8F3, form) == comparison_form(KA + CEA + ANUSVARA_SIGN + CED, form)


def test_the_accent_stripped_anusvara_arrival_form_also_folds() -> None:
    """U+1CED is combining and is stripped first, so U+1CEA+U+0902 must fold too."""
    form = ComparisonForm.SEARCH_NORMALIZED
    assert comparison_form(KA + A8F3, form) == comparison_form(KA + CEA + ANUSVARA_SIGN, form)


def test_ascii_colon_stands_in_for_visarga_only_in_devanagari() -> None:
    """A source convention, not a typo: the accented VSM layer types visarga as ':'.

    It must fold in Devanagari and must NOT fold in Latin, where a colon is punctuation.
    """
    form = ComparisonForm.SEARCH_NORMALIZED
    assert comparison_form(KA + ":", form) == comparison_form(KA + VISARGA, form)
    # Latin text keeps the old behaviour: the colon is editorial and becomes a space.
    assert comparison_form("a: b", form) == "a b"


def test_the_devanagari_convention_fold_never_touches_stored_surfaces() -> None:
    """`text_original` must be recoverable; only derived surfaces may be rewritten."""
    text = KA + ":"
    assert comparison_form(text, ComparisonForm.SOURCE_ORIGINAL) == text
    assert comparison_form(text, ComparisonForm.NFC) == text


def test_devanagari_folding_leaves_latin_corpora_alone() -> None:
    """Rigveda, Samaveda and Atharvaveda carry no Devanagari, so this must be a no-op."""
    from vedagraph.normalize.unicode import fold_devanagari_source_conventions

    for latin in ("agnim īḷe puróhitaṃ", "a:b:c", "kl̥pta"):
        assert fold_devanagari_source_conventions(latin) == latin


# --------------------------------------------------------------------------------------
# 5. G11 / G12: provenance checks that the structural gates are blind to
# --------------------------------------------------------------------------------------

RIGHTS = "REFERENCE_ONLY"
SHA_A = "a" * 64
SHA_B = "b" * 64


def _artifact(artifact_id: str, checksum: str | None) -> SourceArtifact:
    return SourceArtifact(
        artifact_id=artifact_id,
        source_id="GRETIL",
        url="https://example.org/x.htm",
        format="html",
        filename="x.htm",
        checksum_sha256=checksum,
        rights_status=RIGHTS,
    )


def test_an_unregistered_artifact_is_an_error() -> None:
    """A release asserting provenance under an id the rights authority never declared.

    Found in the real Yajurveda pilot, which passed all seven structural gates and
    validate_corpus with 0 issues while claiming two unregistered artifact ids.
    """
    issues = verify_registry_checksums([_artifact("X.NOT.REGISTERED", SHA_A)], [])
    assert [i for i in issues if i.check_id == "registry_artifact_declared"]
    assert all(i.severity == QASeverity.ERROR for i in issues)


def test_a_registry_checksum_disagreement_is_an_error() -> None:
    issues = verify_registry_checksums([_artifact("A.B.C", SHA_A)], [_artifact("A.B.C", SHA_B)])
    found = [i for i in issues if i.check_id == "registry_checksum_agreement"]
    assert found and found[0].severity == QASeverity.ERROR


def test_agreeing_checksums_produce_no_issue() -> None:
    assert verify_registry_checksums([_artifact("A.B.C", SHA_A)], [_artifact("A.B.C", SHA_A)]) == []


def test_a_checksum_absent_on_both_sides_is_reported_not_waived() -> None:
    issues = verify_registry_checksums([_artifact("A.B.C", None)], [_artifact("A.B.C", None)])
    assert issues and issues[0].severity == QASeverity.WARNING


def test_a_one_sided_checksum_cannot_pass_silently() -> None:
    """The branch that would otherwise skip: exactly one side states a checksum."""
    for release, registry in ((SHA_A, None), (None, SHA_A)):
        issues = verify_registry_checksums(
            [_artifact("A.B.C", release)], [_artifact("A.B.C", registry)]
        )
        assert issues, (release, registry)
        assert issues[0].severity == QASeverity.WARNING


def test_content_addressed_snapshot_corruption_is_caught(tmp_path) -> None:
    import hashlib

    good = tmp_path / (hashlib.sha256(b"ok").hexdigest() + ".htm")
    good.write_bytes(b"ok")
    bad = tmp_path / ("c" * 64 + ".htm")
    bad.write_bytes(b"tampered")
    unrelated = tmp_path / "notes.txt"
    unrelated.write_bytes(b"skipped, not guessed about")

    issues = verify_content_addressed_snapshots(tmp_path)
    assert len(issues) == 1
    assert issues[0].check_id == "content_addressed_snapshot_intact"
    assert bad.name in issues[0].entity_id


def _namespace_assertion(target: str | None) -> SourceAssertion:
    value: dict[str, object] = {"raw_directory": "data/raw/gretil_avs/"}
    if target is not None:
        value["registered_source_id"] = target
    return SourceAssertion(
        assertion_id=uuid_for_urn("urn:vedagraph:assertion:ns-test:" + str(target)),
        subject_id="GRETIL_AVS",
        predicate="SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE",
        value=value,
        source_id="GRETIL",
        source_locator="test",
    )


def _registered(source_id: str) -> list[Source]:
    """Use the real registry rather than fabricating a Source.

    `verify_snapshot_namespaces` only reads `source_id`, and a hand-built Source would need
    a full RightsInfo that this test has no opinion about. Selecting a genuinely registered
    source keeps the test honest and fails loudly if the id ever disappears.
    """
    sources = [source for source in load_sources() if source.source_id == source_id]
    assert sources, f"{source_id} is not in data/registry/sources.yaml"
    return sources


def test_a_storage_namespace_resolving_to_a_declared_source_passes() -> None:
    """`data/raw/gretil_avs/` with snapshot prefix GRETIL_AVS is storage layout, not a
    rights claim, so bare equality against the record's GRETIL would wrongly fail."""
    assert verify_snapshot_namespaces([_namespace_assertion("GRETIL")], _registered("GRETIL")) == []


def test_a_namespace_resolving_to_an_undeclared_source_is_an_error() -> None:
    issues = verify_snapshot_namespaces([_namespace_assertion("GRETIL")], _registered("VEDAWEB"))
    assert issues and issues[0].severity == QASeverity.ERROR


def test_a_namespace_with_no_declared_target_is_an_error() -> None:
    issues = verify_snapshot_namespaces([_namespace_assertion(None)], _registered("GRETIL"))
    assert issues and issues[0].severity == QASeverity.ERROR


# --------------------------------------------------------------------------------------
# 6. G11b / G13 / G14: provenance checks added from peer review
# --------------------------------------------------------------------------------------


def test_a_wiki_page_and_its_api_url_are_the_same_scope() -> None:
    """A human wiki URL and its api.php equivalent name one page and must not mismatch."""
    from vedagraph.qa.checks import _wiki_page_identity

    human = "https://en.wikisource.org/wiki/The_Hymns_of_the_Samaveda"
    api = (
        "https://en.wikisource.org/w/api.php?action=parse"
        "&page=The%20Hymns%20of%20the%20Samaveda&prop=wikitext&format=json"
    )
    assert _wiki_page_identity(human) == _wiki_page_identity(api)
    assert _wiki_page_identity(human) == "The Hymns of the Samaveda"


def test_a_different_wiki_page_is_a_different_scope() -> None:
    """The real defect: a checksum pinned to the work's preface instead of its text."""
    from vedagraph.qa.checks import _wiki_page_identity

    text = "https://sa.wikisource.org/wiki/%E0%A4%B6%E0%A5%81%E0%A4%95%E0%A5%8D%E0%A4%B2"
    preface = (
        "https://sa.wikisource.org/w/api.php?action=query&titles="
        "%E0%A4%B6%E0%A5%81%E0%A4%95%E0%A5%8D%E0%A4%B2%2F%E0%A4%AA%E0%A5%8D%E0%A4%B0"
    )
    assert _wiki_page_identity(text) != _wiki_page_identity(preface)


def test_a_non_wiki_url_is_not_guessed_about() -> None:
    from vedagraph.qa.checks import _wiki_page_identity

    assert _wiki_page_identity("https://gretil.sub.uni-goettingen.de/x/avs_acu.htm") is None


def test_an_unregistered_text_version_id_is_an_error() -> None:
    """Rights attach to the version descriptor, so an undeclared id is unadjudicated rights.

    Found by Agent C. Measured across the real releases: 6 unregistered ids spanning all
    three new-Veda pilots, because data/registry/text_versions.yaml declares 7 descriptors
    and all 7 are Rigvedic.
    """
    text = TextVersion(
        text_id=uuid_for_urn("urn:vedagraph:text:tv-test:1"),
        passage_id=uuid_for_urn("urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1"),
        language="sa",
        script="Latn",
        text_form="SAMHITA",
        text_version_id="NOT.REGISTERED.ANYWHERE",
        text_original="agnim",
        text_nfc="agnim",
        accented=False,
        source_id="GRETIL",
        source_locator="x",
        content_sha256="a" * 64,
        rights_status="REFERENCE_ONLY",
    )
    issues = verify_text_version_registration([text], [])
    assert issues and issues[0].check_id == "text_version_registered"
    assert issues[0].severity == QASeverity.ERROR
    assert issues[0].details["record_count"] == 1


def test_a_text_record_without_a_version_id_is_skipped_not_guessed() -> None:
    """Not every text is a distinguishable version; inventing an id would be the same
    mistake in the opposite direction."""
    text = TextVersion(
        text_id=uuid_for_urn("urn:vedagraph:text:tv-test:2"),
        passage_id=uuid_for_urn("urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:2"),
        language="sa",
        script="Latn",
        text_form="SAMHITA",
        text_original="agnim",
        text_nfc="agnim",
        accented=False,
        source_id="GRETIL",
        source_locator="x",
        content_sha256="a" * 64,
        rights_status="REFERENCE_ONLY",
    )
    assert verify_text_version_registration([text], []) == []


def test_a_manifest_naming_absent_snapshots_is_an_error(tmp_path) -> None:
    """A manifest naming bytes that are not there is an unverifiable provenance claim."""
    from vedagraph.qa.checks import verify_manifest_snapshots

    manifest = {"source_snapshot_ids": ["GRETIL:" + "d" * 64]}
    issues = verify_manifest_snapshots(manifest, tmp_path)
    assert issues and issues[0].severity == QASeverity.ERROR


def test_a_manifest_under_reporting_its_snapshots_is_reported(tmp_path) -> None:
    """Agent D's failure class: a build listed 2 of the 25 snapshots it read and every
    gate passed, because nothing compared the manifest against the tree."""
    import hashlib

    from vedagraph.qa.checks import verify_manifest_snapshots

    directory = tmp_path / "gretil"
    directory.mkdir()
    digests = []
    for payload in (b"one", b"two", b"three"):
        digest = hashlib.sha256(payload).hexdigest()
        (directory / f"{digest}.htm").write_bytes(payload)
        digests.append(digest)
    manifest = {"source_snapshot_ids": [f"GRETIL:{digests[0]}"]}
    issues = verify_manifest_snapshots(manifest, tmp_path)
    unlisted = [i for i in issues if i.details.get("unlisted_count")]
    assert unlisted and unlisted[0].details["unlisted_count"] == 2
    assert unlisted[0].severity == QASeverity.WARNING


def test_a_fully_listed_manifest_produces_no_issue(tmp_path) -> None:
    import hashlib

    from vedagraph.qa.checks import verify_manifest_snapshots

    directory = tmp_path / "gretil"
    directory.mkdir()
    digest = hashlib.sha256(b"only").hexdigest()
    (directory / f"{digest}.htm").write_bytes(b"only")
    manifest = {
        "source_snapshot_ids": [f"GRETIL:{digest}"],
        "raw_snapshot_hashes": {"GRETIL.X": digest},
    }
    assert verify_manifest_snapshots(manifest, tmp_path) == []


def test_a_manifest_recorded_hash_that_disagrees_with_the_bytes_is_an_error(tmp_path) -> None:
    import hashlib

    from vedagraph.qa.checks import verify_manifest_snapshots

    directory = tmp_path / "gretil"
    directory.mkdir()
    digest = hashlib.sha256(b"real").hexdigest()
    (directory / f"{digest}.htm").write_bytes(b"real")
    manifest = {"raw_snapshot_hashes": {"GRETIL.X": "e" * 64}}
    issues = verify_manifest_snapshots(manifest, tmp_path)
    assert issues and issues[0].severity == QASeverity.ERROR


def test_an_unverifiable_scope_is_reported_not_silently_passed() -> None:
    """A skip must not look like a pass.

    When the wrong-scope checksum on the Vajasaneyi samhita artifact was later *removed*
    rather than corrected, `verify_checksum_scope` lost its input and the gate went green.
    An artifact whose scope could not be checked has to be visibly distinguishable from one
    that was checked and agreed.
    """
    from vedagraph.qa.checks import verify_checksum_scope

    artifact = _artifact("A.B.C", None)
    issues = verify_checksum_scope([artifact], pathlib.Path("data/raw"), [artifact])
    assert issues, "an artifact with no checksum anywhere must be reported, not skipped"
    assert issues[0].check_id == "checksum_scope_agreement"
    assert issues[0].severity == QASeverity.INFO
    assert "NOT verified" in issues[0].message


def test_a_pinned_checksum_with_no_retained_bytes_is_reported() -> None:
    from vedagraph.qa.checks import verify_checksum_scope

    artifact = _artifact("A.B.C", "f" * 64)
    issues = verify_checksum_scope([artifact], pathlib.Path("data/raw"), [artifact])
    assert issues and issues[0].severity == QASeverity.INFO
    assert "not retained locally" in issues[0].message


def test_an_emitted_text_role_disagreeing_with_the_registry_is_an_error() -> None:
    """TextRole is a permission statement, not a description.

    Agent E's live case: a pilot emitted PRIMARY_TEXT for a layer the registry had
    deliberately registered as EXTRACTED_FROM_CONTAINER, because the layer keeps only one
    of two attested readings at VSM 16.37. Choosing a role in build code asserts a
    permission the rights authority never granted.
    """
    from vedagraph.models import TextVersionDescriptor
    from vedagraph.qa.checks import verify_text_role_matches_registry

    declared = [
        d for d in load_text_versions() if d.text_version_id == "WIKISOURCE_SA.YV.VSM.ACCENTED"
    ]
    assert declared, "expected the registry to declare the accented Vajasaneyi layer"
    assert isinstance(declared[0], TextVersionDescriptor)

    overreaching = TextVersion(
        text_id=uuid_for_urn("urn:vedagraph:text:role-test:1"),
        passage_id=uuid_for_urn(
            "urn:vedagraph:mantra:yajurveda:vajasaneyi-madhyandina:adhyaya:1:mantra:1"
        ),
        language="sa",
        script="Deva",
        text_form="SAMHITA",
        text_role="PRIMARY_TEXT",
        text_version_id="WIKISOURCE_SA.YV.VSM.ACCENTED",
        text_original="agnim",
        text_nfc="agnim",
        accented=True,
        source_id="WIKISOURCE_SA",
        source_locator="x",
        content_sha256="a" * 64,
        rights_status="REFERENCE_ONLY",
    )
    issues = verify_text_role_matches_registry([overreaching], declared)
    assert issues and issues[0].check_id == "text_role_matches_registry"
    assert issues[0].severity == QASeverity.ERROR
    assert issues[0].details["emitted_role"] == "PRIMARY_TEXT"
    assert issues[0].details["registry_role"] == "EXTRACTED_FROM_CONTAINER"


def test_an_agreeing_text_role_produces_no_issue() -> None:
    from vedagraph.qa.checks import verify_text_role_matches_registry

    declared = [
        d for d in load_text_versions() if d.text_version_id == "WIKISOURCE_SA.YV.VSM.ACCENTED"
    ]
    conforming = TextVersion(
        text_id=uuid_for_urn("urn:vedagraph:text:role-test:2"),
        passage_id=uuid_for_urn(
            "urn:vedagraph:mantra:yajurveda:vajasaneyi-madhyandina:adhyaya:1:mantra:2"
        ),
        language="sa",
        script="Deva",
        text_form="SAMHITA",
        text_role=declared[0].text_role,
        text_version_id="WIKISOURCE_SA.YV.VSM.ACCENTED",
        text_original="agnim",
        text_nfc="agnim",
        accented=True,
        source_id="WIKISOURCE_SA",
        source_locator="x",
        content_sha256="a" * 64,
        rights_status="REFERENCE_ONLY",
    )
    assert verify_text_role_matches_registry([conforming], declared) == []


def test_role_checking_does_not_double_count_an_unregistered_version() -> None:
    """That defect belongs to verify_text_version_registration; one defect, one check."""
    from vedagraph.qa.checks import verify_text_role_matches_registry

    orphan = TextVersion(
        text_id=uuid_for_urn("urn:vedagraph:text:role-test:3"),
        passage_id=uuid_for_urn("urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:3"),
        language="sa",
        script="Latn",
        text_form="SAMHITA",
        text_role="PRIMARY_TEXT",
        text_version_id="NOT.IN.THE.REGISTRY",
        text_original="agnim",
        text_nfc="agnim",
        accented=False,
        source_id="GRETIL",
        source_locator="x",
        content_sha256="a" * 64,
        rights_status="REFERENCE_ONLY",
    )
    assert verify_text_role_matches_registry([orphan], []) == []


def test_unlisted_manifest_snapshots_are_attributed_not_just_counted(tmp_path) -> None:
    """A shared raw directory makes parity unreachable, so the check must show its working.

    Agent C proved the case: data/raw/wikisource_sa holds Samaveda fetches under the same
    source id as Yajurveda, so a bare count would permanently read cross-agent traffic as
    under-reporting.
    """
    import hashlib

    from vedagraph.qa.checks import verify_manifest_snapshots

    directory = tmp_path / "shared"
    directory.mkdir()
    listed = hashlib.sha256(b"mine").hexdigest()
    (directory / f"{listed}.json").write_bytes(b"mine")
    other = hashlib.sha256(b"someone else").hexdigest()
    (directory / f"{other}.json").write_bytes(b"someone else")
    (directory / f"{other}.metadata.json").write_bytes(
        b'{"retrieval_url": "https://example.org/another-agents-page"}'
    )

    manifest = {"source_snapshot_ids": [f"SHARED:{listed}"]}
    issues = verify_manifest_snapshots(manifest, tmp_path)
    unlisted = [i for i in issues if i.details.get("unlisted_count")]
    assert unlisted and unlisted[0].details["unlisted_count"] == 1
    assert "another-agents-page" in unlisted[0].details["unlisted"][0]
    assert "shared storage" in unlisted[0].message
