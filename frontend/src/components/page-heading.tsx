import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

export function PageHeading({
    title,
    description,
    backHref,
    backLabel,
}: {
    title: string;
    description?: string | null;
    backHref?: string;
    backLabel?: string;
}) {
    return (
        <header className="page-heading">
            {backHref && (
                <Link className="back-link" href={backHref}>
                    <ArrowLeft size={16} />
                    {backLabel ?? "Back"}
                </Link>
            )}
            <h1>{title}</h1>
            {description && <p>{description}</p>}
        </header>
    );
}
