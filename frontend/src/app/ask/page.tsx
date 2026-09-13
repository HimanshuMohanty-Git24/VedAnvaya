import { AskExperience } from "@/components/ask/ask-experience";
import { PageHeading } from "@/components/page-heading";

export const metadata = {
    title: "Ask VedAnvaya",
    description:
        "Ask a research question in natural language and read an answer built only from retrieved graph evidence, with every claim carrying a citation you can open.",
};

export default async function AskPage({
    searchParams,
}: {
    searchParams: Promise<{ passage?: string; entity?: string; q?: string }>;
}) {
    const { passage = "", entity = "", q = "" } = await searchParams;

    // A contextual entry point seeds the composer with the question a reader would have
    // typed, while the subject itself still travels as structured context on the request.
    const seeded =
        q ||
        (passage ? `What is ${passage} about?` : "") ||
        (entity ? `What does VedAnvaya record about ${entity}?` : "");

    return (
        <div className="shell page ask-page">
            <PageHeading
                title="Ask VedAnvaya"
                description="A research instrument, not a chat model. Your question is classified, named entities are resolved against the graph, a fixed catalogue of retrieval channels runs, and only what those channels returned is used to write the answer."
            />

            <section className="ask-contract" aria-label="What Ask will and will not do">
                <div>
                    <h2>What it does</h2>
                    <p>
                        Every factual sentence carries a citation into the evidence it came from.
                        The markers in the prose are clickable: each one opens the retrieved item,
                        its Sanskrit, its translation and its canonical citation, so an answer can
                        be checked rather than trusted.
                    </p>
                </div>
                <div>
                    <h2>What it refuses to do</h2>
                    <p>
                        A question this build cannot answer returns{" "}
                        <b>insufficient evidence</b> and names the dimension it could not reach. It
                        does not guess, and it does not turn a gap in the graph into a confident
                        denial about the Vedas. Where retrieval found an interpretation rather than
                        a textual fact, the answer says so.
                    </p>
                </div>
            </section>

            <AskExperience
                initialQuestion={seeded}
                passageContext={passage || null}
                entityContext={entity || null}
            />
        </div>
    );
}
