#!/usr/bin/env node
/**
 * `FALLBACK_COMPLETENESS` must still agree with the backend it is a copy of.
 *
 * The constant in `src/lib/api.ts` is the frozen certified state that `loadCompleteness()`
 * serves when `/api/v1/completeness` cannot be reached. That is a reasonable thing to have and
 * a dangerous thing to leave unchecked: measured at the start of this pass, the route did not
 * exist on the running backend at all - it had been added one commit earlier and the server
 * predated it - so every figure on the homepage, /vedas, /limits and /sources was coming from
 * this literal, and no surface said so. A stale fallback is indistinguishable from live data
 * that happens to be wrong.
 *
 * So this fetches the live endpoint and compares the fields that carry a claim. It fails when
 * they diverge, and it also fails when the endpoint cannot be reached, because a check that
 * quietly passes when it could not run is worse than no check: it converts "unverified" into
 * "verified" on the way past.
 *
 * Run it against a live stack:  pnpm audit
 * Point it elsewhere with:      VEDAGRAPH_API_URL=http://host:port
 */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const apiBase = process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000";
const url = `${apiBase.replace(/\/$/, "")}/api/v1/completeness`;

/**
 * The constant, read out of the TypeScript source rather than imported.
 *
 * `api.ts` is a module full of Next-flavoured imports and this is a plain node script, so the
 * object literal is cut out and evaluated on its own. Brittle in exactly one way - if the
 * declaration is renamed - and that failure is loud, which is the acceptable kind.
 */
function fallbackFromSource() {
    const source = readFileSync(join(here, "..", "src", "lib", "api.ts"), "utf8");
    const marker = "export const FALLBACK_COMPLETENESS: CompletenessResponse = ";
    const start = source.indexOf(marker);
    if (start < 0) {
        throw new Error(
            "audit-completeness-fallback: FALLBACK_COMPLETENESS is not declared in src/lib/api.ts. " +
                "If it was renamed or removed, update this audit with it.",
        );
    }
    const open = source.indexOf("{", start);
    let depth = 0;
    let end = -1;
    for (let i = open; i < source.length; i += 1) {
        const ch = source[i];
        if (ch === "{") depth += 1;
        else if (ch === "}") {
            depth -= 1;
            if (depth === 0) {
                end = i + 1;
                break;
            }
        }
    }
    if (end < 0) throw new Error("audit-completeness-fallback: could not read the object literal.");
    return new Function(`return (${source.slice(open, end)});`)();
}

/**
 * Fields that must be present on both sides and must agree, named exactly.
 *
 * The first version of this list guessed at four of them -- `translations.total_released`,
 * `dedicated_translations`, `reused_renderings`, `samaveda_notation.validated_witnesses` -- and
 * skipped every one with an `!== undefined` guard, so the audit printed "matches on 18 claims"
 * while silently comparing neither the translation typology nor the notation figures. A
 * validator that skips is worse than none: it converts "not checked" into "checked and fine".
 *
 * So the names are asserted rather than probed. A key missing from both payloads is a failure
 * of this file, and it says so.
 */
const REQUIRED = {
    "": ["certified_release_commit", "as_of_date", "total_canonical_mantras"],
    translations: [
        "total_mantras",
        "total_dedicated_english",
        "total_range_covered",
        "total_reused_rendering",
        "total_non_english",
        "total_uncovered",
    ],
    samaveda_notation: [
        "canonical_corpus_mantras",
        "validated_notation_witnesses",
        "unaligned_withheld_verses",
        "musicalized_as_edges",
        "gana_works_modeled",
    ],
    audio: ["released_catalogue_records"],
    ask_benchmark: [
        "total_questions",
        "supported_correct",
        "partial_correct",
        "insufficient_evidence_refused",
        "misleading",
        "hallucinated",
    ],
};

/**
 * The fields that carry a claim, flattened.
 *
 * Not a deep equality over the whole payload: the backend is free to add a field or reword a
 * caveat without that being a divergence a reader would notice. These are the numbers and the
 * identities that appear on product pages, so a disagreement in any of them means a page is
 * printing something the service does not say.
 */
function claims(state) {
    const out = {};
    for (const [block, fields] of Object.entries(REQUIRED)) {
        const source = block === "" ? state : (state[block] ?? {});
        for (const field of fields) {
            out[block === "" ? field : `${block}.${field}`] = source[field];
        }
    }
    for (const corpus of state.corpora ?? []) {
        out[`corpus.${corpus.veda}.canonical_mantras`] = corpus.canonical_mantras;
        out[`corpus.${corpus.veda}.recension`] = corpus.recension;
    }
    for (const [veda, item] of Object.entries(state.translations?.by_veda ?? {})) {
        out[`translations.${veda}.dedicated_english`] = item.dedicated_english;
        out[`translations.${veda}.reused_rendering`] = item.reused_rendering;
        out[`translations.${veda}.has_own_dedicated_english`] = item.has_own_dedicated_english;
    }
    for (const [veda, count] of Object.entries(state.audio?.released_by_veda ?? {})) {
        out[`audio.released_by_veda.${veda}`] = count;
    }
    for (const [tier, count] of Object.entries(state.audio?.released_by_tier ?? {})) {
        out[`audio.released_by_tier.${tier}`] = count;
    }
    return out;
}

/** Keys neither payload carries. The audit believes it checked them; it did not. */
function unreachable(a, b) {
    return Object.keys(a).filter((key) => a[key] === undefined && b[key] === undefined);
}

async function main() {
    const fallback = fallbackFromSource();

    let live;
    try {
        const response = await fetch(url, { signal: AbortSignal.timeout(15_000) });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        live = await response.json();
    } catch (reason) {
        console.error(`FAIL  ${url} could not be read: ${reason.message ?? reason}`);
        console.error(
            "      The fallback could not be checked against anything, which is a failure and " +
                "not a pass. Start the API (uvicorn vedagraph.api.app:app) and run this again.",
        );
        process.exit(1);
    }

    const a = claims(fallback);
    const b = claims(live);
    const keys = [...new Set([...Object.keys(a), ...Object.keys(b)])].sort();

    const missing = unreachable(a, b);
    if (missing.length > 0) {
        console.error(
            `FAIL  ${missing.length} claim(s) exist in neither the fallback nor the live payload, ` +
                "so they were compared as undefined against undefined and passed without being read:",
        );
        for (const key of missing) console.error(`      ${key}`);
        console.error("      Fix the names in REQUIRED, or remove them if the field is gone.");
        process.exit(1);
    }

    const diverged = keys.filter((key) => JSON.stringify(a[key]) !== JSON.stringify(b[key]));

    if (diverged.length > 0) {
        console.error(`FAIL  FALLBACK_COMPLETENESS disagrees with ${url} on ${diverged.length} claim(s):`);
        for (const key of diverged) {
            console.error(`      ${key}: fallback ${JSON.stringify(a[key])} vs live ${JSON.stringify(b[key])}`);
        }
        console.error(
            "      Update FALLBACK_COMPLETENESS in src/lib/api.ts to the certified state the " +
                "backend now reports, or fix the backend. Do not relax this audit.",
        );
        process.exit(1);
    }

    console.log(`OK    FALLBACK_COMPLETENESS matches ${url} on ${keys.length} claims.`);
}

await main();
