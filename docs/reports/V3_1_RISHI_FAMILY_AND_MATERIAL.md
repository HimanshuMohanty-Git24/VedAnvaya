# V3.1 — the ṛṣi family layer, and the material-culture recall audit

Two passes. The first built a layer that was declared and empty; the second audited an
existing layer for attestations it was missing. Every number below was measured against
the live graph after the write, not taken from a loader's summary.

Artifact: `data/domain/vedagraph_domain_v2/rishi_families_v1.json`
Derivation: `src/vedagraph/domain/rishi_families.py`
Builder: `scripts/build_rishi_families.py`
Loader: `vedagraph.domain.v3_loader.load_rishi_families`, projected as layer
`rishi_families` in `scripts/build_knowledge_model_v3.py`
Tests: `tests/domain/test_rishi_families.py` — 14 passed, 1 live-gated

---

## 1. The derivation rule, in one sentence

A ṛṣi belongs to a family when a token of the Anukramaṇī's own seer string **equals** one
of the finitely many inflected surfaces of a vṛddhi patronymic hand-listed in
`GOTRA_PATRONYMICS` together with its eponym — never when two names merely resemble each
other — and one family exists per stated patronymic stem.

Re-runnable form, precisely:

1. Read the three ṛṣi registries (`rishis.yaml`, `rishis_yv.yaml`, `rishis_av.yaml`). For
   the Atharvavedic rows, fold Whitney's orthography (`ç`→`ś`, `n̄`/`n̈`→`ṅ`, `āu`→`au`,
   `āi`→`ai`, drop the typographic apostrophe) and strip parentheticals and verse-range
   prefixes; for the Yajurvedic rows **keep** parentheticals, because there they hold the
   other half of the same name (`kāśyapaḥ(vatsāraḥ-)` = `vatsāraḥ kāśyapa`) rather than a
   wish annotation.
2. If the whole label is in `NON_SEER_ASCRIPTIONS`, stop: no family, no decomposition.
3. Otherwise tokenize on whitespace and punctuation, lowercase, and for each token:
   equality against `SURFACE_INDEX` → membership (`patronymic-token-equality-v1`);
   equality against `DECLINED_INDEX` → refusal recorded by name; otherwise attempt a
   longest-match split of the token into a full patronymic surface plus a residue of at
   least three characters (`patronymic-fused-token-split-v1`); otherwise the token is a
   personal name.
4. `vasiṣṭhaputrāḥ` is handled by an explicit one-entry table
   (`explicit-descent-compound-v1`) because it states descent in words, not by vṛddhi.
5. One edge per (ṛṣi, family); token equality beats a fused split for the same stem.
6. `surfaces(stem)` is generated, not listed: for an `-a` stem, the stem itself plus
   `-ḥ -s -ś -ṣ -r` and the replacements `-o -au -āḥ -ā -ī -e`; for an `-i` stem, `-i -iḥ
   -ir -iṇ -ī -yau -iṇaḥ`. Those are the visarga-sandhi outcomes and the nominative
   singular, dual, plural and feminine, so matching stays an equality test against a
   closed set. The table is checked at import for surface collisions and raises rather
   than letting membership depend on table order.

**Why this is source-stated evidence.** The first element of a Ṛgvedic Anukramaṇī seer
string is a vṛddhi derivative, and vṛddhi is the Sanskrit grammatical marker of descent
(`bhṛgu`→`bhārgava`, `atri`→`ātreya`, `aṅgiras`→`āṅgirasa`, `kaṇva`→`kāṇva`). Confirmed
against all 367 Ṛgvedic labels, not a sample: the shape `patronymic + personal name` holds
throughout, and the two halves are separable.

**Namespaces attempted.** All three. None declined. The Atharvavedic yield is small (8 of
134) and that is reported as a result, not hidden.

---

## 2. What landed

Measured baseline before the write: **108,689 nodes / 263,887 relationships**, `RishiFamily`
= 0 nodes, `BELONGS_TO_FAMILY` = 0 edges.

| measure | value |
|---|---|
| `RishiFamily` nodes | **87** |
| `(Rishi)-[:BELONGS_TO_FAMILY]->(RishiFamily)` edges | **305** |
| `BELONGS_TO_FAMILY` edges with any other endpoint labels | **0** |
| ṛṣis with at least one family | **302** |
| ṛṣis decomposed (patronymic / personal name written) | **729 of 729** |
| edges missing `quality_tier`, `knowledge_layer`, `grade_basis`, `evidence_basis`, `evidence`, `source_token`, `derivation` or `attribution_precision` | **0** |
| node / relationship delta | +87 / +305, exactly as sent |
| loader report | `sent=1121 landed=1121` |
| second run (idempotence) | same counts; mark-and-sweep deleted the one family a table correction retired |
| `scripts/check_live_invariants.py` | `rishi_family_membership_without_evidence` **0**, 0 failing |

Memberships by derivation: 290 `patronymic-token-equality-v1`, 14
`patronymic-fused-token-split-v1`, 1 `explicit-descent-compound-v1`.

### Coverage, as a measured fraction

| population | assigned | total | share |
|---|---|---|---|
| all registry rows | 302 | **729** | **41.4%** |
| rows that are actually seers (729 − 113 non-seer) | 302 | **616** | **49.0%** |
| `RV_WSC2023_ANUKRAMANI` | 260 | 367 | 70.8% |
| `YV_VSM_RSISUCI` | 34 | 228 | 14.9% |
| `AV_WHITNEY_ANUKRAMANI` | 8 | 134 | 6.0% |

Partial and labelled, which is the intended outcome. Assigning a family to every ṛṣi would
mean inventing evidence for roughly 400 of them.

### Grading

Every edge: `knowledge_layer = L2_DETERMINISTIC_DERIVED`, `quality_tier = TIER_B`,
`evidence_basis = SOURCE_METADATA`, `provenance_class = SOURCE_DERIVED_SCOPE`,
`confidence = 1.0`, `evidence` = the exact Anukramaṇī string, `evidence_count = 1`,
`source_token` = the token inside it that licensed the edge, `derivation` = the vṛddhi
statement, `source_id` ∈ {`WSC2023`, `WIKISOURCE_SA`, `WIKISOURCE_WHITNEY_AV`}, and a
`grade_basis` that differs per method so the weaker derivation stays visible.

`BELONGS_TO_FAMILY` was added to `tiers.LAYER_OWNED_GRADES`, because the generic re-grader
would collapse those two `grade_basis` sentences into one; and to `schema.DOMAIN_REL_INDEXES`
as an index on `method`, not on `quality_tier`, since all 305 rows are TIER_B and the tier
partitions nothing. `REL_BELONGS_TO_FAMILY` was already declared in `ontology.py` (constant,
`DOMAIN_RELATIONSHIPS`, and a `RELATIONSHIP_SIGNATURES` entry `Rishi → RishiFamily`), so the
undeclared-live-predicate failure mode does not apply here.

#### `attribution_precision = 'CONTAINER_INHERITED'` — the reasoning

Neither endpoint of this edge is a passage, so on a strict reading the axis does not apply
and the property should be absent. The graph-wide invariant that every edge is fully graded
wins; and once the property must hold *something*, the only safe value is the inherited one.
All three ṛṣi indices state their patronymic at **container** level and never inside a
verse: the Ṛgvedic Sarvānukramaṇī labels a sūkta (10,093 of the RV's 10,565 `HAS_RISHI`
edges are inherited), the Atharvavedic index labels a sūkta in all 5,084 cases, and the
Yajurvedic ṛṣisūcī is an index over the whole Vājasaneyi Saṁhitā. A leaderboard walking
`Passage → HAS_RISHI → Rishi → BELONGS_TO_FAMILY` therefore can never be more precise than
sūkta-wide, and `PER_PASSAGE` here would let a query advertising per-verse strictness
quietly admit container-inherited evidence. `scope_origin = 'SUKTA_WIDE'` records the same
fact in the vocabulary `PRECISION_BY_SCOPE_ORIGIN` maps from, so the two cannot drift.

---

## 3. Families created

87 families, one per stated patronymic. No two stems merged: `kāṇva` and `kāṇvāyana` are
separate because the Anukramaṇī does not join them on the page.

| family | members | eponym | namespaces |
|---|---|---|---|
| āṅgirasa | 51 | aṅgiras | RV,YV |
| ātreya | 42 | atri | RV,YV |
| kāṇva | 30 | kaṇva | RV,AV |
| bhārgava | 13 | bhṛgu | RV,YV,AV |
| vāsiṣṭha | 13 | vasiṣṭha | RV |
| bhāradvāja | 11 | bharadvāja | RV,YV |
| kāśyapa | 10 | kaśyapa | RV,YV |
| vaiśvāmitra | 10 | viśvāmitra | RV,YV |
| atharvaṇa | 6 | atharvan | RV,YV,AV |
| bhārata | 4 | bharata | RV,YV |
| mānava | 4 | manu | RV |
| vairūpa | 4 | virūpa | RV |
| dhānāka, gautama, gārtsamada, kauśika, kākṣīvata, plāta, prāgātha, vaikhānasa, vāmadevya, śāktya | 3 each | | |
| dairghatamasa, gaupāyana, ghaura, hārita, mādhucchandasa, mārīca, paurukutsa, sauhotra, tārkṣya, vārṣāgira, āgastya, āptya | 2 each | | |
| ailūṣa, airammada, aucathya, aurava, auśija, auśinara, bhauma, bhauvana, bhālandana, bhāmyaśva, daivodāsi, dārḻhacyuta, ghauṣeya, gārgya, gāthina, hairaṇyastūpa, jāna, kautsa, kātya, kāvya, kāṇvāyana, naudhasa, nāhuṣa, nārmedha, paijavana, praiyamedha, pārucchepi, rauhidaśva, rāhūgaṇa, saubhara, sthaura, sāmmada, sāṁvaraṇa, sāṅkhya, traivṛṣṇa, vaidarbhi, vainya, vaitahavya, vaiyaśva, vādhryaśva, vāndana, vārṣṭihavya, vāsukra, yauvanāśva, ājīgarti, āmahīyava, āmbhṛṇī, ārṣṭiṣeṇa, āśvya, śailūṣa, śairīṣi, śaunaka, śyāvāśvi | 1 each | | |

Three ṛṣis carry **two** stated patronymics and therefore two memberships, which is a
nested lineage and not a conflict: `auśijo dairghatamasaḥ kakṣīvān` (auśija + dairghatamasa),
`traivṛṣṇastryaruṇaḥ paurukutsastrasadasyuḥ` (traivṛṣṇa + paurukutsa), and the Atharvavedic
`Bhārgava Vāidarbhi` (bhārgava + vaidarbhi).

### The 14 fused splits, audited individually

The fused split is the only place this layer supplies a word boundary the source did not
print, so all of them were checked one by one against the Anukramaṇī reading and pinned as
a closed set in the test file. **14 of 14 correct; no false positives.**

`kāṇvastriśokaḥ`→kāṇva·triśokaḥ · `mānavaścakṣuḥ`→mānava·cakṣuḥ ·
`paurukutsyastrasadasyuḥ`→paurukutsa·trasadasyuḥ · `pārucchepiranānataḥ`→pārucchepi·anānataḥ ·
`traivṛṣṇastryaruṇaḥ`→traivṛṣṇa·tryaruṇaḥ · `paurukutsastrasadasyuḥ`→paurukutsa·trasadasyuḥ ·
`vāsiṣṭhaścitramahāḥ`→vāsiṣṭha·citramahāḥ · `āptyastritaḥ`→āptya·tritaḥ ·
`śyāvāśvirandhīguḥ`→śyāvāśvi·randhīguḥ · `bandhuḥ śrutabandhurviprabandhugaupāyanāḥ`→gaupāyana ·
`kumārahārita`→hārita·kumāra · `dadhyaṅṅātharvaṇa`→ātharvaṇa·dadhyañc ·
`luśodhānāka`→dhānāka·luśa · `svastyātreya`→ātreya·svasti.

---

## 4. Ṛṣis deliberately left unassigned — 427 rows, in nine classes

Written onto the node as `family_assignment_class`, so "why does this seer have no family?"
is answerable from the graph and not only from this file.

| class | n | RV | YV | AV | what it means |
|---|---|---|---|---|---|
| `NON_SEER_ASCRIPTION` | **113** | 45 | 42 | 26 | Not a person. See §5. |
| `NO_PATRONYMIC_STATED` | 170 | 10 | 117 | 43 | A bare personal name, or a string this layer cannot parse. `sindhu dvīpaḥ`, `viśvāmitrajamadagnī`, `plāyoṅgirāsaṅga`; the whole Yajurvedic bulk, whose index gives bare names by design. |
| `EPONYM_WITHOUT_STATED_PATRONYMIC` | 69 | 0 | 24 | 45 | The label is the **non-vṛddhi eponym himself** — `bharadvāja`, `vasiṣṭha`, `atri`, `kaṇva`, `gṛtsamada`, `Bhṛgu`, `Atharvan`, `Kaçyapa`. The source states no patronymic for him. |
| `THEONYMIC_DESCENT` | 45 | 38 | 7 | 0 | A stated patronymic naming a **deity** as the ancestor: `aindra`, `prājāpatya`/`prājapatya`, `vaivasvata`, `vāruṇi`, `bārhaspatya`, `saurya`, `saumya`, `sāvitrī`, `āgneya`, `āditya`, `tvāṣṭra`, `nairṛta`, `maitrāvaruṇi`, `brāhma`, `gandharva`, `kāmayānī`, `vātāyana`, `yāmāyana`, `arbhava`. Divine parentage is not a gotra, and Q2/Q19/Q26 ask about seer families. |
| `COLLECTIVE_LINEAGE_COMPOUND` | 12 | 0 | 0 | 12 | `Bhṛgvan̄giras`, `Atharvān̄giras`, `Pratyan̄girasa` — dvandvas naming the two priestly stocks the Atharvaveda as a whole is ascribed to, not one seer's father. Reifying them would have roughly doubled apparent AV coverage on evidence that does not support it. |
| `TITULAR_NOT_DESCENT` | 8 | 4 | 4 | 0 | `parameṣṭhī` ("the highest"), `kāśirājaḥ` ("king of Kāśi"), `tāpasa` ("ascetic"), `vairāja` (from virāj, a metre). Status words, not ancestors. |
| `SOURCE_SPELLING_OUTSIDE_TABLE` | 5 | 5 | 0 | 0 | `bhāgavo nemaḥ`, `daivaodāsiḥ parucchepaḥ`, `vaivasvasto manuḥ`, `ātreyyapālā`, `āṅgirhavirdhānaḥ`. Each is one apparent misprint away from a table stem. Declined **by name**: "one vowel out" is exactly the distance between `bharadvāja` and `bhāradvāja`, and emending here would license emending anywhere. |
| `KINSHIP_NOT_DESCENT` | 3 | 3 | 0 | 0 | `agastyasvasā` (Agastya's sister), `vasukrapatnī` (Vasukra's wife), `agastyāntevāsī brahmacārī` (Agastya's resident pupil). Real relations to named men; none patrilineal. |
| `MYTHIC_DESCENT` | 1 | 1 | 0 | 0 | `paulomī śacī` — descent from Puloman, an asura. |
| `ETYMON_UNCERTAIN` | 1 | 1 | 0 | 0 | `cāpsavo manuḥ`: `cāpsava` sits in patronymic position and is vṛddhi-shaped, but this layer cannot state its eponym — `c-āpsava` is not a vṛddhi of `apsu`. |

`kutsaḥ(parameṣṭhī vā-)` and `parameṣṭhī vā kutsa` are the Yajurvedic index's *alternative*
ascriptions ("Parameṣṭhin, or Kutsa"). They are filed under `TITULAR_NOT_DESCENT` and no
family is created, because the source does not commit to one seer.

---

## 5. The non-seer finding — 113 of 729 registry rows are not people

Asked for by the coordinator after Agent B measured the strict per-passage ṛṣi leaderboard
with **`devāḥ` — "the gods" — at rank 1**. Confirmed and quantified.

| kind | n | RV | YV | AV |
|---|---|---|---|---|
| DEITY | 58 | 20 | 24 | 14 |
| ABSTRACTION | 21 | 3 | 8 | 10 |
| MYTHIC_BEING | 13 | 9 | 3 | 1 |
| DEITY_GROUP | 11 | 5 | 6 | 0 |
| PLANT_OR_ANIMAL | 5 | 4 | 0 | 1 |
| COLLECTIVE | 3 | 2 | 1 | 0 |
| OBJECT | 2 | 2 | 0 | 0 |
| **total** | **113** | **45** | **42** | **26** |

Written to the graph as `Rishi.is_seer` (boolean) and `Rishi.non_seer_kind` (the kind
above). Measured live: **616 seers, 113 non-seers, 729 total**. The rows are **not**
deleted — the tradition really does ascribe those hymns to those beings, and deleting the
ascription would remove a true fact about the corpus.

Examples across the kinds: `devāḥ`, `agniḥ`, `indraḥ`, `aditiḥ`, `marutaḥ`, `nadyaḥ`
("the rivers"), `akṛṣṭā māṣāḥ` ("the unploughed beans"), `pṛśnayo ajāḥ` ("the dappled
goats"), `godhā` (the monitor lizard), `juhūḥ` (the offering-ladle), `saptarṣayaḥ`
("the seven seers", a collective and not one of them), `vṛṣākapiḥ`, `urvaśī`, `saramā`,
`sārparājñī`; Yajurvedic `prajāpati` (222 occurrences), `devā`, `viśvedevā`, `aśvinau`;
Atharvavedic `Brahman` (83 rows) and `Cātana` (11 rows — a hymn *class*, "expelling",
not a person at all).

### A defect inside the fix

The first version of this classification was an intersection with
`data/registry/devatas.yaml`. It found 18 rows, and **3 of the 18 were human seers** —
`purūravāḥ`, `romaśā` and `svanayo bhāvayavyaḥ` are each *also* named as the devatā of the
hymn they see, which is ordinary for a dialogue hymn or a dānastuti. A 17% error rate on
the question "is this a person?", plus roughly 95 misses. The intersection was measuring
*appears in the deity registry*, not *is not a seer*. The deity registry is no longer
consulted; `NON_SEER_ASCRIPTIONS` is a hand list of 99 keys with a gloss each.

Consequence for the family layer, and it is intended: a non-seer row creates **no** family
even when its label carries a patronymic. `cākṣuṣo agniḥ`, `saucīko agniḥ`, `sauvīko
agniḥ` and `pāvako agniḥ` are Agni under four epithets, so the `cākṣuṣa` family — whose
only member was a god — was retired by mark-and-sweep on the second projection run
(87 families, not 88).

---

## 6. Q2 — the decomposition, and what the query module still needs

Written to every one of the 729 `Rishi` nodes:

| property | meaning | populated |
|---|---|---|
| `patronymics_iast` | every stated patronymic, in label order | 729 (empty where none) |
| `patronymic_iast` | the first of them | 302 |
| `personal_names_iast` | the tokens that are not patronymics | 729 (empty where none) |
| `personal_name_iast` | the first of them | 585 |
| `decomposition_method` | which rule split the label | 729 |
| `family_assignment_class` | why there is no family, when there is none | 427 |
| `is_seer` / `non_seer_kind` | §5 | 729 / 113 |

### Written spec for the integrator — `src/vedagraph/domain/queries.py`

I do not own that module. Four changes, in priority order.

**(a) `rv_seer_leaderboard` (new) — Q2, and it must be presented as a pair.**
Q2's frozen criterion is the Agni leaderboard on **verse-specific** attribution with the
inherited-inclusive figure shown alongside, or the strict one alone. Return both columns
from one query rather than two queries a reader might quote separately:

```cypher
MATCH (p:Passage:Mantra {veda: $veda})-[h:HAS_RISHI]->(r:Rishi)
WHERE r.is_seer AND (p)-[:MENTIONS_DEVATA]->(:Devata {entity_key: $devata})
RETURN r.display_label            AS seer,
       r.patronymic_iast          AS patronymic,
       r.personal_name_iast       AS personal_name,
       count(DISTINCT CASE WHEN h.attribution_precision = 'PER_PASSAGE'
                           THEN p END) AS strict_verses,
       count(DISTINCT p)               AS inherited_inclusive_verses
ORDER BY strict_verses DESC, inherited_inclusive_verses DESC, seer LIMIT 25
```

Three things the caveat must state, all measured:
- `WHERE r.is_seer` is **required**. Without it the strict leaderboard's rank 1 is
  `devāḥ`. 113 of 729 ṛṣi rows are not people.
- `HAS_RISHI` inheritance is not uniform: RV 10,093 of 10,565 inherited, **AV 5,084 of
  5,084**, YV 0 of 2,240. So a strict Atharvavedic leaderboard is **empty by construction**
  and must be reported as *"layer absent: the Atharvavedic index labels only sūktas"* —
  never returned as a zero, which reads as "no Atharvavedic seer praised Agni".
- With YV at 0 of 2,240 inherited, the Yajurvedic `strict` and `inherited_inclusive`
  columns are identical, and a reader comparing across Vedas needs to be told that.

**(b) `rv_family_books_versus_outer_books` — do not change it.** Checked: it groups on
`substring(canonical_key, 10, 3)` and imports the conventional stratigraphic book split as
a query parameter. It says nothing about ṛṣi families and nothing in it needs to move. Its
`family`/`outer` parameter names refer to *books*, not to `RishiFamily`, and the caveat
already says so; worth one clarifying sentence so the new layer does not make the name
misread.

**(c) `rishi_family_leaderboard` (new) — Q19, Q26, Q62.**

```cypher
MATCH (r:Rishi)-[:BELONGS_TO_FAMILY]->(f:RishiFamily)
OPTIONAL MATCH (p:Passage:Mantra)-[:HAS_RISHI]->(r)
RETURN f.display_label AS family, f.eponym_iast AS eponym,
       f.vrddhi_derivation AS derivation,
       count(DISTINCT r) AS seers, count(DISTINCT p) AS passages,
       f.namespaces AS vedas
ORDER BY passages DESC, seers DESC, family LIMIT 30
```

Caveat must carry the denominator: **302 of 729 ṛṣi rows (41.4%), or 302 of 616 once the
113 non-seer rows are removed (49.0%)** carry a family, so this ranks the families the
Anukramaṇī names a patronymic for and is silent about the rest. Per namespace: RV 70.8%,
YV 14.9%, AV 6.0%. Filter `WHERE m.method = 'patronymic-token-equality-v1'` for the
290-row subset where the source printed the patronymic as its own word.

**(d) any query that enumerates `RitualRole` — see §8.** It is currently missing `hotṛ`,
and that is a blocker I could not clear.

---

## 7. Material-culture recall audit

**Denominator, stated because it differs from the one in the brief.** The brief quotes
53 of 73 (72.6%). I could not reconstruct that population from any file in the repo, so I
measured a population I can name: the entities declared in
`domain_entities_material.yaml` (45) plus `domain_entities_ritual_v3.yaml` (21) = **66**,
each counted as covered in a Veda when it has at least one `MENTIONS_ENTITY` edge from a
passage of that Veda.

**Two-Veda coverage before: 44 of 66 = 66.7%.** 22 entities were single-Veda.

### The mechanism behind the biggest block of false zeros

VSM 18.12 reads `vrīhayaśca me yavāśca me māṣāśca me tilāśca me mudgāśca me ...` — and the
source prints every noun **joined to the following `ca` with no space**. The folded surface
therefore holds one token `vrīhayaśca`, never `vrīhayaḥ`. So:

- the **token** pass can never match, whatever pausa form the registry lists;
- the **substring** pass is blocked below six folded characters (`tilāḥ` is 5, `māṣāḥ` is
  5) and is run on the Samaveda only.

The densest material-culture line in the entire Yajurveda was unreachable by construction,
and three crops were reading as Atharvaveda-only as a result. Verified directly against the
stored text of `VG:YV:VSM:A18:V012` in both its `EXTRACTED_FROM_CONTAINER` and
`PARALLEL_TEXT` versions.

### Per-entity audit

| entity | aliases searched | found | locators | verdict |
|---|---|---|---|---|
| **VRIHI-RICE** | `vrīhayaḥ` 0 anywhere; `vrīhayaśca` YV 1, 1 host (itself), 0% intrusion | YV attestation | VSM 18.12 | **recall miss** → 1 Veda → 2 |
| **TILA-SESAME** | `tilāḥ` 0 anywhere; `tilāśca` YV 1, 0% intrusion | YV attestation | VSM 18.12 | **recall miss** → 1 → 2 |
| **MASA-BEAN** | `māṣāḥ` AV 1 only (AVS 12.2.53); `māṣāśca` YV 1, 0% intrusion | YV attestation | VSM 18.12 | **recall miss** → 1 → 2 |
| **SURA-SPIRITUOUS-LIQUOR** | `surā` RV 1 / YV 2 / AV 3 but **47% substring intrusion**, dominated by `asurā`; `surām` 22% intrusion; `surāyāṃ` AV 3, 1 host (itself), 0% intrusion | AV attestations | AVS 6.69.1, 9.1.18, 14.1.35 | **recall miss** → 1 → 2. `surā` itself **still declined** — see below |
| **YAVA-BARLEY** | `yavāśca` YV 1, 0% intrusion (`yavāś` alone is 5 chars and 21% intrusion via `hiraṇyavāśī-`) | YV attestation | VSM 18.12 | recall miss, **no coverage change** (already 4 Vedas); added so one line is not evidence for three crops and not the fourth |
| **DHANYA-GRAIN** | `godhūmāśca` YV 1, 0% intrusion | wheat, VSM 18.12 | VSM 18.12 | not added — `godhūma` is wheat, a distinct crop, and folding it into "grain" is a semantic stretch for zero coverage gain (already 3 Vedas) |
| **UDGATR-CHANTER** | `udgātā`, `udgātṛ`, `udgātāraṃ`, `udgātre` — **0 matches anywhere** | nothing | — | **true absence.** The Samaveda's own priest is not named in the SV, YV or AV corpora. The single RV hit the node already has comes from `udgāteva` (RV 2.43.2), sandhi with the following `iva`; corroborates the note already in `domain_entities_ritual_v3.yaml` |
| **NESTR-LEADER** | `neṣṭā` 0 token, 100% intrusion on substring (`yameneṣṭāpūrtena`); `neṣṭrāt` RV 1 (already held) | nothing new | RV 2.37.3 | **true absence** outside the RV |
| **PRASASTR-DIRECTOR** | `praśāstā` RV 2, 0% intrusion | already held | RV 1.94.6, 2.5.4 | **true absence** outside the RV |
| **AGNIHOTRA** | `agnihotram` 0; `agnihotra` AV 2 substring; `agnihotraṃ` AV 1 token | already held | AVS 11.7.9 | **true absence** in RV/SV/YV at token level |
| **LOHA-COPPER** | `lohitam` AV 4 but 28.6% intrusion, and `lohita` = "red / blood" not copper (AVS 11.3.7 `māṃsāni lohitam`) | homonym only | — | **declined**: adding it would be the `ajaḥ`/`ajasya` homonymy error the V1 audit exists to prevent. Zero stays a **true absence** |
| **ISTAKA-BRICK** | `iṣṭakā` YV 1, 40% intrusion | already held | VSM 17.2 | **true absence** outside the YV; bricks are Yajurvedic vocabulary |
| **ASVAMEDHA** | `aśvamedhena` 0 anywhere | nothing | — | **true absence** outside the YV |
| **PARISRUT** | `parisrutā` YV 18 (already held), 0% intrusion; 0 in RV/SV/AV | nothing new | VSM 19.83, 19.95, 20.59, 20.63 … | **true absence** outside the YV |
| **GANGA-RIVER / YAMUNA-RIVER** | `gaṅgāyāṃ`, `yamunāyāṃ` — 0 matches anywhere | nothing | — | **true absence** for those forms. The V1 report's own "clearest cheap win" is the *English* river tokens in Griffith (RV 10.75.5), which is a different pass and was **not** audited here |

**Worst alias in this pass: `surā`** — 4 folded characters, 116 substring hits, **47.2%
intrusion**, dominated by 14× `asurā`, 7× `asurān`, 5× `asurāṇāṃ`, 4× `asurāya`. It is
reported and **not** added.

`domain_entities_ritual_v3.yaml` already declined `surā` deliberately, with a recorded
reason ("three of its six token hits are the dicing-and-drinking topos of AVS 6.70.1 and
RV 7.86.6 rather than an offering"). I re-verified that judgement and **upheld it**;
overturning a documented, evidence-stated refusal to move a coverage number is the same
failure as deleting a single-Veda entity to move it. `surāyāṃ` is a different case and not
a relaxation of the same judgement: 7 characters, 3 token hits, one host (itself), 0%
intrusion, each hit the liquor being poured.

### Coverage after

Aliases added: 5 (`vrīhayaśca`, `tilāśca`, `māṣāśca`, `yavāśca`, `surāyāṃ`). No entities
added, none removed, none retyped. `probe_domain_aliases.py --collisions` reports no
collision with `data/registry/concepts.yaml` for any of them.

| | before | after |
|---|---|---|
| two-Veda coverage | 44 / 66 = **66.7%** | 48 / 66 = **72.7%** |
| entities crossing the two-Veda threshold | — | VRIHI-RICE, TILA-SESAME, MASA-BEAN, SURA-SPIRITUOUS-LIQUOR |
| new mantra-alias pairs | — | 6, across 4 passages |

**Still below the 80% gate, and honestly so.** The residue is dominated by entities whose
single-Veda status is a true fact about the corpus: the six rivers (Ṛgvedic geography), the
Yajurvedic ritual apparatus (iṣṭakā, parisrut, aśvamedha, avabhṛtha, agnicayana), and the
Atharvavedic-only items V3 added.

### NOT YET PROJECTED — one action for the integrator

The five aliases are committed to the artifacts; the `MENTIONS_ENTITY` edges are **not yet
in the graph**. Landing them means re-deriving `domain_mentions.jsonl` via
`scripts/build_domain_v2.py` and re-running the domain mention projection, which is a
shared layer with its own mark-and-sweep and five agents writing concurrently. I did not
run it rather than risk clobbering another agent's pass mid-flight. Expected delta, measured
from the probe and therefore exact: **+6 mantra-alias pairs, 4 additional passage-entity
edges, 4 entities crossing the two-Veda threshold, 44 → 48 of 66.** Verify with the
per-entity Veda count before accepting.

Entities **not** audited, for the record: the 6 rivers beyond `gaṅgā`/`yamunā` locatives,
the 5 tribes, the English-token pass on all entities, and the 4 remaining single-Veda
Yajurvedic actions (`AVABHRTHA`, `TRTIYA-SAVANA`, `AGNI-CITI`, plus `DRONAKALASA` /
`VAYAVYA` which are already two-Veda). The English river tokens are the largest known
remaining win and stay on the table.

---

## 8. Blocker: `hotṛ` cannot be typed `RITUAL_ROLE`, and the recorded change request is wrong

Verified the measurement: `VG:CONCEPT:HOTR-PRIEST` has **321 mentions across all four
Vedas** and labels `[Concept, DomainEntity]` only — no `RitualRole`. So
`REL_PERFORMED_BY (Ritual → RitualRole)` cannot reach the Rigveda's principal officiant, and
any query enumerating `RitualRole` returns the nine lesser offices without him. Confirmed
as a real misleading-answer shape.

The V3 close-out filed this as "one field on one existing line in
`data/registry/concepts.yaml` (`node_type: CONCEPT` → `RITUAL_ROLE`)". **That is not a
one-line change and I found out by making it.** `load_concepts()` validates
`concepts.yaml` against the frozen `SemanticNodeType` whitelist for every caller that does
not pass `allowed_node_types`, and that enum has no `RITUAL_ROLE`:

```
ConceptRegistryError: VG:CONCEPT:HOTR-PRIEST: node_type 'RITUAL_ROLE' is not an allowed
entity type. Allowed: ACTION, ANIMAL, CONCEPT, COSMIC_ENTITY, NATURAL_PHENOMENON, OBJECT,
OFFERING, PHILOSOPHICAL_CONCEPT, PLACE, PLANT, QUALITY, REGION, RITUAL, RIVER, STATE,
SUBSTANCE, THEME
```

Bare callers that would break: `src/vedagraph/enrich/build.py:104`,
`scripts/probe_domain_aliases.py:186`, `scripts/run_semantic_extraction.py:104`,
`tests/enrich/test_concepts.py:129`, `tests/domain/test_being_and_nonbeing.py:151`. So the
one-line change turns the whole V1 enrichment path and two test modules red. `concepts.yaml`
(the V1 registry) and the V2/V3 domain fragments carry **two incompatible `node_type`
vocabularies**, and `RITUAL_ROLE` exists only in the second — which is why `hotṛ` was left
`CONCEPT` in the first place.

I reverted both the file change and the live label rather than leave the graph
unreproducible from its artifacts, and left the diagnosis as a comment on the line itself.
Two candidate fixes, neither in my scope:

1. **Add `RITUAL_ROLE` to `SemanticNodeType`.** Smallest diff, but that enum is inside the
   V3.2 semantic seal and growing it is a seal decision, not a typing decision.
2. **Pass the V2 node-type set at the V1 call sites** (`enrich/build.py` and the three
   scripts), so `concepts.yaml` is validated once against the wider vocabulary it now
   has to hold. No seal change; touches a shared module and needs the V1 rebuild
   re-measured.

Option 2 is the better one. Until either lands, Q90 stays blocked, and the blocker is the
node-type vocabulary split rather than a missing label.

### The rest of the registry typing pass — measured, and 22 of 23 are correct as they are

Agent B estimated "roughly 60 nodes similarly untyped". **Measured: 23** `DomainEntity`
nodes carry only `[Concept, DomainEntity]`, 6,181 mentions between them. Of those, exactly
**one** is under-typed: `HOTR-PRIEST`. The other 22 are genuine abstractions and I did not
relabel any of them to raise a number:

`VASU-WEALTH` (885), `JANA-PEOPLE` (478), `SAKHYA-FRIENDSHIP` (439), `VAJA-PRIZE` (435),
`AVAS-HELP` (408), `RAJAN-KINGSHIP` (378), `PRAJA-OFFSPRING` (319), `AYUS-LIFE` (281),
`TANU-BODY` (278), `SARMAN-PROTECTION` (272), `SATRU-ENEMY` (242), `PITARAH-ANCESTORS`
(193), `VRATA-ORDINANCE` (189), `ADHVAN-PATH` (173), `VIRA-HERO` (165), `SAMAN-CHANT`
(126), `PRANA-BREATH` (113), `BHESAJA-HEALING` (108), `KAMA-DESIRE` (101), `MRTYU-DEATH`
(101), `HRD-HEART` (96), `ENAS-SIN` (80). None of them is a ritual role, a substance, an
object or a condition in the ontology's sense; `Concept` is the right label. If anything
here is worth revisiting it is `SATRU-ENEMY` and `KAMA-DESIRE` as `HumanConcern`, and that
is an ontology judgement rather than a correction of an error.

---

## 9. Defects found that were not already known

1. **The "one-line" `hotṛ` fix is not one line.** §8. `concepts.yaml` and the V2/V3 domain
   fragments carry incompatible `node_type` vocabularies and `RITUAL_ROLE` exists only in
   the latter, so the change request recorded in the V3 close-out raises
   `ConceptRegistryError` and reddens five call sites including two test modules.
2. **The Yajurveda's densest material-culture line was unreachable by construction.** §7.
   VSM 18.12 prints each grain joined to the following `ca`, so no pausa form can token-match
   and the substring pass is both length-blocked and Samaveda-only. Three crops read as
   Atharvaveda-only for that reason alone.
3. **A deity-registry intersection is not a personhood test.** §5. It called three human
   seers non-seers (17% wrong) and missed roughly 95 non-seers, because a seer being also
   named as the devatā of his own hymn is ordinary.
4. **`check_live_invariants.py` requires `evidence` on a family membership, not just
   `grade_basis`.** My first projection satisfied every grading property the rest of the
   graph carries and still failed the gate, because that check reads `m.evidence`
   specifically. Worth knowing before writing the next membership layer: the invariant is
   stricter than the convention.
5. **Agent B's "roughly 60 untyped nodes" is 23,** of which 22 are correctly typed. §8.
6. **`data/derived/**` is gitignored, so no artifact written there can satisfy the
   reproducibility rule.** This layer was first built into
   `data/derived/rishi_families_v1.json`, which `git status` silently ignores; the graph
   would have been rebuildable only on the machine that built it. Moved to
   `data/domain/vedagraph_domain_v2/rishi_families_v1.json`, which is tracked. Any other
   V3 layer whose builder writes under `data/derived/` has the same problem and it does not
   show up as a failure anywhere -- the build succeeds, the projection succeeds, and the
   artifact is simply not in the repository.
