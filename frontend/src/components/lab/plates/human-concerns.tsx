import { LoadFailure } from "@/components/empty-state";
import {
    BarTable,
    CorpusStrip,
    SmallMultiple,
    type CorpusFigure,
    type Datum,
} from "@/components/lab/marks";
import {
    PlateFigure,
    PlateHandoff,
    PlateHeader,
    PlateLabel,
    PlateTakeaway,
} from "@/components/lab/plate";
import { encoded, load, type AvConcerns, type EntityListResponse } from "@/lib/api";
import { conditionNote } from "@/lib/knowledge";
import { CORPORA, count, PLATES_BY_SLUG, type CorpusCode } from "@/lib/lab";

/**
 * What people asked for.
 *
 * The whole design of this plate is one refusal. An earlier version of this question, in the
 * project's own benchmark, asked what illnesses the corpus addresses and answered it with a
 * ranked list whose top entries were demons: of the 718 mention edges reaching a Condition,
 * 314 reach a THREAT. The registry types every condition, and here the types become the
 * layout — afflictions and threats are two panels with two headings, on two axes, and there
 * is no view of this plate in which they form one list.
 *
 * The second refusal is quieter. These are counts of verses in which a registered Sanskrit
 * alias occurs. They are lexical minima and they are not diagnoses: `takman` is a Sanskrit
 * word for a fever, not an identification of a disease, and nothing here maps a Vedic
 * condition onto a modern one.
 */

const plate = PLATES_BY_SLUG["human-concerns"];

const SHOWN = 12;

const PREDICATE_COPY: Record<string, { label: string; note: string }> = {
    PROTECTS_FROM: {
        label: "Guarded against",
        note: "The verse asks for protection from this.",
    },
    TREATS: {
        label: "Treated",
        note: "The verse is directed at this as something to be dealt with.",
    },
    ADDRESSES_CONCERN: {
        label: "Asked for",
        note: "The verse addresses this as a thing wanted.",
    },
};

export async function HumanConcernsPlate() {
    const [concernsResult, conditionsResult] = await Promise.all([
        load<AvConcerns>(`/insights/atharvaveda/concerns?limit=25`),
        load<EntityListResponse>("/entities/condition?limit=40"),
    ]);
    if (!concernsResult.ok) {
        return <LoadFailure message={concernsResult.message} status={concernsResult.status} />;
    }

    const data = concernsResult.data;
    /* The protection rows carry a label but no key, so the condition index is read once and
       used to make both panels' rows clickable rather than leaving one of them a dead end. */
    const keyByLabel = new Map(
        (conditionsResult.ok ? (conditionsResult.data.items ?? []) : []).map((item) => [
            item.display_label,
            item.id,
        ]),
    );
    const conditionHref = (label: string | null | undefined) => {
        const id = label ? keyByLabel.get(label) : undefined;
        return id ? `/entities/condition/${encoded(id)}` : undefined;
    };

    const afflictions = (data.afflictions ?? []).slice(0, SHOWN);
    const threats = (data.protection_and_treatment ?? []).filter(
        (row) => row.condition_kind === "THREAT",
    );
    const causes = (data.protection_and_treatment ?? []).filter(
        (row) => row.condition_kind === "PATHOGEN_OR_CAUSE",
    );
    const concerns = data.concerns ?? [];
    const rites = data.social_rites ?? [];
    const measured = data.coverage?.measured ?? {};

    const afflictionRows: Datum[] = afflictions.map((row) => ({
        key: row.entity_key ?? row.label ?? "",
        label: row.label ?? "",
        note: row.vedas_reached
            ? `named in ${row.vedas_reached} of 4 collections`
            : "no collection reached",
        value: row.total_mantras ?? null,
        absence: "no alias matched",
        href: conditionHref(row.label),
    }));

    /*
     * The takeaway's arithmetic.
     *
     * "Every concern occurs at a higher rate in the Atharvaveda" is the kind of claim that is
     * true when it is written and false three months later, so it is counted here against the
     * response rather than asserted in the paragraph.
     */
    const wanted = [...(data.concerns ?? []), ...(data.social_rites ?? [])];
    const avOverRv = wanted.filter((row) => {
        const per = row.per_1000_by_veda ?? {};
        return (per.AV ?? 0) > (per.RV ?? 0);
    });
    const avOnly = wanted.filter((row) => {
        const per = row.per_1000_by_veda ?? {};
        return (
            (per.AV ?? 0) > 0 && !CORPORA.some(({ code }) => code !== "AV" && (per[code] ?? 0) > 0)
        );
    });
    const topAffliction = (data.afflictions ?? [])[0];
    const afflictionRatio = (() => {
        const per = topAffliction?.per_1000_by_veda ?? {};
        return per.AV && per.RV ? per.AV / per.RV : null;
    })();

    const threatRows: Datum[] = threats.map((row) => ({
        key: `${row.target}-${row.predicate}`,
        label: row.target ?? "",
        note: PREDICATE_COPY[row.predicate ?? ""]?.label.toLowerCase(),
        value: row.passages ?? null,
        absence: "no edge of this predicate",
        href: conditionHref(row.target),
    }));

    return (
        <>
            <PlateHeader
                lede="The Atharvaveda is the collection that talks about ordinary life: a fever, a rival, a difficult birth, a new house, cattle that should thrive. Reading what it addresses means keeping two things apart that a ranked list would merge — the things people suffered, and the things they believed were doing it to them."
                plate={plate}
            />

            <div className="va-plate-note">
                <strong>A demon is not a disease.</strong>
                <p>
                    The registry types every condition as an affliction, a threat, or a named cause,
                    and the three are never counted together here. An earlier version of this
                    question did merge them and returned demons, sorcery and worms at the top of a
                    list of illnesses. That is why the two panels below have two headings and two
                    scales, and why nothing on this page offers to combine them.
                </p>
            </div>

            <PlateFigure
                description={`${count(measured.afflictions)} afflictions and ${threats.length} threats are recorded in this build. They are drawn side by side and never on the same axis: the left panel is what is suffered, the right is what the verses guard against.`}
                footnote={
                    <>
                        Both panels count verses in which a registered Sanskrit alias occurs. These
                        are lexical minima — the true figures are higher, because the registry does
                        not carry every alias — and they are never diagnoses.
                    </>
                }
                id="afflictions-and-threats"
                title="What is suffered, and what is guarded against"
            >
                <div className="va-panels">
                    <section className="va-panel">
                        <header>
                            <h3>Afflictions</h3>
                            <p>
                                {conditionNote("AFFLICTION")} Counted across all four collections.
                            </p>
                        </header>
                        <BarTable
                            caption="Verses naming each affliction, across all four collections"
                            headers={["Affliction", "", "Verses"]}
                            rows={afflictionRows}
                        />
                    </section>

                    <section className="va-panel">
                        <header>
                            <h3>Threats</h3>
                            <p>{conditionNote("THREAT")} Counted from the protection edges.</p>
                        </header>
                        <BarTable
                            caption="Verses asking for protection from each threat"
                            headers={["Threat", "", "Verses"]}
                            rows={threatRows}
                        />
                        {causes.length ? (
                            <p className="va-panel-note">
                                A third kind sits between them:{" "}
                                {causes.map((row) => row.target).join(", ")} — named by the texts as
                                a cause. {conditionNote("PATHOGEN_OR_CAUSE")}
                            </p>
                        ) : null}
                    </section>
                </div>
            </PlateFigure>

            <PlateFigure
                description="The seven recorded human concerns and the five social rites, each across all four collections, at the rate per 1,000 verses of the collection. This is the form in which the Atharvaveda's distinctiveness is visible without the size difference doing the work."
                footnote={
                    <>
                        The mention layer reaches all four collections, so a collection with no
                        figure here genuinely had no match rather than having no layer. One row is
                        worth the caution: the Atharvaveda&rsquo;s marriage hymn redacts a Rigvedic
                        one, so the Rigvedic share of marriage vocabulary is real rather than noise.
                    </>
                }
                id="concerns-by-corpus"
                title="Who asks for what"
            >
                <div className="va-multiples">
                    {[...concerns, ...rites].map((row) => {
                        const per = row.per_1000_by_veda ?? {};
                        const raw = row.by_veda;
                        const figures = Object.fromEntries(
                            CORPORA.map(({ code }) => {
                                const key = code.toLowerCase() as "rv" | "sv" | "yv" | "av";
                                const counted = raw?.[key];
                                const figure: CorpusFigure = {
                                    value: typeof counted === "number" ? (per[code] ?? null) : null,
                                    absence: "no match",
                                };
                                return [code, figure];
                            }),
                        ) as Record<CorpusCode, CorpusFigure>;
                        return (
                            <SmallMultiple
                                definition={`${count(row.total_mantras)} verses across the corpus. ${
                                    row.kind === "SOCIAL_RITE"
                                        ? "A social rite."
                                        : "A human concern."
                                }`}
                                key={row.entity_key ?? row.label ?? ""}
                                title={row.label ?? ""}
                            >
                                <CorpusStrip
                                    caption={`Verses naming ${row.label} per 1,000 verses, by collection`}
                                    figures={figures}
                                    perThousand
                                    unit="per 1,000"
                                />
                            </SmallMultiple>
                        );
                    })}
                </div>
            </PlateFigure>

            <PlateTakeaway
                interpretation={
                    <>
                        The rates suggest a collection organised around what a household needs
                        rather than around the sacrifice, which is close to how the Atharvaveda is
                        usually described. What these counts cannot tell you is whether that
                        reflects the lives of its reciters or the editorial purpose of the
                        collection, and those are different claims.
                    </>
                }
                observation={
                    <>
                        {count(avOverRv.length)} of the {count(wanted.length)} concerns and social
                        rites in this registry occur at a higher rate in the Atharvaveda than in the
                        Rigveda
                        {avOnly.length
                            ? `, and ${avOnly.length === 1 ? "one of them" : `${count(avOnly.length)} of them`} — ${avOnly.map((row) => row.label).join(", ")} — was matched in no other collection at all`
                            : ""}
                        . The afflictions behave the same way: {topAffliction?.label}
                        {afflictionRatio
                            ? ` is named at about ${afflictionRatio.toFixed(0)} times the Rigvedic rate`
                            : " leads the list"}
                        .
                    </>
                }
            />

            <PlateLabel plate={plate} />

            <PlateHandoff
                links={[
                    {
                        href: "/explore/atharvaveda",
                        label: "The Atharvaveda in full",
                        note: "Every condition, concern and rite, with the verses behind each",
                    },
                    {
                        href: "/entities/condition",
                        label: "All 26 conditions",
                        note: "Each one typed as an affliction, a threat or a named cause",
                    },
                    {
                        href: "/vedas/atharvaveda",
                        label: "Read the Atharvaveda",
                        note: "Twenty kandas, Saunaka recension, with the Paippalada absent",
                    },
                    {
                        href: "/limits",
                        label: "What this layer cannot answer",
                        note: "Including why there is no healing entity in the registry",
                    },
                ]}
            />
        </>
    );
}
