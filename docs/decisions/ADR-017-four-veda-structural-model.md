# ADR-017: One spine for four Vedas, and no invented levels

Status: Accepted
Date: 2026-09-07
Extends [ADR-002](ADR-002-stable-identities.md).
Full model: [docs/FOUR_VEDA_STRUCTURAL_MODEL.md](../FOUR_VEDA_STRUCTURAL_MODEL.md).

## Context

The Rigveda was built first, and its shape leaked into the shared contracts. `EntityType`
and `AlignmentLevel` were `WORK | SECTION | HYMN | MANTRA`, where `SECTION` meant Mandala
and `HYMN` meant Sukta. `CorpusBuildConfig` required `mandala` and `selected_suktas`.
`SuktaDiscoveryRecord` required `sukta_number` and `parent_mandala_key`. None of that was
wrong for a Rigveda-only corpus; all of it is wrong as a universal vocabulary.

The other three works do not fit:

- Vajasaneyi Samhita is `Adhyaya -> Mantra`. **It has no Sukta level at all.**
- Atharvaveda Shaunaka is `Kanda -> Sukta -> Mantra` and genuinely is section/hymn-shaped.
- Samaveda Kauthuma is `Arcika -> Prapathaka -> Ardha -> Dasati -> Verse`, its depth
  **varies between arcikas**, and the registry's declared hierarchy was a guess derived
  from web pages rather than a source record.

The Samaveda guess turned out to be wrong in two places. The selected GRETIL artifact
declares its own reference system in its body — `arcika | prapathaka | ardha | dasati |
verse | line` — so the fourth level is the **dasati**, not `Adhyaya`/`Khanda`, and the
sixth declared level is a sub-verse pāda label rather than the mantra.

The tempting move was to normalize all four works onto three levels. That would have
produced a tidy schema and a false one.

## Decision

**One spine, declared depth, native names preserved.** `Work -> structural container(s)
-> Passage`, where the number of containers is data. `Passage.hierarchy` stays
`dict[str, int | str]`; two new optional fields, `native_labels` and `structural_path`,
carry the edition's own ordered level names and the matching values as strings.

**Every change is additive.** No enum member was renamed or removed, no field was made
required, no URN was altered. `EntityType` and `AlignmentLevel` each gained exactly one
member, `STRUCTURAL_CONTAINER`, for containers that are neither section- nor hymn-shaped.
`SECTION` and `HYMN` keep their RV meanings because 11,590 sealed passages serialize
those strings. Named per-level members (`ARCIKA`, `PRAPATHAKA`, …) were rejected: the
enum would grow with every recension forever, and the level name already lives per-record
in `native_labels`.

**Absence is a value, not a gap.** The Samaveda edition encodes an absent level as a
literal `0`. `sv_mantra_identity` therefore applies `_non_negative` to
`prapathaka`/`ardha`/`dasati` — applying the positive-integer rule would reject 65 real
verses — while `_positive` is retained unchanged for Rigveda, Vajasaneyi and Atharvaveda,
so no level of those works can ever be `0`. `sv_container_identity` further separates
"the source marks this level absent" (`0`, retained in the key) from "this level is not
part of this address" (`None`, truncates the key). Those are different facts.

**A hierarchy is an observation; a key is a commitment.** Samaveda separates the two.
The hierarchy correction is kept, because the file declares its own reference system and
that observation holds regardless of whether the bytes may be ingested — reverting to the
demonstrably wrong `Adhyaya`/`Khanda` guess would be the worse error. But `key_pattern`
stays `null` and `identity_status` stays `RESEARCH_REQUIRED`, because the sole evidencing
artifact was adjudicated unusable on two independent grounds (its rights, and an empty
`<sourceDesc><bibl>`). The hierarchy itself is corroborated by two independent textual
witnesses and one independent addressing scheme — chiefly a rights-clean Sanskrit
Wikisource transcription that corrects the Pandey-lineage text rather than reproducing
it. GRETIL, sanskritdocuments and TITUS are three re-publications of ONE Pandey e-text,
so their agreement is not corroboration. What is missing is narrower: no witness
combines an IDENTIFIED PRINTED EDITION with REDISTRIBUTION RIGHTS. Wikisource clears
rights but not edition; GRETIL clears neither; other Pandey re-publishers agreeing is the
same defect twice, not corroboration. Until one witness clears both bars, no key is
declared, not even provisionally. `sv_mantra_identity` and `sv_container_identity` are implemented and
marked NOT FROZEN so pilots stay coherent and later freezing is purely additive. `Work`
gains `structure_evidence_sha256` so a declared hierarchy points at the artifact
evidencing it instead of resting on prose.

**Fourteen refusals are recorded explicitly**, not left implicit — no synthetic Sukta level,
no running number as identity, no non-nesting kanda as a tree level, no gana inside the
Samhita work, no pāda as a mantra, no prose/metre status as canonical structure, no
alternate citations merged into `Passage`, no single rights verdict per Veda. The full
list is Section 5 of the structural model.

## Consequences

Rigveda is untouched and proven so: 11,590 passages re-validate against the extended
models, and all 11,590 UUIDs re-derive identically from their URNs. Cross-work key and
UUID collisions are zero across 11,903 passages spanning three works.

`STRUCTURAL_CONTAINER` is a deliberate loss of type-level precision: a Samaveda Ardha and
a Dasati share an `entity_type`, and only `native_labels` distinguishes them. That is the
accepted cost of not growing the enum per recension, and it is why `native_labels` should
be populated by every new work rather than treated as decoration.

The refusal to unify `CorpusBuildConfig` is recorded separately in ADR-018.

Samaveda structure is representable but not ingestible, and the blocker is rights and
provenance rather than modelling. Recording the candidate key in code while refusing to
declare it in the registry is a deliberate asymmetry: it keeps the research, and it keeps
the commitment unmade.

Three documents still carry the superseded Samaveda claim and are owned elsewhere:
`docs/architecture/ID_SPEC.md`, `docs/architecture/SOURCE_POLICY.md` (which also still
says there are two arcikas, where the source shows four), and `docs/STATUS.md`. They are
listed as open items rather than silently edited.
