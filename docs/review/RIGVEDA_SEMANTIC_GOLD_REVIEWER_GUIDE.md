# Semantic gold reviewer guide

Use the local EvidencePacket named by each worksheet row. Do not use outside Vedic
knowledge to fill gaps, and do not treat Anukramaṇī assignment or a lexical mention as
an automatic semantic relation.

For each candidate:

1. Entity: mark `ACCEPT`, `REJECT`, or `MODIFY`; choose only an existing constrained
   node type or note an ontology gap.
2. Predicate: mark `ACCEPT`, `REJECT`, or `MODIFY`; use only the predicate whitelist.
3. Explicitness: choose `EXPLICIT`, `STRONG_INFERENCE`, or `INTERPRETIVE`.
4. Evidence: mark `VALID` or `INVALID` and verify every cited token/translation ID is
   present in the packet.
5. Optionally record a missing expected relation, rejected tempting predicate, and a
   short note.

Enter reviewer name, UTC timestamp, and a final row status. These human annotations are
the only inputs that can later unlock a predicate; Luna suggestions are never gold.
