"""GRETIL Atharvaveda-Samhita (Saunaka recension) legacy-HTML adapter.

Why this adapter is not the GRETIL TEI adapter
----------------------------------------------
GRETIL serves the Rigveda as TEI (``corpustei/sa_Rgveda-edAufrecht.xml``) but it does
**not** serve the Saunaka Atharvaveda that way.  The GRETIL index lists AVS only under the
legacy tree, as two hand-formatted HTML files whose payload is one ``<BR>``-separated line
per *pada*, each line prefixed by a parenthesised locator such as ``(AVS_1,1.1a)``.  There
is no TEI header, no ``<lg>`` element and no ``<div>`` hierarchy, so nothing in
``gretil.py`` is reusable and the licence cannot be read from a ``<availability>`` element.

Recension discipline
--------------------
Every locator in these two files is prefixed ``AVS_`` (with the palatal sibilant), the
document title says ``Atharvaveda-Samhita, Saunaka recension``, and the edition basis named
in the header is Orlandi's Saunaka transliteration collated against Roth/Whitney.  The
Paippalada recension is a *separate* GRETIL file (``corpustei/sa_paippalAdasaMhitA.xml``)
which this adapter refuses to touch.  ``assert_saunaka_recension`` makes the check explicit
so that a silently swapped snapshot fails loudly instead of being ingested as AVS.

What the source encodes that a naive parser destroys
----------------------------------------------------
1. **Two numbering systems in one locator.**  Books 11-20 carry the Vishva Bandhu
   (Hoshiarpur 1960-64) numbering in square brackets alongside the Roth/Whitney numbering.
   The bracket can sit on the sukta (``11,4[6].1a``), on the mantra (``11,3.32[4.1]a``),
   can span a range (``15,2.1[2.6-7]f``) and can be an explicit *absence* (``20,96.22[-]a``).
2. **Editorial apparatus inside the text line.**  ``|`` pada divider, ``||18||`` the
   source's own verse-number assertion, ``{12}`` an anuvaka/paryaya group marker, and a
   trailing ``[8]`` alternate-unit marker.  These are captured as fields; they are *not*
   deleted from ``text_original``, because deleting them would make the stored text a
   derived surface rather than the source.
3. **Prose.**  Large parts of kandas 15 and 16 (and 9.6, 12.5, 13.4) are paryaya prose, not
   metrical verse.  In this source a prose unit is not marked as prose; it simply has one
   pada.  This adapter therefore records ``pada_labels`` and refuses to assert a metrical
   classification either way.  ``is_single_pada_unit`` is a fact about the source, not a
   claim about metre.
4. **Label/marker disagreement.**  The parsed locator and the source's own ``||N||`` marker
   sometimes disagree (AVS 9.6, 12.5, 13.4, 20.96).  Both witnesses are kept on every unit
   so the disagreement stays visible instead of being silently resolved upstream.

The adapter produces staging records only.  It never produces canonical records.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from vedagraph.ingest.adapters.base import DiscoveredResource, SourceAdapter
from vedagraph.models import StagingTextRecord
from vedagraph.models.enums import TextRole
from vedagraph.normalize import has_vedic_accents

PARSER_VERSION = "gretil-avs-saunaka-legacy-html-v1"

WORK_ID = "VG:WORK:AV:SAU"

#: Registered source id.  These files are two more ARTIFACTS of GRETIL, not a new source:
#: rights differ per file within one host, which is exactly what the artifact layer is for.
#: GRETIL's Rigveda TEI is CC BY-NC-SA while these Atharvaveda files are REFERENCE_ONLY, so
#: a source-level rights value for a hypothetical "GRETIL_AVS" could not have been correct.
SOURCE_ID = "GRETIL"

#: Local raw-snapshot namespace, deliberately NOT the registered source id.
#: ``PoliteFetcher`` derives its cache directory from whatever id it is handed, so keeping
#: this separate stores the Atharvaveda snapshots under ``data/raw/gretil_avs/`` instead of
#: mixing them into the Rigveda's ``data/raw/gretil/``.  A raw directory is local storage
#: layout; the registry ``source_id`` is the contract.  The two are allowed to differ and
#: the divergence is recorded in the artifact provenance.
SNAPSHOT_SOURCE_ID = "GRETIL_AVS"

GRETIL_AVS_BASE = "https://gretil.sub.uni-goettingen.de/gretil/1_sanskr/1_veda/1_sam"

#: The two GRETIL legacy artifacts, keyed by the variant name used as a build scope.
ARTIFACTS: dict[str, tuple[str, str, str]] = {
    # variant -> (filename, source_artifact_id, human label)
    "ACCENTED": (
        "avs_acu.htm",
        "GRETIL.AV.SAUNAKA.ACCENTED.HTML",
        "Atharvaveda-Samhita, Saunaka recension, ACCENTED TEXT",
    ),
    "UNACCENTED": (
        "avs___u.htm",
        "GRETIL.AV.SAUNAKA.UNACCENTED.HTML",
        "Atharvaveda-Samhita, Saunaka recension, UNACCENTED TEXT",
    ),
}

#: Locator grammar, derived by enumerating every distinct shape actually present in the
#: two files (22 shapes over 11,395 tokens) rather than from an assumed format.
#: Verified to match all 11,395 tokens with zero misses.
_LOCATOR = re.compile(
    r"\(AVŚ_"
    r"(?P<kanda>\d+),"
    r"(?P<sukta>\d+)(?:\[(?P<alt_sukta>[^\]]*)\])?"
    r"\.(?:\[(?P<alt_prefix>[^\]]*)\])?"
    r"(?P<mantra>\d+)(?:\[(?P<alt_mantra>[^\]]*)\])?"
    r"(?P<pada>[^\s)]*)"
    r"\)"
)

_LINE_BREAK = re.compile(r"<\s*br\s*/?\s*>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]*>")

#: The source's own verse-number assertion, e.g. ``||18||``.
_VERSE_MARKER = re.compile(r"\|\|(\d+)\|\|")
#: Anuvaka / paryaya group marker, e.g. ``{12}``.
_GROUP_MARKER = re.compile(r"\{(\d+)\}")
#: Trailing alternate-unit marker used in the kanda 15 paryayas, e.g. ``[8]`` / ``[6-7]``.
_ALT_UNIT_MARKER = re.compile(r"\[(\d+(?:-\d+)?)\]\s*$")

_TITLE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)

_PADA_ORDER = "abcdefghijklmnopqrstuvwxyz"

#: Verbatim licence sentence carried by both legacy files.  Matched, never paraphrased.
_LICENCE_SENTINEL = "FOR REFERENCE PURPOSES ONLY"


class RecensionMismatchError(ValueError):
    """Raised when a snapshot cannot be proven to be the Saunaka recension."""


@dataclass(frozen=True)
class AVSHeaderMetadata:
    """Provenance read out of the legacy HTML preamble, verbatim where it is a claim."""

    title: str | None
    accent_declaration: str | None
    edition_basis: tuple[str, ...]
    input_credits: tuple[str, ...]
    alternate_numbering_note: tuple[str, ...]
    licence_statement_verbatim: str | None
    stated_total_counts: tuple[str, ...]


@dataclass
class AVSUnit:
    """One parsed AVS unit: everything the source says about one numbered passage.

    A "unit" is a maximal run of consecutive pada lines that share a (kanda, sukta, mantra)
    locator *and* whose pada letters strictly advance.  The pada-advance condition is what
    keeps AVS 20.96.22 -- two genuinely different verses that both carry the number 22 --
    from being merged into a single seven-pada blob.
    """

    kanda: int
    sukta: int
    mantra: int
    occurrence: int = 1
    pada_labels: list[str] = field(default_factory=list)
    pada_texts: list[str] = field(default_factory=list)
    locators: list[str] = field(default_factory=list)
    #: The source's own ``||N||`` assertion for this unit, or None when it carries none.
    source_verse_marker: int | None = None
    #: Anuvaka / paryaya group number closed at this unit, if any.
    group_marker: int | None = None
    #: Vishva Bandhu sukta number, when the locator carries one.
    alternate_sukta: str | None = None
    #: Vishva Bandhu mantra numbers taken from the *locator* brackets, in pada order.
    alternate_mantras: list[str] = field(default_factory=list)
    #: The source's own trailing ``[8]`` markers.  A second, independent witness to the
    #: same alternate numbering, kept separately so the two can be cross-checked rather
    #: than silently merged.
    alternate_unit_markers: list[str] = field(default_factory=list)
    #: True when the locator explicitly marks absence in the alternate edition (``[-]``).
    alternate_absent: bool = False

    @property
    def canonical_locator(self) -> str:
        return f"AVS {self.kanda}.{self.sukta}.{self.mantra}"

    @property
    def text_original(self) -> str:
        """Lossless source text: the pada lines, verbatim, one per line.

        Nothing is removed.  The pada divider, the source verse marker and the group
        marker all survive here; consumers that want a clean metrical surface must derive
        one, because a derived surface is not what the source said.
        """
        return "\n".join(self.pada_texts)

    @property
    def is_single_pada_unit(self) -> bool:
        """A source fact, not a metrical claim.  Most prose paryaya units are single-pada."""
        return len(self.pada_texts) == 1

    @property
    def label_agrees_with_source_marker(self) -> bool | None:
        """None when the source asserts no verse number for this unit."""
        if self.source_verse_marker is None:
            return None
        return self.source_verse_marker == self.mantra

    @property
    def alternate_citation_label(self) -> str | None:
        """Vishva Bandhu label for this unit, or None when the source gives none.

        Three locator shapes carry the alternate numbering and each means something
        different, so each is rendered differently rather than through one guess:

        * ``11,4[6].1``  the *sukta* differs      -> AVS 11.6.1
        * ``11,3.32[4.1]``  the sukta *and* mantra differ -> AVS 11.4.1
        * ``15,2.1[2.1]a`` ... ``[2.8]g``  one Roth/Whitney verse is *eight* Vishva Bandhu
          verses, so the label is a range -> AVS 15.2.1-8

        ``[-]`` means the unit has no counterpart in the alternate edition, and that is
        reported as "no label" rather than as an invented one.
        """
        if self.alternate_absent:
            return None
        if self.alternate_sukta:
            return f"AVS {self.kanda}.{self.alternate_sukta}.{self.mantra}"
        distinct = [value for value in dict.fromkeys(self.alternate_mantras) if value]
        if not distinct:
            return None
        if len(distinct) == 1:
            return f"AVS {self.kanda}.{distinct[0]}"
        first, last = distinct[0], distinct[-1]
        first_prefix, _, first_tail = first.rpartition(".")
        last_prefix, _, last_tail = last.rpartition(".")
        if first_prefix and first_prefix == last_prefix:
            # An endpoint may itself be a range ("5.2-3"): take the outer bounds so that
            # AVS 15.5.1 .. 15.5.2-3 renders as 1-3 and not as the nonsense "1-2-3".
            low = first_tail.split("-")[0]
            high = last_tail.split("-")[-1]
            return f"AVS {self.kanda}.{first_prefix}.{low}-{high}"
        return f"AVS {self.kanda}.{first}-{last}"


def _pada_rank(pada: str) -> int:
    """Order a pada letter.  Unknown letters sort last so they never break a run.

    AVS 8.5.11 carries the pada letter "d-with-dot-below" where "c" was meant.  Treating an
    unrecognised letter as "always advances" keeps that typo inside its own verse instead of
    splitting the verse in two.
    """
    if len(pada) == 1 and pada in _PADA_ORDER:
        return _PADA_ORDER.index(pada)
    return len(_PADA_ORDER)


def _strip_tags(fragment: str) -> str:
    return _TAG.sub("", fragment)


def _read(snapshot_path: Path) -> str:
    return snapshot_path.read_bytes().decode("utf-8")


def assert_saunaka_recension(snapshot_path: Path) -> str:
    """Prove from the artifact itself that this is AVS, not AVP.  Return the title.

    Two independent witnesses must agree: the document title must name the Saunaka
    recension, and the body locators must use the ``AVS_`` prefix.  The Paippalada file
    uses neither.
    """
    raw = _read(snapshot_path)
    title_match = _TITLE.search(raw)
    title = _strip_tags(title_match.group(1)).strip() if title_match else ""
    lowered = title.lower()
    if "atharvaveda" not in lowered or "saunaka" not in lowered:
        raise RecensionMismatchError(
            f"snapshot title does not declare the Saunaka Atharvaveda: {title!r}"
        )
    if "paippalada" in lowered or "paippalAda" in title:
        raise RecensionMismatchError(f"snapshot declares the Paippalada recension: {title!r}")
    if not _LOCATOR.search(raw):
        raise RecensionMismatchError("snapshot carries no AVS_ locators")
    return title


class GretilAVSAdapter(SourceAdapter):
    """Parse one GRETIL legacy AVS artifact into staging records."""

    #: ``SourceAdapter.fetch`` checks the resource id against this, so it carries the
    #: snapshot namespace.  Emitted records use ``SOURCE_ID``, the registered id.
    source_id = SNAPSHOT_SOURCE_ID

    def __init__(self, *, variant: str = "ACCENTED") -> None:
        if variant not in ARTIFACTS:
            raise ValueError(f"unknown AVS artifact variant: {variant!r}")
        self.variant = variant
        filename, artifact_id, label = ARTIFACTS[variant]
        self.filename = filename
        self.source_artifact_id = artifact_id
        self.artifact_label = label

    @property
    def url(self) -> str:
        return f"{GRETIL_AVS_BASE}/{self.filename}"

    async def discover(self, scope: str) -> list[DiscoveredResource]:
        """One artifact per adapter instance.  ``scope`` selects nothing: the file is whole.

        The GRETIL legacy AVS text is a single whole-Samhita HTML file, so there is no
        per-kanda resource to discover.  Bounding happens at parse time.
        """
        if scope not in {"AV", "AVS", self.variant}:
            return []
        return [
            DiscoveredResource(
                source_id=SNAPSHOT_SOURCE_ID,
                url=self.url,
                locator=f"GRETIL {self.filename}",
                media_type="text/html",
            )
        ]

    # -- provenance ----------------------------------------------------------------

    def extract_header_metadata(self, snapshot_path: Path) -> AVSHeaderMetadata:
        """Read the legacy preamble.  The licence sentence is captured verbatim."""
        raw = _read(snapshot_path)
        first_locator = _LOCATOR.search(raw)
        preamble = raw[: first_locator.start()] if first_locator else raw
        lines = [
            cleaned
            for line in _LINE_BREAK.split(preamble)
            if (cleaned := " ".join(_strip_tags(line).split()))
        ]
        title_match = _TITLE.search(raw)
        title = _strip_tags(title_match.group(1)).strip() if title_match else None

        accent_declaration = next(
            (line for line in lines if line in {"ACCENTED TEXT", "UNACCENTED TEXT"}), None
        )
        edition_basis = tuple(
            line
            for line in lines
            if line.startswith("Based on the ed")
            or line.startswith("trasliterazione")
            or line.startswith("collated with the ed")
            or line.startswith("Atharva Veda Sanhita")
        )
        input_credits = tuple(
            line
            for line in lines
            if line.startswith(("Input by", "TITUS redaction", "Text of Books", "Revised by"))
            or line.startswith(("Arlo Griffiths", "Philipp Kubisch"))
        )
        numbering_note_start = next(
            (index for index, line in enumerate(lines) if line.startswith("NOTE ON REFERENCES")),
            None,
        )
        alternate_numbering_note: tuple[str, ...] = ()
        if numbering_note_start is not None:
            alternate_numbering_note = tuple(lines[numbering_note_start : numbering_note_start + 6])
        licence = next((line for line in lines if _LICENCE_SENTINEL in line), None)
        if licence is not None:
            index = lines.index(licence)
            licence = " ".join(lines[index : index + 2])
        # The artifact asserts no total kanda/sukta/mantra count anywhere.  Prove it rather
        # than assuming it, so the reconciliation report can say so with evidence.
        stated_total_counts = tuple(
            line
            for line in lines
            if re.search(r"\b(total|altogether|hymns|verses|stanzas)\b", line, re.IGNORECASE)
        )
        return AVSHeaderMetadata(
            title=title,
            accent_declaration=accent_declaration,
            edition_basis=edition_basis,
            input_credits=input_credits,
            alternate_numbering_note=alternate_numbering_note,
            licence_statement_verbatim=licence,
            stated_total_counts=stated_total_counts,
        )

    # -- parsing -------------------------------------------------------------------

    def parse_units(
        self,
        snapshot_path: Path,
        *,
        kandas: frozenset[int] | None = None,
        suktas: frozenset[tuple[int, int]] | None = None,
    ) -> list[AVSUnit]:
        """Parse into ordered units, optionally bounded to whole kandas or whole suktas.

        Bounding is applied *after* run detection so that a bounded build sees exactly the
        units a whole-file build would see; it never changes how a unit is formed.
        """
        assert_saunaka_recension(snapshot_path)
        raw = _read(snapshot_path)
        units: list[AVSUnit] = []
        occurrences: dict[tuple[int, int, int], int] = {}
        previous: tuple[int, int, int] | None = None
        previous_rank = -1

        for line in _LINE_BREAK.split(raw):
            match = _LOCATOR.search(line)
            if match is None:
                continue
            kanda = int(match.group("kanda"))
            sukta = int(match.group("sukta"))
            mantra = int(match.group("mantra"))
            pada = match.group("pada")
            rank = _pada_rank(pada)
            triple = (kanda, sukta, mantra)

            # Text is everything after the locator on this line, tags removed, verbatim
            # otherwise.  Leading/trailing whitespace is collapsed; interior characters,
            # including the editorial apparatus, are untouched.
            body = " ".join(_strip_tags(line[match.end() :]).split())

            starts_new_unit = triple != previous or rank <= previous_rank
            if starts_new_unit:
                occurrences[triple] = occurrences.get(triple, 0) + 1
                units.append(AVSUnit(kanda, sukta, mantra, occurrence=occurrences[triple]))
            unit = units[-1]
            unit.pada_labels.append(pada)
            unit.pada_texts.append(body)
            unit.locators.append(match.group(0))

            if (verse := _VERSE_MARKER.search(body)) is not None:
                unit.source_verse_marker = int(verse.group(1))
            if (group := _GROUP_MARKER.search(body)) is not None:
                unit.group_marker = int(group.group(1))
            if (alt_sukta := match.group("alt_sukta")) is not None:
                if alt_sukta == "-":
                    unit.alternate_absent = True
                else:
                    unit.alternate_sukta = alt_sukta
            for group_name in ("alt_prefix", "alt_mantra"):
                value = match.group(group_name)
                if value is None:
                    continue
                if value == "-":
                    unit.alternate_absent = True
                else:
                    unit.alternate_mantras.append(value)
            if (alt_unit := _ALT_UNIT_MARKER.search(body)) is not None:
                unit.alternate_unit_markers.append(alt_unit.group(1))

            previous, previous_rank = triple, rank

        if kandas is not None:
            units = [unit for unit in units if unit.kanda in kandas]
        if suktas is not None:
            units = [unit for unit in units if (unit.kanda, unit.sukta) in suktas]
        return units

    def parse(
        self,
        snapshot_path: Path,
        *,
        snapshot_id: str,
        kandas: frozenset[int] | None = None,
        suktas: frozenset[tuple[int, int]] | None = None,
    ) -> list[StagingTextRecord]:
        """Contract-shaped staging records.  Duplicated locators are all retained here.

        Deduplication is a *canonicalisation* decision and therefore does not belong in an
        adapter.  Every parsed occurrence is emitted, and ``hierarchy["occurrence"]``
        distinguishes the collisions so nothing is lost before the build sees it.
        """
        units = self.parse_units(snapshot_path, kandas=kandas, suktas=suktas)
        records: list[StagingTextRecord] = []
        for unit in units:
            text = unit.text_original
            hierarchy: dict[str, int | str] = {
                "kanda": unit.kanda,
                "sukta": unit.sukta,
                "mantra": unit.mantra,
            }
            if unit.occurrence != 1:
                hierarchy["occurrence"] = unit.occurrence
            records.append(
                StagingTextRecord(
                    source_id=SOURCE_ID,
                    source_artifact_id=self.source_artifact_id,
                    source_locator=" ".join(unit.locators),
                    work_id=WORK_ID,
                    hierarchy=hierarchy,
                    text_original=text,
                    language="sa",
                    # Latin scholarly transliteration, not Devanagari: vocalic r is
                    # r + U+0325, udatta is U+0301, svarita is U+0300.
                    script="Latin",
                    accented=has_vedic_accents(text),
                    snapshot_id=snapshot_id,
                    text_role=TextRole.PRIMARY_TEXT,
                )
            )
        return records
