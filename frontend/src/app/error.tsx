"use client";

export default function Error({
    retry,
}: {
    error: Error & { digest?: string };
    retry: () => void;
}) {
    return (
        <div className="shell page">
            <section className="empty-state" role="alert">
                <h2>Something interrupted this view</h2>
                <p>
                    This page could not be rendered. No corpus data has been changed, and the rest
                    of the atlas is unaffected.
                </p>
                <button className="button primary" type="button" onClick={retry}>
                    Try again
                </button>
            </section>
        </div>
    );
}
