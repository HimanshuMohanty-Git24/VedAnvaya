export default function Loading() {
    return (
        <div className="shell page" aria-busy="true" aria-label="Loading">
            <div className="skeleton" style={{ width: "42%", height: 54 }} />
            <div className="skeleton" style={{ width: "66%", height: 20, marginTop: 20 }} />
            <div className="skeleton" style={{ height: 380, marginTop: 48 }} />
        </div>
    );
}
