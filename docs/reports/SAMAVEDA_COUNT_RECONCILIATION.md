# Sāmaveda Count Reconciliation — 1,868 vs 1,875

**Run:** `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE` · **Date:** 2026-09-07
**Starting commit:** `dc160d7` · **Work:** `VG:WORK:SV:KAU` (Kauthuma, arcika corpus only)
**Derived by:** Agent C1 · **Independently re-derived by:** Agent F and Agent A (coordinator)
**Artifact:** `data/raw/gretil/2026-09-07/91c28c0394e94dccc9bad12a08224fbcde0a1194402b610df26647621ed92456.xml`
(sha256 matches `structure_evidence_sha256` for `VG:WORK:SV:KAU` in `data/registry/works.yaml`)

---

## 0. Result in one line

**The gap is fully accounted for. `UNRESOLVED_COUNT_RESIDUE = 0`. No verse is missing from the
source. The discrepancy is 100% apparatus — a property of the GRETIL artifact label/marker
apparatus and of the VedaGraph adapter regexes, not of the Kauthuma text.**

---

## 1. The previously recorded equation was arithmetically correct and descriptively wrong

The prior run recorded, and this run **reproduces bit-for-bit**:

```text
structural tuples  = 1868
RN instances       = 1871  (= 1868 + 9 collision surplus - 6 zero-RN)
distinct RNs       = 1870  (= 1871 - 1 duplicate, RN 1181)
1875 - 1870        =    5  <- absent RN values [1035, 1133, 1179, 1211, 1592]
1870 - 1868        =    2  <- net structural residue
TOTAL              =    7
```

Every term is confirmed. **The equation nonetheless measures the adapter output, not the source.**
Measured directly against the artifact, the source prints **exactly 1,875 verse-terminal
apparatus markers**:

```text
total verse-terminal apparatus markers   : 1875
   DOUBLE_DANDA_RN                         1871
   UNPARSEABLE_LABEL_DOUBLE_DANDA_RN          1   <- RN 1035, label defeated by an 'rm' prefix
   SINGLE_DANDA_RN                            2   <- RN 1133, RN 1592
   JUNK_SUFFIX_RN                             1   <- RN 1211, printed '121clsdir'
marker values duplicated                 : [1181]
values in 1..1875 with NO printed marker : [1179, 1211]
values outside 1..1875                   : []
```

### The equation that actually describes the artifact

```text
printed verse-terminal markers            = 1875   <- EXACTLY the traditional total
distinct structural addresses (tuples)    = 1868
addresses bearing NO printed marker       =    2   (4,4,2,1,12) and (4,8,2,8,1)
surplus markers on collided addresses     =   +9   across 7 addresses
identity: 1875 = 1868 - 2 + 9                        OK
therefore: 1875 - 1868 = 9 - 2 = 7                   OK
```

The `1868` is the count of distinct address tuples **after collapsing on a defective verse-index
field**, and nothing more. The artifact contains 1,875 verse units.

### The four-number ladder, for consumers

Four different counts are all correct, of four different things. Conflating any two of them
produces the confusion this document exists to end.

| Quantity | Value | Why it differs from the line above |
|---|---|---|
| Printed verse-terminal markers in the source | **1875** | — |
| Markers the current adapter can lift | **1871** | 4 lost to regex strictness (§3) |
| Distinct structural addresses parsed | **1868** | 9 verses collapse onto 7 addresses; 2 addresses carry no marker |
| Canonical keys actually minted | **1866** | `(4,3,1,4,0)` and `(4,6,2,16,0)` carry verse index `0`; `sv_mantra_identity` fails closed |

Verified by execution against the pinned artifact (Agent A, 2026-09-07).

---

## 2. Term-by-term verdict on the recorded equation

| Term | Recorded | Re-derived | Verdict |
|---|---|---|---|
| structural tuples | 1868 | 1868 | **CONFIRMED** |
| RN instances | 1871 | 1871 | **CONFIRMED** |
| distinct RNs | 1870 | 1870 | **CONFIRMED** |
| collision surplus | +9 | +9, across 7 addresses | **CONFIRMED** |
| zero-RN | −6 | −6 under the strict adapter read | **CONFIRMED as an adapter fact; REFUTED as a source fact** — only 2 addresses genuinely lack a printed marker |
| duplicate | −1 (RN 1181) | −1, on `(4,5,1,2,2)` and `(4,5,1,2,4)` | **CONFIRMED** |
| "5 absent RNs" | 5 | Only **1** value (1179) is genuinely unprinted | **REFUTED as stated** |
| "net residue of 2" | 2 | 2 arithmetically; in source space these are **two nameable addresses**, not a residue | **CONFIRMED arithmetically, REFUTED as characterisation** |
| TOTAL | 7 | 7 | **CONFIRMED and invariant** |

---

## 3. What was wrong in the record, with proof

### (a) The apparatus does NOT skip 1133 or 1592. The source prints both.

The prior report stated *"The apparatus skips from 1132 to 1134 without printing 1133"* and
*"The apparatus skips from 1591 to 1593."* **Both claims are false.** Both numbers are printed, on
the correct pāda line, in the correct sequence position. They are lost because
`_RUNNING_NUMBER` requires a **double** daṇḍa and the source prints a **single** daṇḍa at those
two points:

```text
para=223  label='4 4 2 02 06c'   apparatus=SINGLE(1133)
para=364  label='4 7 3 1003e'    apparatus=SINGLE(1592)
```

**Consequence — a fidelity defect, not merely a counting one:** `1133` and `1592` are currently
ingested **as verse text**. `verse_text()` for `(4,4,2,2,6)` contains the literal digits `1133`,
and for `(4,7,3,10,3)` the literal digits `1592`.

### (b) RN 1211 is not absent; it is printed corrupt.

The apparatus token at `(4,5,1,6,2)` is `121clsdir` — a leaked word-processor or markup control
token adhering to the numeral. `clsdir` occurs **exactly once** in the 272,261-byte artifact and
is the only digit-plus-alpha adhesion in the file that is not a GRETIL in-word numeric svarita
(the other 20 are all `3`-prefixed accent marks). Positionally it sits between markers 1210 and
1212, so slot 1211 is determinate. `clsdir` is likewise ingested as verse text.

### (c) RN 1035 is printed, and this is the most consequential fidelity defect found.

The source line is `rm 4 4 1 02 02c … .. 1035`. The `.. 1035` marker is well formed; the *label*
is defeated by a stray two-letter `rm` prefix against the anchored label regex, so the whole line
— text and marker together — is discarded.

**Consequence: address `(4,4,1,2,2)` is ingested holding only its `a` pāda.** One of the 1,868
records is half a verse. The prior record understated this.

### (d) Only ONE of the five values is genuinely unprinted, and it is a determinate misprint.

RN 1179 is not printed anywhere; 1181 is printed in its slot. Proof: across the entire
1,874-value marker stream in document order there is **exactly one** non-increasing step.

```text
non-increasing steps in the printed marker sequence: 1
   pos 1179  (4,5,1,2,2) marker 1181  ->  (4,5,1,2,3) marker 1180
(4,5,1,2,2) prints 1181 but sits between 1178 and 1180 -> positionally it IS slot 1179
```

So 1179 was typeset as "1181". **Duplicated numbering, not skipped numbering, and no verse is
missing.**

### (e) The "5 + 2" split is an artifact of regex strictness, not a property of anything

Repair only the three cleanly recoverable liftings and the split moves while the total does not:

```text
EQUATION UNDER A PUNCTUATION-TOLERANT READ
  structural tuples = 1868 (UNCHANGED - no new address is created)
  zero-RN tuples    =    3 (was 6): (4,4,2,1,12) (4,5,1,6,2) (4,8,2,8,1)
  RN instances      = 1874 (= 1868 + 9 - 3)
  distinct RNs      = 1873
  1875 - distinct   =    2  <- absent RNs [1179, 1211]
  distinct - tuples =    5  <- net structural residue
  TOTAL             =    7
  counting the corrupt token as intended RN 1211:
     distinct=1874  1875-distinct=1  distinct-tuples=6  total=7
```

The split becomes 5/2, then 2/5, then 1/6. **Only the 7 is invariant.**

> **Any report that names "5 identifiable absent RNs plus a residue of 2" is publishing a parser
> configuration as a philological result.** That sentence is the durable lesson of this
> reconciliation and it generalises beyond Sāmaveda.

### (f) The false mechanism was live in six places, three of them YAML a build reads

`data/source_registry/four_veda_canonical_sanskrit_blockers.yaml`,
`data/source_registry/samaveda_sources.yaml` (`running_numbers_absent`),
`data/registry/works.yaml` ("it is defective (five values absent, one duplicated)"),
`docs/FOUR_VEDA_STRUCTURAL_MODEL.md`, `docs/FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKERS.md`, and
`docs/reports/FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE.md`.

This is the third recorded instance of the standing hazard that a correction pass scoped to
`docs/` certifies a claim absent while it is live in a registry. All six sites are corrected in
this run.

---

## 4. The 7 collided addresses carrying the 9 surplus markers

Verified by execution (Agent A, 2026-09-07); identical to the independent derivations by
Agent C1 and Agent F.

| # | Address | Markers | Surplus | Pāda labels | Notation | Mechanism |
|---|---|---|---|---|---|---|
| 1 | `(4,1,1,6,3)` | 666, 667, 668 | +2 | a c a c a c | SPACED | verse-index field stuck at `03` |
| 2 | `(4,5,2,6,3)` | 1282, 1288 | +1 | a c a c | SPACED | displaced line-block |
| 3 | `(4,5,2,7,4)` | 1283, 1295 | +1 | a c a c | SPACED | displaced line-block |
| 4 | `(4,5,2,8,5)` | 1284, 1302 | +1 | a c a c | SPACED | displaced line-block |
| 5 | `(4,5,2,10,1)` | 1307, 1308, 1309 | +2 | a c a c a c | SPACED | verse-index field stuck at `01` |
| 6 | `(4,6,2,16,0)` | 1421, 1422 | +1 | a c a c | CONCAT | verse-index field stuck at `00` |
| 7 | `(4,8,2,8,2)` | 1679, 1680 | +1 | c a c | CONCAT | pāda-label off-by-one |

`2+1+1+1+2+1+1 = 9`. Three distinct mechanisms: stuck verse-index field (#1, #5, #6), the
displaced 1280–1285 line-block (#2, #3, #4), and pāda-label off-by-one (#7).

**The displaced block is fully diagnosed** — GRETIL incremented the daśati instead of holding it,
and every true home is a vacant append slot:

```text
running 1280 -> (4,5,2,5,1)      1286 -> (4,5,2,6,1)
running 1281 -> (4,5,2,5,2)      1287 -> (4,5,2,6,2)
running 1282 -> (4,5,2,6,3)   <- belongs at (4,5,2,5,3) VACANT
running 1283 -> (4,5,2,7,4)   <- belongs at (4,5,2,5,4) VACANT
running 1284 -> (4,5,2,8,5)   <- belongs at (4,5,2,5,5) VACANT
running 1285 -> (4,5,2,9,6)   <- belongs at (4,5,2,5,6) VACANT
```

### The collision mechanism is a concatenative merge, not first-wins or last-wins

This matters more than the count. Every matching line is appended to `verse.lines`, and
`verse_text()` joins all of them:

```text
(4,1,1,6,3)  key=VG:SV:KAU:A4:P01:R1:D06:V03
   lines=['a','c','a','c','a','c']  merged_len=197
     constituent RN 666: padas=['a','c'] len=64
     constituent RN 667: padas=['a','c'] len=64
     constituent RN 668: padas=['a','c'] len=66
   merged == first constituent? False
   merged == last  constituent? False
```

Re-parsing is byte-identical across 5 runs, so this is deterministic — but a line-order shuffle
changes text at 891–917 of 1,868 addresses, so **the pāda order inside a merged address is an
artifact of document order, not of structure.** The identity consequence is analysed in
`SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE.md` §5 and is one of the two reasons identity was not
frozen.

---

## 5. The 6 zero-marker addresses — only 2 are genuine

| Address | Pādas ingested | Why no marker | Marker actually printed? |
|---|---|---|---|
| `(4,4,1,2,2)` | a | `rm` prefix kills the label line | **YES**, `.. 1035` |
| `(4,4,2,1,12)` | a | `c` pāda mislabelled `13c`; marker went to `(…,13)` | **NO — genuine** |
| `(4,4,2,2,6)` | a c | single daṇḍa `. 1133` | **YES**, `. 1133` |
| `(4,5,1,6,2)` | a c | numeral fused to `clsdir` | **YES**, corrupt |
| `(4,7,3,10,3)` | a c e | single daṇḍa `. 1592` | **YES**, `. 1592` |
| `(4,8,2,8,1)` | a | `c` pāda mislabelled `0802c`; marker went to `(…,2)` | **NO — genuine** |

**Four of the six are adapter lifting failures. Two are genuine.**

### The phantom address — a canonical key for a verse that does not exist

The two genuine cases are pāda-label off-by-one errors, and one of them has already minted a key
for nothing. Daśati `(4,4,2,1)` prints markers **1116–1127 = 12 verses**, but VedaGraph mints
**13 addresses**:

```text
V11 pada_labels=[a, c]  running=[1126]   key=VG:SV:KAU:A4:P04:R2:D01:V11
V12 pada_labels=[a]     running=[]       key=VG:SV:KAU:A4:P04:R2:D01:V12
V13 pada_labels=[c]     running=[1127]   key=VG:SV:KAU:A4:P04:R2:D01:V13
```

`12a` and `13c` are the two pādas of **one** verse, marker 1127. So
**`VG:SV:KAU:A4:P04:R2:D01:V13` is a canonical identifier for a verse that does not exist**, and
marker 1127 pādas are split across two IDs.

It is invisible to every existing gate: because the labels land in *different* verse buckets,
`DUPLICATE_LINE_LABEL` never fires. The corpus-wide detector for this class finds exactly four
addresses whose first pāda label is not `a`:

```text
(1,1,1,1,2)  ['c']          rn=[2]           <- the documented 0101a pada-bleed
(1,3,1,1,8)  ['c','a']      rn=[201]
(4,4,2,1,13) ['c']          rn=[1127]        <- PHANTOM
(4,8,2,8,2)  ['c','a','c']  rn=[1679,1680]
```

The shortage and the surplus cancel in the total, which is exactly why a 1,868-vs-1,875 check
cannot see either: the address space is **9 short overall** while containing **one unit where it
is long**.

---

## 6. Per-arcika counts and gap attribution

```text
arcika   addresses  markers   delta   marker range
1        585        585       +0      1..585
2         55         55       +0      586..640
3         10         10       +0      641..650
4       1218       1225       +7      651..1875
TOTAL   1868       1875       +7

PURVARCIKA GROUP (arcika 1+2+3): addresses=650  markers=650  delta=+0
UTTARARCIKA      (arcika 4)    : addresses=1218 markers=1225 delta=+7
traditional split 650 + 1225 = 1875 -> EXACT MATCH on both sides
contiguity of 1..650 in the Purvarcika group: COMPLETE, no gaps
units out of balance: 7 of 464
```

Both prior claims are **CONFIRMED**, and the Uttarārcika result is stronger than recorded: it
prints **exactly 1,225** markers, matching the traditional 1,225 on the nose.

Uttarārcika breakdown of the +7: `4.1.1.06` +2, `4.4.2.01` −1, `4.5.2.06` +1, `4.5.2.07` +1,
`4.5.2.08` +1, `4.5.2.10` +2, `4.6.2.16` +1, `4.8.2.08` 0 (address-balanced yet internally
misassigned). Net **+7**. Prapāṭhaka `4.5` alone contributes **+5 of the +7**.

> **Caveat that must travel with the "complete at 650" claim.** That is a **count**-axis statement
> only. Three Pūrvārcika addresses carry misassigned pādas — `(1,1,1,1,1)`, `(1,4,1,4,6)` and
> `(1,5,2,8,9)`. **Count-clean is not text-clean**, and the two must never be conflated in a
> release note.

---

## 7. Apparatus vs text — verdict and its limits

**VERDICT: 100% APPARATUS. ZERO TEXT.**

Four independent grounds:

1. **The artifact prints exactly 1,875 verse-terminal markers** — measured, not inferred, with
   zero unlabelled orphan markers and zero values outside `1..1875`.
2. **The per-arcika split is exactly 650 + 1,225**, matching the traditional Kauthuma split
   independently on both sides of the boundary. A missing-verse hypothesis would have to place
   all seven losses in the Uttarārcika *and* leave its marker count intact at 1,225. It does not
   survive.
3. **Every one of the 7 net units has a determinate correct reading** recoverable from the
   artifact alone — flanking-unit regularity for the stuck-index cases, the contiguous 1280–1285
   series for the displacement, pāda-pair logic for the two splits. No external collation needed.
4. **No verse text is absent.** All 1,875 markers sit on a printed pāda line. The one genuinely
   damaged text is `(4,4,1,2,2)`, which lost its `c` pāda to a two-letter `rm` typo — also
   apparatus.

Classification of all seven: 4 × duplicated numbering, 3 × editorial structure (displaced
line-block), 2 × split units; and on the apparatus-read axis 2 × different counting convention
(single daṇḍa) and 2 × source corruption (`rm`, `clsdir`). **`UNRESOLVED_COUNT_RESIDUE: 0`.**

### Stated evidence limits — these are real

- **This is forensics on a rejected witness.** Everything above derives from an artifact this
  project rejected as canonical primary (`PERMISSION_REQUIRED`, empty `sourceDesc/bibl`, Pandey
  1998 lineage). It establishes that the gap is not a philological fact. It establishes nothing
  about the selected witness.
- **The Wikisource cross-check is NOT AVAILABLE for the gap region.** Measured, not assumed:

```text
total Wikisource verses across all pinned snapshots: 29
running-number coverage: 1..10, 45..54, 586..594
fraction of the 1875-verse corpus pinned: 1.55%
gap-region (RN 1035..1592) coverage: 0 verses -> CROSS-CHECK NOT AVAILABLE
uttararcika (RN 651..1875) coverage: 0 verses
all pinned pages are in the purvarcika group (RN 1..650): True
overlap of Wikisource coverage with the 16 defect RNs: [] -> 0 verses
```

  All three pinned pages sit in the Pūrvārcika group — **the one region with zero defects.** Not
  one of the seven can be checked against Wikisource. The 1.55% that is pinned is exactly the part
  where the two sources cannot disagree.
- **The cross-witness join is not independent.** It uses the GRETIL printed apparatus as the
  bridge, so Wikisource cannot corroborate coordinates anywhere that apparatus is defective —
  precisely the verses needing corroboration.
- What the snapshots **do** establish (3/3 parsed, 29 verses, 0 unparsed): exact set-equality of
  running numbers with GRETIL on every page — `1..10` vs unit `(1,1,1,1)`; `45..54` vs `(1,1,1,5)`;
  `586..594` vs `(2,0,0,1)`; and live `145..154` vs `(1,2,·,6)`. Each a contiguous run, each an
  exact match. Corroborated across two lineages proved textually independent — **in the
  defect-free region only.**
- The `1179 -> 1181` and `1211 -> 121clsdir` slot assignments rest on **positional inference**
  from the monotone marker stream, not on a printed numeral. Marked `INFERRED_FROM_SEQUENCE`.
  They do not affect the equation, since the 1,875 marker total is measured directly.
- **Does the discrepancy travel with a source change? Predicted NO — and this is a prediction, not
  a measurement.** Every mechanism is a defect in the GRETIL label field or in the adapter
  regexes. None is a statement about the Kauthuma tradition. Confirming it requires fetching the
  Wikisource pages covering RN 1035, 1133, 1179, 1211 and 1592, none of which is pinned. Until
  then: **demonstrated for the GRETIL artifact, predicted for the corpus.**

---

## 8. Independent corroboration of 1,875, and one important negative

Agent B established the traditional total on-wiki, independently of GRETIL: the root page
`सामवेदः/कौथुमीया/संहिता` states the ranges `पूर्वार्चिकः (१–६५०)` / `उत्तरार्चिकः (६५१–१८७५)`, and a
2013 Kannada essay on `सम्भाषणम्:सामवेदः/राणायनीया` independently gives ṛk = 1875, sāma = 2639.

**But the continuous 1..1875 numbering is NOT corroborated by an identified printed edition.**
Agent B read the Sāmaśramī print (Bibliotheca Indica, 1874–78) directly: it prints
`॥ <local verse no.> ॥ <second number>`, and the second number **resets per section** (p. 316 →
१४/१५ where p. 260 → ९६). `insource:"१८७५"` returns 0 hits across the scans. The running number is
therefore attested only by the hand-keyed wiki text and by GRETIL.

**This independently vindicates the existing project refusal** (Refusal 3 in
`docs/FOUR_VEDA_STRUCTURAL_MODEL.md`) to treat the running verse number as identity. It is
recorded as a non-canonical `Citation`, and that remains correct.

---

## 9. Machine-readable ledger

The full per-item ledger — with `mechanism`, `evidence`, `count_delta` and
`canonical_key_assignable` for every count-axis item, apparatus-read item and
canonical-key-defect item — is recorded in `data/source_registry/samaveda_count_ledger.yaml`.

Two axes are kept **strictly separate** in that file, because summing them is the double-count the
superseded table committed:

- **count axis** — `count_delta` sums to exactly `+7`.
- **apparatus-read axis** — the five "absent RNs"; `count_delta` is `0` for all five, because they
  are lifting failures already booked on the count axis.

---

## 10. Follow-up owned by the re-point, not by this run

1. **Adapter repairs, cheap and bounded.** `_RUNNING_NUMBER` should accept a single daṇḍa; the
   label match should tolerate a leading junk token rather than discard the line; a corrupt
   apparatus token should raise a defect rather than be ingested as text. Three ingested records
   currently carry apparatus residue in `text_original` (`1133`, `1592`, `clsdir`) and one carries
   only half its printed text. That is a fidelity issue independent of the count question, and it
   is not something a `PRIMARY_TEXT` role should tolerate.
2. **Referent repair before any identity freeze.** The 7 collided addresses and the phantom `V13`
   must be repaired and recorded as `SourceAssertion` / `NEEDS_REVIEW` first. See
   `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE.md` §5.
3. **`structural_count_discrepancy` stays `RESOLVED`** — the gap is accounted for, now more
   exactly than before. Only the stated *mechanism* was wrong, and it is corrected here and in all
   six recording sites.
