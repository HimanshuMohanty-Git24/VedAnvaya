# Atharvaveda-Saṃhitā (Śaunaka) — Source Research and Adjudication

**Work:** `VG:WORK:AV:SAU` · **Recension:** Śaunaka (AVŚ) · **Date:** 2026-09-07
**Machine-readable candidate matrix:** `data/source_registry/atharvaveda_sources.yaml`
**Pilot:** `docs/pilots/ATHARVAVEDA_PILOT.md`

Everything below was established by fetching. Nothing was taken from memory. Where a fact
could not be verified it is marked **UNVERIFIED** rather than smoothed over.

---

## 0. The three findings that matter most

1. **GRETIL does not serve the Śaunaka Atharvaveda as TEI.** It serves the *Paippalāda*
   recension as TEI and the Śaunaka recension only as two hand-formatted legacy HTML files
   in `1_sanskr/1_veda/1_sam/`. Anyone who assumes the Rigveda TEI pipeline generalises to
   AVŚ will find nothing to parse. Consequently the project's preferred format tier
   (structured XML/TEI) is **unavailable for AVŚ from any source**, and format rank 3
   (machine-readable text) is the best achievable today. No OCR was performed or needed.

2. **GRETIL's Rigveda CC BY-NC-SA licence does not extend to its Atharvaveda files, and
   GRETIL has no site-level licence at all.** The AVŚ files carry their own statement —
   *"THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS
   FOR SOURCE FILE."* — which is a disclaimer deferring to TITUS, not a licence.

3. **VedaWeb 2.0 now hosts both Atharvaveda recensions.** This overturns the working
   assumption that VedaWeb is Rigveda-only, and it delivered the single most useful artifact
   of this investigation: a **per-stanza Whitney & Lanman (1905) English translation**
   addressable by printed citation.

4. **The root of the Sanskrit provenance chain is Orlandi 1991, and it is still in
   copyright.** This corrects an earlier conclusion of my own, and it is the most consequential
   correction in this report. GRETIL, TITUS and VedaWeb's AVŚ Sanskrit layer are indeed *one*
   licensing dependency rather than three — but a single TITUS permission does **not** unlock
   them, because behind TITUS sits *Gli inni dell' Atharvaveda (Saunaka)*, trasliterazione a
   cura di Chatia Orlandi, Pisa: Giardini, 1991 — a modern scholarly transliteration still in
   copyright, collated with the public-domain Roth/Whitney 1856. See §10.

---

## 1. Candidate sources investigated

Eleven candidates: eight investigated as usable sources, three recorded as explicit
non-candidates. Full attribute set and verbatim rights text per candidate are in
`data/source_registry/atharvaveda_sources.yaml`; this is the summary.

| source_id | Role | Format (rank) | Accents | Complete | Granularity | Rights (recommended) | Selected |
|---|---|---|---|---|---|---|---|
| `GRETIL_AVS` | primary Sanskrit | legacy HTML (3) | **YES** (Latin U+0301/U+0300) | 20/20 kāṇḍas | per-mantra + per-pada | `REFERENCE_ONLY` | **YES** |
| `VEDAWEB_AVS` | English translation | JSON REST (3) | n/a (English) | 4,881/5,842; **no kāṇḍa 20** | per-stanza | `PUBLIC_DOMAIN` | **YES** |
| `TITUS_AVS` | upstream + parallel | frameset HTML (3) | YES (U+0301) | 20/20 | per-halfverse | `REFERENCE_ONLY` | no — rights |
| `WIKISOURCE_AVS_SA` | parallel Sanskrit | wikitext + API (2) | **NO** | 20/20, messy titles | per-sūkta | `CC_BY_SA` | no — unaccented |
| `WIKISOURCE_WHITNEY_AV` | English translation | wikitext + API (2) | n/a | **no Book XX** | per-hymn | `PUBLIC_DOMAIN` | no — granularity |
| `WIKISOURCE_GRIFFITH_AV` | English translation | wikitext + API (2) | n/a | 18/731 hymns (2.5%) | per-hymn | `PUBLIC_DOMAIN` | no — abandoned stub |
| `VHP_AVS` | Sanskrit + audio | WordPress HTML (2) | **YES** (U+0951/U+0952) | ~734/731 | per-sūkta | `PERMISSION_REQUIRED` | no — rights |
| `THEVYASA_AVS` | parallel Sanskrit | WordPress HTML (2) | **YES** (U+0951/U+0952) | 20/20 across pages | kāṇḍa-range pages | `UNKNOWN` | no — rights |
| `GRETIL_AVP` | — | TEI XML | — | — | — | — | **non-candidate: Paippalāda** |
| `VEDAWEB_AVP` | — | JSON | — | — | — | — | **non-candidate: Paippalāda** |
| `GRETIL_AV_UNSPECIFIED` | — | none available | — | — | — | — | **non-candidate: no artifact, recension unstated** |

### Verbatim rights evidence

**`GRETIL_AVS` — artifact level** (extracted programmatically from the snapshot preamble by
`GretilAVSAdapter.extract_header_metadata().licence_statement_verbatim`):

> THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY!
> COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE.

**`GRETIL_AVS` — site level:** **NONE EXISTS.** `gretil.html` (1,033,721 bytes fetched)
contains no occurrence of *licence*, *license*, *copyright*, *terms of use*,
*Creative Commons* or *public domain* anywhere. `https://gretil.sub.uni-goettingen.de/` and
`/gretil.htm` are 59-byte meta-refresh redirects. There are no about/terms/legal/impressum
links. GRETIL's own introduction describes it as a re-host: *"providing the contributions of
varying sources and quality in an appropriately normalized way"*. **No artifact-vs-site
conflict, because there is no site statement to conflict with.**

**`TITUS_AVS` — artifact level** (from `.../ved/av/avs/avs.htm` and each `avsNNN.htm` footer):

> This text is part of the TITUS edition of Atharva-Veda-Samhita (Saunaka).
> Copyright TITUS Project, Frankfurt a/M, 4.3.2015. No parts of this document may be
> republished in any form without prior permission by the copyright holder.

**`TITUS_AVS` — site level** (`http://titus.uni-frankfurt.de/texte/textex.htm`, section
"Notice on copyright and etiquette"):

> All texts that can be downloaded via http from the TITUS server can be used freely for
> scholarly purposes, provided that they are quoted as sources and the name(s) of the
> editor(s) and the date of last changes are indicated in publications. The texts must not
> be used for any kind of commercial usage. Downloading of some of the texts is restricted
> to members of the TITUS project.

**Artifact-vs-site conflict: YES, AND MATERIAL.** The site grants free scholarly use with
attribution; the artifact forbids republication *in any form* without prior permission. A
redistributed derived corpus cannot satisfy both. The stricter artifact-level statement
governs, per this project's rule.

**One thing worth flagging for whoever writes to TITUS.** The catalogue labels a plain-text
AVŚ version *"Plain text retrieval (TITUS Members only)"* at
`titus.fkidg1.uni-frankfurt.de/private/texte/indica/vedica/av/av.txt`. That URL currently
returns HTTP 200 with no authentication — the access control is not enforced. It sits under
`/private/`, which is `Disallow:`-ed in `robots.txt` on both TITUS hosts. **VedaGraph did not
ingest it and must not.** An unenforced restriction is still a restriction.

**`VEDAWEB_AVS` — artifact level:** the API returns `"license": null` and
`"licenseUrl": null`, and the translation resource carries **no** restrictive statement,
only a citation request. **The contrast is the point:** VedaWeb's AVŚ *Sanskrit* resource
(`696f331f6f50da42570ad028`) reproduces verbatim in its own description:

> "Copyright TITUS Project, Frankfurt a/M, 4.3.2015. No parts of this document may be
> republished in any form without prior permission by the copyright holder."

That clause attaches to the Sanskrit text. This build uses only the translation resource.

**`VEDAWEB_AVS` — site level** (`systemSiteNotice`, enUS, via `GET /api/platform`):

> Individual resources provide their own citation guidelines, which can be found in the
> resource information. Please use these for citing specific data.

**`VHP_AVS` — site level** (`https://vedicheritage.gov.in/copyright-policy/`, full policy
body):

> The contents of this website can not be reproduced partially or fully, without written
> permission from Indira Gandhi National Center for the Arts or the contributor (with
> intimate to IGNCA). If referred to as a part of another publication, the source must be
> appropriately acknowledged. The contents of this website can not be used in any misleading
> or objectionable context.

There is **no** open-government-data licence, **no** GODL-India reference, **no** Creative
Commons licence and **no** personal-use carve-out anywhere on the Terms & Conditions or
Copyright Policy pages. `robots.txt` disallows only `/wp-admin/`, `/wp-includes/`,
`/wp-content/plugins/` and one intro video — but **robots.txt permitting a crawl does not
grant reproduction rights.**

**A live self-contradiction on the same site, recorded rather than resolved:**
`https://vedicheritage.gov.in/terms-conditions/` says *"We do not object to linking directly
to the information that is hosted on this portal and no prior permission is required for the
same."* `https://vedicheritage.gov.in/hyper-linking-policy/` says *"Prior permission is
required before hyperlinks are directed from any website/portal to this site."* Both footers
are dated "Information Update on August 27, 2026". (`/hyperlinking-policy/` without the
hyphen is a 404.) Framing is separately prohibited. If linking matters, get it in writing.

**`WIKISOURCE_*` — site level** (raw `<li id="footer-info-copyright">`):

> Text is available under the Creative Commons Attribution-ShareAlike License; additional
> terms may apply. By using this site, you agree to the Terms of Use and Privacy Policy.

The visible string omits the version; the `href` resolves it to CC BY-SA **4.0**.
**GFDL could not be confirmed** — the strings `GFDL` and `Free Documentation` are absent from
the rendered footers fetched. Treat "CC BY-SA + GFDL" as historically true but **UNVERIFIED**
today.

**`WIKISOURCE_WHITNEY_AV` — artifact level:** the root wikitext carries `{{PD/US|1941}}`,
which renders:

> …public domain in the United States because it was published before January 1, 1931. The
> longest-living author of this work died in 1941, so this work is in the public domain in
> countries and areas where the copyright term is the author's life plus 84 years or less.

**This is a layering, not a conflict:** the 1905 work is public domain; CC BY-SA 4.0 covers
Wikisource contributors' own markup and annotation. Citing the PD source alone is *not*
sufficient if the wiki markup is reused verbatim. No `oldid` was pinned because this source
was not ingested — pinned revision ids must be captured at ingestion time, not retro-fitted.

**`THEVYASA_AVS` — rights: NONE FOUND.** No occurrence of copyright, licence, permission or
terms in the rendered page. **UNKNOWN is not permissive.**

---

## 2. Selections and why

**Primary Sanskrit — `GRETIL_AVS` accented (`avs_acu.htm`).** The only accented, complete,
machine-readable, per-mantra-addressable AVŚ text whose recension can be proved from the
artifact. Rejected alternatives and the reason each lost:

* TITUS — same text, better granularity (halfverse), but harder rights (non-commercial +
  no republication) and far noisier markup. Rejected on rights, not quality.
* VedaWeb's AVŚ Sanskrit layer — cleanest machine-readability of all (1 MB JSON, one
  anonymous GET), but it explicitly re-serves the TITUS no-republication clause, so it is
  *no better* rights-wise while adding a dependency on someone else's editorial revisions.
* sa.wikisource — best licence (CC BY-SA 4.0) but **unaccented**, which is disqualifying.
* vedicheritage.gov.in — best *content* (accented Devanagari + audio) but reproduction is
  explicitly forbidden.

**Parallel Sanskrit — `GRETIL_AVS` unaccented (`avs___u.htm`).** Used, but with an honest
label: it is **not an independent witness**. See §5.

**English translation — `VEDAWEB_AVS`, Whitney & Lanman 1905, per stanza.** Public domain,
per-stanza, and addressable by *printed* citation via location aliases, which is what
mantra-level alignment requires. English Wikisource carries the same translation but only
per-hymn and **without Book XX**. Griffith on Wikisource is a 2.5%-complete abandoned stub.

**Kāṇḍa 20 is translatable after all — by Griffith, and it is mirrorable.** This corrects
the initial read. Ralph T. H. Griffith, *The Hymns of the Atharvaveda* (1895–96; 2nd ed.
E. J. Lazarus, Benares, Vol. I books I–IX 1916, Vol. II books X–XX + "The Kuntapa Section"
1917) is **the only complete AVŚ translation**, and unlike Whitney it covers book XX.

* **Addressability: per-verse.** `sacred-texts.com/hin/av/av{BB}{HHH}.htm` with per-verse
  anchors `<a name="an_0100101">` = book 01 / hymn 001 / verse 01. Verified via the Wayback
  Machine (the live host returns HTTP 403 to non-browser clients).
* **Numbering: Berlin/Roth–Whitney, the same spine as the primary artifact.** Verified: book
  index hymn-link counts are bk 1 = 35, bk 7 = **118** (not the Bombay 123), bk 11 = 10,
  bk 15 = 18, bk 20 = 143. Griffith's printed book VII also ends at HYMN CXVIII. So
  GRETIL, Whitney and Griffith are 1:1 alignable — **this is the single most load-bearing
  alignment fact in the whole investigation.**
* **Rights: mirrorable.** `sacred-texts.com/cnote.htm`, verbatim: *"Public domain files from
  this site can be used for **any** purposes… Create derivative works… **without asking
  anyone (including sacred-texts) for permission**."* The bulk dump
  `sacred-texts.com/hin/av/av.txt.gz` states in its own header: *"Scanned, proofed and
  formatted at sacred-texts.com, April 2007, by John Bruno Hare. This text is in the public
  domain because it was published prior to 1923."*
  **Two carve-outs matter:** sacred-texts' *own* index pages, sub-section graphics and
  descriptive material are copyright J. B. Hare and *"may not be reproduced in any form"* —
  so the per-hymn body text is usable but `avbook01.htm` etc. are not. And whether the AV
  file is on their commercial-licensing Bibliography list is **UNVERIFIED**.
* **Defects, audited rather than assumed.** The bulk dump yields 721 of 731 hymns and 5,602
  of 5,839 verses. Of the shortfall: **AVŚ 2.20–2.23 are genuinely missing**, with the
  file's own editorial note *"It appears that hymns 20-23 were omitted--JBH"*; the remaining
  "gaps" are **anchor-ID corruption, not missing text** (AVŚ 6.7 is present under the
  correct header but anchored `[0700601]`, i.e. book 07 hymn 006; same class of error near
  7.3 and 20.120). **The human-readable headers are trustworthy; the machine anchors are not
  in spots.** Separately, Griffith printed some passages in Latin in an appendix rather than
  English — AVŚ 1.11.3–6, 4.4.3–9, 6.72, 6.101, 20.126.16–17 and 20.136 — and none of that
  appendix material is in the dump.

**Recommendation: use both.** Whitney (VedaWeb, per-stanza, books I–XIX) as the scholarly
translation, Griffith (sacred-texts, per-verse, all 20 books) for coverage — recorded as two
independent `Translation` records per passage, never merged.

**Maurice Bloomfield, SBE 42 (1897) — confirmed PARTIAL, and quantified twice.** Its own
sacred-texts page says verbatim it is *"an **anthology of representative hymns**… grouped
thematically, so the hymns are not in numeric order"*. Coverage measured two independent
ways — parsing the sacred-texts index, and parsing the printed table of contents in the
archive.org OCR — **both give 208 distinct (book, hymn) pairs**, i.e. roughly 32–35% of AVŚ
hymns. **Books 14, 15, 16, 17 and 18 have zero coverage.** A third cross-check agrees: of
Whitney's 580 machine-detected "Translated:" bibliography paragraphs, 187 cite Bloomfield
against 551 citing Griffith. Also note the sacred-texts etext *"leave[s] out most of the
introduction and all of the footnotes"* — for the apparatus the archive.org scan
(`hymnsofatharvave00bloouoft`, `NOT_IN_COPYRIGHT`) is required.

**Devi Chand and Tulsi Ram Sharma: `REFERENCE_ONLY`.** Both are complete modern
translations, both on archive.org with CC0 asserted by third-party digitisers rather than by
rightsholders. Tulsi Ram is dated 2013. Not usable.

**Hindi translation — NOTHING RIGHTS-CLEAR AND MACHINE-READABLE EXISTS.** Stated plainly
rather than fudged, and now checked properly rather than assumed:

* **Kṣemakaraṇadāsa Trivedī, *Atharvaveda Bhāṣya*** is the best candidate and it still fails.
  Complete coverage of all 20 kāṇḍas across `atharvaveda-bhashyam-1` … `-5` on archive.org,
  with an excellent structure (mūla mantra → padapāṭha → Sanskrit gloss → Hindi anvaya →
  bhāvārtha). Trivedī's own dates are printed on the scan — *"निधन : १३ फरवरी १९३९"*,
  **died 13 February 1939** — so his authorship is PD in India (life+60, from 2000) and in
  the US. **But:** the scanned edition is the *dvitīya saṃskaraṇa* **edited by
  Dr. Prajñādevī**, whose editorial layer is plausibly still in copyright (**UNVERIFIED** —
  no legible edition year); the book prints **"[ सर्वाधिकार प्रकाशकाधीन ]"** = *"All rights
  reserved by the publisher"*; and the page-level *"CC-0"* stamp is asserted by the
  digitising library, not the publisher. **Machine-readability also fails outright** — the
  Devanagari OCR is badly corrupted (broken conjuncts, garbled padapāṭha).
* **Śrīrām Śarmā Ācārya (Gayatri Pariwar)** is rights-blocked. Thirteen archive.org items
  carry CC0 asserted by third-party uploaders, but the rightsholder's own site states
  verbatim: **"Copyright © 2026 SRI VEDMATA GAYATRI TRUST (TMD). All rights reserved."**
  The widely repeated claim that Ācārya renounced copyright comes from third-party sites and
  is contradicted by the primary statement. Died 1990 → India copyright to 2050.
* **Hindi Wikisource and Sanskrit Wikisource: zero hits** for अथर्ववेद (API-checked).
  **sanskritdocuments.org: none.** **vedicheritage.gov.in:** Hindi *essays* only, no
  translation of the Saṃhitā. **vedicscriptures.in:** login-walled (302 to `/user/login`).
  Harisharan Siddhantalankar, Viśvanātha (2024) and the Nag Publishers reprint are all
  modern and in copyright. Vishva Bandhu's 1962 edition is access-blocked on archive.org
  (*"under review by the Million Books Project"*).

**Recommendation: no Hindi layer for AVŚ.** The only viable path would be a fresh Devanagari
re-OCR of the Trivedī scans, accepting an unresolved publisher-versus-digitiser rights
conflict and an unquantified editorial layer. That needs a rights opinion, not an engineer.

## 3. Structure and computed counts

Full table per kāṇḍa: `docs/pilots/ATHARVAVEDA_PILOT.md` §3 and
`docs/manifests/atharvaveda_pilot_structure_v1.json` (machine-readable).

**Hierarchy confirmed from the selected source records:** every locator is
`(AVŚ_{kāṇḍa},{sūkta}.{mantra}{pada})`, i.e. Kāṇḍa → Sūkta → Mantra with an explicit
sub-mantra pada level. This matches the `identity_status: FINAL` hierarchy in `works.yaml`
exactly; nothing needed redesigning.

**Computed from the snapshot — not from any reference work:**

* **20 kāṇḍas**
* **731 sūktas** — per kāṇḍa: 35, 36, 31, 40, 31, 142, 118, 10, 10, 10, 10, 5, 4, 2, 18, 9,
  1, 4, 72, 143. Sūkta numbering is 1..N **contiguous in all twenty books** (zero gaps).
* **5,839 distinct mantras** (5,843 parsed units; the difference is the four locator
  collisions)
* **11,395 padas**
* 220 anuvāka `{N}` markers, but in only **11 of 20** kāṇḍas
* 702 single-pada units, concentrated in the prose books (kāṇḍa 15: 98/141; 16: 66/93)
* 261 units carrying an alternate (Vishva Bandhu) citation

### Reconciliation — and the honest answer

**The artifact states no counts.** Verified programmatically:
`extract_header_metadata().stated_total_counts` returns the empty tuple. So for this artifact
there is **no source-stated total to reconcile against**, and that absence is itself recorded
in the build provenance rather than quietly replaced by a textbook figure.

Against external figures, **four different counts exist in one textual lineage**:

| Witness | Verse count | Notes |
|---|---:|---|
| GRETIL/TITUS legacy HTML (this pilot's primary) | **5,839** distinct / 5,843 units | computed |
| VedaWeb, "revision of TITUS verse count" | **5,842** stanza locations | VedaWeb's own documented edit |
| TITUS restricted plain text | **5,919** verse markers | not ingested (robots-disallowed) |
| reference literature, commonly cited | **~5,977** | not a source, a citation |

All of the first three descend from the same Petr/Vavroušek data entry of Roth-Whitney +
Orlandi. **The differences are real editorial decisions, not parser noise, and none has been
reconciled here.** Sūktas: computed 731 against the commonly cited 730 — a genuine +1
divergence with no spurious or missing hymn to find, since every book is internally
contiguous. The divergence lives in *which edition is being counted*.

Nothing was renumbered, inserted or dropped to make any total match.

### Alternate citation systems, captured as data

The artifact embeds the Vishva Bandhu (Hoshiarpur 1960–64) numbering in brackets, per its own
preamble. Three bracket positions occur and each means something different; each is emitted
as a distinct non-canonical `Citation` under system `AVS_VISHVA_BANDHU_1960`:

| Locator | Meaning | Emitted label |
|---|---|---|
| `11,4[6].1a` | the **sūkta** differs | `AVS 11.6.1` |
| `11,3.32[4.1]a` | sūkta **and** mantra differ | `AVS 11.4.1` |
| `15,2.1[2.1]a`…`[2.8]g` | one Roth/Whitney verse = **eight** Vishva Bandhu verses | `AVS 15.2.1-8` |
| `20,96.22[-]a` | explicit **absence** in the other edition | none — a `SourceAssertion` instead |

Whitney's translation numbering is captured separately and independently, through VedaWeb's
location aliases, so the two systems never have to be assumed equal.

### Books 19 and 20, handled explicitly

* **Kāṇḍa 19** (72 sūktas, 453 units, 69 single-pada) — sampled (19.1) and parses cleanly.
* **Kāṇḍa 20** (143 sūktas, 959 units — the largest book) — sampled twice, deliberately:
  20.96 for the two-verses-one-number collision, and 20.127 for a *kuntāpa* hymn.
  **No deduplication against the Rigveda was performed and no AVŚ mantra is sourced from the
  Rigveda.** A Rigvedic parallel is a candidate for the derived parallels layer
  (`src/vedagraph/lexical/parallels.py`) only. This is recorded in the build as a
  `CROSS_WORK_PARALLEL_POLICY` assertion so the decision is auditable, not just intended.
* **Kāṇḍa 20 has no *Whitney* translation** — 958 of 5,839 mantras (16.4%) — because
  Whitney deliberately excluded it (*"that is in the main a pure mass of excerpts from the
  Rig-Veda; it stands in no conceivable relation to the rest of the Atharva-Veda"*).
  **Griffith does cover it**, per-verse and mirrorably (§2), so the gap is closable; it is
  simply not closed in this release.

---

## 4. Recension verification

GRETIL hosts **both** recensions as different files, so this had to be proved, not assumed.

`assert_saunaka_recension()` runs before every parse and requires **two independent witnesses
inside the artifact**:

1. **Document title** must contain both *atharvaveda* and *saunaka* and must not contain
   *paippalada*. Actual: `Atharvaveda-Samhita, Saunaka recension, ACCENTED TEXT`.
2. **Body locators** — all 11,395 are prefixed `AVŚ_` with the palatal sibilant. The
   recension marker is in the data per verse, not only in a header that could belong to a
   swapped file.

A snapshot failing either check raises `RecensionMismatchError` rather than being ingested.
The Paippalāda TEI file (`corpustei/sa_paippalAdasaMhitA.xml`) and VedaWeb's `avp` text are
recorded as **explicit non-candidates** with the reason, so a future reader cannot mistake
either for a parallel of AVŚ. A cross-*recension* comparison layer would be a legitimate
separate project; conflation would not.

### Per-artifact accent status — established, never assumed

| Artifact | Declares | Verified | Encoding |
|---|---|---|---|
| `avs_acu.htm` | `ACCENTED TEXT` | **5,843/5,843** accent-positive | combining **Latin**: U+0301 udātta, U+0300 svarita |
| `avs___u.htm` | `UNACCENTED TEXT` | **0/5,843** | — |
| TITUS AVŚ HTML | — | accented | U+0301 only; U+02B0 for aspirates |
| VedaWeb AVŚ Sanskrit | — | accented | ISO 15919 normalised (`ṃ`→`ṁ`); `l̥` disambiguated |
| sa.wikisource | — | **UNACCENTED** | only U+094D VIRAMA present |
| vedicheritage.gov.in | — | accented | **Devanagari** U+0951/U+0952 |
| thevyasa.in | "सस्वरा" | accented | Devanagari U+0951 ×9,204, U+0952 ×12,305 |

Two things follow that a Rigveda-shaped assumption would get wrong:

* **AVŚ accentuation really is inconsistently preserved across electronic editions** — the
  best-licensed source (sa.wikisource) has none at all.
* **The primary artifact's accents are Latin combining marks, not Devanagari svaras.** There
  is no U+0951/U+0952 and no Vedic Extensions codepoint anywhere in it. They stack on letters
  themselves built from combining marks (vocalic r = `r` + U+0325), so *long vocalic r with
  udātta* is four codepoints in one grapheme. Pluti is an inline digit `3`.

---

## 5. Cross-source comparison (D5)

`compare_readings()` from `src/vedagraph/compare/text.py`, 153 sampled mantras, accented vs
unaccented artifact:

| `TextComparisonCategory` | Count | Share |
|---|---:|---:|
| `ACCENT_ONLY` | **153** | 100.0% |
| all other categories | 0 | 0% |

**This is weaker evidence than a clean 100% looks, and that is the finding.** A perfect
`ACCENT_ONLY` distribution combined with perfect 1:1 locator alignment (both artifacts yield
5,843 units in identical order) shows the unaccented file is a **mechanical accent-strip of
the accented file**, not an independent witness. Corroboration: the unaccented file's own
preamble reads `WḌ. Whitney` where the accented reads `W.D. Whitney` — the accent-removal
transform corrupted `.D` into `Ḍ` in the header prose.

So this validates the comparison machinery and the accent handling **on real AVŚ bytes**. It
does **not** corroborate the AVŚ text across editions. That needs a genuinely independent
edition, and the two candidates are both rights-blocked (TITUS, vedicheritage.gov.in).

Genuine cross-source corroboration did arrive from an unexpected direction: **VedaWeb's
translation-layer numbering independently confirms the GRETIL 13.4 defect** — see
`docs/pilots/ATHARVAVEDA_PILOT.md` §9.

**Tooling limitation, stated:** `compare.run.run_comparison()` could not be used. Its
`TextComparisonConfig` has a required `mandala: int` field and `load_readings()` dispatches
only on `source_id in {GRETIL, VEDAWEB}` — it is Rigveda-shaped. Extending it means editing
shared comparison infrastructure this agent does not own. `compare_readings()`, `classify()`,
`VersionReading` and the `TextComparison` model were reused **unchanged**.

---

## 6. Traditional metadata — availability and a safe resolution method

**What exists, and what does not.** The Atharvaveda names its own apparatus. From
**Atharvavedaparisista 49 (Caranavyuha) 4.8**, verbatim from GRETIL:

> `laksanagrantha bhavanti | caturadhyayika pratisakhyam pancapatalika dantyosthavidhir brhatsarvanukramani ceti ||`

So: Saunakiya Caturadhyayika (Pratisakhya), **Pancapatalika**, Dantyosthavidhi,
**Brhatsarvanukramani**. Here is what is actually obtainable.

| Apparatus | Machine-readable? | Rights | Verdict |
|---|---|---|---|
| **Whitney's per-hymn Anukramani brackets, via English Wikisource** | **YES — 588 hymn pages, ProofreadPage `Progress=V` (Validated), correct IAST** | **`PUBLIC_DOMAIN`** (`{{PD/US|1941}}`) | * **the only PD, machine-extractable, SOURCED per-hymn rsi/devata/chandas source for AVS** — see 6.2 |
| **Brhatsarvanukramani** (the AV's own index) | **NO e-text exists anywhere** — verified absent from the whole GRETIL index and from TITUS | 1922 Lahore ed. is PD (`archive.org/details/pIEJ_brihat-sarva-anukramanika-...`, CC0) | print-only; Devanagari OCR badly corrupted |
| **Pancapatalika** (Whitney's "Old Anukr.") | **NO e-text exists** | only accessible ed. is 1990 Ajmer -> **in copyright**; the CC0 on the scan is an uploader assertion | unusable |
| **Saunakiya Caturadhyayika** (AV Pratisakhya) | **NO** — GRETIL's Pratisakhya section holds only Nirukta and Rgvidhana | — | print-only |
| **Vishva Bandhu, *Atharvaveda Rsi-Devata-Chando-Anukramanika*, Hoshiarpur 1970** | yes, as a scan | **IN COPYRIGHT — the book prints "sarvadhikarah suraksitah" ("All rights reserved"); Vishva Bandhu d. 1973 -> India life+60 to 2034, URAA-restored in the US** | **the only true per-mantra source, and it is legally off-limits. DO NOT MIRROR.** The CC0 on archive.org is asserted by the digitiser, not the rightsholder. |
| **Kausika Sutra, Vaitana Sutra, Kausikapaddhati, Gopatha-Brahmana, Atharvavedaparisistas** | **YES — GRETIL TEI, all HTTP 200** | **`CC_BY_NC_SA`** — every file declares `licence target="https://creativecommons.org/licenses/by-nc-sa/4.0/"` | usable non-commercially; **ritual application, NOT per-mantra rsi/devata/chandas** |
| vedicheritage.gov.in per-sukta rsi/devata/metre | HTML only, scrapable | **`PERMISSION_REQUIRED`** | rights-blocked |
| sa.wikisource per-sukta header notes + index pages | yes, deterministically | **`CC_BY_SA`**, no PD template anywhere | high coverage but **UNSOURCED** — 6.1 |

**The pilot emits ZERO `TraditionalMetadataAssertion` records**, with an explicit
`TRADITIONAL_METADATA_UNAVAILABLE` assertion recording the absence and its reason. That
decision was made before the Wikisource-Whitney route was verified. It remains correct for
*this* release, but 6.2 now names a concrete, sourced, public-domain route for the next one.

### 6.0 What the Atharvavedaparisistas actually contain (checked, because it was claimed)

`gretil/corpustei/sa_atharvavedapariziSTas.xml` — HTTP 200, 526,680 bytes, 80 parisista
sections, 3,124 numbered references. Source edition **Bolling and von Negelein, Leipzig
1909-1910** -> US public domain. Its GRETIL TEI header carries, verbatim:

> "This e-text was provided to GRETIL in good faith that no copyright rights have been
> infringed. If anyone wishes to assert copyright over this file, please contact the GRETIL
> management ... The file will be immediately removed pending resolution of the claim."
> "Distributed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0
> International License."

**It does NOT map rsi/devata/chandas per mantra.** Keyword counts over the whole
416,978-character text: `rsi` 16, `devat` 62, `chandas` 5, `anukram` 4. It is a ritual, omen
and astrological appendix corpus. Two sections *are* real traditional metadata:
**#32 `ganamala`**, the ritual hymn-group lists (*santigana, krtyagana, catanagana,
takmanasanagana, ayusyagana* ...) — i.e. ritual-function tagging of AVS hymns, **but given
by pratika (incipit) only, never by number**, so resolving them needs a pratika index that
does not exist in machine-readable form; and **#49 `caranavyuha`**, which lists the nine AV
sakhas and the apparatus quoted above.

Note also that this file's rights rest on GRETIL's "good faith" clause rather than on a
positive grant, which is a real removal risk for anything built on it.

### 6.1 The sa.wikisource lead was verified in full. Verdict: deterministic, high-coverage, **unsourced**

This was the most promising route, so it was checked properly: **all 773 `सूक्तम्`-bearing
subpages** of `अथर्ववेदः/` were fetched via the MediaWiki API, plus both index pages, the
kāṇḍa pages, and the talk pages.

**Coverage is genuinely good.** Of 756 real content pages (849 subpages, 769 canonical-pattern,
13 of those redirects, 4 off-pattern junk):

| field | pages | coverage |
|---|---:|---:|
| ṛṣi (own `author` parameter) | 753 | 99.6% |
| `notes` present | 743 | 98.3% |
| devatā (marked `दे.`, consistent on 737/737) | 734 | 97.1% |
| chandas token present | 690 | 91.3% |
| mantra-range-scoped values | 43 ṛṣi / 127 devatā / 89 chandas | — |

**And it is genuinely parseable.** `दे.` is a perfectly consistent devatā marker; the
range-qualifier grammar is regular; `author` normalises from 264 raw surface strings to a
small ṛṣi set by rule. The existing `MetadataScope.MANTRA_RANGE` already models the
`१-५ पूरणः, ६-१० यक्ष्मनाशनः` scoping the source itself states. **No LLM inference is
needed.** Books 15, 16 and 20 are *not* empty, contrary to what one would guess.

**Four findings nevertheless block it as a metadata layer, and the first is fatal:**

1. **NO SOURCE IS CITED. ANYWHERE.** Not on any of the 756 sūkta pages, not on either index
   page (which have no header template at all — they open directly with `<poem>`), and not
   on any talk page (`चर्चा:अथर्ववेदः` and both index talk pages return `missing`). Searches
   for `स्रोत`, `संस्करण`, `आधार`, `सम्पादक`, `Whitney`, `विश्वबन्धु` returned only false
   positives — `स्रोत` matches the *word* `स्रोत्याः` inside mantras. The internal evidence
   proves the apparatus was transcribed from *some* printed anukramaṇī — the telegraphic
   `दे. X। <metre>, <n> <metre>।` format, and 162 pages (21%) carrying explicit
   "not transcribed" placeholders (`उष्णिक्, .......।`) — but **which edition is unrecorded**.
2. **A measured 5.3% internal disagreement rate.** The site's own two transcriptions of the
   same data — the per-page `author` fields and the `ऋषिसूची` index — were cross-validated on
   562 comparable `(kāṇḍa, sūkta)` keys: **532 agree, 30 disagree**. 14 are orthographic
   (`भृगुः`/`भृृगुः` with a doubled vowel sign); **16 are substantive**, ~10 of them flat name
   conflicts: AV 2.3, 2.24, 6.36, 6.99, 7.21, 9.8, 16.1, 16.2, 19.9, 20.2. **These are
   unresolvable on the available evidence, because there is no cited edition to adjudicate
   against.**
3. **The numbering does not join.** Wikisource's `(kāṇḍa, sūkta)` is **not** the standard
   Śaunaka numbering in books 7–13: paryāya-sūktas are split across separate pages, so kāṇḍa
   12 has 11 pages for 5 standard hymns and kāṇḍa 13 has 9 for 4. 115 pages disclose the
   canonical number in a `section` parenthetical (`सूक्तं १३.७(१३.४)`); the rest do not —
   kāṇḍa 12 entirely, and 13.5/13.6. A hand-built mapping table would be required before any
   harvested key joins to this project's AVŚ passages.
4. **The chandas gap lands exactly on the prose books.** 162 pages carry an explicit elision
   placeholder, concentrated in K15 (17/18), K16 (8/10), K13 (9/10), K10 (10/10), K8 (11/15).
   Book 16's chandas is effectively absent. Book 20, counter-intuitively, is the *best*
   covered (124/143).

Also: the index pages are transcribed **prose**, not tables — 34–36% of their entries carry
defects (`.` used for `,` as the separator, ref groups of ambiguous arity where `४, ५, ६` is
either {4.5, 4.6} or {4.5.6}, standalone `वा` alternatives, `(?)` uncertainty markers). And
22 devatā values are `मन्त्रोक्त` — "whatever the mantra names", an explicit non-answer —
while 30 are `अध्यात्मम्`, a subject label rather than a deity.

**Rights:** CC BY-SA 4.0 confirmed from the raw footer; **no PD template on any of the 769
pages** (regex-scanned, zero hits). The underlying traditional ascriptions are PD by age, but
because no edition is cited it **cannot be established that the transcription came from a
public-domain printed edition** rather than a modern in-copyright one.

**Conclusion: a high-value bootstrap corpus, not a gold layer.** Its internal disagreement
rate is measurable and its provenance is not. Given this project's precedent on the Rigveda
semantic layer, unsourced metadata must not enter as gold.

### 6.2 Safe resolution method, in priority order

**1. Whitney's Anukramani brackets from English Wikisource — PD, sourced, deterministic.**
This is the recommended route and it was not on the original candidate list. Whitney's
per-hymn bracketed header *is* an excerpt of the Brhatsarvanukramani, and the Wikisource
transcription is ProofreadPage-**Validated** (`Progress=V`) with correct IAST:

```
[''Atharvan'' (''ayuskamah'').—''vaicvadevam. traistubham: 3. cakvaragarbha viradjagati.'']
```

That is rsi (plus the rsi's *kama*) / devata / chandas, **with per-verse metre exceptions**,
present for essentially all **588 hymns of books I-XIX**. `Anukr` is cited 567 times in
volume 1 alone. Licence, verbatim from the rendered `{{PD/US|1941}}`:

> "This work is in the public domain in the United States because it was published before
> January 1, 1931. The longest-living author of this work died in 1941, so this work is in
> the public domain in countries and areas where the copyright term is the author's life
> plus 84 years or less."

Life+84 comfortably covers India's life+60. **Mirroring permitted.**

Conditions and limits, all real: it is per-**hymn** for rsi/devata (per-mantra only for the
metre exceptions); it does **not** cover kanda 20; the old Harvard Oriental Series
orthography needs a c-cedilla to s-acute normalisation pass; and pinned `oldid`s must be
captured at ingestion time. Bonus: the adjacent
`Translated: Weber, iv. 424; Ludwig, p. 430; Griffith, i. 34; Bloomfield, 99, 274.` lines
give a ready-made per-hymn concordance across six translators (580 such paragraphs, 551
citing Griffith, 187 citing Bloomfield).

**2. sa.wikisource per-page headers — as CANDIDATE only, never gold.** Extract from the
per-page `{{header}}` fields, **not** from the index pages (34-36% defect rate, irreducible
arity ambiguity). Conditions: pin `oldid`; keep the raw string alongside every parsed value;
emit `AssertionStatus.UNREVIEWED` with `provenance = UNSOURCED_WIKISOURCE`; build the books
7-13 numbering map by hand before joining anything; and queue the roughly 10
index-vs-header conflicts and 162 placeholdered chandas for human adjudication. Its value
over route 1 is that it *does* cover kanda 20 and the prose books.

**3. IGNCA permission for vedicheritage.gov.in.** Highest-authority per-sukta
rsi/devata/metre, *plus* scanned page images — the external authority that would resolve
route 2's conflicts. Blocked only by rights.

**4. Re-OCR the 1922 Brhatsarvanukramani.**
`archive.org/details/pIEJ_brihat-sarva-anukramanika-...` (CC0, Pandit Ramgopala Shastri,
Lahore, July 1922 -> US public domain) is a genuine forward per-sukta table: for AVS 7.74 it
gives the pratika, *caturrcam* (4 verses), rsi *Atharvangiras*, devata and chandas, with
per-verse metre exceptions — **plus Hindi editorial footnotes reconciling the Anukramani's
divisions against the Pancapatalika, Kausika Sutra, Vaitana Sutra and the printed
Samhitas**, which is directly useful for the numbering work in section 3. Blocked only by
OCR quality. **UNVERIFIED:** Ramagopala Shastri's death year, so the India status is
undetermined.

**What must NOT be done, restated because both remain tempting.** Do not transfer Rigvedic
Anukramani rules — the repo's mature Rigvedic pipeline (`data/registry/rishis.yaml`,
`devatas.yaml`, `chandas.yaml`, `ingest/adapters/anukramani.py`, `WSC2023`) is not
authoritative for AVS, and reusing those registries as if they were AVS metadata would
fabricate provenance. And do not infer any of it with a language model.

**Sāyaṇa-bhāṣya, incidentally:** present on ≈123 of 756 AVŚ sūkta pages (16%), heavily
front-loaded — kāṇḍas 1 and 2 complete, then collapsing to 2/143 in kāṇḍa 20 and zero in
kāṇḍas 5, 8, 10, 12–16. (Note: the site-wide `insource:"सायणभाष्यम्"` count of 1,168 is
dominated by the Rigveda and is *not* an Atharvaveda figure; the AVŚ-scoped count is 123, and
an independent local scan of all 769 pages agreed at 123.) The authenticity of the
Atharvaveda Sāyaṇa-bhāṣya is disputed; presence is recorded, authenticity is **not** asserted.

---

## 7. Audio inventory

**Nothing was downloaded or mirrored. Zero `AudioRecording` records are in the release** —
because alignment work is required first, not because everything is blocked. Two items *are*
mirrorable.

| # | Item | Recension | Scope | Recitation type | Reciter / tradition | Source | Duration | Format | Alignment granularity | Rights (verbatim basis) | Mirror? | Direct link? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Vedavani** ASR corpus | Śaunaka (inferred from text match; **not stated**) | **9,997 AV samples**; kāṇḍas 1–13 explicitly named (6,306), remainder under opaque `Part_NNN` (3,691) | saṃhitā-pāṭha (inferred; **not stated**) | **UNVERIFIED — not stated** | `huggingface.co/datasets/sanganaka/Vedavani-Dataset` (ACL 2025, arXiv:2506.00145) | AV portion of ~54 h total | WAV + CSV transcripts | **per-mantra / per-hemistich**, with Devanagari transcription — but **no AVŚ kāṇḍa.sūkta.mantra reference** | **`APACHE_2_0`** — README: "📜 **License**: Apache License 2.0" | **YES** | yes |
| 2 | archive.org **`atharvaveda_202107`** "Atharva Veda Complete Chanting", Veda Prasara Samithi 2020 | unstated → **UNVERIFIED** | complete, 28 files | saṃhitā-pāṭha (assumed) | unnamed | `archive.org/details/atharvaveda_202107` | **19.20 h** | MP3 | **none** — arbitrary ~42-min parts | **`UNKNOWN` — I was OVERRULED here, see below** | **NO** | yes |
| 3 | **Vedic Heritage Portal** per-sūkta HLS **video** | **Śaunaka** (page title) | **kāṇḍas 1–5 only**, 168 live streams (K1 35/35, K2 35/36, K3 31/31, K4 37/40, K5 30/31). Kāṇḍas 6–20 return **404** | saṃhitā-pāṭha (**UNVERIFIED**) | **UNVERIFIED — no credit on the page** | `vedicheritage.gov.in/atharva-veda/HLS/Kanda{N}/Atharvaveda_K{NN}_{SS}/index.m3u8` | **6.60 h** | MPEG-TS video (`video/mp2t`), 10 s segments | **per-sūkta** — finest structural alignment of any traditional source found | **`PERMISSION_REQUIRED`** — Copyright Policy: "The contents of this website can not be reproduced partially or fully, without written permission from Indira Gandhi National Center for the Arts" | **NO** | **DISPUTED** (§1) |
| 4 | **Vedic Heritage** per-sūkta MP3 (`Athss_KK_SSS.mp3`) | Śaunaka | naming covers all 20 kāṇḍas; `Athss_01_001.mp3` and `Athss_20_143.mp3` both verified HTTP 206 | saṃhitā-pāṭha (**UNVERIFIED**) | **UNVERIFIED** | `vedicheritage.gov.in/atharaveda_mp3/` | not stated | `audio/mpeg`, range-capable | **per-sūkta** | **`PERMISSION_REQUIRED`** — same policy | **NO** | **DISPUTED** |
| 5 | **vedamu.org** (Sri Sathya Sai Veda Pratishtan) | **Śaunaka *and* Paippalāda, separately labelled** | Śaunaka saṃhitā-pāṭha in full; Paippalāda in full | **saṃhitā-pāṭha only** | Sri Sathya Sai Veda Pratishtan, Hyderabad | `vedamu.org/VedicChanting.aspx`, files `vedamu.org/VedicChanting/{ID}${NAME}.mp3` | AV part of 178 h across five śākhās | MP3 | per-kāṇḍa (Kāṇḍa 1) / opaque | **`REFERENCE_ONLY`** by the operator's own words: "We also present the entire text of Sounaka-sakha in Samhitapatha which is **open to listen, and not to download**." Only Prārthanā + Kāṇḍa 1 have download buttons. No terms page exists on the site. | **NO** (except Prārthanā + K1) | yes |
| 6 | archive.org **`AtharvaVedam`** (Sringeri) | unstated | **per-kāṇḍa files** `Kandam 01`–`Kandam 21` | saṃhitā-pāṭha (assumed) | Sringeri | `archive.org/details/AtharvaVedam` | **38.95 h** (largest found) | MP3 | **per-kāṇḍa** | **no `licenseurl` field → NO reuse grant** | **NO** | yes |
| 7 | archive.org **`atharvaved-tune`** | unstated | per-kāṇḍa `Kanda 1`–`Kanda 20` | saṃhitā-pāṭha | "Sages" | `archive.org/details/atharvaved-tune` | 18.64 h | MP3/M4A | **per-kāṇḍa** | no `licenseurl` → no grant | **NO** | yes |
| 8 | archive.org **`Atharvaveda-shaunaka-shAkhA`** | **Śaunaka (explicit)** | 11 files | saṃhitā-pāṭha | — | `archive.org/details/Atharvaveda-shaunaka-shAkhA` | 19.47 h | MP3 | per-kāṇḍa | **`REFERENCE_ONLY` and rights-questionable** — the filenames are byte-identical to the vedamu.org files their operator says are "not to download", i.e. this looks like an unauthorised mirror | **NO** | avoid |
| 9 | archive.org `AtharvaVeda1-189` (+4 split duplicates), `atharvaveda1`/`2`, `atharvaveda_202106`, `arya-samaj-vedas-hindi-mp3`, `avinash04121996_gmail_006` | unstated | various | assumed | unnamed | archive.org | 6.6–29.9 h each | MP3 | **none** (arbitrary time slices) | no `licenseurl` → no grant | **NO** | yes |

### Findings that change the plan

* **One mirrorable AVŚ audio source exists: Vedavani (Apache-2.0).** I initially reported
  two, counting `atharvaveda_202107` on the strength of its CC Public Domain Mark, and **I was
  overruled — correctly.** A PD Mark is not a licence and not a waiver; it is an *assertion by
  whoever applied it* that a work is already out of copyright. This is a 2020 recording of
  living performers tagged by a third-party re-uploader with no standing, so the assertion is
  not merely unverified, it is not credible. **My own evidence is what settles it:**
  `atharvaveda_202106` is a **byte-identical** file set carrying **no** licence field at all.
  The same bytes cannot be simultaneously public domain and all-rights-reserved, which proves
  the tag is uploader noise rather than a rights position. Recorded `UNKNOWN`, no
  redistribution. Nothing is lost operationally, since that item's alignment granularity is
  `none` anyway. Recommend **Vedavani** as the audio base.
* **But no source combines per-mantra alignment with AVŚ references.** Vedavani is
  per-mantra-*segmented* with unaccented Devanagari transcripts and **no** kāṇḍa.sūkta.mantra
  key; alignment to the VedaGraph spine must be done by text-matching against the AVŚ
  Sanskrit. That is real work and should be a reviewable derived layer, not asserted as
  source data.
* **AVŚ pada-, krama-, jaṭā- and ghana-pāṭha recordings DO NOT EXIST.** This is a definitive
  negative from the only institution that would have them, vedamu.org, in its own words:
  "We are working through a group of scholars to construct **Pada and Krama pathas** for
  Sounaka & Pippalada sakhas… Thereafter, we intend to get **Jata and Ghana pathas** also to
  be constructed." So any AVŚ `patha_type` other than `SAMHITA` is currently unfillable.
* **`robots.txt` permitting a crawl of `vedicheritage.gov.in/atharaveda_mp3/` is irrelevant.**
  A crawl permission is not a reproduction licence, and the Copyright Policy forbids
  reproduction "partially or fully" without written permission. Flagged explicitly because
  "publicly playable and not robots-blocked" is exactly the reasoning that would get this
  mirrored by mistake.
* **Reciter identity, śākhā and recitation type are UNVERIFIED for every item** except
  vedamu (saṃhitā-pāṭha, stated). Recension is unstated for every archive.org item except
  `Atharvaveda-shaunaka-shAkhA`. None of this may be filled in by inference.
* **Dead:** `vedicreserve.mum.edu` / `is1.mum.edu/vedicreserve` / `mum.edu/vedicreserve` —
  connection failure on both HTTP and HTTPS. The Maharishi Vedic Literature Collection is
  offline. **Not found:** any SAKSI, IGNCA-separate, or Gujarat/Kolkata academic AVŚ
  field-recording archive. Searched; does not appear to exist publicly.
* **`sanskritdocuments.org` has no AVŚ Saṃhitā recitation** — only Atharva-derived Upaniṣads.

## 8. Reproducibility

```bash
# 1. Sanskrit — two immutable hashed snapshots, then the pilot
./.venv/Scripts/python.exe scripts/build_atharvaveda_pilot.py

# 2. Translation staging (optional; already staged, cached snapshots are reused)
./.venv/Scripts/python.exe scripts/fetch_atharvaveda_translation.py
```

Every network read goes through `PoliteFetcher` with a stable URL, so each response is an
immutable hashed snapshot under `data/raw/gretil_avs/` (2 files) or `data/raw/vedaweb_avs/`
(23 files) and a rerun reuses the cache without refetching. VedaWeb's two-step
`/resources/{id}/export` flow was **deliberately not used**: its download URL carries an
ephemeral `pickupKey` and would not be reproducible. `GET /api/contents` and
`GET /api/locations` were used instead — both single stable GETs.

The build is byte-identical across processes, verified by `diff -r` on all 14 output files
including `manifest.json`. `built_at` is pinned to the newest snapshot retrieval timestamp
rather than wall-clock time, which is what makes the manifest itself stable.

---

## 9. What is still unverified

Recorded rather than glossed, because each affects a conclusion above.

**Resolved since the first draft of this report — no longer open:**

* The kāṇḍa-7 label/marker cluster is **solved and proved** from Whitney HOS 7 p. 389
  (Berlin vs Bombay hymn division; 6/6 of Whitney's stated split points matched by the
  parser with zero misses). See `docs/pilots/ATHARVAVEDA_PILOT.md` §6.2.
* The sa.wikisource metadata lead is **fully verified** (§6.1): deterministic, 97–99%
  covered, and **unsourced**.
* The broader audio survey is **complete** (§7), and it changed the conclusion: two
  mirrorable sources exist.
* Kāṇḍa 20's translation gap is **closable** — Griffith covers it (§2).
* The GRETIL `sa_atharvavedapariziSTas.xml` TEI licence **was** read (CC BY-NC-SA 4.0 plus
  a "good faith" removal clause) and its contents checked: it does **not** carry per-mantra
  ṛṣi/devatā/chandas (§6.0).
* Hindi was checked properly rather than assumed (§2). The conclusion now rests on verified
  facts — a publisher "all rights reserved" notice, a documented death date, and corrupted
  OCR — not on a guess.

**Still open:**

* **Which printed edition the sa.wikisource metadata derives from.** This is a fact about
  the source, not a gap in the search: no citation exists anywhere on the wiki, on either
  index page, or on any talk page (they do not exist). Consequently the ~10 substantive ṛṣi
  conflicts in §6.1 have **no resolution on the available evidence**. The Google Drive
  artefacts linked from the index pages were not fetched — off-wiki, unversioned, and
  outside the CC BY-SA corpus.
* **Whether the AVŚ file is on sacred-texts.com's commercial-licensing Bibliography list.**
  Their policy says some prepared PD files "may be licensed for commercial use… listed in
  the Bibliography", and that list could not be located. Material if the corpus is ever
  used commercially.
* **Publication year and copyright status of Prajñādevī's editorial layer** in the Trivedī
  Hindi bhāṣya 2nd edition, and **Rāmagopāla Śāstrī's death year** (which determines the
  India status of the 1922 Bṛhatsarvānukramaṇī). Both block a rights ruling on their
  respective sources.
* **Reciter identity, śākhā and recitation type for every audio item** except vedamu
  (saṃhitā-pāṭha, stated). Recension is unstated for every archive.org audio item except
  `Atharvaveda-shaunaka-shAkhA`. None of this may be filled in by inference.
* **Vedavani's chain of title** — Apache-2.0 is asserted by the dataset authors over
  recordings that appear to originate from a third-party archive.org upload. Coherent, not
  verified.
* **Whether TITUS's unauthenticated HTTP 200 on its `/private/` plain text is intentional.**
* **Scope of `arya-samaj-vedas-hindi-mp3` (25.3 GB) and `avinash04121996_gmail_006`** — the
  AVŚ portion was not isolated.
* **Whether any SAKSI or Gujarat/Kolkata academic AVŚ field-recording archive exists.**
  Searched and not found; recorded as UNVERIFIED rather than as "none exists", because the
  living Śaunaka tradition in Saurāṣṭra, Varanasi and Gokarna is well attested in secondary
  literature even though no accessible recording archive surfaced.
* **Source-count anomalies not chased to ground:** vedicheritage.gov.in kāṇḍa 13 (9 pages vs
  canonical 4) and kāṇḍa 18 (3 vs 4); sa.wikisource's duplicate/stub titles and
  en.wikisource's 222 Roman-numeral duplicates (a per-page content diff was not run).
* **The three remaining locator collisions** (9.6.48, 12.5.53, 13.4.26) are almost certainly
  source typos and the evidence is strong in each case, but "almost certainly" is not
  "proved", and no correction was applied to any of them.
* **GFDL in current Wikimedia terms** — absent from the page footers fetched;
  `Wikisource:Copyright policy` and the WMF Terms of Use were not fetched.
* **Whether VedaWeb will publish an AVŚ TEI, Devanagari or morphology layer.** No
  announcement found (`announcements: []`); `vedaweb-data` on GitHub contains only a
  `rigveda` directory today.

## 10. The gaps that are permission problems, not engineering problems

1. **No accented Sanskrit under an open licence — and the blocker is deeper than TITUS.**
   Every accented AVŚ source is rights-encumbered; the only openly-licensed AVŚ source is
   unaccented. I originally wrote that one TITUS request would unlock the Latin accented text
   together with GRETIL and VedaWeb's Sanskrit layer. **That was wrong.** Following the
   provenance chain to its root: every accented Latin AVŚ text in this matrix descends from
   Orlandi, Pisa: Giardini, 1991 — a modern scholarly transliteration **still in copyright** —
   collated with the public-domain Roth/Whitney 1856. The Sanskrit Library asserts
   CC BY-NC-SA 3.0 *downstream* of Orlandi, which cannot cure an encumbered root.

   **So the genuinely open routes are two, and neither is TITUS alone:**
   * **IGNCA**, which would unlock accented Devanagari *and* the per-sūkta audio corpus in
     one grant; or
   * **a Śaunaka text derived solely from Roth/Whitney 1856 with no Orlandi-derived
     collation** — the only identified route to a rights-clear Śaunaka Sanskrit text, and no
     such artifact was found in this investigation.

   A TITUS grant remains necessary for the current artifact, but it is not sufficient.

2. **No *retrievable* XML/TEI for AVŚ.** Corrected too: a TEI edition **does exist** — The
   Sanskrit Library, 2010, ed. Peter M. Scharf, XML and TEI header by Matthias H. Ahlborn —
   but only its bibliographic catalogue record is reachable; the underlying TEI is not exposed
   at any discovered URL. GRETIL has TEI for Paippalāda but not Śaunaka (its corpustei
   collection holds only the ancillary `sa_atharvavedapariziSTas.xml` and
   `sa_atharvaprAyazcittAni.xml`, which are not the Saṃhitā). So the accurate statement is
   "no TEI is retrievable", not "no TEI exists" — and the fix is a request to The Sanskrit
   Library, not a request for someone to produce TEI from scratch.

## 11. Readiness verdict

# `SOURCE_STACK_APPROVED_WITH_LIMITATIONS`

**Justification.** Every *engineering* question is answered and demonstrated, so this is not
`SOURCE_ADJUDICATION_INCOMPLETE`: the recension is proved from the artifact, the whole
5,839-mantra structure parses with zero unhandled tokens, identity uses the frozen
`avs_*_identity` functions with 174/174 UUIDs independently recomputed, accents survive
verbatim alongside derived surfaces, 115 translations are aligned by printed citation, the
shared cross-Veda gate returns one issue and that issue is a declared source defect, and the
build is byte-identical across processes.

It is not `SOURCE_STACK_APPROVED_FOR_FULL_INGESTION` because of four limitations, each of
which is a real constraint rather than an unfinished task:

1. **Rights, and this is the binding one.** The primary Sanskrit source is `REFERENCE_ONLY`
   by its own words. Full-corpus *ingestion* is technically ready today; full-corpus *use or
   redistribution* is not authorised by anything found. This is a permission decision, not a
   capability question, and it should be made deliberately rather than by running a bigger
   build. **And it is a harder decision than I first reported:** a TITUS grant is necessary
   but **not sufficient**, because the root of that provenance chain is Orlandi 1991 and still
   in copyright (§10). The clean routes are IGNCA, or a Śaunaka text built solely on
   Roth/Whitney 1856.
2. **Four unreconciled verse counts in one textual lineage** (5,839 / 5,842 / 5,919 / ~5,977),
   and the primary artifact states no total of its own, so there is nothing internal to
   reconcile against. A full corpus would bake in one of the four by default.
3. **Four locator collisions and thirteen label/marker disagreements** are handled
   deterministically and losslessly, but three of the collisions are source typos and one is
   a genuine edition divergence where a 3-integer canonical key cannot represent both verses.
   That last one needs a human editor.
4. **No traditional-metadata layer and no audio layer are possible today.** The only sourced
   candidate for either (`vedicheritage.gov.in`) forbids reproduction; the only openly
   licensed metadata candidate (`sa.wikisource`) cites no edition and disagrees with itself
   at a measured 5.3%.

**What would move this to `SOURCE_STACK_APPROVED_FOR_FULL_INGESTION`:** either written
permission from IGNCA (which would unlock accented Devanagari *and* the audio corpus in one
grant), or permission from **both** TITUS *and* the Orlandi/Giardini rights holders, or a
Śaunaka Sanskrit text derived solely from the public-domain Roth/Whitney 1856 edition. Plus a
human ruling on the AVŚ 20.96.22 double-numbered verse and on which of the four verse counts
the corpus adopts.
