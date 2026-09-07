# Sāmaveda final identity

| Field | Value |
|---|---|
| **Run** | `SAMAVEDA_REFERENT_INTEGRITY_REPAIR` |
| **Date** | 2026-09-07 |
| **Starting commit** | `5896856` (branch `semantic-pilot-v1`) |
| **Work** | `VG:WORK:SV:KAU` — Sāmaveda, Kauthuma recension, arcika (verse) text only |
| **`identity_status`** | **`FINAL`** |
| **`coverage_status`** | `INCOMPLETE_BOUNDED` — 1,844 of 1,875 |
| **Session decision** | `SAMAVEDA_REFERENT_INTEGRITY_REPAIRED_WITH_BOUNDED_REVIEW` |

---

## 1. The declared key

```
CHANDA      VG:SV:KAU:CHANDA:P{prapathaka:02d}:D{dasati:02d}:V{verse:02d}
ARANYA      VG:SV:KAU:ARANYA:D{dasati:02d}:V{verse:02d}
MAHANAMNYA  VG:SV:KAU:MAHANAMNYA:V{verse:02d}
UTTARA      VG:SV:KAU:UTTARA:P{prapathaka:02d}:R{ardha:02d}:D{dasati:02d}:V{verse:02d}
```

Registered in `data/registry/works.yaml` as

```yaml
key_pattern: "VG:SV:KAU:{collection}[:P{prapathaka:02d}][:R{ardha:02d}][:D{dasati:02d}]:V{verse:02d}"
```

## 2. The declared URN

```
urn:vedagraph:mantra:samaveda:kauthuma:{collection_lower}[:prapathaka:{p}][:ardha:{r}][:dasati:{d}]:verse:{v}
```

Containers use the same shape under `urn:vedagraph:section:`, truncated at the deepest
level supplied. Worked examples:

| Key | URN |
|---|---|
| `VG:SV:KAU:CHANDA:P01:D01:V01` | `urn:vedagraph:mantra:samaveda:kauthuma:chanda:prapathaka:1:dasati:1:verse:1` |
| `VG:SV:KAU:ARANYA:D03:V01` | `urn:vedagraph:mantra:samaveda:kauthuma:aranya:dasati:3:verse:1` |
| `VG:SV:KAU:MAHANAMNYA:V07` | `urn:vedagraph:mantra:samaveda:kauthuma:mahanamnya:verse:7` |
| `VG:SV:KAU:UTTARA:P06:R03:D16:V02` | `urn:vedagraph:mantra:samaveda:kauthuma:uttara:prapathaka:6:ardha:3:dasati:16:verse:2` |
| `VG:SV:KAU:UTTARA:P06:R03` | `urn:vedagraph:section:samaveda:kauthuma:uttara:prapathaka:6:ardha:3` |

Note the URN carries **unpadded** integers while the key pads to two digits. That is
deliberate and pre-existing across all four works: the key is a sortable display and join
surface, the URN is the UUID input, and only the URN may never be re-spelled.

## 3. UUID stability policy

`entity_id = uuid5(VEDAGRAPH_NAMESPACE_UUID, canonical_urn)`, unchanged, with
`VEDAGRAPH_NAMESPACE_UUID = 7c8cde94-2bc0-50e2-8819-568ae65a3ec4`.

What the UUID depends on, exhaustively: the namespace constant and the URN string.
What it must therefore never depend on, and does not:

- the source artifact, its URL, its revision, or its licence;
- the TextVersion, the script, the accent notation, or the text itself;
- the build, the parser version, or the segmentation policy version;
- sequence position anywhere.

**`text_sha256` and `comparison_sha256` are not identity inputs.** They live on
`PassageReferentBinding` and are compared *against the previous release's value for the
same key*. Putting a content hash into a UUID would make every re-encoding a new entity
and would couple canonical identity to a mutable wiki; the guard achieves the opposite —
it detects a changed referent while leaving the identifier alone.

## 4. What the scheme is required to do, and how each requirement is met

| Requirement | How it is met |
|---|---|
| Source-independent | The key names no source. `uuid_for_urn` takes one string. `Passage` has no source, URL or edition field under `extra="forbid"` |
| Kauthuma-recension-specific | `KAU` is in the key and `kauthuma` in the URN |
| Structurally meaningful | Every segment is a level a witness declares for that collection |
| Unique | 1,844 minted keys, 1,844 distinct. Zero collisions in key, URN or UUID space |
| Stable under TextVersion replacement | No text reaches the URN. Re-fetching, re-encoding or re-normalising cannot change a key |
| Stable when missing units are recovered | The **whole** affected daśati is withheld, never partially minted, so filling a gap is purely additive. See §6 |
| Independent of sequence position | For the **verse index**, fully: it is arithmetic over printed numbers, sorted by value. For the **Uttarārcika daśati**, qualified: it is the nearest preceding printed daśati numeral *in document order*, because that is how the source declares it. See §5.4 — the unqualified claim was wrong and is corrected |
| No ambiguous arcika ordinal | The top slot is a **name**. See `SAMAVEDA_ARCIKA_ARITY_DECISION.md` |
| Gāna stays separate | Gāna is excluded by notation and needs its own `work_id` (Refusal 5) |
| Deterministic UUIDv5 under the existing namespace | Unchanged function, unchanged namespace constant |

## 5. Three design decisions, and what each one refuses

### 5.1 The collection is named, not numbered

A bare ordinal in the top slot had no stable denotation: slot-1 value `2` means
Āraṇyārcika in the Pandey e-text lineage and Uttarārcika in all six independent witnesses.
Naming the collection records the thing every witness agrees on — *which* collections
exist and what belongs to each, extents 585 / 55 / 10 / 1225 — and moves the bracketing
dispute to the container spine, where revising it renumbers nothing.

**MEASURED:** collection assignment agrees between the two lineages for **1,867 of 1,867**
comparable printed verse numbers, zero disagreements.

The four **sub**-collections are named rather than the two top-level groupings because the
extent of the name "Pūrvārcika" is *itself* disputed (585 in Caland and Vedapeetha, 650 in
Wikisource, the Vedic Heritage Portal, Wikipedia and B. R. Sharma HOS 57). Keying on the
disputed name would have imported the dispute into identity.

### 5.2 A level a collection does not declare is omitted, never zero-filled

The superseded key wrote `0`. That made the rejected edition's flattening choice part of
canonical identity, and it conflated "the text has no ardha here" with "the edition
declined to number it". Under the frozen scheme `sv_mantra_identity` **refuses** a value
for an undeclared level, including `0`.

That refusal is deliberately as loud for `0` as for any other value. An earlier revision of
this very run exempted zero (`value not in (None, 0)`), which meant old five-slot code
ported by mechanically passing zeros got *silence* from the mantra path while the container
path refused the same input. Silence is the migration hazard, because it produces a
well-formed key from a caller that still believes in the flattened address. Caught by
Agent D, fixed, and pinned by `test_a_level_the_collection_does_not_declare_is_refused`.

The consequence reaches beyond identity: a passage's hierarchy is now an
outermost-anchored **subsequence** of its work's declared levels rather than a prefix of
them. `qa/checks.py::_check_structural_position` was rewritten accordingly — it previously
required a prefix and would have **crashed** on the first Āraṇya passage of a canonical
build — and zero moved from an INFO "declared absent" to an ERROR.

### 5.3 Ardha is in the Uttarā key and not the Chanda key

Not symmetry, evidence:

- **Uttarārcika:** ardha is load-bearing because daśati **resets** inside each ardha —
  prapāṭhaka 1 has ardha 1 spanning daśati 1–23 and ardha 2 spanning daśati 1–22, so
  dropping ardha would collapse 22 distinct units onto 22 keys. **MEASURED:** ardha agrees
  1,217/1,217 across the two lineages.
- **Chanda:** the selected witness declares no ardha at all, and daśati already numbers
  1–10 continuously across the prapāṭhaka, so the slot would carry no information. An
  identified printed edition *does* assert ardha here — and in that print daśati resets
  1–5 per ardha. Admitting a redundant ardha would therefore make the print's competing
  convention **ambiguously representable**: the same key shape producible by two
  conventions denoting different units. Omitting it makes the print convention
  **unrepresentable** — it fails closed. The print's reset is recorded as an alternate
  Citation, not a competing canonical value.

### 5.4 What the adversarial pass corrected in this document

The first version of this report claimed the address is "independent of sequence position"
without qualification, and that the selected witness does not print running number 713.
Both were wrong, and the second one was a **weld**, not a gap: `713` is printed as
`… चर्षणीनां ७१३ ॥`, a marker with no opening separator, which the lifter read as an
ordinary pāda and appended to verse 714. `VG:SV:KAU:UTTARA:P01:R02:D01:V01` therefore
denoted two printed verse units, and repairing it would have moved that key and `:V02`.
Found by hostile review, fixed as a sixth marker dialect, and pinned by
`test_no_verse_carries_a_leftover_marker_numeral`, which catches the whole family without
needing a second witness.

Stated exactly, so the claim is not overstated again:

- The **verse index** is order-free. It is arithmetic over printed numbers, sorted by
  value; permuting verse blocks cannot change it. Verified under permutation, three seeds.
- The **Uttarārcika daśati** is not. It is the nearest preceding printed daśati numeral in
  **document order**, because that is how the source declares it, so moving a verse block
  across a heading moves its daśati. This affects the daśati level of 1,194 of the 1,844
  released keys. It is a property of the source's layout rather than a parser choice, and
  no alternative exists short of the source numbering every verse — but it is a real
  dependency and is now recorded as one in the adapter, in `works.yaml` and here.

Two gate defects were also found and fixed, and both mattered more than the marker:
`compare_referents` compared only the text digest, which in **this** corpus is not
sufficient — the Uttarārcika repeats Pūrvārcika verses verbatim, so 369 of 1,844 keys share
a digest with another key — and the 137 `KEY_REASSIGNED_BEFORE_FREEZE` rows of this run's
own ledger were pre-licensing referent change on 105 released keys. See
`SAMAVEDA_REFERENT_INTEGRITY_REPAIR.md` §11.

## 6. Gap insertion is additive, and this is the property that matters most

The freeze bar includes "zero future-gap insertion renumbering". Coverage is incomplete —
31 of 1,875 verses carry no key — so this has to be argued, not assumed.

The withholding rule is what makes it safe: **when a daśati's partition is not
corroborated, or its printed run does not close, the whole group is withheld.** Never part
of it.

| Withheld group | Verses | Printed markers | Reason |
|---|---:|---|---|
| `UTTARA:P4:R1:D22` | 9 | 1107–1115 | daśati headings 23 and 24 absent from the page |
| `UTTARA:P4:R2:D14` | 3 | 1172–1174 | heading absent; second witness reads daśati 13 |
| `UTTARA:P5:R1:D17` | 3 | 1241–1243 | heading absent; second witness reads daśati 16 |
| `UTTARA:P5:R2:D5` | 6 | 1280–1285 | heading absent; the displaced line block |
| `UTTARA:P5:R1:D2` | 9 | 1178, 1180, 1181, 1181, 1182–1186 | run non-contiguous — `1179` typeset as a second `1181` |

Because no key was minted anywhere inside those groups, supplying the missing structure
later **adds** `UTTARA:P4:R1:D22/D23/D24` and their verses without touching any existing
key. The same holds for the two unprinted running numbers.

**Verified by simulation, not asserted.** Each repair was constructed against the committed
baseline and the resulting key set compared: for the four omitted-heading groups and for
running number 1315, *added* keys only — **0 disappeared, 0 moved referent**. The one
repair that did move released keys, running number 713, was the blocking case of §5.4 and
is now fixed at source, so it is a no-op. One group, `UTTARA:P5:R2:D5`, is **untestable
rather than proven**: the second witness's own labels there are self-contradictory (its
verses carry running-number pairs `[1282, 1288]`, `[1283, 1295]`, `[1284, 1302]`), so no
repair is constructible from it. The selected witness's reading of that ardha is internally
consistent — D04–D08 are all six-verse daśatis — so the group is **over**-withheld, which
fails closed.

Had the disagreeing verses alone been withheld and the rest minted, `D22:V01`–`V03` would
exist now and would keep their meaning, but `D22` would silently change from a nine-verse
unit to a three-verse one — a container whose extent moved. Withholding the group avoids
that too.

## 7. The freeze bar

| Criterion | Result |
|---|---|
| Zero two-referent/one-key collisions | **0** — measured over all 1,844 |
| Zero one-referent/two-key accidental splits | **0** — `duplicate_referents` over the committed baseline returns `{}` |
| Zero spurious verse keys | **0** — the phantom V13 is retired and now unrepresentable |
| Zero unexplained positional identity | Met — the local index is printed-number arithmetic; document order is never read |
| Zero canonical coordinates dependent on HTML ordering | Met — verified by re-parse and by the order-independence test |
| Zero future-gap insertion renumbering | Met — see §6 |
| Zero cross-work collisions | Met — no RV/YV/AV key, URN or UUID changed |
| Deterministic UUID regeneration | Met — unchanged function and namespace |
| Parent chain valid | Met — and the gate was rewritten for subsequence hierarchies, which it previously got wrong |
| Variable hierarchy handled | Met — four collection shapes, from three levels below the collection down to none |
| Referent-binding manifest complete | Met — one binding per minted key, 1,844 of 1,844 |

## 8. What `FINAL` does and does not claim

**Claims.** The key pattern, the URN pattern and the UUID policy will not change again.
Every minted key is corroborated on its container address by a second, textually distinct
lineage, and its local index is derived from a contiguous printed run. No minted key is
capable of denoting a different textual occurrence, and a build that made one do so would
now fail.

**Does not claim.**

1. **That the corpus is complete.** It is not: 31 verses have no key.
   `coverage_status: INCOMPLETE_BOUNDED` records that, deliberately as a separate field,
   because identity and coverage fail independently and conflating them would either block
   a sound freeze or overstate what exists.
2. **That the arity question is philologically settled.** It is not. It is no longer an
   *identity* question.
3. **That the Sanskrit may be published.** It may not, yet: the independence grade is
   `NOT_A_VERBATIM_COPY` on one locus, this run found three loci pointing the other way,
   and codepoint-level re-verification at more than two loci is a precondition for bulk
   text release.
4. **That VedaGraph "has the Sāmaveda".** It has the arcika. The ~2,639 gānas are a larger
   parallel body needing their own `work_id`.
5. **That a canonical build can run today.** No `WIKISOURCE_SA.SV.KAU.*` text_version is
   registered, so a build would bind rows to the encumbered `GRETIL.SV.KAUTHUMA` at
   `PERMISSION_REQUIRED`. That registry record must be created first.

## 9. Cross-references

- [`SAMAVEDA_REFERENT_INTEGRITY_REPAIR.md`](SAMAVEDA_REFERENT_INTEGRITY_REPAIR.md) — the audit, the segmentation repair, and the gate
- [`SAMAVEDA_ARCIKA_ARITY_DECISION.md`](SAMAVEDA_ARCIKA_ARITY_DECISION.md) — the arity decision and the level classification
- [`SAMAVEDA_REFERENT_MIGRATION.md`](SAMAVEDA_REFERENT_MIGRATION.md) — the 144-entry migration ledger
- `data/registry/works.yaml` — the declaration itself
- `tests/unit/test_samaveda_referent_integrity.py` — the executable pins
