"""Corpus-derived profiles for deities, and the metrics an interpretation may cite.

A profile here is arithmetic over edges that already exist. Nothing is read, inferred or
characterised: "Indra is attributed to 2,869 Rigvedic mantras, 8,329 of the corpus's
deity attributions arrive by sūkta inheritance, and his most frequent co-attributed deity
is X" are all counts. That restraint is the point. The spec this implements is explicit
that evolution must be *computed, not asserted* -- there is to be no
``Indra -[:DECLINED_IN]-> LaterVeda`` edge -- so what this module produces is the
measurement, and :mod:`vedagraph.domain.claims` is the only place allowed to say what a
measurement might mean.

**The coverage limit is part of the profile, not a footnote to it.** The Anukramaṇī
attribution layer is Rigveda-only: 10,552 of 10,552 Rigvedic mantras carry a deity, and
0 of 5,839 Atharvavedic, 0 of 1,975 Yajurvedic and 0 of 1,844 Sāmavedic ones do. So a
profile that reported "Indra: RV 2869, SV 0, YV 0, AV 0" would be read as *Indra is absent
from the other three Vedas*, which is false and is the single most misleading sentence
this layer could produce. Every profile therefore carries
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

#: Vedas whose mantras carry an Anukramaṇī deity/ṛṣi/metre attribution. Measured, not
#: assumed: see the module docstring for the counts.
ATTRIBUTION_VEDAS: tuple[str, ...] = ("RV",)

#: All four, for the layers that do span the corpus.
ALL_VEDAS: tuple[str, ...] = ("RV", "SV", "YV", "AV")

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
    #: The subset the source states of the mantra itself, not of its enclosing sūkta.
    attributed_per_passage: int = 0
    attributed_inherited: int = 0
    #: Lexical mentions by Veda. Spans four Vedas where deity aliases exist.
    mentions: dict[str, int] = field(default_factory=dict)
    #: Structural spread, e.g. {"1": 300, "2": 40, ...} by maṇḍala.
    by_division: dict[str, int] = field(default_factory=dict)
    top_rishis: list[tuple[str, int]] = field(default_factory=list)
    top_chandas: list[tuple[str, int]] = field(default_factory=list)
    top_concepts: list[tuple[str, int]] = field(default_factory=list)
    co_devatas: list[tuple[str, int]] = field(default_factory=list)
    formula_count: int = 0

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
            "by_division": dict(sorted(self.by_division.items())),
            "top_rishis": [list(item) for item in self.top_rishis],
            "top_chandas": [list(item) for item in self.top_chandas],
            "top_concepts": [list(item) for item in self.top_concepts],
            "co_devatas": [list(item) for item in self.co_devatas],
            "formula_count": self.formula_count,
            "domain_model_version": DOMAIN_MODEL_VERSION,
        }


def _pairs(session: Session, query: str, **parameters: Any) -> list[tuple[str, int]]:
    return [
        (str(record["label"]), int(record["n"]))
        for record in session.run(query, **parameters)
        if record["label"] is not None
    ]


def compute_profile(session: Session, entity_key: str) -> DevataProfile:
    """Count everything the graph already knows about one deity.

    One query per dimension rather than one joined query, because a single query joining
    ṛṣis, metres, concepts and co-attributions over 2,869 passages multiplies rows and the
    counts come back inflated. Separate aggregations are slower to write and correct.
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

    for record in session.run(
        """
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(:Devata {entity_key: $key})
        RETURN p.veda AS veda, count(*) AS n
        """,
        key=entity_key,
    ):
        profile.mentions[str(record["veda"])] = int(record["n"])

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


def top_devatas(session: Session, limit: int = 20) -> list[str]:
    """Deity keys ordered by attribution count, for choosing what to profile."""
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
            method="count of HAS_DEVATA edges grouped by passage veda",
            scope_note=(
                "The Anukramani attribution layer exists for the Rigveda only "
                f"({', '.join(ATTRIBUTION_VEDAS)}). A zero for another Veda means that "
                "Veda has no attribution layer, NOT that the deity is absent from it."
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
                "Rigveda only: the Anukramani attribution layer does not cover SV, YV or AV."
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
