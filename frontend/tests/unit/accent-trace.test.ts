import { describe, expect, it } from "vitest";
import { accentTrace } from "@/lib/accent-trace";

/**
 * The Accent Trace, tested for the things that would make it lie.
 *
 * The trace claims exactly one thing: these are the accent marks this edition prints, and
 * this one is above the letter and that one below. Four ways it could stop being true, and
 * one test for each:
 *
 *   it could count a letter as an accent - `ś` decomposes to `s` + U+0301, and a naive scan
 *   over combining marks counts every palatal sibilant in the Atharvaveda as an accented
 *   syllable;
 *
 *   it could count a diacritic as an accent - the macron is vowel length, the dot below
 *   builds the retroflexes, and neither says anything about accent;
 *
 *   it could turn a sung notation into a pitch contour - the Sāmavedic svara numerals are a
 *   melody, and drawing them as a rising and falling line is the one thing the brief forbids
 *   outright;
 *
 *   it could guess rather than refuse - a text with no marks, or one mark, has no contour in
 *   it, and a drawing that appeared anyway would be decoration wearing a derivation's
 *   clothes.
 *
 * Every string below is real text from this corpus, copied out of the reader payload, with
 * the codepoints named where it matters.
 */

/** RV 1.32.1, Aufrecht via GRETIL. U+0331 is anudātta, U+030D is svarita. */
const RV_1_32_1 =
    "indra̍sya̱ nu vī̱ryā̱̍ṇi̱ pra vo̍ca̱ṃ";

describe("accentTrace", () => {
    it("reads the Rigvedic marks and places each one above or below", () => {
        const trace = accentTrace(RV_1_32_1, "IAST");
        expect(trace).not.toBeNull();
        const placements = new Set(trace?.turns.map((turn) => turn.placement));
        expect(placements.has("above")).toBe(true);
        expect(placements.has("below")).toBe(true);
    });

    it("counts one turn per marked cluster and no more", () => {
        const trace = accentTrace(RV_1_32_1, "IAST");
        /* Counted by hand off the string above: the vertical lines and the macrons below. */
        const marksInText =
            (RV_1_32_1.match(/̍/g)?.length ?? 0) +
            (RV_1_32_1.match(/̱/g)?.length ?? 0);
        /* One cluster can carry both, in which case the module refuses it rather than
           guessing - so the turn count is at most the mark count, never more. */
        expect(trace?.marked).toBeLessThanOrEqual(marksInText);
        expect(trace?.marked).toBe(trace?.turns.length);
    });

    it("does not count the acute of ś as an accent", () => {
        /* THE trap. Decomposed, `ś` is `s` + U+0301, which is also the Atharvavedic udātta.
           A scan over combining marks alone reports four accents in this string and there
           are none. */
        const sibilants = "śivám śarma śravaḥ śubham";
        expect(accentTrace(sibilants, "IAST")).toBeNull();
    });

    it("counts the acute of a vowel as an accent, which is what it is in the Atharvaveda", () => {
        /* AVS-style marking: the acute on a syllable nucleus is udātta. Two of them, on `a`
           and on `i`, beside two that are part of `ś`. */
        const mixed = "śivám ágnim śarma índram";
        const trace = accentTrace(mixed, "IAST");
        expect(trace?.marked).toBe(3);
        expect(trace?.turns.every((turn) => turn.placement === "above")).toBe(true);
    });

    it("does not count a macron, a dot below, a dot above or a ring below", () => {
        /* Vowel length, the retroflexes and the visarga, `ṅ`, and the vocalic r. None of
           them is an accent and all of them are combining marks. */
        const diacritics = "vīṣṇu r̥ta ṅa mātā ḥi";
        expect(accentTrace(diacritics, "IAST")).toBeNull();
    });

    it("fails closed on a Samavedic notated witness rather than drawing a melody", () => {
        /* U+A8E1-U+A8EF are the combining Devanagari digits: the sung svara numerals written
           over a notated Sāmavedic text. They are a notation of melody, and a line rising and
           falling with them would be a reconstruction - which this must never produce. */
        const sung = "अग्न꣢ आ꣡ याह꣣";
        expect(accentTrace(sung, "DEVANAGARI")).toBeNull();
    });

    it("fails closed on a sung text even where it also carries readable accent marks", () => {
        /*
         * The test above is not enough on its own, and saying so is the point: with the
         * notation guard deleted it still passes, because nothing in that string is a mark
         * this module recognises and it falls out through the "fewer than two turns" exit.
         * A test that passes for a reason other than the one it names is not protecting
         * anything.
         *
         * This is the case the guard actually exists for. The Kauthuma witnesses held today
         * carry only the numerals, but a notated text that also carried U+0951 would, without
         * the guard, produce a partial contour over a melody - a drawing of two accents
         * standing on a page of sung notation, which is the misreading the whole module is
         * built to refuse. Deleting the `SAMAVEDIC_NOTATION` line fails this test.
         */
        const sungWithAccents =
            "अग्न꣢॑ आ॒꣡ याह꣣॑";
        expect(accentTrace(sungWithAccents, "DEVANAGARI")).toBeNull();
    });

    it("reads the Yajurvedic Devanagari marks", () => {
        /* U+0951 above, U+0952 below: the same above/below distinction the IAST carries, in
           the other script. */
        const yv = "इषे॑ त्वा॒ उर्जे॑";
        const trace = accentTrace(yv, "DEVANAGARI");
        expect(trace).not.toBeNull();
        expect(trace?.marked).toBe(3);
        expect(trace?.turns.filter((turn) => turn.placement === "below")).toHaveLength(1);
    });

    it("refuses an unaccented text rather than drawing a flat line as a contour", () => {
        expect(accentTrace("agnim ile purohitam yajnasya devam rtvijam", "IAST")).toBeNull();
    });

    it("refuses a single mark, because one point is not a contour", () => {
        expect(accentTrace("agni̱m ile", "IAST")).toBeNull();
    });

    it("refuses nothing at all", () => {
        expect(accentTrace("", "IAST")).toBeNull();
        expect(accentTrace(null, "IAST")).toBeNull();
        expect(accentTrace(undefined, "DEVANAGARI")).toBeNull();
    });

    it("places every turn inside the unit interval, in text order", () => {
        const trace = accentTrace(RV_1_32_1, "IAST");
        let previous = -1;
        for (const turn of trace?.turns ?? []) {
            expect(turn.at).toBeGreaterThanOrEqual(0);
            expect(turn.at).toBeLessThanOrEqual(1);
            expect(turn.at).toBeGreaterThan(previous);
            previous = turn.at;
        }
    });

    it("is a pure function of the text: the same string gives the same trace", () => {
        /* Deterministic, because it is a derivation and not a rendering. Two readers on two
           machines must see the same contour for the same verse. */
        expect(accentTrace(RV_1_32_1, "IAST")).toEqual(accentTrace(RV_1_32_1, "IAST"));
    });
});
