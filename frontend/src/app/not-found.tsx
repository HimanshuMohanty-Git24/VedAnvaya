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
