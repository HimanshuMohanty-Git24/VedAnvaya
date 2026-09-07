# Real-Luna predicate stability

NO HUMAN GOLD EXISTS.

MODEL SELF-AGREEMENT IS NOT ACCURACY.


Counts are assertions; intersection/union and Jaccard are passage-level predicate presence.
Supported omissions and policy ambiguities are EvidencePacket engineering assessments, not gold
labels.

| Predicate | A count | B count | Intersection | Union | A-only | B-only | Jaccard | Supported omissions | Unsupported extras | Policy ambiguities |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DESCRIBES | 5 | 3 | 1 | 7 | 4 | 2 | 0.143 | 4 | 0 | 1 |
| DESCRIBES_ACTION | 21 | 0 | 0 | 20 | 20 | 0 | 0.0 | 18 | 0 | 3 |
| INVOKES | 2 | 2 | 0 | 3 | 2 | 1 | 0.0 | 3 | 0 | 0 |
| INVOLVES_OFFERING | 2 | 3 | 2 | 3 | 0 | 1 | 0.667 | 0 | 0 | 1 |
| INVOLVES_RITUAL | 0 | 1 | 0 | 1 | 0 | 1 | 0.0 | 0 | 0 | 1 |
| INVOLVES_SUBSTANCE | 3 | 6 | 0 | 8 | 3 | 5 | 0.0 | 7 | 0 | 1 |
| PRAISES | 3 | 3 | 3 | 3 | 0 | 0 | 1.0 | 0 | 0 | 0 |
| REQUESTS | 21 | 15 | 6 | 21 | 12 | 3 | 0.286 | 18 | 1 | 3 |

The measured dominance is verified rather than assumed: REQUESTS and DESCRIBES_ACTION contribute
most one-run supported assertions. INVOLVES_SUBSTANCE is also unstable, especially where one run
emits a direct material mention while the other emits a request or action from a different clause.
INVOKES has a small denominator and one expert-dependent case; DESCRIBES varies mainly by
co-emission policy, not contradictory entity identity.
