"""Bridge the Atharvavedic ascription layer to canonical Devatā identity, by morphology.

GAP-CROSS-VEDA-DEVATA-IDENTITY-BRIDGE-001, GAP-ATTRIBUTION-002.

**The defect.** ``HAS_DEVATA`` points at a ``:Devata`` whose display label is an English
deity name; ``HAS_DEVATA_ASCRIPTION`` points at a ``:DevataAscription`` whose display label
is a Sanskrit adjective. 210 labels against 324, sharing **0**. The zero is a category
difference and not a coverage accident, so a join on display labels returns nothing and
reports it as an absence of shared deities.

**Why this is not a string join.** The owner's ruling forbids joining the layers on display
label and forbids guessing. What licenses a resolution here is a *grammatical derivation*,
not a resemblance: ``āgneyam`` is the taddhita of ``agni`` under Pāṇini 4.2.24 ``sāsya
devatā`` -- "X is its deity" -- formed by vṛddhi of the first syllable plus a secondary
suffix. The adjective's own morphology states the dedication. The identity claim's
independent basis is that derivation; the folded comparison only *checks* the result, which
is the division OWNER_DECISIONS section 2 and section 11 require.

So a resolution here is a ``DERIVED`` claim with a stated method, never a
``SAME_CANONICAL_ENTITY`` assertion inferred from spelling.

**Two derivation paths, both deterministic.**

``DEITY_ADJECTIVE_SUFFIX``
    The explicit formations -- ``-devatyam``, ``-daivatam``, ``-devatākam`` and the
    transcription variants the printed source spells them with. Strip the suffix, match the
    stem. This is the path the Wave 3 probe implemented; it reaches 8 of 324.
``VRDDHI_TADDHITA``
    The implicit formation, which is the majority: ``vāruṇam`` < ``varuṇa``, ``bārhaspatyam``
    < ``bṛhaspati``, ``sāumyam`` < ``soma``, ``cāndramasam`` < ``candramas``. De-vṛddhi the
    first syllable, strip the secondary suffix, restore the stem final, match. This path is
    what the probe did not have, and it is where the other 165 unresolved labels live.

**Ambiguity is refused, not broken.** A candidate that matches two or more distinct
``:Devata`` resolves to neither. That is not a formality: the length-insensitive comparison
tier collides on exactly five clusters in this registry -- ``aśva``, ``dadhikrā``, ``go``,
``pavamāna`` and ``viśve deva`` -- and one of them is ``VG:DEVATA:PAVAMANAH`` against
``VG:DEVATA:PAVAMANAH-SOMAH``, whose separation is a settled owner decision. Refusing the
ambiguous case is what keeps this resolver from quietly re-merging them.

**The fold is proved, not assumed.** :func:`length_collisions` enumerates every collision
the length-insensitive tier introduces over the live registry, so the cost of the looser
comparison is a measured list rather than a hope. Over-normalising and under-normalising
both look like a clean run; only the collision list tells them apart.

**Four refusals, taken before any parse.** Straight from the owner's ``must_not_do``:
a compound naming two ascriptions is not resolved to one deity; a plurality such as
``bahudevatyam`` is not resolved at all; a subject descriptor such as ``bhāiṣajyam`` is not
a deity; and ``liṅgoktadevatyam`` -- "the deity indicated by the wording" -- is the
Anukramaṇī's own deferral marker and resolves to a null, not to a god.
"""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass

CONTRACT_VERSION: Final = "VG:ASCRIPTION_BRIDGE:V1"

#: Whitney's transliteration against the registry's IAST. Each mapping is one-to-one in the
#: source and carries no ambiguity: Whitney writes palatal s as ``ç`` always, velar n as
#: ``n̄``, anusvara as ``ṁ``. This is transcription-system equivalence, NOT accent folding:
#: ``ś`` is never folded to ``s``, because the IAST acute is both a palatal and an udatta
#: and collapsing it is how a fold silently inverts an identity.
WHITNEY_TO_IAST: Final[dict[str, str]] = {
    "ç": "ś",
    "n̄": "ṅ",
    "ṁ": "ṃ",
    # Whitney prints an editorial quotation mark where the printed text elides a vowel
    # (`utāi ”ndram`). It is punctuation in the apparatus, not a phoneme, and it is
    # dropped rather than folded. RUF001 flags these as ambiguous, which is exactly what
    # they are -- that is why they are here and named.
    "”": "",
    "’": "",  # noqa: RUF001
    "‘": "",  # noqa: RUF001
}

_VOWELS: Final[frozenset[str]] = frozenset("aāiīuūṛṝḷeo")

#: Vowel length only. Applied as a SECOND tier and only when the exact tier found nothing.
_LENGTH: Final[dict[str, str]] = {"ā": "a", "ī": "i", "ū": "u", "ṝ": "ṛ"}

#: Vṛddhi of the first syllable, written as (strengthened, underlying). Both readings of a
#: diphthong are generated because vṛddhi of ``i`` and of ``e`` are the same surface, and
#: the registry decides which one exists.
VRDDHI_REVERSALS: Final[tuple[tuple[str, str], ...]] = (
    ("āi", "i"),
    ("āi", "e"),
    ("ai", "i"),
    ("ai", "e"),
    ("āu", "u"),
    ("āu", "o"),
    ("au", "u"),
    ("au", "o"),
    ("ār", "ṛ"),
    ("ā", "a"),
)

#: Secondary (taddhita) suffixes of the ``sāsya devatā`` formation.
TADDHITA_SUFFIXES: Final[tuple[str, ...]] = ("", "a", "ya", "eya", "īya", "ka", "ā")

#: Nominal stem finals restored after the suffix is stripped.
STEM_FINALS: Final[tuple[str, ...]] = (
    "",
    "a",
    "i",
    "ī",
    "u",
    "ū",
    "ṛ",
    "an",
    "as",
    "at",
    "in",
    "ā",
    "au",
)

#: Explicit "-having X as deity" suffixes, longest first so a longer formation is never
#: truncated by a shorter one inside it. Read off the 324 stored labels, not off a grammar,
#: because the source is a printed transcription that spells one formation several ways.
DEITY_ADJECTIVE_SUFFIXES: Final[tuple[str, ...]] = (
    "devatakam",
    "devatyam",
    "daivatyam",
    "daivatam",
    "ddivatam",
    "devatya",
    "devata",
    "daivata",
)

#: A conjunction inside the label: two ascriptions, so one target is wrong by construction.
CONJUNCTION: Final = re.compile(
    r"\s+ut[aā]i?\s*[”’‘]*\s*|\s+ca\s+|\s+ca$"  # noqa: RUF001 - the printed apparatus's own marks
)

#: Heads that are the hymn's SUBJECT, which Whitney's apparatus prints in the deity slot.
NON_DEITY_HEADS: Final[tuple[str, ...]] = (
    "bhaisajyam",
    "bhāiṣajyam",
    "ayusyam",
    "āyuṣyam",
    "suktam",
    "sūktam",
    "mantroktam",
)

#: "of many deities" / "of various deities" -- a plurality, not a deity.
PLURALITY_HEADS: Final[tuple[str, ...]] = ("bahu", "nānā", "nana")

#: The Anukramani's own deferral marker: "the deity stated by the mark in the mantra".
DEFERRAL_HEADS: Final[tuple[str, ...]] = ("liṅgokta", "lingokta")

#: The closed vocabulary of ``ascription_resolution_status``.
RESOLUTION_STATUSES: Final[frozenset[str]] = frozenset(
    {
        "RESOLVED_TO_CANONICAL_DEVATA",
        "UNRESOLVED_COMPOUND_TWO_ASCRIPTIONS",
        "UNRESOLVED_NAMES_A_PLURALITY",
        "UNRESOLVED_SUBJECT_DESCRIPTOR_NOT_A_DEITY",
        "UNRESOLVED_SOURCE_DEFERS_TO_THE_MANTRA",
        "UNRESOLVED_AMBIGUOUS_TWO_OR_MORE_DEVATAS",
        "UNRESOLVED_STEM_MATCHES_NO_CANONICAL_DEVATA",
    }
)


def fold(text: str) -> str:
    """Whitney's transcription onto the registry's IAST. Case and visarga only besides.

    The final visarga is dropped because it is a sandhi ending and carries no stem
    information; ``agniḥ`` and ``agni`` are the same stem, and the registry stores both.
    Nothing else is normalised away.
    """
    value = (text or "").strip().lower()
    for source, target in WHITNEY_TO_IAST.items():
        value = value.replace(source, target)
    return value.replace("ḥ", "")


def shorten(text: str) -> str:
    """Vowel length folded out. Second tier only; :func:`length_collisions` prices it."""
    for long_vowel, short_vowel in _LENGTH.items():
        text = text.replace(long_vowel, short_vowel)
    return text


def devrddhi(word: str) -> list[tuple[str, str]]:
    """Every underlying first syllable this surface could be the vṛddhi of.

    Vṛddhi falls on the first VOWEL, which may sit behind a consonant onset --
    ``v-ā-ruṇa``, not ``ā-...`` -- so the onset is preserved and the reversal applied to
    the vowel. Getting this wrong is not a small error: an onset-blind version of this
    function resolved 4 ascriptions instead of 19.
    """
    index = 0
    while index < len(word) and word[index] not in _VOWELS:
        index += 1
    onset, rest = word[:index], word[index:]
    return [
        (onset + short + rest[len(long) :], f"{long}->{short}")
        for long, short in VRDDHI_REVERSALS
        if rest.startswith(long)
    ]


@dataclass(frozen=True)
class Candidate:
    """One underlying stem this ascription could be derived from, and how."""

    stem: str
    path: str
    vrddhi_rule: str = ""
    taddhita_suffix: str = ""
    stem_final: str = ""


def suffix_candidates(folded: str) -> list[Candidate]:
    """The explicit ``-devatyam`` family."""
    for suffix in DEITY_ADJECTIVE_SUFFIXES:
        folded_suffix = fold(suffix)
        if folded.endswith(folded_suffix) and len(folded) > len(folded_suffix):
            return [
                Candidate(
                    stem=folded[: -len(folded_suffix)],
                    path="DEITY_ADJECTIVE_SUFFIX",
                    taddhita_suffix=suffix,
                )
            ]
    return []


def vrddhi_candidates(folded: str) -> list[Candidate]:
    """The implicit ``sāsya devatā`` taddhita, de-derived."""
    if not folded.endswith("m"):
        return []
    out: list[Candidate] = []
    for derived, rule in devrddhi(folded):
        body = derived[:-1]
        for suffix in TADDHITA_SUFFIXES:
            if suffix and not body.endswith(suffix):
                continue
            core = body[: len(body) - len(suffix)] if suffix else body
            if not core:
                continue
            cores = [core]
            # An r-stem taddhita: savitṛ -> sāvitra, so the stripped core ends in a plain
            # r where the stem has the vocalic ṛ.
            if core.endswith("r"):
                cores.append(core[:-1] + "ṛ")
            for variant in cores:
                for final in STEM_FINALS:
                    out.append(
                        Candidate(
                            stem=variant + final,
                            path="VRDDHI_TADDHITA",
                            vrddhi_rule=rule,
                            taddhita_suffix=suffix,
                            stem_final=final,
                        )
                    )
    return out


@dataclass
class SurfaceIndex:
    """Every folded surface a canonical ``:Devata`` answers to, at two tiers."""

    exact: dict[str, set[str]] = field(default_factory=lambda: collections.defaultdict(set))
    length_insensitive: dict[str, set[str]] = field(
        default_factory=lambda: collections.defaultdict(set)
    )

    @classmethod
    def build(cls, devatas: list[dict[str, Any]]) -> SurfaceIndex:
        index = cls()
        for row in devatas:
            surfaces = [row.get("label_iast"), row.get("preferred_label")]
            surfaces.extend(row.get("aliases_iast") or [])
            for value in surfaces:
                folded = fold(str(value or ""))
                if not folded:
                    continue
                index.exact[folded].add(str(row["entity_key"]))
                index.length_insensitive[shorten(folded)].add(str(row["entity_key"]))
        return index

    def length_collisions(self) -> dict[str, list[str]]:
        """What the looser tier costs, enumerated rather than assumed."""
        return {
            surface: sorted(keys)
            for surface, keys in sorted(self.length_insensitive.items())
            if len(keys) > 1
        }


def length_collisions(devatas: list[dict[str, Any]]) -> dict[str, list[str]]:
    return SurfaceIndex.build(devatas).length_collisions()


@dataclass(frozen=True)
class Resolution:
    """One ascription's verdict, with the evidence that produced it."""

    ascription_key: str
    label: str
    occurrences: int
    status: str
    devata_key: str | None = None
    derivation_path: str | None = None
    stem: str | None = None
    vrddhi_rule: str | None = None
    taddhita_suffix: str | None = None
    stem_final: str | None = None
    comparison_tier: str | None = None
    candidates_matched: tuple[str, ...] = ()
    reason: str = ""


def _refusal(folded: str) -> tuple[str, str] | None:
    if any(folded.startswith(fold(head)) for head in DEFERRAL_HEADS):
        return (
            "UNRESOLVED_SOURCE_DEFERS_TO_THE_MANTRA",
            "lingokta: the Anukramani declines to name the deity and defers to the mark in "
            "the mantra. Resolving it would be reading the mantra and judging, not parsing "
            "the index.",
        )
    if any(folded.startswith(fold(head)) for head in PLURALITY_HEADS):
        return (
            "UNRESOLVED_NAMES_A_PLURALITY",
            "The label names a plurality of deities, not one deity. Resolving it to a "
            "single Devata would assert something the source does not.",
        )
    if any(folded.startswith(fold(head)) for head in NON_DEITY_HEADS):
        return (
            "UNRESOLVED_SUBJECT_DESCRIPTOR_NOT_A_DEITY",
            "Whitney's apparatus prints the hymn's SUBJECT in the deity slot. This label is "
            "a subject, so there is no deity to resolve it to.",
        )
    return None


def resolve_one(
    ascription: dict[str, Any], index: SurfaceIndex, *, allow_length_tier: bool = True
) -> Resolution:
    key = str(ascription["entity_key"])
    label = str(ascription.get("label_iast") or "")
    occurrences = int(ascription.get("occurrence_count") or 0)
    folded = fold(label)

    if CONJUNCTION.search(label):
        return Resolution(
            ascription_key=key,
            label=label,
            occurrences=occurrences,
            status="UNRESOLVED_COMPOUND_TWO_ASCRIPTIONS",
            reason=(
                "The label joins two ascriptions with uta/ca. One target would be wrong by "
                "construction; the compound is retained in its ascription form."
            ),
        )
    refusal = _refusal(folded)
    if refusal is not None:
        status, reason = refusal
        return Resolution(
            ascription_key=key,
            label=label,
            occurrences=occurrences,
            status=status,
            reason=reason,
        )

    candidates = suffix_candidates(folded) or vrddhi_candidates(folded)
    for tier, surfaces in (
        ("EXACT", index.exact),
        ("LENGTH_INSENSITIVE", index.length_insensitive if allow_length_tier else {}),
    ):
        hits: dict[str, Candidate] = {}
        for candidate in candidates:
            probe = candidate.stem if tier == "EXACT" else shorten(candidate.stem)
            for devata_key in surfaces.get(probe, set()):
                hits.setdefault(devata_key, candidate)
        if len(hits) == 1:
            devata_key, candidate = next(iter(hits.items()))
            return Resolution(
                ascription_key=key,
                label=label,
                occurrences=occurrences,
                status="RESOLVED_TO_CANONICAL_DEVATA",
                devata_key=devata_key,
                derivation_path=candidate.path,
                stem=candidate.stem,
                vrddhi_rule=candidate.vrddhi_rule or None,
                taddhita_suffix=candidate.taddhita_suffix or None,
                stem_final=candidate.stem_final or None,
                comparison_tier=tier,
                candidates_matched=(candidate.stem,),
                reason=(
                    f"Taddhita of the sasya-devata type: {label} derives from {candidate.stem} "
                    f"by {candidate.path.lower()}, matched at the {tier.lower()} tier."
                ),
            )
        if len(hits) > 1:
            return Resolution(
                ascription_key=key,
                label=label,
                occurrences=occurrences,
                status="UNRESOLVED_AMBIGUOUS_TWO_OR_MORE_DEVATAS",
                comparison_tier=tier,
                candidates_matched=tuple(sorted(hits)),
                reason=(
                    "The stem matches more than one canonical Devata. Picking the more "
                    "frequent one is what the owner decision forbids."
                ),
            )
    return Resolution(
        ascription_key=key,
        label=label,
        occurrences=occurrences,
        status="UNRESOLVED_STEM_MATCHES_NO_CANONICAL_DEVATA",
        reason=(
            "No recognised derivation reaches a canonical Devata surface. The ascription "
            "keeps its own form and stays addressable as an ascription."
        ),
    )


ASCRIPTION_QUERY: Final = (
    "MATCH (n:DevataAscription) RETURN n.entity_key AS entity_key, "
    "n.label_iast AS label_iast, n.occurrence_count AS occurrence_count ORDER BY entity_key"
)
DEVATA_QUERY: Final = (
    "MATCH (d:Devata) RETURN d.entity_key AS entity_key, d.label_iast AS label_iast, "
    "d.preferred_label AS preferred_label, d.aliases_iast AS aliases_iast ORDER BY entity_key"
)


def resolve_all(
    ascriptions: list[dict[str, Any]], devatas: list[dict[str, Any]]
) -> list[Resolution]:
    index = SurfaceIndex.build(devatas)
    return [resolve_one(row, index) for row in ascriptions]


def summarise(resolutions: list[Resolution]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    occ_by_status: dict[str, int] = {}
    for item in resolutions:
        by_status[item.status] = by_status.get(item.status, 0) + 1
        occ_by_status[item.status] = occ_by_status.get(item.status, 0) + item.occurrences
    resolved = [r for r in resolutions if r.status == "RESOLVED_TO_CANONICAL_DEVATA"]
    total_occ = sum(r.occurrences for r in resolutions)
    return {
        "ascriptions": len(resolutions),
        "resolved": len(resolved),
        "resolved_share": round(len(resolved) / len(resolutions), 4) if resolutions else None,
        "distinct_devatas_reached": len({r.devata_key for r in resolved}),
        "occurrences_total": total_occ,
        "occurrences_resolved": sum(r.occurrences for r in resolved),
        "occurrence_share_resolved": (
            round(sum(r.occurrences for r in resolved) / total_occ, 4) if total_occ else None
        ),
        "by_status": dict(sorted(by_status.items())),
        "occurrences_by_status": dict(sorted(occ_by_status.items())),
        "by_derivation_path": dict(
            sorted(collections.Counter(r.derivation_path for r in resolved).items())
        ),
        "by_comparison_tier": dict(
            sorted(collections.Counter(r.comparison_tier for r in resolved).items())
        ),
    }


def check_resolutions(resolutions: list[Resolution]) -> dict[str, Any]:
    """The bridge's own gate.

    ``every_status_in_vocabulary``
        an unresolved ascription must carry a typed reason from the closed enum, which is
        the closure test's "the unresolvable descriptors carry an explicit reason".
    ``every_unresolved_has_a_reason``
        a status without prose is a refusal a reader cannot check.
    ``no_display_label_join``
        no resolution may be produced without a stated derivation path.
    ``soma_and_pavamana_not_merged``
        the settled owner decision, asserted rather than trusted: nothing may resolve to
        ``VG:DEVATA:PAVAMANAH-SOMAH`` by collapsing it into Soma or the reverse.
    """
    bad_status = [r.ascription_key for r in resolutions if r.status not in RESOLUTION_STATUSES]
    unreasoned = [r.ascription_key for r in resolutions if not r.reason]
    pathless = [
        r.ascription_key
        for r in resolutions
        if r.status == "RESOLVED_TO_CANONICAL_DEVATA" and not r.derivation_path
    ]
    soma_keys = {"VG:DEVATA:SOMAH", "VG:DEVATA:PAVAMANAH", "VG:DEVATA:PAVAMANAH-SOMAH"}
    ambiguous_soma = [
        r.ascription_key
        for r in resolutions
        if r.status == "RESOLVED_TO_CANONICAL_DEVATA"
        and r.devata_key in soma_keys
        and len(set(r.candidates_matched)) > 1
    ]
    return {
        "every_status_in_vocabulary": not bad_status,
        "statuses_outside_vocabulary": bad_status[:20],
        "every_unresolved_has_a_reason": not unreasoned,
        "rows_without_a_reason": unreasoned[:20],
        "no_display_label_join": not pathless,
        "resolutions_without_a_derivation_path": pathless[:20],
        "soma_and_pavamana_not_merged": not ambiguous_soma,
        "passes": not (bad_status or unreasoned or pathless or ambiguous_soma),
    }


# ---------------------------------------------------------------------------
# The property contract for the edges this bridge produces
# ---------------------------------------------------------------------------
#
# **The defect this section exists to remove, which was mine.** The first version of this
# bridge invented three property values and wrote them into slots that already have closed
# vocabularies:
#
#     evidence_basis        = DERIVED_FROM_ANUKRAMANI_ASCRIPTION_MORPHOLOGY
#     evidence_basis        = DERIVED_FROM_TADDHITA_MORPHOLOGY
#     attribution_precision = SOURCE_EXPLICIT_ASCRIPTION_RESOLVED
#
# All three resolve to ``UNKNOWN`` through ``EvidenceSurface`` and
# ``basis_from_attribution_precision``, so the product would have published UNKNOWN as the
# evidence basis for 921 edges. That is the same shape as the defect
# :class:`~vedagraph.api.models.common.EvidenceBasis` documents in its own warning, where
# reading the graph property straight into the enum reported all 44,778 attribution edges
# as UNKNOWN.
#
# The root error was not a missing mapping. It was writing a DERIVATION into a SURFACE slot
# and a RESOLUTION QUALITY into a SCOPE slot. Two axes, one property each, and neither slot
# was this module's to redefine.
#
# **The measured scope.** All 882 Atharvavedic dedications derive from ascription edges
# carrying ``attribution_precision = CONTAINER_INHERITED`` and ``scope_origin = SUKTA_WIDE``;
# ``scope_container_key`` equals the mantra's ``parent_key`` on 882 of 882 and the verse's
# own key on 0. Independently: all 505 Atharvavedic suktas that carry an ascription carry
# the IDENTICAL ascription set on every one of their verses, so no verse in the corpus is
# ascribed differently from its sukta. The Anukramani states a deity for the hymn, and
# there is no verse-level Atharvavedic devata ascription anywhere to inherit a stronger
# precision from.
#
# So a derived dedication is CONTAINER_INHERITED and must say so, even though the
# resolution step that produced it is exact. The precision of the resolution and the scope
# of the assertion are different questions, and answering the second with the first is how
# a hymn-wide claim starts reading as a per-verse one.
#
# **The resolution axis keeps its own properties** -- ``ascription_resolution_*`` -- so a
# reader sees "the scope is container-wide" and "the resolution was an exact stem match" as
# two facts rather than one blended grade. They are namespaced so they cannot be mistaken
# for the product vocabulary.

#: Read off the parent ``HAS_DEVATA_ASCRIPTION`` edge rather than chosen: a derived
#: dedication cannot rest on a better surface than the ascription it came from, and that
#: surface is the Anukramani apparatus, not the Samhita text.
INHERITED_EVIDENCE_SURFACE: Final = "SOURCE_METADATA"

#: Measured, not assumed. 882 of 882.
INHERITED_ATTRIBUTION_PRECISION: Final = "CONTAINER_INHERITED"

#: The closed vocabularies these edges must stay inside. Held as literals on purpose:
#: importing the API package into the domain layer would invert the dependency, and
#: ``tests/domain/test_ascription_bridge.py`` asserts these agree with the enums.
PRODUCT_EVIDENCE_SURFACES: Final[frozenset[str]] = frozenset(
    {
        "SANSKRIT",
        "STRUCTURAL",
        "SOURCE_METADATA",
        "MIXED",
        "TRANSLATION",
        "SHARED_REGISTRY_ENTITIES",
        "UNKNOWN",
    }
)
PRODUCT_ATTRIBUTION_PRECISIONS: Final[frozenset[str]] = frozenset(
    {
        "PER_PASSAGE",
        "CONTAINER_INHERITED",
        "TEXTUAL_MENTION",
        "NOT_AN_ATTRIBUTION",
        "UNKNOWN",
    }
)


class UnmappedPropertyValue(ValueError):
    """A property value outside the product's closed vocabulary. Raised, never written.

    The API degrades an unknown value to ``UNKNOWN`` so that one odd property cannot fail a
    request. That is right for a read and wrong for a write: a generator emitting an
    unmapped value has created the odd property, and it should stop rather than ship
    hundreds of edges the product cannot describe.
    """


def edge_properties(resolution: Resolution) -> dict[str, Any]:
    """Properties for one ``ASCRIBES_TO_DEVATA`` edge.

    ``attribution_precision`` is ``NOT_AN_ATTRIBUTION`` because this edge is not one: it
    joins a descriptor to the deity it is morphologically derived from. The attribution
    lives on the passage edge, which is where the scope question belongs.
    """
    return {
        "evidence_basis": INHERITED_EVIDENCE_SURFACE,
        "attribution_precision": "NOT_AN_ATTRIBUTION",
        "quality_tier": "TIER_B",
        "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
        "confidence": 1.0,
        "ascription_resolution_method": "TADDHITA_SASYA_DEVATA_DERIVATION",
        "ascription_resolution_path": resolution.derivation_path,
        "ascription_resolution_stem": resolution.stem,
        "ascription_resolution_comparison_tier": resolution.comparison_tier,
        "ascription_bridge_version": CONTRACT_VERSION,
    }


def dedication_properties(resolution: Resolution, ascription_key: str) -> dict[str, Any]:
    """Properties for one derived ``HAS_DEVATA_DERIVED`` dedication edge.

    ``attribution_precision`` is ``CONTAINER_INHERITED`` because the source states the deity
    of the sukta. The exactness of the resolution lives on ``ascription_resolution_*`` and
    does not upgrade the scope.
    """
    return {
        "evidence_basis": INHERITED_EVIDENCE_SURFACE,
        "attribution_precision": INHERITED_ATTRIBUTION_PRECISION,
        "scope_origin": "SUKTA_WIDE",
        "quality_tier": "TIER_B",
        "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
        "confidence": 1.0,
        "via_ascription": ascription_key,
        "ascription_resolution_method": "TADDHITA_SASYA_DEVATA_DERIVATION",
        "ascription_resolution_path": resolution.derivation_path,
        "ascription_resolution_comparison_tier": resolution.comparison_tier,
        "ascription_bridge_version": CONTRACT_VERSION,
    }


def check_property_vocabulary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Every emitted value must already be a member of the product's closed vocabulary.

    Raises rather than reports, because the alternative is hundreds of edges the product
    describes as UNKNOWN and a guard that goes red after the import instead of before it.
    """
    bad_surface = sorted(
        {
            str(row.get("evidence_basis"))
            for row in rows
            if str(row.get("evidence_basis")) not in PRODUCT_EVIDENCE_SURFACES
        }
    )
    bad_precision = sorted(
        {
            str(row.get("attribution_precision"))
            for row in rows
            if str(row.get("attribution_precision")) not in PRODUCT_ATTRIBUTION_PRECISIONS
        }
    )
    if bad_surface or bad_precision:
        raise UnmappedPropertyValue(
            f"evidence_basis values outside EvidenceSurface: {bad_surface}; "
            f"attribution_precision outside AttributionPrecision: {bad_precision}. "
            "Map the value or stop emitting it. Do not widen the enum to accept a "
            "derivation written into a surface slot."
        )
    return {
        "rows": len(rows),
        "evidence_surfaces": sorted({str(row["evidence_basis"]) for row in rows}),
        "attribution_precisions": sorted({str(row["attribution_precision"]) for row in rows}),
        "passes": True,
    }
