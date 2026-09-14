import { AskExperience } from "@/components/ask/ask-experience";

export const metadata = {
    title: "Ask VedAnvaya",
    description:
        "Ask a research question across the four Samhitas and inspect the evidence behind the answer. Every claim carries a citation you can open.",
};

/**
 * Ask.
 *
 * The head states the contract before the composer rather than after the first answer,
 * because the contract is the reason to use this rather than a general model: the question is
 * classified, the names in it are resolved against the graph, a fixed catalogue of channels
 * runs, and only what those channels returned is used to write the answer. A reader who does
 * not know that will read the output as a model's opinion, which is the one thing it is not.
 */
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
        <div className="va-page va-ask-page">
            <header className="va-page-head">
                <p className="va-ask-kicker" lang="sa">
                    प्रश्न
                </p>
                <h1>Ask VedAnvaya</h1>
                <p>
                    Ask a question across the corpus and inspect the evidence behind the answer.
                </p>
            </header>

            <div className="va-ask-contract">
                <section>
                    <h2>What it does</h2>
                    <p>
                        Every factual sentence carries a citation into the evidence it came from.
                        The markers in the prose open the retrieved item, its Sanskrit, its
                        translation and its canonical citation, so an answer can be checked rather
                        than trusted.
                    </p>
                </section>
                <section>
                    <h2>What it refuses to do</h2>
                    <p>
                        A question this build cannot answer returns insufficient evidence and names
                        the dimension it could not reach. It does not guess, and it does not turn a
                        gap in the graph into a confident denial about the Vedas. Where retrieval
                        found an interpretation rather than a textual fact, the answer says so.
                    </p>
                </section>
            </div>

            <AskExperience
                entityContext={entity || null}
                initialQuestion={seeded}
                passageContext={passage || null}
            />
        </div>
    );
}
