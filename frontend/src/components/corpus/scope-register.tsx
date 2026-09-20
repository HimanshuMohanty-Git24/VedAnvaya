import Link from "next/link";
import { vedaNames, workSlugs, type Work } from "@/lib/api";

/**
 * What recension of each collection this product holds, and what it does not.
 *
 * ## Why this is a register and not a tree
 *
 * The obvious drawing is a tree: a Veda at the root, its śākhās branching beneath it, the
 * held one in ink and the rest ghosted. It would be the wrong drawing, and not slightly.
 *
 * A tree asserts descent. Drawn from the Rigveda down to Śākala and Bāṣkala it says those
 * two are siblings born of a common parent, and the relationship between the śākhās of a
 * Veda is a live question in the scholarship that this build has no evidence about and no
 * business settling in a diagram. Worse, the exclusions here are not all śākhās: the
 * Rigvedic row holds a second recension beside the Brāhmaṇas, the Āraṇyakas and the
 * Upaniṣads, which belong to different textual layers entirely. A tree would draw four
 * different kinds of thing as four branches of one kind.
 *
 * So: a register. One ruled block per collection, the held edition first and in ink with
 * its measured extent, and beneath it every corpus the registry records this edition as not
 * addressing, subdued. The claim is "this build holds this and not those", which is a scope
 * statement and is exactly what the data supports.
 *
 * ## Where every line comes from
 *
 * `work.recension` and `work.mantra_count` from `/works`, and `work.excluded_corpora` from
 * the same record - the registry's own enumeration, not a list typed beside the design.
 * `EXCLUDED_LABEL` maps a registry code to the words a reader of the tradition would use and
 * falls through to the code spelled out, so a corpus added to the registry tomorrow appears
 * here without anyone remembering to add it.
 *
 * ## An exclusion is not an apology
 *
 * The held row is the loud one: ink, medium weight, its figure beside it. The excluded rows
 * are quiet and they are *present*, because a reader who cannot see what an edition leaves
 * out cannot judge an absence measured in it. Neither is drawn as a fault.
 */

/** Corpus identifiers, in the words a reader of the tradition would use. */
const EXCLUDED_LABEL: Record<string, string> = {
    SECOND_RIGVEDIC_RECENSION: "The Bāṣkala recension",
    RIGVEDIC_BRAHMANA: "The Rigvedic Brāhmaṇas",
    RIGVEDIC_ARANYAKA: "The Rigvedic Āraṇyakas",
    ASHVALAYANA_SAMHITA: "The Āśvalāyana Saṃhitā",
    UPANISAD: "The Upaniṣads",
    ATHARVAVEDA_PAIPPALADA_RECENSION: "The Paippalāda recension",
    GOPATHA_BRAHMANA: "The Gopatha Brāhmaṇa",
    KRISHNA_YAJURVEDA_TAITTIRIYA: "The Taittirīya Saṃhitā",
    KRISHNA_YAJURVEDA_KATHAKA: "The Kāṭhaka Saṃhitā",
    KRISHNA_YAJURVEDA_MAITRAYANI: "The Maitrāyaṇī Saṃhitā",
    KRISHNA_YAJURVEDA_KAPISTHALA: "The Kapiṣṭhala Saṃhitā",
    SHUKLA_YAJURVEDA_KANVA_RECENSION: "The Kāṇva recension",
    SATAPATHA_BRAHMANA: "The Śatapatha Brāhmaṇa",
    SAMAVEDA_GRAMAGEYA_GANA: "The Grāmageyagāna",
    SAMAVEDA_ARANYAKAGEYA_GANA: "The Āraṇyakageyagāna",
    SAMAVEDA_ARANYAGANA: "The Āraṇyagāna",
    SAMAVEDA_UHAGANA: "The Ūhagāna",
    SAMAVEDA_UHA_GANA: "The Ūhagāna",
    SAMAVEDA_UHYAGANA: "The Ūhyagāna",
    SAMAVEDA_UHYA_GANA: "The Ūhyagāna",
    SECOND_SAMAVEDIC_RECENSION: "The Jaiminīya and Rāṇāyanīya recensions",
    SAMAVEDIC_BRAHMANA: "The Sāmavedic Brāhmaṇas",
};

/**
 * The recension each edition holds, in words.
 *
 * `work.recension` from the service is the registry's short code - "KAU", "VSM", "SAK",
 * "SAU" - which is the right thing for a key and unreadable as the first line of a scope
 * statement. This table was previously duplicated on /limits and on /vedas; it lives here
 * now, in the one component that renders it, and falls back to whatever the service says
 * so a fifth edition would appear with its code rather than not at all.
 */
const RECENSION: Record<string, string> = {
    RV: "Śākala recension, Saṃhitā only",
    SV: "Kauthuma recension, ārcika only",
    YV: "White Yajurveda, Vājasaneyi Mādhyandina recension",
    AV: "Śaunaka recension, Saṃhitā only",
};

/**
 * Which textual layer a registry code names.
 *
 * Printed beside the label because the exclusions of one collection are not all of one
 * kind: for the Rigveda they are a second recension of the same Saṃhitā *and* three later
 * layers, and running them together as one list of "not held" flattens a distinction the
 * registry codes themselves carry.
 */
function layerOf(code: string): string {
    /*
     * The Kṛṣṇa Yajurveda śākhās are recensions of the Yajurveda and are coded without the
     * word: `KRISHNA_YAJURVEDA_TAITTIRIYA` rather than `..._SAMHITA` or `..._RECENSION`. Read
     * by the two generic tests below they came out as "outside this edition", which is true
     * and says nothing - and on the Yajurvedic row, where four of the seven exclusions are
     * exactly this case, it said nothing four times.
     */
    if (code.startsWith("KRISHNA_YAJURVEDA")) return "another recension";
    if (code.includes("RECENSION") || code.endsWith("_SAMHITA")) return "another recension";
    if (code.includes("BRAHMANA")) return "a Brāhmaṇa";
    if (code.includes("ARANYAKA")) return "an Āraṇyaka";
    if (code === "UPANISAD") return "a later layer";
    if (code.includes("GANA")) return "a song collection";
    return "outside this edition";
}

const DEVANAGARI: Record<string, string> = {
    RV: "ऋग्वेद",
    SV: "सामवेद",
    YV: "यजुर्वेद",
    AV: "अथर्ववेद",
};

export function ScopeRegister({
    works,
    /** Link each collection's name to its own page. Off on /vedas, where it already is one. */
    link = true,
}: {
    works: Work[];
    link?: boolean;
}) {
    return (
        <ul className="va-scope">
            {works.map((work) => {
                const code = work.veda ?? "";
                const name = vedaNames[code] ?? work.traditional_name ?? code;
                const excluded = work.excluded_corpora ?? [];
                return (
                    <li className="va-scope-veda" key={work.work_id}>
                        <div className="va-scope-name">
                            {link ? (
                                <strong>
                                    <Link href={`/vedas/${workSlugs[code] ?? ""}`}>{name}</Link>
                                </strong>
                            ) : (
                                <strong>{name}</strong>
                            )}
                            {DEVANAGARI[code] && (
                                <span lang="sa">{DEVANAGARI[code]}</span>
                            )}
                        </div>
                        <ul className="va-scope-lines">
                            <li className="va-scope-line" data-held="true">
                                <span aria-hidden="true" className="va-scope-mark" />
                                <span className="va-scope-text">
                                    <strong>
                                        {RECENSION[code] ??
                                            work.recension ??
                                            "Recension not stated"}
                                    </strong>
                                    <small>
                                        <span className="va-scope-state">Held</span>
                                        {work.mantra_count != null
                                            ? ` · ${work.mantra_count.toLocaleString("en-GB")} mantras, each with a canonical key`
                                            : ""}
                                    </small>
                                </span>
                            </li>
                            {excluded.map((corpus) => (
                                <li className="va-scope-line" data-held="false" key={corpus}>
                                    <span aria-hidden="true" className="va-scope-mark" />
                                    <span className="va-scope-text">
                                        <strong>
                                            {EXCLUDED_LABEL[corpus] ??
                                                corpus.toLowerCase().replaceAll("_", " ")}
                                        </strong>
                                        <small>
                                            <span className="va-scope-state">Not held</span>
                                            {` · ${layerOf(corpus)}`}
                                        </small>
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </li>
                );
            })}
        </ul>
    );
}
