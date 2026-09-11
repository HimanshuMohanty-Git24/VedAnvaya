import Link from "next/link";

export default function NotFound() {
    return (
        <div className="shell page">
            <section className="empty-state">
                <p className="not-found-code">404</p>
                <h1>This atlas entry is not held here</h1>
                <p>
                    The identifier may be wrong, or the thing it names may sit outside the four
                    Samhitas this build holds. That is a limit of this corpus, not a statement about
                    the Vedas.
                </p>
                <div className="hero-actions">
                    <Link className="button primary" href="/search">
                        Search the corpus
                    </Link>
                    <Link className="button secondary" href="/limits">
                        What this atlas holds
                    </Link>
                </div>
            </section>
        </div>
    );
}
