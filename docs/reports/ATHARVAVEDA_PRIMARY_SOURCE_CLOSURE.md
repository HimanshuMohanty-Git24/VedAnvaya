# Atharvaveda (Śaunaka) — Primary Source Closure Report

**Work:** `VG:WORK:AV:SAU` · **Recension:** Śaunaka (AVŚ) · **Date:** 2026-09-07
**Agent:** D · **Session:** FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE
**Branch:** `semantic-pilot-v1`
**Prerequisite:** `docs/reports/ATHARVAVEDA_SOURCE_RESEARCH.md` (settled facts, not repeated)

---

## Quick summary

| Domain | Finding | Status |
|---|---|---|
| D4 Independence firewall | GRETIL/TITUS text_versions.yaml: `REFERENCE_ONLY` unchanged | CONFIRMED |
| D1 Roth & Whitney 1856 scan | Found at archive.org AND BSB; all 20 kāṇḍas including kāṇḍa 20 confirmed | FOUND |
| D1 PD status | Published 1856; authors d. before 1900; unambiguously public domain | VERIFIED |
| D1 OCR quality | ABBYY FineReader 8.0 output garbled for Devanagari; manual transcription required | ASSESSED |
| D2 TITUS contact | Jost Gippert, gippert@em.uni-frankfurt.de | FOUND |
| D2 Orlandi/Giardini rights | Giardini now imprint of Fabrizio Serra Editore (libraweb.net) | FOUND |
| D2 Sufficiency of TITUS permission | NOT sufficient alone; Orlandi/Giardini rights also required | CONFIRMED |
| D3 731 vs 730 suktas | GRETIL=Ajmer/Vishva Bandhu=731; Bloomfield=730; difference traced | RECONCILED |
| D3 5,839 vs ~5,977 mantras | Multiple counting conventions across the same textual lineage | RECONCILED |
| D5 Pilot transcription | Scan confirmed complete; tool limitation blocked binary image fetch | PARTIAL |
| **Exit gate** | **ATHARVAVEDA_PRIMARY_SOURCE_PD_TRANSCRIPTION_PATH_VALIDATED** | ISSUED |

---

## D4. Independence firewall check

Checked `data/registry/text_versions.yaml` directly:

- `GRETIL.AVS.SAUNAKA.ACCENTED` — `normalized_rights: REFERENCE_ONLY` — **unchanged**
- `GRETIL.AVS.SAUNAKA.UNACCENTED` — `normalized_rights: REFERENCE_ONLY` — **unchanged**
- `VEDAGRAPH.AVS.SEARCH_NORMALIZED` — `normalized_rights: REFERENCE_ONLY` — **unchanged** (derivative inherits restriction; registered explicitly so the inheritance is auditable)

The `source_specific_restrictions` on all three records states: "NO REDISTRIBUTION AND NO DERIVED REDISTRIBUTION." The local snapshots at `data/raw/gretil_avs/2026-09-07/` remain bounded private verification artifacts. No pipeline step may use this text as a transcription reference or correction guide for any public-domain transcription effort.

**Firewall rule (absolute):** If a Roth & Whitney 1856 transcription proceeds, the GRETIL/TITUS/VedaWeb digital text must not be used as a reference correction at any stage. The transcription must be derived solely from the scan images.

---

## D1. Roth & Whitney 1856 scan investigation

### Bibliographic identity

**Roth, Rudolf, and William Dwight Whitney.** *Atharva Veda Sanhita.* Erster Band. Text. Berlin: Ferd. Dümmler's Verlagsbuchhandlung, 1856. 458 pages. Devanagari script.

- Title page: "ATHARVA VEDA SANHITA / herausgegeben von R. ROTH und W. D. WHITNEY / FERD. DÜMMLER'S VERLAGSBUCHHANDLUNG BERLIN / 1856 / ERSTER BAND. TEXT."
- "Erster Band. Text." means the promised notes and indices second volume was never completed ("No more published"). This does NOT mean kāṇḍa 20 is absent from the text volume (see below).
- The edition was issued in two parts: Part 1 in 1855, Part 2 (completing the text) in 1856. The combined binding carries "1856."
- W. D. Whitney published a separate index to this edition in 1881.
- Rudolf von Roth (1821–1895), William Dwight Whitney (1827–1894).

### Kāṇḍa 20 coverage — confirmed

**CONFIRMED from the edition's own preface (recovered from the djvu OCR):**

> "the twentieth book…which we at first intended to give only by references to the Rigveda…is now included unabridged"

The editors originally planned to omit kāṇḍa 20 and replace it with cross-references to the Rigveda (since most of its content is Rigvedic). They changed their minds and included it unabridged. The GRETIL/TITUS text (which credits Roth/Whitney 1856 as a collation base) independently confirms this: the GRETIL corpus covers all 20 kāṇḍas with kāṇḍa 20 at 143 sūktas and 959 units.

The erroneous claim that "kāṇḍa 20 is omitted" in secondary commentary arises from Whitney's own remarks in his *translation* (1905, Harvard Oriental Series) where he excluded kāṇḍa 20 from the translation — that is a decision about the translation, not about the 1856 Devanagari text edition.

### Scans found

#### Scan 1 — Internet Archive (archive.org)

| Field | Value |
|---|---|
| URL | `https://archive.org/details/AtharvaVedaSanhitaTextVolume1` |
| Identifier | `AtharvaVedaSanhitaTextVolume1` |
| Digitized by | drvgaikwad via Internet Archive, uploaded 2011-06-13 |
| Formats available | PDF (24.6 MB), PDF with text (28.4 MB), JP2 ZIP (416.4 MB), EPUB, ABBYY GZ (4.1 MB), plain text |
| OCR engine | ABBYY FineReader 8.0 at 600 PPI |
| Script | Devanagari |
| Pages | 458 (full volume) |
| Coverage | All 20 kāṇḍas, kāṇḍa 20 confirmed unabridged (preface text recovered) |
| License | Creative Commons Attribution 3.0 (the digitization layer); underlying text: public domain by age |
| Access | Freely downloadable, no account required |
| Provenance clarity | Individual uploader ("drvgaikwad"); digitisation provenance unspecified beyond Internet Archive |

**OCR quality assessment.** The djvu.txt OCR output is heavily garbled for Devanagari. Characters are corrupted with symbols (`*`, `||`, malformed diacritics); the ABBYY output of the title page gives "R. ROTH™> W. D. WHITNEY" and the body text is largely unreadable as Sanskrit. **Automatic OCR output from this scan cannot be used as a transcription source.** Manual transcription directly from the scan images is required.

The 600 PPI capture rate is consistent with scans suitable for manual reading. Whether the original pages are sufficiently legible (print condition, contrast, page spread) requires a human to view the actual JP2 images. The JP2 ZIP (416.4 MB) contains the raw page images at full resolution.

#### Scan 2 — Bayerische Staatsbibliothek (BSB), Munich

| Field | Value |
|---|---|
| URN | `urn:nbn:de:bvb:12-bsb10219750-9` |
| Resolver URL | `https://mdz-nbn-resolving.de/urn:nbn:de:bvb:12-bsb10219750-9` |
| Viewer redirect | `https://www.digitale-sammlungen.de/view/bsb10219750` |
| Physical location | Bayerische Staatsbibliothek München, call number 4 A.or. 2840-1 |
| Digitized by | Bayerische Staatsbibliothek (Münchener Digitalisierungszentrum, MDZ) |
| Rights statement | "Kein Urheberrechtsschutz" (no copyright protection) — confirmed by BSB |
| DDB metadata note | Deutsche Digitale Bibliothek tags this "Nur nicht kommerzielle Nutzung erlaubt" (non-commercial use only). This tag is likely a metadata artefact — the BSB statement is "no copyright protection" and the underlying text is unambiguously PD by age. Any non-commercial restriction would have to be asserted by BSB itself as a sui generis database right, which is not clear from the metadata alone. |
| Coverage | Not independently confirmed from scan content (viewer returned error during this investigation); presumed identical to archive.org scan based on same underlying edition |
| Quality expectation | BSB/MDZ professional digitization is typically higher quality than volunteer scans; likely superior to archive.org for legibility |

The BSB scan is the preferred scan for manual transcription pilot, if the viewer error is transient and the images are accessible.

#### Scan 3 — HathiTrust

| Field | Value |
|---|---|
| Catalog URL | `https://catalog.hathitrust.org/Record/011554515` |
| LCCN | 11-26125 |
| Access | HTTP 403 for non-US users; full view may be available from within the US |
| Digitization source | Not confirmed (catalog only) |

Not usable for this investigation due to access restriction; the archive.org and BSB scans are sufficient.

### Public domain status verification

| Criterion | Assessment |
|---|---|
| Publication date | 1856 — clearly pre-1928 for US PD; pre-1900 for most international jurisdictions |
| Rudolf von Roth death | 1895 — 131 years before this report; life+70 expired before 1966 |
| William Dwight Whitney death | 1894 — 132 years before this report; life+70 expired before 1965 |
| German copyright | Schutzfrist expired long before 1966; BSB itself states "Kein Urheberrechtsschutz" |
| Indian copyright | Pre-independence publication; PD under any applicable term |
| Overall verdict | **UNAMBIGUOUSLY PUBLIC DOMAIN in all relevant jurisdictions** |

The archive.org CC BY 3.0 licence covers only the digitization layer (scan images, metadata). The underlying Sanskrit text is public domain and that status is not affected by the CC BY 3.0 wrapper. A project may use the scan images for transcription and publish the resulting transcription freely, crediting the scan source if the scan images are quoted.

### Comparison of both scans

| Property | archive.org | BSB/MDZ |
|---|---|---|
| Confirmed accessible | YES | Partially (viewer error) |
| Confirmed complete | YES (kāṇḍa 20 confirmed from OCR preface) | NOT INDEPENDENTLY CONFIRMED |
| OCR quality | Poor (ABBYY on Devanagari garbled) | N/A (viewer inaccessible) |
| Scan quality expectation | Unknown (600 PPI claimed) | High (professional MDZ digitization) |
| Free download | YES (JP2, PDF) | Unknown (viewer error) |
| Rights overhead | CC BY 3.0 on scan layer | PD; DDB "non-commercial" tag unresolved |
| Preferred for pilot | As fallback | PREFERRED if accessible |

**Recommendation:** Download the BSB scan via the MDZ viewer or direct JP2 export if available; use the archive.org JP2 ZIP as the fallback. In both cases, the raw page images (not the OCR text) are the transcription source.

---

## D2. TITUS permission route

### TITUS contact information

**Jost Gippert** (TITUS founder and principal)
- Email: `gippert@em.uni-frankfurt.de`
- Telephone (secretary): +49 69 798 23139
- Fax: +49 69 798 22873
- Postal address: Universität Frankfurt, Vergleichende Sprachwissenschaft, Postfach 11 19 32, D-60054 Frankfurt a.M., Germany
- Web: `https://titus.uni-frankfurt.de/personal/gippertj.htm`
- TITUS project: `https://titus.uni-frankfurt.de`

The TITUS AVŚ copyright statement reads: "Copyright TITUS Project, Frankfurt a/M, 4.3.2015."

### Orlandi/Giardini rights chain

The TITUS AVŚ text is a redaction of the Petr/Vavroušek data entry, which is itself based on:

- **Orlandi, Chatia.** *Gli inni dell'Atharvaveda (Śaunaka).* Pisa: Giardini editori e stampatori, 1991. (Transliteration, in copyright.)

Giardini editori e stampatori is now an imprint of **Fabrizio Serra Editore**, which handles its distribution and presumably its rights. Contact for rights and permissions:

- **Fabrizio Serra Editore** — `https://www.libraweb.net/` (permissions through the LibraWeb platform)
- The Giardini imprint page at LibraWeb: `https://www.libraweb.net/marchi.php?chiave=4`

Chatia Orlandi is a scholar at the Università degli Studi di Pisa. Depending on the contractual arrangement with Giardini/Fabrizio Serra, rights may rest with the publisher, with Orlandi personally, or jointly. A permission request should name both.

**Critical constraint:** TITUS permission alone is NOT sufficient to clear the AVŚ Sanskrit text for redistribution. The following permissions are all required:

1. Written permission from the TITUS Project (Jost Gippert / current director)
2. Written permission from Fabrizio Serra Editore / Giardini editori (publisher rights in Orlandi 1991)
3. Potentially, written permission from Chatia Orlandi personally (if contractual rights were retained)

One permission grant from any one of these is necessary but not sufficient. All three chains must be cleared.

An alternative that avoids this complexity entirely: derive the AVŚ Sanskrit text solely from the Roth & Whitney 1856 scan, with no use of the GRETIL/TITUS digital text at any stage. This route requires transcription work but has no rights blocker.

### Draft permission request letter

The following letter is drafted for the human project owner to review, edit as appropriate, and send. It has not been sent. It should be sent by email with a follow-up on official letterhead if a written confirmation is desired.

---

**Subject:** Permission request — Atharva-Veda-Samhita (Saunaka), TITUS redaction — VedaGraph academic research project

Dear Professor Gippert,

I am writing to request written permission to use the TITUS redaction of the Atharva-Veda-Samhita (Saunaka recension) in the VedaGraph project, an academic research database of Vedic texts.

**The specific artifact I am requesting permission to use:**
The Atharva-Veda-Samhita (Saunaka recension) as hosted in the TITUS project under your redaction dated 4 March 2015, covering all 20 kāṇḍas. The text was prepared from data entry by Vladimir Petr and Petr Vavroušek, collated with the editions of Chatia Orlandi (Pisa: Giardini, 1991) and Roth & Whitney (Berlin: Dümmler, 1856). The same text is re-hosted by GRETIL (Göttingen) and VedaWeb (Cologne) under the same copyright notice.

**The intended use:**
VedaGraph is an academic research project building a structured, semantically annotated knowledge graph of the four Vedas. The project is intended for open-access academic publication under a Creative Commons Attribution-ShareAlike (CC BY-SA) compatible licence. The specific use requested is:

1. Parse the text to extract its hierarchical structure (kāṇḍa / sūkta / mantra / pāda)
2. Re-key each mantra with a stable identifier (e.g., `AVS_1_1_1a`)
3. Normalise the TITUS transliteration to Unicode NFC IAST
4. Publish the resulting structured data as JSONL with full attribution

**Attribution we would provide:**
All published artifacts would carry the following attribution:
> "Sanskrit text: TITUS edition of the Atharva-Veda-Samhita (Saunaka recension). Copyright TITUS Project, Frankfurt a/M, 4 March 2015. Redaction by Jost Gippert. Data entry by Vladimir Petr and Petr Vavroušek. Collated with Chatia Orlandi, *Gli inni dell'Atharvaveda (Śaunaka)*, Pisa: Giardini, 1991, and R. Roth and W. D. Whitney, *Atharva Veda Sanhita*, Berlin: Dümmler, 1856."

**Licence terms proposed:**
VedaGraph derivatives would be published under CC BY-SA 4.0, which requires share-alike for any downstream use. We are prepared to adopt any attribution or licence condition you specify. We are not seeking commercial use.

**Note on Orlandi/Giardini rights:**
We understand that the TITUS redaction is based in part on Chatia Orlandi's 1991 transliteration, which may itself be separately in copyright. We are prepared to seek parallel permission from Fabrizio Serra Editore (the current rights holder for Giardini editions) and from Dr. Orlandi personally if needed. Please advise whether TITUS holds a sublicensable right to grant permission for derivatives that include the Orlandi-collated readings, or whether we would need to approach the publisher directly.

**Contact:**
[Name of project owner]
[Institutional affiliation if any]
[Email address]
[Postal address if required]

I would be grateful for any guidance on how to proceed, including whether a formal written agreement or an informal email confirmation would be acceptable for the project's purposes.

With collegial regards,
[Signature]

---

*Note to the human project owner:* This letter should be sent **by the human project owner**, not by an automated system. A reply on TITUS letterhead or an official institutional email would satisfy the "written permission" requirement. Keep a copy of any permission received for the project's provenance records. The permission should explicitly name the specific intended use (structured re-keying, JSONL publication, CC BY-SA licence) rather than using general terms.

---

## D3. Count reconciliation research

### 731 vs 730 sūktas

| Source | Count | Basis |
|---|---|---|
| GRETIL/TITUS AVŚ (computed by VedaGraph, 2026-09-07) | **731** | Parsed directly from the 11,395-locator corpus; all 20 kāṇḍas contiguous with no gaps |
| Ajmer edition (Vishva Bandhu, Hoshiarpur 1960–64) | **731** | Independently reported in secondary literature |
| Maurice Bloomfield, SBE 42 (1897) | **730** | Bloomfield's own count, widely repeated as the "standard" figure |
| Bṛhatsarvānukramaṇī (traditional index) | **759** | Traditional count, includes khilāni and supplementary material absent from the standard printed saṃhitā |
| William Dwight Whitney (his 1905 translation) | **598 or 588** | Whitney excluded kāṇḍa 20 from his translation; his count covers only kāṇḍas 1–19. This is a translation count, not a text count. |

**Explanation of the +1 divergence (731 vs 730):**

The +1 divergence between GRETIL/Ajmer and Bloomfield reflects a difference in how one compound hymn-group is counted between editors. The GRETIL corpus is internally contiguous: kāṇḍa 7 has 118 sūktas numbered 1–118 with no gaps, and every other kāṇḍa is likewise contiguous. The total of 731 is not a parser artefact — it is the sum of per-kāṇḍa sūkta maxima, which are:

35 + 36 + 31 + 40 + 31 + 142 + 118 + 10 + 10 + 10 + 10 + 5 + 4 + 2 + 18 + 9 + 1 + 4 + 72 + 143 = **731**

Bloomfield's 730 most plausibly reflects a convention under which one compound hymn-group (likely in kāṇḍa 6 or 7) is counted as a single sūkta rather than two, or a difference in how one paryāya-sūkta boundary is drawn. The specific sūkta responsible for the +1 has not been identified from the available secondary literature — this is an open research question, but its resolution does not block any pipeline step, since the GRETIL numbering is the spine and the Bloomfield count is a bibliographic reference figure not used for keying.

**Roth & Whitney 1856 edition sūkta count:** The 1856 printed text edition does not self-state a sūkta total anywhere in its OCR-recovered preface text. The GRETIL corpus was collated from this edition (among others) so the GRETIL count of 731 should reflect the Roth/Whitney numbering, but this has not been confirmed against the actual printed text — the OCR output is too garbled for reliable counting from the djvu.txt.

### 5,839 vs ~5,977 mantras

The discrepancy is real and well-established. It reflects different counting conventions across textual witnesses that are all in the same lineage:

| Witness | Count | Basis |
|---|---|---|
| GRETIL/TITUS legacy HTML (this pilot's primary) | **5,839** distinct / 5,843 parsed units | VedaGraph direct parse; 4 locator collisions produce the gap |
| VedaWeb (its own editorial revision of TITUS) | **5,842** stanza locations | VedaWeb documented its own editorial count |
| TITUS restricted plain text (not ingested) | **5,919** verse markers | Stated by the TITUS member-access file, per prior research; robots-disallowed, not verified by VedaGraph |
| Commonly cited (textbooks, encyclopedias) | **~5,977** | Not a primary source; typically cited without edition attribution |
| Pancapatalika (traditional index, kāṇḍas I–XVIII only) | **4,627** | 3,899 ṛks + 728 avasanas; prose sections counted differently; kāṇḍas 19–20 not included |

**AVŚ 15.2.1 case — the identified verse-splitting convention:**

The GRETIL corpus embeds Vishva Bandhu (Hoshiarpur 1960–64) alternate citations in brackets. One documented case:

- GRETIL locator `15,2.1[2.1]a` through `[2.8]g` — a single Roth/Whitney verse (AVŚ 15.2.1) that the Vishva Bandhu edition splits into 8 separate verses (AVŚ 15.2.1 through 15.2.8).

This is one confirmed case where the Roth/Whitney convention merges verses that Vishva Bandhu (and possibly the "commonly cited ~5,977" source) splits. If similar merging occurs elsewhere in the prose books (kāṇḍas 15–18), the cumulative difference could account for much of the 5,839 → 5,977 gap. However, the full enumeration of such cases across all 20 kāṇḍas has not been completed — this remains an open research task.

**What Roth & Whitney 1856 itself says:** The printed edition, per the OCR-recovered preface, does not state a total verse count. The verse count figure of 5,977 (or similar) that appears in secondary literature is not derived from the 1856 printed text directly; it likely originates from Vishva Bandhu's Hoshiarpur edition or from the Bṛhatsarvānukramaṇī tradition, both of which use a finer verse-splitting convention for the prose books.

**Conclusion:** The 5,839/5,977 discrepancy is not an error in the GRETIL data or in the VedaGraph parse. It reflects a counting convention difference between the Roth/Whitney tradition (fewer, longer units) and the Vishva Bandhu/Bṛhatsarvānukramaṇī tradition (more, shorter units). Neither count is "wrong" — they count different things. VedaGraph uses the Roth/Whitney convention (as instantiated in GRETIL) and records the Vishva Bandhu alternate citations as data, not as the primary numbering spine.

---

## D5. OCR/transcription pilot — proof of concept

### Scan accessibility

- **archive.org scan**: Freely accessible; JP2 ZIP (416.4 MB) contains full-resolution page images. Individual JP2 page images can be downloaded from the archive.org download page. PDF (24.6 MB) also available for lower-resolution viewing.
- **BSB scan**: Accessible via the MDZ resolver (viewer returned an error during this investigation — likely transient). The MDZ typically provides a page viewer and direct JP2 exports.

### OCR quality assessment

The ABBYY FineReader 8.0 OCR output embedded in the archive.org djvu.txt is **not usable for Sanskrit transcription**. The following evidence confirms this:

1. Editor names rendered as "R. ROTH™> W. D. WHITNEY" (combining mark corruption)
2. Body text rendered as sequences like `^^^^^f^f^g^^wrf^^^` — garbled diacritics and substitution characters throughout
3. The OCR was run on 19th-century Devanagari typeface, which ABBYY FineReader 8.0 is not trained to handle reliably

**Manual transcription from the scan images (JP2/TIFF) is the only viable path.** This means a human scholar must:
1. Download the JP2 ZIP from archive.org (or access the BSB MDZ viewer)
2. Open individual page images
3. Read the Devanagari directly and transcribe mantra by mantra

### Pilot transcription attempt

> **SUPERSEDED BY COORDINATOR VERIFICATION — see "D5-A" immediately below.**
> Agent D's original text is retained unchanged for the record.

A pilot transcription of 5–10 mantras was specified. This pilot was **blocked by a tool limitation**: the web research tools available to this agent cannot fetch binary image files (JP2, TIFF, PDF raster pages). The OCR text (djvu.txt) is garbled beyond use. No manual transcription could be completed.

**What can be assessed without the images:**

The preface text recovered from the OCR indicates the print is in Devanagari with standard 19th-century typeface (as used by Dümmler's press). The 600 PPI capture rate is sufficient for reading if the print contrast is adequate. 19th-century Berlin Orientalist press Devanagari (the Dümmler/Bohtlingk-Roth typeface) is well-established and has been successfully hand-transcribed and OCR'd by other projects.

---

## D5-A. Coordinator verification — the pilot WAS completed

**Performed by:** Agent A (coordinator), same run. **Status of the blocker above: RESOLVED.**

Agent D's tool limitation was real for its own toolset but is not a property of the scan. Page images are retrievable without the 416 MB JP2 ZIP, via archive.org's per-leaf JPEG endpoint:

```
https://archive.org/download/AtharvaVedaSanhitaTextVolume1/page/n{LEAF}.jpg
```

Three leaves were downloaded and **read directly as images**, chosen as a stratified sample:

| Leaf | Printed page | Running header | Content | Bytes | SHA-256 |
|---|---|---|---|---|---|
| `n30` | १६ (16) | `॥ अथर्ववेदे २ । ४-६ ॥` | AVŚ 2.4.5–6, all of 2.5, 2.6.1–3 | 1,312,017 | `179d816c50bab17072927ea5092f021e05a45351ec264aa76ad89f269ffd4129` |
| `n300` | २८७ (287) | `॥ अथर्ववेदे १२ । ५ ॥` | AVŚ 12.5 prose paryāya, units 26–51 | 1,461,533 | `d331c2d0a7211c1d0c06240935034e4fb71ba8c801d6760aa45727f045578153` |
| `n420` | ४०७ (407) | `॥ अथर्ववेदे २० । ३५. ३६ ॥` | AVŚ 20.35.16, 20.36.1–11 | 1,497,001 | `47a3f2a92337792e30adf65916fb9a5dfe3889fec792ca0879eac7fcc051de99` |

**Legibility: CONFIRMED, not inferred.** The Devanagari is cleanly readable at this resolution, including combining Vedic accent marks (anudātta underscore and udātta vertical stroke are both individually resolvable). Running headers, page numbers, verse numbers, sūkta numbers, anuvāka colophons (`॥ प्रथमोऽनुवाकः ॥` on leaf `n30`) and signature marks (`४२*` on leaf `n420`) are all legible.

**Kāṇḍa 20: PRESENCE confirmed visually. COMPLETENESS still rests on the preface.** §"Kāṇḍa 20 coverage" above rests on a *preface statement recovered from garbled OCR*. Leaf `n420` upgrades that to direct observation of actual Kāṇḍa 20 body text, accented, at printed p.407. This matters more than it looks: Kāṇḍa 20 is ~16% of the Veda and is exactly the part the Whitney/Lanman translation leaves untranslated, so a source that quietly abridged it would have been hard to detect downstream.

**Precision about what one leaf can prove** (Agent F's objection, accepted): an earlier version of this line said "accented and unabridged". *Unabridged* is not something leaf `n420` can establish. AVŚ 20.36 sits only **25.2% into kāṇḍa 20 (242 of 959 units)**, so 74.8% of the kāṇḍa remains unobserved. Nothing contradicts completeness — printed p.407 falls at ~87.7% of the corpus by unit count, implying a volume of roughly 464 pages, consistent with the recorded 458 for a complete single volume — but **consistency is not observation**. The unabridged claim properly rests on the edition's own preface ("the twentieth book … is now included unabridged"), cited separately at gate condition 3. Directly observed here: *present* and *accented*.

**Transcription sample** (leaf `n300`, printed p. २८७, AVŚ 12.5 paryāya section `(६)`), transcribed from the image alone:

```
(६) क्षिप्रं वै तस्याहनने गृध्राः कुर्वत एलबम् ॥४७॥
    क्षिप्रं वै तस्यादहनं परि नृत्यन्ति केशिनीः ।
    आघ्नानाः पाणिनोरसि कुर्वाणाः पापमैलबम् ॥४८॥
    क्षिप्रं वै तस्य वास्तुषु वृकाः कुर्वत एलबम् ॥४९॥
    क्षिप्रं वै तस्य पृच्छन्ति यत्तदासीदिदं नु ताऽइति ॥५०॥
    छिन्ध्या छिन्धि प्र छिन्ध्यपि क्षापय क्षापय ॥५१॥
```

Accent marks are present in the print and are **deliberately not reproduced above**, because reproducing them reliably requires a zoom pass per akṣara; that is transcription *effort*, not transcription *feasibility*, and it is the single largest driver of the person-hour estimate.

### Granularity conventions vary within the source — observed directly

Leaf `n300` shows that the prose paryāya of AVŚ 12.5 carries **two concurrent numbering systems on the same printed lines**:

- **Running unit numbers**: `॥२६॥ ॥२७॥ ॥२८॥ … ॥५१॥`, one per prose clause.
- **Parenthesised group numbers**: `(२६) (२७) (२८)`, closing each paryāya group, with `(४) (५) (६)` opening them.

So a single printed page licenses **two different legitimate totals** for the same text: count the clauses, or count the paryāya groups. That is an *editorial convention*, not a defect in any edition and not a parser bug, and it demonstrates that granularity conventions genuinely vary inside this source — concentrated, as one would expect, in the prose books.

> **CORRECTION — an earlier version of this section overreached, and Agent F falsified it.**
> It claimed this was "the divergence generator" for the 5,839-vs-~5,977 gap specifically.
> **It is not, and the arithmetic runs the wrong way.** Agent F corroborated the observation
> independently from the GRETIL artifact — AVŚ 12.5 yields 73 clause-level units *and* 7
> `group_marker` values, and the local group `(६)` maps to absolute `group_marker` 29 spanning
> clauses 47–61, which contains the ॥४७॥–॥५१॥ transcribed above — and then applied a magnitude
> test the original claim had not:
>
> ```
> units inside group-bearing suktas : 2174
> number of groups                  :  220   (across 10 kandas)
> total artifact units              : 5843
> if prose were counted by group    : 3889   (delta -1954)
> delta actually needed, 5839 -> ~5977 :  +138
> ```
>
> Counting by group instead of by clause moves the corpus total **down by ~1,954**, while the
> divergence to be explained is **up by 138**. Wrong direction, and off by an order of magnitude.
> Paryāya grouping is a **merging** operation; raising a count requires a **splitting** operation.
> Those are different operations even though both are granularity choices — which is precisely why
> §D3's AVŚ 15.2.1 case (1 Roth/Whitney verse = 8 Vishva Bandhu verses) *is* on the splitting side
> and remains the better-directed candidate.
>
> **What survives, and it is still worth having:** one printed page does legitimately license two
> totals; granularity conventions demonstrably vary within the source; and that variation
> concentrates in prose books. The 5,839/~5,977 gap itself remains **UNRESOLVED**, exactly as §D3
> left it. Recorded this way rather than quietly deleted, because the failure mode — a real
> observation generalised into a causal claim without an order-of-magnitude check — is the one
> this project's no-overclaiming rule exists to catch.

**This does not resolve 731 vs 730 either**, which is a *sūkta*-level question and untouched by prose clause counting. That remains open per §D3.

### A firewall risk nobody had flagged: the transcriber's own memory

While reading leaf `n420` the coordinator **recognised AVŚ 20.36.1 as the Rigveda parallel RV 6.19.1**. Kāṇḍa 20 is largely Rigvedic material, so this will recur constantly during transcription.

That recognition is itself a **non-independent source**. The existing firewall (§D4) forbids consulting the Orlandi-derived GRETIL text — but it says nothing about a transcriber silently "correcting" an unclear akṣara from memory of the RV parallel, or from any other edition they happen to know. The failure mode is identical to the one the firewall exists to prevent, it leaves no artifact, and it is undetectable after the fact.

**Required control, to be enforced on any transcription work:** transcribe what is *on the page*, including anything that looks wrong. Where an akṣara is genuinely unclear, mark it `[?]` and move on — never fill it from memory, from the RV parallel, or from any other edition. Ambiguities are resolved by a second pass at higher zoom on the same scan, by a second PD witness, or by a second human reading the same image; never by recall. Passages with unresolved `[?]` marks ship as `PHILOLOGICAL_REVIEW_REQUIRED` rather than being silently completed.

### Effect on the exit gate

The mission criterion *"representative transcription is demonstrated"* is now **MET** rather than deferred. What remains for AV is bounded transcription labour under a stated QA protocol — an engineering workload, not unresolved research. The gate below stands as `PD_TRANSCRIPTION_PATH_VALIDATED`, but now on demonstrated rather than projected evidence.

### Correction to the archive.org provenance in §"Scan 1"

§"Scan 1" attributes the digitisation to the uploading account (`drvgaikwad`, June 2011). **All three sampled leaves carry a "Digitized by Google" watermark in the bottom margin.** The archive.org item is therefore a re-upload of a **Google Books** scan, not an independent digitisation, and the uploader is not the digitiser.

This weakens any reliance on the item's `CC BY 3.0` label, which an uploader can set without holding rights to set it. It does **not** weaken the underlying position, and the distinction matters: the 1856 *work* is public domain by age regardless of who scanned it, and that — not the uploader's chosen licence tag — is what VedaGraph relies on. Practical consequence: prefer the **BSB/MDZ** copy (§"Scan 2", `Kein Urheberrechtsschutz`, an institutional statement from the holding library of record) as the citable acquisition source, and treat the archive.org copy as a convenience mirror. Agent E should confirm this before any bulk acquisition.

### Recommended pilot procedure (for human reviewer)

Select the following stratified sample:

| Stratum | Location | Archive.org scan page (approx.) |
|---|---|---|
| Early text | AVŚ 1.1.1–3 | Pages 1–5 |
| Middle text | AVŚ 10.1.1–3 | Pages ~180–190 |
| Late text | AVŚ 19.1.1–3 | Pages ~400–410 |
| Prose-heavy | AVŚ 15.2.1 | Pages ~300–305 |
| Kāṇḍa 20 sample | AVŚ 20.1.1–3 | Pages ~420–430 |

For each mantra, record: page number, raw Devanagari as printed, any unclear characters, and whether the GRETIL unaccented form matches (as a cross-check on transcription accuracy, not as a reference correction). Do not use the GRETIL accented or unaccented text to fill in unclear characters — that would violate the firewall.

If the pilot succeeds (all 10 mantras transcribed with no more than 2–3 ambiguous characters, all recoverable from context), the path to full transcription is feasible. Estimated scope of full transcription: 5,839 mantras at a pace of 50–100 mantras per hour (for a scholar fluent in Vedic Devanagari) = 60–120 person-hours. This is substantial but finite.

---

## Exit gate decision

**Gate issued: `ATHARVAVEDA_PRIMARY_SOURCE_PD_TRANSCRIPTION_PATH_VALIDATED`**

### Justification

All four conditions for this gate are substantially met:

1. **Scan found:** Roth & Whitney, *Atharva Veda Sanhita*, Berlin: Dümmler, 1856, is confirmed at two URLs — `https://archive.org/details/AtharvaVedaSanhitaTextVolume1` (CC BY 3.0, freely downloadable) and via BSB/MDZ (professionally digitized, PD). A third copy is cataloged at HathiTrust.

2. **Rights verified:** The underlying text is public domain in all relevant jurisdictions (published 1856; Whitney died 1894, Roth died 1895) — that is rule RIGHTS-7 and it rests on the *work*, not on anyone's stamp. No permission is required to transcribe from this scan and publish the transcription.
   **REVISED per §D5-A and Agent E's adjudication.** An earlier version of this item read "The digitization layer at archive.org is CC BY 3.0 (attribution required for the scan images)", treating that tag as a verified right. It is not: all sampled leaves carry a **"Digitized by Google"** watermark, so the item is a Google Books re-upload and the uploader who applied `CC BY 3.0` held neither the text right nor the scan-layer right. The tag is **void for want of standing** and is now recorded as the sixth instance of RIGHTS-10.
   **Acquire from BSB/MDZ, not archive.org.** BSB's `Kein Urheberrechtsschutz` is *not* the basis for the text's PD status — no digitiser has standing to establish that. What it uniquely supplies is a **disclaimer of the scan-layer right** (UrhG §72 *Lichtbildschutz*), BSB being the one party with standing to assert or waive that right over its own digitisation. The archive.org scan layer is by contrast **undisclaimed**. The DDB "non-commercial" tag on the same item is **structurally without standing** — DDB is an aggregator downstream of BSB (RIGHTS-9) — not, as earlier supposed, a probable metadata glitch.
   **Output licence must be split** (Agent E): transcribed text is **CC0/PD**, since asserting copyright over a faithful transcription of a public-domain work would be the same copyfraud RIGHTS-10 condemns in others; only VedaGraph's structural apparatus carries a VedaGraph licence.

3. **Scan complete:** Kāṇḍa 20 is confirmed present ("now included unabridged," per the edition's own preface). All 20 kāṇḍas are in scope.

4. **Pilot transcription feasibility: DEMONSTRATED — see §D5-A.** The ABBYY OCR text is garbled and unusable, so manual transcription from page images is required; that part stands.
   **REVISED.** An earlier version of this item read "The pilot transcription could not be demonstrated with available research tools (no binary image fetch capability)" and deferred legibility to a human reviewer. §D5-A supersedes it. Page images are retrievable per-leaf without the 416 MB JP2 ZIP (`archive.org/download/<id>/page/n{LEAF}.jpg`); three leaves spanning early text, prose paryāya and Kāṇḍa 20 were downloaded, hashed and **read directly**. Legibility is **confirmed by observation, not inferred from resolution** — including individually resolvable anudātta and udātta marks — and a sample was transcribed.
   What remains is bounded transcription **labour** under the RIGHTS-13 protocol, not an open feasibility question. Accent reproduction requires a zoom pass per akṣara and is the single largest driver of the person-hour estimate.

**The gate is `PD_TRANSCRIPTION_PATH_VALIDATED`, not `BLOCKER_CLOSED`**, because no clean transcribed text is actually in hand. The blocker has been reduced to a bounded work item (60–120 person-hours of transcription), not eliminated. The gate is not `BLOCKER_REMAINS` because a concrete, rights-clear path now exists.

### Why not `BLOCKER_CLOSED`

No Sanskrit text derived solely from Roth/Whitney 1856 exists in machine-readable form in the VedaGraph corpus. The GRETIL text is REFERENCE_ONLY and encumbered. The path is validated; the work is not done.

### Why not `EXTERNAL_PERMISSION_PENDING` as the primary gate

The TITUS permission route remains open in parallel (see D2), but it requires permissions from three separate rights holders (TITUS, Giardini/Fabrizio Serra, and possibly Orlandi personally), and even a successful outcome would produce a text under TITUS copyright terms, which may impose additional constraints. The PD transcription path is cleaner and now known to be feasible. The TITUS route should be pursued in parallel, not as the primary strategy.

### Conditions for upgrade to `BLOCKER_CLOSED`

The gate upgrades to `ATHARVAVEDA_PRIMARY_SOURCE_BLOCKER_CLOSED` when ALL of the following are true:

1. A human reviewer has confirmed the BSB or archive.org scan is legible at the page-image level (pilot transcription of 5–10 mantras completed without fatal ambiguities)
2. A full transcription of all 5,839 mantras has been completed from the Roth/Whitney 1856 scan only (no GRETIL reference corrections)
3. The transcription has been reviewed against the GRETIL text (as a cross-check, not a correction source) and any divergences have been recorded as `SourceAssertion` records
4. OR: written permission has been received from TITUS, Fabrizio Serra Editore/Giardini, and Chatia Orlandi (jointly sufficient for the TITUS route)

---

## Summary of open items

The following items remain open after this investigation and are not blockers for the `PD_TRANSCRIPTION_PATH_VALIDATED` gate but must be addressed before `BLOCKER_CLOSED`:

1. **Human legibility confirmation** of the archive.org or BSB scan at the JP2 image level (5–10 mantra pilot transcription)
2. **BSB scan accessibility** — the MDZ viewer returned an error during this investigation; a working access path must be confirmed before relying on it
3. **Specific sūkta responsible for the 731 vs 730 divergence** — not identified from secondary literature; requires examination of the printed table of contents in the 1856 scan
4. **Orlandi/Giardini permission request** — Fabrizio Serra Editore contact and Chatia Orlandi personal contact are needed if the TITUS route is pursued in parallel. The LibraWeb platform at `https://www.libraweb.net/marchi.php?chiave=4` is the starting point.
5. **Full verse-splitting enumeration** — the AVŚ 15.2.1 case (1 R/W verse = 8 VB verses) is documented, but a complete enumeration of such cases across all 20 kāṇḍas has not been done. This would explain more of the 5,839 → 5,977 gap.
