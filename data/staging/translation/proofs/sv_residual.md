# The 602 Samaveda verses with no per-verse evidence at any tier

Of the 1,844 Kauthuma Arcika mantras, 1,242 landed on a tier and **602 did not**. This records
what was searched, what was rejected and why, and what remains open. It is a negative result
with a named route out, not a shrug.

## 1. Tier 1 does not exist, and the search for it is now nine avenues deep

No published English translation of the **Kauthuma** Arcika was found. Every candidate is
either a different recension, a different text, or not public.

| Candidate | Verdict | Basis |
|---|---|---|
| Griffith, *Hymns of the Samaveda* (1893) | **RANAYANIYA**, not Kauthuma | his own preface, read verbatim from the Wayback capture: "I have followed Benfey's text", and the same preface identifies Benfey's edition as of "the same recension" as Stevenson's Ranayaniya |
| Benfey (1848), edition + German metrical translation | **RANAYANIYA** | named as such in Griffith's preface |
| Stevenson (1842), ed. Wilson | **RANAYANIYA**, and Purvarcika only | Griffith's preface: "A translation, by Dr. Stevenson, of the Ranayaniya recension" |
| Satyavrata Samasrami, Bibliotheca Indica (1874-78) | **RANAYANIYA** | Griffith's preface: "according to the same recension". The archive.org DLI scans of it are therefore not a Kauthuma witness either |
| en.wikisource, "The Sama Veda" | dead | one page, preface only. Re-confirmed. Note `data/registry/sources.yaml` still lists `WIKISOURCE_GRIFFITH_SV` as `BOUNDED_PILOT_ALLOWED`, promising coverage this source does not have |
| Devi Chand, *The Samaveda* | in copyright, explicit no-reproduction notice | Wave 0; the Scribd copies are unauthorised |
| *Samaveda Samhita* (Text, Translation, Commentary & Notes in English), sold as "An Old and Rare Book" | not public | commercial reprint, out of print, no public full text located |
| `sanskritdocuments.org/doc_veda/samaveda_kauthuma.pdf` | **Kauthuma, but Sanskrit only** | useful as a Kauthuma text witness for future verification; carries no translation |
| Pancavimsa Brahmana (Kauthuma), Caland tr., on wisdomlib | wrong text | a Brahmana of the Kauthuma school, not the Samhita; cannot be addressed to a mantra key |
| `Samved.xlsx` | verified trap, not used | header promises 1,875 verses, file holds 890 rows, 985 numbers absent across 89 disjoint runs, 70% of rows with text spilled into attribution columns, private-use-area font hacks instead of Unicode |

One number worth recording because it will come up again: independent sources put the Kauthuma
Samhita at **1,875 mantras**, and this graph holds **1,844**. That 31-verse delta is a property
of our own spine, not of Griffith, and it is unrelated to the Ranayaniya question.

## 2. Tier 2 was tried per verse and failed for these 602 on their own evidence

The method that worked for the other 1,242 is described in `translation.md`. For a verse to
reach tier 2 it needed *its own* Sanskrit to be surface-identical to a Rigveda verse this graph
already asserts a relation to. For these 602, either:

- **the graph asserts no Rigveda parallel at all** — so there is no third text against which
  Griffith's Ranayaniya base could be checked for this verse; or
- **the parallel is near but not identical** (typically 0.90-0.99 after accent stripping and
  script folding, which is exactly what a Samavedic variant reading of a Rigvedic verse looks
  like) **and** no Griffith Samaveda unit could be pinned to the verse by content, its best
  English control match falling below the 0.60 score / 0.08 uniqueness gate.

Each rejected row in `rejected.jsonl` carries which of the two applies, its nearest parallel,
and that parallel's measured similarity.

## 3. Tier 3 was available and was refused

Griffith's *Hymns of the Samaveda* is a public scholarly edition, and a positional join would
put an English rendering on all 602. That is exactly the move section 1 forbids — reusing
another recension's translation because the Sanskrit looks similar — and the three compounding
offsets make it worse than usual: cross-recension (Ranayaniya against Kauthuma), structural,
and arithmetic. Measured here, the map from our running order to his drifts monotonically from
offset 0 at the head to -81, so position alone is not even self-consistent.

735 verses *did* land at tier 3, but only where the Griffith unit was identified for that verse
**by content**, and every one of them is staged at `PROBABLE` and is not importable.

## 4. What remains open: tier 4, and what would make it cheap

The campaign's tier 4 — `MODEL_ASSISTED_LITERAL_TRANSLATION`, `quality_class:
MODEL_ASSISTED_DERIVATION`, attributed to no translator, source Sanskrit cited, uncertainty
recorded — is the standing route for all 602. It was not exercised in this pass, and that is a
scope statement rather than a finding: 602 literal renderings is a generation run with its own
gate, not a by-product of an acquisition pass, and mixing a few hundred model rows into an
otherwise attributed artifact would make the artifact harder to reason about, not easier.

Two cheaper things would shrink 602 first, and both are already in this campaign's scope:

1. **Benfey 1848** (`bub_gb_0C_oEB7TkVgC`, 291 pp, PD by age) carries Griffith's own base
   **Sanskrit** beside its numbering. Aligning Benfey's Sanskrit to our Kauthuma Sanskrit
   converts the 735 tier-3 rows from `PROBABLE` to decidable, and supplies the missing control
   for the verses that have no Rigveda parallel. This is the single highest-leverage artifact
   for the Samaveda and it is the reconnaissance's own recommendation.
2. **More Rigveda parallels.** Tier 2 here is gated by the graph's parallel layer, not by the
   translation: 182 of the 602 have no asserted Rigveda parallel whatsoever. Every parallel
   added is a verse that becomes decidable without any new translation being acquired.
