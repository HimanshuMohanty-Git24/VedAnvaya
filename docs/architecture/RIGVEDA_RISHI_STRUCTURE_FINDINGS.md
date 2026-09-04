# Ṛṣi Family and Lineage Structure — Source Investigation

**Finding: `NO SUFFICIENT DETERMINISTIC SOURCE FOUND`.**

No `MEMBER_OF_FAMILY`, `FATHER_OF`, `DESCENDANT_OF`, `HAS_GOTRA` or equivalent
edges are created in this phase.

---

## What was asked

Whether any source already approved and pinned in this repository supplies
**explicit** Ṛṣi family, patronymic, gotra or ancestor information — as data, in a
field of its own, rather than as something a reader could infer.

## What the pinned source actually contains

`WSC2023` (digitized Rigvedic Anukramaṇī, commit
`05b5987d6d8d6ec7228926eb68d6a21117c9b1f2`) is the only pinned source of Ṛṣi
information. One row looks like this:

```
1.9.vaiśvāmitro madhucchandāḥ.agniḥ.gāyatrī
```

Parsed, a staging record carries exactly these fields:

```
mandala, sukta, declared_verse_count,
raw_seer_field, raw_divinity_field, raw_meter_field,
segments, parse_status, parse_notes, ...
```

Verified across the whole staged file: the field set is closed, and there is
**one** seer field. There is no family column, no gotra column, no patronymic
column, no ancestor column, and no separate genealogical table anywhere in the
dataset.

## Why the data nevertheless looks like it contains genealogy

Because it does — inside the names, as grammar rather than as data.

`vaiśvāmitro madhucchandāḥ` means "Madhucchandas, descendant of Viśvāmitra". The
lineage is carried by the vṛddhi derivation `viśvāmitra-` → `vaiśvāmitra-`, a
productive Sanskrit patronymic pattern. The same shape recurs across the registry:
`śaunako gṛtsamadaḥ`, `rāhūgaṇo gotamaḥ`, `ājīgartiḥ śunaḥśepaḥ`,
`maitrāvaruṇirvasiṣṭhaḥ`, `bhārgavo venaḥ`.

Extracting `DESCENDANT_OF(madhucchandas, viśvāmitra)` from that string requires
applying a morphological rule to a proper name and trusting the result. That is
converting name grammar into asserted genealogy, which is precisely what this
phase forbids without a source. The prohibition is not pedantry:

- vṛddhi derivation marks descent, but also school affiliation, adoption into a
  lineage, and simple association; the pattern does not distinguish them.
- some Anukramaṇī seer labels are not patronymics at all (`agastyasvasā`,
  "Agastya's sister"; `sarpparājñī`, "queen of serpents"), and a suffix rule
  applied blindly would manufacture relationships from them.
- the same derived name can point to more than one ancestor figure across the
  tradition, and the Anukramaṇī does not disambiguate.

An inference that is right most of the time is still an inference, and this
repository does not record inferences as source-explicit edges.

## Other sources considered

**VHP.** Not investigated in bulk. The rights policy in this repository restricts
bulk use of that source, and a genealogy layer would require exactly the kind of
bulk extraction it disallows. Not pursued.

**Public structured scholarly datasets.** No rights-compatible dataset was found
that supplies Rigvedic Ṛṣi genealogy as structured data with per-claim provenance.
Encyclopaedic and community sources exist, but they carry no per-statement
citation, and this layer's whole premise is that every edge names the assertion it
came from.

**Common knowledge / an LLM.** Explicitly excluded. Vedic genealogy is
well-attested in secondary literature, and a language model would produce a
plausible and largely correct family tree. It would also be unattributable, and
this phase creates no knowledge without a source.

---

## Consequence for lexical mentions

This finding does more than block genealogy edges — it also determines the scope of
`MENTIONS_ENTITY`.

Because the Ṛṣi registry stores the Anukramaṇī's compound labels verbatim
(`VG:RISHI:RAHUGANO-GOTAMAH`) and the morphology layer supplies bare lemmas
(`gótama-`), linking a lemma to a single canonical Ṛṣi would require decomposing
those labels by the same name grammar this document declines to trust.

Rather than break the rule in a different place, v1 creates **no Ṛṣi lexical
mentions at all**. See ADR-013 and
[RIGVEDA_LEXICAL_MENTION_POLICY.md](RIGVEDA_LEXICAL_MENTION_POLICY.md).

The affected lemmas are present and identified in the token layer — `vásiṣṭha-`
(53 mantras), `káṇva-` (54), `bharádvāja-` (19), `gótama-` (18), `áṅgiras-` (68),
`átri-` (44) — so nothing is lost. The work is deferred, not blocked.

---

## What would change this finding

Any one of:

1. A rights-compatible structured dataset giving Rigvedic Ṛṣi genealogy with
   per-claim citations. Register it as a source and build from it.
2. A reviewed registry mapping each compound Ṛṣi label to its component
   patronymic and personal name, authored and reviewed by a person — the same
   pattern `devata_components.yaml` already uses for composite Devatās. This is
   the cheapest credible route, and the schema for it already exists.
3. An explicit genealogical Anukramaṇī edition, digitized and pinned.

Until one of those exists, the honest output is no edges.
