/**
 * The reader, before it has arrived.
 *
 * A skeleton is only useful if it is the shape of the thing it stands in for; a generic set of
 * grey bars just moves the layout shift from the content to the placeholder. So this is the
 * reader's own composition - breadcrumb, citation, the verse block, then the apparatus rail
 * beside it - at the reader's own measures, which means the page does not reflow when the text
 * lands.
 *
 * The verse lines are set to uneven widths because Vedic verse lines are uneven, and three
 * equal bars would promise a shape the text does not have.
 */
export default function ReaderLoading() {
    return (
        <div aria-busy="true" aria-label="Loading this passage" className="va-reader va-reader-skeleton">
            <div className="va-reader-where">
                <span className="skeleton" style={{ width: 132, height: 12 }} />
                <span className="skeleton" style={{ width: 54, height: 12 }} />
                <span className="skeleton" style={{ width: 54, height: 12 }} />
            </div>

            <div className="va-reader-layout">
                <div className="va-reading">
                    <div className="va-reader-head">
                        <span className="skeleton" style={{ width: 196, height: 34 }} />
                    </div>

                    <div className="va-verse">
                        <span className="skeleton" style={{ width: "84%", height: 22 }} />
                        <span className="skeleton" style={{ width: "71%", height: 22 }} />
                        <span className="skeleton" style={{ width: "78%", height: 22 }} />
                    </div>

                    <div className="va-reader-skeleton-block">
                        <span className="skeleton" style={{ width: "100%", height: 15 }} />
                        <span className="skeleton" style={{ width: "92%", height: 15 }} />
                        <span className="skeleton" style={{ width: "46%", height: 15 }} />
                    </div>
                </div>

                <div className="va-reader-skeleton-rail">
                    {[0, 1, 2].map((group) => (
                        <div className="va-reader-skeleton-block" key={group}>
                            <span className="skeleton" style={{ width: 104, height: 10 }} />
                            <span className="skeleton" style={{ width: "68%", height: 17 }} />
                            <span className="skeleton" style={{ width: "84%", height: 12 }} />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
