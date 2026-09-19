import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";
import { CopyButton } from "@/components/copy-button";
import { encoded, type ParallelView, type Reader, vedaNames } from "@/lib/api";
import {
    evidenceBasisCopy,
    matchLevelCopy,
    parallelKindCopy,
    trustTierCopy,
} from "@/lib/knowledge";
import { KnowledgeStatus } from "./status";

type Summary = ParallelView["passage"];

type TranslationItem = NonNullable<Reader["translations"]["items"]>[number];

/*
 * This is the one view where a reused rendering and the passage it was taken from are on
 * screen together, so it is the view where presenting it as the target corpus's own
 * translation is worst: the reader is looking at the Rigvedic verse on the left and the
 * same English on the right, and would conclude the Samaveda has its own translation of
 * it. The column therefore takes the whole translation item and not just its text.
 */
function TextColumn({
    citation,
    veda,
    href,
    text,
    script,
    translation,
}: {
    citation: string;
    veda: string;
    href: string;
    text?: string | null;
    script?: string | null;
    translation?: TranslationItem | null;
}) {
    return (
        <div className="comparison-column">
            <div className="comparison-head">
                <span className="veda-chip">{vedaNames[veda] ?? veda}</span>
                <Link href={href}>
                    {citation}
                    <ArrowRight size={14} aria-hidden="true" />
                </Link>
            </div>
            {text ? (
                <>
                    <p
                        className={script === "DEVANAGARI" ? "sanskrit devanagari" : "sanskrit"}
                        lang="sa"
                    >
                        {text}
                    </p>
                    <CopyButton text={text} />
                </>
            ) : (
                <KnowledgeStatus
                    status="INSUFFICIENT_EVIDENCE"
                    note="No displayable Sanskrit surface was returned for this passage."
                />
            )}
            <div
                className="comparison-translation"
                data-coverage={translation?.coverage_kind}
                data-language={translation?.language}
            >
                {translation ? (
                    <>
                        <blockquote lang={translation.language}>{translation.text}</blockquote>
                        <cite>{translation.translator}</cite>
                        {translation.disclosure && (
                            <p className="comparison-translation-note">{translation.disclosure}</p>
                        )}
                    </>
                ) : (
                    /* The same sentence the reader page prints, so the two views do not
                       describe one state in two registers. */
                    <p className="muted">No English rendering is linked to this passage.</p>
                )}
            </div>
        </div>
    );
}

/** Two passages placed beside one another, with the surface that actually matched. */
export function ParallelComparison({
    source,
    target,
    targetSummary,
    relations,
}: {
    source: Reader;
    target: Reader | null;
    targetSummary: Summary;
    relations: ParallelView[];
}) {
    const strongest = relations[0];
    const spans = strongest.evidence?.spans ?? [];
    const matchedSurface = spans.find((span) => span.quote)?.quote ?? null;
    const identicalSurface =
        spans.length > 1 && spans.every((span) => span.quote === spans[0].quote);

    return (
        <article className="comparison">
            <header className="comparison-banner">
                <div>
                    <span>{parallelKindCopy(strongest.relation_kind).label}</span>
                    <h2>
                        {source.canonical_citation}
                        <i aria-hidden="true">&rarr;</i>
                        {targetSummary.canonical_citation}
                    </h2>
                    <p>{parallelKindCopy(strongest.relation_kind).detail}</p>
                </div>
                <KnowledgeStatus status="PARTIAL" compact />
            </header>

            <div className="comparison-grid">
                <TextColumn
                    citation={source.canonical_citation ?? source.display_label ?? ""}
                    veda={source.veda}
                    href={`/passage/${encoded(source.canonical_key)}`}
                    text={source.primary_text?.text}
                    script={source.primary_text?.script}
                    translation={source.translations.items?.[0]}
                />
                <TextColumn
                    citation={targetSummary.canonical_citation ?? targetSummary.display_label ?? ""}
                    veda={targetSummary.veda}
                    href={`/passage/${encoded(targetSummary.canonical_key)}`}
                    text={target?.primary_text?.text}
                    script={target?.primary_text?.script}
                    translation={target?.translations.items?.[0]}
                />
            </div>

            {matchedSurface && (
                <section className="matched-surface">
                    <h3>The surface that matched</h3>
                    <p className="panel-note">
                        {identicalSurface
                            ? "Both passages fold to the same comparison surface. Accents, word breaks and sandhi are removed before comparison, so this string is not how either text reads."
                            : "Each passage folds to its own comparison surface. Accents, word breaks and sandhi are removed before comparison."}
                    </p>
                    <code lang="sa">{matchedSurface}</code>
                </section>
            )}

            <section className="comparison-evidence">
                <h3>Evidence for this link</h3>
                <dl>
                    <div>
                        <dt>Relationship classes</dt>
                        <dd>
                            {relations
                                .map((row) => parallelKindCopy(row.relation_kind).label)
                                .filter((value, index, all) => all.indexOf(value) === index)
                                .join(", ")}
                        </dd>
                    </div>
                    <div>
                        <dt>Match level</dt>
                        <dd>{matchLevelCopy(strongest.match_level)}</dd>
                    </div>
                    <div>
                        <dt>Knowledge grade</dt>
                        <dd>{trustTierCopy(strongest.quality_tier)}</dd>
                    </div>
                    <div>
                        <dt>How it was established</dt>
                        <dd>{evidenceBasisCopy(strongest.trust).label}</dd>
                    </div>
                    {strongest.metrics?.ngram_jaccard != null && (
                        <div>
                            <dt>Overlap</dt>
                            <dd>
                                {Math.round((strongest.metrics.ngram_jaccard ?? 0) * 100)}% of
                                character n-grams shared
                            </dd>
                        </div>
                    )}
                    <div>
                        <dt>Stored direction</dt>
                        <dd>
                            {strongest.stored_direction === "THIS_PASSAGE_IS_SUBJECT"
                                ? `${source.canonical_citation} is the subject of the stored edge`
                                : strongest.stored_direction === "THIS_PASSAGE_IS_OBJECT"
                                  ? `${targetSummary.canonical_citation} is the subject of the stored edge`
                                  : "Not stored as a directed edge"}
                        </dd>
                    </div>
                </dl>
                <details>
                    <summary>Technical details</summary>
                    <p>Method: {strongest.method ?? "Not recorded"}</p>
                    <p>Knowledge layer: {strongest.knowledge_layer ?? "Not recorded"}</p>
                    <p>Review state: {strongest.state ?? "Not recorded"}</p>
                    <p>Relationship id: {strongest.parallel_id ?? "Not recorded"}</p>
                </details>
            </section>
        </article>
    );
}
