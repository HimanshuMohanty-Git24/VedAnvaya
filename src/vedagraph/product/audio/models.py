"""The audio catalog's vocabulary: what a recording is, and what we mapped it to.

**Why this layer exists outside the graph at all.** Audio is product content, not
knowledge. The ontology is frozen and the graph census is a release gate, so an `Audio`
node would reopen both for a layer that asserts nothing about the Vedas. The catalog is
therefore a sidecar keyed by ``canonical_key``, and :mod:`vedagraph.product.audio.catalog`
is the only thing that joins the two.

**The failure this vocabulary is shaped to prevent.** A recording that covers one sukta
attached to each of its ten mantras as though each mantra had its own track. The catalog's
present source publishes one file per *verse*, so that shape is no longer the common case
-- but the first source tried did record whole suktas, a reader heard the difference
immediately, and a future source may be coarse again. So :class:`AudioScope` records *what
the file covers* and :class:`MappingConfidence` records *how we know*, and the two stay
separate fields: a per-sukta file honestly mapped to a sukta is `STRUCTURAL` and correct,
while the same file mapped to a mantra would be a lie regardless of how confident the
mapper felt.

**Two vocabularies for scope, on purpose.** :class:`AudioScope` is the tradition's
vocabulary -- SUKTA, ADHYAYA, KANDA -- because that is what a recording's publisher
states and what a reader understands. The graph's node vocabulary is
``entity_type``: HYMN, SECTION, MANTRA, STRUCTURAL_CONTAINER. They do not correspond one
to one (a SECTION node is an adhyaya in the Yajurveda and a kanda in the Atharvaveda), so
:data:`SCOPE_TO_ENTITY_TYPES` holds the correspondence and the validator checks it. A
record claiming ``scope_type=MANTRA`` over a key whose node is a HYMN is rejected rather
than rendered.

**Gana is not arcika.** The Samavedic text in this corpus is the Kauthuma arcika; the
gana corpus is not held. External Samavedic recordings are very often gana -- Wikimedia
Commons describes its files as "Recitation of a melody of Samaveda" -- so
:attr:`AudioType.SAMAGANA` exists to keep that distinction on the record. A gana
performance must never be catalogued as :attr:`AudioType.RECITATION` against an arcika
verse, because the product would then imply it holds a corpus it does not.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AudioScope(StrEnum):
    """What structural span one recording actually covers.

    The tradition's vocabulary rather than the graph's, because this field records the
    publisher's claim about the file. Values are deliberately coarse: there is no
    half-verse or pada value, since no located source segments below the verse.
    """

    MANTRA = "MANTRA"
    """One verse, recorded on its own. The granularity the current source publishes."""

    SUKTA = "SUKTA"
    """One hymn, recorded whole. What a coarser source offers for the Rigveda or Atharvaveda."""

    SECTION = "SECTION"
    """A structural span the source names but does not map to a traditional level."""

    ADHYAYA = "ADHYAYA"
    """One Yajurvedic chapter, recorded whole."""

    KANDA = "KANDA"
    """One Atharvavedic book."""

    COLLECTION = "COLLECTION"
    """A named Samavedic collection -- ARANYA, CHANDA, MAHANAMNYA, UTTARA."""

    WORK = "WORK"
    """The whole Samhita. What a source offers when its internal order is not resolvable."""

    UNKNOWN = "UNKNOWN"
    """The source does not state the span. Never guess it into a narrower value."""


class AudioType(StrEnum):
    """What kind of vocal performance the recording is.

    Small on purpose. This is product metadata, not a musicology ontology, and every
    value here answers exactly one question a reader can be misled about.
    """

    RECITATION = "RECITATION"
    """Samhita-patha style spoken recitation of the text as this corpus holds it."""

    CHANT = "CHANT"
    """Recitation with tonal realisation, where the source says so without naming a gana."""

    SAMAGANA = "SAMAGANA"
    """A Samavedic melodic performance. NOT the arcika text this corpus holds."""

    PADAPATHA = "PADAPATHA"
    """Word-by-word recitation. A different text surface from the samhita reading."""

    OTHER_VEDIC_RECITATION = "OTHER_VEDIC_RECITATION"
    """Vedic recitation whose style the source does not establish."""


class MappingConfidence(StrEnum):
    """How the recording came to be attached to this passage.

    Ordered from strongest to weakest. The product renders different copy for each, so
    weakening a record's confidence to widen coverage changes what the reader is told
    rather than hiding the change.
    """

    EXACT = "EXACT"
    """The source states this file is this passage, at this passage's own granularity."""

    HIGH = "HIGH"
    """The source states the passage, and independent structure confirms it."""

    STRUCTURAL = "STRUCTURAL"
    """Derived from the source's own file-per-passage layout, verified against the graph.

    A file is a given passage's because the source's path or numbering scheme says so and
    because that scheme's boundaries coincide with the canonical structure -- not because
    the recited text was ever compared. Weaker than :attr:`EXACT` for exactly that reason:
    a scheme can be right about where its files sit and wrong about how they are numbered,
    which is precisely what a renumbered edition looks like from outside.
    """

    EXTERNAL_ONLY = "EXTERNAL_ONLY"
    """A real recording of this Veda whose position inside it is not established.

    Catalogued so a reader can find it, never presented as a given passage's recording.
    """


class PublicationTier(StrEnum):
    """Whether a human has heard this recording, kept apart from whether it is published.

    **Why the two were ever one field.** Until 2026-09-19 they were not fields at all:
    publication *was* the gate. ``OWNER_DECISION_E_AUDIO_GATE`` (OWNER_DECISIONS.md §8 and
    §14) held that no fragile audio entered the canonical layer until its row had been
    listened to, so 954 staged rows sat outside the catalogue and the catalogue carried no
    review vocabulary because everything in it was, by construction, on the same footing.

    ``OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION`` of 2026-09-19 supersedes that gate and
    replaces it with this enum. Audible review is now a badge. The one thing the new policy
    does not permit is the collapse these two values exist to prevent: describing an
    unreviewed recording as verified. Hence
    :attr:`AudioRecord.audible_review_evidence`, which
    :meth:`AudioRecord._check_internal_consistency` requires before
    :attr:`RELEASED_VERIFIED` may be written and refuses on
    :attr:`SOURCE_MAPPED_UNREVIEWED` -- so the tier cannot be typed, only earned, and
    cannot be half-typed either.

    The default is :attr:`SOURCE_MAPPED_UNREVIEWED` on purpose. A catalogue line written
    before this field existed carries no tier, and the honest reading of a row that says
    nothing about review is that nobody reviewed it. A default of
    ``RELEASED_VERIFIED`` would have promoted all 16,834 incumbent records to a verdict no
    listener ever gave.
    """

    RELEASED_VERIFIED = "RELEASED_VERIFIED"
    """A named person played this recording and confirmed it is the passage it is mapped to.

    The evidence is a decision row in ``data/manual/audio_review/sample_decisions.jsonl``
    naming the reviewer, the time, the media URL actually played and the bytes heard.
    """

    SOURCE_MAPPED_UNREVIEWED = "SOURCE_MAPPED_UNREVIEWED"
    """Mapped and checked by instrument, never heard by a person.

    Published because the source resolves, the canonical mapping is evidenced, the text
    comparison passed and no rejection stands against it -- and *not* published as
    verified. Every reader-facing surface must say so, and
    :func:`~vedagraph.product.audio.catalog.tier_note` is the one place that sentence is
    written.
    """


class Availability(StrEnum):
    """Whether the media answered when last checked.

    ``BROKEN`` is deliberately hard to reach: a single timeout is
    ``TEMPORARILY_UNAVAILABLE``, because third-party media hosts time out under ordinary
    polite load and treating that as proof the recording never existed would delete real
    coverage from the catalog.
    """

    AVAILABLE = "AVAILABLE"
    """Reachable, with a plausible media content type."""

    TEMPORARILY_UNAVAILABLE = "TEMPORARILY_UNAVAILABLE"
    """Did not answer. Says nothing about whether the recording exists."""

    BROKEN = "BROKEN"
    """Answered with a definite absence -- a 404 or 410."""

    EXTERNAL_ONLY = "EXTERNAL_ONLY"
    """Not probed by design: a source page or player rather than a media file."""


class PlaybackMode(StrEnum):
    """How the product is allowed to play this record."""

    REMOTE_DIRECT = "REMOTE_DIRECT"
    """Stream the publisher's own URL. No copy is held."""

    LOCAL_CACHE = "LOCAL_CACHE"
    """Served from ``data/audio/cache``. Only for records whose licence permits a copy."""

    EXTERNAL_EMBED = "EXTERNAL_EMBED"
    """A player the publisher supports embedding."""

    EXTERNAL_LINK = "EXTERNAL_LINK"
    """Open the source page. The product plays nothing itself."""

    PROXIED_STREAM = "PROXIED_STREAM"
    """The publisher serves audio in a form a browser cannot play, so this product
    fetches, decodes and re-serves it through its own streaming route.

    Needed because VedSearch returns audio as base64 inside a JSON document rather than as
    a media file: handing that URL to an ``<audio>`` element plays nothing. The route is
    addressed by catalog id and takes no URL parameter, so it cannot be used as an open
    proxy, and ``media_url`` is never published to the client for these records -- a client
    that fetched it would get JSON.
    """


#: Which graph ``entity_type`` values a given :class:`AudioScope` may legitimately name.
#:
#: This is the check that catches the defect in Section 44 of the release spec -- "Sukta
#: recording labelled as mantra". A ``scope_type`` is a claim about the recording and a
#: ``scope_key`` is a node in the graph; if the node's type is not in this map's entry for
#: the claimed scope, one of the two is wrong and the record is rejected.
#:
#: ``SECTION`` nodes appear under three scopes because the graph uses one node type for
#: the Rigvedic mandala, the Yajurvedic adhyaya and the Atharvavedic kanda.
SCOPE_TO_ENTITY_TYPES: Final[dict[AudioScope, frozenset[str]]] = {
    AudioScope.MANTRA: frozenset({"MANTRA"}),
    AudioScope.SUKTA: frozenset({"HYMN"}),
    AudioScope.SECTION: frozenset({"SECTION", "STRUCTURAL_CONTAINER"}),
    AudioScope.ADHYAYA: frozenset({"SECTION"}),
    AudioScope.KANDA: frozenset({"SECTION"}),
    AudioScope.COLLECTION: frozenset({"STRUCTURAL_CONTAINER"}),
    AudioScope.WORK: frozenset({"WORK"}),
    AudioScope.UNKNOWN: frozenset(),
}

#: The recension code each ``veda`` value must carry, from ``EXPECTED_WORK_IDS``.
#:
#: Present so that cross-recension mislabelling is a schema error and not a review
#: finding. Taittiriya audio cannot be catalogued as Yajurvedic here, because the only
#: accepted Yajurvedic recension string is ``VSM``; Paippalada cannot pass as ``SAU``;
#: Jaiminiya cannot pass as ``KAU``.
VEDA_RECENSIONS: Final[dict[str, str]] = {
    "RV": "SAK",
    "SV": "KAU",
    "YV": "VSM",
    "AV": "SAU",
}


class AudioRecord(BaseModel):
    """One recording, what it claims to be, and what this product mapped it to.

    Strict and frozen for the same reason the API models are: a typo in a catalog field
    name must fail the load rather than silently drop the field that carried the
    provenance.

    **Every record answers four questions** -- where it came from (``source_name``,
    ``source_page``), what it claims to be (``audio_type``, ``title``, ``performer``,
    ``tradition``), what we mapped it to (``veda``, ``recension``, ``scope_type``,
    ``scope_key``) and how certain that is (``mapping_confidence``, ``mapping_method``).
    Section 12 of the release spec makes these more important than rights metadata, and
    the model enforces them by making the first three non-optional.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    audio_id: str = Field(
        min_length=3,
        description="Stable identifier. Derived from the source and its own path, never "
        "from the passage, so re-running discovery does not renumber the catalog.",
    )

    veda: str = Field(description="RV, SV, YV or AV.")
    recension: str = Field(
        description="The recension code. Checked against VEDA_RECENSIONS, so a "
        "cross-recension record cannot load."
    )

    scope_type: AudioScope
    scope_key: str | None = Field(
        default=None,
        description="The canonical_key this recording is attached to, or None for an "
        "EXTERNAL_ONLY record that names no position inside its Veda.",
    )

    audio_type: AudioType

    title: str = Field(min_length=1, description="What the source calls this recording.")
    performer: str | None = Field(
        default=None,
        description="Named reciter, where the source names one. Never inferred: the "
        "current source states no reciter anywhere reached, so these are None and say so.",
    )
    tradition: str | None = Field(
        default=None, description="Recitation tradition or sakha-style, where stated."
    )
    location: str | None = Field(default=None, description="Recording location, where stated.")

    source_name: str = Field(min_length=1, description="The publishing body or archive.")
    source_page: str = Field(
        min_length=1, description="A human-openable page establishing this recording's origin."
    )

    media_url: str | None = Field(
        default=None, description="Direct media URL, where one is publicly served."
    )
    embed_url: str | None = Field(
        default=None, description="Embeddable player URL, where supported."
    )
    local_cache_path: str | None = Field(
        default=None,
        description="Path under data/audio/cache, relative to the data directory. Never "
        "absolute: an absolute path in a committed manifest leaks the builder's filesystem.",
    )

    duration_seconds: float | None = Field(
        default=None, gt=0, description="Measured, never estimated from text length."
    )
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, gt=0)

    mapping_method: str = Field(
        min_length=1, description="How the mapping was derived, in one reproducible phrase."
    )
    mapping_confidence: MappingConfidence
    availability: Availability = Availability.EXTERNAL_ONLY
    playback_mode: PlaybackMode

    publication_tier: PublicationTier = Field(
        default=PublicationTier.SOURCE_MAPPED_UNREVIEWED,
        description="Whether a person has heard this recording. Defaults to the unreviewed "
        "tier, so a row written before this field existed is never silently promoted.",
    )
    audible_review_evidence: str | None = Field(
        default=None,
        description="Where the hearing is recorded, for a RELEASED_VERIFIED row: the "
        "artifact, the reviewer and the timestamp, in one phrase. Required for that tier "
        "and refused for the other, so the two fields can never disagree.",
    )

    licence: str | None = Field(
        default=None,
        description="The per-file licence where the source states one. Per-file and never "
        "flattened to a collection default: the Commons Samavedic set is 458 CC BY-SA and "
        "16 CC0, and collapsing them would misstate 16 files' terms.",
    )
    local_copy_permitted: bool = Field(
        default=False,
        description="Whether this product may keep a copy of the bytes. Default False, so "
        "the cache tool mirrors nothing it was not explicitly told it may. Setting it true "
        "permits a copy rather than causing one: the cache tool still refuses to run "
        "without an explicit --all, --veda or --audio-id. A source whose terms or technical "
        "measures indicate otherwise stays False and is streamed instead of copied.",
    )
    attribution: str | None = Field(
        default=None, description="The attribution string a share-alike licence requires."
    )

    source_reference: str | None = Field(
        default=None,
        description="The source's own identifier for this item, e.g. VedSearch's "
        "``shlok_id`` '1.1.1'. Kept so the streaming route can re-derive the fetch without "
        "parsing it back out of a URL.",
    )
    text_verified: bool = Field(
        default=False,
        description="Whether the text the source says this recording recites was compared "
        "against this corpus's own text for ``scope_key`` and matched.\n\n"
        "This is the field that separates a checked mapping from a plausible one. VedSearch "
        "numbers Rigvedic Mandala 8 in Griffith's order, so 55 hymns there map eleven hymns "
        "away from where a naive key-for-key rule would put them; a coordinate transform "
        "fixes it and this flag proves it was fixed. A record with "
        "``mapping_confidence=EXACT`` and ``text_verified=False`` is a contradiction and "
        "is refused.",
    )
    last_verified: str | None = Field(
        default=None, description="ISO-8601 date the availability field was last measured."
    )
    checksum: str | None = Field(
        default=None, description="SHA-256 of the cached bytes, where a copy is held."
    )
    notes: str | None = Field(default=None)

    @model_validator(mode="after")
    def _check_internal_consistency(self) -> AudioRecord:
        """Reject the records that would mislead rather than merely be incomplete.

        Each clause is a defect from Section 44 of the release spec, expressed as the
        condition that makes it impossible.
        """
        expected = VEDA_RECENSIONS.get(self.veda)
        if expected is None:
            raise ValueError(f"{self.audio_id}: unknown veda {self.veda!r}")
        if self.recension != expected:
            raise ValueError(
                f"{self.audio_id}: {self.veda} in this corpus is recension {expected!r}, "
                f"but this record claims {self.recension!r}. A cross-recension recording "
                f"may be catalogued as EXTERNAL_ONLY under its own Veda, never as this one."
            )

        # An EXACT or HIGH mapping asserts the source placed this file at this passage.
        # Without a key there is no passage, so the confidence is unsupportable.
        if self.mapping_confidence in (MappingConfidence.EXACT, MappingConfidence.HIGH):
            if self.scope_key is None:
                raise ValueError(
                    f"{self.audio_id}: {self.mapping_confidence} mapping names no scope_key."
                )
        if self.mapping_confidence is MappingConfidence.STRUCTURAL and self.scope_key is None:
            raise ValueError(f"{self.audio_id}: STRUCTURAL mapping names no scope_key.")

        # UNKNOWN scope cannot be pinned to a key: the pair asserts a position the source
        # did not state.
        if self.scope_type is AudioScope.UNKNOWN and self.scope_key is not None:
            raise ValueError(
                f"{self.audio_id}: scope_type UNKNOWN cannot carry scope_key "
                f"{self.scope_key!r} -- that pair claims a position the source did not state."
            )

        # A playable record must say what to play. This is the check that stops an
        # external link being dressed as hosted audio.
        if self.playback_mode is PlaybackMode.REMOTE_DIRECT and not self.media_url:
            raise ValueError(f"{self.audio_id}: REMOTE_DIRECT playback names no media_url.")
        if self.playback_mode is PlaybackMode.LOCAL_CACHE and not self.local_cache_path:
            raise ValueError(f"{self.audio_id}: LOCAL_CACHE playback names no local_cache_path.")
        if self.playback_mode is PlaybackMode.EXTERNAL_EMBED and not self.embed_url:
            raise ValueError(f"{self.audio_id}: EXTERNAL_EMBED playback names no embed_url.")
        if self.playback_mode is PlaybackMode.PROXIED_STREAM and not self.media_url:
            raise ValueError(f"{self.audio_id}: PROXIED_STREAM playback names no media_url.")

        # An EXACT mapping asserts the source placed this file at this passage's own
        # granularity. For this catalog that claim is only ever earned by comparing the
        # recited text, so the two fields cannot disagree.
        if self.mapping_confidence is MappingConfidence.EXACT and not self.text_verified:
            raise ValueError(
                f"{self.audio_id}: EXACT mapping without text_verified. An exact claim here "
                f"is earned by matching the recited text against this corpus, not asserted."
            )

        # The two-tier contract, in the only two clauses that can enforce it. A tier is a
        # claim about a person's ear, so RELEASED_VERIFIED must name where that hearing is
        # written down -- and SOURCE_MAPPED_UNREVIEWED must name none, because a row
        # carrying review evidence while declaring itself unreviewed is two statements
        # about the same fact and a reader would be entitled to believe either.
        if self.publication_tier is PublicationTier.RELEASED_VERIFIED:
            if not (self.audible_review_evidence or "").strip():
                raise ValueError(
                    f"{self.audio_id}: RELEASED_VERIFIED names no audible_review_evidence. "
                    f"That tier asserts a named person heard this recording; it is earned "
                    f"by citing the decision row, never by typing the value."
                )
        elif self.audible_review_evidence is not None:
            raise ValueError(
                f"{self.audio_id}: audible_review_evidence is set on a "
                f"{self.publication_tier.value} row. Evidence of a hearing and a tier that "
                f"denies one cannot both stand."
            )

        if self.local_cache_path and self.local_cache_path.startswith(("/", "\\")):
            raise ValueError(f"{self.audio_id}: local_cache_path must be relative.")
        if self.local_cache_path and ".." in self.local_cache_path.split("/"):
            raise ValueError(f"{self.audio_id}: local_cache_path must not traverse upward.")

        if (
            self.start_seconds is not None
            and self.end_seconds is not None
            and self.end_seconds <= self.start_seconds
        ):
            raise ValueError(f"{self.audio_id}: end_seconds must exceed start_seconds.")

        return self
