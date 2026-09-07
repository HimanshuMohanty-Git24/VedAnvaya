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
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode

import orjson

from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord
from vedagraph.models.enums import TextRole
from vedagraph.normalize import has_vedic_accents, normalize_nfc

PARSER_VERSION = "wikisource-sa-vsm-v1"

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

# Closing marker of an accented mantra inside the commentary block: one or two dandas,
# the mantra number in Devanagari digits, then one or two dandas.
_ACCENTED_TERMINAL = re.compile(
    r"[।॥]{1,2}\s*(?P<mantra>[०-९]+)\s*[।॥]{1,2}\s*$"  # noqa: RUF001
)

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
    """

    adhyaya: int
    mantra: int
    kind: str
    removed: str
    reason: str


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
        return AdhyayaParse(
            adhyaya=adhyaya,
            revision=revision,
            samhita=samhita,
            accented=accented,
            alternate_citations=citations,
            failures=failures,
            accented_collisions=collisions,
            editorial_interventions=interventions,
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

        A mantra quotation is a run of consecutive accented lines closed by a line whose
        final token is the mantra number between dandas. The number is taken from that
        marker, so a missing quotation leaves a gap rather than shifting every later
        mantra by one.
        """
        records: list[StagingTextRecord] = []
        interventions: list[EditorialIntervention] = []
        seen: dict[int, int] = {}
        buffer: list[str] = []
        is_commentary = False
        for line_number, raw in enumerate(revision.content.split("\n"), start=1):
            stripped = _strip_markup(raw)
            if not stripped:
                continue
            if not has_vedic_accents(stripped):
                # Unaccented prose ends any quotation in progress. A run that opened
                # with a commentator siglum is expected to end this way, so it is not
                # reported as a failure.
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
                continue
            if not buffer:
                is_commentary = stripped.startswith(_COMMENTATOR_SIGLA)
            buffer.append(stripped)
            terminal = _ACCENTED_TERMINAL.search(stripped)
            if terminal is None:
                continue
            if is_commentary:
                # A commentary paragraph, not a reading of the mantra. Dropped on
                # purpose; the mantra's own quotation was recorded when it appeared.
                buffer, is_commentary = [], False
                continue
            try:
                mantra = parse_mixed_digits(terminal.group("mantra"))
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
                interventions.append(
                    EditorialIntervention(
                        adhyaya=adhyaya,
                        mantra=mantra,
                        kind="SECOND_READING_DROPPED",
                        removed=body[:200],
                        reason=(
                            "The page prints this mantra more than once. The FIRST reading "
                            "is kept and this one is dropped. Where the two differ this is "
                            "a variant-selection judgement, not a mechanical dedup, and it "
                            "should be reviewed: VSM 16.37 prints both 'srutyaya' and "
                            "'satyaya'."
                        ),
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
        return records
