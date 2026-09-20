import { CopyButton } from "@/components/copy-button";

/**
 * The Samavedic notation witness, printed as its own section.
 *
 * This text used to be the second row inside a collapsed disclosure headed "One other
 * witness prints this text", which is the same sentence a second Rigvedic edition gets.
 * For 1,136 Samavedic verses it is not a second edition of the same thing: it is the only
 * surface in this product that carries the tone marks the tradition sings from, and hiding
 * it behind a generic summary is most of why a Samavedic page reads as empty.
 *
 * What the section must not do is over-claim. The marks are the source edition's marks,
 * reproduced; nothing here deciphers them into pitches and no melody is reconstructed from
 * them. That is said once, in a disclosure the reader opens, rather than in a warning box
 * that competes with the text it qualifies.
 */
export function SvaraNotation({
    text,
    witness,
    provenance,
}: {
    text: string;
    witness?: string | null;
    provenance?: string | null;
}) {
    return (
        <section aria-labelledby="va-reader-svara" className="va-reader-notation">
            <h2 className="va-reading-heading" id="va-reader-svara">
                Svara notation
            </h2>
            <div className="va-verse-meta">
                <span>{witness ?? "Notated witness"}</span>
                <CopyButton text={text} />
            </div>
            <p
                className="sanskrit devanagari va-reader-notation-text"
                data-script="DEVANAGARI"
                lang="sa"
            >
                {text}
            </p>
            {provenance ? <p className="va-reader-provenance">{provenance}</p> : null}
            <details className="va-reader-notation-about">
                <summary>About these marks</summary>
                <p>
                    The svara marks above and below the syllables are reproduced exactly as the
                    source edition prints them. They are a record of that edition&rsquo;s notation,
                    not a reconstructed melody, and nothing here derives a sung realisation from
                    them.
                </p>
            </details>
        </section>
    );
}
