# Atharvaveda (Shaunaka): Whitney/Lanman translation coverage against the 1856 print

Measured 2026-09-08 on branch `semantic-pilot-v1`.

Artifacts measured:

| Role | Path |
| --- | --- |
| Translation stage | `data/staged/atharvaveda_translation_stage.json` |
| Canonical structure summary | `data/source_registry/atharvaveda_1856_structure_summary.json` |
| Canonical structure map | `data/source_registry/atharvaveda_1856_structure_map.jsonl` |
| Staging script | `scripts/fetch_atharvaveda_translation.py` |
| Upstream English snapshot | `data/raw/vedaweb_avs/2026-09-07/19591257ab94...cda1d.json` |

No canonical text was modified. Nothing below is estimated; every number is read off the
files named above.

## 1. Shape of the translation stage

`data/staged/atharvaveda_translation_stage.json` is a single JSON object,
`stage_version = "atharvaveda-translation-stage-v1"`, `work_id = "VG:WORK:AV:SAU"`.

| Field | Value |
| --- | --- |
| `verses` | 116 records |
| `translation_layer_total_contents` | 4881 |
| `sample_suktas` | 11 entries: 1.1, 4.1, 6.1, 7.6, 8.5, 13.4, 15.2, 16.1, 19.1, 20.96, 20.127 |
| `hymn_alias_misses` | `[]` - empty |
| `unresolved_stanza_labels` | `[]` - empty |
| `snapshot_ids` | 23 |
| `source_artifact_id` | `VEDAWEB.AVS.WHITNEY_LANMAN_1905.PLAINTEXT.L2` |

`alignment_method` reads, verbatim:

> resolved through VedaWeb location aliases, which are the printed book.hymn.stanza labels; NEVER by sequence position

Each of the 116 verse records carries the location as three integers - `kanda`, `sukta`,
`mantra` - plus a `source_alias` string of the form `k.s.m`. All 116 aliases agree exactly
with their integer triple; there are zero alias/triple mismatches. All 116 carry
`alignment = "EXACT_MANTRA_ALIGNMENT"`, `language = "en"`, `rights_status = "PUBLIC_DOMAIN"`.

What the two empty lists actually mean matters, and it is not "no gaps":

- `hymn_alias_misses = []` means all 11 requested hymn aliases, **including 20.96 and
  20.127**, resolved to a level-1 location on VedaWeb. The Book 20 hymns exist in the
  location tree.
- `unresolved_stanza_labels = []` means every stanza child label encountered was numeric and
  therefore mappable to an integer mantra slot. No label was ambiguous.

Neither list records the third failure mode, which is the one that actually bites: a stanza
that resolves cleanly but has **no translation text**. The script's inner loop drops such a
stanza with a bare `continue` and appends nothing to any diagnostic list. That silent drop is
where Book 20 disappears (section 5).

## 2. Per-kanda, per-sukta inventory of translated stanzas

The 116 staged stanzas fall in 9 suktas across 9 kandas. Every covered sukta's mantra
sequence is contiguous from 1 to its maximum with no holes.

| Kanda | Sukta | Stanzas | Mantra range |
| --- | --- | --- | --- |
| 1 | 1 | 4 | 1-4 |
| 4 | 1 | 7 | 1-7 |
| 6 | 1 | 3 | 1-3 |
| 7 | 6 | 4 | 1-4 |
| 8 | 5 | 22 | 1-22 |
| 13 | 4 | 56 | 1-56 |
| 15 | 2 | 4 | 1-4 |
| 16 | 1 | 13 | 1-13 |
| 19 | 1 | 3 | 1-3 |
| **Total** | **9 suktas** | **116** | |

Kandas 2, 3, 5, 9, 10, 11, 12, 14, 17, 18 and 20 contribute zero stanzas.

The reason is not a source failure. `scripts/fetch_atharvaveda_translation.py` hard-codes a
`SAMPLE_SUKTAS` tuple of 11 hymns and iterates only over that tuple. The stage is a
**pilot sample by construction**, kept deliberately in step with
`scripts/build_atharvaveda_pilot.py`. It was never a full-corpus fetch.

## 3. Comparison against the 1856-derived structure

The 1856 structure summary gives `per_kanda.highest_sukta_seen` for each of 20 kandas,
summing to 731 suktas over 458 text leaves (canvas n15-n472). That is the denominator.

| Kanda | Suktas in 1856 | Suktas covered | Stanzas covered | Suktas not covered | Covered sukta indices |
| --- | --- | --- | --- | --- | --- |
| 1 | 35 | 1 | 4 | 34 | 1 |
| 2 | 36 | 0 | 0 | 36 | - |
| 3 | 31 | 0 | 0 | 31 | - |
| 4 | 40 | 1 | 7 | 39 | 1 |
| 5 | 31 | 0 | 0 | 31 | - |
| 6 | 142 | 1 | 3 | 141 | 1 |
| 7 | 118 | 1 | 4 | 117 | 6 |
| 8 | 10 | 1 | 22 | 9 | 5 |
| 9 | 10 | 0 | 0 | 10 | - |
| 10 | 10 | 0 | 0 | 10 | - |
| 11 | 10 | 0 | 0 | 10 | - |
| 12 | 5 | 0 | 0 | 5 | - |
| 13 | 4 | 1 | 56 | 3 | 4 |
| 14 | 2 | 0 | 0 | 2 | - |
| 15 | 18 | 1 | 4 | 17 | 2 |
| 16 | 9 | 1 | 13 | 8 | 1 |
| 17 | 1 | 0 | 0 | 1 | - |
| 18 | 4 | 0 | 0 | 4 | - |
| 19 | 72 | 1 | 3 | 71 | 1 |
| **20** | **143** | **0** | **0** | **143** | **-** |
| **Total** | **731** | **9** | **116** | **722** | |

Sukta-level coverage is 9 / 731 = 1.23%.

Every covered sukta index sits inside its kanda's 1856 range, including the two tightest
cases: 13.4 against a kanda of exactly 4 suktas, and 8.5 against a kanda of exactly 10.

Two caveats on the denominator, both carried by the structure summary itself:

- `highest_sukta_seen` is documented there as a **lower bound** in principle: a running head
  names the suktas on that leaf, not the kanda's total. The summary notes the final leaf of
  every kanda was legible, so each bound is tight against the printed heads.
- The n159/n160 head anomaly (kanda 7, printed page 145) is the print's only recorded
  head/body disagreement. It concerns suktas 5-9 of kanda 7 and does not touch 7.6's
  membership in kanda 7, so it does not disturb any classification here.

## 4. Classification of all 731 suktas

Definitions applied exactly as specified. The universe is the 731 suktas of the 1856
structure.

| Class | Count | Share |
| --- | --- | --- |
| ALIGNED | 9 | 1.23% |
| MISSING | 722 | 98.77% |
| AMBIGUOUS | 0 | 0.00% |
| STRUCTURALLY_DIVERGENT | 0 | 0.00% |
| **Total** | **731** | **100%** |

ALIGNED (9): 1.1, 4.1, 6.1, 7.6, 8.5, 13.4, 15.2, 16.1, 19.1. Each has translation stanzas
present and a sukta index within its kanda's 1856 range.

MISSING (722): no translation record exists. This includes all 143 suktas of kanda 20 and all
suktas of kandas 2, 3, 5, 9, 10, 11, 12, 14, 17, 18, plus the untouched remainder of the nine
sampled kandas. 20.96 and 20.127 are counted MISSING, not AMBIGUOUS: their labels resolved
without ambiguity, and the absence is of text, not of a mapping.

AMBIGUOUS (0): `unresolved_stanza_labels` is empty and `hymn_alias_misses` is empty. No label
in the staged material failed to resolve to a 1856 sukta.

STRUCTURALLY_DIVERGENT (0), **with one limb of the test unmeasurable**. The class has two
limbs:

- *Sukta index outside the kanda's 1856 range* - measurable, and measured. Zero violations
  across all 9 covered suktas and both Book 20 probes.
- *Stanza count that cannot fit* - **not measurable from the available data.** The 1856
  structure map records kanda, sukta-first and sukta-last per leaf; it records no mantra
  counts. Its own summary states this explicitly: mantra counts "are not carried by the
  running head; they can only be obtained by reading the mantra terminals on each page, which
  this pass did not do", and it leaves `mantra_total.derived_from_1856_headers` as `null`.
  There is therefore no 1856-derived per-sukta stanza capacity to test 13.4's 56 stanzas or
  8.5's 22 stanzas against. The zero above is a zero on the index limb only. Whether any
  translated sukta overruns its printed stanza count is **unknown**, and will stay unknown
  until the mantra terminals are read off the leaf images.

Whitney's numbering is known to diverge from the Shaunaka Samhita numbering - this is the
stated reason the script refuses positional alignment. The staged sample is too small
(9 of 731 suktas) for the absence of index divergence in it to say anything about the
corpus. Do not read the 0 as evidence that Whitney and the 1856 print agree.

## 5. Book 20 (kanda 20): NOT COVERED

Plainly: **kanda 20 is not covered at all.** Zero of 143 suktas, zero stanzas.

The 1856 print gives kanda 20 as 143 suktas over 68 text leaves, canvas n405 (printed 391,
head `॥ अथर्ववेदे २० । १-४ ॥`) through n472 (printed 458, head `॥ अथर्ववेदे २० । १४३ ॥`),
closed by the colophon stating the twentieth kanda and the samhita are complete.

This is a measured absence, verified against the raw snapshots rather than assumed:

| Probe | Level-1 hymn resolved | Numeric stanza children | Children carrying Whitney text |
| --- | --- | --- | --- |
| 20.96 | yes (`696f2fee931b6009810ad2e5`) | 24 | **0** |
| 20.127 | yes (`696f2fee931b6009810ad304`) | 14 | **0** |
| 1.1 (control) | yes | 4 | 4 |
| 13.4 (control) | yes | 56 | 56 |

Both Book 20 hymns exist in VedaWeb's location tree with fully numeric stanza labels, and not
one of their 38 stanzas has an English row in the Whitney resource. The staging script
anticipates this in a comment - "Whitney does not translate every stanza (Book 20 is
untranslated)" - and drops such stanzas silently.

Scope of the claim, stated precisely: 38 of kanda 20's stanzas were probed directly and all 38
came back with no translation. The remaining 141 suktas of kanda 20 were never requested, so
their absence from the stage is a consequence of `SAMPLE_SUKTAS`, not an independent
measurement. What is measured is that kanda 20 has **zero** coverage in this stage, and that
where it was probed the upstream English layer had nothing to give.

The upstream English layer holds 4881 stanzas with text
(`translation_layer_total_contents = 4881`, all 4881 rows non-empty). How those 4881
distribute across kandas 1-20 is **unknown from local data**: the contents snapshot is keyed
by opaque `locationId` only, and no full locations dump is cached, so the mapping from
location id to `k.s.m` exists locally for only the 11 probed hymns. Whether 4881 covers
kandas 1-19 completely, and by how much it falls short of the full Shaunaka stanza count,
cannot be settled without fetching the full location index. It is not estimated here.

## 6. Rights posture

`rights_evidence` in the stage file says, verbatim:

- `underlying_work_status`: `"PUBLIC_DOMAIN"`
- `underlying_work_basis`: "published 1905, before 1931, therefore public domain in the United States; longest-living author Charles Rockwell Lanman died 1941"
- `corroboration`: "English Wikisource tags the same edition {{PD/US|1941}} at https://en.wikisource.org/wiki/Atharva-Veda_Samhita"
- `digital_layer_declared_license`: `null`
- `digital_layer_note`: "VedaWeb resource 696f42266f50da42570ad040 returns \"license\": null and \"licenseUrl\": null. It carries NO restrictive statement. This is materially different from VedaWeb's AVS Sanskrit resource 696f331f6f50da42570ad028, whose description reproduces verbatim: \"Copyright TITUS Project, Frankfurt a/M, 4.3.2015. No parts of this document may be republished in any form without prior permission by the copyright holder.\" That clause attaches to the Sanskrit text, not to this translation."
- `platform_site_notice_verbatim`: "Individual resources provide their own citation guidelines, which can be found in the resource information. Please use these for citing specific data."
- `citation_required_verbatim`: "Whitney, William Dwight & Charles Rockwell Lanman. 1905. Atharva-Veda Samhita. Translated with a critical and exegetical commentary by William Dwight Whitney. Revised and brought nearer to completion and edited by Charles Rockwell Lanman. Cambridge, MA: Harvard University Press. Curated and hosted by VedaWeb - Online Research Platform for Old Indic texts. University of Cologne."

Confirmed posture. The **English layer is usable**: its public-domain status rests on the
underlying 1905 Harvard Oriental Series work, not on VedaWeb's silence. The registry row for
`VEDAWEB.AVS.WHITNEY_LANMAN_1905.PLAINTEXT.L2` in `data/registry/source_artifacts.yaml` makes
that reasoning explicit under policy rule RIGHTS-8 - a null licence "is NOT a grant", so the
grant is taken from the 1905 publication date and Lanman's 1941 death instead. Use requires
the verbatim citation above.

VedaWeb's **Sanskrit is not usable**. Resource `696f331f6f50da42570ad028` carries the TITUS
no-republication clause. No Sanskrit from that resource is used in this stage or in this
report; the canonical structure in section 3 was derived independently from BSB page images of
the 1856 print under RIGHTS-13, which records that no VedaWeb material was consulted in
deriving it.

## Summary

| Measure | Value |
| --- | --- |
| Translated stanzas staged | 116 |
| Suktas covered | 9 of 731 (1.23%) |
| ALIGNED | 9 |
| MISSING | 722 |
| AMBIGUOUS | 0 |
| STRUCTURALLY_DIVERGENT | 0 (index limb only; stanza-count limb unmeasurable) |
| Kanda 20 coverage | 0 of 143 suktas, 0 stanzas |
| Upstream English layer size | 4881 stanzas (per-kanda distribution unknown locally) |

The stage is a 9-sukta pilot sample, not a translation of the Atharvaveda. Treating it as a
coverage baseline would overstate readiness by roughly two orders of magnitude.
