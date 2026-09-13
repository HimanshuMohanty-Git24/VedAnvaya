"""Sanskrit Wikisource adapter for the Vajasaneyi Samhita (Madhyandina recension).

Why this source at all
----------------------
GRETIL has no Vajasaneyi Samhita artifact: its index lists the title and then says
"Restricted download / proprietary format from TITUS" and "Converted file(s) not
available at present".  TITUS does hold a complete accented Madhyandina text, but its
every page carries "No parts of this document may be republished in any form without
prior permission by the copyright holder", so it cannot enter a redistributable corpus.
Sanskrit Wikisource is the best structured source whose licence permits ingestion
(CC BY-SA 4.0, as declared by the wiki's own ``meta=siteinfo&siprop=rightsinfo``).

What one page contains
----------------------
Each ``shuklayajurvedah/adhyayah NN`` page carries several ``<poem>`` blocks:

* the **unaccented samhita** block, whose mantras are labelled ``<adhyaya>.<mantra>``
  on a line of their own; and
* an **Uvata-Mahidhara commentary** block, inside which the *same* mantras are quoted
  in **fully accented** Devanagari, each closing with its own mantra number written in
  Devanagari digits between dandas, e.g. ``.. 1..``.

These are two distinct text layers of one artifact, exactly as the VedaWeb Rigveda TEI
carries several editions in one file.  Both are parsed; neither is derived from the
other and neither overwrites the other.  Where the two layers disagree about how many
mantras an adhyaya has, that divergence is recorded as data, never reconciled here
(see docs/decisions/ADR-010-edition-order-divergence.md).

Discipline
----------
This adapter produces ``StagingTextRecord`` only.  Every mantra number is read from a
label the source itself wrote; nothing is assigned by counting position in the file.
Accented text is never replaced by an unaccented reading, and normalization happens
downstream on derived surfaces only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlencode

import orjson

from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord
from vedagraph.models.enums import TextRole
from vedagraph.normalize import has_vedic_accents, normalize_nfc

PARSER_VERSION = "wikisource-sa-vsm-v2"

WORK_ID = "VG:WORK:YV:VSM"
WIKI_HOST = "sa.wikisource.org"

#: Root page of the Sukla Yajurveda tree on Sanskrit Wikisource.
ROOT_TITLE = "शुक्लयजुर्वेदः"
#: "adhyayah" - the subpage prefix. Titles are zero-padded in Devanagari digits, but
#: adhyayas 2, 3 and 6 live at the *unpadded* title and the padded form is a redirect,
#: so every request must let MediaWiki resolve redirects.
ADHYAYA_WORD = "अध्यायः"

DEVANAGARI_DIGITS = "०१२३४५६७८९"
_DEVANAGARI_TO_ASCII = {digit: str(index) for index, digit in enumerate(DEVANAGARI_DIGITS)}

# A samhita mantra label: "1.1", optionally followed by a braced cross-reference such as
# "40.1 {IsavasyaUp. Kanva1}". Adhyaya 40 labels *all* carry that annotation, which is
# why a bare r"\d+\.\d+" label pattern silently drops the whole adhyaya.
_SAMHITA_LABEL = re.compile(
    r"^(?P<adhyaya>[0-9०-९]+)\.(?P<mantra>[0-9०-९]+)"  # noqa: RUF001
    r"(?:\s*\{(?P<annotation>[^}]*)\})?\s*$"
)
# Any line that begins like a label, used to detect labels this parser fails to read
# instead of skipping them in silence.
_LABEL_SHAPED = re.compile(r"^[0-9०-९]+\s*\.\s*[0-9०-९]+")  # noqa: RUF001

# Closing marker of an accented mantra inside the commentary block: one or two opening
# dandas, the mantra number in Devanagari digits, then zero-or-more closing dandas.
#
# Source-level variations handled by this pattern:
#   • Standard:             "।। ४१ ।।"  — two opening + two closing dandas
#   • Three closing dandas: "।। २२ ।।।" — extra danda at section boundary (VSM 1.22)
#   • No closing dandas:    "।। २७"      — editor omitted trailing dandas (VSM 17.27)
#   • Space in number:      "।। ४ १ ।।" — typesetting space between digits (VSM 18.41)
#   • Section separator:    "।। ३७।। ॥" — U+0965 double danda mark after a space,
#                           appended by the wiki editor as a chapter-end marker (VSM 6.37)
#
# The mantra group captures the full number token (possibly space-separated digits).
# Call .replace(" ", "") before passing to parse_mixed_digits().
#
# The trailing character class [।॥\s]* is intentionally permissive: it matches any
# combination of dandas (U+0964, U+0965) and whitespace after the mantra number so that
# all of the above variants, including the space-separated section separator, are covered
# without separate branches.
_ACCENTED_TERMINAL = re.compile(
    r"[।॥]{1,2}\s*(?P<mantra>[०-९]+(?:\s+[०-९]+)*)\s*[।॥\s]*$"  # noqa: RUF001
)

# Ordinal header lines in the Nirṇaya Sāgara commentary layout.
#
# The 1929 Panasikara edition places a Sanskrit ordinal phrase before every
# accented mūla quotation, e.g. "तत्र प्रथमा।" (the first), "द्वितीया।" (the
# second), up to "षट्षष्टी।" (the sixty-sixth, in adhyaya 16). These are
# the PRIMARY mūla-start signal in v2; accent-presence alone is the fallback.
#
# After markup stripping, an ordinal header consists of:
#   - optional "तत्र " (= "there; the …") prefix for the first mantra of each series
#   - one or two Devanagari words (the ordinal itself)
#   - a single danda "।" (NOT double danda "॥")
#
# The Devanagari range excludes U+0951-U+0954 (udatta ॑, anudatta ॒, and the
# DEVANAGARI GRAVE/ACUTE ACCENT combining marks) so that accented text can never
# match. U+0900-U+0950 covers base letters, matras, halanta, chandrabindu and the
# OM sign; U+0955-U+097F covers extended vowel signs and supplemental letters.
# In practice the outer gate ``not has_vedic_accents(stripped)`` makes this
# exclusion redundant, but it is stated explicitly for clarity.
_DEV_WORD = r"(?:[ऀ-ॐ]|[ॕ-ॿ])+"

_ORDINAL_HEADER = re.compile(
    r"^(?:तत्र\s+)?"  # optional "tatra" prefix
    r"(?:" + _DEV_WORD + r")"  # first Devanagari word (the ordinal itself)
    r"(?:\s+" + _DEV_WORD + r")?"  # optional second word (compound ordinals)
    r"\s*।\s*$",  # ends with single danda — ॥ excluded
    re.UNICODE,
)

# Same pattern but without the end-of-string anchor — used to strip an ordinal
# prefix from a line that also carries mantra text (occurs in VSM 16.37 where
# the second reading is printed on a single line "सप्तत्रिंशी। नमः स॒त्याय…").
#
# Crucially, this pattern is RESTRICTED to lines where the ordinal word ends in
# the Sanskrit ordinal numeral suffixes -ī (ी, U+0940) or -ā (ā, U+093E).
# All Sanskrit ordinals used in this commentary end with one of these vowels:
#   प्रथमा (1st), द्वितीया (2nd), तृतीया (3rd), चतुर्थी (4th), पञ्चमी (5th), …
#   सप्तत्रिंशी (37th), एकचत्वारिंशी (41st), …
#
# This lookbehind prevents false matches on prose openers such as
# "अथ विचारः।" (discussion beginning, no ordinal suffix) which previously
# triggered the inline-detection path and produced a false record in adhyaya 40.
_ORDINAL_HEADER_PREFIX = re.compile(
    r"^(?:तत्र\s+)?"
    r"(?:" + _DEV_WORD + r")"  # the ordinal word, greedily consumed
    r"(?<=[ीा])"  # lookbehind: last char must be ī (U+0940) or ā (U+093E)
    r"\s*।\s+",  # danda followed by whitespace + more content
    re.UNICODE,
)

# Maximum character length (after markup stripping) for a standalone ordinal
# header. Longest ordinal seen: "एकोनचत्वारिंशी।" ≈ 24 chars; using 45 as
# a generous ceiling that still excludes any mantra line.
_ORDINAL_MAX_LENGTH = 45

# Commentator sigla. Inside the commentary block a paragraph of Uvata's or Mahidhara's
# prose opens with an abbreviated name -- "u0" / "m0", written with the Devanagari zero
# as the abbreviation mark -- and such a paragraph quotes fragments of the mantra, so it
# both contains tone marks and ends with the same numbered danda marker as the mantra
# itself. Excluding runs that open with a siglum is what separates the text from the
# commentary on it; without this the accented layer collects each mantra two or three
# times over.
#
# "maa0" is a third spelling of Mahidhara's siglum used from adhyaya 19 onward; it was
# found by investigating a duplicate rather than assumed, and omitting it lets one
# commentary paragraph masquerade as a reading of VSM 19.48.
_COMMENTATOR_SIGLA = ("उ०", "म०", "मा०", "उ०.", "म०.", "मा०.")

# A scribal invocation that opens a section, e.g. "harih om |" before VSM 1.1. It is
# front matter, not part of the mantra, so it is removed from the stored reading. The
# rule is deliberately narrow -- a known invocation formula, at the very start, closed by
# a danda -- because a looser rule would eat text. In the four sampled adhyayas exactly
# one record is affected (VSM 1.1).
_LEADING_INVOCATION = re.compile(r"^(?:हरिः\s*ॐ|हरि:\s*ॐ|हरिः|हरि:|ॐ)\s*[।॥]+\s*(?=\S)")

_POEM_BLOCK = re.compile(r"<poem\b[^>]*>(?P<body>.*?)</poem>", re.DOTALL)
_HTML_TAG = re.compile(r"<[^>]+>")
_WIKI_LINK = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]")
_EXTERNAL_LINK = re.compile(r"\[(?:https?|//)[^\s\]]*\s*([^\]]*)\]")
_REF_TAG = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.DOTALL)


def devanagari_number(value: int, *, width: int = 0) -> str:
    """Render an integer in Devanagari digits, optionally zero-padded."""
    text = f"{value:0{width}d}" if width else str(value)
    return "".join(DEVANAGARI_DIGITS[int(digit)] for digit in text)


def parse_mixed_digits(text: str) -> int:
    """Read an integer written in ASCII digits, Devanagari digits, or a mix of both."""
    converted = "".join(_DEVANAGARI_TO_ASCII.get(char, char) for char in text)
    if not converted.isdigit():
        raise ValueError(f"not a number: {text!r}")
    return int(converted)


def adhyaya_title(adhyaya: int) -> str:
    """The zero-padded Devanagari subpage title for one adhyaya."""
    return f"{ROOT_TITLE}/{ADHYAYA_WORD} {devanagari_number(adhyaya, width=2)}"


def content_api_url(title: str) -> str:
    """Revision-content endpoint for one page, resolving redirects."""
    query = urlencode(
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "rvprop": "content|ids|timestamp",
            "rvslots": "main",
            "redirects": "1",
            "titles": title,
        },
        quote_via=quote,
    )
    return f"https://{WIKI_HOST}/w/api.php?{query}"


def canonical_page_url(title: str) -> str:
    return f"https://{WIKI_HOST}/wiki/{quote(title.replace(' ', '_'))}"


@dataclass(frozen=True)
class PageRevision:
    """Revision provenance for one fetched wiki page."""

    requested_title: str
    resolved_title: str
    page_id: int
    revision_id: int
    revision_timestamp: str
    redirected: bool
    content: str


@dataclass(frozen=True)
class ParseFailure:
    """One line this parser recognised as label-shaped but could not read."""

    resolved_title: str
    line_number: int
    line: str
    reason: str


@dataclass(frozen=True)
class EditorialIntervention:
    """One place this parser departed from the source bytes, and why.

    Every departure is recorded so it can be reviewed and reversed. The project's rule is
    that interpretation is probabilistic and points at evidence; an intervention that is
    only described in a docstring is neither.

    ``status`` is non-empty only for interventions that require human review before the
    data can be treated as settled. Recognised value: ``"NEEDS_REVIEW"``.
    """

    adhyaya: int
    mantra: int
    kind: str
    removed: str
    reason: str
    status: str = ""


@dataclass(frozen=True)
class AdhyayaParse:
    """Everything one adhyaya snapshot yields, including its own failures."""

    adhyaya: int
    revision: PageRevision
    samhita: list[StagingTextRecord]
    accented: list[StagingTextRecord]
    alternate_citations: dict[int, str]
    failures: list[ParseFailure]
    #: Mantra numbers for which the accented layer supplied more than one reading. The
    #: first reading is kept and the collision is reported; the page genuinely prints a
    #: variant (VSM 16.37 has both "srutyaya" and "satyaya"), so this is data.
    accented_collisions: dict[int, int]
    #: Departures from the source bytes, emitted downstream as reviewable assertions.
    editorial_interventions: list[EditorialIntervention]
    #: mantra number -> the source line its accented run OPENED on. An
    #: ORDINAL_HEADER_ABSENT ParseFailure carries the same line_number, so a consumer can
    #: attribute a boundary fallback to the right record BY LINE. Attributing it by text
    #: prefix is unsound: VSM 11.9 and 11.28 share their first 63 characters, so a greedy
    #: earliest match claims 11.9 for a fallback that belongs to 11.28.
    accented_start_lines: dict[int, int] = field(default_factory=dict)


def _strip_markup(line: str) -> str:
    """Remove wiki and HTML markup without touching Sanskrit characters."""
    text = _REF_TAG.sub("", line)
    text = _WIKI_LINK.sub(r"\1", text)
    text = _EXTERNAL_LINK.sub(r"\1", text)
    text = _HTML_TAG.sub("", text)
    return " ".join(text.split())


class YajurvedaWikisourceAdapter(SourceAdapter):
    """Parse one Sanskrit Wikisource adhyaya page of the Vajasaneyi Samhita."""

    #: The REGISTERED source id from data/registry/sources.yaml. This is deliberately not
    #: a Yajurveda-specific invention: the adhyaya pages are further artifacts of the
    #: already-registered Sanskrit Wikisource source, and inventing a per-Veda source id
    #: would attach rights at a level the rights authority never adjudicated.
    source_id = "WIKISOURCE_SA"

    def __init__(
        self,
        *,
        source_artifact_id: str = "WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI",
    ) -> None:
        self.source_artifact_id = source_artifact_id

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        """Resolve a ``VSM.<adhyaya>`` scope to its revision-content endpoint."""
        parts = scope.split(".")
        if len(parts) != 2 or parts[0] != "VSM":
            raise ValueError("Yajurveda Wikisource discovery requires scope VSM.<adhyaya>")
        adhyaya = int(parts[1])
        if not 1 <= adhyaya <= 40:
            raise ValueError(f"adhyaya out of range for the Vajasaneyi Samhita: {adhyaya}")
        title = adhyaya_title(adhyaya)
        return [
            DiscoveredResource(
                source_id=self.source_id,
                url=content_api_url(title),
                locator=f"VSM {adhyaya}",
                media_type="application/json",
            )
        ]

    # -- snapshot reading ------------------------------------------------------

    def read_revision(self, snapshot_path: Path) -> PageRevision:
        """Read revision provenance and wikitext out of an immutable API snapshot."""
        payload = orjson.loads(snapshot_path.read_bytes())
        query = payload.get("query")
        if not isinstance(query, dict):
            raise ValueError(f"{snapshot_path} is not a MediaWiki query response")
        pages = query.get("pages")
        if not isinstance(pages, list) or not pages:
            raise ValueError(f"{snapshot_path} contains no pages")
        page = pages[0]
        if page.get("missing"):
            raise ValueError(f"{snapshot_path} records a missing page: {page.get('title')!r}")
        revisions = page.get("revisions")
        if not isinstance(revisions, list) or not revisions:
            raise ValueError(f"{snapshot_path} contains no revisions")
        revision = revisions[0]
        content = revision.get("slots", {}).get("main", {}).get("content")
        if not isinstance(content, str):
            raise ValueError(f"{snapshot_path} has no main-slot wikitext")
        redirects = query.get("redirects") or []
        requested = redirects[0]["from"] if redirects else page["title"]
        return PageRevision(
            requested_title=requested,
            resolved_title=page["title"],
            page_id=int(page["pageid"]),
            revision_id=int(revision["revid"]),
            revision_timestamp=str(revision["timestamp"]),
            redirected=bool(redirects),
            content=content,
        )

    # -- parsing --------------------------------------------------------------

    def parse(self, snapshot_path: Path, *, snapshot_id: str) -> list[StagingTextRecord]:
        """Return the unaccented samhita layer; ``parse_adhyaya`` returns everything."""
        return self.parse_adhyaya(snapshot_path, snapshot_id=snapshot_id).samhita

    def parse_adhyaya(self, snapshot_path: Path, *, snapshot_id: str) -> AdhyayaParse:
        revision = self.read_revision(snapshot_path)
        adhyaya = self._adhyaya_from_title(revision.resolved_title)
        blocks = [match.group("body") for match in _POEM_BLOCK.finditer(revision.content)]
        failures: list[ParseFailure] = []
        samhita, citations = self._parse_samhita_layer(
            blocks, adhyaya=adhyaya, revision=revision, snapshot_id=snapshot_id, failures=failures
        )
        accented = self._parse_accented_layer(
            revision, adhyaya=adhyaya, snapshot_id=snapshot_id, failures=failures
        )
        collisions = dict(getattr(self, "_last_collisions", {}))
        interventions = list(getattr(self, "_last_interventions", []))
        start_lines = dict(getattr(self, "_last_accented_start_lines", {}))
        return AdhyayaParse(
            adhyaya=adhyaya,
            revision=revision,
            samhita=samhita,
            accented=accented,
            alternate_citations=citations,
            failures=failures,
            accented_collisions=collisions,
            editorial_interventions=interventions,
            accented_start_lines=start_lines,
        )

    @staticmethod
    def _adhyaya_from_title(resolved_title: str) -> int:
        """Read the adhyaya number out of the page title the wiki actually served."""
        tail = resolved_title.rsplit("/", 1)[-1]
        digits = tail.split()[-1] if " " in tail else tail
        try:
            return parse_mixed_digits(digits)
        except ValueError as error:
            raise ValueError(f"cannot read an adhyaya number from {resolved_title!r}") from error

    def _record(
        self,
        *,
        adhyaya: int,
        mantra: int,
        text: str,
        revision: PageRevision,
        snapshot_id: str,
        text_version_id: str,
        text_role: TextRole,
    ) -> StagingTextRecord:
        return StagingTextRecord(
            source_id=self.source_id,
            source_artifact_id=self.source_artifact_id,
            source_locator=f"{revision.resolved_title}#{adhyaya}.{mantra}",
            work_id=WORK_ID,
            hierarchy={"adhyaya": adhyaya, "mantra": mantra},
            text_original=text,
            language="sa",
            script="Devanagari",
            accented=has_vedic_accents(text),
            snapshot_id=snapshot_id,
            text_version_id=text_version_id,
            text_role=text_role,
        )

    def _parse_samhita_layer(
        self,
        blocks: list[str],
        *,
        adhyaya: int,
        revision: PageRevision,
        snapshot_id: str,
        failures: list[ParseFailure],
    ) -> tuple[list[StagingTextRecord], dict[int, str]]:
        """Read the unaccented samhita block: labelled mantras, one label per line.

        The samhita is the first ``<poem>`` block that yields any label at all. Scanning
        rather than assuming ``blocks[0]`` matters because some pages open with an image
        or a heading block.
        """
        records: list[StagingTextRecord] = []
        citations: dict[int, str] = {}
        for block in blocks:
            found = self._read_labelled_block(
                block,
                adhyaya=adhyaya,
                revision=revision,
                snapshot_id=snapshot_id,
                failures=failures,
                citations=citations,
            )
            if found:
                records = found
                break
        return records, citations

    def _read_labelled_block(
        self,
        block: str,
        *,
        adhyaya: int,
        revision: PageRevision,
        snapshot_id: str,
        failures: list[ParseFailure],
        citations: dict[int, str],
    ) -> list[StagingTextRecord]:
        records: list[StagingTextRecord] = []
        current: int | None = None
        buffer: list[str] = []

        def flush() -> None:
            if current is None:
                return
            body = " ".join(part for part in buffer if part)
            if not body:
                failures.append(
                    ParseFailure(
                        resolved_title=revision.resolved_title,
                        line_number=-1,
                        line=f"{adhyaya}.{current}",
                        reason="label carried no text lines",
                    )
                )
                return
            records.append(
                self._record(
                    adhyaya=adhyaya,
                    mantra=current,
                    text=normalize_nfc(body),
                    revision=revision,
                    snapshot_id=snapshot_id,
                    text_version_id="WIKISOURCE_SA.YV.VSM.UNACCENTED",
                    text_role=TextRole.PRIMARY_TEXT,
                )
            )

        for line_number, raw in enumerate(block.split("\n"), start=1):
            stripped = _strip_markup(raw)
            if not stripped:
                continue
            match = _SAMHITA_LABEL.match(stripped)
            if match is not None:
                try:
                    label_adhyaya = parse_mixed_digits(match.group("adhyaya"))
                    label_mantra = parse_mixed_digits(match.group("mantra"))
                except ValueError:
                    failures.append(
                        ParseFailure(
                            resolved_title=revision.resolved_title,
                            line_number=line_number,
                            line=stripped,
                            reason="label digits unreadable",
                        )
                    )
                    continue
                if label_adhyaya != adhyaya:
                    failures.append(
                        ParseFailure(
                            resolved_title=revision.resolved_title,
                            line_number=line_number,
                            line=stripped,
                            reason=f"label adhyaya {label_adhyaya} != page adhyaya {adhyaya}",
                        )
                    )
                    continue
                flush()
                current, buffer = label_mantra, []
                if annotation := match.group("annotation"):
                    citations[label_mantra] = " ".join(annotation.split())
                continue
            if _LABEL_SHAPED.match(stripped) and current is None:
                failures.append(
                    ParseFailure(
                        resolved_title=revision.resolved_title,
                        line_number=line_number,
                        line=stripped,
                        reason="line looks like a mantra label but did not match the label rule",
                    )
                )
                continue
            if current is not None:
                buffer.append(stripped)
        flush()
        return records

    def _parse_accented_layer(
        self,
        revision: PageRevision,
        *,
        adhyaya: int,
        snapshot_id: str,
        failures: list[ParseFailure],
    ) -> list[StagingTextRecord]:
        """Read accented mantras out of the Uvata-Mahidhara commentary block.

        **v2 boundary detection (primary signal: ordinal headers)**

        The 1929 Nirṇaya Sāgara edition prints a Sanskrit ordinal phrase before
        every mūla quotation: "तत्र प्रथमा।" for the first mantra, "द्वितीया।" for
        the second, and so on up to "षट्षष्टी।" in the long adhyayas. These lines
        are unaccented, short, and end with a single danda. This adapter now reads
        them as the PRIMARY mūla-start signal.

        When no ordinal header precedes an accented run (e.g., the ~22 mantras
        across all adhyayas where the edition omits the header), the onset falls
        back to the v1 accent-presence logic. Each such fallback is logged as a
        ``ParseFailure`` with reason ``ORDINAL_HEADER_ABSENT`` so gaps can be
        investigated without silently accepting inferred boundaries.

        The numbered terminal marker (``[।॥]{1,2} N [।॥]{1,2}``) remains the
        **end** signal and is unchanged from v1.

        **VSM 16.37 (both readings preserved)**

        The source prints mantra 37 twice, first accented as "स्रुत्याय" then
        as "सत्याय". The FIRST reading is kept as the canonical record. The SECOND
        reading is recorded in an ``EditorialIntervention`` with ``kind="SECOND_READING"``
        and ``status="NEEDS_REVIEW"`` — the full text is stored without truncation.
        Neither reading is silently discarded.

        The second reading appears on a single line beginning with the ordinal header
        "सप्तत्रिंशी। " immediately followed by the mantra text. This inline pattern
        is detected by ``_ORDINAL_HEADER_PREFIX`` and handled as a mūla-start signal
        while the ordinal prefix is stripped from the stored text.
        """
        records: list[StagingTextRecord] = []
        interventions: list[EditorialIntervention] = []
        seen: dict[int, int] = {}
        buffer: list[str] = []
        run_start_line = -1
        accented_start_lines: dict[int, int] = {}
        is_commentary = False
        ordinal_header_seen = False  # True when the previous meaningful line was an ordinal header
        # "Pending mula" state: when the ordinal-signaled accented run ends without a
        # numbered terminal embedded in the mūla lines themselves, we save the buffer
        # and scan up to _PENDING_MULA_SCAN_LIMIT subsequent non-accented commentary
        # lines looking for a commentary-confirmed terminal (the mantra number cited in
        # the gloss). If found, we emit the record and log COMMENTARY_TERMINAL_FALLBACK.
        # VSM 24.25 is the known case where the terminal is on the *second* commentary
        # line (Mahidhara's gloss), not the first (Uvata's).
        _PENDING_MULA_SCAN_LIMIT = 3
        pending_mula_buffer: list[str] = []
        pending_mula_scans: int = 0  # remaining commentary lines to scan

        for line_number, raw in enumerate(revision.content.split("\n"), start=1):
            stripped = _strip_markup(raw)
            if not stripped:
                continue

            # ── Primary signal: standalone ordinal header ────────────────────────
            # A short, unaccented, purely Devanagari line ending in a single danda,
            # optionally preceded by "तत्र ".
            is_pure_ordinal = (
                not has_vedic_accents(stripped)
                and len(stripped) <= _ORDINAL_MAX_LENGTH
                and _ORDINAL_HEADER.match(stripped) is not None
            )
            if is_pure_ordinal:
                # Flush any pending-mula scan that ran out of commentary lines.
                if pending_mula_scans > 0:
                    failures.append(
                        ParseFailure(
                            resolved_title=revision.resolved_title,
                            line_number=line_number,
                            line=" ".join(pending_mula_buffer)[:120],
                            reason=(
                                "accented run ended without a numbered terminal marker "
                                "(next ordinal reached before commentary terminal found)"
                            ),
                        )
                    )
                    pending_mula_buffer, pending_mula_scans = [], 0
                # Flush any incomplete run before this header — should not happen in
                # a well-formed source, but record it if it does.
                if buffer and not is_commentary:
                    failures.append(
                        ParseFailure(
                            resolved_title=revision.resolved_title,
                            line_number=line_number,
                            line=" ".join(buffer)[:120],
                            reason=(
                                "accented run ended without a numbered terminal marker "
                                "before the next ordinal header"
                            ),
                        )
                    )
                buffer, is_commentary = [], False
                ordinal_header_seen = True
                continue

            # ── Non-accented, non-ordinal line ──────────────────────────────────
            if not has_vedic_accents(stripped):
                # ── Pending-mula continuation scan ──────────────────────────────
                # If a prior ordinal-signaled run ended without an embedded terminal,
                # we are scanning subsequent commentary lines for a terminal that
                # confirms the mantra number (commentary terminal fallback).
                if pending_mula_scans > 0:
                    fallback_terminal = _ACCENTED_TERMINAL.search(stripped)
                    if fallback_terminal is not None:
                        try:
                            fb_mantra = parse_mixed_digits(
                                fallback_terminal.group("mantra").replace(" ", "")
                            )
                            fb_joined = " ".join(pending_mula_buffer)
                            fb_body = _LEADING_INVOCATION.sub("", fb_joined)
                            if fb_body != fb_joined:
                                interventions.append(
                                    EditorialIntervention(
                                        adhyaya=adhyaya,
                                        mantra=fb_mantra,
                                        kind="LEADING_INVOCATION_REMOVED",
                                        removed=fb_joined[: len(fb_joined) - len(fb_body)].strip(),
                                        reason=(
                                            "A scribal invocation opening the section. "
                                            "Front matter of the printed page, "
                                            "not part of the mantra."
                                        ),
                                    )
                                )
                            interventions.append(
                                EditorialIntervention(
                                    adhyaya=adhyaya,
                                    mantra=fb_mantra,
                                    kind="COMMENTARY_TERMINAL_FALLBACK",
                                    removed="",
                                    reason=(
                                        "The accented mūla lines lack an embedded "
                                        "numbered terminal "
                                        "marker; the mantra number was confirmed by a following "
                                        "commentary gloss. Text is complete but the mūla boundary "
                                        "was inferred from commentary rather than the mūla itself."
                                    ),
                                )
                            )
                            if fb_mantra in seen:
                                seen[fb_mantra] += 1
                                interventions.append(
                                    EditorialIntervention(
                                        adhyaya=adhyaya,
                                        mantra=fb_mantra,
                                        kind="SECOND_READING",
                                        removed=fb_body,
                                        reason=(
                                            "The page prints this mantra more than once. The FIRST "
                                            "reading is kept as the canonical record. This SECOND "
                                            "reading is stored here in full for "
                                            "philological review. "
                                            "Status: NEEDS_REVIEW."
                                        ),
                                        status="NEEDS_REVIEW",
                                    )
                                )
                            else:
                                seen[fb_mantra] = 1
                                accented_start_lines[fb_mantra] = run_start_line
                                records.append(
                                    self._record(
                                        adhyaya=adhyaya,
                                        mantra=fb_mantra,
                                        text=normalize_nfc(fb_body),
                                        revision=revision,
                                        snapshot_id=snapshot_id,
                                        text_version_id="WIKISOURCE_SA.YV.VSM.ACCENTED",
                                        text_role=TextRole.PARALLEL_TEXT,
                                    )
                                )
                            pending_mula_buffer, pending_mula_scans = [], 0
                        except ValueError:
                            pending_mula_scans -= 1
                            if pending_mula_scans == 0:
                                failures.append(
                                    ParseFailure(
                                        resolved_title=revision.resolved_title,
                                        line_number=line_number,
                                        line=" ".join(pending_mula_buffer)[:120],
                                        reason=(
                                            "accented run ended without a numbered terminal marker"
                                        ),
                                    )
                                )
                                pending_mula_buffer = []
                    else:
                        pending_mula_scans -= 1
                        if pending_mula_scans == 0:
                            failures.append(
                                ParseFailure(
                                    resolved_title=revision.resolved_title,
                                    line_number=line_number,
                                    line=" ".join(pending_mula_buffer)[:120],
                                    reason="accented run ended without a numbered terminal marker",
                                )
                            )
                            pending_mula_buffer = []
                    continue  # do NOT reset ordinal_header_seen or buffer here

                # ── Normal non-accented processing ─────────────────────────────
                # Any open accented run that is NOT commentary prose should have
                # closed with a terminal marker.  However, a small number of
                # adhyaya pages in the VSM corpus have their accented mūla block
                # without an embedded terminal: the mantra number appears only in
                # the immediately following commentary gloss(es).
                #
                # Strategy — "commentary terminal fallback" (initiated here):
                #   When all three conditions hold:
                #     (a) a non-empty mūla buffer is open (buffer and not is_commentary)
                #     (b) the run was started by an ordinal header (ordinal_header_seen)
                #     (c) THIS non-accented line carries a terminal marker
                #   → emit the record using the commentary-confirmed mantra number and
                #     log a COMMENTARY_TERMINAL_FALLBACK intervention.
                #
                # If (c) fails on this first line, we save the buffer in
                # pending_mula_buffer and scan up to _PENDING_MULA_SCAN_LIMIT more
                # non-accented lines (VSM 24.25: terminal is on the SECOND commentary
                # line, not the first).
                if buffer and not is_commentary and ordinal_header_seen:
                    fallback_terminal = _ACCENTED_TERMINAL.search(stripped)
                    if fallback_terminal is not None:
                        try:
                            fb_mantra = parse_mixed_digits(
                                fallback_terminal.group("mantra").replace(" ", "")
                            )
                            fb_joined = " ".join(buffer)
                            fb_body = _LEADING_INVOCATION.sub("", fb_joined)
                            if fb_body != fb_joined:
                                interventions.append(
                                    EditorialIntervention(
                                        adhyaya=adhyaya,
                                        mantra=fb_mantra,
                                        kind="LEADING_INVOCATION_REMOVED",
                                        removed=fb_joined[: len(fb_joined) - len(fb_body)].strip(),
                                        reason=(
                                            "A scribal invocation opening the section. "
                                            "Front matter of the printed page, "
                                            "not part of the mantra."
                                        ),
                                    )
                                )
                            interventions.append(
                                EditorialIntervention(
                                    adhyaya=adhyaya,
                                    mantra=fb_mantra,
                                    kind="COMMENTARY_TERMINAL_FALLBACK",
                                    removed="",
                                    reason=(
                                        "The accented mūla lines lack an embedded "
                                        "numbered terminal "
                                        "marker; the mantra number was confirmed "
                                        "by the immediately "
                                        "following commentary gloss. Text is complete but boundary "
                                        "was inferred from the commentary, not the mūla itself."
                                    ),
                                )
                            )
                            if fb_mantra in seen:
                                seen[fb_mantra] += 1
                                interventions.append(
                                    EditorialIntervention(
                                        adhyaya=adhyaya,
                                        mantra=fb_mantra,
                                        kind="SECOND_READING",
                                        removed=fb_body,
                                        reason=(
                                            "The page prints this mantra more than once. The FIRST "
                                            "reading is kept as the canonical record. This SECOND "
                                            "reading is stored here in full for "
                                            "philological review. "
                                            "Status: NEEDS_REVIEW."
                                        ),
                                        status="NEEDS_REVIEW",
                                    )
                                )
                            else:
                                seen[fb_mantra] = 1
                                accented_start_lines[fb_mantra] = run_start_line
                                records.append(
                                    self._record(
                                        adhyaya=adhyaya,
                                        mantra=fb_mantra,
                                        text=normalize_nfc(fb_body),
                                        revision=revision,
                                        snapshot_id=snapshot_id,
                                        text_version_id="WIKISOURCE_SA.YV.VSM.ACCENTED",
                                        text_role=TextRole.PARALLEL_TEXT,
                                    )
                                )
                            buffer, is_commentary = [], False
                            ordinal_header_seen = False
                            continue
                        except ValueError:
                            pass  # fall through to pending-mula path

                    # Terminal not found on this first non-accented line.
                    # Save buffer and scan up to _PENDING_MULA_SCAN_LIMIT more lines.
                    pending_mula_buffer = buffer[:]
                    pending_mula_scans = _PENDING_MULA_SCAN_LIMIT
                    buffer, is_commentary = [], False
                    ordinal_header_seen = False
                    continue

                if buffer and not is_commentary:
                    failures.append(
                        ParseFailure(
                            resolved_title=revision.resolved_title,
                            line_number=line_number,
                            line=" ".join(buffer)[:120],
                            reason="accented run ended without a numbered terminal marker",
                        )
                    )
                buffer, is_commentary = [], False
                ordinal_header_seen = False
                continue

            # ── Accented line ────────────────────────────────────────────────────
            # Check for an inline ordinal header prefix ONLY when no standalone
            # ordinal header was already seen for this run. This guards the known
            # case where a leading scribal invocation ("हरिः ॐ ।") opens the first
            # mantra: if the standalone ordinal "तत्र प्रथमा।" has already set
            # ordinal_header_seen, the invocation will be on the next accented line
            # and should be stripped by _LEADING_INVOCATION (preserving the editorial
            # intervention record) rather than silently dropped here.
            #
            # When ordinal_header_seen is False, an inline prefix is the only signal
            # available (VSM 16.37 second reading: "सप्तत्रिंशी। नमः स॒त्याय…").
            if not buffer and not ordinal_header_seen:
                inline_match = _ORDINAL_HEADER_PREFIX.match(stripped)
                if inline_match and len(inline_match.group(0)) <= _ORDINAL_MAX_LENGTH:
                    mantra_part = stripped[inline_match.end() :].strip()
                    if mantra_part:
                        # The ordinal prefix identified this run as a mūla; start
                        # fresh with the prefix stripped.
                        ordinal_header_seen = True
                        stripped = mantra_part

            # Determine whether this run is a mūla or a commentary excerpt.
            if not buffer:
                if ordinal_header_seen:
                    # Primary signal confirmed: ordinal header preceded this run.
                    is_commentary = False
                else:
                    # Fallback: rely on commentator sigla alone, as in v1.
                    is_commentary = stripped.startswith(_COMMENTATOR_SIGLA)
                    if not is_commentary:
                        # Accented run started without an ordinal header. Log it so
                        # the gap can be investigated; do not suppress the record.
                        failures.append(
                            ParseFailure(
                                resolved_title=revision.resolved_title,
                                line_number=line_number,
                                line=stripped[:120],
                                reason=(
                                    "ORDINAL_HEADER_ABSENT: accented run began without a "
                                    "preceding ordinal header; boundary inferred from "
                                    "accent-presence (v1 fallback)"
                                ),
                            )
                        )

            if not buffer:
                # The line this run OPENED on. An ORDINAL_HEADER_ABSENT failure is emitted
                # at exactly this moment and carries the same line_number, so recording it
                # lets a consumer join failure to record BY LINE instead of by text prefix.
                # Prefix joining is what mis-attributed VSM 11.9 and 11.28: both open with
                # the same 63-character formula, so a greedy earliest match claimed 11.9
                # for a fallback that belongs to 11.28.
                run_start_line = line_number
            buffer.append(stripped)
            terminal = _ACCENTED_TERMINAL.search(stripped)
            if terminal is None:
                continue

            # Terminal marker found — close the current run.
            ordinal_header_seen = False  # consumed

            if is_commentary:
                # A commentary paragraph; the mūla was (or will be) a separate run.
                buffer, is_commentary = [], False
                continue

            try:
                # Strip spaces before converting — the source occasionally writes
                # multi-digit numbers with a typesetting space (e.g., "४ १" = 41).
                mantra = parse_mixed_digits(terminal.group("mantra").replace(" ", ""))
            except ValueError:
                failures.append(
                    ParseFailure(
                        resolved_title=revision.resolved_title,
                        line_number=line_number,
                        line=stripped,
                        reason="terminal mantra number unreadable",
                    )
                )
                buffer, is_commentary = [], False
                continue

            joined = " ".join(buffer)
            body = _LEADING_INVOCATION.sub("", joined)
            if body != joined:
                interventions.append(
                    EditorialIntervention(
                        adhyaya=adhyaya,
                        mantra=mantra,
                        kind="LEADING_INVOCATION_REMOVED",
                        removed=joined[: len(joined) - len(body)].strip(),
                        reason=(
                            "A scribal invocation opening the section. Front matter of the "
                            "printed page, not part of the mantra."
                        ),
                    )
                )

            if mantra in seen:
                seen[mantra] += 1
                # Both readings are preserved. The FIRST reading is kept as the
                # canonical record (already emitted). The SECOND is stored here as
                # a reviewable intervention with its full text — no truncation.
                interventions.append(
                    EditorialIntervention(
                        adhyaya=adhyaya,
                        mantra=mantra,
                        kind="SECOND_READING",
                        removed=body,
                        reason=(
                            "The page prints this mantra more than once. The FIRST reading "
                            "is kept as the canonical record. This SECOND reading is stored "
                            "here in full for philological review. Where the two differ this "
                            "is a variant-selection judgement that the parser must not make: "
                            "VSM 16.37 prints both 'srutyaya' and 'satyaya'. "
                            "Status: NEEDS_REVIEW."
                        ),
                        status="NEEDS_REVIEW",
                    )
                )
                buffer, is_commentary = [], False
                continue

            seen[mantra] = 1
            records.append(
                self._record(
                    adhyaya=adhyaya,
                    mantra=mantra,
                    text=normalize_nfc(body),
                    revision=revision,
                    snapshot_id=snapshot_id,
                    text_version_id="WIKISOURCE_SA.YV.VSM.ACCENTED",
                    text_role=TextRole.PARALLEL_TEXT,
                )
            )
            accented_start_lines[mantra] = run_start_line
            buffer, is_commentary = [], False

        if buffer and not is_commentary:
            failures.append(
                ParseFailure(
                    resolved_title=revision.resolved_title,
                    line_number=-1,
                    line=" ".join(buffer)[:120],
                    reason="accented run at end of page had no numbered terminal marker",
                )
            )
        self._last_collisions = {m: n for m, n in sorted(seen.items()) if n > 1}
        self._last_interventions = interventions
        self._last_accented_start_lines = accented_start_lines
        return records
