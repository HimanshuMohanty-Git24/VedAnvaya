# VedAnvaya — Brand & Visual Research Brief

**Agent 1 — Visual / Brand Research**
**Date:** 2026-09-13
**Status:** Research reference. Not a spec. Feeds the design system and the frontend build.
**Design philosophy under test:** MANUSCRIPT MODERNISM — ancient Indian manuscript discipline × contemporary cultural institution × digital scholarship × exceptional modern visualization.

---

## 0. How to read this document

Every claim below is attached to a named site, a named designer, a named measurement or a named URL. Where I could not verify something, it is marked **[UNVERIFIED]** rather than smoothed over. Several museum sites (Getty, Smithsonian Open Access, Bodleian South Asian Manuscripts, Sefaria Help Center) returned HTTP 403 to automated fetching; those are flagged and the finding is sourced elsewhere or marked unverified.

The document is organised as the task specified: institutions → scholarly interfaces → manuscripts → typographic identity → Devanagari/Vedic type → anti-patterns → layout. The single most actionable sections are **§5 (font recommendation with evidence)** and **§7 (layout)**.

Fixed constraints assumed throughout:

| Token | Value | Role |
|---|---|---|
| `manuscript-ivory` | `#F4F0E7` | Ground |
| `carbon-ink` | `#171815` | Text |
| `rubric-red` | `#B64A2E` | Primary accent — *rubrication, not decoration* |
| `aged-gold` | `#B49A62` | Rare |
| `indigo-ink` | `#26364A` | Secondary |
| Display | Fraunces (variable, 4 axes) | |
| UI | Inter | |
| Sanskrit (prominent) | Noto Serif Devanagari | **see §5 — needs a companion** |
| Sanskrit (compact) | Noto Sans Devanagari | |

---

# 1. Premium cultural institution / museum / archive web design

## 1.1 Rijksmuseum — the typographic identity as the whole identity

The 2013 Rijksmuseum identity was designed by **Irma Boom Office**, who deliberately chose **"a predominantly typographical solution"**, with **Bold Monday (Paul van de Laan)** commissioned to design a *series* of typefaces rather than one. (ATypI presentation: <https://atypi.org/presentation/the-new-rijksmuseum-identity-and-typeface-family/>)

This is the first institutional move worth stealing: **the institution's confidence is expressed in letterforms, not in a logo mark.** A museum that needs a graphic device to feel serious does not feel serious. VedAnvaya should not commission or invent a symbol. The wordmark **वेदान्वय / VedAnvaya** set in Fraunces + a Devanagari companion, with a single rubric-red element, *is* the identity.

Concrete layout findings from the Rijksmuseum web work:

- The site redesign introduced **more white space and a two-column grid** specifically to *reduce scrolling* and improve accessibility for users with physical disabilities — whitespace was justified as an accessibility argument, not a taste argument. (<https://ixd.prattsi.org/2023/09/design-critique-rijksmuseum-website/>)
- A **four-column responsive grid** is used for the artwork tiles so works display "in full glory on any screen."
- Rijksstudio's redesign (Museums & the Web 2018) states the operating principle as **"the image as the interface"** with metadata secondary. They shipped **only two presentation templates**: the personal-set template (Pinterest-style) and the full-screen image. Navigation is split by axis — **vertical scrolling through sets and tours, horizontal swiping through full-screen works.** Stated reasoning: **"people like things big"**, plus the Pareto principle — broad function for the widest audience over niche features.
  (<https://mw18.mwconf.org/paper/rijksmuseum-mobile-first-redesign-rijksstudio-the-new-rijksmuseum-app/index.html>)

**Transfer to VedAnvaya:** the *verse* is our image. Give it the full-screen treatment. Two templates, not twelve — a verse reading template and a graph/entity template. Axis-splitting navigation (scroll = sequence within a hymn; lateral = variants/translations/connections) is a strong, unclichéd interaction idea for a Samhitā.

## 1.2 Cooper Hewitt — giving the typeface away, and fixing search honestly

Identity by **Pentagram (Eddie Opara)**; the wordmark characters were developed into a full typeface, **Cooper Hewitt**, by **Chester Jenkins of Village**, released free under the **SIL Open Font License** and described by Pentagram as **"a design that truly belongs to the people."**
(<https://www.pentagram.com/work/cooper-hewitt-smithsonian-design-museum-1/story>, <https://www.cooperhewitt.org/open-source-at-cooper-hewitt/cooper-hewitt-the-typeface-by-chester-jenkins/>)

The collection-site search redesign (Museums & the Web 2015) is the most transferable document I found for a corpus product:
(<https://mw2015.museumsandtheweb.com/paper/reconsidering-searching-and-browsing-on-the-cooper-hewitts-collections-website/index.html>)

- **Facets were previously inside a drop-down accordion, collapsed by default — used in only 6.81% of searches.** They were moved to a **persistent sidebar**. The measurement is the argument: hidden facets are dead facets.
- They **deleted the category dropdown** (Collection / People / Objects / Media / Exhibitions / Fancy Search) that gated search behind a choice. "Searches via the global input field go straight to the results page." One input, no pre-selection.
- They **separated the ranking function for search from browse**: search results deliberately do **not** boost records that have images, because that biases toward the most complete records; browse results **do** boost images, "to create a more visually pleasurable experience." Two different jobs, two different sorts.
- They **refused to merge search and browse** into one interface, arguing that merging "sacrifices the quality of search results for bias."
- Microcopy was treated as design: placeholder became **"Search the Collection"**; the browse entry was renamed from "The Collection" to **"Explore the Collection."**
- Results stayed a **three-column grid of images** for consistency across the site.

Cooper Hewitt Labs also documents four ideas worth noting (<https://labs.cooperhewitt.org/>):
- **Dive into Color** — browsing by colour harmony over time; they found an **artist's RYB colour wheel matched user expectation better than RGB**, and that colour browsing "offers a visual, intuitive way to explore a digitised collection without needing specialist knowledge."
- **Timeline + tags** — deliberately **irregular, tightly-packed image layouts** to encourage pattern recognition *rather than precise date reading*. A deliberate anti-grid, used for a reason.
- **Large-print exhibition labels** generated in six sizes, **18–28pt**. Accessibility as a first-class published feature.
- **IIIF deep zoom across 200,000+ objects.**

**Transfer:** VedAnvaya's ranking for the search page and for the "browse the corpus" page must not be the same function. And our equivalent of "browse by colour" — a non-expert, visual, non-lexical entry into the corpus — is probably **browse by metre**, **browse by deity**, or **browse by maṇḍala as a strip of 10 uneven blocks**. That is the one place irregular, pattern-revealing layout beats a grid.

## 1.3 V&A — one typeface for everything, and a search mistake to learn from

The V&A uses **TheSans (Luc(as) de Groot)** as webfonts for *all* text; the museum's print identity has used **V&A Sans**, an adapted TheSans, since 2002. **A single family does display and UI.** (<https://fontsinuse.com/uses/25490/vand-a-website>)

From the V&A's own launch blog (<https://www.vam.ac.uk/blog/digital/new-website>):
- Framed as **"not a refresh, it's a rebuild"** — a full rewrite on Ruby on Rails to get freedom over feature sequencing.
- Design goals: **"much larger, richer imagery"** and **"a bolder use of the brand and logo"**; explicitly seeking "a better balance between text and image."
- **The instructive failure:** they deprioritised site search at launch on the evidence that **"only 5% of sessions involve search"**, assuming Google was the front door. The comment thread records sustained user complaint about discoverability, and they committed to fixing it.

**Transfer:** the V&A could survive deprioritising search because a museum's atoms are objects you browse. **VedAnvaya cannot.** Our atoms are addressable text strings; search *is* the product. The 5%-of-sessions statistic is a museum statistic, not a corpus statistic — do not import it. Also note the 2021 **"Explore the Collections"** relaunch, which "unites collections data with our editorial content so audiences can explore the bigger picture" — i.e. the institution merged its *catalogue* and its *writing* into one surface. That is exactly the VedAnvaya problem: the graph and the essay must live on the same page, not in separate "Explore" and "Blog" silos.

## 1.4 Wellcome Collection — inclusion stated as a design principle, and three sites merged into one

Wellcome's published design vision frames inclusion as **"an opportunity for creativity and innovation"** and names seven characteristics of inclusive design, of which three are directly typographic/interface-relevant:
(<https://wellcomecollection.org/our-design-vision>)

1. **"Is consistent, but not uniform"** — the single best sentence in this entire brief for a manuscript-modernist system. Consistency of *rules*, variation of *expression*.
2. **"Offers choice and flexibility"**
3. **"Is intuitive to use"**

Strategically, Wellcome merged **wellcomecollection.org + wellcomelibrary.org + wellcomeimages.org into a single website** with one coherent discovery experience, backed by IIIF. (<https://stacks.wellcomecollection.org/a-digital-strategy-for-wellcome-collection-1b43e5365331>)

Observable on the collections page today: neutral background so imagery is the only colour; **horizontal rules dividing major sections** (not cards); browse-by-theme grouped as **People and organisations / Types and techniques / Subjects / Places** — i.e. **facets promoted to navigation.**

**Transfer:** VedAnvaya's analogous browse-by-theme is **Deities / Seers / Metres / Concepts / Formulae** — the graph's node types, promoted to a first-class navigation row on the home page. That single move converts "we have a knowledge graph" from a claim into an interface.

## 1.5 Europeana, Tate, Getty, Smithsonian

- **Europeana** runs an explicit build → test → evaluate → redesign loop with **external heuristic reviews and direct user interviews**, and validated its grid view by adoption measurement (**66,500+ search page views using the grid in one month, rising**). (<https://pro.europeana.eu/post/exploring-europeana-s-approach-to-design>, <https://pro.europeana.eu/post/a-behind-the-curtains-look-at-europeana-s-design-process-and-next-steps>)
- **Tate**'s custom face "combined classical proportions of Roman inscriptions in the capitals with the geometry of 20th-century modernism in the lowercase," designed to be **"uniquely identifiable yet sufficiently neutral to allow the art to have a voice."** (<https://newlyn.com/blog/the-face-of-tate>) — This is the governing sentence for VedAnvaya's whole visual system. Substitute "the verse" for "the art." Everything we design should be identifiable and then get out of the way.
- **Getty** (<https://www.getty.edu/art/collection/>) and **Smithsonian Open Access** (<https://www.si.edu/openaccess>) both refused automated fetch (403 / empty SPA shell). **[UNVERIFIED by fetch]** — do a manual screenshot pass before citing either in the design system.
- **Internet Archive**: Democracy's Library and Internet Archive Scholar (**35M+ articles full-text as of Feb 2024**) exist, but I found **no published visual-identity or redesign documentation for 2024–25**. **[UNVERIFIED]** Do not cite IA as a design precedent; cite it only as a scale/access precedent.

## 1.6 What actually makes a site read "institutional" rather than "SaaS" — the concrete list

Synthesised from the above, every item traceable to a named site:

1. **A typographic identity instead of a graphic mark.** (Rijksmuseum/Irma Boom; Tate; V&A's single family.)
2. **One type family carrying both display and UI**, or two with a *large* contrast in role — never three interchangeable sans-serifs. (V&A/TheSans.)
3. **Content-first colour:** the page ground is neutral, and the only saturated colour on screen belongs to the *artefact*, not to the chrome. (Wellcome, Rijksmuseum.)
4. **Rules, not cards.** Institutions divide with hairlines and whitespace. SaaS divides with elevated white rectangles on grey. (Wellcome's horizontal rules.)
5. **Facets exposed permanently in a rail, not hidden in a dropdown** — and the willingness to measure that. (Cooper Hewitt, 6.81%.)
6. **Different ranking for different intents.** Search ≠ browse. (Cooper Hewitt.)
7. **Real metadata shown as text, in full, without truncation-with-ellipsis.** Institutions publish; products summarise.
8. **Accessibility published as a feature, with numbers** (18–28pt labels; social model of disability). (Cooper Hewitt, Wellcome.)
9. **Deep zoom / high-resolution as a default expectation**, via IIIF. (Cooper Hewitt, Wellcome.)
10. **Microcopy in the institution's register** — "Explore the Collections", not "Get Started" / "Learn More". (Cooper Hewitt, V&A.)
11. **Open licensing as a brand act** — Cooper Hewitt gave its typeface away; Rijksmuseum gave its images away. Generosity reads as authority.
12. **No conversion furniture.** No sticky signup bar, no "trusted by" logo strip, no testimonial carousel, no pricing table, no newsletter modal on scroll.

---

# 2. Editorial digital-humanities and scholarly interfaces

## 2.1 VedaWeb (vedaweb.uni-koeln.de) — the closest peer, studied in depth

**What it is.** A DFG-funded Cologne platform (part of C-SALT), Rigveda as pilot text, **10,522 stanzas**, morphological annotation supplied by Universität Zürich, linked to the Cologne Digital Sanskrit Dictionaries.
(<https://github.com/VedaWebProject/vedaweb>, <https://gepris.dfg.de/gepris/projekt/329358806?language=en>, <https://dh.phil-fak.uni-koeln.de/en/studieren-am-idh/service-einrichtungen/news-and-guest-speakers/news-and-guest-speakers/vedaweb>)

**Stack and design origin — the critical finding.** The interface **uses Ant Design**. That single decision explains its entire visual character: Ant's blue primary, 2px radii, dense form controls, tab bars and collapsible panels. VedaWeb looks like an internal enterprise research console because it *is* dressed in an enterprise component library. Backend is **Elasticsearch + MongoDB**, containerised with Docker. The frontend repo is now **legacy**, superseded by the successor platform **"Tekst."**

**What VedaWeb gets right — and VedAnvaya must match or beat:**

- **Two search modes with honest names:** "Quick search" (wildcards, boolean operators) and **"Grammar search"** over morphological annotations. Crucially there is an **accent-sensitive search toggle** — the interface acknowledges that *accented and unaccented forms are different queries.* Any Vedic search product without this is lying to the user.
- **Direct address by citation.** You can retrieve a stanza by index or by Rigveda locus in standard notation (`1.1.1`) and by alternative delimiters. **The citation is the URL.**
- **Stacked annotation layers per stanza:** original text, multiple translations (**Grassmann, Geldner, Griffith**), commentary (**Oldenberg**), morphology, metre. Each layer is a togglable band, not a tab that hides the others.
- **Word-to-lemma-to-dictionary linking**, TEI-modelled: word forms link into **Grassmann's 1873 dictionary** and back.
- **TEI-XML export per stanza and per user-defined query result.** Export is a first-class citizen.

**What it gets wrong:**

- **Component-library default chrome.** Ant Design's visual language is the opposite of archival. Blue-on-white, uniform small radii, dense controls, no editorial voice.
- **No reading mode.** The page is a control surface with text embedded in it, rather than a text with controls attached to it. You cannot get to a state where you are just *reading* the Rigveda.
- **Search-panel dominance.** A large persistent query builder occupies prime real estate even when you are reading.
- **Weak on mobile and weak on typographic hierarchy** — translations, transliterations and Devanagari sit at near-identical visual weight.
- **The accents are present but not designed.** No consideration of how the udātta/anudātta/svarita marks interact with line-height, or of the accent as a *visual feature of the page* rather than an encoding detail.

**The VedAnvaya opportunity, stated plainly:** VedaWeb proves the scholarly data model. Nobody has yet given that data model a designed reading experience. That gap is the entire product thesis.

## 2.2 Sefaria (sefaria.org) — the connection/link-graph UX, studied closely

Sefaria is the strongest existing answer to "how do you show a text *and* its network at once."

**The Resource Panel.** Clicking **any** text segment opens a resource panel beside it. The panel lists connections from the database. **Clicking a connection opens a new panel, with its own connection list — panels stack laterally.** The user walks the graph by reading, not by querying.
(<https://help.sefaria.org/hc/en-us/articles/18472472138652-Quick-Guide-Meet-the-Sefaria-Library-Resource-Panel> — *403 to automated fetch; content corroborated via* <https://www.sefaria.org/sheets/219447> *and* <https://www.sefaria.org/sheets/63158>)

Named tools inside the panel:
- **Connections list**, filterable by **relevance, chronology, text category, and specific book**.
- **Compare Text** — place two or more texts side by side, **each scrolling independently**. (Independent scroll is the detail most clones get wrong.)
- **Add Connection** (authenticated) — users can link the primary text to another text.
- **Sheets** — "The number in parenthesis is the number of public sheets that include the text." **A count in parentheses next to the tab name is a tiny, perfect affordance**: it tells you whether opening the tab is worth it before you open it.

**Link typology.** Sefaria's connections are typed, not generic: **Commentary, Quotation, Reference, Summary, Explication, Related Passage.** (<https://developers.sefaria.org/docs/commentaries>) Scale illustration: **over 30,000 instances of the Talmud quoting a verse of Tanakh.**

**The Link Explorer** at <https://www.sefaria.org/explore> is a dedicated visualisation of Talmud↔Tanakh connections — i.e. the graph gets *one* purpose-built visual page, and is otherwise delivered as lists inside the reader. That is the right ratio.

**Bilingual reading modes — directly applicable to Sanskrit/English.** Sefaria exposes user-selectable layouts:
- **Source with Translation** (paired)
- **Source & Translation Stacked**
- **RTL Text Left of LTR Text** (script-direction control)
Plus a language toggle, font-size reduce/enlarge, and a "Want to change the translation?" prompt that routes to a translations menu.

**Transfer to VedAnvaya, concretely:**
- Ship **three** reading layouts on day one: *Sanskrit only*, *Sanskrit + translation interleaved per pāda/verse*, *Sanskrit and translation in parallel columns*. Persist the choice.
- **Type every edge** in the graph and show the type name in the panel. "Related" is not a relationship.
- **Put a count in parentheses on every connection tab.** It is the cheapest possible respect for the reader's time.
- **Panels stack; they do not replace.** Walking from RV 1.1.1 → Agni → another Agni hymn should leave a trail.
- Independent scroll in comparison view. Non-negotiable.

**Where Sefaria is weak:** its visual identity is thin — near-grayscale, category cards on the library page, and a typographic system that does not distinguish the register of a Talmud page from a modern essay. It solved the interaction problem and left the aesthetic problem on the table. **That is precisely the half VedAnvaya should win on.**

## 2.3 Perseus / Scaife Viewer

The **Scaife Viewer** is the reading environment for Perseus 5.0 (<https://scaife.perseus.org/>, <https://github.com/scaife-viewer/scaife-viewer>). The Society for Classical Studies review describes the redesign as having **"an uncluttered layout with legible texts"**, achieved by **removing** specific legacy elements: *floating grey text-boxes, blurry title cards, distracting Unicode–Betacode display preferences, and rows of patchwork horizontal browsing bars.*
(<https://classicalstudies.org/scs-blog/stephensansom/review-perseus-digital-library-scaife-viewer> — *403 to fetch; corroborated via* <https://wiki.digitalclassicist.org/Scaife_Viewer> *and* <https://libraryofantiquity.wordpress.com/2018/04/07/perseus-5-0-viewer-overview/>)

Interaction model: **click a word → the Morphology widget parses it; the Word List gives quick definitions (powered by Logeion).** The architecture is explicitly **a growing library of widgets** in the reading panel, integrating annotations and external APIs.

**The lesson:** the Perseus 5.0 improvement was almost entirely *subtraction*. And "widgets in a reading panel" is a better mental model than "a dashboard of modules" — the text stays primary and tools attach to it.

**Where it's still weak:** the widget stack can become a wall of accordions; and Greek/Latin typography is treated as solved (it is not — nor is Devanagari).

## 2.4 Ambuda (ambuda.org)

- **Information architecture in Sanskrit's own categories**: उपनिषदः, काव्यानि, with "View all X texts →" as the expansion affordance. The taxonomy is emic, not translated into Western genre labels. Strong, quiet, and free of cliché.
- Opens with **॥ श्रीः ॥** — an invocation, set typographically, no graphic. This is exactly the "sacred without devotional" register: a *textual* convention, not an icon.
- **A script transliteration switcher across many scripts**: Devanagari, Roman, Bengali, Brahmi, Grantha, Gujarati, Gurmukhi, Kannada, Malayalam and more. **This is a genuinely distinctive scholarly feature and it costs almost nothing in UI** — one select control, applied globally, persisted.
- **Proofing** (collaborative OCR correction) is promoted into top-level navigation alongside Texts and Dictionaries — the institution shows its working.
- Weaknesses: mostly-default sans UI, white ground, little typographic hierarchy, no sense of page.

**Transfer:** ship the transliteration switcher (Devanagari / IAST / ISO-15919 / Harvard-Kyoto at minimum). Use Sanskrit-native category names with English glosses beneath, never English-only.

## 2.5 GRETIL, SARIT, TITUS, Pandanus, Bibliotheca Polyglotta, DCS

These are the honest baseline of what "scholarly Sanskrit on the web" looks like today, and why the bar is low:

- **GRETIL** (<https://gretil.sub.uni-goettingen.de/gretil.html>): texts organised by language then literary category, each with contributor attribution and downloads. Offers **TEI-conformant XML with parallel HTML and plaintext**. The non-Unicode CSX/REE (CP437) formats were deprecated in June 2019. But: **no corpus-wide search on the page, early-2000s HTML, minimal metadata, no annotation or comparison tools, many expired external links, no mobile optimisation.** It is an archive, not an interface.
- **Bibliotheca Polyglotta** (<https://www2.hf.uio.no/polyglotta/index.php>): 13 collections of aligned multilingual texts (Biblia in Hebrew/LXX/Vulgata/KJV; Pāli Tipiṭaka with English and Thai). Homepage is a text-heavy directory with **minimal visual hierarchy, no screenshots or layout explanation**, and delegates comprehension to a separate search-help wiki. The alignment data is valuable; the interface hides it.
- **Digital Corpus of Sanskrit** (<http://www.sanskrit-linguistics.org/dcs/>): **the TLS certificate does not match the hostname** (`*.serverdomain.org`) — automated fetch fails outright. **[UNVERIFIED]** A scholarly resource that browsers warn against is a resource that loses a generation of users.
- **SARIT / TITUS / Pandanus**: not fetched in this pass. **[UNVERIFIED]** — TITUS in particular is known for frame-based navigation and legacy encodings; treat as the baseline to beat, not a model.

**The composite lesson:** the Sanskrit DH field has excellent *data* and almost no *design*. VedAnvaya does not need to out-scholar these projects. It needs to be the first one a non-specialist can read without instruction, while remaining citable by a specialist.

## 2.6 Chinese Text Project (ctext.org) and Quran.com

- **ctext.org** actively blocks automated fetching with a scraping/ToS interstitial — I could not analyse the live interface. **[UNVERIFIED by fetch]** Its known contributions (from the literature) are per-character dictionary lookup on click, parallel-passage detection across the corpus, and a dense left navigation tree. Its weakness is visual density without hierarchy.
- **Quran.com** is the single best-engineered *devotional-but-not-decorative* text reader on the web, and its frontend is open source.
  (<https://deepwiki.com/quran/quran.com-frontend-v2>, <https://github.com/nuqayah/qpc-fonts>)
  - **Multi-script rendering with specialised web fonts** — Uthmani, IndoPak, etc. — selectable by the reader. The KFGQPC fonts are distributed **per-page**, so the on-screen line breaks match the printed Madinah Muṣḥaf that readers have memorised against.
  - **Audio with word-level highlighting**, via Howler.js.
  - **Preferences (font choice, translations, night mode) persisted in LocalStorage.**

**Transfer — and this is a direct product requirement:** VedAnvaya has recitation audio. **Word-level or pāda-level highlighting synchronised to audio is the feature that will make the product feel alive**, and Quran.com is the proof that it is achievable with an open stack. The per-page-font insight also matters: *reader memory is attached to a specific visual arrangement of the text.* Reciters know the Rigveda in pādas; our line-breaking must be pāda-faithful, never reflowed prose.

---

# 3. Manuscript presentation on the web, and the real structure of Indic manuscript pages

## 3.1 What an Indian manuscript page actually looks like — measured

The most precise open source I found is the D'source layout study of a Jain paper manuscript (<https://www.dsource.in/course/study-jain-manuscripts/layout-study>). Real numbers:

| Feature | Measurement |
|---|---|
| Folio size | **32.5 cm × 9.4 cm** (≈ **3.46 : 1** landscape; the study calls it "roughly 4:1") |
| Column structure | **Two columns**: left **82 mm**, right **123 mm** — *deliberately unequal* |
| Column border | **5 mm** |
| Margin ratio | **2 : 1 : 2 : 1** — right fore-edge : upper : left fore-edge : foot |
| Side margins | **43 mm** and **42 mm** |
| Column rules | **Thin black double lines filled with red** |
| Folio number (recto side) | Right margin, centred, **inscribed over a red circle** |
| Folio number (other side) | Left margin, **written out in words** |
| String hole | **Centre of the page**, decorated with a red circle or auspicious symbol; **gutter width matches the top margin** to protect the paper from thread damage |
| Lines per column | **6** |
| Line height | **6–7 mm** |
| Leading | **4 mm** |
| Marginal notes | Smaller than the main text |
| Illustration panels | Squarish; divide the two columns into three; occupy top and bottom margins |

Palm-leaf structure (Google Arts & Culture; conservation literature):
- Long rectangular strips, **both sides written**, gathered, **holes drilled through all leaves**, bound with string between **wooden covers** (bamboo or teak, chosen against insects), and the bundle **wrapped in red cloth.**
- In South India, text is **incised with a metal stylus**, then **lampblack mixed with gingelly oil** is rubbed in and wiped off, so the letters appear black against pale leaf. **The mark is a cut that has been filled, not a stroke that has been laid down.**
- Script shape followed material: **angular in Devanagari/Bengali/Assamese, rounded in Telugu/Malayalam/Kannada**, because a stylus on leaf splits along the grain.
(<https://artsandculture.google.com/asset/folios-of-palm-leaf-manuscripts...>, <http://www.ijim.in/wp-content/uploads/2017/07/Vol-2-Issue-II-122-128-paper-17-soumen-Ghosh-PALM-LEAF-MANUSCRIPT.pdf>)

Rubrication and punctuation in Sanskrit codices:
- **Red ink marks daṇḍas, headings, invocations and section divisions**; the main text is black. Rubrication was a **separate production stage**.
- **The daṇḍa (।) and double daṇḍa (॥) are the only punctuation in Sanskrit texts.** In metrical texts the **double daṇḍa delimits verses**; in prose it ends a paragraph, story or section.
- **Foliation appears as letter-numerals or Nepālākṣara numerals in the margin, on the verso.**
(<https://en.wikipedia.org/wiki/Danda>, <https://en.wikipedia.org/wiki/Rubric>, <https://blogs.loc.gov/international-collections/2018/01/sanskrit-manuscripts-in-the-south-asian-rare-books-collection/>)

> Bodleian's South Asian Manuscripts catalogue (<https://south-asian.bodleian.ox.ac.uk/>) has per-manuscript codicological descriptions (dimensions, lines per folio, rubrication) but returned **HTTP 403** to automated fetch. **[UNVERIFIED]** — worth a manual pass to harvest 5–10 real descriptions as design source material.

## 3.2 The abstraction rules — what to take and what to refuse

This is the operative part of §3. Manuscript modernism means extracting **structural logic**, never surface.

**TAKE — these are structure:**

1. **The landscape proportion.** 3.46:1 is the folio. Use it as a *component* ratio — the verse card, the hero band, the citation strip, an OG image — not as the page. A wide, short block is instantly, non-obviously Indic.
2. **The 2:1:2:1 margin ratio.** Side margins twice the top and bottom. This inverts the Western manuscript convention (generous foot) and produces a page that feels *held* rather than *hung*. Apply it to the reading column's container.
3. **Unequal columns (82 : 123 mm ≈ 0.67 : 1).** The manuscript grid is asymmetric by design. This is direct licence for an asymmetric two-column reading layout — **narrow rail : wide text ≈ 2 : 3** — and a documented reason to refuse the centred single column.
4. **The double rule filled with red.** A black hairline, a 3–4 px gap, a second black hairline, with `rubric-red` in the gap. This is a *signature element* available to no other product on earth, it costs 4 lines of CSS, and it is completely non-clichéd. Use it for the top rule of a hymn, the header/content boundary, and the section divider. **This should become the VedAnvaya divider.**
5. **The folio number over a red circle.** Our citation chip — `RV 1.1.1` — set in Inter tabular figures, on a rubric-red ring (not a filled pill). The circle is a real manuscript convention; the pill badge is a Tailwind default. Prefer the ring.
6. **Foliation in two registers** — numerals on one side, *words* on the other. Translation: show the machine address (`RV 1.1.1`) *and* the human address ("Maṇḍala 1, Hymn 1, Verse 1") in the same component, at different weights.
7. **The string hole as a void.** A deliberate, structural blank in the centre of the measure, which the text flows around and which is never filled with content. On a page this is a wide gutter or an intentional negative-space column. **A blank you can justify is the most confident thing a layout can contain.**
8. **Rubrication as function, not decoration.** Red in a Sanskrit manuscript means: *this is a boundary, a heading, an invocation, or an editorial intervention.* Therefore in VedAnvaya, `rubric-red` is permitted **only** for: daṇḍa/verse boundaries, section and hymn headings, the active/current state, editorial corrections and apparatus markers, and the single primary action. **It is never a hover tint, never a gradient stop, never a chart series, never a decorative underline.**
9. **Ink that is filled, not laid.** The palm-leaf incise-and-fill technique argues for **outlined or hairline-ruled forms filled with colour**, rather than solid blocks with drop shadows. A practical rule: **borders before fills; fills before shadows; shadows basically never.**
10. **The double daṇḍa as verse delimiter.** Render `॥` in `rubric-red` at the end of each verse, at reduced opacity. It is typographically correct, culturally exact, and reads as a designed mark to anyone who does not know what it is.

**REFUSE — these are surface:**

- Faux parchment/palm-leaf **textures**, paper grain overlays, torn-edge PNGs, sepia photo filters.
- **Drawn ruling lines mimicking a scribe's ruling across the whole page.** The ruling was a production aid; simulating it is set dressing.
- Border ornament, corner flourishes, "auspicious symbols" as decoration, decorative initials, illuminated capitals.
- A literal string hole with a rendered string or a drilled-hole graphic.
- **Any skeuomorphic page-turn**, book spine, curled corner, or 3D folio.
- Sanskrit text rendered as an image so it "looks authentic." Text is text; it must be selectable, searchable, screen-readable.
- Devanagari used as **texture** — a wall of faint Sanskrit behind a hero. This is the single most common Indic-site cliché.

## 3.3 IIIF and viewers

If VedAnvaya ever displays manuscript images, use IIIF, and pick deliberately:
(<https://iiif.io/get-started/iiif-viewers/>, <https://projectmirador.org/>, <https://training.iiif.io/intro-to-iiif/UNIVERSAL_VIEWER_AND_MIRADOR.html>)

- **Mirador 3** — multi-window workspace for **comparing objects from different institutions side by side**, zoom/pan/rotate, **annotation creation**, saveable workspace state. Built for scholarly comparison. Choose this if witnesses/recensions are ever compared.
- **Universal Viewer** — embeddable, **modular UI component library**, supports IIIF image **plus audio and video**, and non-IIIF 3D and PDF. Choose this if the priority is embedding one object cleanly into an editorial page, or if audio needs to live in the same viewer.

Both ship with their own visual language that will fight `manuscript-ivory`. Budget for a theming layer; do not accept viewer chrome as-is.

## 3.4 Apparatus criticus on the web — the best current practice

Two good sources: the **Library of Digital Latin Texts guidelines** (<https://digitallatin.github.io/guidelines/LDLT-Guidelines.html>) and a practitioner synthesis (<https://digitalrelics.uk/posts/digital-editions/edition-apparatus-display>).

The **LDLT Viewer** presents the apparatus **two ways at once**: *clickable icons in the margin of the text*, and *a traditional apparatus block at the end of each section*. Variant types (e.g. orthographic) can be **filtered out** to reduce on-screen entries.

Distilled best practice, all of it directly usable for VedAnvaya's variant/recension display:

1. **Encode once, render many ways.** TEI `<app>/<lem>/<rdg>`. "Layout becomes a presentation choice, not a data problem."
2. **Offer at least two layouts and let the reader switch.** The three viable ones are: *inline popover* (quick lookup, narrow screens), *foot-of-text collapsible* (systematic reading), *side panel or margin* (wide screens, dense apparatus — "collapses badly on mobile").
3. **Hide by default for a calm reading text — but never hide the existence of a variant.** Always leave "a subtle marker (a small superscript, a tinted word, a margin tick)."
4. **Two-way highlighting.** "Clicking the marked word highlights the apparatus entry; clicking the entry scrolls to and highlights the word."
5. **A global "show all apparatus" switch** for systematic readers.
6. **Keyboard-operable, not hover-only.** A hover tooltip is an accessibility failure and a mobile failure.
7. **Sigla expand on hover *or focus*** to full witness name and shelfmark; **the witness list stays one click away at all times.**
8. **Mobile transforms, not mobile removals:** margin apparatus → tap marker → **bottom sheet**; hover tooltip → tap → **dismissible popover**; large tap targets.

**Transfer:** the "tinted word" marker should be a `rubric-red` **underline or dotted rule**, not a superscript number, because a superscript collides with Vedic accent marks above the śirorekhā. **This is a real, project-specific constraint: the space above Devanagari is already occupied.** Put apparatus markers *below* the line or in the margin rail.

---

# 4. Typographic identity for an archival/scholarly brand

## 4.1 Fraunces at institution scale

**Fraunces** is a variable font with **four axes — Weight (`wght`), Optical Size (`opsz`), Softness (`SOFT`), Wonky (`WONK`)** — commissioned by Google Fonts from **Undercase Type** in 2018 and published October 2020.
(<https://fonts.google.com/specimen/Fraunces/about>, <https://github.com/googlefonts/fraunces>, <https://design.google/library/a-new-take-on-old-style-typeface>)

- **`SOFT`**: controls the "wetness"/inkiness. **`SOFT 0` = sharp and crisp; `SOFT 100` = super-soft rounded terminals.**
- **`WONK`**: a **binary 0–1 switch** that substitutes deliberately irregular alternates — the leaning `h`, `n`, `m` in the roman; the flagged ball terminals of `b d h k l v w` in the italic.
- Undercase shipped SOFT and WONK **as design controls, not weight substitutes**.

Fraunces' reputation is "playful / food / lifestyle branding." That reputation comes entirely from **high SOFT**. **The institutional register is reached by holding SOFT at 0.**

**Recommended axis policy for VedAnvaya:**

| Use | `opsz` | `wght` | `SOFT` | `WONK` |
|---|---|---|---|---|
| Wordmark | 144 | 400–500 | **0** | **1** (one wonk, once — the mark's only idiosyncrasy) |
| Display / hero | 96–144 | 300–400 | **0** | 0 |
| Section headings | 48–72 | 400–500 | **0** | 0 |
| Subheads | 24–36 | 500–600 | **0** | 0 |
| Pull-quote / running text in Fraunces | 14–18 | 400 | **0** | 0 |
| **Never** | — | ≥700 | **>0** | — |

Two hard rules:
- **`opsz` must track the rendered size.** Fraunces at `opsz 144` used at 16px looks anaemic and spindly; at `opsz 9` used at 96px it looks clotted. Bind `font-optical-sizing: auto` and verify — this is the single highest-leverage typographic setting in the whole system, and it is the one people forget.
- **WONK once, or never.** A wonky `h` in the wordmark is a signature. Wonky `h`s throughout the body copy is a gimmick.

Also: Fraunces is an **old-style** design with real optical-size drama. Set the display sizes with **negative tracking (−0.01 to −0.02 em) and tight leading (0.95–1.05)**. Institutional display type is set tight; SaaS display type is set loose.

## 4.2 Fraunces + Inter — making the pairing read as institutional

Inter is the most-used interface font on earth and is explicitly named in the AI-slop literature as a fingerprint (see §6). Using it is fine; using it *by default* is the problem. Make it deliberate:

- **Restrict Inter to genuine UI**: controls, labels, facets, metadata, table data, breadcrumbs, counts, citations. **Never** use Inter for a paragraph of prose. If prose is not in Fraunces, it is in Fraunces.
- **Use Inter's real features**: `font-feature-settings: "tnum" 1` on all citations and counts (a `RV 10.129.1` citation with proportional figures is visibly amateurish); `"ss01"` for the disambiguated single-storey forms if desired; `"cv05"`/`"cv08"` alternates to move it a step away from stock Inter; and `font-variation-settings: "opsz"` on Inter Variable, which most teams never touch.
- **Push the size contrast further than feels comfortable.** The institutional signal is a *large* jump between display and UI — e.g. 72px Fraunces headline over 13px Inter metadata — not a smooth 6-step ramp. Smooth ramps read as SaaS.
- **Set Inter small and let it be small.** 12–13px metadata in `carbon-ink` at 70% opacity, with generous letter-spacing (+0.02em), reads as a museum label. 16px grey `text-gray-500` reads as a component library.

## 4.3 Latin + Devanagari alignment — the real problems and the real solutions

The authoritative practical source is **Alphabettes, "Devanagari Typography 101: A guide for typesetting with Latin"** (<https://www.alphabettes.org/devanagari-typography-101-a-guide-for-typesetting-with-latin/>), supplemented by the **Mota Italic Devanagari documentation** (<https://motaitalic.github.io/devanagari-documentation/languages/devanagari-overview/devanagari-overview.html>) and Pooja Saxena's Devanagari type anatomy (<https://www.type-together.com/devanagari-type-anatomy>).

**The structural fact.** Devanagari has **no baseline-and-x-height system.** The organising element is the **śirorekhā (headline)** from which letters *hang*. "Vertical alignments in Devanagari are not based on notions of baseline and x-height." The baseline is only "a rough guide and alignment zone," because **multiple tiers of conjuncts and vowel signs make the lower part deeper and legibility-critical.**

**Alignment rules (quoted/derived):**

1. **Match Latin x-height to the Devanagari śirorekhā height, not cap height** — "The x-height ... can be comparable to the shirorekha height in Devanagari because of an equally imposing horizontal weight." Cap-height may correspond to upper matra height *in some cases*.
   - Mota Italic's cross-check: the headline "usually sits somewhere between the Latin small-cap height and the cap-height."
   - **Practical implication:** Devanagari set at the same nominal px size as Latin will usually look *too small*. Expect to run Devanagari at **+8% to +15%** and verify optically against `क` vs `o`.
2. **Sentence case Latin next to Devanagari; all-caps needs work.** "Devanagari set in the same pt. size as Latin works better with a sentence case Latin. All caps Latin may need adjustments such as an increased pt. size and a baseline shift." → **Ban all-caps Latin anywhere adjacent to Devanagari.** This kills the eyebrow-label/all-caps-kicker pattern in bilingual contexts, which is a bonus (it is also an anti-pattern, §6).
3. **Left-align, ragged right.** "Justifying Devanagari type can be very tricky." Use **optical alignment and overhangs**, not mathematical alignment. **Never justify Devanagari on the web** (`text-align: justify` is banned for Devanagari).
4. **Devanagari needs more leading than Latin.** "Devanagari may require additional line spacing as compared to the Latin script ... a typographer should carefully control line spacing." Avoid automated leading.
   - **Implementation:** a separate `--leading-deva` token. Start Latin body at `line-height: 1.55` and Devanagari body at **`1.85–2.0`**. Accented Vedic text needs more still — see §5.5.
5. **NEVER letter-space Devanagari.** "Adding letter spacing may create incorrect gaps in the Shirorekha." Tracking literally breaks the headline into fragments. → **`letter-spacing: 0` must be enforced on every Devanagari element**, and any global `letter-spacing` utility must be excluded from Devanagari selectors. This is the #1 way a Tailwind default silently destroys the script.
6. **No hyphenation.** "Hyphenation ... is not traditionally used in Devanagari." → `hyphens: none` on Devanagari.
7. **Weight matching by eye, using `o` vs `क`.** Choose faces with "comparable stroke weight and terminal shapes, along with contrast types." Note the structural inversion: "the letter construction contrast in Devanagari is the opposite of Latin" — yet a standard regular-contrast Devanagari can sit correctly with **serif roman capitals**, which is good news for Fraunces.
8. **Devanagari is unicase — use weight and a second face for hierarchy, not caps.** Suggested devices: a second Devanagari font to match a stylised Latin (the role Latin italics/small-caps play), or **"breaking up the Shirorekha, a curved or stylized shirorekha, a double shirorekha, exaggerated stroke endings."**
   - **For VedAnvaya:** Noto Serif Devanagari = prominent/reading; Noto Sans Devanagari = compact/UI. That is already the correct two-face hierarchy. Add **weight** as the third axis and stop there.
9. **Never add a śirorekhā to Latin letterforms.** Alphabettes calls it "decorative and gimmicky" and **"disrespectful to Devanagari."** → **Absolute ban.** This includes "Sanskrit-style" Latin display fonts, logo treatments with a bar over the wordmark, and any "fusion" lettering. This is the fastest way for VedAnvaya to look like a yoga studio.
10. **Prefer a family that ships both scripts.** "The easiest and most foolproof way ... is by selecting a font family that offers both Devanagari and Latin support." We cannot fully honour this (Fraunces has no Devanagari), so the burden moves to **explicit metric tuning** — see §5.5.

**Vertical rhythm across scripts — the honest answer.** A single baseline grid across Latin and Devanagari is not achievable, because the two scripts do not share an alignment reference. Do not try. Instead:
- Snap **block spacing** (space between paragraphs, headings, rules) to the grid.
- Let **line-height** differ per script inside a block.
- Align **the śirorekhā of the Devanagari line with the cap-height/x-height zone of the adjacent Latin line** only where they are truly side by side (e.g. an interlinear translation) — and do it by measured offset on a per-font-pair basis, not by formula.

---

# 5. Devanagari and Vedic accent typography on the web — evidence and recommendation

## 5.1 What must actually be supported

Vedic accent marks are spread across **three** Unicode blocks, not one — a fact that breaks naive "does this font support Devanagari?" checks:

| Block | Range | Contents |
|---|---|---|
| Devanagari | U+0900–U+097F | **U+0951 (udātta/svarita sign), U+0952 (anudātta sign)**, U+0953, U+0954 |
| **Vedic Extensions** | **U+1CD0–U+1CFF** | **48 code points, 43 assigned**; introduced in Unicode 5.2 (2009); tone marks and Vedic signs, incl. Sāmaveda and Yajurveda notation |
| Devanagari Extended | U+A8E0–U+A8FF | Cantillation/accent marks used with Devanagari |

(<https://en.wikipedia.org/wiki/Vedic_Extensions>, <https://www.unicode.org/charts/PDF/U1CD0.pdf>, <https://en.wikipedia.org/wiki/Devanagari_Extended>)

**A font that covers U+0951/0952 but not U+1CD0–1CFF will render the Rigveda and fail the Sāmaveda.** Given VedAnvaya covers all four Samhitās, the Vedic Extensions block is a hard requirement, not a nice-to-have.

## 5.2 The primary evidence — Peter Scharf's 2023 INDOLOGY comparison

This is the best systematic test I could find, posted to the INDOLOGY list, August 2023:
<https://list.indology.info/pipermail/indology/2023-August/058005.html>

**Conjunct formation (failures out of the full test set):**

| Font | Conjunct failures | Notes |
|---|---|---|
| **Shobhika (Regular & Bold)** | **2** (ṭty, ṭṣṭh) | best in test |
| **Siddhanta** | 4 (ṅkṣṇv, ṅkhn, ddbr, l̃l) | |
| Chandas / Uttara | 7 | |
| LaTeX Skt package | 29 | |
| Sanskrit Text (Windows) | 64 | |
| Sanskrit 2020 | 81 | |
| Sanskrit 2003 | 82 | |
| Praja ($35) | 195 | |
| Arial Unicode MS | 208 | |
| Mangal | 244 | |
| Devanagari MT | 263 | |

**Vedic accent and extended-character support:**

- **Complete:** "Only Sanskrit Text font and Praja font handled them all properly."
- **Near-complete:** Sanskrit 2020 — all except the *Maitrāyaṇī Saṁhitā* midstroke. **Shobhika — all except that and the Sāmaveda accents.** LaTeX Skt — "handles most Vedic accentuation."
- **Most other fonts handled "only the common accentual system."**

**The disqualifying finding.** Scharf notes that **Bayaryn's fonts (Chandas, Uttara, Siddhanta) use *private code points* to handle accents**, and recommends they be upgraded to use the two standard Unicode pages.

> **This is decisive for us.** Private-use code points mean: text does not survive copy-paste, does not index in Elasticsearch, does not match a search query typed in standard Unicode, does not read correctly in a screen reader, and does not round-trip through the corpus pipeline. **Siddhanta and Chandas are excellent print fonts and are unusable for VedAnvaya's web corpus.** This is exactly the class of defect that looks fine in a screenshot and destroys a search product.

Scharf's conclusion: the **first ten fonts are "commendable"; the last three (Arial Unicode MS, Mangal, Devanagari MT) "are inadequate for Sanskrit."**

Also recorded in the same thread (Harry Spier): the **Tiro Sanskrit** font "adds some more conjunct ligatures" and includes **"support for Vedic characters"**, with **Google funding enabling it to be open-sourced.**

## 5.3 Candidate-by-candidate assessment

| Font | Vedic Extensions? | Standard code points? | Licence | Web/WOFF2 | Verdict |
|---|---|---|---|---|---|
| **Noto Serif Devanagari** | **Yes** — officially "272 characters from 6 Unicode blocks: Devanagari, **Vedic Extensions**, Devanagari Extended, Basic Latin, General Punctuation, Common Indic Number Forms"; 871 glyphs, 18 OT features; variable. (<https://notofonts.github.io/noto-docs/specimen/NotoSerifDevanagari/>) | Yes | OFL 1.1 | **Yes — Google Fonts API serves WOFF2** | **KEEP as primary.** Coverage confirmed; depth of accent *positioning* unverified — must be tested (§5.4). |
| **Noto Sans Devanagari** | Yes (same Noto Vedic coverage family) | Yes | OFL 1.1 | Yes | **KEEP as compact/UI.** |
| **Tiro Devanagari Sanskrit** | **Yes** — "support for Vedic accents and notational systems"; extended for the OFL release to add "signs for Vedic texts." Origin: commissioned 2012 by Harvard UP from **Fiona Ross & John Hudson** for the **Murty Classical Library of India**; Google approached Tiro in 2019 to extend and open-source it. Regular + Italic (italic by Paul Hanslow). Latin includes **IAST transcription diacritics**. (<https://www.tiro.com/fonts/tiro-devanagari-sanskrit>, <https://design.google/library/the-modern-tiro-indic-collection-font>) | Yes | **OFL 1.1** | **Yes — on Google Fonts** | **ADOPT as the accented-verse face / first fallback.** This *is* "Murty Sanskrit, free." |
| **Shobhika** | **Almost** — "svarita, dīrgha-svarita, anudātta ... and a number of other vedic accents and nasalisation marks required for the proper typesetting of ṛgveda and yajurveda"; 1600+ Devanagari glyphs, 1100+ conjuncts; Devanagari + Latin + **Cyrillic**; Regular + Bold. Built at **IIT Bombay** (CISTS + IDC), led by **Aditya Kolachana** under **Prof. K. Ramasubramanian** and **Prof. Girish Dalvi**. **Scharf: all Vedic accents except the Sāmaveda accents and the Maitrāyaṇī midstroke.** (<https://github.com/Sandhi-IITBombay/Shobhika>, <https://ctan.org/pkg/shobhika>) | Yes | **OFL 1.1** | Not on Google Fonts; **TTF from GitHub releases → self-convert to WOFF2** | **ADOPT as self-hosted second fallback** — best-in-test conjuncts (2 failures), explicitly Rigveda/Yajurveda-tuned. |
| **Adishila** (family: Adishila, Adishila San, Adishila Dev, Adishila Samskrta) | **Yes** — "Vedic and Devanagari Extended Unicode character sets" + Latin with IAST; up to 8 weights; revivals of **Vanivilas Press, Srirangam / Nirnay Sagar** types; letterpress variants. (<https://adishila.com/fonts/>) | Yes | **BLOCKING:** "you are not allowed to sell, rent, or carry out any related monetary transactions, **host or distribute them**." | **NO** | **REJECT for web.** The licence forbids hosting — a self-hosted webfont *is* hosting and distributing. Beautiful; legally unusable as a webfont. Usable in print/PDF exports only, and even then check. |
| **Siddhanta** | Yes (claims full Vedic + Devanagari Extended) | **NO — private code points for accents** (Scharf) | Unclear | No official WOFF2 | **REJECT.** Breaks search, copy-paste, a11y. |
| **Chandas / Uttara** | Partial | **NO — private code points** (Scharf); Chandas is GPL | GPL (Chandas) | No | **REJECT.** Same reason; GPL on a webfont is also a licensing trap. |
| **Sahadeva** | No specific evidence found; part of the legacy sanskritweb.net family (<http://www.sanskritweb.net/fonts/>) | Unverified | Unverified | No | **[UNVERIFIED] — REJECT by default.** Legacy desktop font; no evidence of Vedic Extensions or web distribution. |
| **Murty Sanskrit** | — | — | — | — | **Superseded:** the free, extended, open-source descendant is **Tiro Devanagari Sanskrit**. Use that name. |
| **Pragati / Pragati Narrow** | **No evidence** of Vedic support. Libre Devanagari sans designed as a companion to **Archivo Narrow**, by Omnibus Type. (<https://github.com/Omnibus-Type/PragatiNarrow>) | Yes | OFL 1.1 | Yes (Google Fonts) | **UI/label use only — never for accented verse.** |
| **Mukta** | **No evidence** of Vedic support. Ek Type; Unicode-compliant, contemporary, **mono-linear, 7 weights**, Devanagari + Gujarati + Gurmukhi + Tamil + Latin. (<https://github.com/EkType/Mukta>) | Yes | OFL 1.1 | Yes (Google Fonts) | **UI use only.** Mono-linear — too low-contrast to sit with Fraunces. |
| **Vesper Libre** | **No evidence** of Vedic support. Devanagari begun by **Rob Keller** (2006), completed 2014 with **Kimya Gandhi**. | Yes | OFL 1.1 | Yes (Google Fonts) | **Display/consider-only.** Genuinely handsome, high-contrast — a possible *display* Devanagari companion to Fraunces, but must not be used where accents appear. |
| **BharatiVaidika** | **Could not locate any authoritative source** in open search. | — | — | — | **[UNVERIFIED — cannot recommend.]** Treat as not existing until someone produces a repository and licence. |
| **Anek Devanagari** *(not on the brief's list, but relevant)* | No Vedic claim | Yes | OFL 1.1 | Yes (Google Fonts, **variable: `wght` + `wdth`**, 8 weights × 5 widths = 40 styles) | Ek Type / Kailash Malviya. Strong **UI** Devanagari with a width axis — a real alternative to Noto Sans Devanagari for compact labels. |

## 5.4 The rendering bug that will bite this project

There is a **long-standing, documented Vedic rendering defect** involving tone markers and post-base visarga/anusvāra:
(<https://corp.unicode.org/pipermail/unicode/2019-December/008430.html>)

- **U+0951 and U+0954 have canonical combining class (CCC) = 230. Visarga has CCC = 0.** The mismatch causes normalisation/reordering conflict.
- Result: **`यः॑` and `यः॔` (visarga *before* the tone mark) produce a dotted circle for U+0954 and broken mark positioning in both cases**; putting visarga *after* the tone marks produces a dotted circle on the visarga instead. Reported against Mangal, but the underlying cause is the shaping engine.
- The proposed fix is engine-side: "the simplest solution would be for the Indic shaping engines to suppress the dotted circle for VISARGA (or ANUSVARA) where appropriate."

Separately, **browser shaping differs**: Chrome uses HarfBuzz shaper-driven segmentation (best font/codepoint-sequence match, tends to keep combined sequences in one font), while **Safari and Firefox scan fonts for coverage first, then segment.** This means **a font-fallback chain behaves differently across browsers for combining marks** — a Devanagari base glyph from font A with an accent from font B is a real possibility in Firefox/Safari and a visual disaster.

**Consequence — two hard engineering requirements:**

1. **Never rely on a fallback chain for accented Vedic text.** The verse element must specify **one** font that covers the whole sequence. Fallback is for the *absence* of the font, not for the absence of a glyph.
2. **Build a rendering test harness before choosing.** It must render, per candidate font, per browser (Chromium / Firefox / WebKit):
   - every code point in U+1CD0–U+1CFF, U+A8E0–U+A8FF, and U+0951–U+0954;
   - `क` + each accent; `क` + mātrā + accent; conjunct + accent;
   - the **visarga/anusvāra ± tone mark ordering cases above**;
   - real lines from all four Samhitās, including Sāmaveda numeric notation;
   - assert **zero dotted circles (U+25CC)** and **zero `.notdef`/tofu**.
   Screenshot-diff it. This is cheap and it is the only way to know.

> Project note: VedaGraph's own history includes an accent-placement gate that **passed perfectly per line and failed at band scale** (0/21 released at band scale vs 1.000 agreement line-by-line). The same failure mode applies to type rendering: **a font that renders one verse correctly can fail on a page of them.** Test at page scale, not glyph scale.

## 5.5 Recommendation (with evidence)

**Primary stack — adopt this:**

```css
/* Reading Sanskrit, prominent, accented — Rigveda/Yajurveda/Atharvaveda */
--font-sanskrit-read: "Noto Serif Devanagari", serif;

/* Accented verse where Vedic Extensions density is high, and Samaveda */
--font-sanskrit-vedic: "Tiro Devanagari Sanskrit", "Shobhika", serif;

/* Compact Sanskrit — labels, chips, graph nodes, table cells */
--font-sanskrit-ui: "Noto Sans Devanagari", sans-serif;
```

**Rationale, stated as evidence:**

1. **Keep Noto Serif Devanagari as primary.** It is the only candidate that is simultaneously (a) documented to cover the **Vedic Extensions** block, (b) **OFL**, (c) served as **WOFF2 from Google Fonts** with subsetting, and (d) **variable**, so weight hierarchy costs no extra requests. The fixed-palette brief already names it; the evidence supports keeping it.
2. **Add Tiro Devanagari Sanskrit.** It is the only face in this list *designed for the job* — built by Fiona Ross and John Hudson for the Murty Classical Library, extended specifically with "signs for Vedic texts" for the OFL release, OFL 1.1, on Google Fonts. It also carries **IAST Latin diacritics in the same family**, which solves transliteration rendering in one stroke. If the harness in §5.4 shows it out-positions Noto on accents, **promote it to primary for verse** and keep Noto for running Sanskrit prose.
3. **Self-host Shobhika as the scholarly fallback.** Best conjunct performance in the only systematic public test (2 failures vs Siddhanta's 4 and Sanskrit 2003's 82), explicitly built for **Rigveda and Yajurveda** typesetting by IIT Bombay, OFL 1.1. Known gap: **Sāmaveda accents** — so it is a fallback, not the answer for SV.
4. **Reject Siddhanta, Chandas, Uttara outright** — private code points break the corpus contract. This is a data-integrity decision, not an aesthetic one.
5. **Reject Adishila for web** — its licence forbids hosting and distribution.
6. **Treat Pragati, Mukta, Vesper Libre as Latin-adjacent UI/display faces only**; no evidence of Vedic coverage, therefore never on an accented string.
7. **BharatiVaidika and Sahadeva: unverified.** Do not put an unverifiable font in a shipped stack.
8. **Sāmaveda is the open risk.** No free font in this survey is documented as fully handling Sāmaveda accents (Shobhika explicitly excludes them; only the non-free/system Sanskrit Text and Praja handled "all"). **Name this as a blocker now, before SV rendering is promised in the UI.** Possible mitigations: verify Tiro's SV coverage empirically; or render SV notation from the graph as designed marks rather than relying on font glyphs.

**Typesetting parameters for accented Devanagari (implementation):**

```css
.verse-sa {
  font-family: var(--font-sanskrit-vedic);
  font-size: clamp(1.35rem, 1.1rem + 0.9vw, 1.9rem); /* ~+12% over Latin body */
  line-height: 2.05;          /* accents live above the śirorekhā; 1.5 clips them */
  letter-spacing: 0;          /* MANDATORY — tracking shatters the śirorekhā */
  text-align: start;          /* never justify */
  hyphens: none;
  font-feature-settings: "kern" 1;
  font-variant-ligatures: normal;   /* do NOT disable — conjuncts are ligatures */
  text-rendering: optimizeLegibility;
}
```

Three notes on that block:
- **`line-height: 2.05` is not generosity, it is clearance.** Anudātta sits below the baseline, svarita above the śirorekhā, and both can coexist on one akṣara. At 1.5 the marks collide with the line above and the browser clips them without warning.
- **Never `font-variant-ligatures: none` or `font-feature-settings: "liga" 0` on Devanagari.** Conjuncts are implemented as ligatures/substitutions; disabling them destroys the script. Some CSS resets do this globally — audit for it.
- **Any global `letter-spacing` utility must be excluded from `[lang="sa"]`.** Add a lint rule.

---

# 6. Anti-patterns — the exact visual tells

## 6.1 The documented "AI-generated / default Tailwind" fingerprint

The sameness has a traceable origin: **in August 2025 Tailwind's creator Adam Wathan publicly apologised for making every button in Tailwind UI `bg-indigo-500` five years earlier, "leading to every AI generated UI on earth also being indigo."** Models trained on that corpus learned "modern web design = purple buttons."
(<https://saschb2b.com/blog/same-same-but-different>, <https://axe-web.com/insights/ai-website-design-sameness/>, <https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website>, <https://www.designsystemscollective.com/is-anyone-else-tired-of-every-tailwind-shadcn-app-looking-the-same-69c545e73114>)

Named tells from those sources — **all banned:**

**Colour**
- `bg-indigo-500` / Tailwind blue as primary.
- Purple→cyan or violet gradients anywhere.
- Gradient text on headlines or on metric numbers.
- A single saturated "brand colour" applied uniformly to every interactive thing.
- Timid all-grey palettes with one accent.

**Typography**
- **Inter as the only typeface**, at default weights, default tracking.
- Gradient-filled display type.
- A smooth 6-step type ramp with no dramatic jump.
- All-caps tracked-out "eyebrow" labels above every heading.

**Layout & components**
- **The dark hero with a radial glow** behind centred text.
- **Centred headline + subhead + two buttons, one filled and one outlined.**
- **Three feature cards in a row, each with a small icon.** (The "card grid of 3" is the single most reliable tell.)
- Cards nested inside cards inside cards.
- Glassmorphism (backdrop-blur + white/10 border) applied everywhere.
- White surface + floating action button.
- Everything centred; everything the same width; every section the same height.

**Motion**
- Bounce / elastic easing.
- `hover:scale-105` on every card.
- Fade-up-on-scroll applied uniformly to every element.
- Shimmer skeletons that persist after the data has loaded.

## 6.2 The extended, VedAnvaya-specific ban list

Additions from direct observation of the pattern space. Each is a concrete, checkable tell:

**Geometry & spacing**
1. **A single border-radius token used everywhere** — 8px on buttons, cards, inputs, avatars, images, modals and badges alike. Institutions use *mixed* geometry: sharp rules, sharp text blocks, and at most one soft element.
2. **`max-w-7xl mx-auto` on every section**, producing identical content width from hero to footer.
3. **Uniform vertical section padding** (`py-24` everywhere). Real editorial rhythm is uneven.
4. **8px-multiple spacing with no exceptions.** A system that never breaks its own grid reads as generated.
5. **Symmetric padding on asymmetric content** — a card with 24px on all four sides regardless of what's inside.

**Components**
6. **Pill badges** (`rounded-full px-3 py-1 text-xs bg-*-100 text-*-700`). Instantly recognisable. Use a **ring**, an **underline**, or **plain small caps with a rule** instead.
7. **Icon-in-a-rounded-square**, typically 40–48px with a tinted background and a 20–24px icon centred in it.
8. **Lucide (or Heroicons) at 24px inside a circle.** The icon set itself is fine; the circle is the tell. Also: institutions use **almost no icons** — they use words.
9. **`shadow-lg` / `shadow-xl` on resting elements.** Shadow should indicate a *raised* state, not a default one.
10. **Stat strips of exactly four numbers** with a big number over a small label, evenly spaced.
11. **Testimonial carousel. "Trusted by" logo row. Pricing table. FAQ accordion at the bottom of the page.** None of these belong on a research product.
12. **A newsletter modal or sticky CTA bar.**
13. **Avatar stacks with negative margin overlap.**
14. **Gradient borders** (`bg-gradient` on a wrapper + inset child).
15. **Emoji in section headings**, and **"✨" / sparkle motifs** anywhere.

**Content shape**
16. **Three of everything.** Three features, three steps, three testimonials, three pricing tiers.
17. **Every section introduced by an eyebrow + centred H2 + centred one-sentence subhead.**
18. **Verbs from the SaaS register:** "Get Started", "Learn More", "Unlock", "Supercharge", "Seamlessly", "Powerful", "Effortless".
19. **Placeholder-flavoured stats** — "10,000+ verses" set in a giant gradient number with no source.

**Domain-specific — the Indic-cliché ban list**
20. Om symbol (ॐ), lotus, temple silhouette, diya, chakra, generic mandala, "sacred geometry" background, Sri Yantra.
21. **Saffron→gold gradient.** Also: saffron as a large field colour at all.
22. **A faint Devanagari wall as hero background texture.**
23. **Faux-Sanskrit Latin display fonts** (Samarkan, Kailasa and their descendants) — and the related sin of adding a bar over a Latin wordmark.
24. Parchment/palm-leaf **texture** images, sepia filters, torn-paper edges, scroll graphics.
25. **A rotating mandala as a loading spinner.**
26. Sanskrit set as an image.
27. Meditation-app gradient (soft purple→peach), Ayurveda-brand sage-and-terracotta, astrology-app starfield, crypto-graph neon node diagram, spiritual-SaaS glassmorphism.
28. **A force-directed graph with glowing nodes on a dark background** — the crypto/AI-tool default. A knowledge graph rendered this way says "blockchain," not "scholarship."

## 6.3 The positive inversion — what to do instead

| Instead of | Do |
|---|---|
| Card with shadow | Block bounded by a **hairline rule** above it |
| Pill badge | **Ring** or small-caps label with a rubric-red rule |
| Icon in a circle | **A word**, or nothing |
| Three equal cards | **One large, two small** — or a list with rules |
| Centred hero | **Left-aligned hero with an asymmetric counterweight** (§7.3) |
| Gradient accent | **One flat rubric-red mark**, used sparingly |
| Uniform `py-24` | **A rhythm of 3 unequal spacing steps** |
| `hover:scale-105` | **Rule colour shift** + 120ms opacity |
| Glassmorphism | **Solid ivory with a hairline** |
| Stat strip of 4 | **One number, in Fraunces, with a sourced caption** |
| Force-directed glowing graph | **Ruled, typographic adjacency lists** + one purpose-built visualisation (Sefaria's ratio) |

---

# 7. Layout recommendations — specific and opinionated

## 7.1 The grid — an asymmetric 12-column with a margin rail

Justified by two independent findings: the **Jain manuscript's deliberately unequal columns (82 mm : 123 mm ≈ 2 : 3)** and the **institutional rejection of centred sameness**.

**Reading page (≥1280px), 12 columns, 24px gutters:**

```
| 1  2  3 | 4  5  6  7  8  9 | 10  11  12 |
|  RAIL   |      MEASURE      |  APPARATUS  |
| 3 cols  |      6 cols       |   3 cols    |
```

- **Rail (cols 1–3):** the folio address. Citation (`RV 1.1.1`), maṇḍala/hymn/verse in words, metre, deity, seer, audio control. Sticky. Right-aligned against the measure, so the rule between rail and measure is the page's spine. **Everything in Inter, 12–13px, tabular figures.**
- **Measure (cols 4–9):** the verse and its translation. Nothing else ever enters this column.
- **Apparatus (cols 10–12):** variants, connections, notes. **Collapsible to zero**, in which case the measure shifts to cols 4–10 and the page stays left-weighted — it does **not** re-centre. (Re-centring on collapse is the tell that a layout has no opinion.)

**Below 1024px:** apparatus collapses to markers + bottom sheet (per §3.4); rail collapses to a single sticky citation strip at the top.

**Editorial / essay pages:** 2 columns — a **wide left margin rail** (cols 1–3) holding running heads, figure captions, sidenotes and citations, and text in cols 4–9. **Sidenotes in the rail, never footnotes at the bottom.** This is the Tufte/critical-edition move and it is unmistakably scholarly.

**Home / browse pages:** break the grid deliberately once. One full-bleed band at the manuscript ratio (**3.46:1**) is worth more than ten evenly-padded sections.

## 7.2 Measure and line length

Evidence: Bringhurst's **45–75 characters** for a single-column serif page, **66 widely regarded as ideal**; Dyson & Haselgrove found **~55 CPL** supports effective reading at both normal and fast speeds; novices do best around **45 CPL**, experts tolerate up to **80**.
(<http://webtypography.net/2.1.2>, <https://baymard.com/blog/line-length-readability>, <https://blogs.oregonstate.edu/calverta/line-width-in-digital-typography-for-accessibility-and-comprehension/>)

**Recommendations:**

| Content | Measure | Notes |
|---|---|---|
| English prose (essays, notes) | **62–68ch** | `max-width: 34rem–38rem` at 18px Fraunces |
| English translation beside Sanskrit | **52–58ch** | shorter, because the eye is alternating between scripts |
| Sanskrit (Devanagari) verse | **~38–45 akṣara** — roughly **28–32rem** | **Narrower than Latin.** The śirorekhā is a continuous horizontal stroke; a long line of it degrades return-sweep accuracy in a way Latin does not. There is no published CPL study for Devanagari that I could find **[UNVERIFIED — this is a reasoned recommendation, test it]**, but the structural argument is sound and Indic printed editions run short measures. |
| Metadata / apparatus in the rail | **28–34ch** | small type, short lines |
| Table/data cells | n/a | tabular figures, right-aligned numerics |

**Do not use `ch` units on Devanagari** — `ch` is the advance of `0`, which has no relationship to akṣara width. Use `rem` with an empirically checked value.

## 7.3 The hero that is not a centred blob

Three patterns, any of which is defensible; **pick one and commit:**

**(A) The folio band.** A single full-bleed band at **3.46:1**, `manuscript-ivory` ground, containing **one real verse** in large Noto Serif/Tiro Devanagari, left-set in the measure column, with its translation beneath at half the size, and the citation in the rail. The product name appears only in the header. **The hero is the corpus, not a claim about the corpus.** This is the Rijksstudio "image as the interface" move, transposed to text. **Recommended.**

**(B) The asymmetric split, 5:7.** Left five columns: the wordmark, a one-line statement in Fraunces at 56–72px, and a single search field (full width of the five columns, hairline-bordered, no rounded corners, no icon). Right seven columns: a live, quiet visualisation — e.g. the ten maṇḍalas as ten unequal vertical bars sized by hymn count, in `indigo-ink`, with one bar in `rubric-red`. **Never 50/50 — 50/50 reads as a template.**

**(C) The index page.** No hero at all. The home page opens directly into the corpus: a ruled index of the four Samhitās with counts, an immediate search field in the header, and the five node-type entries (Deities / Seers / Metres / Concepts / Formulae) as a ruled row. This is the most institutional option and the most confident. It is also the hardest to sell to stakeholders.

**In all three:** the search input is present **above the fold, in the header, on every page** — Cooper Hewitt's "global input field goes straight to the results page."

## 7.4 Section rhythm

Editorial rhythm is **uneven by design**. Use exactly **three** vertical spacing steps and alternate them:

- `--space-section-tight: 4rem`
- `--space-section: 7rem`
- `--space-section-loose: 11rem`

Rules of rhythm:
1. **Never use the same step twice in a row.**
2. **A section that follows a rule gets tight spacing above and loose below** — the rule is doing the separating work, so space above it is wasted.
3. **One section per page is allowed to be twice the height of any other.** That is the section the page is about.
4. **Alternate the alignment axis.** If section *n* is left-set in the measure column, section *n+1* should span the full grid or sit right-of-rail. Alternating axis is what makes a long page feel authored.
5. **No section may be introduced by a centred eyebrow + centred H2 + centred subhead.** Headings sit at the left edge of the measure, with the section number/label in the rail beside them.

## 7.5 Hairlines vs cards — the decision rule

**Use a hairline when** items share a type and are read in sequence (search results, verse lists, connection lists, index entries, metadata rows). A ruled list scans faster than a card grid because the eye tracks one left edge.

**Use a card (a bounded block) only when** an item is genuinely a different kind of object from what surrounds it, and there are **fewer than four** of them on the page.

**Hairline specification:**
- Default: `1px solid rgba(23, 24, 21, 0.14)` — `carbon-ink` at 14%, never a grey.
- **The VedAnvaya divider** (the manuscript double rule): two `carbon-ink` hairlines at 18% with a **3px** gap between them filled with `rubric-red` at 100%. Use for hymn openings, the header/content boundary, and the footer boundary. **Nowhere else** — scarcity is what makes it a signature.
- Section rules: **full-bleed to the grid edge, not inset**. Inset rules with equal margins read as a component; full-bleed rules read as a page.
- **Never `border-radius` on a rule, a table, or a text block.**

## 7.6 Colour application rules

- **`manuscript-ivory #F4F0E7` is the only ground.** No white cards on ivory; if a surface must lift, lighten to `#FAF7F1` or darken to `#EDE8DC` — never introduce `#FFF`.
- **`carbon-ink #171815` for all text.** Secondary text is `carbon-ink` at **62%** opacity, not a grey token. Tertiary at **44%**. Keeping everything on one ink is what makes the page look printed rather than themed.
- **`rubric-red #B64A2E`: the rubrication rule.** Permitted uses, exhaustively: daṇḍa/double-daṇḍa marks; hymn and section headings' leading mark; the current/active state; apparatus and correction markers; the single primary action per view; the one highlighted element in a data visualisation. **Target: under 2% of pixels on any screen.** Banned: hover fills, gradients, chart palettes, large fields, body text.
- **`aged-gold #B49A62`: rare** means *at most one element per page*, and usually zero. Best use: a hairline under the wordmark, or the audio-progress fill. **Never as a text colour** (contrast fails on ivory).
- **`indigo-ink #26364A`: the data colour.** Graph edges, chart series, secondary links, code/technical surfaces. Because it is the only cool colour in the palette, it automatically reads as "machine/derived" against the warm ink — use that: **ink for what the Veda says, indigo for what we computed.** That is an honest and legible semantic split, and it directly serves an evidence-backed product.
- **Dark mode:** invert to `#171815` ground with `#F4F0E7` text at 88%, and **desaturate rubric-red to `#C9613F`** or it will vibrate. Test it; do not ship it untested.

## 7.7 Type scale (concrete)

Fluid, with a genuine jump between display and UI:

| Role | Font | Size | Leading | Tracking |
|---|---|---|---|---|
| Display | Fraunces `opsz 144, wght 300, SOFT 0` | `clamp(2.75rem, 2rem + 3.5vw, 5.5rem)` | 0.98 | −0.02em |
| H1 | Fraunces `opsz 72, wght 400` | `clamp(2rem, 1.6rem + 1.8vw, 3.25rem)` | 1.08 | −0.015em |
| H2 | Fraunces `opsz 48, wght 400` | 2rem | 1.15 | −0.01em |
| H3 | Fraunces `opsz 36, wght 500` | 1.375rem | 1.25 | 0 |
| Body (English) | Fraunces `opsz 18, wght 400` | 1.125rem | 1.55 | 0 |
| Sanskrit verse | Noto Serif / Tiro Devanagari | `clamp(1.35rem, 1.1rem + 0.9vw, 1.9rem)` | **2.05** | **0** |
| Sanskrit compact | Noto Sans Devanagari | 0.95rem | 1.7 | **0** |
| UI / label | Inter `wght 500` | 0.8125rem (13px) | 1.4 | +0.02em |
| Metadata / citation | Inter `wght 400`, `tnum` | 0.75rem (12px) | 1.45 | +0.03em |

Note the **ratio between Display (up to 88px) and Metadata (12px) is over 7:1**. That gap is the institutional signal.

## 7.8 Motion

- Duration **120–200ms**; easing `cubic-bezier(0.2, 0, 0.13, 1)`. No bounce, no elastic, no spring.
- **Animate opacity and colour. Do not animate scale or translate on content.**
- Panel/rail transitions may translate, at 200ms.
- **Respect `prefers-reduced-motion` by removing transitions entirely**, not by shortening them.
- **No scroll-triggered reveal animations on text.** A scholarly text that fades in as you scroll is a text that is not there when you search the page.

## 7.9 Ten rules to hand to the implementer

1. The ground is `manuscript-ivory`; there is no `#FFF` anywhere.
2. All text is `carbon-ink` at 100 / 62 / 44 percent. There are no grey tokens.
3. `rubric-red` marks boundaries, states and editorial acts. Under 2% of pixels.
4. Hairlines divide; cards are exceptional and never nested.
5. Nothing is centred except the one element that is deliberately centred.
6. The measure never exceeds 68ch for Latin or ~45 akṣara for Devanagari.
7. `letter-spacing: 0` and `hyphens: none` on every Devanagari element, enforced by lint.
8. Devanagari verse leading is ≥ 2.0 because the accents need the room.
9. Fraunces runs at `SOFT 0`, with `opsz` bound to rendered size.
10. Every verse is addressable by URL, exportable, and cited in full — the interface's job is to make that legible, not to decorate it.

---

# 8. Open questions and named blockers

1. **Sāmaveda accent coverage is unresolved.** No free, web-distributable font in this survey is documented as fully rendering Sāmaveda accents. Shobhika explicitly excludes them; only non-free Sanskrit Text and Praja handled "all" in Scharf's test. **Verify Tiro Devanagari Sanskrit empirically before promising SV display.**
2. **Getty, Smithsonian Open Access, Bodleian South Asian Manuscripts, Sefaria Help Center and ctext.org all returned 403 or an empty SPA shell to automated fetch.** Their findings here are corroborated from secondary sources or marked unverified. A manual screenshot pass would close this.
3. **BharatiVaidika could not be located** in any authoritative source. Either someone has a repository/licence for it, or it should be struck from the candidate list.
4. **No published CPL (characters-per-line) readability study for Devanagari** was found. The ~38–45 akṣara recommendation in §7.2 is reasoned from the śirorekhā's return-sweep effect and from printed Indic practice; it should be user-tested.
5. **The visarga/tone-mark ordering bug** (§5.4) is a shaping-engine issue, not a font issue. It may affect our corpus if any Samhitā line puts visarga adjacent to U+0951/U+0954. **Grep the corpus for those sequences before choosing a font.**
6. **Devanagari + Latin metric tuning** cannot be derived from documentation; it requires measuring the chosen Fraunces/Noto/Tiro combination and hard-coding an offset. Budget for it.

---

# 9. Source index

**Institutions**
- Rijksmuseum identity (Irma Boom Office; Bold Monday / Paul van de Laan) — https://atypi.org/presentation/the-new-rijksmuseum-identity-and-typeface-family/
- Rijksstudio mobile-first redesign (MW18) — https://mw18.mwconf.org/paper/rijksmuseum-mobile-first-redesign-rijksstudio-the-new-rijksmuseum-app/index.html
- Rijksmuseum design critique (grid, whitespace, accessibility) — https://ixd.prattsi.org/2023/09/design-critique-rijksmuseum-website/
- Cooper Hewitt typeface (Chester Jenkins / Village, OFL) — https://www.cooperhewitt.org/open-source-at-cooper-hewitt/cooper-hewitt-the-typeface-by-chester-jenkins/
- Cooper Hewitt identity (Pentagram / Eddie Opara) — https://www.pentagram.com/work/cooper-hewitt-smithsonian-design-museum-1/story
- Cooper Hewitt search & browse redesign (MW2015) — https://mw2015.museumsandtheweb.com/paper/reconsidering-searching-and-browsing-on-the-cooper-hewitts-collections-website/index.html
- Cooper Hewitt Labs — https://labs.cooperhewitt.org/
- V&A new website rationale — https://www.vam.ac.uk/blog/digital/new-website
- V&A typefaces (TheSans / V&A Sans) — https://fontsinuse.com/uses/25490/vand-a-website
- V&A Explore the Collections — https://www.vam.ac.uk/blog/digital/new-website ; https://collections.vam.ac.uk/
- Wellcome Collection design vision — https://wellcomecollection.org/our-design-vision
- Wellcome digital strategy (three sites into one) — https://stacks.wellcomecollection.org/a-digital-strategy-for-wellcome-collection-1b43e5365331
- Europeana design approach — https://pro.europeana.eu/post/exploring-europeana-s-approach-to-design
- Europeana design process — https://pro.europeana.eu/post/a-behind-the-curtains-look-at-europeana-s-design-process-and-next-steps
- Tate custom typeface — https://newlyn.com/blog/the-face-of-tate

**Digital humanities / scholarly interfaces**
- VedaWeb — https://vedaweb.uni-koeln.de/rigveda/
- VedaWeb source — https://github.com/VedaWebProject/vedaweb ; https://github.com/VedaWebProject/vedaweb-legacy
- VedaWeb project (DFG GEPRIS) — https://gepris.dfg.de/gepris/projekt/329358806?language=en
- VedaWeb co-development paper (CEUR) — https://ceur-ws.org/Vol-2365/05-TwinTalks-DHN2019_paper_5.pdf
- VedaWeb annotations paper — https://convegni.unica.it/hicov/files/2019/01/Koelligan-et-al.pdf
- Sefaria Resource Panel — https://help.sefaria.org/hc/en-us/articles/18472472138652-Quick-Guide-Meet-the-Sefaria-Library-Resource-Panel
- Sefaria connections in practice — https://www.sefaria.org/sheets/219447 ; https://www.sefaria.org/sheets/63158
- Sefaria link types — https://developers.sefaria.org/docs/commentaries
- Sefaria Link Explorer — https://www.sefaria.org/explore
- Scaife Viewer — https://scaife.perseus.org/ ; https://github.com/scaife-viewer/scaife-viewer
- Scaife Viewer review (SCS) — https://classicalstudies.org/scs-blog/stephensansom/review-perseus-digital-library-scaife-viewer
- Scaife Viewer overview — https://libraryofantiquity.wordpress.com/2018/04/07/perseus-5-0-viewer-overview/
- Ambuda — https://ambuda.org/
- GRETIL — https://gretil.sub.uni-goettingen.de/gretil.html
- Bibliotheca Polyglotta — https://www2.hf.uio.no/polyglotta/index.php
- Digital Corpus of Sanskrit — http://www.sanskrit-linguistics.org/dcs/ (TLS cert mismatch)
- Chinese Text Project — https://ctext.org/ (blocks automated access)
- Quran.com frontend v2 — https://deepwiki.com/quran/quran.com-frontend-v2
- KFGQPC per-page Quran fonts — https://github.com/nuqayah/qpc-fonts

**Manuscripts, IIIF, apparatus**
- Jain manuscript layout study (measurements) — https://www.dsource.in/course/study-jain-manuscripts/layout-study
- Palm-leaf manuscript surfaces — https://dsource.in/course/study-jain-manuscripts/process-making/surfaces/palm-leaf-manuscripts
- Palm-leaf conservation (technique, binding) — http://www.ijim.in/wp-content/uploads/2017/07/Vol-2-Issue-II-122-128-paper-17-soumen-Ghosh-PALM-LEAF-MANUSCRIPT.pdf
- Sanskrit manuscripts at the Library of Congress (red ink, layout) — https://blogs.loc.gov/international-collections/2018/01/sanskrit-manuscripts-in-the-south-asian-rare-books-collection/
- Bodleian South Asian Manuscripts — https://south-asian.bodleian.ox.ac.uk/ (403 to fetch)
- Daṇḍa — https://en.wikipedia.org/wiki/Danda
- Rubric / rubrication — https://en.wikipedia.org/wiki/Rubric
- IIIF viewers — https://iiif.io/get-started/iiif-viewers/
- Mirador — https://projectmirador.org/
- UV vs Mirador — https://training.iiif.io/intro-to-iiif/UNIVERSAL_VIEWER_AND_MIRADOR.html
- LDLT encoding guidelines (apparatus display) — https://digitallatin.github.io/guidelines/LDLT-Guidelines.html
- Best practices for critical apparatus on the web — https://digitalrelics.uk/posts/digital-editions/edition-apparatus-display

**Typography**
- Fraunces on Google Fonts — https://fonts.google.com/specimen/Fraunces/about
- Fraunces source — https://github.com/googlefonts/fraunces
- Fraunces (Google Design) — https://design.google/library/a-new-take-on-old-style-typeface
- Fraunces axes explained — https://fontaza.com/fraunces-font/
- Devanagari Typography 101 (Alphabettes) — https://www.alphabettes.org/devanagari-typography-101-a-guide-for-typesetting-with-latin/
- Devanagari overview (Mota Italic) — https://motaitalic.github.io/devanagari-documentation/languages/devanagari-overview/devanagari-overview.html
- Devanagari type anatomy (Pooja Saxena, TypeTogether) — https://www.type-together.com/devanagari-type-anatomy
- Typotheque, history of printed Devanagari — https://www.typotheque.com/research/devanagari-the-makings-of-a-national-character
- Bringhurst's measure, applied to the web — http://webtypography.net/2.1.2
- Line-length readability (Baymard) — https://baymard.com/blog/line-length-readability
- Line width and comprehension — https://blogs.oregonstate.edu/calverta/line-width-in-digital-typography-for-accessibility-and-comprehension/

**Fonts & Vedic encoding**
- Scharf, revised Devanagari font comparison (INDOLOGY, Aug 2023) — https://list.indology.info/pipermail/indology/2023-August/058005.html
- Noto Serif Devanagari specimen (block coverage) — https://notofonts.github.io/noto-docs/specimen/NotoSerifDevanagari/
- Noto Serif Devanagari on Google Fonts — https://fonts.google.com/noto/specimen/Noto+Serif+Devanagari
- Noto issue: Vedic accents across Indic fonts — https://github.com/notofonts/noto-fonts/issues/2256
- Tiro Devanagari Sanskrit — https://www.tiro.com/fonts/tiro-devanagari-sanskrit
- Tiro Indic collection (Google Design) — https://design.google/library/the-modern-tiro-indic-collection-font
- Shobhika — https://github.com/Sandhi-IITBombay/Shobhika ; https://ctan.org/pkg/shobhika ; https://rnd.iitb.ac.in/index.php/node/1064
- Adishila fonts (and licence) — https://adishila.com/fonts/
- Anek Devanagari (Ek Type) — https://fonts.google.com/specimen/Anek+Devanagari ; https://design.google/library/anek-multiscript
- Mukta (Ek Type) — https://github.com/EkType/Mukta
- Pragati Narrow (Omnibus Type) — https://github.com/Omnibus-Type/PragatiNarrow
- Vesper Libre — https://fonts.google.com/specimen/Vesper+Libre
- sanskritweb legacy fonts (Sahadeva et al.) — http://www.sanskritweb.net/fonts/
- Vedic Extensions block — https://en.wikipedia.org/wiki/Vedic_Extensions ; https://www.unicode.org/charts/PDF/U1CD0.pdf
- Devanagari Extended block — https://en.wikipedia.org/wiki/Devanagari_Extended
- Vedic tone markers + post-base visarga/anusvāra bug — https://corp.unicode.org/pipermail/unicode/2019-December/008430.html
- Browser font-fallback/shaping differences — https://shkspr.mobi/blog/2026/03/an-odd-font-rendering-bug-in-firefox-and-safari/

**Anti-patterns**
- The anatomy of AI design sameness (indigo, Wathan's apology) — https://saschb2b.com/blog/same-same-but-different
- Why AI websites all look the same — https://axe-web.com/insights/ai-website-design-sameness/
- Why your AI keeps building the same purple gradient website — https://prg.sh/ramblings/Why-Your-AI-Keeps-Building-the-Same-Purple-Gradient-Website
- Everything built with shadcn/ui looks the same — https://www.designsystemscollective.com/is-anyone-else-tired-of-every-tailwind-shadcn-app-looking-the-same-69c545e73114
- Breaking out of shadcn generics — https://uxskill.laithjunaidy.com/blog/shadcn-ui-looks-generic.html
