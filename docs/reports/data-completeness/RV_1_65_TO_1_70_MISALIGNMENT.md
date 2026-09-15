# RV 1.65–1.70: twenty-five translations are attached to the wrong verse

**This is not a gap. It is wrong data, shipped in Product V1 and served to users today.**

Found by Agent 3 while working the translation gap, and confirmed here by reading the
Sanskrit against the English on the live graph rather than by inspecting the pipeline that
produced it.

## What is wrong

Griffith's edition prints these six hymns with **half as many verses as our Śākala spine
holds**, because he renders each pair of our verses as one unit. His unit *N* therefore
corresponds to our verse *2N − 1*.

The import bound his units onto our verses one-for-one: unit 1 → verse 1, unit 2 → verse 2,
and so on. So every unit after the first landed one or more places too early.

RV 1.65, read off the live graph. The right-hand column is where each translation actually
belongs:

| Our verse | Sanskrit opens | Translation attached | Belongs to |
|---|---|---|---|
| 1.65.1 | `paśvā na tāyuṁ guhā catantaṁ` | "ONE-MINDED, wise, they tracked thee like a thief…" | **1.65.1 — correct** |
| 1.65.2 | `sajoṣā dhīrāḥ padair anu gmann` | "The Gods approached the ways of holy Law…" | 1.65.3 |
| 1.65.3 | `ṛtasya devā anu vratā gur` | "Like grateful food, like some wide dwelling place…" | 1.65.5 |
| 1.65.4 | `vardhantīm āpaḥ panvā suśiśvim` | "Kin as a brother to his sister floods…" | 1.65.7 |
| 1.65.5 | `puṣṭir na raṇvā kṣitir na pṛthvī` | "Like a swan sitting in the floods he pants…" | 1.65.9 |
| 1.65.6–1.65.10 | — | none | — |

The alignment is checkable by eye: "The Gods approached the ways of holy Law" is
`ṛtasya devā anu vratā gur`, which is our verse 3, and it is attached to our verse 2.

RV 1.66 shows the identical pattern. Our verse 2 carries the translation of
`dādhāra kṣemam oko na raṇvo yavo` (verse 3); our verse 5 carries that of
`taṁ vaś carāthā vayaṁ vasatyāstaṁ` (verse 9).

## Blast radius, measured

| Hymn | Our verses | Translated rows | Correct | Misattached |
|---|---|---|---|---|
| RV 1.65 | 10 | 5 | 1 | 4 |
| RV 1.66 | 10 | 5 | 1 | 4 |
| RV 1.67 | 10 | 5 | 1 | 4 |
| RV 1.68 | 10 | 5 | 1 | 4 |
| RV 1.69 | 10 | 5 | 1 | 4 |
| RV 1.70 | 11 | 6 | 1 | 5 |
| **Total** | **61** | **31** | **6** | **25** |

Only the first verse of each hymn is right, and it is right by coincidence — it is the one
position where *N* and *2N − 1* agree.

## It is confined to these six hymns

The signature is a hymn whose translated count is about half its verse count. Scanning
every Rigvedic hymn with partial translation coverage returns fifteen, and only these six
show it:

| Hymn | Verses | Translated |
|---|---|---|
| RV 1.65–1.70 | 10–11 | 5–6 — **the defect** |
| RV 10.61 | 27 | 22 |
| RV 10.86 | 23 | 21 |
| RV 1.53, 1.73, 5.55, 8.93, 9.7, 10.48, 10.132 | 7–34 | one short each |

RV 10.61 was spot-checked against its Sanskrit and is correctly aligned — verse 1's
`idam itthā raudraṁ gūrtavacā` carries "THE welcome speaker in the storm of battle", verse
2's Cyavana verse carries Griffith's Cyavana rendering. Its five absences are genuinely
missing verses, a different cause with the same surface appearance.

## Why nothing caught it

Three separate safeguards were each satisfied:

1. **The totals balance.** 31 units in, 31 rows out. No row was lost, so no count check
   could see it.
2. **Every row resolves.** All 31 canonical keys exist and are Rigvedic, so the staging
   validator's graph checks pass — as they should; the keys are real, they are just the
   wrong ones.
3. **Coverage looks like a gap, not a defect.** The 30 untranslated verses present exactly
   as "30 of the Rigveda's 50 missing translations", which is how they were recorded in this
   campaign's own baseline. The missing verses were the *visible symptom* of the
   misalignment, and reading them as a gap hid the defect behind them.

The deeper lesson is the one this project keeps relearning: a figure can be right while its
meaning is wrong. "RV translations: 10,502 of 10,552" is arithmetically exact, and 25 of
those 10,502 are translations of a different verse.

## What must not be done about it

Do not import the 30 missing verses on top of this. Adding the absent translations while
the present ones are shifted would fill the hymn and make the defect invisible: every verse
would carry text, and 25 would still carry the wrong text. The realignment must come first.

## What has to happen

1. Re-align the 25 misattached rows to *2N − 1*, verse by verse, with per-verse Sanskrit
   verification rather than by applying the formula blindly — RV 1.70's 11 verses against 6
   units show the mapping is not uniformly a doubling.
2. Then import the absent translations for the even-numbered verses.
3. Add an invariant that fails when a hymn's translated count is a near-half of its verse
   count, so the next edition with merged verses is caught at import rather than by a reader.
4. Check the other three Vedas for the same edition property. Agent 3 found declared
   `merged_verses_undeclared` defects in its QA sample (3 of them), so merged verses are not
   unique to these six hymns — only this instance of the binding error has been measured.

Agent 3 rejected these rows rather than staging them, because re-aligning already-imported
data is outside a specialist's write surface. That was the right call, and it is why the
defect is recorded here for the lead instead of being quietly fixed inside a staging file.

## Registry

Recorded as `GAP-TRANSLATION-006`, classification `IMPLEMENTATION_GAP`, owner lead. Its
closure test is that every one of the 31 rows reads against its own Sanskrit, not that the
hymn is full.
