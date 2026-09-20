/**
 * The Accent Trace: a picture of the accent marks this edition prints, and nothing else.
 *
 * ## What it is
 *
 * The selected text is segmented into grapheme clusters. Every cluster that carries a
 * recognised accent mark becomes one turn on a line: a mark printed *above* the letter turns
 * the line up, a mark printed *below* turns it down, and an unmarked cluster leaves the line
 * on the baseline. That is the whole derivation. It is deterministic, it is a pure function
 * of the string the reader is looking at, and it runs in about a tenth of a millisecond.
 *
 * ## What it is not, stated here because the UI must never imply otherwise
 *
 *   It is **not measured pitch.** Nothing here has heard the recording.
 *   It is **not a reconstructed melody.** No interval, no scale, no duration is claimed.
 *   It is **not word-level or syllable-level audio timing.** The horizontal axis is position
 *   in the *text*, not position in the *recording*, and the two are not the same axis. A
 *   playhead may ADVANCE across the trace because the reader is listening to a recording of
 *   this verse, and that is the only relationship asserted.
 *   It is **not phonetic analysis.** Whether a mark above means udatta or svarita differs by
 *   edition and by corpus, and this module does not adjudicate that. It records where the
 *   mark is printed.
 *
 * ## Why classification is by position and not by accent name
 *
 * The three corpora that carry accents do not mark them the same way. The Rigvedic IAST here
 * marks anudatta with a macron below (U+0331) and svarita with a vertical line above
 * (U+030D), leaving udatta unmarked. The Atharvavedic IAST marks with an acute (U+0301). The
 * Yajurvedic Devanagari marks with U+0951 above and U+0952 below. Mapping all of those onto
 * one three-way pitch vocabulary would be an editorial judgement about four different
 * printing conventions, made silently, in a drawing. So the trace says only what it can see:
 * this mark is above the letter, that one is below.
 *
 * ## The trap this module is written around
 *
 * **U+0301 is both the udatta and the acute of `s`.** Decomposed, `ś` is `s` + U+0301, and a
 * naive scan over combining marks counts every palatal sibilant in the Atharvaveda as an
 * accented syllable. Measured over six AV verses: 78 acutes, of which 5 sit on `s` and 73 on
 * a vowel. So an acute is an accent only when its base is a vowel, which is also the correct
 * rule linguistically - a Vedic accent falls on a syllable nucleus, and `ś` is not one.
 *
 * ## Failing closed
 *
 * `accentTrace` returns null rather than a degraded trace when it cannot be sure, and the
 * player draws no contour at all in that case. Null is returned for: an empty text; a text
 * with no recognised marks; a text with only one mark, which is a point and not a contour;
 * and a Samavedic notated witness, whose U+A8E1-U+A8EF combining Devanagari digits are the
 * sung svara *numerals* - turning those into a rising and falling line would be drawing a
 * melody, which is the one thing this must not do.
 */

/** Where a mark is printed relative to its letter. The only distinction this module draws. */
export type MarkPlacement = "above" | "below";

export type AccentTurn = {
    /** Position along the text, from 0 to 1: the index of the marked cluster over the total. */
    at: number;
    placement: MarkPlacement;
};

export type AccentTraceResult = {
    turns: AccentTurn[];
    /** Grapheme clusters in the text. The denominator of every `at`. */
    clusters: number;
    /** How many of them carry a mark. */
    marked: number;
    /** The script the marks were read in, for the disclosure. */
    script: "IAST" | "DEVANAGARI";
};

/**
 * Marks printed above the letter.
 *
 * U+0301 is conditional and is handled separately; the rest are unambiguous.
 * U+030D vertical line above, U+030E double vertical line above, U+0951 the Devanagari
 * stress sign written above.
 */
const ABOVE = new Set(["̍", "̎", "॑"]);

/** Marks printed below the letter. U+0331 macron below, U+0952 the Devanagari sign below. */
const BELOW = new Set(["̱", "॒"]);

/**
 * Marks that are part of a letter and are never an accent.
 *
 * Listed rather than inferred, because every one of them was a false turn in an earlier
 * draft: the macron is vowel length, the dot below builds the retroflexes and the visarga
 * and the anusvara, the dot above builds `n` with dot above, the ring below builds the
 * vocalic r in the alternative transliteration, and the candrabindu is nasalisation. None of
 * them says anything about accent.
 */
const NOT_AN_ACCENT = new Set([
    "̄", // macron: vowel length
    "̣", // dot below: retroflex, visarga, anusvara
    "̇", // dot above
    "̥", // ring below: vocalic r
    "̐", // candrabindu
    "्", // Devanagari virama
]);

/**
 * The Samavedic sung notation.
 *
 * U+A8E0 to U+A8FF are the combining Devanagari digits and marks used to write the svara
 * numerals over a notated Samavedic text. They are a musical notation, and a line rising and
 * falling with them would be a drawn melody. Their presence fails the whole text closed.
 */
const SAMAVEDIC_NOTATION = /[꣠-ꣿ]/u;

/** A vowel base, in IAST. An acute is an accent only over one of these. */
const IAST_VOWEL = /[aeiouāīūṛṝḷḹ]/iu;

/**
 * Split into grapheme clusters: a base character plus every combining mark that follows it.
 *
 * `Intl.Segmenter` would do this and is not used, for two reasons. It is not available in
 * every runtime this renders in, and a silent fallback to something coarser is how a
 * validator ends up passing by not looking. And it is not needed: the only clustering this
 * has to get right is "a letter and its marks", which `\p{M}` states exactly.
 */
function clusters(text: string): string[] {
    const out: string[] = [];
    // A non-mark character, followed by any run of combining marks.
    for (const match of text.matchAll(/\P{M}\p{M}*/gu)) out.push(match[0]);
    return out;
}

/**
 * The placement of the accent on one cluster, or null if it carries none.
 *
 * Returns null - rather than guessing - for a cluster carrying both an above and a below
 * mark. No text in this corpus does that, and if one ever arrives it is a question about the
 * edition rather than something a drawing should resolve.
 */
function placementOf(cluster: string): MarkPlacement | null {
    let above = false;
    let below = false;
    const base = cluster[0];

    for (const ch of cluster.slice(1)) {
        if (NOT_AN_ACCENT.has(ch)) continue;
        if (ABOVE.has(ch)) above = true;
        else if (BELOW.has(ch)) below = true;
        else if (ch === "́" || ch === "́") {
            /* The acute. An accent over a vowel; part of the letter over anything else. */
            if (IAST_VOWEL.test(base)) above = true;
        }
    }

    if (above && below) return null;
    if (above) return "above";
    if (below) return "below";
    return null;
}

/** Above this many marks the text is not a verse and something upstream is wrong. */
const MAX_MARKS = 300;

export function accentTrace(
    text: string | null | undefined,
    script: "IAST" | "DEVANAGARI",
): AccentTraceResult | null {
    if (!text) return null;
    // A notated Samavedic witness is a melody written in numerals. See SAMAVEDIC_NOTATION.
    if (SAMAVEDIC_NOTATION.test(text)) return null;

    const parts = clusters(text);
    if (parts.length < 2) return null;

    const turns: AccentTurn[] = [];
    parts.forEach((cluster, index) => {
        const placement = placementOf(cluster);
        if (!placement) return;
        turns.push({ at: index / (parts.length - 1), placement });
    });

    /* One mark is a point, not a contour, and nothing is drawn for it. */
    if (turns.length < 2 || turns.length > MAX_MARKS) return null;

    return { turns, clusters: parts.length, marked: turns.length, script };
}
