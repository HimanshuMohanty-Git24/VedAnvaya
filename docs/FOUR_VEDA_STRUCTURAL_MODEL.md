# Four-Veda structural model

Status: **Accepted for all four Vedas.** Samaveda identity was the last outstanding one and
is now `FINAL`.

**Updated 2026-09-07 by `SAMAVEDA_REFERENT_INTEGRITY_REPAIR`.** Samaveda identity is
**FROZEN**: `key_pattern` and `urn_pattern` are declared, the top slot is a collection
**name** rather than an arcika ordinal, a level a collection does not declare is omitted
rather than zero-filled, and a referent-integrity gate now binds each released key to the
source occurrence it denotes. `referent_integrity` and `arcika_arity` are both `RESOLVED`, the latter
*dissolved* as an identity question rather than adjudicated. Coverage is tracked
separately and is `INCOMPLETE_BOUNDED` (1,844 of 1,875). See
[`SAMAVEDA_FINAL_IDENTITY.md`](reports/SAMAVEDA_FINAL_IDENTITY.md) and
[`SAMAVEDA_REFERENT_INTEGRITY_REPAIR.md`](reports/SAMAVEDA_REFERENT_INTEGRITY_REPAIR.md).

*Superseded status line, kept so the change is legible:* "Accepted for Rigveda, Vajasaneyi
and Atharvaveda. Samaveda structure observed, Samaveda identity NOT declared
(`RESEARCH_REQUIRED`)."

Date: 2026-09-07
Owner: shared-contract single writer (`identity.py`, `models/enums.py`, `models/core.py`,
`schema.py`, `data/registry/works.yaml`).
Decision record: [ADR-017](decisions/ADR-017-four-veda-structural-model.md).
Build-configuration corollary: [ADR-018](decisions/ADR-018-per-work-build-configuration.md).

This document defines how four Vedas with four different native organizations are
addressed by one set of record types, without any of them being read through another's
vocabulary. It exists because the Rigveda was the reference implementation, and a
reference implementation quietly becomes a universal assumption unless the assumption is
written down and refused.

---

## 1. The generic spine

There is exactly one addressing spine:

```
Work  ->  structural container(s)  ->  Passage
```

- **Work** is one recension of one Veda (`data/registry/works.yaml`, model `Work`). A
  work declares its own ordered `hierarchy` of level names, its `citation_pattern`, its
  `key_pattern`, and an `identity_status`.
- **structural container(s)** is a chain of zero or more nested nodes. The chain length
  is a property of the work, not of the schema. Rigveda has two containers, Vajasaneyi
  has one, Samaveda has up to four.
- **Passage** is any addressable node, container or leaf. Containers and leaves are the
  same record type, distinguished by `entity_type`.

Every node carries, in `Passage`:

| Field | Meaning |
|---|---|
| `canonical_key` | Human-readable stable key, `^VG:[A-Z]+:[A-Z]+:.+$` |
| `canonical_urn` | Stable URN, `^urn:vedagraph:`; the **sole** input to the UUID |
| `entity_id` | `uuid5(VEDAGRAPH_NAMESPACE_UUID, canonical_urn)` |
| `entity_type` | `WORK` / `SECTION` / `HYMN` / `STRUCTURAL_CONTAINER` / `MANTRA` |
| `work_id` | Which work this node belongs to |
| `hierarchy` | `dict[str, int \| str]` — level name to value |
| `native_labels` | The edition's own ordered level names (optional) |
| `structural_path` | The level values as strings, positionally aligned (optional) |
| `parent_key` | The containing node's `canonical_key`, or `None` at the root |
| `sequence_in_parent` | Position among siblings |
| `canonical_citation` | The work's own printed citation form |

### Native labels are preserved explicitly

`hierarchy` is a dict, and a dict does not contractually carry order. `native_labels`
therefore does two jobs: it supplies the authoritative **order** of the levels, and it
records the level names **as the selected edition names them**. A reader of a Samaveda
passage sees `["Arcika", "Prapathaka", "Ardha", "Dasati", "Verse"]`, not a projection
onto Mandala/Sukta/Mantra.

`structural_path` holds the same levels' values as **strings**, positionally aligned
with `native_labels`. Strings, not integers, because:

- zero-padding is a property of some editions' printed citations and is lost by `int`;
- a level may legitimately be non-numeric (Samaveda's sub-verse `line` is `a`/`c`/`e`,
  and while `line` is not an identity level, nothing in the contract should assume
  numeric levels forever).

Both fields are optional with empty defaults. The sealed Rigveda corpus predates them
and validates unchanged; new works are expected to populate them.

A `Passage` validator enforces that when `native_labels` is supplied it names exactly
the levels present in `hierarchy` (case-insensitively, no repeats), and that
`structural_path`, when supplied, is the same length and cannot be supplied without
`native_labels` to define its order.

---

## 2. The exact native hierarchy per Veda

### Rigveda — `VG:WORK:RV:SAK`, Shakala. `identity_status: FINAL`

```
Mandala -> Sukta -> Mantra
```

| Level | `entity_type` | Key | URN |
|---|---|---|---|
| Mandala | `SECTION` | `VG:RV:SAK:M{m:02d}` | `urn:vedagraph:section:rigveda:shakala:mandala:{m}` |
| Sukta | `HYMN` | `VG:RV:SAK:M{m:02d}:S{s:03d}` | `urn:vedagraph:hymn:rigveda:shakala:mandala:{m}:sukta:{s}` |
| Mantra | `MANTRA` | `VG:RV:SAK:M{m:02d}:S{s:03d}:V{v:03d}` | `urn:vedagraph:mantra:rigveda:shakala:mandala:{m}:sukta:{s}:mantra:{v}` |

Sealed: 10 Mandalas, 1,028 Suktas, 10,552 Mantras, 11,590 passages. These keys, URNs and
UUIDs are frozen. Nothing in this document may change them.

### Atharvaveda — `VG:WORK:AV:SAU`, Shaunaka. `identity_status: FINAL`

```
Kanda -> Sukta -> Mantra
```

| Level | `entity_type` | Key | URN |
|---|---|---|---|
| Kanda | `SECTION` | `VG:AV:SAU:K{k:02d}` | `urn:vedagraph:section:atharvaveda:shaunaka:kanda:{k}` |
| Sukta | `HYMN` | `VG:AV:SAU:K{k:02d}:S{s:03d}` | `urn:vedagraph:hymn:atharvaveda:shaunaka:kanda:{k}:sukta:{s}` |
| Mantra | `MANTRA` | `VG:AV:SAU:K{k:02d}:S{s:03d}:V{v:03d}` | `urn:vedagraph:mantra:atharvaveda:shaunaka:kanda:{k}:sukta:{s}:mantra:{v}` |

Atharvaveda is the one work whose three levels genuinely map onto RV's `SECTION` /
`HYMN` / `MANTRA`: its Sukta really is a hymn. This is a finding, not a default.

Its prose *paryāya* units (Kandas 15 and 16, plus 9.6, 12.5, 13.4) are addressed by the
same kanda/sukta/mantra triple in the selected source and are therefore ordinary
Passages. **VedaGraph does not assert metrical-versus-prose status as canonical
structure.** Pāda counts and the edition's own verse markers are `SourceAssertion`
records. The *anuvāka* markers the source carries are likewise `SourceAssertion`, not a
fourth hierarchy level, because the declared hierarchy is FINAL at three levels.

### Shukla Yajurveda — `VG:WORK:YV:VSM`, Vajasaneyi Madhyandina. `identity_status: FINAL`

```
Adhyaya -> Mantra
```

| Level | `entity_type` | Key | URN |
|---|---|---|---|
| Adhyaya | `SECTION` | `VG:YV:VSM:A{a:02d}` | `urn:vedagraph:section:yajurveda:vajasaneyi-madhyandina:adhyaya:{a}` |
| Mantra | `MANTRA` | `VG:YV:VSM:A{a:02d}:V{v:03d}` | `urn:vedagraph:mantra:yajurveda:vajasaneyi-madhyandina:adhyaya:{a}:mantra:{v}` |

**Two levels. There is no Sukta.** This is stated here, asserted by test, and is the
single most likely place for an RV assumption to leak in.

### Samaveda — `VG:WORK:SV:KAU`, Kauthuma. `identity_status: FINAL`

```
Collection -> Prapathaka -> Ardha -> Dasati -> Verse
```

**FROZEN 2026-09-07 by `SAMAVEDA_REFERENT_INTEGRITY_REPAIR`.** `key_pattern` and
`urn_pattern` are declared; `coverage_status` is `INCOMPLETE_BOUNDED`. Full detail in
[`SAMAVEDA_FINAL_IDENTITY.md`](reports/SAMAVEDA_FINAL_IDENTITY.md).

**Samaveda is the one work whose hierarchy is not a PREFIX chain.** The five levels above
are the work's declared vocabulary, but no single passage carries all of them: each
collection carries exactly the levels it declares, and a level a collection does not have
is **omitted**, not zero-filled. A passage's hierarchy is therefore an
outermost-anchored **subsequence** of the declared list. `qa/checks.py` enforces that
rule; it previously required a prefix, which would have rejected every Āraṇya passage.

| Collection | Levels below the collection | Key | Verses |
|---|---|---|---:|
| `CHANDA` | prapāṭhaka, daśati | `VG:SV:KAU:CHANDA:P{p:02d}:D{d:02d}:V{v:02d}` | 585 |
| `ARANYA` | daśati | `VG:SV:KAU:ARANYA:D{d:02d}:V{v:02d}` | 55 |
| `MAHANAMNYA` | *(none)* | `VG:SV:KAU:MAHANAMNYA:V{v:02d}` | 10 |
| `UTTARA` | prapāṭhaka, ardha, daśati | `VG:SV:KAU:UTTARA:P{p:02d}:R{r:02d}:D{d:02d}:V{v:02d}` | 1,225 |

**The top slot is a NAME, and that is the whole repair.** The superseded candidate key
wrote `A{arcika}`, a bare ordinal whose denotation is not stable across witnesses: slot-1
value `2` means Āraṇyārcika in the Pandey e-text lineage and Uttarārcika in all six
independent witnesses, a 1,225-verse referent collision. Every witness holds the same four
blocks in the same order with the same extents, so naming them records exactly what is
agreed and leaves the bracketing dispute to the container spine, where revising it
renumbers nothing. **MEASURED: collection assignment agrees between the two lineages for
1,867 of 1,867 comparable printed verse numbers, zero disagreements.**

**`ardha` is present only in the Uttarārcika**, where daśati resets inside each ardha
(prapāṭhaka 1: ardha 1 = daśati 1–23, ardha 2 = daśati 1–22, agreement 1,217/1,217). It is
deliberately absent from the Chanda key even though an identified print asserts it there,
because in the Chanda collection daśati already numbers 1–10 continuously and a redundant
slot would make the print's competing per-ardha convention *ambiguously representable*
rather than unrepresentable.

**`verse` is the daśati-local index, never the samhita running number.** The selected
witness prints only the running number, so the local index is derived from the source's own
printed arithmetic and the derivation fails closed when the run is not contiguous.

The paragraphs below are the original hierarchy-discovery record. They remain accurate
about the LEVEL LIST and about how it was corroborated, and are retained for that. Where
they describe the key, the zero encoding, or `identity_status`, they are superseded by the
block above.

The hierarchy rests on the selected source's own declared reference system, corroborated
by **two independent textual witnesses and one independent addressing scheme**. Counting
carefully matters here, so the tally is stated exactly:

**The selected source** — the GRETIL Samavedasamhita TEI
(`structure_evidence_sha256` `91c28c0394e94dccc9bad12a08224fbcde0a1194402b610df26647621ed92456`)
declares its own reference system in its body (below).

**Independent textual witnesses — 2:**

1. **Sanskrit Wikisource** — **106 arcika pages** (the other 725 of the 840 are gāna and
   out of scope for this `work_id`; "840 pages" must never be cited as this work's
   coverage), CC BY-SA 4.0, Devanagari. It **corrects** the Pandey text at one locus:
   GRETIL mislabels verse 2's first pāda as `0101a`, which bleeds the pāda into verse 1
   and strips it from verse 2, while Wikisource carries both verses whole.

   > **CORRECTED 2026-09-07.** This item previously read *"Independence is proven, not
   > argued"* and cited the maxim *"a text cannot inherit from a source it does not share
   > an error with."* The grade of record is **`NOT_A_VERBATIM_COPY`**, not proven. The
   > maxim is invalid as a universal — it excludes only verbatim **uncorrected**
   > inheritance, not copy-then-correct — and the claim rests on **one** locus whose defect
   > is conspicuous enough to be exactly what a copyist would repair.
   >
   > `SAMAVEDA_REFERENT_INTEGRITY_REPAIR` then found **three loci pointing the other
   > way**: running number 1179 is typeset as a second 1181 in **both** lineages at the
   > same place, and so are single-daṇḍa verse terminators at 1133 and 1592. Either common
   > descent or a shared print antecedent; not adjudicated. The better independence
   > evidence remains the wholesale difference in numbering system (running 1..1875 versus
   > daśati-local), not the pāda.
   >
   > Not load-bearing for identity, which is mechanically source-blind. **Is** load-bearing
   > for text redistribution, and codepoint-level re-verification at more than two loci is
   > a precondition for any bulk release.
2. **Griffith 1895**, translating Benfey (Ranayaniya), structures his English as
   BOOK / CHAPTER / **DECADE** with 1–10 verses per decade. It predates Pandey by a
   century and independently uses the dasati as the fourth level.

**Independent addressing evidence — 1:**

3. **TITUS** addresses Kauthuma at eight levels
   (`SV > SVK > Arcika > Prapathaka > Ardha-Prapathaka > Dasati > Rca > Pada`),
   corroborating the level *vocabulary*.

   > **CORRECTED 2026-09-07 by `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE`.** This item
   > previously also credited TITUS with corroborating *"that there are exactly four
   > arcikas."* **It cannot** — TITUS is Pandey lineage, as the very next paragraph of this
   > document states, so on any question of *arity* it is the **same witness** as GRETIL.
   > Withdrawing that leaves the four-arcika claim with **1 witness, 0 independent
   > corroborations and 6 independent contradictions.** See §7 item 1 and
   > [`SAMAVEDA_ADDRESSING_STABILITY.md`](reports/SAMAVEDA_ADDRESSING_STABILITY.md).
   > Two further defects in this section, both found in the same run: the **DECADE** claim
   > for Griffith is cited to `data/raw/wikisource_griffith_sv/…7fe81ea….php`, which
   > contains `Decad`/`ecade` **zero times** — the claim is true but the evidence lives in
   > the unsnapshotted `sacred-texts.com/hin/sv.htm`; and `source_artifacts.yaml` asserts
   > Griffith Part II has **six** Books against Kauthuma's nine, where the measured figure
   > is **15 BOOK headings = 6 (Part I) + 9 (Part Second)**, so Part Second matches Kauthuma
   > exactly. That wrong count was the sole *structural* support for the recension-mismatch
   > verdict; the verdict still stands on Griffith's preface, but the number is withdrawn.
   **Its text is NOT independent** — the page carries
   `Copyright (C) 1998, 1999 Anshuman Pandey`, so it is a re-publication of the same
   e-text. Gippert's 8-level scheme is his own editorial analysis layered on that text.
   Citation authority only; its terms forbid republication.

**Same-text re-publications — 3, counting as ONE witness:** GRETIL, sanskritdocuments and
TITUS all carry the same Pandey 1998/99 e-text. **Their agreement is not corroboration.**
The Pandey root is now read directly off the artifact at three re-publishers rather than
inferred at two, which strengthens rather than weakens that caution.

An earlier draft of this document claimed "four independent witnesses". That overstated
the corroboration and is corrected here. The hierarchy conclusion is unaffected — the
level names agree across every witness, the selected source declares its own reference
system verbatim, and `Adhyaya`/`Khanda` remain wrong — but the *strength* of the
corroboration is two textual witnesses, not four.

The GRETIL declaration:

```
REFERENCE SYSTEM:
arcika | prapathaka | ardha | dasati | verse | line
1 1 1 01 01 a
```

| Level | `entity_type` | Key fragment |
|---|---|---|
| Arcika | `STRUCTURAL_CONTAINER` | `A{arcika}` |
| Prapathaka | `STRUCTURAL_CONTAINER` | `P{prapathaka:02d}` |
| Ardha | `STRUCTURAL_CONTAINER` | `R{ardha}` |
| Dasati | `STRUCTURAL_CONTAINER` | `D{dasati:02d}` |
| Verse | `MANTRA` | `V{verse:02d}` |

The **candidate** key and URN forms, implemented in `sv_mantra_identity` and
`sv_container_identity` and recorded so the research is not lost and so freezing later is
a purely additive change. They are candidates, not declarations:

- Mantra key: `VG:SV:KAU:A{arcika}:P{prapathaka:02d}:R{ardha}:D{dasati:02d}:V{verse:02d}`
- Mantra URN: `urn:vedagraph:mantra:samaveda:kauthuma:arcika:{a}:prapathaka:{p}:ardha:{r}:dasati:{d}:verse:{v}`
- Container URN: `urn:vedagraph:section:samaveda:kauthuma:arcika:{a}[:prapathaka:{p}][:ardha:{r}][:dasati:{d}]`

Both functions carry a NOT FROZEN warning in their docstrings, and nothing may treat
their output as canonical Samaveda identity.

**This supersedes the earlier VHP-derived guess** of
`[Arcika, Prapathaka, Ardha, Adhyaya, Khanda, Mantra]`. The fourth level is the
**Dasati**; there is no Adhyaya and no Khanda identity level. A test asserts that the
superseded names cannot creep back in.

`line` (`a` / `c` / `e`) is a sub-verse pāda label. It is the sixth declared level of the
source's reference system and is **deliberately not an identity level**: the mantra is
the verse. `line` never appears in `hierarchy`, `native_labels` or `structural_path`.

**Depth is not uniform**, and this is the load-bearing fact of the whole model:

| Arcika | Prapathaka | Ardha | Dasati | Verses |
|---|---|---|---|---|
| 1 Purvarcika | 1–6 | 1–2 | 1–10 across the ardha | 585 |
| 2 Aranya | **absent (0)** | **absent (0)** | 1–5 | 55 |
| 3 Mahanamnya | **absent (0)** | **absent (0)** | **absent (0)** | 10 |
| 4 Uttararcika | 1–9 | 1–2, or 1–3 for prapathaka 6–9 | resets per ardha | 1,218 |

The four **blocks** are **Purvarcika, Aranya, Mahanamnya and Uttararcika**, in that order.

> **CORRECTED 2026-09-07 by `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE`.** This paragraph
> previously read *"four, not the two that earlier notes recorded."* **That inverted the
> evidence.** The "two" was **right** as the *top-level* division, and this correction is
> now tracked as the open blocker dimension `arcika_arity`.
>
> Every witness holds the **same four blocks in the same order** — that much is not in
> dispute. They disagree on **how to bracket them**, and therefore on what number the *top
> slot of the key* takes:
>
> | Arity | Witnesses |
> |---|---|
> | **4 flat siblings** | GRETIL, TITUS — **both Pandey lineage, i.e. ONE witness** |
> | **2 top-level** (Chandas / Aranya / Mahanamnya being the three *sub-segments of the Purvarcika*) | Sanskrit Wikisource, Griffith 1895, Wikipedia, Vedic Heritage Portal (GoI), Vedapeetha, B. R. Sharma HOS 57 |
> | **3** | Caland / Kashikar |
>
> So: **1 witness, 0 independent corroborations, 6 independent contradictions.**
>
> This is not academic. **Two hard coordinate collisions were verified on both sides.**
> Tuple `(1,1,2,6)`: Wikisource `1.1.2.6` = Purvarcika / chandas / **prapathaka 2** /
> dasati 6 = running verses **145–154**, while GRETIL `1 1 2 06` = arcika 1 /
> **prapathaka 1** / **ardha 2** / dasati 6 = running verses **55–62** — disjoint. And slot
> 1 value `2`: GRETIL reads Aranyarcika (55 verses), every other witness reads Uttararcika
> (**1,225 verses**) — so Wikisource `1.2.1` = RN 586–594 while GRETIL `1 2 1` = RN 97–144,
> **the same literal address string over disjoint passages.**
>
> The table above this note describes **the selected artifact's encoding**, which is
> accurate and is retained as such. It must not be read as the settled arity. See
> [`SAMAVEDA_ADDRESSING_STABILITY.md`](reports/SAMAVEDA_ADDRESSING_STABILITY.md) §4–§5.

**Scope limit — this is not a caveat, it is a boundary.** `VG:WORK:SV:KAU` addresses the
arcika (verse) text **only**. The Kauthuma gana collections — roughly **2,639 ganas**
across gramageya, aranyakageya, uha and uhya/rahasya, against **1,875 arcika verses** —
are a parallel and *larger* body that this `work_id` does not cover and cannot address.
The sung dimension is not a decoration on the verse skeleton; it is the reason the
Samaveda is a distinct Veda rather than a Rigveda excerpt.

**Any claim that VedaGraph "has the Samaveda" while holding only the arcika is false.**
The ganas require their own `work_id`. Sanskrit Wikisource carries all four gana books as
reusable text, so this is real future work rather than a hypothetical.

The fourth slot is deliberately given **no fixed cardinality**. A Purvarcika dasati is a
true decad numbered 1–10 across the ardha; an Uttararcika dasati resets inside each ardha
and holds two or three verses. Same slot name, different unit. Nothing in the codebase
encodes "ten verses per dasati".

---

## 3. Variable depth without breaking the three-level assumption

Rigveda relies on three fixed levels. Samaveda has five, two of which may be absent.
Both are represented by the same records, by four mechanisms:

**1. Depth lives in the data, not the schema.** `hierarchy` is
`dict[str, int | str]`, so it holds two entries for Vajasaneyi and five for Samaveda.
No fixed `mandala` / `sukta` / `mantra` columns exist anywhere in `Passage`.

**2. Absence is a value, not a gap.** The selected Samaveda edition encodes an absent
level as a literal `0`. VedaGraph preserves that rather than omitting the key, so a
5-slot address stays positionally parseable and an Aranya verse is
`VG:SV:KAU:A2:P00:R0:D03:V01`. `identity.py` therefore applies `_non_negative` — not
`_positive` — to Samaveda's `prapathaka` / `ardha` / `dasati`. Applying the
positive-integer rule there would reject 65 real verses. **`_positive` is retained
unchanged for every other work**, so no RV, VSM or AVS level can ever be `0`.

**3. "Absent" and "not addressed" are different facts.** `sv_container_identity`
distinguishes them: `None` means "this level is not part of this container's address"
and truncates the key; `0` means "the source marks this level absent in this arcika" and
is retained. So `VG:SV:KAU:A2` (the arcika as a whole) and `VG:SV:KAU:A2:P00` (its
absent-prapathaka container) are distinct nodes. Supplying a gap in the chain raises.

**4. Container depth is expressed by truncation, not by a depth field.** A container's
key is the prefix of its descendants' keys, so `parent_key` chains are derivable and
`ORDER BY canonical_key` is a valid structural sort within a work.

**Nothing about the Rigveda changed.** Not one field was renamed, not one enum member
removed, not one URN altered. The Rigveda corpus validates against the extended models
and re-derives its UUIDs identically (Section 6).

---

## 4. `EntityType` and `AlignmentLevel` extension decisions

### `EntityType`: one member added, none renamed

```
WORK | SECTION | HYMN | STRUCTURAL_CONTAINER | MANTRA
```

`SECTION` and `HYMN` are RV-derived names promoted into a shared vocabulary before there
was anything to share it with. They are now **frozen by the sealed corpus and must never
be renamed** — 11,590 committed passages serialize those strings.

But neither name generalizes. A Samaveda Ardha is not a "section" in the sense a Mandala
is, and a Dasati is emphatically not a hymn. Rather than stretch `HYMN` to cover
whatever sits one level above the leaf — which is exactly how false equivalence gets
built — a single generic member was added:

- Use `SECTION` / `HYMN` where the work genuinely has section- and hymn-shaped
  containers: Rigveda (Mandala / Sukta) and Atharvaveda (Kanda / Sukta).
- Use `SECTION` for a work with exactly one container that is not a hymn: Vajasaneyi
  (Adhyaya).
- Use `STRUCTURAL_CONTAINER` for containers that are neither, at any depth: all four
  Samaveda container levels. The real level name is carried in `native_labels`.

Named members per Samaveda level (`ARCIKA`, `PRAPATHAKA`, …) were rejected: the enum
would then grow with every recension ingested forever, and the level name is already
recorded, per-record, in `native_labels` where it can be edition-specific.

**The accepted cost, stated plainly.** Because Samaveda labels all four of its non-leaf
depths `STRUCTURAL_CONTAINER`, `entity_type` no longer identifies *which* level an SV
passage occupies — only its depth does. Nothing in `entity_type` stops a build from
labelling a Prapathaka and a Dasati identically and mis-nesting them. QA checks therefore
derive an SV passage's level from its depth against the work's declared `hierarchy`, not
from `entity_type`. This is the strongest argument for **populating `native_labels` and
`structural_path` rather than leaving them empty**: for variable-depth works they are the
only per-record fields that can catch a mis-nesting.

### `AlignmentLevel`: one member added, symmetrically

```
WORK | SECTION | HYMN | STRUCTURAL_CONTAINER | MANTRA
```

Without this, a translation aligned to a Vajasaneyi Adhyaya or a Samaveda Dasati would
have to claim `HYMN` alignment it does not have. That is a false claim about a
translation's precision, which is a correctness problem, not a cosmetic one.

### `RightsStatus`: `CC0` added

Requested by the rights/provenance owner. `CC0` is a 1.0 Universal public-domain
*dedication* — an explicit waiver — which is not the same fact as `PUBLIC_DOMAIN`, a
status reached by law. Collapsing them would lose the distinction. Twelve existing
members are unchanged; `APACHE_2_0`, `PERMISSION_GRANTED`, `RESEARCH_ONLY` and
`EXTERNAL_REFERENCE_ONLY` are all in live use and were explicitly retained. The
vocabulary is closed at 13 and asserted by exact-set test, so growing it stays a
decision rather than a silent drift.

---

## 5. False equivalence: what this model explicitly refuses to unify

Each refusal below is a place where unification would be easy, would look tidier, and
would destroy information.

**1. A "Sukta" level for works that have none.** Vajasaneyi is `Adhyaya -> Mantra`.
Samaveda's organization is its own. Inserting a synthetic hymn level to make all four
Vedas three-deep would fabricate a structural claim no edition makes. Asserted by test.

**2. `Adhyaya` and `Khanda` as Samaveda identity levels.** They came from reading VHP
web pages, not a source record. The selected edition declares `dasati`. The guess is
superseded and tested against.

**3. A single running mantra number as Samaveda identity.** Both witnesses print a running
verse number 1..1875. It is recorded as a `Citation` with `is_canonical=False` and never as
identity, and the refusal has been **independently strengthened twice** since it was first
made.

> **CORRECTED 2026-09-07.** This refusal previously justified itself by calling the
> apparatus *"defective: five values absent (1035, 1133, 1179, 1211, 1592) and one
> duplicated (1181)"*, and by citing a *"count gap of 1,868 structural verse keys against
> the edition's own 1,875 claim."* **Both figures are refuted, and §7 of this same document
> plus three registries already said so** — this paragraph was missed when they were
> corrected.
>
> What is actually true. The rejected artifact prints **exactly 1,875** markers; four of
> the five "absent" values are **printed** and were lost to parser regex strictness. The
> selected witness prints **1,872** distinct markers and recovers all four of them
> (1035, 1133, 1211, 1592). Only **1179** is genuinely unprinted — by *either* lineage,
> which is what makes the identification firm. The count equation is
> `1875 = 1872 printed + 3 the selected witness does not print`, residue 0.
>
> **The refusal itself stands, on better grounds than the ones it was originally given.**
> (a) The one located printed edition carries **no continuous 1..1875 series at all**, only
> a per-section counter that resets, so the running number is attested by the hand-keyed
> wiki text and the Pandey lineage and by no print. (b) It is **not injective**: 1181 sits
> on two addresses in both lineages. A non-injective, print-unattested number cannot be an
> identifier. It is, however, the correct *alignment axis* between witnesses, and the
> cross-witness structural comparison uses it as exactly that.

The dasati-local verse index used by the frozen key is *derived* from this running number's
arithmetic and fails closed where the arithmetic does not close — which is a different
thing from using the number as identity.

**4. Samaveda kanda as a tree level.** The named kanda division (agneya, aindra,
saumya-pavamana, aranya) does not nest: its colophons cut *across* prapathaka and ardha
boundaries. A non-nesting division cannot be a hierarchy level without lying about the
tree. It is an alternate `Citation` system.

**5. Gana collections inside the Samhita work.** The selected artifact is the arcika
(verse) text only and contains no Gramageya / Aranyageya / Uha / Uhya material. There is
no gana slot in the Samaveda key. Gana collections, if ever ingested, get their **own
`work_id`** — they are a different organization of the same words, not a deeper level of
this one.

**6. `line` / pāda as a mantra.** Samaveda's sixth declared level is a sub-verse label.
The mantra is the verse. Sub-verse addressing is a future concern for annotation layers,
not an identity level.

**7. Metrical versus prose status as canonical structure.** Atharvaveda's paryāya units
are addressed like any other passage. Whether a unit "is verse" is interpretation and
lives in `SourceAssertion`.

**8. Alternate citation numbers inside `Passage`.** An `alternate_citations` field on
`Passage` was considered and **rejected**. `Citation` already exists with `system`,
`label`, `source_id` and `is_canonical`. Duplicating it onto `Passage` would merge two
record types and lose the per-citation source attribution. Alternate systems — the
Samaveda running number, its kanda division, Atharvaveda's Vishva Bandhu numbering —
are all `Citation` rows.

**9. "No number in this system" as a flag on `Citation`.** The Atharvaveda source prints
`[-]` at AVS 20.96.22 to mean the alternate system has no corresponding number. That is
an assertion *about a source*, so it belongs in `SourceAssertion` with its
`source_locator` and the verbatim marker — strictly more faithful than a boolean, and it
does not widen a shared contract for one edition's convention.

**10. An edition's in-text marker treated as "the source's own number".** These can be two
different editions' counts inside one file. In Atharvaveda Kanda 7 the printed `||N||`
markers carry the Bombay (Major Anukramani) count while the locators carry the Berlin
(Roth/Whitney) count, because the Bombay edition splits hymns 6, 45, 68, 72 and 76 each
into two. A parser that "corrects" locators from in-text markers would silently convert
a whole book into a different edition's numbering *while looking like it was fixing
typos*. **The rule is: treat a numbering marker as an edition-relative claim, never as
ground truth — store both witnesses, promote neither.** Each becomes its own `Citation`,
and a disagreement between them is recorded as a `SourceAssertion` rather than resolved.
This generalises to every work: agreement between two numbering witnesses is evidence,
and disagreement is *also* evidence, but neither licenses overwriting one with the other.

This is a validated detector, not an anecdote: an independent label-versus-marker
disagreement check flagged **all six** of the renumbering points Whitney names in HOS 7
p. 389 — 6/6, zero misses and zero false negatives.

**11. A text layer extracted by editorial judgement treated as primary.** A Vajasaneyi
layer built by lifting mantra quotations out of a commentary block has boundaries the
source never declared — deciding where each quotation begins and ends is a judgement.
Labelling it `PRIMARY_TEXT` would make an interpretive segmentation canonical, which the
core principle forbids; `NORMALIZED` and `LINGUISTIC_ANNOTATION` would both be false
claims about what was done to it. `TextRole.EXTRACTED_FROM_CONTAINER` exists for exactly
this, and a layer carrying it **must never be selected as `primary_sanskrit`**. How the
extraction was performed goes in `TextVersionDescriptor.transformation_provenance`.
Note that rights are unaffected by this: a layer's licence and its permitted *role* are
independent, and getting the rights right does not make a layer primary.

**The governing principle, which generalises past this one layer: a role describes the
layer AS PRODUCED, not the structure the source could support.** The worked example is
instructive. The registry first assigned this role believing the mantras were fragments
quoted inside running prose. The Yajurveda owner disagreed and *tested* rather than
argued, showing the 1929 edition uses a standard mūla-bhāṣya layout with ordinal headers
— 271 ordinal-header lines against 293 accented records across six adhyāyas — so the mūla
genuinely is a declared structural level and the original premise was wrong. The role
nevertheless stood, because the adapter does not read that declared boundary: it infers
the mūla start from accent presence and is wrong in 3 of 40 adhyāyas by its own
measurement, and the produced layer embeds a variant-selection judgement (at VSM 16.37
the page prints the mantra twice, and the layer silently keeps the first). A layer that
picks one of two attested printed readings is not a transcription of a declared boundary,
whatever the edition could have supported.

**Roles are therefore downgradable and upgradable on implementation evidence, and the
upgrade condition is written into the record rather than left to memory.** Here: if the
adapter reads the ordinal headers that were proven to exist and the outstanding
`NEEDS_REVIEW` assertions are resolved, `PRIMARY_TEXT` becomes correct. Recording the
condition is what keeps a conservative role reviewable instead of permanent.

**12. One rights verdict per Veda.** Rights are per-artifact **and per-role**. A Veda
whose Sanskrit text is clear may have an UNKNOWN Hindi translation and
REFERENCE_ONLY audio. Nothing in this structural model assumes a single rights verdict
per work.

**13. One build configuration for all works.** See ADR-018. `CorpusBuildConfig` is
Rigveda-specific and stays that way; other works use `WorkBuildConfig`.

**14. `SuktaDiscoveryRecord` for works without suktas.** It requires `sukta_number`,
`mandala_number` and `parent_mandala_key`. It is left untouched because 2,247 sealed
records depend on it; `SectionDiscoveryRecord` is the generic form.

---

## 6. Rigveda compatibility

Re-validated after every contract change in this document:

| Check | Result |
|---|---|
| `passages.jsonl` validates against extended `Passage` | 11,590 / 11,590, 0 invalid |
| `entity_type` histogram | `SECTION` 10, `HYMN` 1,028, `MANTRA` 10,552 |
| `uuid5(namespace, canonical_urn)` re-derived and compared | 11,590 checked, **0 mismatched** |
| `rv_*_identity()` round-trip of key + URN + UUID | 11,590 checked, **0 mismatched** |
| All 13 canonical record files | 0 invalid records |
| Knowledge + lexical layers | 0 invalid records |
| Cross-work key / UUID collisions | 0 across 11,903 passages |

New optional fields carry empty defaults and are absent from the JSON Schema `required`
array, which is why records written before they existed still validate.

---

## 7. Open items

1. **Samaveda identity is blocked, but the blocker is now narrow and actionable.**
   `identity_status` is `RESEARCH_REQUIRED` and `key_pattern` is `null`. The blocker is
   **not** "no witness exists" — four now do. It is that **no witness combines an
   identified printed edition with redistribution rights**:
   - The GRETIL TEI was adjudicated unusable on two independent grounds: its rights (the
     upstream it names self-declares reference-only and forbids modification, so the
     CC BY-NC-SA 4.0 on the 2020 TEI is a blanket licence the upstream never granted) and
     its edition identity (`<sourceDesc><bibl>` is empty).
   - Other Pandey-lineage re-publishers do not help. Every one traces to the same
     1998/1999 data entry, so two of them agreeing is **the same defect twice, not
     corroboration**. That principle generalises beyond Samaveda and is worth applying
     whenever two sources "agree".
   - Sanskrit Wikisource clears the **rights** bar (CC BY-SA 4.0) but not the **edition**
     bar: it is a community transcription with no single named printed edition.
   - TITUS is citation authority only; its terms forbid republication.

   Resolution therefore requires an identified printed Kauthuma edition that is also
   redistributable — by written consent from the data-entry rights holder, by a fresh
   transcription from a public-domain printed edition, or by tracing the Wikisource pages
   to a named edition.

   > **SUPERSEDED IN PART, 2026-09-07, by `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE`.**
   > Read [`SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE.md`](reports/SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE.md)
   > before acting on the paragraph above. Three things changed:
   >
   > 1. **The edition question is settled and was NOT the binding constraint.** The pinned
   >    corpus is now shown *positively* to be a hand-keyed community transcription with no
   >    printed antecedent — not scan-backed, no front matter (proven by enumerating all 908
   >    titles), zero links to any Sāmaveda scan across 840+ pages, contributor testimony of
   >    *ṭaṅkaṇam* ("typing"), and both prior candidate editions refuted. **There is no
   >    edition to find.** A 5-volume PD printed edition *was* located (Sāmaśramī,
   >    Bibliotheca Indica 1874–78) but its **recension is not established**, so ADR-017's
   >    first bar is still not cleared.
   > 2. **The governance question is answered: edition identity is NOT required to freeze
   >    Passage identity.** Identity is mechanically source-blind, the registry's own
   >    layering puts `source_edition` at the artifact level and `underlying_edition` at the
   >    text_version level with **neither in `works.yaml`**, and **no** RV/YV/AV entry names
   >    an edition while all three are `FINAL`. Requiring the Wikisource edition *in order to
   >    freeze the ID* is a category error.
   > 3. **The real blockers are elsewhere**, and both are new: **referent integrity** (7
   >    addresses absorb 9 printed verses by concatenative merge; `VG:SV:KAU:A4:P04:R2:D01:V13`
   >    denotes a verse that does not exist; repairing them moves 5 referents under
   >    byte-identical UUIDs, undetectably) and **arcika arity** (see §5.2 above).
   >
   > **The count gap is no longer open.** The sentence below is retained for the audit trail
   > and is **wrong on both counts**: the gap is `RESOLVED` with `UNRESOLVED_COUNT_RESIDUE = 0`,
   > and the pāda-mislabel is *not* its explanation. The source prints **exactly 1,875**
   > markers; the identity is `1875 = 1868 − 2 markerless + 9 surplus`. See
   > [`SAMAVEDA_COUNT_RECONCILIATION.md`](reports/SAMAVEDA_COUNT_RECONCILIATION.md).

   ~~A separate 7-verse count gap (1,868 structural keys against the edition's own 1,875
   claim) also remains open, and is itself partly explained by the pāda-mislabel corruption
   above.~~
2. **Documents that still carry the superseded Samaveda claim** and are not owned by the
   shared-contract writer: `docs/STATUS.md` (lists Samaveda under BLOCKED, and its one
   Samaveda line predates all four-Veda work).

   > **CORRECTED 2026-09-07.** This item previously also named
   > `docs/architecture/ID_SPEC.md` and `docs/architecture/SOURCE_POLICY.md`. **Both were
   > already current** and are removed from the list: `ID_SPEC.md` correctly states
   > `RESEARCH_REQUIRED` / `key_pattern: null` / candidate-only, and `SOURCE_POLICY.md`
   > explicitly marks its old bullet `SUPERSEDED AS A HIERARCHY SOURCE` and gives the correct
   > five levels. **A stale-claim list that itself goes stale is the hazard it exists to
   > prevent** — and note the irony now recorded in §5.2: `SOURCE_POLICY.md`'s "two arcikas",
   > cited here as an error, was **right** about the top-level division.
   >
   > **One document was missing from this list and carried a claim that was never true.**
   > `docs/reports/FOUR_VEDA_QA_REPORT.md` asserted that `key_pattern` "is now set" and that
   > `identity_status` had moved to `PROVISIONAL`. No such state exists in any commit. It is
   > corrected in place, and the miss is analysed in
   > [`docs/qa/STALE_FOUR_VEDA_CLAIMS.md`](qa/STALE_FOUR_VEDA_CLAIMS.md).
3. **Sub-verse (pāda / `line`) addressing** is unmodelled by design. When an annotation
   layer needs it, it should be a separate record type keyed to a mantra, not a sixth
   hierarchy level.
4. **Rights, not structure, are the binding constraint on three of four Vedas.** Per the
   rights owner: English translation is rights-clear for all four Vedas; primary Sanskrit
   is rights-clear for exactly one (Rigveda); Hindi for none; audio is REFERENCE_ONLY for
   all four. This structural model can represent all four works today. That is not the
   same as being permitted to ingest them, and the two must not be confused when judging
   readiness.
5. **`CorpusBuildConfig` and `WorkBuildConfig` coexist.** Rigveda is not expressed as a
   `WorkBuildConfig`; doing so is a rebuild-scale change, deliberately not attempted. See
   ADR-018.
6. **`SectionDiscoveryRecord` has no QA consumer yet.** The count-reconciliation check in
   `qa/checks.py` is keyed on `(mandala, sukta)` and is owned by the QA owner. Until it is
   generalised, non-Rigveda works reconcile counts in their own modules.
