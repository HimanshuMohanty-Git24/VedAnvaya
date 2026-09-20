import { createHash } from "node:crypto";

/** All consumers reject malformed publication identities before computing output. */
export function validatePublicGraph(raw) {
    const ids = raw.nodes.map((node) => node.id);
    if (ids.some((id) => typeof id !== "string" || id.length === 0)) {
        throw new Error("Public graph contains a null or empty identifier");
    }
    if (new Set(ids).size !== ids.length) {
        throw new Error("Public graph contains duplicate identifiers");
    }
    for (const [source, target] of raw.edges) {
        if (![source, target].every((i) => Number.isInteger(i) && i >= 0 && i < ids.length)) {
            throw new Error("Public graph contains an unknown endpoint reference");
        }
    }
    return { nodes: ids.length, edges: raw.edges.length, duplicateIdentifiers: 0, unknownReferences: 0 };
}

export function exportHash(bytes) {
    return createHash("sha256").update(bytes).digest("hex");
}
