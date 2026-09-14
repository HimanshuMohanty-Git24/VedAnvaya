import Link from "next/link";
import { Thread } from "@/components/brand/thread";
import { Action } from "@/components/home/sections";

export const metadata = {
    title: "Not held here",
};

/**
 * The missing thread.
 *
 * The brand's divider is a hairline with a rubric diamond held in a flare at its centre; the
 * broken variant opens a gap and lets the diamond drift in it. That is the right mark for this
 * page, because the thing this product exists to draw is a connection, and the honest content
 * of a 404 here is that a connection could not be drawn.
 *
 * The copy matters as much as the mark. A missing identifier and a thing outside the four
 * Samhitas are different failures and the page cannot tell which one happened, so it names
 * both rather than guessing, and it says plainly that a limit of this corpus is not a
 * statement about the Vedas. That sentence is the same one the rest of the product makes
 * about every absence it reports.
 *
 * ## There is deliberately no root `loading.tsx`, and restoring one breaks this page
 *
 * This UI used to render under an HTTP 200. Seven routes could reach it - `/passage/[key]`,
 * `/devatas/[id]`, `/entities/[type]/[id]`, `/formula-families/[id]`, `/reuse/[key]`,
 * `/rituals/[id]` and `/vedas/[veda]` - and every one of them answered a soft 404: the
 * broken thread was drawn, the status line said the record was fine.
 *
 * The cause is the framework's HTTP contract rather than anything in these route files. From
 * the shipped documentation (`next/dist/docs/01-app/02-guides/streaming.md`, "The HTTP
 * contract"): "The response body begins streaming when a Suspense fallback renders (for
 * example, a `loading.tsx`) or when a component suspends under a `<Suspense>` boundary", and
 * once it has begun "you cannot change the status code or headers". `notFound()` fired after
 * the shell had been committed, so Next could only inject `<meta name="robots"
 * content="noindex">` and carry on with the 200 it had already sent.
 *
 * A `loading.tsx` is per-segment, and the one at the root of `app/` was a boundary above all
 * seven. Removing it returns a real 404 on six; the seventh needed its own segment-level
 * `passage/[key]/loading.tsx` removed as well.
 *
 * So: do not add a `loading.tsx` at the root of `app/`, and do not add one to a segment whose
 * page can call `notFound()`. Adding one to a segment that *cannot* 404 is safe, and is the
 * supported way to get a streaming skeleton back on a specific route. `corpus-surfaces.spec.ts`
 * asserts the status on all seven, so a restored boundary turns the suite red rather than
 * quietly reinstating the soft 404.
 */
export default function NotFound() {
    return (
        <div className="va-page va-missing">
            <Thread broken size={26} />
            <p className="va-missing-code">404</p>
            <h1>This thread is not held here</h1>
            <p className="va-missing-body">
                Either the identifier does not name anything in this build, or the thing it names
                sits outside the four Samhitas held here. This page cannot tell which, so it will
                not guess.
            </p>
            <p className="va-missing-body">
                A limit of this corpus is not a statement about the Vedas.
            </p>
            <div className="va-missing-ways">
                <Action href="/search">Search the corpus</Action>
                <Action href="/vedas">Browse the four Samhitas</Action>
                <Action href="/limits" note="What is held, and what is deliberately not">
                    What this atlas holds
                </Action>
            </div>
            <p className="va-missing-foot">
                If you followed a link from inside the product, it is a broken reference here
                rather than a mistake you made. <Link href="/about">About the project</Link>
            </p>
        </div>
    );
}
