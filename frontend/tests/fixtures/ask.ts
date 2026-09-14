import type { AskResponse } from "@/lib/ask";

/** Shaped from a real POST /ask response, trimmed to what the UI reads. */
export const askResponseFixture = {
    answer:
        "Agni and Indra are invoked together in a number of Rigvedic hymns, most often in the " +
        "dual divinity form indrāgnī [E1][E2]. The pairing is attested across the collection " +
        "rather than confined to one mandala [E3].",
    status: "SUPPORTED",
    support_level: "MODERATE",
    citations: [],
    evidence: [
        {
            id: "E1",
            type: "PASSAGE",
            passage_key: "VG:RV:SAK:M01:S021:V001",
            citation: "RV 1.21.1",
            veda: "RV",
            sanskrit: "i̱hendrā̱gnī upa̍ hvaye̱ tayo̱rit stoma̍m uśmasi",
            translation: "Hither I call Indra and Agni; it is their praise that we desire.",
            knowledge_status: "SUPPORTED",
            qualifier:
                "A dual invocation records that the two were addressed together. It does not establish that either was subordinate to the other.",
        },
        {
            id: "E2",
            type: "PASSAGE",
            passage_key: "VG:RV:SAK:M06:S059:V002",
            citation: "RV 6.59.2",
            veda: "RV",
            sanskrit: "i̱ndrā̱gnī apā̍d i̱yaṁ pū̱rvāgā̍t",
            translation: "Indra and Agni, this footless one has come before.",
            knowledge_status: "SUPPORTED",
            qualifier: "A single verse. Frequency claims require the distribution channel.",
        },
        {
            id: "E3",
            type: "CORPUS_DISTRIBUTION",
            citation: "indrāgnī across the four collections",
            fact: "RV 24 passages, SV 3, YV 1, AV 6, counted at DEITY_CERTAIN only.",
            knowledge_status: "PARTIAL",
            qualifier:
                "Counts exclude ambiguous referents, so each figure is a lower bound rather than a total.",
        },
    ],
    entities: [
        {
            label: "Agni",
            entity_key: "VG:DEVATA:AGNIH",
            entity_type: "DEVATA",
            resolved: true,
            match_rank: "EXACT_LABEL",
        },
        {
            label: "Indra",
            entity_key: "VG:DEVATA:INDRAH",
            entity_type: "DEVATA",
            resolved: true,
            match_rank: "EXACT_LABEL",
        },
        { label: "Mitra-Varuna", resolved: false, asked_as: "mitravaruna" },
    ],
    related_questions: [
        "Where else is the dual divinity form used in the Rigveda?",
        "Which hymns are dedicated to Indra and Agni jointly?",
    ],
    caveats: [
        {
            text: "Counts reported here exclude referents graded ambiguous, so every figure is a lower bound.",
            source: "certainty_scope",
        },
    ],
    retrieval_summary: {
        channels_used: ["PASSAGE_SEARCH", "CORPUS_DISTRIBUTION"],
        channels_empty: ["FORMULA_FAMILY"],
        intents: ["ENTITY_RELATIONSHIP"],
        entities_resolved: ["Agni", "Indra"],
        entities_unresolved: ["Mitra-Varuna"],
        veda_scope: "ALL",
        evidence_count: 3,
        planner_ms: 41,
        retrieval_ms: 812,
        synthesis_ms: 104_318,
        total_ms: 105_171,
    },
    interpretive_content_present: false,
    llm: { provider: "groq", model: "llama-3.3-70b-versatile" },
} as unknown as AskResponse;

/**
 * The same answer, stopped at the output cap.
 *
 * The service does not send a boolean for this. It appends a caveat whose `source` is
 * `generation_truncated`, downgrades `status` to PARTIAL and holds `support_level` at LIMITED
 * or below, so the fixture reproduces all three rather than only the one the UI reads.
 */
export const truncatedResponseFixture = {
    ...askResponseFixture,
    status: "PARTIAL",
    support_level: "LIMITED",
    answer:
        "Agni and Indra are invoked together in a number of Rigvedic hymns, most often in the " +
        "dual divinity form indrāgnī [E1][E2]. The distribution across the other three " +
        "collections is uneven, with the Atharvaveda recording",
    caveats: [
        {
            text: "The generated response reached its output limit and may be incomplete. The supporting VedaGraph evidence remains available below.",
            source: "generation_truncated",
        },
        ...askResponseFixture.caveats,
    ],
} as unknown as AskResponse;
