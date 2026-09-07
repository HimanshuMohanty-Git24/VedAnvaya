# Sāmaveda Ārcika Arity — How the Blocker Was Closed Without Being Adjudicated

**Run:** `SAMAVEDA_REFERENT_INTEGRITY_REPAIR` · **Date:** 2026-09-07
**Starting commit:** `5896856` · **Work:** `VG:WORK:SV:KAU` (Kauthuma, ārcika corpus only)
**Dimension:** `arcika_arity`, `OPEN_PHILOLOGICAL_REVIEW` → `RESOLVED`
**Verdict:** `DISSOLVED_AS_AN_IDENTITY_QUESTION` — the philological dispute is still open; it is
no longer capable of moving a canonical key.

This document is about **ADDRESSING, not textual reuse.** No encumbered Sanskrit is reproduced
anywhere in it — level names, page titles, counts, addresses and printed running numbers only.

---

## 0. Verdict

### `ARITY_DISSOLVED_AS_AN_IDENTITY_QUESTION`

The blocker did not close because the arity was settled. It closed because the key stopped
depending on it.

- The superseded candidate key put a **bare ordinal** in its top slot. That ordinal has no stable
  denotation across witnesses, so the key could not be frozen while the dispute stood.
- The repaired key **names the four sub-collections and numbers nothing.** Every witness holds the
  same four blocks, in the same order, with the same extents. Naming them records exactly what is
  agreed.
- The bracketing question moves to the **container spine**, where revising it renumbers **no key**.
  That is the property the ordinal scheme lacked and the precise reason arity had to block a
  freeze before.

**What is NOT claimed.** Whether the Kauthuma saṃhitā "has" two, three or four top-level ārcikas
is not answered here and is not answerable from the evidence reached. §11 states what is still
open and why none of it is an identity blocker any more.

---

## 1. The problem — an ordinal in the top slot

The superseded candidate key was:

```text
VG:SV:KAU:A{arcika}:P{prapathaka:02d}:R{ardha}:D{dasati:02d}:V{verse:02d}
```

Slot 1 was an ordinal, and the ordinal's denotation is witness-dependent.

| Collision | Coordinate | Pandey e-text lineage reads | Every independent witness reads | Overlap |
|---|---|---|---|---|
| **A — top slot, largest blast radius** | slot 1 value `2` | **Āraṇyārcika**, 55 verses, running 586–640 | **Uttarārcika**, 1,225 verses, running 651–1875 | **none** |
| **B — 4-number tuple** | `(1, 1, 2, 6)` | GRETIL label `1 1 2 06` = running 55–62 | Wikisource `1.1.2.6` = running 145–154 | **none** |

**Blast radius, MEASURED: 1,280 of 1,875 verses** are mis-addressed if slot 1 is instantiated on
the wrong reading (55 Āraṇya + 1,225 Uttara). Collision A is airtight because it was verified
against live artifacts on *both* sides; see `docs/reports/SAMAVEDA_ADDRESSING_STABILITY.md` §5.

An ordinal whose value depends on which witness you asked **MAY NOT enter a canonical key.** That
is the whole of the blocker, and it is a property of the key, not of the text.

---

## 2. Witness tally

Counted exactly, so it cannot be inflated. **The lineage collapse matters more than the raw
count:** GRETIL, TITUS and sanskritdocuments are three re-publications of one Pandey 1998/99
e-text, so their agreement is one witness, not three.

| Arity | Witnesses | Independent count |
|---|---|---|
| **4** | GRETIL TEI · TITUS · sanskritdocuments — **all three are the Pandey 1998/99 e-text** | **1** |
| **2** | Sanskrit Wikisource · Griffith 1895 (translating Benfey; **predates Pandey by a century**) · Wikipedia · Vedic Heritage Portal (Government of India) · Vedapeetha · B. R. Sharma HOS 57 (vol 1 = Pūrvārcika, vol 2 = Uttarārcika) | **6** |
| **3** | Caland / Kashikar (Pañcaviṃśa-Brāhmaṇa introduction) | **1** |

The four-ārcika reading therefore stands on **1 witness, 0 independent corroborations, 6
independent contradictions.** Registry mirror: `arcika_arity_witness_count: {four: 1, two: 6,
three: 1}` in `data/source_registry/four_veda_canonical_sanskrit_blockers.yaml`.

---

## 3. The selected witness states its own arity

The selected witness is not silent on the question, and it does not need to be interpreted.

- Its root page `सामवेदः/कौथुमीया/संहिता` (**revid 364594**) numbers the top level itself:
  `१. पूर्वार्चिकः (१ - ६५०)` and `२. उत्तरार्चिकः (६५१ - १८७५)`.
- Its Pūrvārcika index page (**revid 131420**, MEASURED present in the pinned corpus) asserts the
  three-way internal split with exact ranges: `छन्द आर्चिकः (१- ५८५)`,
  `अथारण्यार्चिकः (५८६ - ६४०)`, `महानाम्न्यार्चिकः (६४१ - ६५०)`.

So the witness declares **two** top-level ārcikas and **three** sub-segments inside the first. It
is internally consistent and it contradicts the ordinal the superseded key encoded.

> **Provenance caveat, stated rather than buried.** The Pūrvārcika index revid 131420 is
> reproducible from the pinned snapshots. The root page `…/संहिता` (revid 364594) is **not in the
> 106-page pinned set** — the fetch was scoped to `पूर्वार्चिकः` and `उत्तरार्चिकः` subtrees. Its
> two numbered ranges are therefore **INFERRED from an unpinned live read**, not MEASURED from a
> snapshot. Nothing in the key depends on it: the same 650/1225 split is independently carried by
> the Vedic Heritage Portal, Wikipedia and HOS 57.

---

## 4. The live page tree, enumerated

**MEASURED** by re-parsing all pinned snapshots under `data/raw/wikisource_sa/2026-09-07/`
(106 files carrying a `parse` payload; 150 metadata files exist, 44 carry no payload and are
excluded).

| Branch | Pages | Composition |
|---|---|---|
| `…/संहिता/पूर्वार्चिकः` | **74** | 1 root index + `छन्द आर्चिकः` 66 + `अथारण्यार्चिकः` 6 + `महानाम्न्यार्चिकः` 1 |
| `…/संहिता/उत्तरार्चिकः` | **32** | 1 root index + 9 prapāṭhaka indexes + **22 ardha leaves** |
| **Total ārcika pages** | **106** | |
| gāna branch (`ऊहगानम्` 362, `ग्रामगेयः` 190, `ऊह्यगानम्` 87, `आरण्यकगेयः` 86) | **~725** | **out of scope for this work_id** |

**Leaf pages: 87** = 59 Chanda daśati + 5 Āraṇya daśati + 1 Mahānāmnya + 22 Uttarārcika ardha.
Matches the registry's `selected_witness_leaf_pages: 87`.

### 4.1 The two ārcikas have different hierarchies

This is the structural fact that decides the key shape.

| Collection | Substructure, MEASURED | Levels between collection and verse |
|---|---|---|
| **छन्द आर्चिकः** | 6 prapāṭhakas holding **10, 10, 10, 10, 10, 9 = 59** daśati leaf pages | prapāṭhaka, daśati — **no ardha level** |
| **अथारण्यार्चिकः** | **5** daśati leaf pages, titled `1.2.1 प्रथमा दशतिः` … `1.2.5 पञ्चमी दशतिः` | daśati only — **no prapāṭhaka level** |
| **महानाम्न्यार्चिकः** | **1** page carrying all 10 verses directly | **none** |
| **उत्तरार्चिकः** | 9 prapāṭhakas whose leaf pages are **ardha** pages, counts `[2,2,2,2,2,3,3,3,3] = 22` | prapāṭhaka, ardha, daśati — the daśati is printed **inside** the ardha page as a numeral, **it is not a page level** |

A single fixed five-slot address cannot describe that. The superseded key described it anyway, by
writing a literal `0` into the slots a collection does not have — which made an edition's
flattening choice part of canonical identity.

---

## 5. The decisive finding — "Pūrvārcika" is itself a disputed name

This is the reason the key names the **four sub-collections** rather than the **two top-level
groupings**, and it was not known before this run.

| Witness | Extent of the name "Pūrvārcika" |
|---|---|
| Sanskrit Wikisource | **650** (1–650) |
| Vedic Heritage Portal (GoI) | **650** (Āgneya 114 + Aindra 352 + Pavamāna 119 + Āraṇya 65) |
| Wikipedia | **650** |
| B. R. Sharma, HOS 57 | **650** (vol 1 = Pūrvārcika) |
| Caland / Kashikar | **585** — "Pūrvārcika, in 6 prapāṭhakas", with the Āraṇyaka-Saṃhitā a **separate** collection |
| Vedapeetha | **585** — "The Pūrvārcika part has 585 single verses" |

**So the "2 vs 3" dispute is not a disagreement about the text at all. It is a disagreement about
how far one NAME reaches.** Both readings describe the same 650 verses in the same order; they
differ on whether the last 65 are inside the name or beside it.

By contrast:

| Sub-collection | Extent | Disputed by |
|---|---|---|
| Chanda | **585** | nobody |
| Āraṇya | **55** | nobody |
| Mahānāmnya | **10** | nobody |
| Uttara | **1,225** | nobody |

The four sub-collection extents are agreed by **every** witness without exception, **including the
rejected one** — GRETIL's own flat ārcikas 1/2/3/4 have exactly these extents. Keying on the four
names is therefore **strictly more defensible** than keying on the two: it is the finer partition,
and the finer partition is the one nobody contests.

---

## 6. Mahānāmnya placement — not a contradiction, two functions

The Mahānāmnya's 10 verses appear in two places in the witness tree, and this is often mistaken
for an inconsistency. It is not.

1. **In the ārcika (verse) collection**, its 10 verses **ARE part of the 650** — Wikisource
   numbers them 641–650. The Vedic Heritage Portal and Wikipedia count them **inside** the Āraṇya
   sub-part, which is how they reach Āraṇya = 65 (55 + 10) rather than 55.
2. **In the song-books**, Caland records that the mahānāmnīs are an **appendix to the
   āraṇyakageya-gāna**. This is why the live tree also carries
   `सामवेदः/कौथुमीया/संहिता/आरण्यकगेयः/परिशिष्टः/महानाम्न्यार्चिकः` in the gāna branch.

**Same 10 verses, two functions.** The gāna occurrence is out of scope for `VG:WORK:SV:KAU` and
addresses nothing this key addresses. The 55-vs-65 Āraṇya figure is a **naming choice about where
to book the last decade**, not a count disagreement: 55 + 10 = 65 either way, and the key does not
have to choose, because it names Āraṇya and Mahānāmnya separately.

---

## 7. The resolution — the key names the collection and numbers nothing

```text
VG:SV:KAU:CHANDA:P{prapathaka:02d}:D{dasati:02d}:V{verse:02d}
VG:SV:KAU:ARANYA:D{dasati:02d}:V{verse:02d}
VG:SV:KAU:MAHANAMNYA:V{verse:02d}
VG:SV:KAU:UTTARA:P{prapathaka:02d}:R{ardha:02d}:D{dasati:02d}:V{verse:02d}
```

Implemented in `src/vedagraph/identity.py` (`SamavedaCollection`, `SV_COLLECTION_LEVELS`,
`sv_mantra_identity`, `sv_container_identity`); frozen in `data/registry/works.yaml`.

Three properties, each doing specific work:

1. **The top slot is a NAME.** No ordinal, so no witness's bracketing can reinterpret it. The
   1,225-verse collision of §1 becomes **unrepresentable**, not merely avoided.
2. **Each collection carries only the levels it declares.** The literal `0` is gone.
   `_sv_levels` **refuses** a value for an undeclared level rather than coercing it, so a caller
   cannot reintroduce the flattened five-slot address by passing `ardha=0` into Chanda.
3. **Every level is padded to two digits.** The superseded key left the ārcika and ardha slots
   unpadded, which made `A10` sort before `A2`. Fixed width means lexicographic order equals
   coordinate order and no key is a prefix of another.

**The bracketing question now lives on the container spine.** Whether Chanda is a sibling of
Uttara or a child of a Pūrvārcika is a statement about the parent chain of four container rows.
Revising it renumbers **no** mantra key.

> **A defect in the frozen contract's own documentation, recorded rather than smoothed.**
> `src/vedagraph/identity.py:232` still spells the Uttara shape with an **unpadded** ardha,
> `R{ardha}`, in the `sv_mantra_identity` docstring. `_SV_LEVEL_KEY_FORMAT` uses `R{:02d}` and the
> keys the build actually mints are `R01`/`R02`/`R03` — MEASURED in
> `data/source_registry/samaveda_referent_migrations.jsonl`. The docstring is stale, the
> implementation and `works.yaml` are correct, and the discrepancy is cosmetic. Repairing it is
> not an identity change.

---

## 8. Cross-witness measurement

**Structure only.** No encumbered Sanskrit text was read: the comparison uses the GRETIL
artifact's declared reference labels and its printed running numbers, which is the affirmatively
granted use — the artifact carries `verification_roles: [hierarchy, reference_system,
edition_comparison]` while its `bulk_ingestion_status` remains
`PROHIBITED_PENDING_RIGHTS_RESOLUTION`.

Run by `scripts/compare_samaveda_sources.py`; output at
`data/derived/samaveda_cross_witness_structure.json`. The join key is the printed running number,
the one axis both witnesses state directly. It is **not injective on either side** — 1181 is
printed twice in both lineages — so ambiguous values are excluded from the agreement rate rather
than silently first-won.

### 8.1 Join surface

| Quantity | Value |
|---|---|
| GRETIL running values | **1,870** |
| Wikisource running values | **1,873** |
| Shared and unambiguous | **1,867** |
| Join key ambiguous on either side | `[1181]` |
| Only in GRETIL | `1315` |
| Only in Wikisource | `1035, 1133, 1211, 1592` |

**The four Wikisource-only values are EXACTLY the four the count ledger said GRETIL prints but its
parser could not lift.** From `data/source_registry/samaveda_count_ledger.yaml`: 1035 is defeated
by a stray `rm` label prefix; 1133 and 1592 carry a **single** danda where the parser required a
double; 1211 is printed corrupt as `121clsdir`. The repaired Wikisource parser recovers all four.
This is a **mutual confirmation**, not a coincidence: the "five absent running numbers" figure was
a parser configuration, and only 1179 is genuinely unprinted by either lineage.

### 8.2 Agreement

| Level | Compared | Agree | Disagree |
|---|---|---|---|
| **Collection assignment** | 1,867 | **1,867** | **0** |
| CHANDA — prapāṭhaka | 585 | **585** | 0 |
| CHANDA — daśati | 585 | **585** | 0 |
| CHANDA — verse | 585 | **585** | 0 |
| ARANYA — daśati | 55 | **55** | 0 |
| ARANYA — verse | 55 | **55** | 0 |
| MAHANAMNYA — verse | 10 | **10** | 0 |
| UTTARA — prapāṭhaka | 1,217 | **1,217** | 0 |
| UTTARA — ardha | 1,217 | **1,217** | 0 |
| UTTARA — daśati | 1,217 | 1,201 | **16** |
| UTTARA — verse | 1,217 | 1,187 | **30** |

**The 1,867/1,867 collection agreement is the load-bearing number of this decision.** The two
lineages disagree completely about how to *number* the top level and agree completely about which
collection every single verse belongs to. That is precisely the asymmetry a name-keyed top slot
exploits.

**The Uttarārcika daśati/verse disagreements are localized, not diffuse.** All 16 daśati
disagreements fall on four pages — `2.4.1` (6), `2.5.2` (4), `2.4.2` (3), `2.5.1` (3) — the
shifted-heading signature described in the script's own docstring. Those four daśati groups are
**withheld entirely** rather than keyed on a contested partition; see §11 and the registry's
`coverage_equation`.

---

## 9. The ardha sub-decision

Ardha is **present** in the UTTARA key and **absent** from the CHANDA key. Both choices are
evidence-driven, and they point in opposite directions for good reason.

### 9.1 In the Uttarārcika, ardha is load-bearing

**MEASURED** by re-parsing the pinned corpus: in prapāṭhaka 1, **ardha 1 spans daśati 1–23** (23
distinct values) and **ardha 2 spans daśati 1–22** (22 distinct values). The daśati **resets**
inside each ardha.

Dropping ardha would therefore **collapse 22 distinct units onto 22 keys** in prapāṭhaka 1 alone.
Ardha is not derivable there; it carries information no other slot carries.

Corroboration: cross-witness ardha agreement **1,217/1,217**; the cardinality fingerprint
`[2,2,2,2,2,3,3,3,3]` from five witnesses across three lineages; 22 ardha page titles in the
selected witness, all 22 carrying the ardha word (MEASURED, `…ऽर्द्धः`); and a printed colophon in
an identified edition, `इति चतुर्थस्यार्धः प्रपाठकः` (Sāmaśramī vol 1 p. 693).

### 9.2 In the Chanda collection, the selected witness declares no ardha at all

**MEASURED across all 74 Pūrvārcika pages:**

| Measurement | Result |
|---|---|
| Page titles containing the ardha word | **0 of 74** |
| Occurrences of the exact strings `अर्ध` / `अर्द्ध` in wikitext | **0** |
| Occurrences of the `र्ध` / `र्द्ध` cluster in wikitext | 40 |
| …of those, in a heading or list line | **0** |

All 40 cluster hits are **lexical, inside mantra vocabulary** — `ऊर्ध्व-`, `वर्ध-`, `स्पर्ध-`,
`शर्ध-`, `मूर्ध्न-`, `पूर्धि` and the like. **Zero are structural.**

And the daśati already numbers **1–10 continuously across the prapāṭhaka** (MEASURED: prapāṭhakas
1–5 each carry daśati 1–10, prapāṭhaka 6 carries 1–9, total 59). So `ardha = 1 if dasati <= 5 else
2` — an ardha slot would carry **no information**.

### 9.3 However — an identified print DOES assert ardha in the Chanda collection

This is the part that makes the decision non-obvious, and it must be stated rather than skipped.

The Sāmaśramī edition (Bibliotheca Indica, Calcutta 1874–78) prints the colophon
`छन्दस्यार्चिके द्वितीयस्यार्धः प्रपाठकः` at **vol 1 p. 342** — ardha, inside the Chanda
collection, in a named printed edition. And in that print the daśati **resets 1–5 per ardha**:
of the daśati colophons transcribed from vol 1, **30 carry ordinals 1–5 and ZERO carry 6–10.**

So the print's `(prapāṭhaka, daśati)` pair is **ambiguous without ardha.** Two competing
conventions exist for the same collection:

| Convention | daśati numbering | ardha needed to disambiguate? |
|---|---|---|
| GRETIL + Wikisource (both machine-readable witnesses) | **1–10 continuous** across the prapāṭhaka | no |
| Sāmaśramī print | **1–5 per ardha**, resetting | **yes** |

### 9.4 The decision, and the reasoning stated explicitly

**Ardha is excluded from the Chanda key.**

- **Including a redundant ardha** with the continuous 1–10 daśati would make the print's competing
  convention **AMBIGUOUSLY REPRESENTABLE**: the same key shape would be producible by two
  conventions denoting different units, and nothing in the key would say which.
- **Omitting it** makes the print convention **UNREPRESENTABLE** — it **fails closed.** A caller
  holding a Sāmaśramī-convention address cannot mint a well-formed key from it at all, which is
  the correct outcome for an address the frozen convention does not cover.

Failing closed is preferred to failing silently. The print's per-ardha daśati reset is recorded as
an **alternate Citation**, not as a competing canonical value. Both machine-readable witnesses
number the Chanda daśati 1–10 continuously and agree **585/585**.

> ### 9.5 This CORRECTS a claim in `SAMAVEDA_ADDRESSING_STABILITY.md` §6
>
> That report states, of the Pūrvārcika ardha: *"It is redundant in the Pūrvārcika — daśati numbers
> 1–10 continuously across the prapāṭhaka, so `ardha = 1 if dasati <= 5 else 2`, derivable with
> zero information loss."*
>
> **That is true only under the GRETIL/Wikisource convention and FALSE for the identified print.**
> Under the Sāmaśramī convention the daśati resets 1–5 per ardha, so ardha is **not** derivable
> from the daśati — it is the very thing that distinguishes daśati 3 of ardha 1 from daśati 3 of
> ardha 2. The §6 claim should read: *redundant under the convention both machine-readable
> witnesses use, load-bearing under the convention the located print uses.*
>
> The **decision** is unaffected — ardha still stays out of the Chanda key — but the **reason**
> changes from "it carries no information" to "it carries no information *under the declared
> convention*, and admitting it would make a second convention ambiguously representable." The
> weaker reason is the honest one.

---

## 10. Level classification

Every structural level the Kauthuma ārcika corpus exhibits, with its verdict and the evidence that
produced it. `STABLE_CANONICAL_COORDINATE` means it may enter a key.

| Level | Verdict | Justification |
|---|---|---|
| **Ārcika as a bare ordinal** | `EDITION_RELATIVE_COORDINATE` | Value not stable across witnesses; collision verified on live artifacts on both sides; 1,280 of 1,875 verses at risk. **MAY NOT enter a key.** |
| **Ārcika as a collection NAME** | `STABLE_CANONICAL_COORDINATE` | Extents 585/55/10/1225 agreed by **every** witness including the rejected one; collection assignment agrees **1,867/1,867**, zero disagreements. |
| **Grouping name "Pūrvārcika"** | `EDITION_RELATIVE_COORDINATE` | Extent is **585 or 650 depending on witness** (§5). Display / derived only; never keyed. |
| **Prapāṭhaka** (within a named collection) | `STABLE_CANONICAL_COORDINATE` | Arity 6 (Chanda) / 9 (Uttara) across 5 witnesses in 3 lineages; agreement **1,217/1,217** and **585/585**; attested in printed colophons (`इति छन्दस्यार्चिके प्रथमः प्रपाठकः`, vol 1 p. 260). |
| **Ardha (Uttarārcika)** | `STABLE_CANONICAL_COORDINATE` | Load-bearing — daśati resets inside each ardha (MEASURED: P1 ardha 1 = d1–23, ardha 2 = d1–22). Agreement **1,217/1,217**; fingerprint `[2,2,2,2,2,3,3,3,3]`; printed colophon vol 1 p. 693; 22/22 page titles name it. |
| **Ardha (Chanda)** | `SOURCE_ASSERTION_ONLY` | Asserted by the Sāmaśramī print (vol 1 p. 342) with a per-ardha daśati reset; **absent from the selected witness** (MEASURED: 0 of 74 titles, 0 structural occurrences). **Deliberately excluded** from the key so the print convention fails closed rather than aliasing (§9.4). |
| **Ardha (Āraṇya, Mahānāmnya)** | `DISPLAY_ONLY_STRUCTURE`, **properly absent** | No witness asserts one. GRETIL's literal `0` in that slot **encodes absence, not a coordinate**, and treating it as a value is what put an edition's flattening choice into identity. |
| **Daśati (Chanda)** | `STABLE_CANONICAL_COORDINATE` **UNDER A DECLARED CONVENTION** | **585/585** across both machine-readable witnesses, on a 1–10 continuous numbering. **Be honest: this is admitted under a declared convention, not convention-free.** The print's per-ardha 1–5 reset is a real competing convention, recorded as an alternate Citation. |
| **Daśati (Āraṇya)** | `STABLE_CANONICAL_COORDINATE` | 5 daśatis, **no competing convention found in any witness**. MEASURED ranges 586–594 (9), 595–601 (7), 602–614 (13), 615–626 (12), 627–640 (14) — contiguous 586–640, summing to **exactly 55**. Agreement 55/55. |
| **Daśati (Uttarārcika)** | `STABLE_CANONICAL_COORDINATE` **where corroborated** | 1,201/1,217 agree. **4 groups are NOT corroborated and are WITHHELD** — pages `2.4.1`, `2.4.2`, `2.5.1`, `2.5.2`, where the selected witness omits a daśati heading and the second witness contradicts its partition. 21 verses affected; the whole daśati is withheld, so supplying the structure later **adds** keys without renumbering one. |
| **Verse** | `STABLE_CANONICAL_COORDINATE` as a **daśati-LOCAL index** | Derived from the source's own **printed running-number arithmetic** (rank within the daśati's contiguous ascending run) and **never the running number itself**. The derivation fails closed when the run is not contiguous. Document order is never consulted. |
| **pāda / line (`a`/`c`/`e`)** | `DISPLAY_ONLY_STRUCTURE` | Sub-verse label. GRETIL's 6th slot, TITUS's 8th level. Correctly excluded from identity in every scheme the project has held. |
| **Kāṇḍa** (āgneya / aindra / pavamāna / āraṇya) | `EDITION_RELATIVE_COORDINATE`, alternate citation | 114 + 352 + 119 = **585 = Chanda**, and 55 + 10 = **65 = the āraṇya kāṇḍa**, so it maps cleanly onto the collections. But its colophons cut across prapāṭhaka/ardha boundaries, **and HOS 57 vol 1 is subtitled "Kāṇḍas 1–5", so even the arity is contested** (four or five). Cannot be a tree level. |
| **Adhyāya / Khaṇḍa / Sūkta** | `EDITION_RELATIVE_COORDINATE`, alternate citation | Printed in the Sāmaśramī running heads (vol 3 p. 67: `[७ अ० ४ ख० ०२ सू० १,२] उत्तरार्चिकः`). **The 4th-level NAME differs by ārcika:** `दशति` in the Chanda, `सू०` in the Uttarārcika print, where `दशति` appears on **0** pages and `सू०` on **74**. The selected witness shows the same split independently — MEASURED across its 22 Uttarārcika ardha pages: `दशति` on **0**, `सूक्त` on **9**. |

---

## 11. What remains open

**Stated plainly as NOT closed.** None of these is an identity blocker any more.

| # | Open question | What would close it | Status |
|---|---|---|---|
| **O1** | Does the name **"Pūrvārcika" reach 585 or 650?** | A philologist reading **HOS 57 vol 3's introduction** and **vol 1 front matter**. | `OPEN_PHILOLOGICAL_REVIEW`, documentation-only |
| **O2** | **Kāṇḍa arity — four or five?** The 114/352/119/65 scheme gives four; HOS 57 vol 1's subtitle "Kāṇḍas 1–5" gives five. | The same reader, same volumes. | Open; kāṇḍa is an alternate citation either way |
| **O3** | Does the **Sāmaśramī print ever use the word "Pūrvārcika" at all?** | The vol 1 title page. **0 hits across 798 transcribed vol-1 pages and 132 vol-3 pages** — but **the title pages sit in an OCR gap**, so this is **SUGGESTIVE and NOT PROBATIVE.** A zero over an incomplete surface is not an absence; this repository has been burned twice by exactly that inference. | Open, and explicitly not treated as evidence |

### Why none of these blocks identity any more

**Answering any of them changes the container spine and renumbers no key.**

- O1 changes the **parent** of `VG:SV:KAU:CHANDA`, `:ARANYA` and `:MAHANAMNYA` — from a top-level
  root to a `VG:SV:KAU:PURVA` container, or the reverse. The four collection keys and every
  mantra key beneath them are byte-identical either way.
- O2 adds or removes rows in an **alternate Citation system**. Alternate citations are not
  identity; the kāṇḍa was already refused as a tree level because its colophons cut across
  prapāṭhaka boundaries.
- O3 bears on how the print should be **described**, not on what any key denotes.

That is the whole content of the closure. **The arity dispute was binding only because the key
encoded an arity.** It no longer does, so the dispute can stay open indefinitely without costing
a migration — and if it is ever settled, settling it costs a documentation edit and a container
reparent, not a renumbering.

Registry state: `arcika_arity: RESOLVED  # dissolved as an identity question`, with the transition
recorded in `data/source_registry/four_veda_canonical_sanskrit_blockers.yaml`
(`state_transitions`, run `SAMAVEDA_REFERENT_INTEGRITY_REPAIR`).

---

## 12. Provenance of every figure in this report

| Claim | Label | Where it can be re-derived |
|---|---|---|
| 106 pinned ārcika pages; 74 Pūrv / 32 Uttar; 87 leaf pages | **MEASURED** | `data/raw/wikisource_sa/2026-09-07/` (`parse.title` enumeration) |
| Chanda 10,10,10,10,10,9 = 59 daśati leaves; Āraṇya 5; Mahānāmnya 1; Uttara ardha `[2,2,2,2,2,3,3,3,3]` = 22 | **MEASURED** | same |
| Pūrvārcika ardha word: 0 titles, 0 structural occurrences, 40 lexical | **MEASURED** | same, wikitext scan |
| Uttarārcika ardha pages: `दशति` 0, `सूक्त` 9 of 22 | **MEASURED** | same |
| Uttara P1 ardha 1 = daśati 1–23, ardha 2 = daśati 1–22 | **MEASURED** | `SamavedaWikisourceAdapter` + `resolve_local_indices` over the pinned corpus |
| Chanda daśati 1–10 continuous per prapāṭhaka | **MEASURED** | same |
| Āraṇya daśati RN ranges summing to 55 | **MEASURED** | same |
| 1,867/1,867 collection agreement and all §8 figures | **MEASURED** | `scripts/compare_samaveda_sources.py` → `data/derived/samaveda_cross_witness_structure.json` |
| 1035 / 1133 / 1211 / 1592 as GRETIL parser losses | **MEASURED** | `data/source_registry/samaveda_count_ledger.yaml` |
| Witness tally 4:1 / 2:6 / 3:1 | **MEASURED** (from cited primary and secondary sources) | `docs/reports/SAMAVEDA_ADDRESSING_STABILITY.md` §1, registry `arcika_arity_witness_count` |
| Wikisource root page revid 364594 and its two numbered ranges | **INFERRED** — live read, **not pinned** | not reproducible from a snapshot; see §3 caveat |
| Wikisource Pūrvārcika index revid 131420 | **MEASURED** | pinned corpus |
| Sāmaśramī colophons (vol 1 pp. 260, 342, 693; vol 3 p. 67); `दशति` 29 hits | **MEASURED** (by Agent B, prior run) | `docs/reports/SAMAVEDA_ADDRESSING_STABILITY.md` §3 |
| Sāmaśramī vol 1: 30 daśati colophons with ordinals 1–5, **0** with 6–10 | **MEASURED this run**, **not written to any repository artifact** | external OCR read; not re-derivable locally |
| Sāmaśramī: `दशति` 0 pages / `सू०` 74 pages in the Uttarārcika running heads | **MEASURED this run**, **not written to any repository artifact** | external OCR read; not re-derivable locally |
| "Pūrvārcika" 0 hits / 798 vol-1 pages / 132 vol-3 pages | **MEASURED this run**, **explicitly NOT PROBATIVE** (OCR gap at the title pages) | external OCR read; not re-derivable locally |
| Caland "in 6 prapāṭhakas" / Vedapeetha "585 single verses" / HOS 57 vol 1 "Kāṇḍas 1–5" | **quoted this run**, **not written to any repository artifact** | external reads; not re-derivable locally |

The last four rows are the honest weak spot of this report: they are the print-edition and
secondary-literature measurements, they were taken outside the repository, and **no pinned
artifact in this repository can reproduce them.** They support §9.3, §10 and §11 — the *reasoning*
for the ardha exclusion and the *statement* of what is open — and they support **none** of the
measurements that the frozen key rests on. Every figure the key depends on is in the first block
of the table and is re-derivable from pinned snapshots.
