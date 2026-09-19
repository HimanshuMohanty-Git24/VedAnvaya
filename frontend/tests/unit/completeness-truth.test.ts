import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { FALLBACK_COMPLETENESS } from "@/lib/api";

describe("Frontend Certified Completeness Truth", () => {
    it("holds certified release commit and invariant core counts", () => {
        expect(FALLBACK_COMPLETENESS.certified_release_commit).toBe(
            "50a40429103fa32a5667ee58c72c029cfbeb0f74",
        );
        expect(FALLBACK_COMPLETENESS.total_canonical_mantras).toBe(20210);

        const corpora = Object.fromEntries(
            FALLBACK_COMPLETENESS.corpora.map((c) => [c.veda, c.canonical_mantras]),
        );
        expect(corpora.RV).toBe(10552);
        expect(corpora.SV).toBe(1844);
        expect(corpora.YV).toBe(1975);
        expect(corpora.AV).toBe(5839);
        expect(corpora.RV + corpora.SV + corpora.YV + corpora.AV).toBe(20210);
    });

    it("holds typed translation breakdown with exact sum reconciliation", () => {
        const trans = FALLBACK_COMPLETENESS.translations;
        expect(trans.total_mantras).toBe(20210);
        expect(trans.total_dedicated_english).toBe(18145);
        expect(trans.total_range_covered).toBe(128);
        expect(trans.total_reused_rendering).toBe(194);
        expect(trans.total_non_english).toBe(24);
        expect(trans.total_uncovered).toBe(1719);

        const sum =
            trans.total_dedicated_english +
            trans.total_range_covered +
            trans.total_reused_rendering +
            trans.total_non_english +
            trans.total_uncovered;
        expect(sum).toBe(20210);

        // Samaveda translation truth
        const sv = trans.by_veda.SV;
        expect(sv.dedicated_english).toBe(0);
        expect(sv.has_own_dedicated_english).toBe(false);
        expect(sv.reused_rendering).toBe(173);
        expect(sv.uncovered).toBe(1671);
        expect(sv.total).toBe(1844);
    });

    it("holds Samaveda musical notation certification and gate boundaries", () => {
        const notation = FALLBACK_COMPLETENESS.samaveda_notation;
        expect(notation.canonical_corpus_mantras).toBe(1844);
        expect(notation.validated_notation_witnesses).toBe(1136);
        expect(notation.unaligned_withheld_verses).toBe(708);
        expect(notation.musicalized_as_edges).toBe(0);
        expect(notation.gana_works_modeled).toBe(0);
        expect(notation.gates_passed.some((g) => g.includes("Gate A: PASS"))).toBe(true);
        expect(notation.gates_passed.some((g) => g.includes("Gate B: PASS"))).toBe(true);
        expect(notation.gates_passed.some((g) => g.includes("Gate C: SURVIVED"))).toBe(true);
    });

    it("holds audio catalogue release counts and audible review gates", () => {
        const audio = FALLBACK_COMPLETENESS.audio;
        expect(audio.released_catalogue_records).toBe(16834);
        expect(audio.released_by_veda.RV).toBe(10402);
        expect(audio.released_by_veda.AV).toBe(4680);
        expect(audio.released_by_veda.YV).toBe(1752);
        expect(audio.released_by_veda.SV).toBe(0);

        expect(audio.owner_audible_sample_status).toBe("ACCEPTED");
        expect(audio.owner_sample_reviewed).toBe(20);
        expect(audio.owner_sample_verified).toBe(20);
        expect(audio.owner_sample_rejected).toBe(0);
        expect(audio.not_individually_heard).toBe(1001);
        expect(audio.queue_rows_promoted).toBe(0);
        expect(audio.withheld_gates).toContain("GAP-AUDIO-002");
        expect(audio.withheld_gates).toContain("GAP-AUDIO-003");
        expect(audio.withheld_gates).toContain("GAP-AUDIO-004");
    });

    it("holds formal Ask 60 benchmark verification outcomes", () => {
        const ask = FALLBACK_COMPLETENESS.ask_benchmark;
        expect(ask.total_questions).toBe(60);
        expect(ask.effective_acceptable).toBe("60/60");
        expect(ask.supported_correct).toBe(39);
        expect(ask.partial_correct).toBe(4);
        expect(ask.insufficient_evidence_refused).toBe(17);
        expect(ask.misleading).toBe(0);
        expect(ask.hallucinated).toBe(0);
    });

    it("verifies that old stale completeness claims cannot reappear in frontend source files", () => {
        const vedasSource = readFileSync(
            join(process.cwd(), "src/app/vedas/page.tsx"),
            "utf8",
        );
        const homeSource = readFileSync(
            join(process.cwd(), "src/app/page.tsx"),
            "utf8",
        );
        const limitsSource = readFileSync(
            join(process.cwd(), "src/app/limits/page.tsx"),
            "utf8",
        );

        // Old stale claims that must never reappear
        const stalePhrases = [
            "deciphering them needs an authority this build does not have",
            "No recording exists. The source publishes Samavedic verse text and no Samavedic audio",
            "The gap is in what has been published anywhere",
        ];

        for (const phrase of stalePhrases) {
            expect(vedasSource).not.toContain(phrase);
            expect(homeSource).not.toContain(phrase);
            expect(limitsSource).not.toContain(phrase);
        }

        // New certified truths must appear
        expect(vedasSource).toContain("173");
        expect(vedasSource).toContain("reused");
        expect(vedasSource).toContain("1,136");
        expect(vedasSource).toContain("1,001 withheld");

        expect(limitsSource).toContain("20,210");
        expect(limitsSource).toContain("18,145");
        expect(limitsSource).toContain("16,834");
        expect(limitsSource).toContain("GAP-AUDIO-002");

        expect(homeSource).toContain("173 reused");
        expect(homeSource).toContain("Zero released records");
    });
});
