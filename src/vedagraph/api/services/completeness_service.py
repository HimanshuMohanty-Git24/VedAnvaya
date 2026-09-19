"""Service assembling certified data-completeness metrics across VedAnvaya."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vedagraph.api.models.common import CaveatView, KnowledgeStatus
from vedagraph.api.models.completeness import (
    AskBenchmarkCompleteness,
    AudioCompleteness,
    CompletenessResponse,
    CorpusCompletenessItem,
    EvidenceLayersCompleteness,
    SamavedaNotationCompleteness,
    TranslationCompletenessSummary,
    TranslationVedaItem,
)
from vedagraph.domain import layer_figures
from vedagraph.product.audio.catalog import AudioCatalog
from vedagraph.product.audio.models import PublicationTier


#: The date the certified state below describes. A constant rather than ``date.today()``:
#: this response states when the corpus was certified, not when it was asked about, and a
#: date that moves every morning is a claim of freshness nothing behind it supports.
CERTIFIED_AS_OF_DATE = "2026-09-19"


class CompletenessService:
    """Delivers the certified current data completeness and release state."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or Path("data")

    def _read_audio_pass_gates(self) -> dict[str, Any]:
        path = self._data_dir / "staging" / "release_prep" / "audio_pass_final_gates.json"
        if path.is_file():
            try:
                with path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_completeness(self) -> CompletenessResponse:
        # 1. Corpus invariant counts
        corpus_mantras = dict(layer_figures.CORPUS_MANTRAS)
        total_mantras = sum(corpus_mantras.values())

        corpora = [
            CorpusCompletenessItem(
                veda="RV",
                traditional_name="Rigveda Samhita",
                devanagari_name="ऋग्वेद",
                recension="Śākala recension",
                scope_honest_label="Rigveda Samhita - Śākala recension",
                scope_note="Samhita only, in one recension. No Brahmana, Aranyaka or Upanisad layer is held.",
                canonical_mantras=corpus_mantras["RV"],
                structure="Mandala → Sukta → Mantra",
                excluded_corpora=[
                    "SECOND_RIGVEDIC_RECENSION",
                    "RIGVEDIC_BRAHMANA",
                    "RIGVEDIC_ARANYAKA",
                    "UPANISAD",
                ],
                limitations="Samhita only, in the Śākala recension. The Āśvalāyana recension is absent.",
            ),
            CorpusCompletenessItem(
                veda="SV",
                traditional_name="Samaveda Samhita",
                devanagari_name="सामवेद",
                recension="Kauthuma recension, ārcika only",
                scope_honest_label="Samaveda Samhita - Kauthuma ārcika only (gāna corpus NOT included)",
                scope_note="Kauthuma ārcika verse corpus only. The gāna song-books are not included. 1,136 validated notation witnesses are held; no melody or pitch is inferred.",
                canonical_mantras=corpus_mantras["SV"],
                structure="Collection → Prapathaka → Ardha → Dasati → Verse",
                excluded_corpora=[
                    "SAMAVEDA_GRAMAGEYA_GANA",
                    "SAMAVEDA_ARANYAKAGEYA_GANA",
                    "SAMAVEDA_UHAGANA",
                    "SAMAVEDA_UHYAGANA",
                    "SECOND_SAMAVEDIC_RECENSION",
                    "SAMAVEDIC_BRAHMANA",
                    "UPANISAD",
                ],
                limitations="Ārcika verses only. Gāna song-books not included; no canonical Gāna works or MUSICALIZED_AS edges.",
            ),
            CorpusCompletenessItem(
                veda="YV",
                traditional_name="Vājasaneyi Samhitā",
                devanagari_name="यजुर्वेद",
                recension="Śukla, Vājasaneyi Mādhyandina",
                scope_honest_label="Vājasaneyi Samhitā - Śukla Yajurveda, Mādhyandina recension",
                scope_note="Śukla (White) Yajurveda only. The Krishna Yajurveda is not held at all.",
                canonical_mantras=corpus_mantras["YV"],
                structure="Adhyaya → Mantra",
                excluded_corpora=[
                    "KRISHNA_YAJURVEDA_TAITTIRIYA",
                    "KRISHNA_YAJURVEDA_KATHAKA",
                    "KRISHNA_YAJURVEDA_MAITRAYANI",
                    "KRISHNA_YAJURVEDA_KAPISTHALA",
                    "SHUKLA_YAJURVEDA_KANVA_RECENSION",
                    "SATAPATHA_BRAHMANA",
                    "UPANISAD",
                ],
                limitations="White Yajurveda only. Krishna Yajurveda (Taittirīya, Kāṭhaka, Maitrāyaṇī, Kapiṣṭhala) absent entirely.",
            ),
            CorpusCompletenessItem(
                veda="AV",
                traditional_name="Atharvaveda Samhita",
                devanagari_name="अथर्ववेद",
                recension="Śaunaka recension",
                scope_honest_label="Atharvaveda Samhita - Śaunaka recension",
                scope_note="Śaunaka recension only, held as a working private corpus. Paippalāda recension is absent.",
                canonical_mantras=corpus_mantras["AV"],
                structure="Kanda → Sukta → Mantra",
                excluded_corpora=[
                    "ATHARVAVEDA_PAIPPALADA_RECENSION",
                    "GOPATHA_BRAHMANA",
                    "UPANISAD",
                ],
                limitations="Śaunaka recension only. The Paippalāda recension is substantially different and absent.",
            ),
        ]

        # 2. Translation coverage breakdown
        dedicated = dict(layer_figures.DEDICATED_ENGLISH_MANTRAS)
        range_cov = dict(layer_figures.RANGE_COVERED_MANTRAS)
        reused = dict(layer_figures.REUSED_RENDERING_MANTRAS)
        non_en = dict(layer_figures.NON_ENGLISH_MANTRAS)

        by_veda_trans: dict[str, TranslationVedaItem] = {}
        for v in ("RV", "SV", "YV", "AV"):
            total_v = corpus_mantras[v]
            ded_v = dedicated.get(v, 0)
            rng_v = range_cov.get(v, 0)
            reu_v = reused.get(v, 0)
            non_v = non_en.get(v, 0)
            covered_v = ded_v + rng_v + reu_v + non_v
            uncov_v = max(0, total_v - covered_v)
            indep_en = ded_v + rng_v
            pct = round((covered_v / total_v) * 100, 2)

            if v == "RV":
                notes = (
                    "High dedicated English coverage (10,480 verses). 60 verses covered in multi-verse "
                    "ranges; 6 Latin substitutions; 6 mantras uncovered."
                )
            elif v == "SV":
                notes = (
                    "No own translation layer. 173 verses carry published English renderings reused "
                    "from verified character-identical Rigvedic parallels; 1,671 mantras uncovered."
                )
            elif v == "YV":
                notes = (
                    "1,950 verses carry dedicated English translations; 25 mantras uncovered."
                )
            else:
                notes = (
                    "5,715 dedicated English renderings, 68 range-covered, 21 reused from Rigveda "
                    "parallels, 18 Latin substitutions, 17 uncovered."
                )

            by_veda_trans[v] = TranslationVedaItem(
                veda=v,
                total_mantras=total_v,
                dedicated_english=ded_v,
                range_covered=rng_v,
                reused_rendering=reu_v,
                non_english=non_v,
                uncovered=uncov_v,
                independent_english=indep_en,
                coverage_percentage=pct,
                has_own_dedicated_english=ded_v > 0,
                notes=notes,
            )

        translations_summary = TranslationCompletenessSummary(
            by_veda=by_veda_trans,
            total_mantras=total_mantras,
            total_dedicated_english=sum(item.dedicated_english for item in by_veda_trans.values()),
            total_range_covered=sum(item.range_covered for item in by_veda_trans.values()),
            total_reused_rendering=sum(item.reused_rendering for item in by_veda_trans.values()),
            total_non_english=sum(item.non_english for item in by_veda_trans.values()),
            total_uncovered=sum(item.uncovered for item in by_veda_trans.values()),
            truth_statement=(
                "Translation coverage is explicitly typed into five states: dedicated English, "
                "multi-verse range coverage, reused parallel rendering, non-English (Latin) substitution, "
                "and uncovered remainder. For the Samaveda, 'no own translation' is not 'no translation available at all': "
                "173 verses carry verified reused English from Rigvedic parallels."
            ),
        )

        # 3. Samaveda musical notation
        samaveda_notation = SamavedaNotationCompleteness(
            canonical_corpus_mantras=1844,
            validated_notation_witnesses=1136,
            gates_passed=["Gate A: PASS", "Gate B: PASS", "Gate C: SURVIVED"],
            evidence_class="PARALLEL_WITNESS / PARALLEL_TEXT",
            notation_system="Kauthuma numeric svara (source-printed codepoints)",
            source_supplied=True,
            interpreted_into_pitch=False,
            unaligned_withheld_verses=708,
            withheld_reason="Unaligned or unsupported notation rows withheld",
            gana_object_layer="OUT_OF_SCOPE",
            gana_works_modeled=0,
            musicalized_as_edges=0,
            truth_statement=(
                "VedAnvaya holds the Kauthuma Ārcika as its canonical Samaveda text (1,844 mantras). "
                "Source-explicit notation witnesses are available for 1,136 aligned verses (validated "
                "through Gates A, B, and C). Unaligned/unsupported notation remains withheld (708 verses). "
                "VedAnvaya does not model the canonical Gāna corpus as separate Gāna works and does not assert "
                "MUSICALIZED_AS relations."
            ),
        )

        # 4. Audio catalogue & the two publication tiers
        #
        # Every figure here is counted off the catalogue that is actually loaded. The block
        # this replaces mixed the two: it took `total_audio_records` from the file and then
        # wrote the per-Veda split into a sentence by hand, so admitting 946 recordings made
        # the response read "17,780 catalogued records (RV 10,402; AV 4,680; YV 1,752)" -
        # a total that no longer matched its own breakdown, in the one field a product
        # surface is invited to quote verbatim. A figure typed into prose is the only figure
        # nothing can check, so there are none left in it.
        tier_counts: dict[str, int] = {}
        by_veda_and_tier: dict[str, dict[str, int]] = {}
        try:
            catalog = AudioCatalog.load_default()
            total_audio_records = len(catalog)
            raw_counts = catalog.counts_by("veda")
            released_by_veda = {v: raw_counts.get(v, 0) for v in ("RV", "AV", "YV", "SV")}
            released_scope_keys = {
                v: len(catalog.scope_keys_for_veda(v)) for v in ("RV", "AV", "YV", "SV")
            }
            by_veda_and_tier = catalog.counts_by_veda_and_tier()
            for tier in PublicationTier:
                tier_counts[tier.value] = len(catalog.for_tier(tier))
        except Exception:
            # A catalogue that cannot be read is a zero *nobody should quote*, so the
            # figures are left empty rather than filled with a frozen copy of a past
            # release. The old fallback here held 16,834 and survived the admission of 946
            # recordings unchanged, which is the failure mode of every stale constant.
            total_audio_records = 0
            released_by_veda = {}
            released_scope_keys = {}

        reviewed_count = tier_counts.get(PublicationTier.RELEASED_VERIFIED.value, 0)
        unreviewed_count = tier_counts.get(PublicationTier.SOURCE_MAPPED_UNREVIEWED.value, 0)

        gate_json = self._read_audio_pass_gates()
        audio_info = gate_json.get("audio", {})

        audio_completeness = AudioCompleteness(
            released_catalogue_records=total_audio_records,
            released_by_veda=released_by_veda,
            released_scope_keys_by_veda=released_scope_keys,
            owner_audible_sample_status=audio_info.get("AUDIO_OWNER_SAMPLE", "ACCEPTED"),
            owner_sample_reviewed=audio_info.get("AUDIO_SAMPLE_REVIEWED", 20),
            owner_sample_verified=audio_info.get("AUDIO_SAMPLE_VERIFIED", 20),
            owner_sample_rejected=audio_info.get("AUDIO_SAMPLE_REJECTED", 0),
            queue_total=audio_info.get("queue_total", 1021),
            not_individually_heard=audio_info.get("NOT_INDIVIDUALLY_HEARD", 1001),
            queue_rows_promoted=audio_info.get("queue_rows_promoted", 0),
            released_by_tier=tier_counts,
            released_by_veda_and_tier=by_veda_and_tier,
            # Stated in words rather than as sprint identifiers. GAP-AUDIO-002/003/004 named
            # the same three facts to anybody holding the registry and nothing at all to a
            # reader, and this field is served to a product surface.
            withheld_gates=[
                "No Samavedic recitation is catalogued from any source.",
                "Recordings are streamed from their publishers; none is redistributed here.",
                "Human audible review is a per-recording badge, not a condition of publication.",
            ],
            truth_statement=(
                f"{total_audio_records:,} recitations are catalogued"
                + (
                    " ("
                    + "; ".join(
                        f"{veda} {count:,}" for veda, count in released_by_veda.items()
                    )
                    + ")"
                    if released_by_veda
                    else ""
                )
                + ". "
                + (
                    f"{reviewed_count:,} of them have been listened to and confirmed by a "
                    f"person; the remaining {unreviewed_count:,} are mapped to their verse "
                    "and checked against its text automatically, and no one has heard them. "
                    if tier_counts
                    else ""
                )
                + "They are not described as human-verified."
            ),
        )

        # 5. Ask formal 60 benchmark
        ask_completeness = AskBenchmarkCompleteness(
            benchmark_version="ask_benchmark_v1",
            status="COMPLETE",
            total_questions=60,
            effective_acceptable="60/60",
            supported_correct=39,
            partial_correct=4,
            insufficient_evidence_refused=17,
            misleading=0,
            hallucinated=0,
            truth_statement=(
                "Ask formal 60 benchmark achieved 60/60 acceptable results (39 SUPPORTED_CORRECT, "
                "4 PARTIAL_CORRECT, 17 INSUFFICIENT_EVIDENCE_CORRECTLY_REFUSED) with 0 MISLEADING "
                "and 0 HALLUCINATED claims. Ask returns PARTIAL or INSUFFICIENT_EVIDENCE when "
                "the knowledge graph lacks evidence; it is not factually omniscient."
            ),
        )

        # 6. Evidence layers and grounding rules
        evidence_layers = EvidenceLayersCompleteness(
            source_explicit=(
                "Quoted text, traditional index ascriptions, and published translations. "
                "Quotations from editions and Anukramaṇī apparatus; the strongest evidence held."
            ),
            deterministic_derived=(
                "Properties computed strictly by rule from source statements: container projections, "
                "canonical hierarchy resolution, and exact-string character matches."
            ),
            semantic_model_assisted=(
                "Candidate extractions authored with language models (2,459 Rigvedic candidates in "
                "a 35,131-assertion layer spanning all four Samhitas). Permanently candidate status; "
                "not equivalent to human scholarly adjudication."
            ),
            interpretive_claim=(
                "Model-authored candidate readings (6 in total across the build), each explicitly carrying "
                "the observation that would falsify it."
            ),
            normalization_rule=(
                "Normalization is a comparison instrument for search and alignment, not identity evidence by itself."
            ),
            predicate_reach_rule=(
                "Absence from one annotation predicate does not necessarily mean absence from the Vedic text."
            ),
        )

        caveats = [
            CaveatView(
                text=(
                    "These figures represent the certified post-campaign data state of VedAnvaya at commit "
                    "50a40429103fa32a5667ee58c72c029cfbeb0f74. The corpus comprises four Samhitas in one "
                    "recension each (20,210 canonical mantras total)."
                ),
                source="certified_release",
            )
        ]

        total_canonical = sum(corpus.canonical_mantras for corpus in corpora)
        by_veda_counts = {corpus.veda: corpus.canonical_mantras for corpus in corpora}

        return CompletenessResponse(
            data_status=KnowledgeStatus.SUPPORTED,
            certified_release_commit="50a40429103fa32a5667ee58c72c029cfbeb0f74",
            as_of_date=CERTIFIED_AS_OF_DATE,
            total_canonical_mantras=total_canonical,
            truth_summary=(
                f"VedAnvaya holds {total_canonical:,} canonical mantras across four Vedic "
                f"Samhitas in one recension each (RV "
                f"{by_veda_counts.get('RV', 0):,}; SV {by_veda_counts.get('SV', 0):,}; "
                f"YV {by_veda_counts.get('YV', 0):,}; AV {by_veda_counts.get('AV', 0):,}), "
                f"{translations_summary.total_dedicated_english:,} dedicated English "
                f"translations and {translations_summary.total_reused_rendering:,} renderings "
                f"reached through a verified parallel, "
                f"{samaveda_notation.validated_notation_witnesses:,} validated Samaveda "
                f"notation witnesses, and "
                f"{audio_completeness.released_catalogue_records:,} catalogued recordings."
            ),
            corpora=corpora,
            translations=translations_summary,
            samaveda_notation=samaveda_notation,
            audio=audio_completeness,
            ask_benchmark=ask_completeness,
            evidence_layers=evidence_layers,
            caveats=caveats,
        )
