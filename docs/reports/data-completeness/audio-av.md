# Atharvaveda audio — the gap was a hymn division, not an absence

**Agent 7, Wave 1. Artifact: `data/staging/audio_av/`. Validator: PASS with `--graph`.**

| | |
|---|--:|
| AV Śaunaka mantras | 5,839 |
| Catalogued before this artifact | 4,680 (80.1%) |
| Gap assessed — every one of it | 1,159 |
| **Accepted** | **771** (66.5% of the gap) |
| — importable now (`EXACT`) | 764 |
| — staged, not importable (`PROBABLE`) | 7 |
| Unresolved, with a named open route | 197 |
| Rejected as a typed negative, with a proof record | 191 |
| AV audio after importing the 764 `EXACT` rows | **5,444 of 5,839 = 93.2%** |

No canonical write occurred. Every Cypher statement run was a `MATCH`/`RETURN`.

## 1. The 495 `text_mismatch` — the diagnosis

**It is systematic, it is structural, and it is ours. 494 of the 495 are one thing: the
source divides the Atharvaveda into more hymns than we do.**

Our corpus follows the Berlin (Roth & Whitney 1856) hymn division — 731 sūktas. VedSearch
follows a division with **754**. The 23-sūkta difference is not spread about; it sits in
exactly five kāṇḍas, and it is an arithmetic fact that needs no text matching to establish:

| kāṇḍa | our sūktas | source sūktas | Δ | what the source splits |
|---:|--:|--:|--:|---|
| 7 | 118 | 123 | +5 | six of our hymns split in two, less our 7.59 which it lacks entirely |
| 9 | 10 | 15 | +5 | our 62-verse paryāya 9.6 becomes source 9.6–9.11 |
| 11 | 10 | 12 | +2 | our 56-verse paryāya 11.3 becomes source 11.3–11.5 |
| 12 | 5 | 11 | +6 | our 73-verse paryāya 12.5 becomes source 12.5–12.11 |
| 13 | 4 | 9 | +5 | our 55-verse paryāya 13.4 becomes source 13.4, 13.6–13.9 |
| | **731** | **754** | **+23** | |

`vedsearch_coordinates()` maps an AV key straight through — kāṇḍa, sūkta and mantra
unchanged. Past the first split in a kāṇḍa that is the wrong verse, and the text check
correctly refused it. The refusals were right; the coordinate was wrong.

The offset is cumulative within a kāṇḍa, which is why no single constant shift describes it.
In kāṇḍa 7 the source divides six of our hymns in two — our 7.6, 7.45, 7.54, 7.68, 7.72 and
7.76 — while our 7.59 has no counterpart in the source at all, so six splits net to +5: it
runs +1 ahead of us from our 7.7 and +5 ahead at our 7.118, which it numbers 7.123.

In the paryāya books the source also **restarts verse numbering at 1 in each piece**, so a
verse offset appears alongside the sūkta offset: in kāṇḍa 12 it takes the values +6, +11,
+27, +38, +46 and +61, and +61 is the largest anywhere in the AV. The full per-sūkta
correspondence is recorded in
`manifest.json → hymn_division_correspondence` and named per row in `mapping_method`.

### How each row was re-established

Not by applying the offset table. The offset table is the *result*; each row was
established independently and the table was read off it afterwards.

| pass | rule | rows |
|---|---|--:|
| 1 | the source verse reciting **letter-identical** text is unique in all 5,916 rows, unclaimed, and audio-bearing | 607 |
| 2 | more than one letter-identical candidate; exactly one falls inside the source-order window fixed by the mantra's nearest mapped neighbours | 9 |
| 3 | an orthographic variant ≥ 0.90 beating its runner-up by 0.05, in the same kāṇḍa, **immediately adjacent in source order to a letter-identical anchor** of the same hymn | 109 |

The structural corroboration is what makes these mappings rather than resemblances. Over
the combined alignment of **5,405** mapped mantras — the incumbent 4,680 plus my 725 — there
are exactly **three** source-order inversions, and all three are explained:

- **`K19:S036:V001` / `V002`** — the source transposes the first two verses of 19.36. Both
  are letter-identical, so the pairing is not in doubt. A naive coordinate map attaches each
  to the other; this artifact fixes that. It is the clearest single proof that the text check
  was earning its keep.
- **`K11:S003:V049` / `V050`** — inside source 11.5 the paryāya's own order differs: source
  11.5.1–6 is our 11.3.50–55 and source 11.5.7–18 is our 11.3.38–49. Every one of the
  eighteen is letter-identical, and each names a different body part, so no pairing is
  ambiguous.
- **`K07:S061:V001`** — **the source repeats itself.** Source 7.61.1 and source 7.63.1 are
  letter-identical to each other and to our 7.61.1, so our single mantra has two equally
  valid source occurrences. The incumbent attached the earlier one; the corrected alignment
  puts our 7.61 wholly at source 7.63, which would leave 7.61 free. Either way the recitation
  is the right mantra, so this is an ordering artifact rather than a wrong attachment, and
  source 7.63.1 is simply left unclaimed. Not touched.

## 2. The comparator defects, measured on the Atharvaveda

The coordinator asked me to test Agent 6's two `vedsearch.py` defects before acquiring
anything, and to treat "this probably explains the AV's 495" as a prediction. **It does not
hold for the AV, and the measurement says why.**

Both defects are real. Neither is load-bearing here.

| | measured on the AV |
|---|---|
| AV mantra skeleton length | median **80**, p95 122, max 579 |
| AV mantras above difflib's 200-element autojunk trigger | **30 of 5,839 = 0.5%** |
| autojunk effect, variant aligned pairs **at or below** the trigger (n=1,286) | median Δ **0.0000**, max Δ 0.0093 |
| autojunk effect, variant aligned pairs **above** the trigger (n=8) | median Δ **0.1423**, max Δ 0.2182 |
| AV stored `PRIMARY_TEXT` rows containing an ASCII colon | **0 of 5,839** |
| VedSearch AV source rows containing an ASCII colon | 11 of 5,916 |
| coordinate-aligned pairs passing at 0.90, before → after | **4,680 → 4,681** |
| regressions (passed before, fails after) | **0** |
| **verses the two defects actually cost the Atharvaveda** | **1** |

The single verse is `VG:AV:SAU:K19:S009:V014`, which scored 0.8798 broken and **0.9142**
corrected, at its own unshifted coordinate 19.9.14. It is accepted here at `EXACT`, because
its coordinate is established independently by the transform and the text merely confirms it.

**Why the YV and the AV diverge is the length gate.** `autojunk` only engages above 200
elements. The Yajurveda's verses were extracted from adhyāya containers and run long; the
Atharvaveda's are mostly metrical and run 80 characters. Below the trigger the heuristic does
nothing at all, which is why the median delta over 1,286 pairs is exactly zero. Above the
trigger the effect is large and matches Agent 6's finding — but all eight such AV pairs still
land between 0.10 and 0.38 even corrected, because the coordinate genuinely holds a different
prose unit. **Fixing the comparator does not find them; only the hymn-division correction does.**

AV-specific recalibration, so the AV inherits no one else's numbers:

| population | n | p5 | median | max | ≥ 0.90 |
|---|--:|--:|--:|--:|--:|
| coordinate-aligned, all | 5,175 | 0.2995 | 1.0000 | 1.0000 | 4,681 |
| coordinate-aligned, variant path only | 1,286 | 0.1872 | 0.9859 | 0.9972 | — |
| mispaired, random same-recension | 1,000 | 0.1353 | 0.2637 | **0.4859** | **0** |

The AV's mispaired maximum of 0.4859 is far below the module's newly recorded all-Veda
maximum of 0.8413. That headroom is Atharvavedic and must not be generalised: the module's
worst wrong pair is two adjacent formulaic Yajurvedic verses, and the AV's paryāya refrains
are the same hazard. I did not lower the threshold anywhere.

The lead repaired `src/vedagraph/product/audio/vedsearch.py` while this artifact was being
generated, and has since committed it. The artifact was first produced against a local correction; that correction
was then verified to produce **byte-identical skeletons over all 21,752 relevant texts**
(5,839 canonical, 5,916 source, 9,997 Vedavani) and identical similarity over 400 random
pairs, the generator was repointed at the repaired module, and the whole chain was re-run to
**identical output**. Nothing in `src/` was modified by me.

## 3. The full 1,159, by the reason the original run recorded

| original reason | total | accepted | unresolved | rejected |
|---|--:|--:|--:|--:|
| `text_mismatch` | 495 | **356** | 51 | 88 |
| `no_source_verse` | 420 | **385** | 10 | 25 |
| `source_has_no_audio` | 244 | **30** | 136 | 78 |
| | **1,159** | **771** | **197** | **191** |

`no_source_verse` turned out to be the *same* defect as `text_mismatch`, not a different one.
Both are the hymn division: where the source's sūkta has fewer verses than ours, our verse
number falls off the end and the row reports "absent"; where it has a different verse there,
it reports "mismatch". 385 of the 420 closed. That is the largest single block in this
artifact and nobody had predicted it — the 420 were carried in the registry as needing
"another source".

`source_has_no_audio` is the one that really is the source's limit. 232 of the 244 are in
kāṇḍa 6, where VedSearch holds 452 verses of text and only 220 with audio. **Re-probed live
on 2026-09-15: 14 of 14 sampled verses returned no audio payload from the endpoint, so the
harvested flag is not stale.** 30 of the 244 closed, 29 of them from Vedavani.

Final dispositions across the residual 388:

| | rejected | unresolved |
|---|--:|--:|
| `TEXT_ABSENT_FROM_SOURCE_EDITION` | 121 | 65 |
| `SOURCE_HAS_TEXT_BUT_NO_AUDIO` | 52 | 122 |
| `NO_VERSE_LEVEL_MATCH_IN_SOURCE` | 16 | 7 |
| `ONLY_AUDIO_OCCURRENCE_CLAIMED_BY_ANOTHER_VERSE` | 2 | 2 |
| `AMBIGUOUS_REPEATED_TEXT` | — | 1 |

`TEXT_ABSENT_FROM_SOURCE_EDITION` concentrates in the prose books, and for a reason that is
not an absence of material but a difference of segmentation. Kāṇḍa 15 is 141 units for us and
**219** for the source; kāṇḍa 16 is 93 against 103; kāṇḍa 8 is 259 against 242. A source unit
there is a different span of prose from ours, so no 1:1 mantra correspondence exists to find.
This is the one part of the AV audio gap that is genuinely not closable at `MANTRA` scope by
re-mapping, and 70 of the 191 rejections sit in those two books.

## 4. Acquisition — Vedavani, and what it can and cannot do

**Vedavani** (`huggingface.co/datasets/sanganaka/Vedavani-Dataset`, Apache-2.0, ACL 2025,
arXiv:2506.00145) is the one mirrorable AVŚ audio corpus, and reconnaissance's summary of it
needs two corrections.

- It does **not** cover only kāṇḍas 1–13. Its Atharvavedic filenames are
  `Atharvaveda_Kanda_{1..13}_NNNN.wav` and `Atharvaveda_Part_{014..020}_NNNN.wav`, and the
  "Part" numbers are the remaining **kāṇḍas 14–20**. All twenty are present: 9,997 samples,
  17.77 h.
- It is **not** keyless. The filename carries a kāṇḍa and a running index, and the CSVs carry
  a Devanagari transcript per file. That is not a key, but it is two independent structural
  claims to check a text match against.

Its real limit is granularity: median sample 5.77 s, 9,997 samples for 5,839 mantras. Only
**773 transcripts (7.7%) are letter-identical to a whole mantra**; the rest are hemistichs.

**46 rows accepted**, all at `EXACT`, each having passed seven conditions together:

1. the transcript is letter-identical to our Śaunaka `PRIMARY_TEXT` for that mantra;
2. the sample is filed under that mantra's own kāṇḍa (753 of the **766 distinct mantras** with a whole-mantra
   transcript agree on this, so the filename is a real signal and not noise);
3. its running index falls between the indices of the mantra's nearest letter-identical
   neighbours in the same kāṇḍa — the dataset's own ordering must agree with the text match;
4. it is the only sample in that window reciting the text;
5. its seconds-per-syllable lies inside the corpus's 1st–99th percentile band [0.2457,
   0.4969], which is the guard against a transcript sitting on the wrong audio;
6. the file exists in the repository listing;
7. no other mantra's mapping claims the same file.

**16 candidates were refused by condition 3 alone** — letter-identical transcript, right
kāṇḍa, index out of order. Those stayed unmapped. That is the guard doing its job on
repeated paryāya refrains.

The boundary is the **file** boundary: one standalone WAV containing exactly that mantra. No
timestamp is asserted anywhere in this artifact, so no row is a `VERIFIED_SEGMENT` and none
needed to be. **No ASR was run by me** — the transcript is the dataset's published metadata.

### Recension: Śaunaka, established by text because nobody states it

Neither source names a recension. Both are established textually, per row and at corpus level.

| | VedSearch | Vedavani |
|---|---|---|
| publisher's recension claim | none | none |
| per-row evidence | the text the source publishes beside the audio is letter-identical to our Śaunaka `PRIMARY_TEXT` (0.9091–1.0 for the seven variants) | the published transcript is letter-identical to our Śaunaka `PRIMARY_TEXT` |
| corpus evidence | 20 kāṇḍas, 754 sūktas, a **143-sūkta kāṇḍa 20** — the Śaunaka Kuntāpa book, which Paippalāda has in no such shape; 5,405 of our 5,839 matched — 4,505 by letter identity, 900 as orthographic variants | **9,034 of 9,997** transcripts are exact letter-**substrings** of the Śaunaka saṃhitā, and 773 are letter-identical to a whole Śaunaka mantra across all 20 kāṇḍas |

A Paippalāda corpus cannot reach letter-exact containment at 90.4%; the recensions differ in
wording, not only in order. All matching used `PRIMARY_TEXT`. `SEARCH_DERIVATIVE` was never
read — it is the layer that stores `kr̥dhi` as `kdhi`, and it would have failed silently on
every vocalic ṛ.

## 5. The recension trap — every Paippalāda candidate, and what identified it

**`archive.org/details/paippalAda-shAkhA` — 54 audio files, 90.59 h. Rejected.**

It is the **largest** Atharvavedic audio item on the Internet Archive — larger than its own
Śaunaka companion at 38.94 h — so anything ranking by size or duration walks straight into
it. Two things identify it, and only the first is obvious:

1. its title and description say `अथर्ववेदः Atharvaveda पैप्पलाद-शाखा paippalAda-shAkhA`
   outright;
2. its filenames use vedamu's `{id}$name` scheme (`421$Kanda1.mp3`) — the same fingerprint
   reconnaissance flagged on `sAmavedaH-kauThuma-shAkhA` — so it is *also* an unauthorised
   mirror of a reference-only source, and would have been refused on rights even if the
   recension had been right.

That is the only Paippalāda audio candidate found in this wave. It is not mapped anywhere,
and no unlabelled Paippalāda material entered the artifact: every accepted row's recension
rests on letter identity with our Śaunaka text, which Paippalāda would fail.

The companion item `Atharvaveda-shaunaka-shAkhA` is the mirror-image trap: **correct**
recension on its own title, same uploader, same vedamu `{id}$name` scheme, and rejected
anyway — 22 files for 5,839 mantras, no cue index, no printed timestamps, and an
unauthorised mirror of a source whose operator states it is open to listen and not to
download. A correct recension label is not a mapping.

## 6. Source families rejected, and why

Enumerated: **48** Internet Archive audio items matching `atharva*`, nine probed file by
file; **80** Wikimedia Commons audio results for "Atharvaveda" and 68 for "atharva veda
recitation". Full records in `sources.jsonl`.

| candidate | what it is | why refused |
|---|---|---|
| `IISH_Atharva_Veda` | 28 files, 19.20 h, courtesy `iish.org`, Dr N. Gopalakrishnan | per-part monolithic, no cue index, no per-mantra boundary |
| `atharvaveda_202107` | 28 files, 19.20 h, CC0 Public Domain Mark, credited "Veda Prasara Samithi" | **the same master.** Its 28 durations are identical to IISH's (2410.4, 2686.6, 2535.8, 2672.1 …). The Public Domain Mark is applied by a third-party uploader over a *differently attributed* creator, so the licence statement is not a rights clearance. Monolithic in any case |
| `atharvaved-tune` | 21 files, 18.64 h, one per kāṇḍa | no licence, no reciter, no boundaries. A kāṇḍa is not a mantra |
| `AtharvaVeda1-40` + 41-90, 91-150, 151-189 | 189 tracks of ~10 min | no licence, no creator, and no index saying which mantras a track holds |
| `AtharvaVedam` | 44 files, 59.58 h, "Kandam 01"–"**Kandam 21**" | one more than the twenty kāṇḍas the Śaunaka saṃhitā has, unexplained; no licence, per-kāṇḍa |
| `atharvaveda1` / `atharvaveda2` | 20 files of ~46 min | no licence, no reciter, ~300 mantras per file |
| Wikimedia Commons | 80 audio hits for "Atharvaveda" | **verified absent.** Every hit is Samavedic gāna, Rigvedic śastra, or a dictionary pronunciation of the word "Veda" |
| Vedic Heritage / IGNCA | Śaunaka Saṃhitā portal | `PERMISSION_REQUIRED`, no credited reciter, so no resolvable consent chain; route already withdrawn by prior decision, not re-probed |

**Not per-mantra anywhere.** Outside VedSearch and Vedavani, the finest Śaunaka granularity in
public is one file per kāṇḍa, and no item publishes a printed timestamp, a cue index or a
chapter index. That is the load-bearing negative behind the 191 proof records.

One observation I can support but not prove: Vedavani names no source for its recordings, and
its 17.77 h of Atharvavedic audio against the IISH master's 18.71 h of saṃhitā-pāṭha (19.20 h
less a 29-minute spoken introduction) is consistent with a segmentation of it. The
`Atharvaveda_Part_0NN` naming is suggestive of the IISH copy's own "Atharvaveda Part 0NN.mp3"
part scheme. **Consistent is not the same as demonstrated**, and I did not compare waveforms.
Recorded so it is not rediscovered as a new lead.

## 7. The 197 unresolved — a route, not a refusal

These are **not** typed absences and must not be counted as any. For each of the 197, a
public recording of the mantra demonstrably exists: a **contiguous run of Vedavani samples**
whose concatenated transcripts are letter-identical to the whole mantra.

| files per mantra | mantras |
|---:|--:|
| 1 | 16 |
| 2 | 157 |
| 3 | 24 |

They sit in kāṇḍas 6 (129), 15 (24), 13 (18), 4 (8), 9 (7), 8 (5), and singly elsewhere. What
blocks them is this artifact's record model, which carries **one `media_url` per mantra**;
attaching one file of a two-file mantra would present a hemistich as the mantra, which the
campaign forbids. `open_route: STITCH_CONSECUTIVE_VEDAVANI_SAMPLES` on every row.

The 16 single-file cases are the ones Vedavani's own ordering contradicted — letter-identical
transcript and right kāṇḍa, but a running index outside the monotone window. Those are a
verification queue, not a defect.

Closing the 197 needs a decision I do not own: either a mantra-scoped record that carries an
ordered list of files, or a concatenation step with its own provenance. It would take AV audio
from 93.2% to **96.6%**.

## 8. The 191 typed negatives

Each has a per-mantra proof record in `proofs/no_public_recording.jsonl` naming **five**
independent avenues with the exact query run, the result, the traditions checked (Śaunaka
accepted, Paippalāda explicitly refused), the nearest available recording, and why mapping it
was rejected. They sit in kāṇḍa 6 (75), 15 (42), 16 (28), 8 (16), 9 (9), 13 (7), and singly
elsewhere.

Two thirds of them are a segmentation mismatch rather than a missing recording: in kāṇḍas 15
and 16 the recorded prose is almost certainly *in* one of the public files, but as a span whose
boundaries no source states and which our unit does not match. Saying "no recording exists" of
those would be wrong, and the proof records say instead that no recording is **attachable at
`MANTRA` scope with verified boundaries**, which is what I actually established.

`verified_zero` is **0** in the manifest. The 191 are the typed-absence population and are
counted once, as `rejected`; writing them into both fields would double-report one population.

## 9. QA

`sampled: 81`, `defects_found: 0`, `human_reviewed: 0`.

Adversarially stratified, not uniform: **all 7** `PROBABLE` rows plus a per-kāṇḍa quota drawn
from every kāṇḍa whose hymn division was corrected — 7 (8), 9 (8), 12 (7), 11 (6), 13 (6), 8
(4), 15 (3), 19 (3), 16 (2) — because a wrong-verse error would hide precisely there.

- **47 accepted VedSearch rows**: audio fetched and decoded; all 47 are real MP3; all 47
  report `granth_name: atharved`. Then an **independent** text check — the audio attachment
  document carries its own `audio_text` field, a different channel from the chapter-search
  `shlok` field the mapping was built on. 36 letter-identical, 3 orthographic variants, 8
  above threshold and below the 0.973 floor, **0 mismatches**, minimum 0.9091.
- **20 accepted Vedavani rows**: fetched, all real RIFF/WAVE, decoded duration agrees with
  the CSV metadata to within 0.02 s on all 20.
- **14 rejected rows** re-probed live at the coordinate the rejection *names*: 14 of 14
  confirmed no audio payload.

**0 rows were reviewed by listening.** Every check above is mechanical. For a mapping whose
whole claim is "this recording is this mantra", that is the residual risk and it is not small:
the evidence is that the *source states* this file recites this text, checked against two
independent statements for VedSearch and one for Vedavani, plus a duration-versus-syllable
plausibility band for Vedavani. It is not the evidence of a human hearing it.

One QA defect surfaced and was in the probe, not the artifact — worth recording because of
what it was. The rejected-row re-probe first built its coordinate from the canonical key, the
very naive mapping this artifact exists to correct, and reported `K07:S041:V001` as "rejected
but audio fetched". Source 7.41.1 does have audio; it recites a different verse, as its own
`audio_text` confirms. The letter-identical text is at source 7.42.1, which has none. The
rejection was right. **The offset is easy to walk back into even while fixing it.**

## 10. Outside my write surface, for the lead

Found in passing, verified, not touched:

1. **`GAP-AUDIO-002`'s prescription is wrong.** The registry records the 495 as "a matcher
   problem" with the remedy "re-run the 495-verse refusal set with accent- and
   sandhi-insensitive matching". The matcher was already accent- and sandhi-insensitive —
   `skeleton()` strips every combining mark — and re-running it changes 1 of the 495. The
   remedy was the hymn division. The gap's `source_dependency` ("the 420 verses absent from
   vedsearch.org need another source") is also wrong: 385 of the 420 were in VedSearch all
   along, at a different coordinate.
2. **The source repeats a verse, and the incumbent picked the earlier copy.** Source 7.61.1
   and 7.63.1 are letter-identical to each other and to our `K07:S061:V001`. The incumbent
   holds the first, the corrected alignment wants the second, and either recites the right
   mantra — so this is the one source-order inversion in 4,680 that is not a defect. Source
   7.63.1 is left unclaimed. Recorded so it is not mistaken for one later.
3. **Two text-layer defects, both of which this artifact pays for in unmapped verses.** 77 AV
   `PRIMARY_TEXT` rows carry a bracket. 68 end in a bare `[n]` and four more in `[n] {m}` or
   `[n-m]`, all of which are legitimate paryāya and anuvāka sub-numbering. The remaining five
   are not:
   - `VG:AV:SAU:K11:S003:V018` stores editorial apparatus —
     `carúṃ páñcabilam ukháṃ gharmò 'bhī̀ndhe ||18|| [note CORRIGENDA ed. ŚPP]`. It is why
     that mantra matches nothing anywhere.
   - `VG:AV:SAU:K16:S005:V002` to `V005` store a literal `[...]` **in place of the repeated
     text** — `vidmá te svapna janítraṃ nírbhūtyāḥ putró 'si [...] || 4 ||`. This is
     consistent with the transcription policy in
     `ATHARVAVEDA_STRUCTURE_RECONCILIATION.md`, which keeps the print's `॰` abbreviation and
     never expands it, so it is not a transcription error. But it means those four mantras
     cannot be matched at full length against anything, and the cost is exact: V002 is one of
     the seven `PROBABLE` rows at 0.9293, and V003, V004 and V005 are three of the 191
     rejections. Expanding the abbreviation in a derived layer — never in `PRIMARY_TEXT` —
     would close three verses and promote a fourth, and it is the cheapest unlock left in
     this domain.
4. **Three AV sūktas have a hole in their verse numbering**: 9.6 has 61 mantras with 49
   missing and a highest of 62; 12.5 has 72 with 1 missing and a highest of 73; 13.4 has 55
   with 1 missing and a highest of 56. So the corpus's own numbering implies 5,842 where it
   holds 5,839. `ATHARVAVEDA_STRUCTURE_RECONCILIATION.md` states plainly that the mantra total
   is *not* derivable from the 1856 print's running heads, so this is exactly the kind of
   carried-over figure it warns about — three verses, each individually checkable against the
   print.
5. **AVŚ `patha_type` other than `SAMHITA` remains unfillable.** Nothing in this wave changed
   the standing negative on pada-, krama-, jaṭā- and ghana-pāṭha.

## 11. Reproducing this

```
.venv/Scripts/python.exe scripts/validate_staging_artifact.py data/staging/audio_av --graph
```

PASS: 15 checks, every one at 100% coverage, 0 defects. `candidates_considered` 1,159 =
771 accepted + 191 rejected + 197 unresolved.

`manifest.json` carries the assessed population explicitly — 1,159 examined of a 1,159 gap,
coverage 1.0 — the full `hymn_division_correspondence` table, the `comparator_correction`
measurements, and the QA detail. `rows.jsonl` names the corrected offset in every row's
`mapping_method`; `rejected.jsonl` and `unresolved.jsonl` name the candidate that was declined
and why.
