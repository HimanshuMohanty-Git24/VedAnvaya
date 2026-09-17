"""Build the Atharvaveda Śaunaka ``traditional_metadata.jsonl`` from Whitney's brackets.

Input
-----
The pinned ``Page:``-namespace scans harvested by
``scripts/fetch_whitney_avs_anukramani.py`` (manifest at
``data/raw/wikisource_whitney_avs/anukramani_page_manifest.jsonl``).  Whitney prints, under
each hymn's English caption, a bracketed excerpt of the **Bṛhatsarvānukramaṇī**::

    [Atharvan.—vācaspatyam. caturṛcam. ānuṣṭubham: 4. 4-p. virāḍ urobṛhatī.]

Output
------
``data/canonical/atharvaveda_saunaka_digital_working_v1/traditional_metadata.jsonl``
in the exact record shape of the Yajurveda artifact (``assertion_id``, ``predicate``,
``value``, ``scope``, ``source_id``, ``source_locator``, ``status``, ``notes``,
``schema_version``), plus a provenance sidecar
``traditional_metadata_provenance.jsonl`` carrying the verbatim bracket per hymn.

Scope: hymn-level primary, never per-verse fan-out
--------------------------------------------------
Whitney's ascription is a statement about a **hymn**.  So every ṛṣi and devatā row, and
every default-metre row, is emitted **once**, at ``scope_type = WHOLE_PASSAGE`` against the
hymn's ``entity_id`` -- the same shape ``src/vedagraph/corpus.py`` already uses for the
Rigvedic sūkta-scoped triad.  ``src/vedagraph/domain/ontology.py`` then grades that scope as
``AttributionPrecision.CONTAINER_INHERITED`` when the projection pushes it down to the
mantras, which is the distinction V2 spent a pass restoring.  Fanning 580 hymn statements
out into ~4,700 per-verse rows here would delete that distinction at the source and would
make one bracket look like fifty independent statements.

The only per-verse rows are Whitney's own **metre exceptions** -- the part of the bracket
after the colon, which does address individual verses.  Those are emitted at
``SINGLE_MANTRA`` (one verse) or ``MANTRA_RANGE`` (``N-M``) scope and are genuinely
source-stated at that scope.

Values are verbatim and unresolved
----------------------------------
Every ``value`` is the source string as printed, with wiki markup removed and the trailing
sentence period dropped.  Nothing is resolved against ``data/registry/rishis.yaml`` or
``devatas.yaml``, nothing is merged across spellings, and ``ç``/``n̄`` are **not**
normalised to ``ś``/``ṅ``.  The measured reason is on record for the Yajurveda: only 13 of
249 ṛṣi strings resolved to the Rigvedic registry, because that registry stores
Sarvānukramaṇī patronymic compounds while the other indices print bare names.  A blanket
merge is an alias-level error that per-row sampling cannot see, so this artifact keeps its
own namespace and defers identity to recorded human review.

The two alignment gates
-----------------------
Both are free and source-stated, and both are enforced:

1. **stated_verse_count** -- the bracket's Sanskrit numeral word (``caturṛcam`` = 4,
   ``daçakam`` = 10 ...) against our own mantra count under that hymn key.  Measured on the
   real data, Whitney states a verse count for **less than half** the hymns, so this gate is
   necessary but not sufficient; the brief's assumption that he states it for every hymn is
   not what the pages contain.
2. **max_referenced_verse** -- the highest verse number appearing in the metre-exception
   list must not exceed our mantra count.  This catches a numbering slip on hymns where no
   count word is printed.

A hymn failing either gate is **refused entirely** -- no row of any predicate -- and the
refusal is recorded in the provenance sidecar with the two numbers.

What is deliberately not emitted
--------------------------------
* Kāṇḍa 20 (143 hymns / 958 mantras): absent at source.  Whitney excluded it.
* Hymns whose bracket ascribes different ṛṣis to different *parts* (x. 5) or is printed once
  per *paryāya* inside one hymn (xii. 5): a single hymn-level ṛṣi would be a fabrication.
* Sub-verse metre addressing (``a of 1-27``, ``1 b``): we hold no pāda-level passages.
* Back-reference ascriptions (``As 28.``, ``(As 42.)``, ``⌊?⌋``): resolving "as the
  preceding" is an inference, so those hymns get no ṛṣi.
* Books xv and xvi carry metre only.  Lanman states this himself (vol. II p. 1038): the
  Vrātya book "is treated as a unit in that no seer is named for the whole nor for any part
  of it."  The gap is the tradition's, and it is left as a gap.

Printed apparatus is filtered, and the filter is recorded
---------------------------------------------------------
The bracket runs the ascription together with the verse count, the pāda addresses, the
metre and Lanman's footnote markers in one period-delimited sequence with no field markers,
so the first harvest emitted all of it.  ``classify_head_part`` now names and refuses each
apparatus class -- see its docstring -- and every refusal is written per hymn to
``rejected_from_devata_slot`` in the provenance sidecar and republished in the generated
registry's ``rejections`` block.

**The compound-statement residual, fixed in Wave 4.**  33 ``HAS_CHANDAS`` values were whole
un-parsed bracket fragments rather than metre names -- 20 carrying a colon, 32 carrying an
embedded verse address, 33 in union.  They arose where a **per-verse devatā exception** is
printed inside the metre list, so the tail splitter read one specification where the page
states two: AVS 5.3's ``8, 11. āindrī. trāiṣṭubham: 2. bhurij`` is a per-verse devatā, then
the hymn's metre, then that metre's own exception, with no semicolon between them.

``compound_metre_statement`` now refuses such a value at both emission sites, by the same
two structural tokens this parser already relies on: a colon separates a statement from its
per-verse exceptions, and a bare ``N.`` is a verse address.

It refuses rather than repairs, and that is deliberate.  The notation makes the compound
*detectable* but not *assignable*: ``trāiṣṭubham`` in that example is the hymn's default
printed inside a per-verse list, so assigning it to verses 8 and 11 would be a fabrication,
and re-addressing ``'7. 5-p. pathyāpan̄kti'`` onto verse 7 would be inference from the mixed
string.  Every refusal is recorded per hymn in the provenance sidecar, so the printed words
survive even though no assertion is made from them.

Usage
-----
    .venv/Scripts/python.exe scripts/build_atharvaveda_anukramani.py --dry-run
    .venv/Scripts/python.exe scripts/build_atharvaveda_anukramani.py
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import orjson

from vedagraph.identity import uuid_for_urn


def use_utf8_console() -> None:
    """Re-encode stdout for IAST output. Called by __main__, never at import.

    Rejection reasons carry the verbatim rejected token, which is IAST, and the Windows
    console is cp1252 -- reporting a rejection must not be the thing that kills the build.

    This used to run at module scope, and that is why the parser had no tests: replacing
    sys.stdout on import detaches pytest's capture buffer, so importing this module killed
    the whole session with "I/O operation on closed file". The builder's docstring named
    33 malformed values as a known residual and shipped them; a parser no test can import
    is a parser whose residual cannot become a failing test. Same fact, two symptoms.
    """
    if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - stream setup
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CORPUS = Path("data/canonical/atharvaveda_saunaka_digital_working_v1")
MANIFEST = Path("data/raw/wikisource_whitney_avs/anukramani_page_manifest.jsonl")
OUT = CORPUS / "traditional_metadata.jsonl"
PROVENANCE = CORPUS / "traditional_metadata_provenance.jsonl"

SOURCE_ID = "WIKISOURCE_WHITNEY_AV"
SOURCE_ARTIFACT_ID = "WIKISOURCE_WHITNEY_AV.AVS.BRHATSARVANUKRAMANI.PAGENS"
PARSER_VERSION = "whitney-avs-anukramani-v1"
SCHEMA_VERSION = "1.0.0"

NOTES = (
    "Hymn-scope excerpt of the Brhatsarvanukramani as printed in brackets by Whitney & "
    "Lanman, Atharva-Veda Samhita (HOS 7-8, 1905), harvested from the en.wikisource "
    "Page: namespace. entity_resolution_method=VERBATIM_SOURCE_STRING_NOT_RESOLVED: the "
    "value is the source string as printed and is not resolved to an entity, merged with a "
    "homonym or normalised across spellings (HOS orthography c/n-macron is preserved). "
    "scope_type=WHOLE_PASSAGE means the source states this of the HYMN and NOT of its "
    "individual mantras; any per-mantra reading of it is CONTAINER_INHERITED, not "
    "SOURCE_STATED. Kanda 20 is absent from this source: Whitney excluded it."
)
NOTES_PER_VERSE = (
    "Per-verse metre exception stated by the Brhatsarvanukramani excerpt after the colon in "
    "Whitney's hymn bracket. This one IS source-stated at mantra scope, unlike the hymn's "
    "default metre. entity_resolution_method=VERBATIM_SOURCE_STRING_NOT_RESOLVED."
)

# --------------------------------------------------------------------------- lexicons
#: Whitney's book numbering is roman throughout the running headers.
ROMAN = {
    label: number
    for number, label in enumerate(
        "i ii iii iv v vi vii viii ix x xi xii xiii xiv xv xvi xvii xviii xix xx".split(), 1
    )
}
RUNNING_HEADER = re.compile(r"\{\{rh\|(.*?)\}\}")
#: "BOOK VII." and the transcribed variant "BOOK. V.".
HEADER_BOOK = re.compile(r"BOOK\.?\s+([IVXLC]+)", re.IGNORECASE)
#: Outer running-header columns, e.g. "vii. 83-" (verso) and "-vii. 83" (recto). Used only
#: as a fallback: vol. 1 p. 434 prints "viii. 68-" against a centre header of BOOK VII.,
#: and book viii has only 10 hymns, so the centre column is the one to trust.
HEADER_COLUMN = re.compile(r"^-?\s*([ivxlc]+)\.\s*[\d,\s\-]*-?$")
BOOK_OPENER = re.compile(r"\{\{larger\|Book\s+([IVXLC]+)\.?\}\}", re.IGNORECASE)
#: Front matter and appended auxiliary matter reuse '''N. Title''' headings, so the book
#: carry-forward must be switched off there or appendix section 7 would be read as xix. 7.
NON_BODY_HEADER = re.compile(
    r"Contents of|Appended Auxiliary|General Introduction|Prefatory|CONTENTS"
    r"|Indexes and other Auxiliary",
    re.IGNORECASE,
)
#: Hymn caption. Book vii and parts of xix print Whitney's own (Berlin) number followed by
#: the Bombay number in parentheses -- "7 (8)", "6 (6, 7)", and sometimes with no period
#: after the parenthesis. The FIRST number is Whitney's and is our spine. The class at
#: the end includes U+00A0 on purpose: several captions are transcribed with a
#: non-breaking space after the number, and excluding it would lose those hymns.
HYMN_CAPTION = re.compile(r"'{3}(\d+)(?:\s*\(([^)]*)\))?\.?[\s ]")  # noqa: RUF001
#: The bracket sits inside the {{smaller ...}} block that immediately follows the caption.
BRACKET_ANCHOR = re.compile(r"\{\{smaller[^\[\]]{0,80}?\[")

#: Metre stems. Every Vedic metre name in these brackets is built from one of these, and
#: none of the devatā adjectives contains one -- checked against the full token inventory.
#: ``[āa][sṣ][tṭ]i`` rather than ``a[sṣ][tṭ]i``: the vrddhi forms ``āṣṭikam`` (iii. 27, the
#: hymn's default metre, whose every verse the same bracket puts in the aṣṭi class) and
#: ``parāṣṭi`` are metres, and the un-lengthened class let ``āṣṭikam`` fall through to the
#: devatā slot.
METRE_STEM = re.compile(
    r"g[āa]yatr|u[sṣ][nṇ]i[hgk]|nu[sṣ][tṭ]ub|bṛhat|b[āa]rhat|pa[nṅ]̄?kt|p[āa][nṅ]̄?kt"
    r"|tri[sṣ][tṭ]ub|tr[āa]i[sṣ][tṭ]ub|jagat|j[āa]gat|[cç]akvar|[cç][āa]kvar|[āa][sṣ][tṭ]i"
    r"|dhṛti|kṛti|prākṛt|kakub|kakum|vir[āa][jḍṭṇ]|ekapad|dv[āa]ipad|dvipad|jyot"
    r"|nicṛ|bhuri|bhūri|svar[āa][jḍṭ]|[sṣ][nṇ]i[hḥ]|[cç][ai][nṅ]̄?kumat|[āa]rṣ[īiy]"
    r"|”rṣ[īiy]|anuṣubh|^\d+-(?:p|av|f)\.?$"
)
#: A head token that cannot be a printed devatā name: a bare verse address, a pāda or
#: avasāna count, a back-reference, or a caption fragment. Emitting any of these as a
#: Devata value would put a page-number-shaped string into the deity namespace.
NOT_A_DEVATA = re.compile(
    r"^[\d\s,\-]+$|^\d|^(?:as|vs|and|etc|cf|sc)(?![a-zāīūṛṅñṭḍṇçśṣḥṁ])|^[a-h]$|^\W*$",
    re.IGNORECASE,
)
#: A pāda reference: Whitney addresses verse quarters by letter, and prints them in the
#: same period-delimited run as the ascriptions ("2 a-d. 4-p. uṣṇih"). A bare or hyphenated
#: run of pāda letters is a *location*, not a deity. ``NOT_A_DEVATA`` catches the
#: single-letter form only; ``a-d`` slipped past it and reached the graph as the
#: devatā-ascription of AVS 19.38.
PADA_REFERENCE = re.compile(r"^[a-h](?:\s*[-,]\s*[a-h])*$")
#: Metrical apparatus that fills the default-metre slot but names no metre. ``ekāvasānam``
#: is an avasāna (pause) count -- the written-out form of the ``1-av.`` qualifier Whitney
#: uses throughout -- and ``viparītapādalakṣmyā`` describes reversed pādas. Both are
#: refused rather than promoted: putting them in the Chandas namespace would move the
#: defect this filter exists to remove rather than fix it.
METRICAL_APPARATUS = re.compile(r"[āa]vas[āa]n|vipar[īi]tap[āa]da")
#: A metre name whose printed ``bh`` ligature has broken to ``hh`` (``ānuṣṭuhham`` for
#: ``ānuṣṭubham`` at vii. 61, ``trāiṣṭuhham`` for ``trāiṣṭubham``). These are metres, so
#: they must not be devatā ascriptions; but the string is corrupt, so it must not become a
#: Chandas node either. Refused, with the token recorded.
CORRUPT_METRE = re.compile(r"[sṣ][tṭ]uhh")
#: Whitney occasionally sets the whole ascription inside parentheses (xiii. 2, xiii. 3),
#: which the parenthetical mask would otherwise hide from the em-dash split.
PARENTHESISED_ASCRIPTION = re.compile(r"^\s*\((.*?—.*?)\)\s*", re.DOTALL)
#: Devatā markers: the tradition's own suffixes for "having X as deity".
DEVATA_MARKER = re.compile(r"devat|d[āa]ivat|devy|d[āa]ivy")

#: A bare verse address inside a value. Whitney writes structural qualifiers as ``3-av.``
#: and ``6-p.`` -- digit, hyphen, letters -- so the negative lookbehind keeps those out of
#: this pattern while a true verse reference (``24. ``, ``7. ``) matches.
EMBEDDED_VERSE_ADDRESS = re.compile(r"(?<![0-9a-zA-Z-])\d{1,2}\.\s")


def compound_metre_statement(value: str) -> str:
    """Why this value cannot be one metre name, in Whitney's own notation, or "".

    Two structural tokens, both already justified elsewhere in this parser. A colon
    separates a statement from its per-verse exceptions -- that is what
    :func:`split_head_and_tail` splits on -- and a bare ``N.`` is a verse address, which is
    what :data:`PER_VERSE_OPENER` recognises. Neither can occur inside the NAME of a metre,
    so a value carrying either is a run of two or more printed statements.

    Deliberately only those two tokens. Generic digit detection would refuse
    ``3-av. 6-p. dvyuṣṇiggarbhā jagatī``, which is one metre name with two structural
    qualifiers; punctuation heuristics would refuse ``trāiṣṭubham, jātavedasam``, which the
    tail loop already splits correctly; and deciding which half of a compound is the metre
    is Sanskrit adjudication, which is exactly what this function exists to avoid doing.

    Returns a refusal reason rather than a bool so the caller records WHICH token fired.
    """
    if ":" in value:
        return "colon_separates_statement_from_per_verse_exceptions"
    if EMBEDDED_VERSE_ADDRESS.search(value):
        return "embedded_verse_address"
    return ""
#: Sanskrit numeral words used for the stated verse count, mapped by explicit table rather
#: than by a compound parser: the vocabulary is 79 strings on the real data and a parser
#: would silently invent values for the irregular ones.
NUMERAL_WORDS: dict[str, int] = {
    "ekarcam": 1,
    "dvyṛcam": 2,
    "dvyrcam": 2,
    "tṛcam": 3,
    "trika": 3,
    "trikam": 3,
    "trayam": 3,
    "caturṛcam": 4,
    "caturrcam": 4,
    "catvāri": 4,
    "catvāri vāi vacanāni": 4,
    "pañcarcam": 5,
    "pañcakam": 5,
    "pañcaka": 5,
    "pañcatam": 5,
    "pañca": 5,
    "ṣaḍṛcam": 6,
    "ṣadṛcam": 6,
    "ṣaṭ": 6,
    "ṣaṭka": 6,
    "ṣaṭkam": 6,
    "saptarcam": 7,
    "saptakam": 7,
    "saptaka": 7,
    "sapta": 7,
    "aṣṭarcam": 8,
    "aṣṭakam": 8,
    "aṣṭaka": 8,
    "aṣṭāu": 8,
    "navarcam": 9,
    "navakam": 9,
    "navaka": 9,
    "daçarcam": 10,
    "daçakam": 10,
    "daçaka": 10,
    "daçaham": 10,
    "daça": 10,
    "ekādaçarcam": 11,
    "ekādaçakam": 11,
    "ekādaçaka": 11,
    "ekādaça": 11,
    "dvādaçarcam": 12,
    "dvādaçakam": 12,
    "dvādaça": 12,
    "trayodaçarcam": 13,
    "trayodaçakam": 13,
    "trayodaça": 13,
    "caturdaçarcam": 14,
    "caturdaçakam": 14,
    "caturdaça": 14,
    "pañcadaçarcam": 15,
    "pañcadaçakam": 15,
    "pañcadaça": 15,
    "ṣoḍaçarcam": 16,
    "ṣoḍaçakam": 16,
    "ṣoḍaça": 16,
    "saptadaçarcam": 17,
    "saptadaçakam": 17,
    "saptadaça": 17,
    "aṣṭādaçarcam": 18,
    "aṣṭādaçakam": 18,
    "aṣṭādaça": 18,
    "dvyūnā viṅçati": 18,
    "viṅçati": 20,
    "viṅçakam": 20,
    "ekaviṅçakam": 21,
    "ekaviṅçati": 21,
    "dvāviṅçakam": 22,
    "dvāviṅçam": 22,
    "trayoviṅçakam": 23,
    "trayoviṅçam": 23,
    "caturviṅçakam": 24,
    "caturviṅçam": 24,
    "caturviṅçarcam": 24,
    "pañcaviṅçakam": 25,
    "pañcaviṅçam": 25,
    "ṣaḍviṅçakam": 26,
    "ṣaḍviṅçam": 26,
    "ṣaḍviṅçati": 26,
    "ṣaḍviṅçaḥ": 26,
    "saptaviṅçakam": 27,
    "saptaviṅçati": 27,
    "aṣṭāviṅçakam": 28,
    "aṣṭāviṅçam": 28,
    "dvyūnā triṅçat": 28,
    "navaviṅçakam": 29,
    "triṅçat": 30,
    "triṅçakam": 30,
    "ekatriṅçat": 31,
    "ekatriṅçatkam": 31,
    "dvātriṅçat": 32,
    "trayastriṅçat": 33,
    "catustriṅçat": 34,
    "pañcatriṅçat": 35,
    "ṣaṭtriṅçat": 36,
    "saptatriṅçat": 37,
    "aṣṭātriṅçat": 38,
    "catvāriṅçat": 40,
    "catuçcatvāriṅçat": 44,
    "pañcāçat": 50,
    "tripañcāçat": 53,
    "pañcapañcāçat": 55,
    "ṣaṣṭi": 60,
    # Added after an enumeration of the whole emitted devatā value space found these
    # printed verse counts sitting in the DEVATĀ slot -- the graph was asserting that the
    # deity-ascription of AVS 18.4 is the number eighty-nine. Each one is confirmed against
    # our own independent mantra count for the hymn it stands on, which is why they are
    # safe to route to the verse gate rather than merely dropped: 18.4=89, 18.3=73,
    # 19.69=4, 19.42=4, 19.51=2, 16.6=11, 12.1=63, 12.3=60, 18.1=61, 18.2=60.
    "dve": 2,
    "catasraḥ": 4,
    "catasras": 4,
    "ṣaṣṭiḥ": 60,
    "ekaṣaṣṭi": 61,
    "triṣaṣṭih": 63,
    "triṣaṣṭiḥ": 63,
    "saptatis tryadhikā": 73,  # saptati + try-adhika, "seventy with three over"
    "ekonanavati": 89,  # eka-ūna-navati, "ninety less one"
    "etādaça": 11,  # the scan's `t` for `k` in `ekādaça`; AVS 16.6 has exactly 11 mantras
}
#: Head tokens that are verse-count *notes* rather than a count of this hymn's verses.
#: An explicit table of two, both read off the printed page, because neither may reach the
#: verse gate and neither may be emitted as a devatā:
#:
#: * ``caturviṅçarcaṁ trayaṁ sūktānām`` (iv. 17) states 24 verses across a *triad* of
#:   hymns; our AVS 4.17 has 8, so gating on 24 would refuse a sound ascription.
#: * ``dvyadhikaṁ vihitam`` (xvi. 7) records that two verses more are prescribed than
#:   stated -- arithmetic about the count, not the count.
VERSE_COUNT_NOTES: frozenset[str] = frozenset(
    {"caturviṅçarcaṁ trayaṁ sūktānām", "dvyadhikaṁ vihitam"}
)
#: Numeral words that count *paryāyas*, not verses. They must never reach the verse gate.
PARYAYA_COUNT = re.compile(r"pary[āa]y")
#: Pre-dash strings that are pointers rather than names.
BACK_REFERENCE = re.compile(r"^\(?\s*(as|As)\b|^⌊\?⌋|^\(\?\)$|^etc\b", re.IGNORECASE)
#: Sub-verse metre addressing we cannot key: "a of 1-27", "1 b", "b of 7-27", "1 c.".
SUB_VERSE = re.compile(r"\b[a-h]\b\s+of\b|^\s*\d+\s+[a-h]\b|^[a-h]\s+of\b")


# --------------------------------------------------------------------------- helpers
#: U+2019 RIGHT SINGLE QUOTATION MARK -- the codepoint this corpus settles on for the
#: avagraha. Named rather than written inline so the three confusable encodings folded onto
#: it below stay legible in a diff.
AVAGRAHA = "’"  # noqa: RUF001


def strip_markup(text: str) -> str:
    """Whitney's bracket as printed: wiki markup out, orthography untouched."""
    text = re.sub(r"\{\{sup\|([^{}]*)\}\}", r"\1", text)
    text = re.sub(r"\{\{smaller\|([^{}]*)\}\}", r"\1", text)
    text = re.sub(r"\{\{hi\|([^{}]*)\}\}", r"\1", text)
    text = re.sub(r"\{\{=\}\}", "=", text)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("'''", "").replace("''", "")
    # Latin letters used in place of the IAST diacritics. Each has no other reading, and
    # each is a *transcription* defect rather than something the page means: leaving them
    # in put `ṣaḑṛcam` (= 6) and `ānuṣṱubham` (a metre) into the deity namespace, because
    # neither the numeral table nor the metre stems can match a retroflex spelled with the
    # wrong diacritic. U+0129 and U+00E3 (i and a with TILDE) and the free-standing
    # U+00B8 CEDILLA are the same class one step further on -- a diacritic that landed on
    # the wrong base letter, or beside it: the scan sets `samni` with a tilde for `sāmnī`,
    # `Catana. anustubham` with tildes for `Cātana. ānuṣṭubham`, and a loose cedilla before
    # `çakvarī` where the cedilla belongs under its own `c`.
    text = text.replace("ș", "ṣ").replace("ț", "ṭ")
    text = text.replace("ḑ", "ḍ").replace("ṱ", "ṭ")
    text = text.replace("ĩ", "ī").replace("ã", "ā").replace("¸", "")  # noqa: RUF001
    # The avagraha -- the mark of an elided initial `a` in `'nuṣṭubh` -- is ONE printed
    # glyph that the transcription encodes three ways: U+2019, U+2018 and U+0027. Every
    # occurrence in all three AV registries was inspected and not one of them is a
    # quotation mark, so unifying them is faithful to the page rather than a guess about
    # it. Left alone it split `puro 'nuṣṭubh` into three Chandas nodes and
    # `bhurik prājāpatyā 'nuṣṭubh` into two.
    text = text.replace("‘", AVAGRAHA).replace("'", AVAGRAHA)  # noqa: RUF001
    # A hyphen before the avagraha is the printed column's line break carried into the
    # transcription (`puro- 'nuṣṭubh` at xix. 58); it is not part of any metre name.
    text = re.sub(rf"-\s*{AVAGRAHA}", AVAGRAHA, text)
    return re.sub(r"\s+", " ", text).strip()


#: Whitney's and Lanman's footnote markers. They attach to whatever word ends the clause,
#: so they arrive glued to a metre name and split it from its own clean sibling:
#: `triṣṭubh*` from `triṣṭubh`, `ārcy anuṣṭubh †` from `ārcy anuṣṭubh`, `jagatī *` from
#: `jagatī`. A marker is never part of a value. Stripped at emission only -- the
#: provenance sidecar's ``printed_bracket`` keeps the page as printed.
FOOTNOTE_MARKER = re.compile(r"\s*[*†‡]+\s*")


def printed_value(text: str) -> str:
    """One emitted metre or ascription value: footnote markers out, spacing tidied.

    Applied at emission and never before a ``METRE_STEM`` test. Stripping the marker first
    would change what counts as a metre: ``4. 4-p*`` at xix. 46 is a bare pāda count that
    the metre test rightly declines, and cleaning it to ``4-p`` beforehand promoted it into
    a Chandas node of its own.
    """
    out = FOOTNOTE_MARKER.sub(" ", text)
    # A marker set inside a parenthetical leaves a gap before the bracket it preceded:
    # `(kitavabādhanakāmas*)` must not become `(kitavabādhanakāmas )`.
    out = re.sub(r"\s+([)\]⌋])", r"\1", out)
    return re.sub(r"\s+", " ", out).strip(" .,;:")


#: Whitney's footnote markers are set as digits immediately after the sentence period
#: ("ṛcas triṅçat.1 ādityadevatyās"), which the token splitter would otherwise read as the
#: start of a per-verse address.
FOOTNOTE_DIGIT = re.compile(r"\.\s?\d(?=\s+[^\d])")


def mask_parentheticals(text: str) -> tuple[str, dict[str, str]]:
    """Hide ``(...)`` and ``⌊...⌋`` spans so periods inside them do not split tokens.

    Both carry per-verse *qualifications* of the token they follow -- Whitney's
    ``rohitādityadevatyam (3. mārutī; 28-31. āgneyyaḥ)`` -- and Lanman's ell-brackets carry
    editorial comment. Neither belongs in an emitted value.
    """
    spans: dict[str, str] = {}

    def swallow(open_char: str, close_char: str, source: str) -> str:
        out: list[str] = []
        depth = 0
        buffer: list[str] = []
        for char in source:
            if char == open_char:
                depth += 1
                buffer.append(char)
            elif char == close_char and depth:
                depth -= 1
                buffer.append(char)
                if depth == 0:
                    token = f"\x00{len(spans)}\x00"
                    spans[token] = "".join(buffer)
                    out.append(token)
                    buffer = []
            elif depth:
                buffer.append(char)
            else:
                out.append(char)
        return "".join(out) + "".join(buffer)

    masked = swallow("⌊", "⌋", text)
    masked = swallow("(", ")", masked)
    return masked, spans


def unmask(text: str, spans: dict[str, str]) -> str:
    for token, value in spans.items():
        text = text.replace(token, value)
    return text


def drop_masks(text: str) -> str:
    return re.sub(r"\s*\x00\d+\x00\s*", " ", text).strip(" .,;")


def book_of_page(text: str) -> tuple[int | None, str]:
    """Which kāṇḍa this scan page belongs to, and by what evidence."""
    headers = RUNNING_HEADER.findall(text)
    for header in headers:
        match = HEADER_BOOK.search(header)
        if match and match.group(1).lower() in ROMAN:
            return ROMAN[match.group(1).lower()], "running_header_centre"
    opener = BOOK_OPENER.search(text)
    if opener and opener.group(1).lower() in ROMAN:
        return ROMAN[opener.group(1).lower()], "book_opener"
    for header in headers:
        for column in header.split("|"):
            match = HEADER_COLUMN.match(column.strip().replace("''", ""))
            if match and match.group(1) in ROMAN:
                return ROMAN[match.group(1)], "running_header_column"
    for header in headers:
        if NON_BODY_HEADER.search(header):
            return None, "non_body"
    if '<section begin="index' in text:
        return None, "non_body"
    return None, "silent"


def read_bracket(stream: str, open_at: int) -> tuple[str | None, str | None]:
    """The balanced ``[...]``, tolerating two transcription defects.

    Five brackets on Wikisource close with the ell-bracket ``⌋`` or with the enclosing
    template instead of ``]``. Each was inspected individually and is a typo for ``]``; the
    terminator used is recorded on every row so the tolerance is auditable.
    """
    square = ell = template = 0
    index = open_at
    limit = min(len(stream), open_at + 3000)
    while index < limit:
        char = stream[index]
        if char == "[":
            square += 1
        elif char == "]":
            square -= 1
            if square == 0:
                return stream[open_at + 1 : index], "square_bracket"
        elif char == "⌊":
            ell += 1
        elif char == "⌋":
            if ell:
                ell -= 1
            elif square == 1 and template == 0:
                return stream[open_at + 1 : index], "ell_bracket_typo"
        elif stream.startswith("{{", index):
            template += 1
            index += 2
            continue
        elif stream.startswith("}}", index):
            if template:
                template -= 1
                index += 2
                continue
            if square == 1 and index > open_at + 8:
                return stream[open_at + 1 : index], "template_close_typo"
        index += 1
    return None, None


def numeral_key(token: str) -> str:
    """One head token reduced to its numeral-table lookup form.

    Editorial brackets and Lanman's ``sc.`` come off, and ``n`` + combining macron is
    folded to ``ñ``: the scan sets ``pan̄carcam`` for ``pañcarcam`` (= 5), and without the
    fold that verse count reached the graph as the devatā-ascription of AVS 6.132. The fold
    is confined to this lookup and never touches an emitted value, because the metre stems
    match ``pa[nṅ]̄?kt`` on the un-folded spelling.
    """
    cleaned = token.strip(" .*[]").replace("⌊", "").replace("⌋", "")
    cleaned = re.sub(r"\bsc\.\s*", "", cleaned).strip(" .[]")
    return cleaned.replace("n̄", "ñ")


def is_exact_numeral(token: str) -> bool:
    """True when the token is, verbatim, one of the tabulated numeral words.

    An exact table hit outranks ``METRE_STEM``: ``ṣaṣṭi`` (= 60) contains the ``aṣṭi``
    metre stem, so the count printed at xii. 3 and xviii. 2 was being silently discarded as
    a stray metre instead of gating the hymn.
    """
    return numeral_key(token) in NUMERAL_WORDS


def numeral(token: str) -> int | None:
    """Stated verse count for one head token, or None if it is not a countable numeral."""
    cleaned = numeral_key(token)
    if PARYAYA_COUNT.search(cleaned):
        return None
    if cleaned in NUMERAL_WORDS:
        return NUMERAL_WORDS[cleaned]
    # "catvāri vinçatiç ca" = four and twenty.
    if cleaned.startswith("catvāri vinçatiç ca"):
        return 24
    words = cleaned.replace(",", " ").split()
    if not words:
        return None
    # "ṛcas triṅçat" puts the numeral last; "dvyṛcam tathā param" puts it first.
    for word in (words[0], words[-1]):
        if word in NUMERAL_WORDS:
            return NUMERAL_WORDS[word]
    return None


@dataclass
class Bracket:
    kanda: int
    hymn: int
    volume: int
    page: int
    bombay: str | None
    raw: str
    terminator: str
    rishi: str | None = None
    devata: list[str] = field(default_factory=list)
    chandas: list[str] = field(default_factory=list)
    stated_count: int | None = None
    max_referenced: int | None = None
    per_verse: list[tuple[int, int, str]] = field(default_factory=list)
    refusals: list[str] = field(default_factory=list)
    #: Every head token that was NOT emitted as a devatā ascription, with the reason.
    #: Kept because a recorded rejection is what stops the value being re-added: the
    #: printed bracket interleaves ascriptions with verse counts, pāda addresses and metre
    #: names, and an unrecorded filter looks indistinguishable from a parser that never saw
    #: them. This list is written to ``traditional_metadata_provenance.jsonl`` per hymn and
    #: aggregated into the generated registry by
    #: ``scripts/build_anukramani_knowledge_layer.py``.
    rejected_from_devata_slot: list[dict[str, str]] = field(default_factory=list)
    rishi_qualifier: str | None = None
    head_boundary: str = ""
    multi_part: bool = False


#: A per-verse specification opens with a verse address: a digit, or a run of digits and
#: commas and hyphens, followed by a period. This is what ends the hymn-scope head, whether
#: or not Whitney printed the colon -- books xv and xvi print none, so splitting on ':'
#: alone promoted their LAST per-verse metre to the hymn default.
PER_VERSE_OPENER = re.compile(r"(?:^|(?<=[.;:]))[\s*⌋†‡]*\d[\d,\s\-]*\.\s")


def split_head_tokens(head: str) -> list[str]:
    """Split on the sentence period, tolerating a footnote marker glued to it ("-am.* ").

    A closing editorial bracket may sit between the period and the space. Lanman restores
    an omitted verse count as ``[caturṛcam.] mantroktadevatyam`` (vi. 121); without that
    tolerance the count and the ascription stayed one token, and the whole string entered
    the deity namespace as a 357th "ascription".
    """
    return [
        token.strip(" .*") for token in re.split(r"\.[*†‡]?[\]⌋]?\s+", head) if token.strip(" .*")
    ]


def reject(item: Bracket, value: str, reason: str) -> bool:
    """Record that ``value`` is not an ascription, and why. Always returns False."""
    item.refusals.append(f"{reason}:{value!r}")
    item.rejected_from_devata_slot.append({"value": value, "reason": reason})
    return False


def classify_head_part(item: Bracket, part: str) -> bool:
    """True when this head part is a printed devatā ascription, else record why not.

    Whitney's bracket interleaves the ascription with the rest of the printed apparatus --
    verse counts, verse-count notes, pāda addresses, metre names and metrical qualifiers --
    in one period-delimited run, and the run carries no field markers. Every branch here
    exists because an enumeration of the emitted value space found that class of apparatus
    standing in the graph as a ``DevataAscription`` node. The rejection is appended to
    ``item.refusals``, which lands in ``traditional_metadata_provenance.jsonl`` with the
    verbatim token, so a recorded rejection is what stops the value being re-added.
    """
    if part in VERSE_COUNT_NOTES:
        return reject(item, part, "head_token_is_verse_count_note")
    count = numeral(part)
    if count is not None and (is_exact_numeral(part) or not METRE_STEM.search(part)):
        # A printed verse count. Route it to the alignment gate, which is what it is for,
        # instead of into the deity namespace.
        if item.stated_count is None:
            item.stated_count = count
        return reject(item, part, "head_token_is_verse_count")
    if PADA_REFERENCE.match(part):
        return reject(item, part, "head_token_is_pada_reference")
    if CORRUPT_METRE.search(part):
        return reject(item, part, "head_token_is_corrupt_metre")
    if METRICAL_APPARATUS.search(part):
        return reject(item, part, "head_token_is_metrical_apparatus")
    if NOT_A_DEVATA.match(part):
        return reject(item, part, "head_token_not_a_devata")
    return True


def split_head_and_tail(rest: str) -> tuple[str, str, str]:
    """Hymn-scope head, per-verse tail, and which boundary was used."""
    colon = rest.find(":")
    opener = PER_VERSE_OPENER.search(rest)
    if colon >= 0 and (opener is None or colon < opener.start()):
        return rest[:colon], rest[colon + 1 :], "colon"
    if opener is not None:
        return rest[: opener.start()], rest[opener.start() :], "verse_address"
    return rest, "", "no_per_verse_list"


def parse_bracket(item: Bracket) -> Bracket:
    """Whitney's bracket into slots, refusing rather than guessing."""
    printed = FOOTNOTE_DIGIT.sub(". ", strip_markup(item.raw))
    # xiii. 2 and xiii. 3 print the whole ascription inside parentheses; unwrap it so the
    # em-dash split still sees it, otherwise the parenthetical mask hides the ṛṣi entirely
    # and the per-verse metre list is read as the hymn-scope head.
    unwrapped = PARENTHESISED_ASCRIPTION.sub(lambda m: m.group(1) + ". ", printed, count=1)
    if unwrapped != printed:
        printed = unwrapped
        item.refusals.append("ascription_printed_in_parentheses")
    masked, spans = mask_parentheticals(printed)
    # Two or more ascriptions in one bracket (vii. 54, vii. 68, vii. 72) each apply to a
    # verse RANGE, not to the hymn, so a single hymn-scope ṛṣi would be a fabrication. The
    # count is taken AFTER masking: xiv. 1 uses an em-dash as ordinary punctuation inside a
    # parenthetical, and counting that would refuse a perfectly good ascription.
    if masked.count("—") > 1:
        item.refusals.append("multi_part_ascription")
        item.multi_part = True
        return item
    if "—" in masked:
        before, rest = masked.split("—", 1)
        candidate = drop_masks(unmask(before, spans).strip(" .*"))
        parenthetical = unmask(before, spans)
        if candidate and not BACK_REFERENCE.match(candidate):
            item.rishi = printed_value(candidate)
            if "\x00" in before:
                item.rishi_qualifier = parenthetical.strip(" .*")
        else:
            item.refusals.append(f"rishi_is_back_reference:{candidate or parenthetical!r}")
    else:
        rest = masked
        item.refusals.append("no_rishi_devata_separator")

    head, tail, boundary = split_head_and_tail(rest)
    item.head_boundary = boundary
    tokens = split_head_tokens(head)
    metre_tokens: list[tuple[int, str]] = []
    for position, token in enumerate(tokens):
        bare = drop_masks(token)
        if not bare:
            continue
        count = numeral(bare)
        if count is not None and (is_exact_numeral(bare) or not METRE_STEM.search(bare)):
            if item.stated_count is None:
                item.stated_count = count
            item.rejected_from_devata_slot.append(
                {"value": bare, "reason": "verse_count_routed_to_alignment_gate"}
            )
            continue
        if PARYAYA_COUNT.search(bare) or bare in {"ekaḥ"}:
            item.rejected_from_devata_slot.append(
                {"value": bare, "reason": "paryaya_count_not_a_verse_count"}
            )
            continue
        if METRE_STEM.search(bare):
            metre_tokens.append((position, bare))
            continue
        # Whitney's own list punctuation: ';' and ',' separate co-ordinate devatā
        # statements. Splitting on printed punctuation is not entity resolution; the parts
        # are kept exactly as printed, and ' uta ' ("and") is deliberately NOT split.
        for part in re.split(r"[;,]", bare):
            part = re.sub(r"\s+\d+$", "", part.strip(" .*")).strip(" .*")
            if not part:
                continue
            if not classify_head_part(item, part):
                continue
            # Without the em-dash we cannot tell which slot a head token belongs to, and
            # the previous code guessed "devatā" -- which put the ṛṣi *Atharvan* into the
            # ascription namespace at vii. 92, whose whole bracket is the back-reference
            # `Atharvan (etc. as hymn 91).`. In that branch only a token carrying the
            # tradition's own devatā suffix is kept; the rest is refused, not guessed.
            if item.rishi is None and "no_rishi_devata_separator" in item.refusals:
                if not DEVATA_MARKER.search(part):
                    reject(item, part, "head_token_without_separator_not_a_devata")
                    continue
            item.devata.append(printed_value(part))
    # Only the FINAL head token can be the hymn's default metre. A metre token in an earlier
    # position belongs to a statement about something narrower that we are not modelling.
    if metre_tokens and metre_tokens[-1][0] == len(tokens) - 1:
        candidate = metre_tokens[-1][1]
        # A token carrying BOTH a metre stem and a devatā marker means the printed period
        # between the two slots is missing on that page. Emitting it whole would put a deity
        # name into a Chandas node, so it is refused rather than guessed apart.
        if DEVATA_MARKER.search(candidate):
            item.refusals.append("chandas_token_carries_devata_marker")
        else:
            # On a handful of pages the period between the devatā and the metre is set as a
            # comma or semicolon ("trāiṣṭubham, jātavedasam"). Split on that punctuation and
            # route each part by the same metre/devatā test used above.
            for part in re.split(r"[;,]", candidate):
                part = part.strip(" .*")
                if not part:
                    continue
                if METRE_STEM.search(part):
                    # Same criterion as the per-verse path. This site emits 0 malformed
                    # values today; a guard placed only where a defect was observed is a
                    # guard waiting for the next page layout.
                    compound = compound_metre_statement(part)
                    if compound:
                        item.refusals.append(
                            f"default_metre_is_a_compound_statement:{compound}"
                        )
                        continue
                    item.chandas.append(printed_value(part))
                elif classify_head_part(item, part):
                    item.devata.append(printed_value(part))
    elif metre_tokens:
        item.refusals.append("default_chandas_not_in_final_position")

    for match in re.finditer(r"(?:^|[;])\s*([0-9][0-9,\s\-]*)\.\s*([^;]+)", tail):
        addresses, value = match.group(1), drop_masks(match.group(2))
        value = re.sub(r"\s+", " ", value).strip(" .")
        if SUB_VERSE.search(addresses) or SUB_VERSE.search(value):
            item.refusals.append("sub_verse_metre_addressing")
            continue
        if not value or not METRE_STEM.search(value):
            continue  # a per-verse devatā exception, not a metre
        # The 33 malformed values entered here. The tail is split on ";" alone, so where a
        # page prints a per-verse devatā, then the hymn's metre, then that metre's own
        # exception without a semicolon between them -- AVS 5.3's
        # "8, 11. āindrī. trāiṣṭubham: 2. bhurij" -- ``[^;]+`` takes all three and
        # METRE_STEM matches the middle one.
        #
        # Refused, not repaired. The notation makes the compound detectable but not
        # assignable: ``trāiṣṭubham`` there is the HYMN's default printed inside a per-verse
        # list, so giving it to verses 8 and 11 would be a fabrication, and re-addressing
        # ``'7. 5-p. pathyāpan̄kti'`` onto verse 7 is inference from the mixed string.
        compound = compound_metre_statement(value)
        if compound:
            item.refusals.append(f"per_verse_metre_is_a_compound_statement:{compound}")
            continue
        for part in addresses.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                low, _, high = part.partition("-")
                if low.strip().isdigit() and high.strip().isdigit():
                    item.per_verse.append((int(low), int(high), printed_value(value)))
            elif part.isdigit():
                item.per_verse.append((int(part), int(part), printed_value(value)))
    referenced = [high for _, high, _ in item.per_verse]
    referenced += [
        int(number)
        for number in re.findall(r"(?:^|[;\s])(\d{1,3})(?=[.,\s])", tail)
        if int(number) <= 200
    ]
    item.max_referenced = max(referenced) if referenced else None
    return item


# --------------------------------------------------------------------------- extraction
def load_pages() -> list[tuple[dict[str, Any], str]]:
    rows = [
        json.loads(line)
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    cache: dict[str, dict[str, Any]] = {}
    pages: list[tuple[dict[str, Any], str]] = []
    for row in rows:
        path = row["snapshot_path"]
        if path not in cache:
            payload = orjson.loads(Path(path).read_bytes())
            cache[path] = {item["title"]: item for item in payload["query"]["pages"]}
        revisions = cache[path][row["page_title"]].get("revisions") or []
        content = revisions[0]["slots"]["main"].get("content", "") if revisions else ""
        pages.append((row, content or ""))
    return pages


def extract_brackets(
    pages: list[tuple[dict[str, Any], str]],
) -> dict[tuple[int, int], Bracket]:
    """One bracket per (kāṇḍa, hymn), read off a per-book continuous page stream.

    The stream is per book rather than per page because a caption and its bracket can fall
    either side of a leaf boundary, and ``<section>`` markers are present on only about half
    the hymns so they cannot be the anchor.
    """
    streams: dict[int, list[tuple[int, int, str]]] = collections.defaultdict(list)
    current: int | None = None
    for row, text in pages:
        book, evidence = book_of_page(text)
        if book is not None:
            current = book
        elif evidence == "non_body":
            current = None
        if current is None:
            continue
        streams[current].append((row["volume"], row["page"], text))

    found: dict[tuple[int, int], Bracket] = {}
    for book, segments in streams.items():
        offsets: list[tuple[int, int, int]] = []
        chunks: list[str] = []
        total = 0
        for volume, page, text in segments:
            offsets.append((total, volume, page))
            chunks.append(text)
            total += len(text)
        stream = "".join(chunks)

        def locate(position: int, offsets: list[tuple[int, int, int]] = offsets) -> tuple[int, int]:
            best = offsets[0]
            for entry in offsets:
                if entry[0] <= position:
                    best = entry
                else:
                    break
            return best[1], best[2]

        captions = list(HYMN_CAPTION.finditer(stream))
        for index, caption in enumerate(captions):
            hymn = int(caption.group(1))
            boundary = captions[index + 1].start() if index + 1 < len(captions) else len(stream)
            anchor = BRACKET_ANCHOR.search(
                stream, caption.end(), min(boundary, caption.end() + 400)
            )
            if anchor is None:
                continue
            raw, terminator = read_bracket(stream, anchor.end() - 1)
            if raw is None:
                continue
            if (book, hymn) in found:
                continue
            volume, page = locate(anchor.start())
            found[(book, hymn)] = Bracket(
                kanda=book,
                hymn=hymn,
                volume=volume,
                page=page,
                bombay=caption.group(2),
                raw=raw,
                terminator=terminator or "",
            )
    return found


# --------------------------------------------------------------------------- corpus join
def load_corpus() -> tuple[
    dict[tuple[int, int], dict[str, Any]], dict[tuple[int, int, int], dict[str, Any]]
]:
    hymns: dict[tuple[int, int], dict[str, Any]] = {}
    mantras: dict[tuple[int, int, int], dict[str, Any]] = {}
    for line in (CORPUS / "passages.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        hierarchy = record["hierarchy"]
        if record["entity_type"] == "HYMN":
            hymns[(hierarchy["kanda"], hierarchy["sukta"])] = record
        elif record["entity_type"] == "MANTRA":
            mantras[(hierarchy["kanda"], hierarchy["sukta"], hierarchy["mantra"])] = record
    return hymns, mantras


DJVU = {1: "Atharva-Veda samhita.djvu", 2: "Atharva-Veda samhita volume 2.djvu"}


def locator(item: Bracket) -> str:
    return f"Page:{DJVU[item.volume]}/{item.page} (AVS {item.kanda}.{item.hymn} Anukr. bracket)"


def assertion(
    *,
    urn: str,
    predicate: str,
    value: str,
    scope: dict[str, Any],
    item: Bracket,
    notes: str,
) -> dict[str, Any]:
    return {
        "assertion_id": str(uuid_for_urn(urn)),
        "notes": notes,
        "predicate": predicate,
        "schema_version": SCHEMA_VERSION,
        "scope": scope,
        "source_id": SOURCE_ID,
        "source_locator": locator(item),
        "status": "UNREVIEWED",
        "value": value,
    }


def build() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    pages = load_pages()
    revid = {(row["volume"], row["page"]): row.get("revid") for row, _ in pages}
    snapshot = {(row["volume"], row["page"]): row for row, _ in pages}
    hymns, mantras = load_corpus()
    verse_counts: collections.Counter[tuple[int, int]] = collections.Counter()
    for kanda, sukta, _ in mantras:
        verse_counts[(kanda, sukta)] += 1

    brackets = {key: parse_bracket(item) for key, item in extract_brackets(pages).items()}
    rows: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "hymns_in_corpus": len(hymns),
        "hymns_in_corpus_k1_19": sum(1 for k, _ in hymns if k <= 19),
        "brackets_extracted": len(brackets),
        "gate": collections.Counter(),
        "refusals": collections.Counter(),
        "rejected_tokens": collections.Counter(),
        "predicate": collections.Counter(),
        "per_kanda": collections.defaultdict(lambda: collections.Counter()),
        "refused_examples": [],
        "no_bracket": [],
    }

    for key in sorted(hymns):
        if key not in brackets:
            if key[0] <= 19:
                stats["no_bracket"].append(f"AVS {key[0]}.{key[1]}")
            continue
    for key in sorted(brackets):
        item = brackets[key]
        hymn = hymns.get(key)
        if hymn is None:
            stats["refusals"]["hymn_absent_from_corpus"] += 1
            continue
        ours = verse_counts[key]
        gate_status = "PASS_NOT_STATED"
        if item.multi_part:
            gate_status = "REFUSED_MULTI_PART_ASCRIPTION"
        elif item.stated_count is not None:
            gate_status = "PASS" if item.stated_count == ours else "REFUSED_COUNT_MISMATCH"
        if not gate_status.startswith("REFUSED") and item.max_referenced is not None:
            if item.max_referenced > ours:
                gate_status = "REFUSED_VERSE_NUMBER_OVERRUN"
            elif gate_status == "PASS_NOT_STATED":
                gate_status = "PASS_BY_MAX_REFERENCED"
        stats["gate"][gate_status] += 1

        provenance_row = {
            "kanda": key[0],
            "hymn": key[1],
            "citation": f"AVS {key[0]}.{key[1]}",
            "hymn_key": hymn["canonical_key"],
            "hymn_passage_id": hymn["entity_id"],
            "predicate": "TRADITIONAL_METADATA_PROVENANCE",
            "source_id": SOURCE_ID,
            "source_artifact_id": SOURCE_ARTIFACT_ID,
            "source_locator": locator(item),
            "page_title": snapshot[(item.volume, item.page)]["page_title"],
            "page_url": snapshot[(item.volume, item.page)]["page_url"],
            "revid": revid[(item.volume, item.page)],
            "snapshot_id": snapshot[(item.volume, item.page)]["snapshot_id"],
            "snapshot_sha256": snapshot[(item.volume, item.page)]["snapshot_sha256"],
            "printed_bracket": strip_markup(item.raw),
            "bracket_terminator": item.terminator,
            "bombay_hymn_number": item.bombay,
            "stated_verse_count": item.stated_count,
            "corpus_verse_count": ours,
            "max_verse_referenced": item.max_referenced,
            "verse_count_gate": gate_status,
            "parsed_rishi": item.rishi,
            "parsed_devata": item.devata,
            "parsed_default_chandas": item.chandas,
            "per_verse_chandas_rows": len(item.per_verse),
            "parse_refusals": item.refusals,
            "rejected_from_devata_slot": item.rejected_from_devata_slot,
            "parser_version": PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
        }
        provenance.append(provenance_row)

        if gate_status.startswith("REFUSED"):
            for reason in item.refusals:
                stats["refusals"][reason.split(":", 1)[0]] += 1
            stats["refusals"][gate_status] += 1
            if len(stats["refused_examples"]) < 12:
                stats["refused_examples"].append(
                    f"AVS {key[0]}.{key[1]}: {gate_status} "
                    f"(source says {item.stated_count}, max verse referenced "
                    f"{item.max_referenced}, corpus has {ours}) "
                    f"| {strip_markup(item.raw)[:110]}"
                )
            continue

        for reason in item.refusals:
            stats["refusals"][reason.split(":", 1)[0]] += 1
            if ":" in reason:
                stats["rejected_tokens"][reason] += 1
        base = f"urn:vedagraph:assertion:whitney-avs-anukr:{key[0]}.{key[1]}"
        hymn_scope = {"passage_id": hymn["entity_id"], "scope_type": "WHOLE_PASSAGE"}

        if item.rishi:
            rows.append(
                assertion(
                    urn=f"{base}:rishi",
                    predicate="HAS_RISHI",
                    value=item.rishi,
                    scope=hymn_scope,
                    item=item,
                    notes=NOTES,
                )
            )
            stats["predicate"]["HAS_RISHI"] += 1
            stats["per_kanda"][key[0]]["HAS_RISHI"] += 1
        for ordinal, value in enumerate(item.devata, start=1):
            rows.append(
                assertion(
                    urn=f"{base}:devata:{ordinal}",
                    predicate="HAS_DEVATA",
                    value=value,
                    scope=hymn_scope,
                    item=item,
                    notes=NOTES,
                )
            )
            stats["predicate"]["HAS_DEVATA"] += 1
            stats["per_kanda"][key[0]]["HAS_DEVATA"] += 1
        for ordinal, value in enumerate(item.chandas, start=1):
            rows.append(
                assertion(
                    urn=f"{base}:chandas:{ordinal}",
                    predicate="HAS_CHANDAS",
                    value=value,
                    scope=hymn_scope,
                    item=item,
                    notes=NOTES,
                )
            )
            stats["predicate"]["HAS_CHANDAS"] += 1
            stats["per_kanda"][key[0]]["HAS_CHANDAS"] += 1
        for low, high, value in item.per_verse:
            if high > ours or low < 1:
                stats["refusals"]["per_verse_address_out_of_range"] += 1
                continue
            if low == high:
                mantra = mantras.get((key[0], key[1], low))
                if mantra is None:
                    stats["refusals"]["per_verse_mantra_missing"] += 1
                    continue
                scope = {"passage_id": mantra["entity_id"], "scope_type": "SINGLE_MANTRA"}
            else:
                scope = {
                    "end_sequence": high,
                    "passage_id": hymn["entity_id"],
                    "scope_type": "MANTRA_RANGE",
                    "start_sequence": low,
                }
            rows.append(
                assertion(
                    urn=f"{base}:chandas:{low}-{high}:{value}",
                    predicate="HAS_CHANDAS",
                    value=value,
                    scope=scope,
                    item=item,
                    notes=NOTES_PER_VERSE,
                )
            )
            stats["predicate"]["HAS_CHANDAS_PER_VERSE"] += 1
            stats["per_kanda"][key[0]]["HAS_CHANDAS_PER_VERSE"] += 1

    seen: dict[str, dict[str, Any]] = {}
    for row in rows:
        seen[row["assertion_id"]] = row
    rows = [seen[key] for key in sorted(seen)]
    return rows, provenance, stats


def report(
    rows: list[dict[str, Any]], provenance: list[dict[str, Any]], stats: dict[str, Any]
) -> None:
    hymn_ids = {
        row["scope"]["passage_id"] for row in rows if row["scope"]["scope_type"] == "WHOLE_PASSAGE"
    }
    print(f"assertions            : {len(rows)}")
    total = stats["hymns_in_corpus_k1_19"]
    print(f"hymns with >=1 row    : {len(hymn_ids)} of {total} (kanda 1-19)")
    print(f"brackets extracted    : {stats['brackets_extracted']}")
    print(f"predicates            : {dict(stats['predicate'])}")
    print(f"verse-count gate      : {dict(stats['gate'])}")
    print(f"parse refusals        : {dict(stats['refusals'])}")
    print(f"hymns with no bracket : {len(stats['no_bracket'])} -> {stats['no_bracket']}")
    print(f"rejected tokens       : {len(stats['rejected_tokens'])} distinct")
    for reason, hits in sorted(stats["rejected_tokens"].items()):
        print(f"  REJECTED x{hits} {reason}")
    for example in stats["refused_examples"]:
        print(f"  REFUSED {example}")


def refresh_manifest_entries(written: dict[Path, int]) -> None:
    """Re-hash the two files this script writes inside the corpus manifest.

    ``manifest.json`` recorded ``traditional_metadata.jsonl`` at 0 records and the sha256 of
    zero bytes, because it was empty when the corpus was built on 2026-09-07. Leaving that
    stale is the same class of defect as a graph and a corpus release disagreeing while only
    one of them is measured, so the two per-file entries are updated here and the whole
    manifest is re-validated against ``CorpusManifest`` so it cannot be left malformed.

    ``built_at`` and ``software_git_commit`` are deliberately NOT touched: they still name
    the corpus build, and a full corpus rebuild is the only thing that can legitimately
    move them.
    """
    from vedagraph.models import CorpusManifest
    from vedagraph.storage.manifest import file_sha256

    manifest_path = CORPUS / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = CORPUS.parent.parent
    for path, count in written.items():
        relative = path.relative_to(root).as_posix()
        entry = {"path": relative, "record_count": count, "sha256": file_sha256(path)}
        files = [row for row in manifest["generated_files"] if row["path"] != relative]
        files.append(entry)
        manifest["generated_files"] = sorted(files, key=lambda row: row["path"])
        manifest["record_counts"][relative] = count
    CorpusManifest.model_validate(manifest)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"manifest: refreshed {len(written)} file entries in {manifest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    args = parser.parse_args()
    rows, provenance, stats = build()
    report(rows, provenance, stats)
    if args.dry_run:
        print("dry run: nothing written")
        return
    with OUT.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with PROVENANCE.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(provenance, key=lambda item: (item["kanda"], item["hymn"])):
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"wrote {len(rows)} assertions -> {OUT}")
    print(f"wrote {len(provenance)} provenance rows -> {PROVENANCE}")
    refresh_manifest_entries({OUT: len(rows), PROVENANCE: len(provenance)})


if __name__ == "__main__":
    use_utf8_console()
    main()
