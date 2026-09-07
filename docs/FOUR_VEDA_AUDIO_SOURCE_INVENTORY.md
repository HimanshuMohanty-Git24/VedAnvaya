# Four-Veda Audio Source Inventory

**Owner:** Agent E (rights / provenance / source archivist) — single writer
**Compiled:** 2026-09-07. All quotes retrieved 2026-09-07 unless stated.
**Vocabulary and operational semantics:** `data/registry/rights.yaml`

---

## 0. The hard rule, stated first

> **Audio carries its own rights and never inherits them from the text source.**
> — `data/registry/rights.yaml`, policy rule RIGHTS-6

A recitation is a **separate copyrightable performance** and usually carries a **separate sound-recording
copyright**, held by the reciter, the recordist, or the publishing institution. The Vedic text being
ancient is irrelevant to the recording's status.

> **Do NOT download or mirror restricted material merely because it is publicly playable.**

### The single most important number in this document

Of **199** archive.org audio items matching
`(rigveda OR samaveda OR yajurveda OR atharvaveda) AND mediatype:audio`:

| | Count |
|---|---|
| Items with **any** `licenseurl` field | **75** |
| Items with **no** licence field (⇒ all rights reserved) | **124 (62%)** |
| Of the 75: **NC-ND** (derivatives forbidden) | **47** |
| Of the 75: **CC Public Domain Mark 1.0** | **21** |
| **Items under `PUBLIC_DOMAIN` / `CC0` / `CC_BY` / `CC_BY_SA` suitable for saṃhitā recitation** | **0** |

**Zero archive.org assets carry a licence permitting redistribution of Veda saṃhitā recitation.**

**ONE EXCEPTION EXISTS, AND IT IS OUTSIDE ARCHIVE.ORG.** Wikimedia Commons holds **474 Ogg files** of
Kauthuma sāman/gāna recitation — 458 CC BY-SA 4.0, 16 CC0, none missing a licence, each verified
individually via the Commons `imageinfo`/`extmetadata` API rather than inferred from platform terms.
**That is the only mirrorable Veda audio found anywhere, and it covers only Sāmaveda.** See §6.5.

For the other three Vedas the position is unchanged: nothing is cleared for local mirroring. No audio
has been snapshotted yet, which remains the correct state.

**Note the shape of that exception.** It was not found by looking harder at the hosts that advertise
licences. It was found on a platform whose licences are *per file*, by checking each file. The 16 CC0
files are also the first and only CC0 material in the whole registry — the enum member requested from
Agent A was unused until they turned up.

### Five failure modes this inventory exists to catch

1. **Playability is not permission.** HTTP 200 on a media file says nothing about rights. §5 is a
   commercially-sold, in-copyright recording that streams fine.
2. **A licence tag from someone without standing is not a licence.** Most archive.org licence tags on
   Vedic audio were applied by third-party re-uploaders who never held the rights. §4.
3. **CC Public Domain Mark 1.0 is an assertion, not a grant.** §2.
4. **ND silently forbids exactly what we want to do.** §3.
5. **Recension labels on audio are frequently wrong.** Most items labelled "Śukla Yajurveda" are
   **Kāṇva**, not the Mādhyandina recension VedaGraph targets.

**A structural irony worth naming up front: the best-aligned assets are the least free.** The two
sources with genuine per-sūkta granularity are the Vedic Heritage Portal (explicitly permission-gated by
IGNCA) and `rgveda-auro-sriranga` (a commercial DVD recording with only an informal,
screenshot-documented permission).

---

## 1. Coverage summary

| Veda | Recension | Best-aligned source | Coverage | Best rights | Mirrorable |
|---|---|---|---|---|---|
| Rigveda | Śākala | `rgveda-auro-sriranga` / VHP | **complete, per sūkta (1028)** | `PERMISSION_REQUIRED` | **No** |
| **Sāmaveda** | **Kauthuma** | **Wikimedia Commons, 474 ogg** | **474 files, page-level** | **`CC_BY_SA` + `CC0`** | **YES** |
| Sāmaveda *(higher authority)* | Kauthuma | VHP `/Samaveda_MP3/` + `Uha_Gaan/` | **partial, irregular** | `PERMISSION_REQUIRED` | No |
| Śukla Yajurveda | **Mādhyandina** | VHP `SYMS_CHAP_01–40` | **complete, per adhyāya** | `PERMISSION_REQUIRED` | **No** |
| Atharvaveda | Śaunaka | VHP `/atharaveda_mp3/` | **complete, per sūkta (~748)** | `PERMISSION_REQUIRED` | **No** |

**All four Vedas have authentic audio located. Exactly one — Sāmaveda — has a mirrorable option.**

**For Sāmaveda the choice is explicitly authority versus usability**, and it should be made deliberately
rather than by default: VHP is institutionally authoritative (IGNCA) and unmirrorable; Commons is
community-contributed with unnamed reciters and mirrorable. That is a curation decision, not a rights
decision.

**Why this matters disproportionately for Sāmaveda.** The available Kauthuma *text* contains
arcika/verse content only, with **zero gāna** — and the Kauthuma gāna corpus is roughly **2,639 gānas
against 1,875 arcika verses**. The sung dimension is the *larger* artifact. So for this one Veda audio
is not supplementary: it carries content the text does not, and the only mirrorable audio happens to
render exactly that.

---

## 2. Standing policy: reject CC Public Domain Mark 1.0 at face value

**21 of the 75 licensed archive.org items use PD Mark**, and in every case checked it was applied by a
**re-uploader who is not the rights holder**, to a **2020 sound recording**.

**PD Mark is not a licence and not a waiver.** It is an *assertion by whoever applied it* that a work is
*already* out of copyright. The underlying Vedic text is ancient and out of copyright; **the recording
is not.**

**Policy:** PD Mark on Vedic audio is treated as **`UNKNOWN`**, never `PUBLIC_DOMAIN`, unless the
applier is demonstrably the rights holder AND the recording's age independently supports expiry. This is
rule RIGHTS-8 (absence or mere assertion of a licence is not a grant) and rule RIGHTS-4 (a permissive
status is never inferred, only evidenced) applied to audio.

**Do not collapse PD Mark into `PUBLIC_DOMAIN` in any future model change.** If a distinct marker is
ever wanted, it must be a *flag on unverified assertions*, not a permissive status.

---

## 3. Standing policy: ND is a hard blocker, not a mild one

**47 of the 75 licensed archive.org items are NC-ND.** NoDerivatives is the single most consequential
licence term in this domain, and it is easy to misread as "licensed, therefore usable".

**A segmented, per-mantra-aligned audio corpus is a derivative work.** ND forbids precisely the one
operation VedaGraph would perform on audio. ND items therefore **cannot feed an alignment pipeline at
all**, even though they superficially look permissioned — often *better* permissioned than the
unlicensed majority.

`CC_BY_NC_ND` is deliberately **not** in the VedaGraph `RightsStatus` vocabulary and has **not** been
requested from Agent A, because no artifact would ever be ingested under it. ND items are recorded
operationally as **`REFERENCE_ONLY`**.

Worked example — the cleanest licence chain in the whole survey, which still fails:
`shukla-yajurveda-kanva-samhita-pri`, `licenseurl: https://creativecommons.org/licenses/by-nc-nd/4.0/`,
complete Kāṇva 40 adhyāyas one file each, licence set **by the credited reciter/uploader himself
(P R Iyer)** — so licensor and rights holder plausibly coincide. It fails twice over: **ND** blocks
per-mantra derivatives, and it is the **wrong recension** (Kāṇva, not Mādhyandina). *A valid licence
from the right party can still be the wrong licence.*

---

## 4. Vedic Heritage Portal (IGNCA) — best aligned, explicitly gated

**URL:** https://vedicheritage.gov.in/ · registered as `VHP`, `PERMISSION_REQUIRED`

By far the best-structured source, and the only one with per-passage file granularity aligned to
canonical reference schemes across **all four** target recensions.

### 4.1 Verbatim rights evidence

**Copyright Policy** — https://vedicheritage.gov.in/copyright-policy/ :

> "The contents of this website can not be reproduced partially or fully, without written permission
> from Indira Gandhi National Center for the Arts or the contributor (with intimate to IGNCA). If
> referred to as a part of another publication, the source must be appropriately acknowledged. The
> contents of this website can not be used in any misleading or objectionable context."

Note it covers "the contents of this website" with **no audio/video carve-out**.

### 4.2 ⚠ Two live IGNCA policies contradict each other on direct linking

This is a **new blocker that affects even the link-only fallback**, and it was not previously recorded.

**Terms & Conditions** — https://vedicheritage.gov.in/terms-conditions/ :

> "Links to Vedic portal by other websites — We do not object to linking directly to the information
> that is hosted on this portal and **no prior permission is required** for the same. However, we would
> like to be informed by you about any links provided to this portal … Also, we do not permit our pages
> to be loaded into frames on your site. The pages belonging to this portal must load into a newly
> opened browser window of the User."

**Hyper linking Policy** — https://vedicheritage.gov.in/hyper-linking-policy/ :

> "**Prior permission is required** before hyperlinks are directed from any website/portal to this site.
> Permission for the same, stating the nature of the content on the pages from where the link has to be
> given and the exact language of the Hyperlink should be obtained by sending a request at Indira Gandhi
> National Centre for the Arts, India"

**Both pages are live and both are linked from every page footer.** One says no prior permission is
needed to link; the other says prior permission *is* required.

**Ruling:** VHP is treated as `PERMISSION_REQUIRED` **for linking as well as for copying**, until IGNCA
clarifies in writing. This is more conservative than the `PERMISSION_REQUIRED` default in
`data/registry/rights.yaml`, which grants `direct_link: yes` — a rights holder can restrict linking, and
this one arguably has. Also binding regardless: **no framing.** Any player must open VHP URLs in a
newly opened window, never an iframe.

### 4.3 Technical anti-download measure — corroborating intent

Every VHP page injects, verbatim from page source:

> `$('audio').attr('controlsList', 'nodownload');`
> `video_element.setAttribute("controlsList", "nodownload");`
> `video_element.setAttribute("disablepictureinpicture", "");`

IGNCA has taken a **deliberate technical step to prevent download**. That is evidence of intent
independent of the policy text, and it removes any argument that publicly playable implies permitted.

### 4.4 Coverage, verified live by HEAD probe

| Veda / recension | Media | Path pattern | Granularity | Verification |
|---|---|---|---|---|
| **Rigveda Śākala** | MP4 **video** | `/video/RIGSS_{MM}_{SSS}.mp4` | **per sūkta** | `01_001`, `01_002`, `05_001`, `09_113`, `10_191` → 200; `10_192` → 404. **Boundary matches the canonical 1028 sūktas.** |
| **Atharvaveda Śaunaka** | MP3 audio | `/atharaveda_mp3/Athss_{KK}_{SSS}.mp3` | **per sūkta, kāṇḍas 1–20** | `01_001`, `10_001`, `15_001`, `18_004`, `19_072`, `20_143` → 200. ~748 files. `05_050` → 404, correctly (AV 5 has 31 hymns). |
| **Śukla YV Vājasaneyi-Mādhyandina** | MP4 **video** (directory misleadingly named `_MP3`) | `/Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_{NN}.mp4` | **per adhyāya, 1–40 complete** | `01,05,10,15,20,25,30,35,40` → 200; `41` → 404. Plus `SYMS_INTRO_CHAP_{06,21,36}`. **The `.mp3` variants now 404** — an earlier MP3 generation existed and was withdrawn. |
| **Sāmaveda Kauthuma** | MP3 audio | `/Samaveda_MP3/SAMKP_{a}_{b}_{c}_{ddd}.mp3`; `Samkp_{06}_{bb}_{ddd}.mp3`; `/Samveda_Kautham_mp3/Uha_Gaan/aheen/SAMKPUG_{04}_{nn}.mp3` | **partial and irregular** | 200 on `SAMKP_01_01_01_001/002/005`, `02_02_01_001`, `03_03_01_001`, `04_04_02_001`, `Samkp_06_01..03_001`, `SAMKPUG_04_01`, `SAMKPUG_04_05`. **Many neighbours 404.** |

**Reciters: UNKNOWN.** VHP states no pāṭha, śākhā-style or reciter name on the pages or in reachable
file metadata. The Rigveda section *does* model regional style as navigation branches — "Mandala Krama",
"Ashtaka Krama", "Maharashtra Tradition", "Kerela Tradition" — but with no per-file attribution.

**Sāmaveda caveat, stated honestly.** VHP hosts Kauthuma audio including an **Uha Gāna** subtree
(`Uha_Gaan/aheen/`), which is the scarcest material anywhere. But the file inventory is built
client-side by a radial-menu widget whose data is not in the served HTML, and naming is irregular.
Existence is confirmed; **completeness could not be enumerated. Do not assume full Kauthuma gāna
coverage — it looks partial.**

**Alignment substrate.** No timestamp files, but the layout gives **implicit alignment**: one media file
per sūkta for Rigveda and Atharvaveda, per adhyāya for Śukla YV, with the accented Devanāgarī text of
that passage rendered in the same page (`<div id="videotext">`). **This is the most useful alignment
substrate found in the entire survey.**

**VERDICT: `PERMISSION_REQUIRED`.** No mirroring. Direct linking **contested** — treat as gated until
IGNCA confirms.

### 4.5 IGNCA audio re-uploaded to archive.org by third parties — the rule in miniature

| Item | Content | Files | `licenseurl` |
|---|---|---|---|
| `sAmaveda-kauthuma-ignca` | Sāmaveda **Kauthuma**; naming `samkp_04_04_02_002.mp3` — **the same scheme as VHP** | 87 mp3, 8.23 h | **absent** |
| `sAmaveda-rANAyanIya-ignca` | Sāmaveda **Rāṇāyanīya** | 42 mp3, 9.16 h | **absent** |
| `kANva-saMhitA-audio-ignca` | Śukla YV **Kāṇva**; `mp3/SYKSCH_01.mp3`… | 40 mp3, 10.20 h | **absent** |

Verbatim descriptions: *"Courtsey IGNCA, Government of India"*; *"Courtsey : IGNCA and Indian
taxpayers."*

**VERDICT: `PERMISSION_REQUIRED`** — the rights holder is IGNCA. **This is the clearest illustration of
the governing rule in the whole survey: a third party mirroring IGNCA audio onto archive.org does not
create a licence.** The "courtesy IGNCA / Indian taxpayers" framing is a moral claim, not a grant, and
it is flatly contradicted by IGNCA's own written policy in §4.1. **These items are not safer than the
VHP originals — they are the same assets with the rights notice stripped off.** The Kauthuma item is
nonetheless the best *sizing* evidence available for VHP's Sāmaveda holdings.

---

## 5. archive.org — items and verdicts

Internet Archive asserts **no rights over uploader content**; per-item `licenseurl` is the only rights
signal. IA's own Terms state access is *"granted for scholarship and research purposes only"*
(https://archive.org/about/terms.php — obtainable only via search-index snippets, so cited as slightly
less firm; the operative point stands regardless).

### 5.1 `rgveda-auro-sriranga` — the highest-value asset in the survey

https://archive.org/details/rgveda-auro-sriranga

| Field | Value |
|---|---|
| Coverage | **Complete Rigveda Śākala Saṃhitā — 1028 files, one MP3 per sūkta** |
| Verification | Per-maṇḍala counts exactly match canon: 191, 43, 62, 58, 87, 75, 104, 103, 114, 191 = **1028** |
| Duration | **40.79 h** MP3, plus a parallel Ogg Vorbis set |
| Reciters | **Sri Shyama Sundara Sharma; Sri Satya Krishna Bhatta** |
| Tradition | **Śṛṅgeri pāṭham, Karnataka** — same recording sold commercially as *"Rigveda Samhita Complete 8 Astakas: Sringeri Patham (Audio DVD)"*, Sriranga Digital Software Technologies Pvt. Ltd., 2012 |
| Pāṭha | saṃhitā-pāṭha. A second file per sūkta (`01-001_2.mp3`) upstream may be padapāṭha — **unconfirmed**, `sri-aurobindo.co.in` unreachable from this environment |
| Rights metadata | `licenseurl` **absent**, `rights` **absent** ⇒ all rights reserved |
| Alignment | None shipped, but one file per sūkta = **implicit sūkta-level alignment for all 1028**. The `.afpk` files are IA's own Columbia Peaks fingerprints, not mantra alignment |

Verbatim item description:

> "ऋग्वेदः। शकल-संहिता।
> Reciters: Sri Shyama Sundara Sharma, Sri Satya Krishna Bhatta
> via aurobindo.ru, by Sriranga Technologies Pvt. Ltd. (2012)
> Sharing permitted by shrI Arjun Kashyap of Sriranga Technologies Pvt. Ltd. ( 20181023 -
> https://imgur.com/a/ftlYJ79 )"

**VERDICT: `PERMISSION_REQUIRED`.** There *is* permission evidence — a named individual at the
rights-holding company, dated, with a screenshot. **But it is not a licence:** no scope, no stated
permitted uses, no successor terms, and the evidence is an imgur screenshot. Under rule RIGHTS-4 that is
not sufficient for a permissive status; under `PERMISSION_GRANTED` semantics the grant document, grantor,
date **and scope** must be on file, and scope is missing. This is exactly the case where a written
licence should be obtained — see §9.

### 5.2 The Veda Prasāra Samithi / IISH family — where the PD Mark trap lives

Five sibling items, uploader `noahvincik@gmail.com`, creator *Veda Prasara Samithi*, dated **2020**:

| Item | Veda | Files | Hours | `licenseurl` |
|---|---|---|---|---|
| `RigvedaChanting` | Rigveda | 55 | 39.96 | **PD Mark 1.0** |
| `suklayajurveda_202107` | Śukla YV (**Kāṇva**) | 54 | 37.34 | **PD Mark 1.0** |
| `samaveda_202106` | Sāmaveda | 65 | 43.75 | **PD Mark 1.0** |
| `krishnayajurveda_202106` | Kṛṣṇa YV | 58 | 39.28 | **PD Mark 1.0** |
| `atharvaveda_202106` | Atharvaveda | 28 | 19.20 | **absent** |

Three hard findings:

- **The same recordings circulate under a second uploader with *different* rights metadata.**
  `IISHSamaVeda` (uploader `prvnbiz@gmail.com`, "Sama Veda - IISH Global") has 65 mp3 / 43.75 h with
  **byte-identical durations** to `samaveda_202106` (2648.04, 2355.42, 2602.93, 2646.42 …). Same for
  `IISHAKrishnaYajurVeda` vs `krishnayajurveda_202106`. **PD Mark on one, nothing on the other. The
  metadata is unreliable on its face.**
- **The fifth sibling has no licence at all** while four claim PD Mark — there is no coherent rights
  position being asserted.
- The 54-part Śukla item is **Kāṇva, not Mādhyandina** (confirmed against Veda Prasar Samiti's own
  archived recension table, "SHUKLA YAJUR VEDA .. Kanva Sakha"), and the master is **still sold as
  physical CDs**, so no re-uploader had standing to license it.

**VERDICT: `UNKNOWN`, default no-redistribution.** These are 2020 sound recordings; the recording
copyright is live; the mark was applied by a re-uploader who is not even the creator named in the item's
own metadata.

**This is the audio analogue of the Sāmaveda *text* finding in `docs/FOUR_VEDA_RIGHTS_MATRIX.md` §2.4:
multiple downstream copies agreeing is the same defect replicated, not corroboration. Here it is worse —
they do not even agree with each other.**

### 5.3 Other identifiers, with verdicts

| Identifier | Content | `licenseurl` | Verdict |
|---|---|---|---|
| `rig-veda_recitation_202009` | "Rigveda Parayana - Complete", 54 mp3 / 39.23 h; track names carry **coarse ranges**, e.g. `M1_S164 (partial) to M1_S186 (partial)` | absent | `UNKNOWN` |
| `atharvaved-tune` | "Atharvaveda Parayana - Complete", 15 mp3 / 9.98 h, **one file per kāṇḍa** | absent | `UNKNOWN` |
| `shukla-yajur-veda_recitation` | 80 mp3 / 36.96 h, per adhyāya but explicitly **`(Kanva)`** — not Mādhyandina | absent | `UNKNOWN` |
| `mAdhyandina-shAkhA-vedamu` | **Mādhyandina** — correct recension — but only 5 mp3 / 8.82 h in huge blocks `Adhyay(1-7)`…`(23-27)`; **stops at 27 of 40**. Mirrored from `vedamu.org`, which publishes no terms. Uploader is a third party; `credits` absent | absent | `UNKNOWN`, **incomplete** |
| `sama-veda-ghanam` | "IISH_Veda_Ghana_Patha_Samveda_Ghanam", 20 mp3 / 14.92 h, `VOL-01A` blocks | absent | `UNKNOWN` |
| `jaiminIya-sAma-gAna-paravastu-tradition-rAmAnuja` (+3 siblings) | **Jaiminīya sāmagāna**, 156 files, **one file per sāman**. Reciter *"Sriman U. Ve. Paravastu Samavedam Srinivasa Ramanuja Swamy (1915-2001) around 1974"*; tradition *"TN-AP-paravastu-tradition … from ALwarthirunagari"* | absent | `UNKNOWN`. **Jaiminīya, not Kauthuma** — out of recension scope, but the best-documented sāmagāna audio found |
| `VedicChantings` | Challakere Brothers, 54 mp3 / 4.16 h, selected sūktas only. Uploader states *"A few of their chantings are found in commercially produced CDs"* — a fan archive, not a rights grant | **CC BY-NC-ND 3.0** | ND ⇒ `REFERENCE_ONLY` |
| `ThiruvenkatamGroupKuwaitAcchidram-VedicChanting` | Ritual chanting, not saṃhitā coverage | CC BY 2.5 | `CC_BY` on paper; **low corpus value** |
| `SamavedaKouthumaSamhitaGana` | **Not audio** despite the title — 0 mp3; it is a book scan (PDF/EPUB/DjVu/JP2) | absent | not an audio source |

### 5.4 `lp_the-four-vedas-...` — the textbook prohibited item

https://archive.org/details/lp_the-four-vedas-the-oral-traditions-of-hymn_various

- 1969 vinyl, publisher **"Asch Mankind Series"**, 38 mp3 / 3.88 h, digitised from Boston Public
  Library vinyl.
- Collections include **`unlockedrecordings`** — IA's restricted-access vinyl programme, **not open
  content**. `licenseurl` **absent**.
- **© 1968/69 Asch Records**, verbatim in the OCR'd liner notes; now **Smithsonian Folkways**, still
  commercially sold. **Files return HTTP 200.**

**VERDICT: `PERMISSION_REQUIRED`. Absolutely no mirroring.**

**This is the canonical example for the rights matrix: playability is not permission.** The files stream
without obstruction. The recording is an in-copyright commercial product of a living publisher. Being in
an "unlocked" collection on a library site is a **hosting decision by the host, not a rights grant by
the owner.**

---

## 6. Academic and institutional sources

### 6.1 Smithsonian Folkways — *The Four Vedas* (the most scholarly publication found)

https://folkways.si.edu/the-four-vedas/poetry-world/album/smithsonian

- Catalog `FW04126` / `FE 4126`; Asch Mankind Series `AHM 4126`, 2 LPs, released **1968**. Sanskrit,
  India.
- **Credits:** *Frits Staal* — recorder, producer; *John Levy* — recorder. Liner notes by Staal.
- **Coverage: all four Vedas, selected passages only** — not saṃhitās. Track titles include
  `Ṛgveda - Vikṛti Recitation`, `White Yajurveda - Vikṛti Recitations`,
  `Sāmaveda - Opening Hymn (Jaiminīya School)`, `Sāmaveda - Gāna (Jaiminīya School)`,
  `Atharvaveda - Hymn for Peace`, `Ritual Recital of the Adhavaryu`.
  **This is the only source in the survey that explicitly labels vikṛti (permuted, non-saṃhitā)
  recitation.**
- **Reciters named — rare and valuable:** R. K. Subrahmanya Sastri; K. Balasubrahmaniam;
  N. Subrahmaniam Ghanapathikal; R. Narayana Sastri; E. J. Kumaraswami Dikshitar; Ekamra Sastri;
  Sivarama Sastri; Sastri Revashankar Bechabhai Trivedi; O. M. Kunhan; Vasudevan Nambudiripad;
  Matangarli Paramashvaran; Raman Nambudiri; Cherumukku Vaidikan Vallabhen Somayajipad; "Group of
  Nambudiri Yajurvedins"; Chittor Narayanan Nambudiripad; Muttathukkattu Itti Ravi Nambudiri.
  **Tradition: substantially Kerala Nambudiri, plus Tamil.**
- **Rights, verbatim:** `"© 2024 Smithsonian Institution"`. Page routes are labelled *"License
  Requests"*, *"Ordering Information"*, *"Wholesale Inquiries"*. **No open licence.**

**VERDICT: `PERMISSION_REQUIRED`.** A commercial nonprofit label with a **formal licensing desk** — the
correct source to approach for a *properly licensed* scholarly seed set. Small (3.88 h) but superbly
documented, covering all four Vedas plus vikṛti and Sāmaveda gāna. No timestamps, but track-level
segmentation is already semantically meaningful.

### 6.2 John Levy Archive — **University of Edinburgh, not Wesleyan**

https://library.ed.ac.uk/heritage-collections/collections-and-search/archives/archives/manuscripts-collections/john-levy-archive

**Correction recorded:** the John Levy collection is at **Edinburgh**. A "Levy at Wesleyan" premise was
investigated and **did not hold up**.

Verbatim:

> "The John Levy Archive is a primary ethnomusicological resource of international importance,
> consisting of nearly 700 original field recordings…"
> "Levy's field recordings … were made on a Nagra-S tape recorder between 1958-1972 in **India (223
> spools)**, Sri Lanka (55), Bhutan (48), Taiwan (101), China (81), South Korea (34), Iceland (35) and
> the UK (107)."
> "Following John Levy's early, tragic death his collection (**and the copyright on all original
> materials**) was bequeathed to the School of Scottish Studies…"

Footer: `"Unless explicitly stated otherwise, all material is copyright © The University of Edinburgh
2026."` The site offers a *"Digitisation and Permission form for AV material"*.

**Coverage:** 223 India spools, **unpublished, catalogue-only — no audio online.**

**VERDICT: `PERMISSION_REQUIRED`.** Paradoxically **the cleanest rights position of any source in the
survey — one identifiable owner, one permission form** — and the only realistic route to the
*unpublished* Levy Veda material. No alignment metadata; likely not even item-level indexing of Vedic
content.

### 6.3 Wesleyan World Music Archives — no asset

https://digitalcollections.wesleyan.edu/about/rights-re-use states its accessibility criteria and:
*"It is your responsibility to determine how you may use images and data that you download from our
digital collections."* **The statement is scoped to images**, and **no Wesleyan Veda audio was found
online.** **VERDICT: `UNKNOWN` / no asset.**

### 6.4 UNESCO — "Tradition of Vedic chanting" — citation value only

https://ich.unesco.org/en/RL/tradition-of-vedic-chanting-00062 · inscribed **2008**, proclaimed 2003,
nomination file No. 00062.

- **Credit lines, verbatim:** `© UNESCO` (video); `© Indira Ghandi National Centre for the Arts` (×3);
  `© Sangeet Natak Akademi, New Delhi, India` (×6).
- **No media file URLs are exposed** — the video sits behind a widget with no resolvable `src`.
- **UNESCO has no usable terms page:** https://www.unesco.org/en/terms-use returns, verbatim,
  `"coming soon..."`; `/en/legal` and `/en/disclaimer` return the generic shell with no legal text.

**VERDICT: `REFERENCE_ONLY` / `PERMISSION_REQUIRED`. Zero corpus value as audio.** Citation material
only — though its framing is substantively useful: *"only thirteen of the over one thousand Vedic
recitation branches have survived"*, with noted schools in Maharashtra, Kerala, Karnataka and Orissa.

### 6.5 Wikimedia Commons — the only mirrorable audio in the survey

| Field | Value |
|---|---|
| Reached via | https://sa.wikisource.org/wiki/सामवेदः ; files on `upload.wikimedia.org` |
| Veda / recension | **Sāmaveda / Kauthuma** |
| Scope | **474 distinct `.ogg`**, referenced from 444 Kauthuma Saṃhitā pages |
| Recitation type | Vedic recitation, sāman/gāna rendering |
| Reciters | **Not named per file.** Principal uploaders "Seet…" (317) and "Puranastudy" (157), Credit "Own work" |
| **Rights** | **458 files CC BY-SA 4.0 · 16 files CC0 · 0 missing a licence** |
| Verification method | **Per file**, via the Commons `imageinfo`/`extmetadata` API — *not* inferred from Commons' general terms |
| **Local mirroring** | **PERMITTED**, conditional on carrying attribution and share-alike **per file** |
| Alignment | **PAGE_LEVEL and SOURCE_PROVIDED** — each file is referenced from the specific Wikisource page (typically one daśati or one gāna) it belongs to |

Example verbatim, for `File:वासिष्ठम्(वृषाशोणो) Vasishtham.ogg` — UsageTerms *"Creative Commons
Attribution-Share Alike 4.0"*, LicenseUrl `https://creativecommons.org/licenses/by-sa/4.0`, Credit
*"Own work"*, 1,971,570 bytes.

**Three things make this artifact exceptional:**

1. **It is the only mirrorable Veda audio located anywhere**, across archive.org (199 items),
   institutional archives, gurukulam sites and streaming platforms.
2. **Its alignment is the source's own statement, not a derived claim.** Every other asset in this
   survey has *no* timing or cue artifact at all; here the file-to-passage mapping is inherent in how
   the files are referenced. That is a categorically stronger position than "we could segment this".
3. **It renders the gāna** — the dimension the Kauthuma text lacks entirely.

**Handling rule, non-negotiable:** licences are **per file and not uniform**. The 16 CC0 files and the
458 CC BY-SA files must retain their own terms and must never be flattened to a single collection
licence.

**Honest caveat:** recitation authority is **lower** than IGNCA's. Unnamed reciters, "Own work"
credit, no stated pāṭha or tradition beyond Kauthuma, and no institutional provenance. Rights are
better; authority is worse.

---

## 7. Community and gurukulam sites

| Source | Finding | Verdict |
|---|---|---|
| **sanskritdocuments.org** | Veda section is **text, not audio**; `/audio/` is devotional stotras and individual sūktas, largely external links. Verbatim: *"They are not to be copied or reposted for promotion of any website or individuals or for commercial purpose without permission."* And, decisively: *"It is of course compiled and available for everyone to use, so **no mirror copies are needed**."* | **`REFERENCE_ONLY`** — about as close to an explicit "do not mirror" as exists. Useful as a **discovery index**, not a source. |
| **vedavms.in** | **Not an audio host** — PDF/document project (jaṭā- and ghana-pāṭha *notation* in nine scripts), **Kṛṣṇa Yajurveda Taittirīya only**, outside our scope. Verbatim: *"We concentrate on only Krishna Yajur Veda Mantras…"*. Its only audio contribution is spreadsheets of **links to TTD** saṃhitā/pada/krama/jaṭā audio. **Its "Terms of Use" and "Privacy Policy" footer links are literally `<a href="#">` — there is no terms page.** | **`UNKNOWN`**, no redistribution. Its own line *"Our site never uses these material for any commercial purpose"* is an admission it is itself redistributing third-party material on a non-commercial rationale — **not a licence it can pass to us.** |
| **Tirumala Tirupati Devasthanams** | https://www.tirumala.org/ footer: `"Copyright © 2015-2026 Tirumala Tirupati Devasthanams(TTD), All Rights Reserved"` | **`PERMISSION_REQUIRED`** — explicit ARR. The most pāṭha-complete Kṛṣṇa YV audio chain terminates here. Addressable: TTD runs Veda institutions. |
| **vedicreserve.miu.edu** | *(Correct host — `vedicreserve.mum.edu` is dead; MUM renamed to MIU.)* Verbatim: *"Click on a branch of Vedic Literature to access the pdf files."* **Zero** `.mp3`/`.mp4`/`.wav` links. | **Not an audio source. Rule out permanently.** |
| **vedamantram.com** | Footer `"Copyright © 2026 Vedamantram"`, no terms page. **Reciter named:** shrī Mārepalli Nāga Veṅkaṭa Śāstri, Kothagudem, Telangana; *"He learned kR^iShNa yajurvEdam for 10 years in a gurukulam."* Kṛṣṇa YV, outside scope. "Free" means free of charge, not freely licensed. | **`UNKNOWN`**, no redistribution. |
| **shaivam.org** | Page title claims *"सम्पूर्ण सामगान कौथुम शाखा — Complete Sama Veda Kauthuma Shakha Parvas"*. JS app; served HTML exposes only a template route with empty metadata and no resolvable media URLs. No terms page found. | **`UNKNOWN`. Highest-value unresolved lead for Sāmaveda.** |
| **vedamu.org** | Site returned empty. Reportedly hosts *"full chanting of Samaveda Samhita (Kauthuma Shakha in both Gana and Rcha forms), and rare Ranayaniya Shakha in Gana form for all parts except Rahasya/Uhya Gana"* — **unverified.** Also the upstream of `mAdhyandina-shAkhA-vedamu`. | **`UNKNOWN`**, unverified. Second unresolved Sāmaveda lead. |

---

## 8. Cross-cutting findings

### 8.1 Streaming platforms — `EXTERNAL_REFERENCE_ONLY`

YouTube Terms of Service, "Permissions and Restrictions"
(https://www.youtube.com/static?template=terms), verbatim:

> "You are not allowed to: access, reproduce, download, distribute, transmit, broadcast, display, sell,
> license, alter, modify or otherwise use any part of the Service or any Content except: (a) as
> expressly authorized by the Service; or (b) with prior written permission from YouTube"
> "You may not use the Service to view or listen to Content other than for personal, non-commercial use"

**VERDICT for the entire class: `EXTERNAL_REFERENCE_ONLY`** — the strictest usable class. Store only a
URL or identifier; fetch and retain nothing, not even a verification snapshot.

**Two independent bars:** the platform ToS forbids downloading *regardless of the uploader's wishes*,
**and** the uploader is usually not the rights holder. **Even a CC-BY-marked video does not cure the
platform-level prohibition.** Note the second clause also constrains *embedded playback* in a
non-personal/commercial product — relevant to whoever owns VedaGraph's licensing posture.

Not enumerated item-by-item, deliberately: the class verdict is uniform.

### 8.2 Per-mantra alignment does not exist anywhere. Corpus-wide blocker.

Searched specifically for a licensed, timestamped Veda audio corpus. **There is none.**

- **`avinashvarna/audio_alignment`** (MIT, last pushed 2025-07-18) is a real text↔audio alignment
  project — corpora are Amarakosha, Ashtadhyayi, Kumārasambhava, Meghadūta, Raghuvaṃśa, **Rāmāyaṇa**,
  Tarkasaṅgraha, Yogasūtra. **No Veda corpus.** Its MIT licence covers code and alignment data, not
  third-party audio.
- **`sanskrit.github.io/projects/audio/veda-audio/`** — cited as "Tech details" by three of the best
  archive.org items — **is dead: 404.** The technical provenance documentation for the highest-value
  assets in this survey **has been lost.**
- **HuggingFace** datasets search for "veda": nothing relevant.
- **No `.vtt`, `.srt`, `.cue` or JSON cue sheet was found on any inspected item.**
- An authoritative track→mantra-range index for the 54-part master **exists but ships only with Veda
  Prasar Samiti's physical CDs.**

| Alignment quality | Sources |
|---|---|
| **Per-mantra timestamps** | **None exist anywhere, for any Veda, at any rights level.** |
| Implicit per-sūkta | `rgveda-auro-sriranga` (1028); VHP Rigveda `RIGSS` (1028); VHP Atharvaveda `Athss` (~748) |
| Implicit per-adhyāya / per-kāṇḍa | VHP Śukla YV `SYMS_CHAP` (40); `atharvaved-tune` (20); `shukla-yajur-veda_recitation` (Kāṇva) |
| Implicit per-sāman | `jaiminIya-sAma-gAna-*` (156) — Jaiminīya, not Kauthuma |
| Coarse ~45-min blocks | the entire Veda Prasāra Samithi / IISH family; `rig-veda_recitation_202009`; `mAdhyandina-shAkhA-vedamu` |

**If VedaGraph wants per-mantra alignment, VedaGraph must build it.** This is independent of the rights
problem and would remain even if every item were public domain. Recorded as finding **F5** in
`docs/reports/FOUR_VEDA_SNAPSHOT_PROVENANCE.md`.

### 8.3 Recitation type is UNVERIFIED — record it, do not assume

A **~3× duration anomaly** for the same text:

| Source | Duration | Per mantra (~2,086 mantras) |
|---|---|---|
| IISH / VPS Kāṇva | ~37 h | ≈ 64 s |
| vedamu Kāṇva | ~36 h | ≈ 64 s |
| IGNCA, same text | 10.2 h | ≈ 17.6 s |

Threefold is not performance variation. Plausible causes: repetition-heavy teaching style, additional
pāṭhas (krama/jaṭā/ghana), or interpolated Brāhmaṇa material.

**Record `recitation_type: UNVERIFIED` rather than assuming `samhita-patha`.** Mislabelling pāṭha type
would corrupt any alignment built on it — a case where the metadata is confidently wrong rather than
merely absent.

---

## 9. Recommended actions

1. **Write to IGNCA.** Single rights holder for the best-aligned, most canonically-organised material
   across **all four** target recensions, with a written permission channel. Ask for two things:
   (a) permission to mirror; (b) a ruling on the **direct contradiction between their Terms & Conditions
   and their Hyper linking Policy** (§4.2) — as things stand **even the link-only path is not clean.**
2. **Write to Sriranga Digital Software Technologies Pvt. Ltd.** about `rgveda-auro-sriranga`. A named,
   dated permission from Arjun Kashyap already exists; converting that screenshot into a real licence
   with stated scope would unlock a **complete, per-sūkta, 1028-file Rigveda Śākala corpus** with named
   reciters and a known pāṭham — the highest-value asset in this survey.
3. **Consider Smithsonian Folkways FW04126 as a licensed seed set.** 3.88 h, all four Vedas, named
   reciters, explicit vikṛti and Jaiminīya gāna, Staal's liner notes, and a real licensing desk. The
   only path found to properly licensed, scholarly-documented Veda audio.
4. **Two unresolved Sāmaveda leads need a manual browser session:** shaivam.org's claimed complete
   Kauthuma sāmagāna, and vedamu.org. Both defeated automated inspection. **Kauthuma gāna is the
   scarcest material in the entire landscape and VHP's own coverage of it looks partial.**
5. **Encode the two standing policies** from §2 and §3: PD Mark must never collapse into
   `PUBLIC_DOMAIN`, and ND is a hard blocker for alignment.
6. **Rule out permanently:** vedicreserve.miu.edu (PDF text only), vedavms.in (PDF notation, Kṛṣṇa YV
   only, dead terms links), UNESCO ICH (no extractable media), Wesleyan (no Veda audio).

---

## 10. Not delivered

Honest gaps, not silent omissions:

| Owed by | Item | Status |
|---|---|---|
| Agent B | **Sāmaveda audio inventory** | **Requested, not delivered.** Agent E researched it independently; §4.4 and §7 are the result. |
| Agent D | Atharvaveda audio inventory | Requested, not delivered. Covered independently in §4.4 and §5.3. |

**Why the Sāmaveda gap matters more than the others.** Sāmaveda is *defined* by its melodic **gāna**
realization, and the available Kauthuma text contains **arcika/verse text only, with no gāna
collections** (`docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.2). For this one Veda audio is **not
supplementary** — it carries content the text does not. A Sāmaveda built from text alone is
structurally incomplete, and no rights position on the text can compensate. The most likely sources —
VHP's partial Uha Gāna subtree, shaivam.org, vedamu.org — are respectively `PERMISSION_REQUIRED`,
`UNKNOWN` and `UNKNOWN`.

---

## 11. Verdict

| Rights class | Assessed sources | Mirrorable |
|---|---|---|
| `PUBLIC_DOMAIN` / `CC0` / `CC_BY` / `CC_BY_SA` for saṃhitā recitation | **0** | — |
| `CC_BY_NC_ND` (ND ⇒ derivatives forbidden) | 2 usable (`VedicChantings`; `shukla-yajurveda-kanva-samhita-pri`) | **No** |
| `PERMISSION_REQUIRED` | 8 — VHP; 3 IGNCA archive re-uploads; `rgveda-auro-sriranga`; Folkways; Edinburgh; TTD | **No** — but 4 have an *addressable* rights holder |
| `UNKNOWN`, default no-redistribution | 9+ — the PD-Mark family, `rig-veda_recitation_202009`, `atharvaved-tune`, `shukla-yajur-veda_recitation`, `mAdhyandina-shAkhA-vedamu`, `sama-veda-ghanam`, Jaiminīya items, vedavms, vedamantram, shaivam, vedamu | **No** |
| `REFERENCE_ONLY` | sanskritdocuments.org; UNESCO ICH; both ND items | **No** |
| `EXTERNAL_REFERENCE_ONLY` | the entire YouTube / streaming class | **No** |

| Question | Answer |
|---|---|
| **Files cleared for local mirroring** | **474** — all Sāmaveda, all Wikimedia Commons |
| **Vedas with a viable audio ingestion path** | **1 of 4** (Sāmaveda) |
| Vedas with authentic audio located but rights-restricted | **3** (Rigveda, Śukla YV, Atharvaveda) |
| Per-mantra alignment metadata found | **None, anywhere** |
| Best alignment available | Page-level, source-provided (Commons); per-sūkta implicit (VHP, `rgveda-auro-sriranga`) |

**Audio remains by a wide margin the least rights-clear layer in the corpus** — but it is no longer
uniformly blocked. One Veda out of four has a genuine, licence-backed, mirrorable audio path, and it is
the Veda for which audio matters most.

**Recommended posture, now split rather than uniform:**

- **Sāmaveda:** Commons is ingestible. Carry per-file licences; do not flatten. Treat VHP as the
  higher-authority reference link-out, subject to CORR-6 below.
- **Rigveda, Śukla Yajurveda, Atharvaveda:** discovery and citation only — record what exists, where it
  is, what it covers and who holds it, and link to it. Any change requires **written permission**, most
  plausibly from **IGNCA**, whose holdings are simultaneously the most authoritative, the best-aligned,
  and the only genuine Mādhyandina source.

**CORR-6 — even the link-only fallback is not clean for VHP.** Two live IGNCA pages contradict each
other on direct linking (§4.2). Since VHP is the reference source for **all four** Vedas, this needs
IGNCA in writing before any link-out UI is built on it.

**One closing observation.** In this domain the licence field and the rights reality are **inversely
correlated**. The unlicensed 62% are at least honestly silent. It is the *licensed* minority that is
dangerous — 47 NC-ND items that look usable but forbid the only operation we need, and 21 PD Mark items
that look free and are 2020 studio recordings tagged by people who never owned them. **A licence field
is the beginning of the rights investigation, not the end of it.**
