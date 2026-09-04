# ADR-010: An edition's hymn order is data, not a parser conditional

Status: Accepted

Canonical passage numbering follows Aufrecht via GRETIL. A translation edition may print the
same hymns in a different order, in which case its page number is not the canonical Sukta
number. The Ṛgveda has exactly one such divergence in the sources ingested for v1:

**Griffith prints the eleven Vālakhilya hymns at the end of his Book 8, as Hymns 93–103.
Aufrecht numbers them inline as RV 8.49–8.59.** Book 8 hymns 1–48 agree; RV 8.60–8.103 are
Griffith's Hymns 49–92.

Building Mandala 8 without this mapping did not produce missing translations — it produced
*wrong* ones. Every mantra from RV 8.49 onward received the English of a different hymn, and
220 mantras looked merely "uncovered" while 1,496 looked correctly aligned. A gap is honest; a
silent misalignment is not. Out-of-sample Mandalas are how such a defect surfaces, which is why
each Mandala is built and gated on its own before assembly.

The mapping lives in `src/vedagraph/editions.py` as a total function
`griffith_page(mandala, sukta) -> int`, with a test proving it is a permutation of Book 8 (no
hymn dropped, none duplicated) and identity everywhere else. It is applied when pinning
snapshots, so the recorded `scope` is always the canonical Sukta and every downstream stage —
staging, build, QA, report — stays edition-agnostic.

Deliberately rejected:

- A `if mandala == 8` branch in the Wikisource adapter. The rule is a property of Griffith's
  edition, not of Mandala 8, and the adapter must stay usable for other translations.
- Leaving the 220 mantras as gaps and documenting the divergence in prose. That would keep
  wrong English attached to RV 8.49–8.59 while claiming honest coverage elsewhere.
- Renumbering canonical passages to follow Griffith. Canonical identity follows Aufrecht; a
  translator's layout must never move a mantra.

Evidence recorded before implementing: per-hymn stanza counts match exactly under the mapping
(Griffith 49–92 ≡ Aufrecht 8.60–8.103, Griffith 93–103 ≡ Aufrecht 8.49–8.59, one genuine
one-stanza gap at RV 8.93), and the opening lines agree — Griffith 8/49 renders RV 8.60.1
("Agni, come hither with thy fires"), Griffith 8/93 renders RV 8.49.1.

Future editions with their own ordering (Wilson, Jamison–Brereton) add entries to the same
module. Nothing else changes.
