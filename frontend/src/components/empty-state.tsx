import { CloudSlash, Compass, MagnifyingGlass, Prohibit } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

/** The API did not answer at all. Distinct from a knowledge limit. */
export function ServiceUnavailable({
    message = "The interface is ready, but the VedAnvaya knowledge service did not respond.",
}: {
    message?: string;
}) {
    return (
        <section className="empty-state" role="alert">
            <CloudSlash size={30} weight="duotone" aria-hidden="true" />
            <h2>The atlas is offline</h2>
            <p>{message}</p>
            <p className="empty-hint">
                No corpus data has been changed. Start the local API and reload this page.
            </p>
            <Link className="button secondary" href="/">
                Return home
            </Link>
        </section>
    );
}

/** A specific request failed. Not the same as the whole service being down. */
export function RequestFailed({ message }: { message: string }) {
    return (
        <section className="empty-state" role="alert">
            <Prohibit size={30} weight="duotone" aria-hidden="true" />
            <h2>This view could not be loaded</h2>
            <p>{message}</p>
            <Link className="button secondary" href="/search">
                Search the corpus
            </Link>
        </section>
    );
}

export function LoadFailure({ status, message }: { status: number; message: string }) {
    if (status >= 500 || status === 0) return <ServiceUnavailable message={message} />;
    return <RequestFailed message={message} />;
}

export function NothingHere({
    title,
    message,
    action,
}: {
    title: string;
    message: string;
    action?: { href: string; label: string };
}) {
    return (
        <section className="empty-state is-inline">
            <Compass size={26} weight="duotone" aria-hidden="true" />
            <h2>{title}</h2>
            <p>{message}</p>
            {action && (
                <Link className="button secondary" href={action.href}>
                    {action.label}
                </Link>
            )}
        </section>
    );
}

export function NoSearchResults({ query }: { query: string }) {
    return (
        <section className="empty-state is-inline">
            <MagnifyingGlass size={26} weight="duotone" aria-hidden="true" />
            <h2>Nothing matched {query}</h2>
            <p>
                No canonical key, citation, registered entity label, Sanskrit form or translation
                phrase in this corpus matched that query. The texts may still use the idea under
                another word.
            </p>
        </section>
    );
}
