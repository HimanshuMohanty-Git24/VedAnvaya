"""One documented predicate for the eligible deity population, landed on the node.

**The defect.** ``:Devata`` is the label the Anukramaṇī's deity slot projects into, and that
slot holds more than deities. 29 of the 214 nodes are not deities at all -- 22 curated
``structure='HUMAN'`` patrons and 7 ``structure='PATRON_PRAISE'`` dānastuti gift-praise
labels -- and they carry 171 dedications between them. A further 42 carry ``ABSTRACT`` or
``UNSPECIFIED`` structure, where *Śraddhā* is a deity addressed in the vocative throughout
RV 10.151 and *abhiśāpa*, a curse, is not.

Nothing held the answer. The eligibility rule existed only inside two staging scripts and
one report, in three different spellings, and the shipped product surface had a fourth:
``domain/queries.py`` excluded ``structure='HUMAN'`` and nothing else, so
``/api/v1/insights/capabilities`` published ``eligible_deities: 192`` -- 35 above the ruled
population and 7 above even the crude one. The registry entry names this as the fixable
part: *"no eligibility field exists to hold the answer"*.

**What this module is.** The field, the one predicate that reads it, and the rulings that
populate it. It mirrors :class:`~vedagraph.domain.rishi_families` prior art on ``:Rishi``,
which already carries ``is_seer`` / ``non_seer_kind`` for exactly this reason, so the two
registries answer the same question the same way.

**The predicate.** :data:`ELIGIBLE_DEITY_PREDICATE` -- ``d.is_deity = true``. One clause.
Not a structure list, because a structure list is the thing that got spelled four ways.

**Three exclusion classes, and a fourth state that is not an exclusion.**

``HUMAN_PATRON`` (22)
    Curated ``structure='HUMAN'``. Taken from the node's own curated structure, never from
    a name heuristic. Still addressable, still carries its dedications; it is simply not a
    member of the deity population.
``DANASTUTI_GIFT_PRAISE`` (7)
    Curated ``structure='PATRON_PRAISE'``. *dānastutiḥ*, "praise of a patron's gift", has
    50 dedications across 15 hymns and was the top-ranked member of a deity co-occurrence
    table once already, graded MISLEADING.
``ABSTRACTION_NOT_AN_ADDRESSEE`` (28)
    Ruled per label in ``data/staging/communities/abstract_label_rulings.json`` against the
    line ``DEVATA_TAXONOMY_V1`` sections 7-8 already drew: *does the label name an
    addressee with a domain, or does it name the hymn's subject or its intended effect?*
    Each carries its own recorded reason. The ruling is loaded from that file, never
    re-derived here, so there is one copy of the judgement.
``UNDECIDED`` (5)
    **Kept in the population**, with ``deity_eligibility_ruling='UNDECIDED'`` recorded on
    the node. An undecided label removed is a decision made by default. Ātmā, Annam,
    Brahma, Rāti and Śacī.

**Yajurvedic ritual implements are deities here and must stay so.** Kātyāyana's opening
sūtra admits *anas*, *śākhā*, *ukhā*, *kapāla*, *idhma* and *ulūkhala* among the devatās as
*pratimābhūta*. Eight are in this graph and all eight are eligible; :data:`RITUAL_IMPLEMENTS`
names them and :func:`check_rows` fails if any is excluded. A contamination sweep that
treats a ritual implement as noise is wrong about the Yajurveda, not about the data.

**The guard that earned itself.** :func:`rulings_for` raises if a ruling key resolves to no
``:Devata``, or if the ruling file does not cover the ABSTRACT/UNSPECIFIED population
exactly. In the communities build the same guard caught a run that silently applied 27 of
28 rulings and reported 158 eligible instead of 157, because one key was spelled
``SAMJNANAM`` against the graph's ``SANJNANAM``. A ruling that matches nothing is not
applied and, without the guard, not reported either.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:  # pragma: no cover - typing only
    from neo4j import Session

CONTRACT_VERSION: Final = "VG:DEITY_ELIGIBILITY:V1"

#: The one documented predicate. Every count over the deity population uses this string.
ELIGIBLE_DEITY_PREDICATE: Final = "d.is_deity = true"

# ---------------------------------------------------------------------------
# The transitional shim, REMOVED. Kept as a note because the hazard it covered is real.
# ---------------------------------------------------------------------------
#
# ``eligible_predicate(alias)`` stood here and returned
# ``coalesce(a.is_deity, NOT coalesce(a.structure,'UNSPECIFIED') IN ['HUMAN','PATRON_PRAISE'])``.
#
# **Why a shim existed at all.** ``is_deity = true`` is the end state, but a query is code
# and the property is data, and the two land in different changes. A shipped query that
# reads a property the graph does not hold does not error -- Neo4j returns null, the WHERE
# excludes every row, and the endpoint answers with an empty result that looks like a
# finding. ``tests/api/test_cypher_property_hygiene.py`` exists because that exact failure
# shipped once. So the shim read the ruling where it existed and fell back to the curated
# structure where it did not.
#
# **Its own removal condition, met.** It said: when
# ``MATCH (d:Devata) WHERE d.is_deity IS NULL RETURN count(d)`` is 0, replace every call
# with :data:`ELIGIBLE_DEITY_PREDICATE`. Measured: 214 of 214 ruled, 0 unruled, 0 excluded
# without a recorded reason. The condition had been met and the shim was still in every
# shipped query, which made it a *second* eligibility predicate -- the one thing
# GAP-ENTITY_COVERAGE-008 exists to remove. It disagreed with the ruling on 29 of the 214:
# it admitted the 28 abstractions ruled ABSTRACTION_NOT_AN_ADDRESSEE and excluded the dog,
# whom the ruling admits. Deleted rather than deprecated, because a fallback nobody calls is
# a fallback somebody will call.


#: Repo root, so the ruling file resolves the same from a test runner, a script and the
#: API process. A relative default here reads as an empty ruling set from any other cwd,
#: and an empty ruling set raises rather than silently keeping all 42 -- but only because
#: :func:`rulings_for` checks coverage, so the anchor is what makes the error legible.
_REPO_ROOT: Final = pathlib.Path(__file__).resolve().parents[3]

#: Where the per-label ABSTRACT judgement lives. One copy, loaded, never re-derived.
ABSTRACT_RULINGS_PATH: Final = (
    _REPO_ROOT / "data" / "staging" / "communities" / "abstract_label_rulings.json"
)

#: Curated structures that are not deities, and the class each becomes.
STRUCTURE_EXCLUSIONS: Final[dict[str, str]] = {
    "HUMAN": "HUMAN_PATRON",
    "PATRON_PRAISE": "DANASTUTI_GIFT_PRAISE",
}

#: The structures whose membership is decided per label rather than by structure.
RULED_STRUCTURES: Final[frozenset[str]] = frozenset({"ABSTRACT", "UNSPECIFIED"})

#: Yajurvedic ritual implements admitted as *pratimābhūta*. Eligible, and asserted to be.
RITUAL_IMPLEMENTS: Final[frozenset[str]] = frozenset(
    {
        "VG:DEVATA:BARHIH",
        "VG:DEVATA:DEVIRDVARAH",
        "VG:DEVATA:GRAVANAH",
        "VG:DEVATA:HAVIRDHANE-SAKATE",
        "VG:DEVATA:ULUKHALAM",
        "VG:DEVATA:ULUKHALAMUSALE",
        "VG:DEVATA:VANASPATIH",
        "VG:DEVATA:YUPAH",
    }
)

#: The closed vocabulary of ``deity_eligibility_ruling``.
RULINGS: Final[frozenset[str]] = frozenset({"DEITY", "NOT_DEITY", "UNDECIDED"})


class RulingCoverageError(ValueError):
    """The ruling file and the graph population do not correspond exactly."""


@dataclass(frozen=True)
class EligibilityRow:
    """One ``:Devata``'s eligibility, with the basis and reason that produced it."""

    entity_key: str
    display_label: str | None
    structure: str | None
    is_deity: bool
    non_deity_kind: str | None
    ruling: str
    basis: str
    reason: str

    def as_properties(self) -> dict[str, Any]:
        return {
            "entity_key": self.entity_key,
            "is_deity": self.is_deity,
            "non_deity_kind": self.non_deity_kind,
            "deity_eligibility_ruling": self.ruling,
            "deity_eligibility_basis": self.basis,
            "deity_eligibility_reason": self.reason,
            "deity_eligibility_contract_version": CONTRACT_VERSION,
        }


def load_abstract_rulings(path: pathlib.Path | None = None) -> dict[str, dict[str, str]]:
    """The per-label ABSTRACT rulings, keyed by entity key."""
    source = path or ABSTRACT_RULINGS_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    rulings = {}
    for item in payload["rulings"]:
        ruling = str(item["ruling"])
        if ruling not in RULINGS:
            raise RulingCoverageError(
                f"{item['key']} carries ruling {ruling!r}, which is outside {sorted(RULINGS)}."
            )
        rulings[str(item["key"])] = {"ruling": ruling, "reason": str(item["reason"])}
    return rulings


def rulings_for(
    devatas: list[dict[str, Any]], rulings: dict[str, dict[str, str]]
) -> list[EligibilityRow]:
    """Every ``:Devata`` becomes exactly one :class:`EligibilityRow`, or this raises.

    ``devatas`` carries ``entity_key``, ``display_label`` and ``structure`` per node.
    """
    ruled_population = {
        str(row["entity_key"])
        for row in devatas
        if str(row.get("structure") or "UNSPECIFIED") in RULED_STRUCTURES
    }
    missing = sorted(ruled_population - set(rulings))
    orphaned = sorted(set(rulings) - ruled_population)
    if missing or orphaned:
        raise RulingCoverageError(
            "The ABSTRACT ruling file does not cover the graph population exactly. "
            f"Ruled in the graph but absent from the file: {missing}. "
            f"In the file but resolving to no ABSTRACT/UNSPECIFIED :Devata: {orphaned}. "
            "A ruling that matches nothing is not applied and must not be reported as if "
            "it were."
        )

    rows: list[EligibilityRow] = []
    for record in devatas:
        key = str(record["entity_key"])
        structure = str(record.get("structure") or "UNSPECIFIED")
        label = record.get("display_label")
        if structure in STRUCTURE_EXCLUSIONS:
            kind = STRUCTURE_EXCLUSIONS[structure]
            rows.append(
                EligibilityRow(
                    entity_key=key,
                    display_label=label,
                    structure=structure,
                    is_deity=False,
                    non_deity_kind=kind,
                    ruling="NOT_DEITY",
                    basis="CURATED_STRUCTURE",
                    reason=(
                        "Curated structure HUMAN: a named human patron the Anukramani puts "
                        "in the deity slot, not an addressee."
                        if kind == "HUMAN_PATRON"
                        else "Curated structure PATRON_PRAISE: a danastuti gift-praise "
                        "label, praise of a gift rather than an addressee."
                    ),
                )
            )
            continue
        if structure in RULED_STRUCTURES:
            ruling = rulings[key]
            not_deity = ruling["ruling"] == "NOT_DEITY"
            rows.append(
                EligibilityRow(
                    entity_key=key,
                    display_label=label,
                    structure=structure,
                    is_deity=not not_deity,
                    non_deity_kind="ABSTRACTION_NOT_AN_ADDRESSEE" if not_deity else None,
                    ruling=ruling["ruling"],
                    basis="ABSTRACT_LABEL_RULING",
                    reason=ruling["reason"],
                )
            )
            continue
        rows.append(
            EligibilityRow(
                entity_key=key,
                display_label=label,
                structure=structure,
                is_deity=True,
                non_deity_kind=None,
                ruling="DEITY",
                basis="CURATED_STRUCTURE",
                reason=(
                    f"Curated structure {structure}: an addressee the Anukramani ascribes "
                    "passages to. Ritual implements are included, per Katyayana's opening "
                    "sutra admitting them as pratimabhuta."
                ),
            )
        )
    return rows


DEVATA_QUERY: Final = (
    "MATCH (d:Devata) RETURN d.entity_key AS entity_key, "
    "d.display_label AS display_label, d.structure AS structure ORDER BY entity_key"
)


def rows_from_session(session: Session, path: pathlib.Path | None = None) -> list[EligibilityRow]:
    devatas = [dict(record) for record in session.run(DEVATA_QUERY)]
    return rulings_for(devatas, load_abstract_rulings(path))


def check_rows(rows: list[EligibilityRow]) -> dict[str, Any]:
    """The contract's gate. Each finding has a way to fail.

    ``every_node_typed``
        no ``:Devata`` may be left without a ruling.
    ``excludes_the_29``
        the curated non-members must all be excluded; this is the figure the closure test
        names.
    ``ritual_implements_retained``
        all eight *pratimābhūta* implements must be eligible. This is the assertion that
        stops a contamination sweep from being run over the Yajurveda.
    ``reasons_recorded``
        an exclusion without a reason is a rule applied implicitly, which is the thing the
        closure test forbids.
    """
    by_kind: dict[str, int] = {}
    for row in rows:
        if row.non_deity_kind:
            by_kind[row.non_deity_kind] = by_kind.get(row.non_deity_kind, 0) + 1
    curated_excluded = by_kind.get("HUMAN_PATRON", 0) + by_kind.get("DANASTUTI_GIFT_PRAISE", 0)
    eligible = [row for row in rows if row.is_deity]
    implements_excluded = sorted(
        row.entity_key for row in rows if row.entity_key in RITUAL_IMPLEMENTS and not row.is_deity
    )
    unreasoned = sorted(row.entity_key for row in rows if not row.reason)
    implements_present = {row.entity_key for row in rows} & RITUAL_IMPLEMENTS
    return {
        "devata_nodes": len(rows),
        "eligible_deities": len(eligible),
        "excluded": len(rows) - len(eligible),
        "excluded_by_kind": dict(sorted(by_kind.items())),
        "every_node_typed": all(row.ruling in RULINGS for row in rows),
        "excludes_the_29": curated_excluded == 29,
        "curated_non_members_excluded": curated_excluded,
        "ritual_implements_present": len(implements_present),
        "ritual_implements_retained": not implements_excluded,
        "ritual_implements_wrongly_excluded": implements_excluded,
        "reasons_recorded": not unreasoned,
        "rows_without_a_reason": unreasoned,
        "undecided_kept": sorted(row.entity_key for row in rows if row.ruling == "UNDECIDED"),
        "passes": (
            all(row.ruling in RULINGS for row in rows)
            and curated_excluded == 29
            and not implements_excluded
            and not unreasoned
        ),
    }


# ---------------------------------------------------------------------------
# GAP-ENTITY_COVERAGE-008: product consumer consistency
# ---------------------------------------------------------------------------

#: The Cypher the registry entry used to carry as its closure measure, kept verbatim because
#: the replacement below is only defensible beside the thing it replaces.
#:
#: It asks whether the structure-based exclusion set and ``is_deity = false`` agree, and it
#: returns 29 *by construction*: 28 ``ABSTRACT`` labels ruled ``NOT_DEITY`` that the structure
#: predicate admits because ``ABSTRACT`` is not in its exclusion set, plus ``VG:DEVATA:SUNAH``
#: -- the dog -- ruled ``DEITY`` on the recorded ground that excluding it for a structure of
#: ``UNSPECIFIED`` rather than ``INDIVIDUAL`` would be excluding on a morphological accident.
#: Driving it to 0 means overturning one of those two recorded curations to satisfy a metric.
#:
#: And the coincidence that hid it: the entry's closure *test* says "counts over it exclude the
#: 29 non-deities", where that 29 is 22 ``HUMAN`` plus 7 ``PATRON_PRAISE`` -- the figure
#: :func:`check_rows` gates as ``excludes_the_29``. Two unrelated quantities that both equal 29,
#: one in the test and one in the measure, which is why a measure comparing the wrong two things
#: read as though it were checking the test.
SUPERSEDED_EQUALITY_MEASURE: Final = (
    "MATCH (d:Devata) WHERE (coalesce(d.structure,'UNSPECIFIED') IN "
    "['HUMAN','PATRON_PRAISE','UNSPECIFIED']) <> (d.is_deity = false) RETURN count(d)"
)

#: The replacement, per OWNER_DECISION_ENTITY_008_DEITY_MEMBERSHIP. Product Deity membership
#: and source addressability-as-deity are not the same predicate, so they are not required to
#: agree; what must hold is that every product surface reads the authoritative one.
PRODUCT_CONSUMER_MEASURE: Final = (
    "MATCH (d:Devata) WHERE d.is_deity IS NULL RETURN count(d)  "
    "// + the static consumer scan in check_product_consumers()"
)

#: Modules permitted to mention a structure-based deity predicate, and why each one may.
#:
#: ``deity_population``  owns the contract and quotes the superseded clause in its own docstring
#: ``deity_eligibility`` this module, which names the exclusion structures to READ the curation
#: ``models/entity``     declares ``DEITY_STRUCTURES`` / ``NON_DEITY_STRUCTURES`` as vocabulary
#: ``domain/queries``    counts structural SHAPE per axis (individual/pair/group), descriptive
#:                       and reconciling to 214; it is not a membership filter
#: ``domain/v3_loader``  selects PAIR/GROUP rows needing decomposition, a structural question
#: ``entity_service``    validates a CLIENT-SUPPLIED ``structure`` filter against the known
#:                       value space (``_validate_choice`` at one call site, and nothing else);
#:                       rejecting an unknown query parameter is not deciding membership, and
#:                       every membership read in that module goes through
#:                       ``deity_structure_clause``
_STRUCTURE_PREDICATE_ALLOWED_IN: Final[frozenset[str]] = frozenset(
    {
        "deity_population.py",
        "deity_eligibility.py",
        "entity.py",
        "entity_service.py",
        "queries.py",
        "v3_loader.py",
    }
)

#: Figures that were the deity population before the eligibility contract landed. A product
#: surface still publishing one of these as a deity count is a stale consumer, which is clause
#: 5 of the owner decision.
SUPERSEDED_POPULATION_FIGURES: Final[tuple[int, ...]] = (184, 192)


def check_product_consumers(session: Session) -> dict[str, Any]:
    """PRODUCT CONSUMER CONSISTENCY: the closure measure for GAP-ENTITY_COVERAGE-008.

    Not predicate equality. The two predicates are intentionally different and the owner
    decision says so; asking them to agree is asking the curation to be overturned. What this
    measures instead is that the product only ever reads the authoritative one.

    ``every_node_ruled``
        ``d.is_deity`` is populated on every ``:Devata``. The clause fails closed, so an
        unruled node is silently excluded from every deity surface -- a shrinking pantheon
        with no response saying so.
    ``divergence_is_explained``
        every node the two predicates disagree about carries a recorded ruling AND a recorded
        reason. This is what makes the divergence a documented decision rather than a defect:
        an unexplained disagreement fails even though the count itself is allowed.
    ``authoritative_population``
        the published figure, from ``ELIGIBLE_DEITY_PREDICATE``.
    ``source_predicate_population``
        what the structure predicate would have published. Reported, never consumed, so the
        gap between them stays visible rather than being argued about.

    The static half -- that no consumer outside :data:`_STRUCTURE_PREDICATE_ALLOWED_IN`
    substitutes the source predicate, and that no surface still publishes 184 or 192 -- is in
    ``tests/api/test_deity_population.py``, because it is a fact about the source tree and not
    about the graph.
    """
    row = session.run(
        f"""
        MATCH (d:Devata)
        RETURN count(d) AS devata_nodes,
               sum(CASE WHEN {ELIGIBLE_DEITY_PREDICATE} THEN 1 ELSE 0 END)
                 AS authoritative_population,
               sum(CASE WHEN d.is_deity IS NULL THEN 1 ELSE 0 END) AS unruled,
               sum(CASE WHEN NOT coalesce(d.structure,'UNSPECIFIED')
                            IN ['HUMAN','PATRON_PRAISE','UNSPECIFIED']
                        THEN 1 ELSE 0 END) AS source_predicate_population
        """
    ).single()
    divergent = [
        dict(record)
        for record in session.run(
            """
            MATCH (d:Devata)
            WHERE (coalesce(d.structure,'UNSPECIFIED') IN ['HUMAN','PATRON_PRAISE','UNSPECIFIED'])
                  <> (d.is_deity = false)
            RETURN d.entity_key AS entity_key, d.display_label AS display_label,
                   d.structure AS structure, d.is_deity AS is_deity,
                   d.deity_eligibility_ruling AS ruling,
                   d.deity_eligibility_reason AS reason
            ORDER BY d.structure, d.entity_key
            """
        )
    ]
    unexplained = sorted(
        str(item["entity_key"])
        for item in divergent
        if not item.get("ruling") or not item.get("reason")
    )
    by_direction: dict[str, int] = {}
    for item in divergent:
        key = f"{item['structure']}|is_deity={item['is_deity']}|{item['ruling']}"
        by_direction[key] = by_direction.get(key, 0) + 1
    return {
        "contract_version": CONTRACT_VERSION,
        "authoritative_predicate": ELIGIBLE_DEITY_PREDICATE,
        "devata_nodes": int(row["devata_nodes"]),
        "authoritative_population": int(row["authoritative_population"]),
        "source_predicate_population": int(row["source_predicate_population"]),
        "unruled": int(row["unruled"]),
        "every_node_ruled": int(row["unruled"]) == 0,
        "documented_intentional_divergence": len(divergent),
        "divergence_by_direction": dict(sorted(by_direction.items())),
        "divergence_is_explained": not unexplained,
        "nodes_diverging_without_a_recorded_reason": unexplained,
        "superseded_equality_measure": SUPERSEDED_EQUALITY_MEASURE,
        "passes": int(row["unruled"]) == 0 and not unexplained,
    }
