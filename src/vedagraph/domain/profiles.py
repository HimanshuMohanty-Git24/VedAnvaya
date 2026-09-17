"""Corpus-derived profiles for deities, and the metrics an interpretation may cite.

A profile here is arithmetic over edges that already exist. Nothing is read, inferred or
characterised: "Indra is attributed to 2,869 Rigvedic mantras, 8,329 of the corpus's
deity attributions arrive by sūkta inheritance, and his most frequent co-attributed deity
is X" are all counts. That restraint is the point. The spec this implements is explicit
that evolution must be *computed, not asserted* -- there is to be no
``Indra -[:DECLINED_IN]-> LaterVeda`` edge -- so what this module produces is the
measurement, and :mod:`vedagraph.domain.claims` is the only place allowed to say what a
measurement might mean.

**The coverage limit is part of the profile, not a footnote to it.** The ``HAS_DEVATA``
layer -- attribution to a deity in the registry -- is Rigveda-only: 10,552 of 10,552
Rigvedic mantras carry one and no mantra of any other corpus does. So a profile that
reported "Indra: RV 2869, SV 0, YV 0, AV 0" would be read as *Indra is absent from the
other three Vedas*, which is false and is the single most misleading sentence this layer
could produce.

**This is NOT the same as "the Anukramaṇī is Rigveda-only", and that wider sentence is
false.** Measured: 4,160 Atharvavedic mantras carry 4,816 ``HAS_DEVATA_ASCRIPTION`` edges
read off Whitney's Anukramaṇī brackets, and 106 of them are dedications to Indra
(``āindram`` and its variants). Those ascriptions are *descriptors* -- adjectival phrases
like ``āgneyam`` -- and are not resolved into the deity registry, which is why they are a
separate predicate and are not counted here. The distinction to keep is between a layer
that does not exist for a corpus and a layer that exists in a form this one cannot join
to; only the first is a coverage limit. Every profile therefore carries
:attr:`DevataProfile.attribution_scope` naming the Vedas the attribution layer covers, and
cross-Veda presence is reported separately and only from the mention layer, which does
span four Vedas.

**Two counts, because there are two questions.** ``attributed_mantras`` counts every
``HAS_DEVATA`` edge; ``attributed_per_passage`` counts only those the source states of that
mantra rather than of its sūkta. For Indra the two differ by a factor that matters, and a
profile showing only the first is overstating what the Anukramaṇī said.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

from vedagraph.domain.ontology import (
    DOMAIN_MODEL_VERSION,
    LABEL_DERIVED_METRIC,
    AttributionPrecision,
)
from vedagraph.domain.theonyms import (
    AMBIGUOUS,
    CERTAIN,
    DEFAULT_REFERENT_TIERS,
    PROBABLE,
    mention_verdict,
)

#: Vedas whose mantras carry a ``HAS_DEVATA`` edge to a resolved deity. Measured, not
#: assumed: see the module docstring for the counts.
#:
#: Deliberately NOT "Vedas with an Anukramaṇī", which this constant used to claim and which
#: is false: the Atharvaveda has one, and 4,160 of its mantras carry ascription descriptors
#: from it. Those descriptors are a different predicate with a different value space and
#: are not resolved into the deity registry, so they are out of scope for this constant and
#: in scope for any sentence about what the corpus records.
#:
#: .. warning::
#:
#:    **Do not widen this to ``("RV", "AV")``.** That change has been proposed as the
#:    follow-on to the Atharvavedic derived-dedication import, and it would be wrong,
#:    because it collapses three predicates that this build deliberately keeps apart:
#:
#:    ``HAS_DEVATA``            attribution resolved to a registry deity. Rigveda-only, and
#:                              the import does not add one of these.
#:    ``HAS_DEVATA_DERIVED``    resolved from an Anukramaṇī descriptor by morphology. The
#:                              import creates these for the Atharvaveda.
#:    ``HAS_DEVATA_ASCRIPTION`` the raw descriptor, unresolved. Atharvavedic, and never
#:                              counted as an attribution to a named deity.
#:
#:    Widening the constant makes "HAS_DEVATA reaches AV" true in prose while the predicate
#:    itself still has no Atharvavedic edge, which is the same defect in the other
#:    direction. Nothing in this module should read a corpus list out of a constant at all
#:    any more: see :func:`measure_attribution_scope`, which measures the reach of every
#:    member of the family and is what the published sentences interpolate.
ATTRIBUTION_VEDAS: tuple[str, ...] = ("RV",)

#: The deity-attribution predicate family, with what each member asserts. Enumerated rather
#: than discovered, because a predicate with no edges must still be reported -- a family
#: discovered from the data cannot distinguish "this predicate reaches no corpus" from
#: "this predicate was never built", and those are the two things the scope note exists to
#: keep apart. Order is from strongest claim to weakest.
ATTRIBUTION_PREDICATES: tuple[tuple[str, str], ...] = (
    (
        "HAS_DEVATA",
        "attribution resolved to a deity in the registry, as the source states it",
    ),
    (
        "HAS_DEVATA_DERIVED",
        "attribution resolved from an Anukramani descriptor by morphology, so the "
        "resolution is this project's and the dedication is the source's",
    ),
    (
        "HAS_DEVATA_ASCRIPTION",
        "the raw Anukramani descriptor, never resolved to a registry deity and never "
        "counted as an attribution to a named god",
    ),
)

#: The predicates ``DEVATA_ATTRIBUTION_BY_VEDA`` actually counts. One name, in one place,
#: read by the metric's ``values``, its ``method`` string and its ``scope_note`` alike, so a
#: build that widens what it counts cannot leave the method or the note describing the
#: narrower set. That divergence -- figure right, sentence wrong -- is the failure this
#: whole module has now produced twice.
COUNTED_ATTRIBUTION_PREDICATES: tuple[str, ...] = ("HAS_DEVATA",)

#: All four, for the layers that do span the corpus.
ALL_VEDAS: tuple[str, ...] = ("RV", "SV", "YV", "AV")

#: The mention tiers a profile counts as *findings* rather than as candidates. Imported
#: from the layer that defines them so the profile cannot drift from the product default:
#: a profile that counted a wider set than the default query returns would describe a
#: deity the product never shows.
PROFILE_MENTION_TIERS: frozenset[str] = DEFAULT_REFERENT_TIERS

#: How many entries a top-N list keeps. Small on purpose: these are denormalised onto the
#: node for display, and a display property holding fifty items is a second copy of the
#: graph that will drift from it.
TOP_N: int = 10


class Session(Protocol):
    def run(self, query: str, /, **kwargs: Any) -> Any: ...


@dataclass
class DevataProfile:
    """Everything counted about one deity, with the scope of each count attached."""

    entity_key: str
    display_label: str
    #: Every HAS_DEVATA edge, by Veda. Only ``ATTRIBUTION_VEDAS`` can be non-zero.
    attributed_mantras: dict[str, int] = field(default_factory=dict)
    #: ``{predicate: [veda, ...]}`` for the whole attribution family, measured when this
    #: profile was computed. Empty means it was not measured, and the metrics built from
    #: this profile then say so rather than declaring a scope they did not check.
    attribution_layer_scope: dict[str, list[str]] = field(default_factory=dict)
    #: The subset the source states of the mantra itself, not of its enclosing sūkta.
    attributed_per_passage: int = 0
    attributed_inherited: int = 0
    #: Textual mentions by Veda, at every referent-certainty tier. Spans four Vedas.
    mentions: dict[str, int] = field(default_factory=dict)
    #: The same mentions split three ways, keyed Veda -> count, one dict per tier. Kept as
    #: three separate figures rather than one total plus a confidence score, because the
    #: requirement on every deity answer is that it can *report* its ambiguity instead of
    #: absorbing it: 51.4% of this layer was ``DEITY_AMBIGUOUS`` before the split and a
    #: single mention count would still be quietly carrying most of that.
    mentions_certain: dict[str, int] = field(default_factory=dict)
    mentions_probable: dict[str, int] = field(default_factory=dict)
    mentions_ambiguous: dict[str, int] = field(default_factory=dict)
    #: Structural spread, e.g. {"1": 300, "2": 40, ...} by maṇḍala.
    by_division: dict[str, int] = field(default_factory=dict)
    top_rishis: list[tuple[str, int]] = field(default_factory=list)
    top_chandas: list[tuple[str, int]] = field(default_factory=list)
    top_concepts: list[tuple[str, int]] = field(default_factory=list)
    #: The same ranking computed over ``attribution_precision = PER_PASSAGE`` edges only.
    #: Stored **beside** the inherited-inclusive ranking rather than instead of it, because
    #: a single stored ranking whose precision basis is not in its name is a trap: for
    #: Varuṇa, ranks 2-8 change completely between the two, and `pāśa` -- the noose, his
    #: defining instrument -- is rank 2 strictly and absent from the inherited list.
    #: Materialising only one of them takes away the reader's ability to recompute.
    top_concepts_strict: list[tuple[str, int]] = field(default_factory=list)
    co_devatas: list[tuple[str, int]] = field(default_factory=list)
    formula_count: int = 0
    #: Actions the agentive layer records this deity as *performing*, and separately the
    #: ones it is *asked* to perform. The two are never merged: "Indra slays Vrtra" and
    #: "slay Vrtra, Indra" are a statement and a request, and the frame distinction is the
    #: agentive layer's whole point.
    top_actions: list[tuple[str, int]] = field(default_factory=list)
    top_requested_actions: list[tuple[str, int]] = field(default_factory=list)
    #: Objects and substances, counted over the passages that *mention* the deity rather
    #: than over the Rigveda-only attribution layer, so this dimension spans four Vedas.
    top_objects: list[tuple[str, int]] = field(default_factory=list)
    #: Co-mentioned deities from the four-Veda mention layer, as against
    #: :attr:`co_devatas`, which is co-*attribution* and therefore Rigveda-only. A profile
    #: that offered only the second would show Agni with no companions outside the Rigveda.
    co_mentioned: list[tuple[str, int]] = field(default_factory=list)

    @property
    def attribution_scope(self) -> tuple[str, ...]:
        """Vedas whose attribution layer this profile could have drawn on.

        Read this before reading a zero. A zero for the Atharvaveda means the Atharvaveda
        has no attribution layer, not that the deity is absent from it.
        """
        return ATTRIBUTION_VEDAS

    @property
    def total_attributed(self) -> int:
        return sum(self.attributed_mantras.values())

    @property
    def mention_scope(self) -> tuple[str, ...]:
        """Vedas in which this deity is mentioned at all, at any tier.

        Distinct from :attr:`attribution_scope`, which names the Vedas the *attribution*
        layer covers and is ``("RV",)`` for every deity. Reading one for the other is the
        specific misreading this pair of properties exists to prevent.
        """
        return tuple(veda for veda in ALL_VEDAS if self.mentions.get(veda))

    @property
    def mentions_total(self) -> int:
        return sum(self.mentions.values())

    @property
    def mentions_default_scope(self) -> int:
        """Mentions the product default admits: certain plus probable, all four Vedas."""
        return sum(self.mentions_certain.values()) + sum(self.mentions_probable.values())

    @property
    def mention_verdict_by_veda(self) -> dict[str, str]:
        """Per Veda, whether the default scope may state a count at all.

        This is the property that stops a zero being read as an absence. See
        :func:`vedagraph.domain.theonyms.mention_verdict` for the measurement that made it
        necessary -- ``DEITY_CERTAIN`` was effectively "came from the Rigvedic annotation",
        so the cautious filter returned wrong zeros for exactly the deities most present in
        the unannotated corpora.
        """
        return {
            veda: mention_verdict(
                self.mentions_certain.get(veda, 0),
                self.mentions_probable.get(veda, 0),
                self.mentions_ambiguous.get(veda, 0),
            )
            for veda in ALL_VEDAS
        }

    @property
    def absent_dimensions(self) -> tuple[str, ...]:
        """Dimensions this deity has no evidence for, named rather than left blank.

        A profile with an honest hole is usable and a profile with an invented value is
        not, so the holes are a stored, queryable property. Almost all of them have one
        cause and it is structural rather than a gap in this deity's record: every
        dimension counted over ``HAS_DEVATA`` is empty for a deity the Anukramani never
        ascribes a passage to, because that layer covers the Rigveda alone.
        """
        empty = {
            "attributed_mantras": not self.attributed_mantras,
            "top_rishis": not self.top_rishis,
            "top_chandas": not self.top_chandas,
            "top_concepts": not self.top_concepts,
            "co_devatas": not self.co_devatas,
            "co_mentioned": not self.co_mentioned,
            "top_actions": not self.top_actions,
            "top_requested_actions": not self.top_requested_actions,
            "top_objects": not self.top_objects,
            "formula_count": not self.formula_count,
            "mentions": not self.mentions,
        }
        return tuple(name for name, is_empty in sorted(empty.items()) if is_empty)

    @property
    def per_passage_share(self) -> float:
        """Share of attributions the source states of the mantra itself."""
        total = self.total_attributed
        return round(self.attributed_per_passage / total, 4) if total else 0.0

    def as_row(self) -> dict[str, Any]:
        return {
            "entity_key": self.entity_key,
            "display_label": self.display_label,
            "attributed_mantras": dict(sorted(self.attributed_mantras.items())),
            "total_attributed": self.total_attributed,
            "attributed_per_passage": self.attributed_per_passage,
            "attributed_inherited": self.attributed_inherited,
            "per_passage_share": self.per_passage_share,
            "attribution_scope": list(self.attribution_scope),
            "mentions": dict(sorted(self.mentions.items())),
            "mentions_certain": dict(sorted(self.mentions_certain.items())),
            "mentions_probable": dict(sorted(self.mentions_probable.items())),
            "mentions_ambiguous": dict(sorted(self.mentions_ambiguous.items())),
            "mentions_total": self.mentions_total,
            "mentions_default_scope": self.mentions_default_scope,
            "mention_scope": list(self.mention_scope),
            "mention_verdict_by_veda": dict(sorted(self.mention_verdict_by_veda.items())),
            "by_division": dict(sorted(self.by_division.items())),
            "top_rishis": [list(item) for item in self.top_rishis],
            "top_chandas": [list(item) for item in self.top_chandas],
            "top_concepts": [list(item) for item in self.top_concepts],
            "top_concepts_strict": [list(item) for item in self.top_concepts_strict],
            "co_devatas": [list(item) for item in self.co_devatas],
            "co_mentioned": [list(item) for item in self.co_mentioned],
            "top_actions": [list(item) for item in self.top_actions],
            "top_requested_actions": [list(item) for item in self.top_requested_actions],
            "top_objects": [list(item) for item in self.top_objects],
            "formula_count": self.formula_count,
            "absent_dimensions": list(self.absent_dimensions),
            "domain_model_version": DOMAIN_MODEL_VERSION,
        }


def _pairs(session: Session, query: str, **parameters: Any) -> list[tuple[str, int]]:
    return [
        (str(record["label"]), int(record["n"]))
        for record in session.run(query, **parameters)
        if record["label"] is not None
    ]


def compute_profile(
    session: Session,
    entity_key: str,
    *,
    attribution_scope: dict[str, list[str]] | None = None,
) -> DevataProfile:
    """Count everything the graph already knows about one deity.

    One query per dimension rather than one joined query, because a single query joining
    ṛṣis, metres, concepts and co-attributions over 2,869 passages multiplies rows and the
    counts come back inflated. Separate aggregations are slower to write and correct.

    ``attribution_scope`` is the whole family's measured reach. It is the same for every
    deity, so a caller building many profiles should measure it once with
    :func:`measure_attribution_scope` and pass it in; a caller that does not gets it
    measured here rather than declared, because a default that declares is how the scope
    note came to assert a Rigveda-only layer that nothing had checked.
    """
    header = session.run(
        """
        MATCH (dv:Devata {entity_key: $key})
        RETURN coalesce(dv.display_label, dv.preferred_label, dv.entity_key) AS label
        """,
        key=entity_key,
    ).single()
    profile = DevataProfile(
        entity_key=entity_key,
        display_label=str(header["label"]) if header else entity_key,
        attribution_layer_scope=(
            attribution_scope
            if attribution_scope is not None
            else measure_attribution_scope(session)
        ),
    )

    for record in session.run(
        """
        MATCH (p:Passage)-[r:HAS_DEVATA]->(:Devata {entity_key: $key})
        RETURN p.veda AS veda,
               count(*) AS n,
               sum(CASE WHEN r.attribution_precision = $per_passage THEN 1 ELSE 0 END) AS exact
        """,
        key=entity_key,
        per_passage=str(AttributionPrecision.PER_PASSAGE),
    ):
        veda = str(record["veda"])
        profile.attributed_mantras[veda] = int(record["n"])
        profile.attributed_per_passage += int(record["exact"])
    profile.attributed_inherited = profile.total_attributed - profile.attributed_per_passage

    # MENTIONS_DEVATA, not MENTIONS_ENTITY. **This is a fix, not a preference.** V3's
    # ``retire_superseded_devata_mentions`` deleted every ``MENTIONS_ENTITY`` edge onto a
    # ``:Devata`` -- there are 0 left -- so this loop used to run, match nothing and leave
    # ``mentions`` empty while the profile still reported success and landed. Every deity
    # profile computed after that retirement silently claimed the deity was mentioned
    # nowhere, and the counts already written to
    # ``data/domain/vedagraph_domain_v2/devata_profiles.jsonl`` are the pre-retirement
    # values, so the artifact looked right and could no longer be reproduced. The
    # replacement layer also spans four Vedas rather than one, which is the whole reason
    # the retirement happened.
    for record in session.run(
        """
        MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
        RETURN p.veda AS veda, m.referent_certainty AS certainty, count(*) AS n
        """,
        key=entity_key,
    ):
        veda, certainty, n = str(record["veda"]), str(record["certainty"]), int(record["n"])
        profile.mentions[veda] = profile.mentions.get(veda, 0) + n
        bucket = {
            CERTAIN: profile.mentions_certain,
            PROBABLE: profile.mentions_probable,
            AMBIGUOUS: profile.mentions_ambiguous,
        }.get(certainty)
        if bucket is None:
            # A tier this module does not know about is a contract break, not a row to
            # quietly fold into a total: the three reported figures would stop summing to
            # the mention count and the discrepancy would be invisible.
            known = sorted(DEFAULT_REFERENT_TIERS | {AMBIGUOUS})
            raise ValueError(
                f"{entity_key}: MENTIONS_DEVATA carries unknown referent_certainty "
                f"{certainty!r}; profiles report exactly {known}"
            )
        bucket[veda] = bucket.get(veda, 0) + n

    # Maṇḍala for the Rigveda; the key name differs per Veda, so the hierarchy map is read
    # rather than a column assumed.
    for record in session.run(
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        WHERE p.hierarchy IS NOT NULL
        WITH apoc.convert.fromJsonMap(p.hierarchy) AS h
        RETURN toString(coalesce(h.mandala, h.kanda, h.adhyaya, 'unknown')) AS label,
               count(*) AS n
        ORDER BY n DESC
        """
        if _has_apoc(session)
        else """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        RETURN split(split(p.canonical_key, ':')[3], '')[0] AS label, count(*) AS n
        ORDER BY n DESC
        """,
        key=entity_key,
    ):
        profile.by_division[str(record["label"])] = int(record["n"])

    profile.top_rishis = _pairs(
        session,
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[:HAS_RISHI]->(rs:Rishi)
        RETURN coalesce(rs.display_label, rs.preferred_label) AS label, count(*) AS n
        ORDER BY n DESC, label LIMIT $limit
        """,
        key=entity_key,
        limit=TOP_N,
    )
    profile.top_chandas = _pairs(
        session,
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[:HAS_CHANDAS]->(ch:Chandas)
        RETURN coalesce(ch.display_label, ch.preferred_label) AS label, count(*) AS n
        ORDER BY n DESC, label LIMIT $limit
        """,
        key=entity_key,
        limit=TOP_N,
    )
    profile.top_concepts = _pairs(
        session,
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[:ABOUT_CONCEPT]->(c)
        RETURN coalesce(c.display_label, c.concept_id) AS label, count(*) AS n
        ORDER BY n DESC, label LIMIT $limit
        """,
        key=entity_key,
        limit=TOP_N,
    )
    profile.top_concepts_strict = _pairs(
        session,
        """
        MATCH (p:Passage)-[r:HAS_DEVATA]->(:Devata {entity_key: $key})
        WHERE r.attribution_precision = $per_passage
        MATCH (p)-[:ABOUT_CONCEPT]->(c)
        RETURN coalesce(c.display_label, c.concept_id) AS label, count(*) AS n
        ORDER BY n DESC, label LIMIT $limit
        """,
        key=entity_key,
        per_passage=str(AttributionPrecision.PER_PASSAGE),
        limit=TOP_N,
    )
    profile.co_devatas = _pairs(
        session,
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[:HAS_DEVATA]->(other:Devata)
        WHERE other.entity_key <> $key
        RETURN coalesce(other.display_label, other.preferred_label) AS label, count(*) AS n
        ORDER BY n DESC, label LIMIT $limit
        """,
        key=entity_key,
        limit=TOP_N,
    )
    profile.co_mentioned = _pairs(
        session,
        """
        MATCH (:Devata {entity_key: $key})-[r:CO_OCCURS_WITH]-(other:Devata)
        RETURN coalesce(other.display_label, other.preferred_label) AS label,
               coalesce(r.passage_count, 0) AS n
        ORDER BY n DESC, label LIMIT $limit
        """,
        key=entity_key,
        limit=TOP_N,
    )
    for relationship, target in (
        ("PERFORMS_ACTION", "top_actions"),
        ("IS_ASKED_TO", "top_requested_actions"),
    ):
        # The relationship type is interpolated rather than parameterised because Cypher
        # does not parameterise it; the two values are literals in this tuple and never
        # reach here from a caller.
        setattr(
            profile,
            target,
            _pairs(
                session,
                f"""
                MATCH (:Devata {{entity_key: $key}})-[r:{relationship}]->(a:ActionPredicate)
                RETURN coalesce(a.display_label, a.action_id, a.predicate) AS label,
                       coalesce(r.passage_count, r.assertion_count, 0) AS n
                ORDER BY n DESC, label LIMIT $limit
                """,
                key=entity_key,
                limit=TOP_N,
            ),
        )
    profile.top_objects = _pairs(
        session,
        """
        MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
        WHERE m.referent_certainty IN $tiers
        MATCH (p)-[:ABOUT_CONCEPT]->(c:DomainEntity)
        RETURN coalesce(c.display_label, c.concept_id) AS label, count(*) AS n
        ORDER BY n DESC, label LIMIT $limit
        """,
        key=entity_key,
        tiers=sorted(PROFILE_MENTION_TIERS),
        limit=TOP_N,
    )
    record = session.run(
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[:USES_FORMULA]->(f:Formula)
        RETURN count(DISTINCT f) AS n
        """,
        key=entity_key,
    ).single()
    profile.formula_count = int(record["n"]) if record else 0
    return profile


_APOC_CHECKED: dict[str, bool] = {}


def _has_apoc(session: Session) -> bool:
    """Whether APOC is callable, cached per process.

    The maṇḍala breakdown needs to read a JSON-encoded ``hierarchy`` map. APOC does it
    directly; without it there is a string-splitting fallback, so the profile degrades
    rather than failing on a database without the plugin.
    """
    if "apoc" not in _APOC_CHECKED:
        try:
            session.run("RETURN apoc.version() AS v").single()
            _APOC_CHECKED["apoc"] = True
        except Exception:
            _APOC_CHECKED["apoc"] = False
    return _APOC_CHECKED["apoc"]


def top_devatas_by_mention(session: Session, limit: int = 20) -> list[tuple[str, int]]:
    """Deity keys ordered by mentions the product default admits, with the count.

    **Why this exists next to :func:`top_devatas`.** That function ranks by ``HAS_DEVATA``,
    and the attribution layer is Rigveda-only, so it answers "which deities does the
    Anukramani name most" and not "which deities does the corpus talk about most". Using
    it to choose which profiles to complete builds a Rigvedic top list and calls it a
    four-Veda one. Ranking by the mention layer at the default certainty tiers spans all
    four Vedas and matches what a default deity query will actually return, which is the
    property that makes a completed profile worth completing.

    Both orders are reported side by side wherever a top-N selection is justified, because
    they disagree and the disagreement is itself a finding.
    """
    return [
        (str(record["key"]), int(record["n"]))
        for record in session.run(
            """
            MATCH (:Passage)-[m:MENTIONS_DEVATA]->(dv:Devata)
            WHERE m.referent_certainty IN $tiers
            RETURN dv.entity_key AS key, count(*) AS n
            ORDER BY n DESC, key LIMIT $limit
            """,
            tiers=sorted(PROFILE_MENTION_TIERS),
            limit=limit,
        )
    ]


def top_devatas(session: Session, limit: int = 20) -> list[str]:
    """Deity keys ordered by attribution count, for choosing what to profile.

    Rigveda-only, because ``HAS_DEVATA`` is. See :func:`top_devatas_by_mention`.
    """
    return [
        str(record["key"])
        for record in session.run(
            """
            MATCH (:Passage)-[:HAS_DEVATA]->(dv:Devata)
            RETURN dv.entity_key AS key, count(*) AS n
            ORDER BY n DESC, key LIMIT $limit
            """,
            limit=limit,
        )
    ]


# ---------------------------------------------------------------------------
# Derived metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DerivedMetric:
    """One named, reproducible measurement an interpretation is allowed to cite.

    ``values`` is JSON-encoded because Neo4j has no nested-map property. ``scope_note`` is
    mandatory and is the field that stops a metric being misread: a count over a layer
    that covers one Veda must say so on the metric, not in a report next to it.
    """

    metric_id: str
    metric_name: str
    subject_key: str
    values: dict[str, Any]
    method: str
    scope_note: str

    def as_row(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "metric_name": self.metric_name,
            "subject_key": self.subject_key,
            "values_json": json.dumps(self.values, ensure_ascii=False, sort_keys=True),
            "method": self.method,
            "scope_note": self.scope_note,
            "domain_model_version": DOMAIN_MODEL_VERSION,
            "display_label": f"{self.metric_name} ({self.subject_key})",
            "display_type": LABEL_DERIVED_METRIC,
        }


def measure_attribution_scope(session: Session) -> dict[str, list[str]]:
    """Which corpora each deity-attribution predicate actually reaches, measured now.

    Returns ``{predicate: [veda, ...]}`` for every member of
    :data:`ATTRIBUTION_PREDICATES`, including the members that reach nothing -- an absent
    key and an empty list mean different things, and only the empty list says "this
    predicate exists in the vocabulary and has no edge".

    **Why this is a measurement and not a constant.** The sentence these figures feed was
    wrong twice for the same structural reason. First it said the Anukramaṇī layer was
    Rigveda-only, which was false because a second predicate carried 4,816 Atharvavedic
    edges. Corrected, it said ``HAS_DEVATA`` is Rigveda-only, which is true and stops being
    *adequate* the moment a third predicate lands 882 Atharvavedic dedications: the figure
    stays right and the reader still infers that the Atharvaveda has no deity attribution.

    A prose fix cannot survive that, because the next predicate is always one import away.
    So the reach is read off the graph at generation time and the sentence is assembled
    from it. A predicate that appears widens the sentence with no edit; a predicate that is
    retired narrows it.
    """
    reach: dict[str, list[str]] = {name: [] for name, _ in ATTRIBUTION_PREDICATES}
    for record in session.run(
        """
        MATCH (p:Passage)-[r]->(:Devata)
        WHERE type(r) IN $predicates
        RETURN type(r) AS predicate, collect(DISTINCT p.veda) AS vedas
        """,
        predicates=[name for name, _ in ATTRIBUTION_PREDICATES],
    ):
        reach[str(record["predicate"])] = sorted(
            str(veda) for veda in record["vedas"] if veda is not None
        )
    # The descriptor layer hangs off :DevataAscription, not :Devata, so the join above
    # cannot see it. Measured separately rather than merged, because keeping the two
    # joins apart is the same distinction the sentence is being built to state.
    for record in session.run(
        """
        MATCH (p:Passage)-[:HAS_DEVATA_ASCRIPTION]->(:DevataAscription)
        RETURN collect(DISTINCT p.veda) AS vedas
        """
    ):
        reach["HAS_DEVATA_ASCRIPTION"] = sorted(
            str(veda) for veda in (record["vedas"] or []) if veda is not None
        )
    return reach


def _reach_sentence(scope: dict[str, list[str]]) -> str:
    """The measured reach of every attribution predicate, as one readable clause.

    Returns a sentence that says the scope was **not measured** when it was not, rather
    than falling back on a declaration. A fallback here would be a validator that silently
    skips: the caller would get a confident Rigveda-only sentence with nothing behind it,
    which is exactly the state this function replaced.
    """
    if not scope:
        return (
            "The reach of the deity-attribution predicates was NOT measured for this "
            "build, so no statement about which corpora carry an attribution is made here. "
            "Query the predicates directly rather than inferring a scope from this metric."
        )
    parts = []
    for name, means in ATTRIBUTION_PREDICATES:
        vedas = scope.get(name)
        if vedas is None:
            continue
        where = ", ".join(vedas) if vedas else "no corpus"
        parts.append(f"{name} reaches {where} ({means})")
    return (
        "Measured reach of each deity-attribution predicate in this build: "
        + "; ".join(parts)
        + "."
    )


def _counted_clause() -> str:
    counted = ", ".join(COUNTED_ATTRIBUTION_PREDICATES)
    return (
        f"This figure counts {counted} and nothing else."
        if len(COUNTED_ATTRIBUTION_PREDICATES) == 1
        else f"This figure counts {counted}, and no other predicate."
    )


def metric_id(metric_name: str, subject_key: str) -> str:
    """Deterministic id, so a rebuild MERGEs rather than duplicating."""
    return f"VG:METRIC:{metric_name}:{subject_key}"


def attribution_metrics(profile: DevataProfile) -> list[DerivedMetric]:
    """The metrics derivable from one deity profile."""
    return [
        DerivedMetric(
            metric_id=metric_id("DEVATA_ATTRIBUTION_BY_VEDA", profile.entity_key),
            metric_name="DEVATA_ATTRIBUTION_BY_VEDA",
            subject_key=profile.entity_key,
            values=dict(sorted(profile.attributed_mantras.items())),
            method=(
                "count of "
                + "/".join(COUNTED_ATTRIBUTION_PREDICATES)
                + " edges grouped by passage veda"
            ),
            scope_note=(
                _counted_clause()
                + " "
                + _reach_sentence(profile.attribution_layer_scope)
                + " A Veda absent from a predicate's reach carries no edge of THAT "
                "predicate. It is not a statement that the deity is absent from the "
                "corpus, and it is not a statement that the corpus has no traditional "
                "index -- a dedication can be recorded by one predicate and unreachable "
                "by another, which is why each is named separately above."
            ),
        ),
        DerivedMetric(
            metric_id=metric_id("DEVATA_ATTRIBUTION_PRECISION", profile.entity_key),
            metric_name="DEVATA_ATTRIBUTION_PRECISION",
            subject_key=profile.entity_key,
            values={
                "per_passage": profile.attributed_per_passage,
                "container_inherited": profile.attributed_inherited,
                "per_passage_share": profile.per_passage_share,
            },
            method="HAS_DEVATA edges split on attribution_precision",
            scope_note=(
                "container_inherited attributions are the sukta's label projected onto "
                "its mantras by a scope rule. They are reproducible derivations, not "
                "statements the source made about the individual mantra."
            ),
        ),
        DerivedMetric(
            metric_id=metric_id("DEVATA_STRUCTURAL_SPREAD", profile.entity_key),
            metric_name="DEVATA_STRUCTURAL_SPREAD",
            subject_key=profile.entity_key,
            values=dict(sorted(profile.by_division.items())),
            method="count of attributed mantras grouped by top-level structural division",
            scope_note="Rigvedic mandala numbers; other Vedas absent for want of a layer.",
        ),
    ]


#: Subject key used by metrics that measure the whole corpus rather than one entity.
CORPUS_SUBJECT: Final[str] = "VG:CORPUS:FOUR-VEDA"


def corpus_metrics(session: Session) -> list[DerivedMetric]:
    """Corpus-scale measurements, computed so that an interpretation can cite one.

    These are the statistics the claims layer refers to. Each is a single aggregation over
    edges that already exist, so a reader who doubts a claim can re-run the ``method``
    string and get the same number.
    """
    metrics: list[DerivedMetric] = []

    precision: dict[str, Any] = {}
    for record in session.run(
        """
        MATCH ()-[r:HAS_DEVATA|HAS_RISHI|HAS_CHANDAS]->()
        RETURN type(r) AS predicate, r.attribution_precision AS precision, count(*) AS n
        """
    ):
        bucket = precision.setdefault(str(record["predicate"]), {})
        bucket[str(record["precision"])] = int(record["n"])
    for bucket in precision.values():
        inherited = bucket.get(str(AttributionPrecision.CONTAINER_INHERITED), 0)
        exact = bucket.get(str(AttributionPrecision.PER_PASSAGE), 0)
        total = inherited + exact
        bucket["inherited_share"] = round(inherited / total, 4) if total else 0.0
    metrics.append(
        DerivedMetric(
            metric_id=metric_id("ATTRIBUTION_PRECISION_CORPUS", CORPUS_SUBJECT),
            metric_name="ATTRIBUTION_PRECISION_CORPUS",
            subject_key=CORPUS_SUBJECT,
            values=precision,
            method=(
                "HAS_DEVATA/HAS_RISHI/HAS_CHANDAS edges grouped by attribution_precision, "
                "which is derived from the knowledge layer's scope_origin"
            ),
            scope_note=(
                _counted_clause()
                + " "
                + _reach_sentence(measure_attribution_scope(session))
                + " A Veda absent from a predicate's reach carries no edge of THAT "
                "predicate, which is not a statement about the corpus."
            ),
        )
    )

    record = session.run(
        """
        MATCH (sv:Passage)-[:REUSES_TEXT_FROM]->(rv:Passage)
        WITH count(*) AS edges, count(DISTINCT sv) AS sv_with_source,
             count(DISTINCT rv) AS rv_sources
        MATCH (m:Mantra {veda: 'SV'})
        RETURN edges, sv_with_source, rv_sources, count(m) AS sv_mantras
        """
    ).single()
    if record:
        sv_mantras = int(record["sv_mantras"])
        sv_with_source = int(record["sv_with_source"])
        metrics.append(
            DerivedMetric(
                metric_id=metric_id("SV_REUSE_OF_RV", "VG:WORK:SV:KAU"),
                metric_name="SV_REUSE_OF_RV",
                subject_key="VG:WORK:SV:KAU",
                values={
                    "reuse_edges": int(record["edges"]),
                    "sv_mantras": sv_mantras,
                    "sv_mantras_with_rv_source": sv_with_source,
                    "distinct_rv_sources": int(record["rv_sources"]),
                    "share_of_sv_with_rv_source": (
                        round(sv_with_source / sv_mantras, 4) if sv_mantras else 0.0
                    ),
                },
                method="distinct SV passages having at least one REUSES_TEXT_FROM edge to RV",
                scope_note=(
                    "Reuse is established on comparison surfaces down to "
                    "SANDHI_INSENSITIVE, the weakest level, which is the only level a "
                    "Devanagari SV text and a Latin RV text can be compared on at all. "
                    "The share would fall under a stricter level."
                ),
            )
        )

    theonym = session.run(
        """
        MATCH ()-[r:MENTIONS_ENTITY]->()
        WHERE r.theonym_ambiguous IS NOT NULL
        RETURN count(*) AS total,
               sum(CASE WHEN r.theonym_ambiguous THEN 1 ELSE 0 END) AS ambiguous
        """
    ).single()
    if theonym and int(theonym["total"]):
        total = int(theonym["total"])
        ambiguous = int(theonym["ambiguous"])
        metrics.append(
            DerivedMetric(
                metric_id=metric_id("THEONYM_AMBIGUITY", CORPUS_SUBJECT),
                metric_name="THEONYM_AMBIGUITY",
                subject_key=CORPUS_SUBJECT,
                values={
                    "mention_edges": total,
                    "theonym_ambiguous": ambiguous,
                    "share": round(ambiguous / total, 4),
                },
                method=(
                    "MENTIONS_ENTITY edges whose every matched alias is also a Devata "
                    "label form, so the mention cannot be assigned to the entity rather "
                    "than to the deity of the same name"
                ),
                scope_note=(
                    "An upper bound on the deity/concept conflation, not a count of "
                    "errors: some of these passages do mean the impersonal referent."
                ),
            )
        )

    coverage: dict[str, Any] = {}
    for record in session.run(
        """
        MATCH (m:Mantra)
        OPTIONAL MATCH (m)-[:MENTIONS_ENTITY]->(e:DomainEntity)
        WITH m, count(e) AS hits
        RETURN m.veda AS veda, count(m) AS mantras,
               sum(CASE WHEN hits > 0 THEN 1 ELSE 0 END) AS covered
        """
    ):
        mantras = int(record["mantras"])
        covered = int(record["covered"])
        coverage[str(record["veda"])] = {
            "mantras": mantras,
            "with_domain_mention": covered,
            "coverage": round(covered / mantras, 4) if mantras else 0.0,
        }
    metrics.append(
        DerivedMetric(
            metric_id=metric_id("DOMAIN_MENTION_COVERAGE", CORPUS_SUBJECT),
            metric_name="DOMAIN_MENTION_COVERAGE",
            subject_key=CORPUS_SUBJECT,
            values=coverage,
            method="mantras with at least one MENTIONS_ENTITY edge to a DomainEntity",
            scope_note=(
                "Sanskrit evidence only. Lower than the V1 concept layer's coverage "
                "because that layer also admitted English-translation matches."
            ),
        )
    )
    return metrics
