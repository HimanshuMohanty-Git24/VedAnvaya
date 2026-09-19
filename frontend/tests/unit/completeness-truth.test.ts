import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { FALLBACK_COMPLETENESS } from "@/lib/api";

/**
 * What the frontend may say about the certified state, and where it may say it.
 *
 * This file used to assert the opposite of what it asserts now, and the reversal is the
 * point rather than an embarrassment. It required `/limits` to contain the literal string
 * `GAP-AUDIO-002` and the homepage to contain `173 reused` and `Zero released records` --
 * that is, it pinned a specific sentence into a specific page, which made two things true
 * at once: internal sprint identifiers could not be removed from a reader-facing page
 * without failing a test, and figures had to be typed into JSX where nothing could check
 * them against the service.
 *
 * Both of those are now defects rather than requirements. So the assertions here changed
 * shape: they pin *arithmetic* on the fallback, which must reconcile whatever the numbers
 * become, and *absence* on the pages, which must not carry this project's issue tracker or
 * a frozen copy of a superseded figure. What a page positively says is checked against the
 * live service by `scripts/audit-completeness-fallback.mjs`, which is the only thing that
 * can check it, because it is the only one of the two that knows what the service says.
 */

/** Product pages a reader reaches without asking for engineering detail. */
const PRODUCT_PAGES = [
    "src/app/page.tsx",
    "src/app/vedas/page.tsx",
    "src/app/vedas/[veda]/page.tsx",
    "src/app/passage/[key]/page.tsx",
    "src/app/connections/page.tsx",
    "src/app/graph/page.tsx",
];

/**
 * This project's own issue tracker, speaking to itself.
 *
 * A reader cannot look any of these up, and several of them name a decision that has since
 * been superseded. `/limits` and `/sources` are where boundaries are explained, and even
 * there the explanation is meant to be in words.
 */
const INTERNAL_IDENTIFIERS = [
    "GAP-AUDIO-",
    "GAP-QUALITY-",
    "GAP-ATTRIBUTION-",
    "REGISTRY_IMPLEMENTATION_FIXABLE",
    "owner-decision-required",
    "dependency stale",
    "completeness campaign",
    "Gate A:",
    "Gate B:",
    "Gate C:",
];

/**
 * Figures that were certified once and are now wrong.
 *
 * Each of these was true of the release this fallback was first written against, and each
 * was superseded by `OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION` admitting 946 further
 * recordings. A page holding one of them is not merely stale: it is stale in a way that
 * looks exactly like a live figure, which is the failure this whole pass is repairing.
 */
const SUPERSEDED_AUDIO_FIGURES = ["16,834", "16834", "10,402", "4,680", "1,752"];

function read(relative: string) {
    return readFileSync(join(process.cwd(), relative), "utf8");
}

describe("the certified state the frontend falls back to", () => {
    it("names the release it is a copy of", () => {
        expect(FALLBACK_COMPLETENESS.certified_release_commit).toBe(
            "50a40429103fa32a5667ee58c72c029cfbeb0f74",
        );
        expect(FALLBACK_COMPLETENESS.as_of_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    });

    it("holds the corpus, which is frozen, exactly", () => {
        const corpora = Object.fromEntries(
            FALLBACK_COMPLETENESS.corpora.map((c) => [c.veda, c.canonical_mantras]),
        );
        expect(corpora.RV).toBe(10552);
        expect(corpora.SV).toBe(1844);
        expect(corpora.YV).toBe(1975);
        expect(corpora.AV).toBe(5839);
        expect(FALLBACK_COMPLETENESS.total_canonical_mantras).toBe(
            corpora.RV + corpora.SV + corpora.YV + corpora.AV,
        );
    });

    it("reconciles the translation typology against the corpus", () => {
        const trans = FALLBACK_COMPLETENESS.translations;
        const sum =
            trans.total_dedicated_english +
            trans.total_range_covered +
            trans.total_reused_rendering +
            trans.total_non_english +
            trans.total_uncovered;
        expect(sum).toBe(FALLBACK_COMPLETENESS.total_canonical_mantras);
        expect(trans.total_mantras).toBe(FALLBACK_COMPLETENESS.total_canonical_mantras);
    });

    it("keeps the Samaveda's reused renderings distinct from translations of its own", () => {
        const sv = FALLBACK_COMPLETENESS.translations.by_veda.SV;
        expect(sv.dedicated_english).toBe(0);
        expect(sv.has_own_dedicated_english).toBe(false);
        expect(sv.reused_rendering).toBeGreaterThan(0);
        expect(sv.total_mantras).toBe(1844);
    });

    it("holds the Samavedic notation scope, and claims no melody", () => {
        const notation = FALLBACK_COMPLETENESS.samaveda_notation;
        expect(notation.canonical_corpus_mantras).toBe(1844);
        expect(notation.validated_notation_witnesses).toBe(1136);
        expect(notation.interpreted_into_pitch).toBe(false);
        expect(notation.musicalized_as_edges).toBe(0);
        expect(notation.gana_works_modeled).toBe(0);
    });

    it("splits the audio catalogue into tiers that sum to it", () => {
        /*
         * Counts rather than literals, because the counts are now allowed to move: the
         * owner's two-tier decision publishes source-mapped recordings, and a test pinned
         * to 16,834 would fail the next admission rather than catch anything. What cannot
         * move is that the parts add up to the whole.
         */
        const audio = FALLBACK_COMPLETENESS.audio;
        const byVeda = Object.values(audio.released_by_veda).reduce((a, b) => a + b, 0);
        const byTier = Object.values(audio.released_by_tier).reduce((a, b) => a + b, 0);
        expect(byVeda).toBe(audio.released_catalogue_records);
        expect(byTier).toBe(audio.released_catalogue_records);
        expect(Object.keys(audio.released_by_tier).sort()).toEqual([
            "RELEASED_VERIFIED",
            "SOURCE_MAPPED_UNREVIEWED",
        ]);
        for (const [veda, tiers] of Object.entries(audio.released_by_veda_and_tier)) {
            const total = Object.values(tiers).reduce((a, b) => a + b, 0);
            expect(total, veda).toBe(audio.released_by_veda[veda]);
        }
    });

    it("never describes an unheard recording as verified", () => {
        /*
         * The one sentence the two-tier decision exists to prevent. 17,760 of 17,780
         * recordings have not been listened to by anybody, and the tier name for them says
         * so; a summary that rolled them into "verified audio" would undo the distinction
         * in the field beneath it.
         */
        const audio = FALLBACK_COMPLETENESS.audio;
        const reviewed = audio.released_by_tier.RELEASED_VERIFIED ?? 0;
        const claim = `${audio.truth_statement} ${FALLBACK_COMPLETENESS.truth_summary}`;
        if (reviewed < audio.released_catalogue_records) {
            expect(claim).not.toMatch(/\b(verified|reviewed|human-checked) (audio|recordings)\b/i);
        }
    });

    it("holds the Ask benchmark outcome", () => {
        const ask = FALLBACK_COMPLETENESS.ask_benchmark;
        expect(ask.total_questions).toBe(60);
        expect(ask.effective_acceptable).toBe("60/60");
        expect(ask.misleading).toBe(0);
        expect(ask.hallucinated).toBe(0);
        expect(
            ask.supported_correct + ask.partial_correct + ask.insufficient_evidence_refused,
        ).toBe(ask.total_questions);
    });
});

describe("what a normal product page may not contain", () => {
    it.each(PRODUCT_PAGES)("%s carries no internal identifier", (page) => {
        const source = read(page);
        for (const identifier of INTERNAL_IDENTIFIERS) {
            expect(source, `${page} contains ${identifier}`).not.toContain(identifier);
        }
    });

    it.each(PRODUCT_PAGES)("%s holds no superseded audio figure", (page) => {
        /*
         * A figure typed into a page is the only figure nothing can check. These five were
         * all correct when they were written and are all wrong now, and none of them
         * failed anything on the way from correct to wrong.
         */
        const source = read(page);
        for (const figure of SUPERSEDED_AUDIO_FIGURES) {
            expect(source, `${page} contains the superseded figure ${figure}`).not.toContain(
                figure,
            );
        }
    });

    it("keeps the detail discoverable on /limits", () => {
        /*
         * The counterpart to the two assertions above: removing the boundaries from product
         * pages only improves the product if they still exist somewhere a reader can reach.
         * Asserted as subject matter rather than as sentences, so /limits can be rewritten
         * without this test having an opinion about its prose.
         */
        const limits = read("src/app/limits/page.tsx");
        for (const subject of [
            /recension/i,
            /translat/i,
            /recitation|audio/i,
            /notation/i,
            /evidence/i,
            /Ask/,
        ]) {
            expect(limits).toMatch(subject);
        }
    });
});
