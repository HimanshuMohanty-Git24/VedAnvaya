# Orchestration Note: Four-Veda Canonical Sanskrit Blocker Closure

**For:** the session that opens `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE`.
**This note specifies safe parallelism only. It does not schedule, size, or launch anything —**
that is a decision for whoever opens that session, informed by the actual scope they choose (which
of the three Vedas, how much external research vs. engineering, whether rights correspondence is
in scope for that session at all).

---

## Why parallelism is safe here, and where it stops being safe

The three blockers (YV, SV, AV) are **independent by construction**: they concern different
`work_id`s, different source artifacts, different adapters
(`yajurveda_pilot.py` / `samaveda_gretil.py` + `samaveda_wikisource.py` /
`atharvaveda_gretil.py`), and different registry rows. None of the three work packets requires
reading or writing another Veda's canonical output to make progress. This mirrors how the four
original pilot builds (B/C/D in the prior session, per `docs/FOUR_VEDA_SOURCE_ADJUDICATION.md`'s
own "Agent B/C/D" attributions) were already run without cross-contamination.

What is **not** independent, and must stay single-writer:

- `data/registry/works.yaml`, `data/registry/text_versions.yaml`,
  `data/registry/rights.yaml`, `data/registry/sources.yaml`,
  `data/registry/source_artifacts.yaml` — shared contract files. Every prior pilot session found
  a defect from a Veda-specific agent editing these locally (the YV pilot's invented artifact ids
  failing Agent F's G11 gate; the SV pilot's SV-1/SV-2 defects; the AV pilot's invented
  `GRETIL_AVS`/`VEDAWEB_AVS` sources). The pattern is consistent enough across all three prior
  pilots to treat as a standing risk, not a one-off.
- `src/vedagraph/qa/checks.py` (`validate_corpus`) — shared QA logic that already needed a
  work-agnostic fix once (the hard-coded `hierarchy["mandala"]` `KeyError`).
- `src/vedagraph/compare/text.py` / `compare/run.py` — shared comparison infrastructure; the AV
  pilot found `run_comparison()` is still Rigveda-shaped (`mandala: int` required) and worked
  around it rather than editing it.
- Final rights classifications (`RightsStatus` values, `PERMISSION_REQUIRED` vs `CC_BY_SA` vs
  `UNKNOWN` determinations) — these are adjudications with legal consequence, not implementation
  details, and the prior session assigned them to a single rights/provenance owner (called
  "Agent E" in the existing docs) precisely so two Veda-specific agents couldn't both propose
  incompatible verdicts for shared sources like GRETIL or TITUS.

## Suggested lanes

- **Agent A — coordinator / integration.** Owns the shared-contract files listed above. Reviews
  and merges any registry change a Veda-lane agent proposes; does not do Veda-specific research
  or engineering itself. This mirrors the existing convention (`FOUR_VEDA_STRUCTURAL_MODEL.md`'s
  "Owner: shared-contract single writer").
- **Agent B — Yajurveda closure.** Works `docs/work_packets/YAJURVEDA_PRIMARY_TEXT_CLOSURE.md`.
  Primarily engineering + one philological-review coordination task (VSM 16.37); no rights
  correspondence needed, since YV rights are already `RESOLVED`.
- **Agent C — Samaveda closure.** Works
  `docs/work_packets/SAMAVEDA_IDENTITY_SOURCE_CLOSURE.md`. Primarily research (edition tracing,
  count reconciliation) with some engineering (re-pointing the adapter at Wikisource). May
  propose a `data/registry/works.yaml` change (freezing `key_pattern`) — routes through Agent A.
- **Agent D — Atharvaveda closure.** Works
  `docs/work_packets/ATHARVAVEDA_PRIMARY_SOURCE_CLOSURE.md`. Primarily research/acquisition
  (locating a Roth & Whitney 1856 scan, or drafting a TITUS permission request) with engineering
  work gated behind acquisition succeeding. Likely the slowest lane, since it is the only one
  blocked on an external, non-code dependency.
- **Agent E — independent rights/provenance reviewer.** Reviews any rights-relevant claim
  Agents B/C/D produce (a newly registered source, a newly asserted licence, a proposed
  `RightsStatus`) before it lands. Per the existing convention, **only Agent E makes final rights
  classifications** — this matches how the prior session's rights matrix was single-authored and
  cross-checked by others rather than voted on.
- **Agent F — QA / reproducibility reviewer.** Re-runs each Veda lane's deterministic-rebuild
  check and shared-gate (`validate_corpus`) independently, the way the prior session's Agent F
  caught SV-1/SV-2 and the AV `sources.jsonl`-empty defect that the Veda-specific agent's own
  local gate had missed. Does not write Veda-specific adapters.

## Constraints carried over from this preflight

- Agents B/C/D **may** spawn bounded research subagents (e.g. to search for a specific archive.org
  scan, or to re-read a specific TEI header) — this preflight explicitly avoided that kind of
  research itself and left it for the closure session to size.
- **Only Agent A** may make shared-contract changes (registries, shared QA, shared comparison
  infrastructure).
- **Only Agent E** may make final rights classifications, matching current repository ownership
  convention (the existing docs consistently attribute rights verdicts to a single named owner,
  never to a Veda-lane agent).
- No lane should re-litigate a corrected finding from `docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §4
  (the six recorded corrections, including the one self-reported error, CORR-1/TITUS) without new
  evidence — re-deriving a settled adjudication from scratch is exactly the wasted-research this
  preflight was scoped to prevent downstream.
