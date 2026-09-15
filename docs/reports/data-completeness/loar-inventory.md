# LOAR *Veda-recitationer* — inventory, no coverage claimed

Owner decision D. Artifact: `data/staging/loar_samaveda/inventory.jsonl`, 22 items.

Royal Danish Library, collection handle `1902/8015`, uuid
`57bd2a3c-22c3-48ce-b9e5-ac536a89bc3d`, enumerated live through the DSpace 7 REST API on
2026-09-15. Collected by Guni Hesting Kirchheiner (d. 2007), Danish indologist.

**527 files, 283,577,847,220 bytes (283.6 GB). Not one byte fetched.** This is an
inventory. Nothing is attached to any canonical key, and `candidate_canonical_work` is a
candidate, never a mapping.

## The verdict on the Samaveda: it does not close the gap

**Zero of the 22 items is an ārcika recitation of the Kauthuma śākhā.** The nine Samavedic
items are gāna, or they are Jaiminīya, or both:

| Item | Recension | Genre | Files |
|---|---|---|--:|
| Gramageya - Aindram - Aindrapathah | Jaiminīya probable | GRĀMAGEYAGĀNA | 7 |
| Gramageya - Agneyam | Jaiminīya probable | GRĀMAGEYAGĀNA | 17 |
| Gramageya - Chandah Pavamanam | Jaiminīya probable | GRĀMAGEYAGĀNA | 18 |
| Gramageya - Aindram Tadvapathah | Jaiminīya probable | GRĀMAGEYAGĀNA | 23 |
| Gramageya - Aindram Bṛhatīpāṭhaḥ | Jaiminīya probable | GRĀMAGEYAGĀNA | 8 |
| Gramageya - Aindram - Asavipathah | Jaiminīya probable | GRĀMAGEYAGĀNA | 5 |
| Aranyakagana | Jaiminīya probable | ĀRAṆYAKAGEYAGĀNA | 28 |
| Samaveda - Uhaganam and Uhyaganam (Usani) | Jaiminīya probable | ŪHAGĀNA + ŪHYAGĀNA | 23 |
| Samaveda - Nambudiri Jaiminiya | **Jaiminīya stated** | OTHER_SAMAVEDIC | 94 |
| Samaveda - Nambudiri Jaiminiya Ārcika | **Jaiminīya stated** | OTHER_SAMAVEDIC | 45 |

The last row is the one that would tempt a wrong claim. It **is** an ārcika — and it is the
**Jaiminīya** ārcika, not the Kauthuma ārcika this product holds. Merging them is forbidden
outright, and the temptation is exactly why the prohibition exists: an item titled
"Ārcika", from a named reciter, in an open-licensed institutional deposit, that is still
not our text.

Recension is marked *probable* rather than verified for the six Grāmageya items and the two
Ūha/Ūhya items. The evidence is contextual and stated as such: the reciters are Nambūdiri,
the Kerala community that preserves the Jaiminīya Sāmaveda, and two sibling items in the
same collection say "Jaiminiya" in their titles. That is good evidence of recension and it
is not a source statement at item level.

**So Wave 0's Samavedic conclusion stands, and its stated reason is withdrawn.** Wave 0
partly rested the gap on every candidate having an unnamed reciter. This deposit names its
reciters, so that reasoning is wrong. The gap survives for a better reason: the Samavedic
material here is a different recension, a different genre, or both.

What the deposit *does* offer the Samaveda is a genuine, openly-licensed, attributed **gāna
performance** corpus — 265 files across seven gāna items. That belongs to the gāna Works,
kept separate from the Ārcika, and is a real lead for that layer rather than for verse audio.

## Two findings outside the Samaveda that change Wave 1 conclusions

### Mādhyandina audio exists under an open licence

**"Sukla Yajurveda - Madhyandina Samhita", V. L. Bhate, 27 files, 11.1 GB.** Mādhyandina is
stated in the title. That is our recension.

Wave 1 left 190 Yajurvedic verses `BLOCKED_RIGHTS_AND_GRANULARITY`, the rights half resting
on IGNCA's material being permission-required. **The rights half does not apply here:** all
22 items in this deposit are CC0 1.0 (3 items) or CC Public Domain Mark (19 items).

The granularity half holds, and the filenames say why. The scheme is
`Veda-<cassette>_<start>-<end>-<sub>.wav`, where the numbers are a **range**:
`Veda-155_001-005-000a` covers adhyāyas 1–5; `Veda-157_006-007-000` covers 6–7 in a single
316 MB file. So 27 files span 40 adhyāyas in multi-chapter blocks of roughly an hour each,
with no cue index. Attaching a verse still requires segmenting an hour of audio with
verified boundaries.

That is a materially better position than before — open rights, a stated recension, and
coordinate *ranges* that give verified outer bounds — and it is not coverage.

### Śaunaka Atharvaveda audio, roughly one kāṇḍa per file

**"Atharvaveda - Saunaka Samhita", Vasudevshastri Pancholi, 41 files, 22.1 GB.** Śaunaka is
stated in the title, and it is our recension.

Filenames resolve finer here: `Veda-186_001-000-000` is kāṇḍa 1, and kāṇḍa 4 splits across
`Veda-189` and `Veda-190`. So 41 files for 20 kāṇḍas, about one kāṇḍa per file. Still far
coarser than a verse, but the coordinate is unambiguous at kāṇḍa scope.

This is a live route for the Atharvavedic residual Wave 1 left open — 197 reachable-but-blocked
plus 191 typed negatives, of which two thirds are kāṇḍa 15/16 prose re-segmentation.

## Correctly rejected, and why

| Item | Reason |
|---|---|
| Krsna Yajurveda - Tattiriya Samhita (46 files) | Taittirīya. Forbidden as a Mādhyandina substitute. |
| Tittiriya Brahmana (32), Tittiriya Aranyaka (11) | Taittirīya ritual prose, not Saṃhitā. |
| Sukla Yajurveda - Kanva Samhita (14) | Kāṇva is a different Śukla recension from Mādhyandina. |
| Aitareya Brahmana (15), Aitareya Aranyaka (5) | Rigvedic ritual prose — supplementary, not core. |
| Rgveda Samhita (Kinjawadekar) | Already the accepted Rigvedic source, via VedaWeb's segmentation of this same master. |

The Kāṇva item is worth dwelling on: it is titled "Sukla Yajurveda", which is correct and
insufficient. Mādhyandina and Kāṇva are both Śukla. A filter on "Śukla" admits the wrong
text, which is the same trap Wave 1 already met in the 37.51-hour Archive item whose
publisher's own table reads Kāṇva.

## Two unread documents that would settle the open questions

- **"Veda Recitation - Catalogue", Shrikant Bahulkar, 1 file.**
- **"The Veda Collection - Catalogue. CD cover.", 1 file.**

Bahulkar is a Vedic scholar, and a catalogue by him of this collection is the document that
would convert every *probable* recension above into a stated one. **Neither has been read.**
They are the cheapest next step in this whole domain and they are named here so that is
obvious.

## Status of every item

All 22 are `review_status: NEEDS_AUDIBLE_REVIEW` and `coverage_claimed: false`. Nothing was
heard: `audible_opening` is null on every row, with the note that this environment cannot
audition audio. No duration is recorded, because none is stated in the metadata and
measuring one would mean fetching files.

Classification rests on what the source states — item title, stated reciter, and sibling
items in the same collection — never on "Samaveda" appearing in a title and never on a
reciter's name alone, both of which decision D forbids.

## A note on the classifier itself

Two items were initially filed `UNKNOWN` by a first pass, and both were consequential: the
Mādhyandina item, and `Aranyakagana` — a genuine Samavedic gāna class whose title contains
neither "gramageya" nor "samaveda". A third, `Tattiriya`, slipped a
`tittiriya|taittiriya` test.

Transliteration variance is the rule in this material, not the exception. A keyword
classifier over Sanskrit titles will under-report, and it fails *silently* into `UNKNOWN` —
which reads as "the deposit has nothing" rather than "the classifier missed it". The
`UNKNOWN` count is therefore a property of the classifier before it is a property of the
collection, and it was only caught by reading the unclassified titles rather than trusting
the tally.
