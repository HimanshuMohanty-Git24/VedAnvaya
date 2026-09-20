"""Append owner round seven (R5) to docs/reports/data-completeness/OWNER_DECISIONS.md.

The file is pure LF with no CRLF anywhere, so the append is written in binary with explicit
``\n`` rather than through text mode, which on this platform would rewrite all 937 line
endings and bury a two-section addition in a whole-file diff.

Both sections are ``OWNER-SUPPLIED``. The attestation is the R5 instruction, which states the
decisions were "explicitly made by the owner after R4" and "are NOT agent-inferred". Per the
provenance table in section 37, that is the strongest attestation available here and is what
licenses a closure to cite them.
"""

from __future__ import annotations

import pathlib

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "reports" / "data-completeness" / "OWNER_DECISIONS.md"

ADDITION = """
# Owner round seven — Release Blocker Closure R5

Two decisions the registry had been holding two entries open for. Both were supplied directly
in the R5 instruction, which states they were "explicitly made by the owner after R4" and
"are NOT agent-inferred". Both are therefore `OWNER-SUPPLIED` under the §37 provenance table,
and both may be cited by a closure.

## 38. `OWNER_DECISION_ENTITY_001_EPITHET_SCOPE` — the denominator is the curated inventory

**Decision, as given:**

> For this release, the Epithet completeness denominator is:
>
>     the currently curated, evidence-backed Epithet inventory
>
> not an arbitrary requirement to span "well beyond 4 deities".
>
> The phrase "well beyond 4 deities" has no numerical denominator and no cited source defining
> the target inventory. Therefore it is NOT a valid release gate.
>
> Rules: process every currently curated Epithet; preserve provenance; normalization may
> connect evidence to an existing identity; normalization must never mint a new identity;
> broader epithet discovery is future enrichment, not release completeness.

**Why the clause could not be evaluated.** `GAP-ENTITY_COVERAGE-001`'s second clause asks the
epithet inventory to reach "well beyond 4 deities". R4 recorded that the clause can be neither
passed nor failed: the 13 curated epithets belong to 4 deities, so the occurrence layer can
only ever reach those 4, and no published epithet index exists in this repository against
which 4 could be measured as incomplete. A gate that cannot fail is not a gate — this ledger
has recorded that finding twice (§21, §23) and replaced both offenders.

**Readback, measured 2026-09-18 against the live store, not taken from R4's receipt.** 13
`:Epithet` nodes; 1,035 `MENTIONS_EPITHET` edges between an `:Epithet` and a `:Passage`, up
from 0 edges of any type; 0 epithets reaching no passage; 4 distinct deities, unchanged and
unchangeable without curation. Per-epithet occurrence is carried per node — `occurrence_mantras`,
`occurrence_tokens`, `occurrence_match_tier`, `occurrence_scope` and `occurrence_contract` —
so recall is measured per epithet rather than asserted as one aggregate, which is the third
clause. The inventory is still the curated 13: `fold_alias` was used to compare and never to
create or merge an identity, so the "normalization is a comparison instrument, never identity
evidence" invariant of §2 holds.

**`GAP-ENTITY_COVERAGE-001` closes `CLOSED_DERIVED`** citing this section. The epithet
inventory was not expanded to raise the deity count.

## 39. `OWNER_DECISION_COMMUNITIES_002_PAIR_DECOMPOSITION` — candidates are not evidence

**Decision, as given:**

> Mechanical pair generation is candidate generation, not evidence.
>
> For this release: only pair decompositions supported by canonical identity plus
> source-explicit or deterministic evidence may be asserted.
>
> The remaining mechanical candidates are NON-ASSERTED CANDIDATES, not missing graph data.
>
> Closure denominator: all evidence-eligible pairs processed. NOT: all mechanically generated
> candidates imported.

**Readback, measured 2026-09-18.** Of 214 `:Devata`, 71 carry `structure` PAIR or GROUP — 38
PAIR and 33 GROUP. All 71 carry a typed `decomposition_status` and 0 are null: 16
`DECOMPOSED_FROM_THE_COMPONENT_REGISTRY` (32 `COMPOSED_OF` edges), 4
`NOT_ENUMERABLE_DECLARED_BY_THE_REGISTRY` carrying the registry's own evidence and review
status, and 51 `NOT_ENUMERABLE_FROM_ANYTHING_HELD`. The entry's own closure measure —
PAIR-or-GROUP deities with `component_count` 0 — reads 55, and every one of the 55 is a typed
non-assertion rather than an unprocessed row.

**The evidence-eligible set is exhausted.** `devata_components.yaml` is the only artifact in
this repository that states a composite deity's members. It declares 20 composites; 14 were
already landed; of the remaining 6, four declare an empty member list with an explicit reasoned
refusal and a review status (`REJECTED` for viśvedevāḥ, ādityāḥ and marutaḥ; `NEEDS_REVIEW` for
dyāvāpṛthivyau), and two were landable and landed. So of the 24 pairs a mechanical pass
proposes, 2 are evidence-eligible and 22 are not, and the 22 have no entry in the only artifact
that could make them eligible. Enumerating them means deciding which deities each contains,
which is curation.

**This decision generalises, and it is applied once more in R5.** `GAP-RITUAL-005`'s second
clause has the identical shape: "every modelled rite carries its offerings" is unsatisfiable
from held evidence *because* the same test's third clause forbids presenting co-occurrence as an
asserted offering, and the only rite-to-offering material in the acquired apparatus is 258 rows
staged `PROBABLE`. Under this section's stated principle the 258 are non-asserted candidates,
the closure denominator is the evidence-eligible set, and the honest fix is a typed per-rite
offering status rather than an import. R5 applies it that way and says so, so that a reader can
see the extension and reject it if the owner did not intend it.

**`GAP-COMMUNITIES-002` closes `CLOSED_DERIVED`** citing this section. No unsupported pair was
imported to reach a count.
"""


def main() -> None:
    raw = DOC.read_bytes()
    if b"\r\n" in raw:
        raise SystemExit("refusing to append: the file now contains CRLF and this script assumes LF")
    marker = b"# Owner round seven"
    if marker in raw:
        raise SystemExit("owner round seven is already present; refusing to duplicate it")
    if not raw.endswith(b"\n"):
        raw += b"\n"
    DOC.write_bytes(raw + ADDITION.encode("utf-8"))
    after = DOC.read_bytes()
    print(f"appended {len(after) - len(raw)} bytes; CRLF in file: {after.count(chr(13).encode())}")
    print(f"sections now: 38={'## 38.' in ADDITION} 39={'## 39.' in ADDITION}")


if __name__ == "__main__":
    main()
