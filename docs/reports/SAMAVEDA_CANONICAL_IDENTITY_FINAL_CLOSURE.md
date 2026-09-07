# Sāmaveda Canonical Identity — Final Closure Attempt

**Run:** `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE` · **Date:** 2026-09-07
**Starting commit:** `dc160d7` (`feat: close Yajurveda blocker and validate Atharvaveda PD source path`)
**Branch:** `semantic-pilot-v1` · **Work:** `VG:WORK:SV:KAU` — Sāmaveda, Kauthuma, **arcika corpus only**
**Runtime:** `CLAUDE_CODE_DIRECT` (ADR-016) · **Agents:** A (coordinator / single writer), B, C1, C2, D, E, F

Companion documents: [`SAMAVEDA_COUNT_RECONCILIATION.md`](SAMAVEDA_COUNT_RECONCILIATION.md) ·
[`SAMAVEDA_ADDRESSING_STABILITY.md`](SAMAVEDA_ADDRESSING_STABILITY.md)

---

## 0. DECISION

### `SAMAVEDA_CANONICAL_IDENTITY_RESEARCH_REQUIRED`

`identity_status` stays `RESEARCH_REQUIRED`. `key_pattern` stays `null`.

**But the blocker is not the one this session was convened to close, and it is no longer an
external dependency.** The session was framed around a single missing external fact — *which
printed edition the Sanskrit Wikisource community transcribed from*. That question is now
**settled as far as it can be**, and it turns out **not to have been the binding constraint**.

Two *newly discovered*, independent grounds forbid the freeze. Either alone is sufficient.

| # | Ground | Owner | Character |
|---|---|---|---|
| **1** | **Referent integrity.** 7 addresses absorb 9 printed verses by concatenative merge, and 1 canonical key denotes a verse that does not exist. Repairing them keys, URNs and UUIDs unchanged while the *verse behind them changes*. No gate in the repository can detect this. 3 of the affected keys are already materialized. | Agent F | **Bounded engineering** against a pinned artifact |
| **2** | **Arcika arity.** The top slot of the key encodes Pandey arity (4 flat sibling arcikas). Six independent witnesses say 2, one says 3. The claim has **1 witness, 0 independent corroborations, 6 contradictions** — and two hard tuple collisions were verified. | Agent C2 | **Narrow philological adjudication** |

Neither is the edition question. Both were invisible to the previous run. **The blocker moved from
`OPEN_RESEARCH` on an external dependency to `OPEN_ENGINEERING` plus one narrow review item — a
strictly better position, reached by disproving the framing rather than by satisfying it.**

This is not a failed session. It is a session that found the *real* blocker.

---

## 1. Agent verdicts

| Agent | Role | Verdict |
|---|---|---|
| **B** | Final Wikisource provenance | `PRINT_EDITION_NOT_IDENTIFIABLE_FROM_AVAILABLE_EVIDENCE` (for the pinned corpus) — plus the discovery of a **second, scan-backed corpus with a complete printed citation** |
| **C1** | Count reconciliation | Gap **fully accounted**; `UNRESOLVED_COUNT_RESIDUE = 0`; the recorded *mechanism* refuted and corrected |
| **C2** | Addressing stability | `ADDRESSING_IS_EDITION_INDEPENDENT` for the level list — **but 2 hard coordinate collisions found**, and the arity is Pandey-specific |
| **D** | Identity governance | Proposition **PROVEN** in both negative clauses, **REJECTED** on the word *edition-independent* for SV |
| **E** | Rights / provenance | `APPROVE_WITH_CONDITIONS` (10 conditions) — rights do not block the freeze |
| **F** | Adversarial QA | **`DO_NOT_FREEZE`** |

**Both approval limbs the identity policy requires were not obtained.** Agent E approved; Agent F
did not. Per the session gate — Option B is available only if *"Agent F cannot identify an identity
collision/instability scenario"* and *"no known witness assigns conflicting meanings to the same
coordinates"* — **both conditions failed**, independently.

---

## 2. Question A — source-edition identity: settled, and shown to be the wrong question

### The negative on the pinned corpus is now *positively established*

Agent B was given one final bounded pass and converted an absence of evidence into evidence of
absence. The pinned `सामवेदः/कौथुमीया/संहिता` tree (**Corpus A**) is a **hand-keyed community
transcription with no printed antecedent**:

- **Not scan-backed.** 0 templates, 0 `पृष्ठम्:`/`अनुक्रमणिका:` links, 0 images on all three pinned
  pages. A pinned page is 908 bytes of bare `<poem>` wrapper — no page anchors, so **no
  page-number correspondence to any printed book exists or could be recovered.**
- **Contributor testimony.** `सदस्यसम्भाषणम्:Vishvas vasuki`, rev 230976, 2020-04-19: the principal
  contributor describes his own work as `टंकणम्` — *typing*.
- **The community itself asked for a source and did not get one.** 2021-07-21, same page: *"could
  you please state the original source of the text… because there are many errors in the
  Devanagari conversion."* Reply: a bare personal-site link. **Source non-attribution is a known
  and unremedied condition of this corpus**, not an artifact of our search.
- **Exhaustive external-link census of the whole tree**: every host is a contributor mirror, a
  lexicon tool, or three `archive.org` links to a single *unrelated* book. **Not one link to any
  scan or printed edition of the Sāmaveda across 840+ pages.**
- **Front matter proven absent by enumeration**, not by failure to find: all **908** namespace-0
  `सामवेद*` titles enumerated to exhaustion; a 20-term Devanagari front-matter sweep returns one
  hit, under `सामविधानब्राह्मणम्`, not the saṃhitā. Wiki-wide `intitle:प्राक्कथनम्` returns exactly 3
  pages — one of which is the **Yajurveda** contrast case. The YV preface exists; the SV analogue
  does not.
- **Both candidate editions refuted as Wikisource-attested sources.** `नारायणस्वामी` → 3 hits, all
  a different work; `insource:"Narayanaswami"` → 6 hits, none Sāmaveda; `बन्सल` and
  `insource:"Bansal"` → **0 totalhits wiki-wide**. Zero occurrences anywhere in the Sāmaveda
  corpus, in any namespace, including all talk and contributor pages.

### A prior negative was partly a false negative by construction

The previous run recorded four exhausted routes. **Route 2 used `चर्चा:` — the *Hindi* Wikisource
talk prefix.** Sanskrit Wikisource uses `सम्भाषणम्:`. That probe would have returned 404 regardless
of content. The corrected probe found the two contributor admissions quoted above.

**Lesson recorded:** an exhausted-route finding is only as strong as the namespace vocabulary it
used. Enumerate the namespace map (`meta=siteinfo&siprop=namespaces`) before declaring a namespace
empty.

### The unanticipated finding: a second corpus, fully cited

All four prior routes missed it because the `अनुक्रमणिका:` (Index) namespace was never probed.
**Corpus B** is scan-backed and identifies its printed edition completely:

> Sāmaveda-saṃhitā with the commentary of Sāyaṇa, ed. Satyavrata Sāmaśramī Bhaṭṭācārya. Calcutta:
> Asiatic Society of Bengal (Bibliotheca Indica). **5 volumes, 1874–1878.** Vols 1–3 on Wikimedia
> Commons; vols 4–5 on archive.org. Public domain.

It does **not** rescue the blocker, for two reasons stated plainly:

1. **Every `पृष्ठम्:` page is `वर्गः:अपरिष्कृतम्` — unproofread raw OCR.** Vol 1 has 163 gaps in 961
   pages; vol 2 has **2** transcribed pages; vols 4–5 are not on Commons at all.
2. **The recension is not established.** Griffith 1895 preface assigns both Benfey and Sāmaśramī to
   **Rāṇāyanīya**. A stobha discriminator points to Kauthuma but is not probative. An identified
   edition of *uncertain recension* does not satisfy ADR-017 first bar.

> **The Atharvaveda parallel does not hold, and the coordinator was wrong to float it.** AV had a
> PD edition of *known identity*. Here the identity is known as a *printing* and unknown as a
> *recension* — and the page that would settle it, vol 1 title page, sits inside the OCR gap.

### The verdict on Question A

**`PRINT_EDITION_NOT_IDENTIFIABLE_FROM_AVAILABLE_EVIDENCE`.** The available evidence is exhausted
and consistently negative. **Route 5 must not be opened on Corpus A.** The residual is a single
named external dependency: fetch vol 1 pp. 1–9 from archive.org `in.ernet.dli.2015.487112` and have
a specialist read the recension off the title page.

---

## 3. Question B — is edition identity actually required to freeze Passage identity? **No.**

This was the session central governance question, and it resolves cleanly **in the negative**.

### The mechanism is source-blind, and that is structural rather than conventional

`src/vedagraph/identity.py` is the entire identity mechanism: `uuid_for_urn` takes **one string**
and returns `uuid5(VEDAGRAPH_NAMESPACE_UUID, urn)`. The module imports only `uuid.UUID` and
`uuid.uuid5`. The SV URN is built from exactly five integers. **The function signature admits
nothing else** — no `source_id`, no `artifact_id`, no `text_version_id`, no URL.

`Passage` (`models/core.py`) has **no** URL, source, artifact or edition field, and `VGModel` sets
`extra="forbid"`. **A source cannot be attached to a Passage.** Verified by execution: `Passage`
has 13 fields and `'text' in Passage.model_fields` is `False`.

**Exhaustively, what determines a Passage UUID:** the frozen namespace literal, and the
`canonical_urn` string. **What does not:** `source_id`, `source_artifact_id`, `text_version_id`,
`url`, `checksum_sha256`, `snapshot_id`, `retrieval_date`, `rights_status`, `source_edition`,
`source_locator`, `sequence_in_parent`, `canonical_citation`, `status`.

### The registry own layering already answers the question

`source_edition` is an **artifact**-level field (25 uses in `source_artifacts.yaml`).
`underlying_edition` is a **text_version**-level field. **Neither exists in `works.yaml` at all.**
The registry structure already declares that **edition is a property of a witness, not of a work
identity.**

### The RV / YV / AV precedent is decisive

| Work | `identity_status` | Edition named in `works.yaml`? |
|---|---|---|
| `VG:WORK:RV:SAK` | FINAL | **No** — Aufrecht lives in ADR-010 only |
| `VG:WORK:YV:VSM` | FINAL | **No** — Nirṇaya Sāgara 1929 lives in the blocker registry only |
| `VG:WORK:AV:SAU` | FINAL | **No** — Roth & Whitney lives in `source_artifacts.yaml` only |

**No work `key_pattern` encodes an edition claim.** And Atharvaveda is `FINAL` while its only
ingested text is `REFERENCE_ONLY`, **no Sanskrit has been transcribed at all**, and its structural
counts remain unreconciled. AV froze identity *first* and now treats the freeze as a constraint on
source resolution.

**Conclusion: requiring the Wikisource printed edition *in order to freeze the Passage ID* is a
category error.** Question B is answered: exact printed-edition identification is **not** required.

### The `forbidden_shortcuts` vs `exit_criteria` tension, adjudicated

Both live in the same block, eight lines apart:

- `exit_criteria`: *"Edition/provenance decision recorded (**named edition, or explicit
  frozen-without-edition statement**)"*
- `forbidden_shortcuts`: *"Freezing key_pattern before an edition **decision** is made"*

**They are consistent, and the word "decision" fixes the reading.** `exit_criteria` defines what an
edition decision *is*, disjunctively. `forbidden_shortcuts` forbids freezing *before* one. A
recorded frozen-without-edition statement **is** one of the two admissible decisions. What is
forbidden is freezing *silently*.

Independently corroborated by the prior closure report own precondition list, written by the agent
that recommended **against** freezing: *"Edition identity established (**or formally waived with
documented justification**)."*

**But the authoritative instrument is more restrictive than either registry line.**
`ADR-017` states: *"Until one witness clears both bars, no key is declared, **not even
provisionally**."* The blocker registry declares its own subordinate status — *"Consolidated,
non-authoritative snapshot… This file restates, it does not decide."*

**So the real tension is between the permissive, non-authoritative registry and the restrictive,
authoritative ADR.** Freezing would not violate `forbidden_shortcuts`. It *would* contradict
ADR-017, and closing that properly requires an ADR that supersedes the clause — not a registry
edit. **That remains true and is now moot**, because grounds 1 and 2 forbid the freeze on
independent, non-governance grounds.

### A definitional defect found in passing, and worth fixing regardless

`Work.identity_status` is documented as: `FINAL` = the key may never change again; `PROVISIONAL` =
*"the structure is confirmed from a source record but something the key depends on is still open"*;
`RESEARCH_REQUIRED` = **"the hierarchy itself is not yet known."**

**By that definition SV is currently mislabelled.** The SV hierarchy *is* known and corroborated —
by five witnesses and now by printed colophons. `RESEARCH_REQUIRED` asserts the opposite.
`PROVISIONAL` is the definitionally exact description of the actual state.

`identity_status` is **not an enum** — `identity_status: str = "FINAL"`, and `work.schema.json`
carries no `enum` constraint. Any string validates. It is also **read by no code**: an exhaustive
search finds only the field definition and two test assertions.

**This run does not change the value**, because moving to `PROVISIONAL` would contradict ADR-017
without superseding it, and because the referent defects make even `PROVISIONAL` an overstatement
today. It is recorded as a **known definitional inconsistency** with a named resolution: repair the
referents, then supersede the ADR-017 clause and move to `PROVISIONAL` in one deliberate change.

A `FINAL_WITH_LIMITATION` state was evaluated and **rejected as a euphemism.** `FINAL` has a single
stipulated meaning; a key either may never change or may. Inventing a hyphenated `FINAL` would let
a not-final key read as final to every consumer that prefix-matches — and because nothing reads the
field, no mechanism would ever catch it.

---

## 4. Question of addressing — resolved, and it favours freezing

Full analysis in [`SAMAVEDA_ADDRESSING_STABILITY.md`](SAMAVEDA_ADDRESSING_STABILITY.md).

**`ADDRESSING_IS_EDITION_INDEPENDENT`** for the ordered level list and the container boundaries.
The dependency runs *opposite* to the one the brief anticipated: **Wikisource is the witness that
least resembles the declared 5-tuple**, and the addressing does not depend on it.

The single most valuable result of the session: **all five levels are printed in the colophons of
an identified printed edition** (Sāmaśramī, Bibliotheca Indica 1874–78) —
`इति छन्दस्यार्चिके प्रथमः प्रपाठकः`, `इति चतुर्थस्यार्धः प्रपाठकः`, `इति पञ्चम-दशति ॥`, `॥ n ॥`.

**Ardha, asked as the weakest link, answered as the strongest.** It is lexically attested by
Wikisource page titles, by TITUS, by Vedapeetha, by Griffith (as CHAPTER) **and by the printed
colophons**; its Uttarārcika cardinality fingerprint `[2,2,2,2,2,3,3,3,3]` is reproduced by five
witnesses across three lineages; and 21/21 Uttarārcika ardha closing boundaries are identical
between GRETIL and Wikisource. The Wikisource omission of ardha in the Pūrvārcika is an
**economy, not a denial** — it drops exactly the copy that is derivable (`ardha = 1 if dasati <= 5
else 2`) and keeps exactly the copy that is not.

**And the running number is now weaker than recorded, correctly.** The printed edition does **not**
carry a continuous 1..1875 series; it prints a per-section counter that resets. The running number
is attested only by the hand-keyed wiki text and by GRETIL. This independently vindicates
Refusal 3 — the running number is a non-canonical `Citation` and must stay one.

---

## 5. GROUND 1 — referent integrity (Agent F, `DO_NOT_FREEZE`)

Every claim below was executed against the pinned artifact and independently re-verified by the
coordinator.

### The candidate identity is not a bijection onto the verses, and the errors run both ways

**Seven addresses absorb nine printed verses**, and the mechanism is a **concatenative merge** —
not first-wins, not last-wins:

```text
(4,1,1,6,3)  key=VG:SV:KAU:A4:P01:R1:D06:V03
   lines=['a','c','a','c','a','c']  merged_len=197
     constituent RN 666: len=64
     constituent RN 667: len=64
     constituent RN 668: len=66
   merged == first constituent? False
   merged == last  constituent? False
```

**One canonical key denotes a verse that does not exist.** Daśati `(4,4,2,1)` prints markers
1116–1127 = **12 verses**; VedaGraph mints **13 addresses**. `12a` and `13c` are the two pādas of
one verse (marker 1127), so `VG:SV:KAU:A4:P04:R2:D01:V13` is an identifier for nothing, and marker
1127 is split across two IDs.

### Referent migration under a stable UUID — worse than renumbering

Key-set additivity *holds*: correcting the gap adds 3 keys and loses 0, and every target slot is a
vacant append slot. **That was the wrong test.** The right one:

| Key | Referent today | Referent after repair | Verdict |
|---|---|---|---|
| `A4:P01:R1:D06:V03` | merge(666, 667, 668) | 668 | **MOVES** |
| `A4:P05:R2:D06:V03` | merge(1282, 1288) | 1288 | **MOVES** |
| `A4:P05:R2:D07:V04` | merge(1283, 1295) | 1295 | **MOVES** |
| `A4:P05:R2:D08:V05` | merge(1284, 1302) | 1302 | **MOVES** |
| `A4:P08:R2:D08:V02` | merge(1679-tail, 1680) | 1680 | **MOVES** |
| `A4:P05:R2:D10:V01` | merge(1307, 1308, 1309) | 1307 | narrows; head preserved |
| `(4,6,2,16,0)` | merge(1421, 1422) | V01 / V02 | no key exists — additive |

**5 of 7 referents move under an unchanged key, unchanged URN and unchanged UUID.**

### No gate in the repository can detect it — verified, not inferred

- `Passage` has **no text field** — 13 fields, confirmed by execution.
- `qa/checks.py` references `text_original` **exactly once**, and it is a UTF-8 encodability
  assert.
- `stable_uuid_deterministic` recomputes `uuid_for_urn(passage.canonical_urn)` from the **URN
  alone**, so it passes identically before and after a referent swap.

**Nothing anywhere binds a canonical key to its text.** Renumbering is at least visible; referent
migration is not.

### Three of the affected keys are already materialized

`data/canonical/samaveda_pilot_v1/passages.jsonl` already carries 139 SV passages at
`status: CANONICAL`, including `A4:P01:R1:D06:V03` with 197 characters of merged text.
`key_pattern: null` never prevented that — which is a separate finding: **the null key was not
functioning as a safety mechanism.**

### One further latent CRITICAL defect on the intended canonical path

`SamavedaWikisourceAdapter.parse_at_address` writes the edition **running number** straight into
the identity-bearing `hierarchy["verse"]`:

```text
hierarchy['verse'] = [45, 46, ... 54]        <- RUNNING numbers
minted key of first = VG:SV:KAU:A1:P01:R1:D05:V45
TRUE key of that verse (GRETIL) = VG:SV:KAU:A1:P01:R1:D05:V01
keys minted from Wikisource that DO NOT EXIST in GRETIL: 19 of 29
```

The docstring warns callers to convert; **no converter exists anywhere in the repository**, there
is no bounds check to reject `V586` inside `D01`, and the only consumer is broken. **In daśati 1
running equals local, so the bug is invisible in exactly the unit a first test would choose.** It
has not reached committed data — latent, not realized.

### And the corroboration artifact is not regenerable

`scripts/compare_samaveda_sources.py` **does not run at HEAD** — verified:
`TypeError: SamavedaWikisourceAdapter.parse() got an unexpected keyword argument 'arcika'`.
`parse` was correctly narrowed to `parse_at_address`; the caller was never updated. Combined with
`data/canonical/**` being gitignored, **the committed comparison artifact is untracked and
unreproducible from a clean clone** — the sealed-artifact hazard again.

### What the adversarial pass could NOT break — recorded, because it matters

**The key *shape* is sound.** 565,566 identities minted across all four works: **0 collisions** in
key, URN or UUID space. Determinism clean (`uuid5` reproduced manually and byte-matched; namespace
is a committed literal; all SV URNs ASCII). Variable depth clean — 219,348 container inputs, 219,348
distinct keys, and `0` (absent) versus `None` (unaddressed) provably distinguishable. Round-trip
safe **even under overflow**, because `:02d` is a minimum width and the letter prefixes keep the key
parseable. Coordinates provably independent of document order — a 3-seed paragraph *and* line
shuffle produced byte-identical key sets.

**The design is not the problem. Freezing that design around a known-defective referent set is.**

Two format findings worth fixing while it is still free: `A` and `R` are unpadded while `P`/`D`/`V`
are `:02d`, so SV is the only work whose keys are not lexicographically sortable at `arcika >= 10`
or `ardha >= 10`; and `V{verse:02d}` diverges from the `V{:03d}` used by RV, YV and AV.

---

## 6. GROUND 2 — arcika arity (Agent C2)

The top slot of the key encodes **Pandey arity**, and it is the least corroborated claim in the
entire SV record.

| Arity | Witnesses |
|---|---|
| **4 flat sibling arcikas** | GRETIL, TITUS — **both Pandey lineage, i.e. ONE witness** |
| **2 top-level arcikas** (Chandas / Āraṇya / Mahānāmnya being the three **sub-segments of Pūrvārcika**) | Sanskrit Wikisource, Griffith 1895, Wikipedia, Vedic Heritage Portal (GoI), Vedapeetha, B. R. Sharma HOS 57 |
| **3** | Caland / Kashikar |

**"Exactly four arcikas" has 1 witness, 0 independent corroborations, and 6 independent
contradictions.**

The project credits **TITUS** with corroborating it — but TITUS is Pandey lineage, which the same
documents concede elsewhere. **This is the identical overstatement the repository was already
burned by** (counting Pandey re-publications as corroboration), one layer deeper: the earlier
correction fixed the *textual* witness count and left the *arity* claim resting on the same defect.

And a standing note reads *"four, not the two that earlier notes recorded"* — which **inverts the
evidence.** The "two" was right as the top-level division.

### Two verified coordinate collisions

**Collision A — `(1, 1, 2, 6)`:** Wikisource `1.1.2.6` = Pūrvārcika / chandas / **prapāṭhaka 2** /
daśati 6 = RN **145–154**. GRETIL `1 1 2 06` = arcika 1 / **prapāṭhaka 1** / **ardha 2** / daśati 6
= RN **55–62**. **Disjoint.**

**Collision B — slot 1, value `2`:** GRETIL/TITUS = **Āraṇyārcika**, RN 586–640 (55 verses).
Everyone else = **Uttarārcika**, RN 651–1875 (**1,225 verses**). Also at 3-number granularity:
Wikisource `1.2.1` = RN 586–594; GRETIL `1 2 1` = RN 97–144. **Same literal address, disjoint
passages.**

**This directly answers the brief question** *"Could another Kauthuma witness use the same
coordinates for different passages?"* — **Yes, twice, verified on both sides.** The condition the
identity policy required is not met.

Freezing today would canonise a 1-witness, 6-contradiction arity claim at the top of the key,
mis-addressing 1,280 of 1,875 verses relative to the majority convention.

---

## 7. Rights — Agent E: `APPROVE_WITH_CONDITIONS`

**Rights do not block the freeze.** A `key_pattern` commits to a *structural address scheme*; that
division is traditional and pre-modern, is no modern editor copyrightable creation, and copies no
expression from any edition. **Rights cannot attach to the thing being frozen.**

The verdict is independent of scholarly quality and does not supply Agent F limb.

### Findings that stand regardless of the freeze decision

- **Licence VERIFIED.** `meta=siteinfo&siprop=rightsinfo` returns CC BY-SA **4.0** with the
  unusual `/deed.sa` suffix, matching the recorded `license_statement_verbatim` character for
  character.
- **One recorded rationale REFUTED.** The claim that *"CC BY-SA attribution on a wiki requires
  identifying contributors"* is **false**. WMF Terms of Use §7(b) permits attribution by **any one
  of three** methods, including a URL alone. The 840-page revision-ID pinning is required for
  **reproducibility against a mutable source** and CC BY-SA §3(a)(1)(A)(iii) URI retention — a
  **redistribution** precondition, not an identity one.
- **The independence proof is WEAK, downgraded from "PROVEN."** It rests on **one locus** (running
  verses 1–2), and the defect it turns on is *conspicuous* — exactly what a copyist would repair.
  *"A text cannot inherit from a source it does not share an error with"* is **not valid as a
  universal**; it excludes only *verbatim uncorrected* inheritance, not copy-then-correct or
  copy-then-collate. Honest statement: **"not a verbatim copy of the Pandey text at the one locus
  tested, and using a different numbering system; full independence of descent is
  unestablished."**
- **A RIGHTS-13 channel nobody had named.** The load-bearing independence comparison is published
  as **IAST versus IAST**, while the Wikisource artifact is **Devanagari**. The Wikisource side
  therefore passed through **agent-performed transliteration of a passage the model holds
  memorised in the target script.** RIGHTS-13 operational test ("transcribe what is on the page")
  does not obviously cover cross-script rendering, because rendering *feels* mechanical. It is
  generative. The pinned bytes make this checkable, so it is a **verification gap, not a
  demonstrated breach.**
- **RIGHTS-9 chain of title is UNRESOLVED AT ITS ROOT**, and the repository frames this as merely
  bibliographic. Because the print antecedent is unknown, it **cannot be shown to be public
  domain.** Both surfaced candidates are **modern works by living authors** — Narayanaswami
  companion volumes carry *"PPN © January 2025."* Countervailing and weighed: a faithful
  transcription of an ancient mantra text copies no original authorship, and the sampled arcika
  pages carry **no accent notation**, which is precisely the feature defining the Narayanaswami
  edition — positive evidence against that candidate.
- **The edition gap is universal to this Veda, not specific to Wikisource.** No Kauthuma digital
  witness in the registry names a printed edition: GRETIL empty `<bibl>`; the Sanskrit Library
  chain resolves only to *"Editor: Anshuman Pandey, 1999."* **Refusing to freeze until one does
  would be a permanent block, not a deferral.**
- **The "840 pages" figure must never sit beside the identity claim.** **725 of the 840 are gāna**
  (grāmageya 190, āraṇyakageya 86, ūha 362, ūhya 87 — verified). The arcika portion is **~106
  pages**.
- **Structural-metadata use is legitimate, not laundering** — and the rule already exists, under
  `REFERENCE_ONLY`: *"structural metadata ABOUT it (counts, presence, hierarchy) may be recorded,
  but its content is not copied into the corpus."* **Gap:** the artifact actually being mined is
  `PERMISSION_REQUIRED`, whose semantics carry **no** structural-metadata clause. The rule is
  attached to the wrong status class for two of the three artifacts it is applied to.
- **A cross-Veda ShareAlike incompatibility recorded nowhere in the repository.** SV and YV are
  **CC BY-SA 4.0**; the Rigveda primary is **CC BY-NC-SA 4.0**. BY-NC-SA is **not**
  BY-SA-compatible, so under CC BY-SA §3(b)(1) **a combined four-Veda release is not licensable as
  a single adapted work** from current sources. This bears directly on the four-Veda ingestion
  gate and is recorded now, at low cost, rather than at release time.

### Conditions that survive the RESEARCH_REQUIRED decision

Recorded because they must be met by whoever eventually freezes, and several are worth doing now:

1. Add `source_edition: UNIDENTIFIED` to the Wikisource SV artifact record — it currently has **no
   such field at all**, and silence is the failure mode RIGHTS-8 forbids.
2. Record `upstream_print_rights_status: UNRESOLVED` with the RIGHTS-9 reasoning.
3. **Register a `WIKISOURCE_SA.SV.KAU.*` text_version** — the **only** SV text_version today is
   `GRETIL.SV.KAUTHUMA` at `PERMISSION_REQUIRED`, so freezing would bind the frozen key, in the
   only registry a build resolves rights through, to the **encumbered lineage**. Agent E named this
   the one condition it would not waive.
4. Correct the CC BY-SA attribution rationale (see above).
5. Complete the truncated `footer_verbatim` — the recorded value drops the trailing
   `; अन्याः संस्थित्यः अपि सन्ति` ("additional terms may apply"), truncating a caveat in our own
   favour.
6. De-adjacency the "840 pages" figure from the arcika identity claim.
7. Downgrade the independence claim from "PROVEN" everywhere it appears.
8. Extend RIGHTS-13 to **cross-script rendering**.
9. Carry the gāna scope note into any release artifact.
10. Record the cross-Veda ShareAlike incompatibility.

---

## 8. What this session changed

| Dimension | Before | After |
|---|---|---|
| `source_edition_identity` | `OPEN_RESEARCH`, "established negative", 2 open candidates | **Negative positively established**; both candidates **refuted**; corpus shown to be hand-keyed with no print antecedent; a **5-volume PD printed edition located** with recension open |
| Addressing corroboration | 2 independent textual witnesses + 1 addressing scheme | **+ an identified printed edition naming all five levels in its colophons**; ardha proven printed |
| `structural_count_discrepancy` | `RESOLVED`, mechanism = "5 absent RNs + residue of 2" | `RESOLVED`, mechanism **refuted and replaced**: source prints **1875**; `1875 = 1868 − 2 + 9`; `UNRESOLVED_COUNT_RESIDUE = 0` |
| Identity blocker | edition identity, an **external dependency** | **referent integrity** (bounded engineering) + **arcika arity** (narrow review) |
| Known coordinate collisions | none recorded | **2 verified** |
| Phantom keys | none recorded | **1 verified** — `A4:P04:R2:D01:V13` |
| Governance question | open | **answered: edition identity is NOT required to freeze Passage identity** |

### Defects found in the existing record, all corrected in this run

1. **A false claim that was never true.** `docs/reports/FOUR_VEDA_QA_REPORT.md` asserted
   *"`key_pattern` is now set and `identity_status` moved `RESEARCH_REQUIRED -> PROVISIONAL`."*
   `git log --all -S PROVISIONAL -- data/registry/works.yaml` returns **nothing**: no such state
   ever landed in any commit. **The claim was false when written.**
2. **The stale-claim audit certified the absence of exactly that claim.**
   `docs/qa/STALE_FOUR_VEDA_CLAIMS.md` records *"'Samaveda already having frozen canonical IDs' —
   not found anywhere. Every reference correctly states `RESEARCH_REQUIRED` / candidate-only."*
   It missed a document **inside its own declared scope** — a fourth instance of the scope gap that
   audit itself confesses to.
3. **The count mechanism was wrong in six places, three of them YAML registries.**
4. **A stale "count gap remains open" claim** in `FOUR_VEDA_STRUCTURAL_MODEL.md` §7, contradicting
   the registry `RESOLVED`.
5. **A stale meta-claim**: the same §7 says `SOURCE_POLICY.md` still carries the superseded
   two-arcika hierarchy. It does not — it was already corrected. **Ironically, its "two arcikas"
   was right about the top-level division.**
6. **A wrong Griffith book count** used as the sole structural support for the recension-mismatch
   verdict (six vs nine; measured 6 + 9).
7. **The Griffith DECADE claim cited to an artifact that does not contain it** (`Decad` × 0 in the
   pinned file).
8. **`make lint` is red at `dc160d7`** — `ruff format --check` fails on 6 files, inherited from the
   prior commit.

---

## 9. Exit criteria — status

| Criterion | Status |
|---|---|
| Canonical witness/source decision recorded | **MET** — Wikisource selected; recorded with an explicit provenance limitation |
| Recension Kauthuma re-confirmed against the selected witness | **MET** for the selected witness; **NOT MET** for the newly found printed edition |
| Edition/provenance decision recorded | **MET** — explicit, evidence-backed `PRINT_EDITION_NOT_IDENTIFIABLE`, with the residual named as a single external dependency |
| 1,868/1,875 discrepancy explained | **MET, exactly** — `UNRESOLVED_COUNT_RESIDUE = 0` |
| Stable identity/key frozen (`identity_status: FINAL`) | **NOT MET** — grounds 1 and 2 |
| Arcika vs gāna distinction stated explicitly | **MET** — see §11 |
| Deterministic rebuild maintained | **MET** — verified byte-identical, and coordinates proven order-independent |

---

## 10. The path to closure — ordered, and each item bounded

**Engineering (no research required):**

1. Repair the **7 collided addresses** and retract the **phantom `V13`**, using the running-number
   derivations in the count report. All target slots are proven vacant. Record each as a
   `SourceAssertion` with `NEEDS_REVIEW`.
2. Add a **content-binding gate** — store `content_sha256` per canonical key and fail the build
   when a frozen key text hash changes without a declared migration. **This is the missing
   invariant, and it is worth more than the freeze itself.**
3. Fix `parse_at_address` to require daśati-local indices (or refuse to emit `hierarchy`), and add
   the bounds check rejecting `V586` inside `D01`.
4. Repair `scripts/compare_samaveda_sources.py` and add a smoke test.
5. Pad `A` and `R` to `:02d` and widen `V` to `:03d` for consistency with RV/YV/AV — **free now,
   impossible after freezing.**
6. Register the `WIKISOURCE_SA.SV.KAU.*` text_version (Agent E condition 3).

**Philological review (one decision each):**

7. **Adjudicate arcika arity** — 2, 3 or 4 — and record the decision with its reasoning. This is
   the only genuine research item, and it is narrow.
8. Read the recension off Sāmaśramī vol 1 pp. 1–9 (`in.ernet.dli.2015.487112`).
9. Re-verify the independence claim at **codepoint level against the pinned Devanagari**, at more
   than two loci.

**Governance (one change):**

10. Supersede the `ADR-017` "not even provisionally" clause, then move `identity_status` to
    `PROVISIONAL` — the value its own definition already requires.

---

## 11. Scope — arcika only

```text
SAMAVEDA_ARCIKA_CORPUS       = the scope of VG:WORK:SV:KAU, ~1875 verses, ~106 Wikisource pages
SAMAVEDA_GANA_CORPUS         = SEPARATE_FUTURE_DATASET
```

The Kauthuma **gāna** collections — roughly **2,639 gānas** across grāmageya, āraṇyakageya, ūha and
ūhya/rahasya, occupying **725 of the 840** Wikisource pages — are a **parallel and larger** body
that `VG:WORK:SV:KAU` does not cover and cannot address. **Any claim that VedaGraph "has the
Sāmaveda" while holding only the arcika is false.** The gānas require their own `work_id`.

**Architectural note, to prevent a future collision:** because the arcika key is `VG:SV:KAU:A…` and
its URNs are `urn:vedagraph:{mantra,section}:samaveda:kauthuma:arcika:…`, a future gāna work must
introduce its own work segment and its own URN path component. It must **not** reuse the `arcika`
URN component, and gāna is **not** equivalent to arcika. No gāna identities are designed here.

---

## 12. Four-Veda gate

```text
FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKERS_PARTIALLY_CLOSED
FULL_SV_YV_AV_CANONICAL_INGESTION_AUTHORIZED = false
NEXT_PROJECT_PHASE = SAMAVEDA_REFERENT_INTEGRITY_REPAIR
```

**Precise remaining blocker:** `VG:WORK:SV:KAU` referent integrity — 7 collided addresses, 1
phantom canonical key, and the absent key-to-text binding invariant — plus one narrow philological
adjudication of arcika arity. **Neither is the source-edition question this session was convened to
close.**

YV (`CLOSED_WITH_REVIEW_ITEM`) and AV (`PD_TRANSCRIPTION_PATH_VALIDATED`) are unchanged and were
not reopened.

**Newly surfaced, and it gates the combined release rather than the ingestion:** SV and YV are
CC BY-SA 4.0 while the RV primary is CC BY-NC-SA 4.0, which is **not** BY-SA-compatible. A combined
four-Veda release is **not licensable as a single adapted work** from current sources.
