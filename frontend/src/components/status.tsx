import { CheckCircle, Circle, Info, Prohibit, WarningCircle } from "@phosphor-icons/react/dist/ssr";
import clsx from "clsx";
import { statusCopy, type StatusTone } from "@/lib/knowledge";

const ICONS: Record<StatusTone, typeof Info> = {
    supported: CheckCircle,
    partial: Circle,
    insufficient: WarningCircle,
    "not-built": Prohibit,
    unknown: Info,
};

/**
 * The one component for coverage. Every surface where absence could be misread
 * renders this rather than an empty list or a zero.
 */
export function KnowledgeStatus({
    status,
    compact = false,
    note,
}: {
    status?: string | null;
    compact?: boolean;
    note?: string | null;
}) {
    const copy = statusCopy(status);
    const Icon = ICONS[copy.tone];
    return (
        <div
            className={clsx("knowledge-status", `tone-${copy.tone}`, compact && "is-compact")}
            data-status={status ?? "UNKNOWN"}
            data-tone={copy.tone}
        >
            <Icon size={17} weight="duotone" aria-hidden="true" />
            <div>
                <strong>{copy.label}</strong>
                {!compact && <span>{note ?? copy.description}</span>}
            </div>
        </div>
    );
}

/** Long scholarly caveats collapse. Short ones stay open. */
export function Caveat({
    children,
    title = "Scope note",
    tone = "neutral",
}: {
    children: React.ReactNode;
    title?: string;
    tone?: "neutral" | "boundary";
}) {
    const text = typeof children === "string" ? children : null;
    if (text && text.length > 260) {
        return (
            <details className={clsx("caveat", "is-collapsible", `caveat-${tone}`)}>
                <summary>
                    <Info size={17} weight="duotone" aria-hidden="true" />
                    <span>{title}</span>
                </summary>
                <p>{text}</p>
            </details>
        );
    }
    return (
        <aside className={clsx("caveat", `caveat-${tone}`)}>
            <Info size={17} weight="duotone" aria-hidden="true" />
            <div>
                <strong>{title}</strong>
                <p>{children}</p>
            </div>
        </aside>
    );
}

export function CaveatList({
    caveats,
    limit = 4,
    title = "Scope notes",
}: {
    caveats?: Array<{ text?: string | null; source?: string | null }> | null;
    limit?: number;
    title?: string;
}) {
    const rows = (caveats ?? []).filter((row) => row.text);
    if (!rows.length) return null;
    return (
        <details className="caveat-list">
            <summary>
                <Info size={16} weight="duotone" aria-hidden="true" />
                {title}
                <span>{rows.length}</span>
            </summary>
            <ul>
                {rows.slice(0, limit).map((row) => (
                    <li key={row.text}>
                        <p>{row.text}</p>
                        {row.source && <cite>{row.source}</cite>}
                    </li>
                ))}
            </ul>
        </details>
    );
}

/** Marks a block as interpretation rather than corpus fact. */
export function InterpretationFrame({
    children,
    label = "Interpretation",
    note = "One reading of the measured data, not a statement the texts make.",
}: {
    children: React.ReactNode;
    label?: string;
    note?: string;
}) {
    return (
        <div className="interpretation-frame" data-knowledge-kind="interpretation">
            <div className="interpretation-tag">
                <span>{label}</span>
                <small>{note}</small>
            </div>
            {children}
        </div>
    );
}
