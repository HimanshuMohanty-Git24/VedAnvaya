import { ChatCircleDots } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

/**
 * The contextual entry point into Ask. Carries the subject as structured context
 * rather than as words inside the question, so the retriever binds the same passage or
 * entity the reader was looking at instead of re-resolving a name from prose.
 */
export function AskAboutButton({
    passageKey,
    entityLabel,
    label,
    variant = "secondary",
}: {
    /** A canonical key, sent as `passage_context`. */
    passageKey?: string;
    /** An entity label, sent as `entity_context`. */
    entityLabel?: string;
    label: string;
    variant?: "primary" | "secondary" | "quiet";
}) {
    const params = new URLSearchParams();
    if (passageKey) params.set("passage", passageKey);
    if (entityLabel) params.set("entity", entityLabel);
    const href = params.size ? `/ask?${params.toString()}` : "/ask";

    return (
        <Link
            className={variant === "quiet" ? "ask-about-quiet" : `button ${variant}`}
            href={href}
            prefetch={false}
        >
            <ChatCircleDots size={18} aria-hidden="true" />
            {label}
        </Link>
    );
}
