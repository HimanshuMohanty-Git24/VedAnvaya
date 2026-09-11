import type { components } from "@/lib/api-schema";
import { humanizePredicate, titleCase } from "@/lib/knowledge";

type MetricRow = components["schemas"]["DerivedMetricRow"];

function formatValue(value: unknown) {
    if (typeof value === "number") {
        return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(3);
    }
    return String(value);
}

/**
 * A computed measure, presented as a measure: what it counts, the numbers, and the
 * scope note that keeps it from being read as a statement the texts make.
 */
export function DerivedMetricCard({ metric }: { metric: MetricRow }) {
    const title = titleCase(humanizePredicate(metric.metric_name));
    const entries = Object.entries(metric.values ?? {}).filter(([, value]) => value != null);

    return (
        <article className="derived-metric" data-knowledge-kind="derived-metric">
            <header>
                <span>Derived measure</span>
                <h3>{title}</h3>
            </header>

            {metric.value != null && (
                <p className="derived-headline">{formatValue(metric.value)}</p>
            )}

            {entries.length > 0 && (
                <dl className="derived-values">
                    {entries.map(([key, value]) => (
                        <div key={key}>
                            <dt>{titleCase(humanizePredicate(key))}</dt>
                            <dd>{formatValue(value)}</dd>
                        </div>
                    ))}
                </dl>
            )}

            {metric.interpretation && <p className="derived-reading">{metric.interpretation}</p>}
            {metric.scope_note && <p className="derived-scope">{metric.scope_note}</p>}

            <details>
                <summary>How it was computed</summary>
                <p>{metric.method ?? "No method was recorded for this measure."}</p>
                <p className="mono">{metric.metric_id}</p>
            </details>
        </article>
    );
}
