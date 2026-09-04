# Morphology Source Decision — VedaGraph Deterministic Lexical v1

**Decision: `PRIMARY_MORPHOLOGY_SELECTED`**

**Selected:** the University of Zurich morphosyntactic annotation as published in
the VedaWeb TEI, text version `VEDAWEB.ZURICH`, at pinned commit
`d3eb8af7324338161520d2d35eae8f7e985a19a5`.

The survey behind this decision is
[RIGVEDA_MORPHOLOGY_SOURCE.md](RIGVEDA_MORPHOLOGY_SOURCE.md).

---

## Against the stated selection criteria

**Full Rigveda coverage.** Measured, not claimed: 10,552 of 10,552 canonical
mantras carry token annotation; 164,758 tokens; zero tokens without a lemma. No
gap to work around and nothing to backfill.

**Manual / curated lemma quality.** The TEI header records over ten years of hand
morphosyntactic annotation at Zurich on Lubotsky's text, followed by a documented
hand disambiguation pass in Cologne against Grassmann's Rigveda dictionary. No
tagger or classifier is in the lineage. This is the criterion that mattered most,
and it is the one where the candidate is strongest.

**Stable verse alignment.** Alignment is structural. The stanza `xml:id`
`b02_h001_01` states Mandala, Sūkta and mantra outright, so a token reaches
`VG:RV:SAK:M02:S001:V001` by parsing integers. Zero unaligned records, zero
duplicate mappings, zero passage mismatches, and no edition mapping table needed.
Nothing is aligned by comparing text, which is the failure mode this project's
source policy exists to prevent.

**Clear licensing.** CC BY 4.0, declared per layer in the corpus TEI header, and
already recorded in `data/registry/text_versions.yaml` as `normalized_rights:
CC_BY`. The restrictive notice attached to the van Nooten–Holland layer does *not*
apply to this one; keeping VedaWeb's layers as separate registry entries is what
makes that distinction visible rather than assumed.

**Reproducibility.** Commit-pinned, per-file SHA256 in
`data/derived/vedaweb_morphology_artifacts.json`, already snapshotted under
`data/raw/vedaweb/`. The build reads that index and refuses to run if any artifact
comes from a commit other than the pinned one. No network access at build time.

**Token-level provenance.** Every token records its annotation layer, source
artifact, snapshot id and the annotation's own `xml:id` as `source_locator`, plus
`annotation_provenance` and `annotation_method` naming the scholars and the method.

**Compatibility with the existing source hierarchy.** This is the decisive
practical point. The ten artifacts are already registered as
`VEDAWEB.RV.BOOK01.TEI.D3EB8AF` … `BOOK10`, already hashed, already rights-recorded,
and the annotation layer already has a `TextVersionDescriptor` (`VEDAWEB.ZURICH`,
role `LINGUISTIC_ANNOTATION`, "Carries lemma, morphosyntax and Grassmann references
per token"). Selecting it registers no new source and grants no new rights.

---

## The decisive property: stable lemma identifiers

Each token carries a Grassmann-linked identifier such as `#lemma_agni_79`
alongside the lemma string. This is worth more than the coverage numbers.

It means entity matching can be done **without comparing strings at all**. A
reviewed lexical alias names a lemma identifier; a token either carries that
identifier or it does not. Sandhi, transcription differences between IAST and
ISO 15919, accent notation, stem-marking conventions — none of them can produce a
false match, because none of them is consulted. Every mention in this build was
produced by `LEMMA_ID_EXACT`, and the fallback string path contributed nothing.

That is the strongest form the "no substring matching, no fuzzy matching" rule can
take: not a filter applied after matching, but a matching method in which the
failure mode is structurally absent.

---

## What was rejected, and what was not

`sanskrit-texts/rigveda` was **not selected as the primary morphology source**, on
one ground only: it would require registering a new source, new rights, new
fetching and a new alignment audit in order to obtain lemmas that the already-pinned
Zurich layer supplies at 100% coverage with exact structural alignment. That is
cost with no corresponding gain for *this* layer.

It was **not rejected as a source.** It carries an independent verb-argument
annotation by Hettrich that has no counterpart in the Zurich layer, and its
independence from the Zurich tradition makes it a genuine cross-check rather than
a second opinion. It remains the recommended source for:

- a future verb-argument / semantic-role layer, which it uniquely enables;
- an independent audit of the lemma decisions relied on here.

Nothing in this decision forecloses adopting it later, and adopting it later
requires no change to any identifier minted now — see below.

---

## Consequences

**Token ids are tied to this annotation layer; mantra ids are not.** Tokenization
is a property of an edition: a different morphology source would segment some
mantras differently and produce different tokens. Token keys therefore name the
layer —

```
VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M01:S001:V001:PA:T001
```

— and are derived by UUIDv5 from the matching URN. Adopting a second morphology
source in future adds `VG:TOKEN:<OTHER-LAYER>:...` alongside these. It does **not**
touch `VG:RV:SAK:M01:S001:V001`, whose identity depends on the canonical corpus
alone. This is stated again in ADR-013 because it is the property most likely to be
eroded by a later convenience.

**The canonical Sanskrit does not change.** `GRETIL.RV.AUFRECHT` remains the
primary text. The Zurich layer is annotation *referencing* mantras; its surface
reading is stored as `surface_form` beside the canonical text, never in place of
it. The two disagree, and the disagreement is preserved: two mantra pairs are
identical in the GRETIL text but not in the Zurich token sequence, and the parallel
engine reports both facts separately rather than picking one.

**Accepting CC BY 4.0 obliges attribution.** Recorded in the manifest
(`morphology_license`, `morphology_annotation_layer_id`) and in every token's
`annotation_provenance`.
