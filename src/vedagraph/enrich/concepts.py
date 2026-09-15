"""The concept layer: a small hand-authored lexicon, and deterministic passage attachment.

Three ideas hold this module together, and each of them is a decision that could have gone
the other way.

**A concept is not a deity, and the code enforces the separation the registry declares.**
``VG:CONCEPT:AGNI-FIRE`` is the fire; ``VG:DEVATA:AGNIH`` is the god. They are joined by
exactly one edge type, ``DEVATA_ASSOCIATED_WITH``, generated from the registry's
``related_devatas`` and validated against ``data/registry/devatas.yaml`` on load, so a
typo'd deity key raises instead of quietly producing an edge to a node that does not exist.
Nothing here merges the two, and the frozen semantic ontology refuses ``REPRESENTS`` and
``IS_GOD_OF`` by name for the same reason.

**A concept is attached by a rule over stored text, never by reading.** Two independent
evidence paths run, and every assertion records which one produced it:

*Sanskrit tokens.* Aliases are folded through
:func:`~vedagraph.normalize.comparison_form` with
:attr:`~vedagraph.normalize.ComparisonForm.SEARCH_NORMALIZED` -- the same call that built
``TextSurfaces.script_folded`` -- and compared against that surface's whitespace tokens.
Folding is not optional here: the search surface replaces ``ṛ``, ``ḷ`` and ``ṃ`` with
private-use sentinels, so a raw IAST ``ṛtasya`` shares no code point with the stored
``\\ue000tasya`` and would match nothing at all. This is the strongest evidence the layer
has, because it is a claim about the Sanskrit.

*Sanskrit on the sandhi surface, for the Samaveda only.* See
:data:`SANDHI_MATCH_VEDAS` for the measurement and the false-positive cost.

*English translations.* 17,281 of the corpus's 20,210 mantras carry one (RV 10,500 of
10,552, YV 1,903 of 1,975, AV 4,878 of 5,839, **SV 0 of 1,844**). Griffith translated the
Rigveda and the Yajurveda; Whitney and Lanman translated the Atharvaveda, and their diction
is not the same, which is why the registry's English aliases were measured against all
three and not assumed from one. An English match is a claim about a nineteenth-century
translator's word choice, so it always scores below a Sanskrit match and can never
outrank one.

**The Samaveda's coverage rests entirely on Sanskrit.** It has no translations at all. Any
report of this layer that quotes a single corpus-wide coverage number is hiding that, so
:func:`assign_concepts` reports coverage per Veda and per evidence path.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import yaml

from vedagraph.enrich.corpus import Corpus, MantraRecord
from vedagraph.enrich.guards import (
    MAX_CONCEPT_ASSERTIONS,
    MAX_CONCEPT_NODES,
    MAX_CONCEPTS_PER_PASSAGE,
    top_k,
)
from vedagraph.enrich.predicates import NodeKind, StructuralPredicate, check_signature
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    RunReport,
    TrustClass,
    run_id,
)
from vedagraph.enrich.records import ConceptAssertionRow, ConceptRow
from vedagraph.enrich.surfaces import render_for_display
from vedagraph.normalize import ComparisonForm, comparison_form
from vedagraph.semantic.ontology import SemanticNodeType

#: Location of the lexicon, relative to the project root. A single constant because the
#: loader, the validator and the tests must not be able to disagree about which file is
#: the registry.
CONCEPT_REGISTRY_PATH: Final = Path("data") / "registry" / "concepts.yaml"
DEVATA_REGISTRY_PATH: Final = Path("data") / "registry" / "devatas.yaml"

#: Concept ids are pinned identity, not derived labels. The pattern is enforced so that a
#: hand edit cannot introduce ``VG:Concept:agni_fire`` and have it silently become a second
#: node alongside ``VG:CONCEPT:AGNI-FIRE``.
CONCEPT_ID_PATTERN: Final = re.compile(r"^VG:CONCEPT:[A-Z0-9]+(?:-[A-Z0-9]+)*$")

#: An English alias must be one token of the translation. Phrase matching over a
#: nineteenth-century translation was rejected: "sacred grass" and "grass, sacred" are the
#: same claim about barhis, and a matcher that finds one and not the other reports a
#: property of Griffith's word order rather than of the verse.
ENGLISH_ALIAS_PATTERN: Final = re.compile(r"^[a-z]+(?:-[a-z]+)*$")

#: How the translation is cut into comparable tokens. A hyphen is *internal* and an
#: apostrophe is *not*, and both halves of that were measured. Keeping hyphens internal
#: removes a whole false-positive class from Whitney's Atharvaveda, where "self-giving",
#: "self-yoked" and "self-controller" would otherwise all assert the concept "self"; it
#: also lets the registry list ``life-time`` (103 Atharvaveda passages) as its own alias
#: rather than pretending it is ``life``. Splitting on the apostrophe recovers the
#: possessives -- "Heaven's", "Soma's" -- which are ordinary occurrences of the noun.
ENGLISH_TOKEN_PATTERN: Final = re.compile(r"[a-z]+(?:-[a-z]+)*")

#: Vedas whose edition does not divide words reliably enough for token matching alone, and
#: which therefore also get a substring pass over ``TextSurfaces.sandhi_insensitive``.
#:
#: Measured over the four canonical corpora: mean folded token length is 5.75 characters in
#: the Rigveda and 5.82 in the Atharvaveda, against 6.98 in the Samaveda and 7.47 in the
#: Yajurveda, and 8.7% of Samavedic tokens exceed twelve characters against 1.0% of
#: Rigvedic ones. The Samaveda's Wikisource text writes ``yaddidhṛkṣema`` where the Rigveda
#: writes ``yad didhṛkṣema``; a token matcher sees no word there at all. Only the Samaveda
#: is listed, for one reason that outweighs the Yajurveda's similar token length: the
#: Samaveda has **no translations**, so without this pass its coverage is whatever the
#: token path happens to reach and nothing else can compensate.
#:
#: The cost is real and is not hidden. Substring matching on a surface with no word
#: boundaries produces matches that span two words: ``devā tā`` becomes ``devātā``, which
#: contains ``vāta`` ("wind"). :data:`MIN_SANDHI_ALIAS_CHARS` is the mitigation, not a
#: cure, and every assertion from this path is scored below every token-path assertion and
#: carries ``sanskrit-sandhi`` in its method so it can be filtered out wholesale.
SANDHI_MATCH_VEDAS: Final[frozenset[str]] = frozenset({"SV"})

#: Shortest folded alias allowed on the sandhi path. Set to six by measurement, not by
#: taste. At five the path admitted these, counted over the corpus token index:
#:
#: * ``tamaḥ`` (darkness) inside ``katamaḥ``, ``uttamaḥ``, ``madintamaḥ`` -- 18 genuine
#:   occurrences against 163 inside a superlative in ``-tama-``;
#: * ``avase`` (help) inside ``śravase``, ``śavase``, ``tavase``, ``pavase`` -- 83 against
#:   140;
#: * ``astam`` (home) inside ``hastam``, ``praśastam``, ``tastambha`` -- 15 against 135;
#: * ``ojasā`` (might) inside ``viśvabhojasā``; ``indur`` (soma) inside ``bhinduḥ``;
#:   ``medhā`` (insight) inside the proper name ``priyamedhā``.
#:
#: Both false positives found in the hand-audited Samaveda sample were five-character
#: aliases. Raising the floor to six removes every alias listed above and costs 7.4
#: percentage points of Samavedic coverage (80.3% to 72.9%; 71.7% once
#: :data:`SANDHI_SUPPRESSED_ALIASES` is also applied). That is the right trade for the one
#: Veda whose assertions no translation can be checked against.
MIN_SANDHI_ALIAS_CHARS: Final = 6

#: Aliases barred from the sandhi path even though they clear
#: :data:`MIN_SANDHI_ALIAS_CHARS`, with the Samavedic word each was found inside. Compiled
#: by scanning every sandhi-eligible alias against the Samaveda's own token vocabulary and
#: reading the hosts, not by intuition: a length floor cannot know that ``ṛtasya`` sits
#: inside ``amṛtasya`` and ``ghṛtasya``, both of which are aliases of *other* concepts in
#: this same lexicon.
#:
#: These stay on the token path, where the word boundary makes them exact and safe. The
#: list is validated against the registry, so an alias renamed out of the lexicon does not
#: leave a dead suppression behind.
SANDHI_SUPPRESSED_ALIASES: Final[dict[str, str]] = {
    "ṛtasya": "inside amṛtasya (immortality) and ghṛtasya (butter); 32 host occurrences "
    "in the Samaveda against 12 genuine ones",
    "mṛtasya": "inside amṛtasya, whose sense is the exact opposite",
    "ratham": "inside prathama- ('first'); 25 host occurrences and 0 genuine ones",
    "dhanam": "inside vardhanam ('increasing') and prasādhanam ('effecting')",
    "dhanaṃ": "inside vardhanaṃ and gayasādhanaṃ, as above",
    "vanāni": "inside bhuvanāni ('worlds') and savanāni ('pressings')",
    "vaneṣu": "inside bhuvaneṣu and savaneṣu, as above",
    "kṣatram": "inside nakṣatram ('star')",
    "yudhaḥ": "inside svāyudhaḥ and tigmāyudhaḥ, which are āyudha 'weapon', not yudh",
    "druhaḥ": "inside adruhaḥ, the negation",
    "dhīmahi": "inside samidhīmahi and idhīmahi, which are indh- 'kindle'",
    "annasya": "inside the word-boundary sequences adṛśran asya and maghavan asya",
    "vāyavaḥ": "inside droṇeṣv āyavaḥ ('men') and tvā yavaḥ",
}

_STAGE: Final = "concepts"
_METHOD_ROOT: Final = "concept-alias-v1"
_PATH_TOKEN: Final = "sanskrit-token"
_PATH_SANDHI: Final = "sanskrit-sandhi"
_PATH_ENGLISH: Final = "english"
_REGISTRY_METHOD_BROADER: Final = "concept-registry-broader-v1"
_REGISTRY_METHOD_DEVATA: Final = "concept-registry-devata-association-v1"
_REGISTRY_SURFACE: Final = "registry:data/registry/concepts.yaml"

# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------
# One scale, three bands, and the bands do not overlap. That is the whole design: a
# consumer who filters at 0.7 gets Sanskrit-token evidence and nothing else, without
# needing to know how any of the numbers were chosen.
#
#   0.80 - 0.92   Sanskrit token. The alias is a whole word of the folded Sanskrit.
#   0.55 - 0.67   Sanskrit sandhi substring, Samaveda only. Same language, no word
#                 boundary, and therefore a materially weaker claim.
#   0.42 - 0.58   English translation. A claim about Griffith's or Whitney's word choice.
#
# Within a band, more distinct aliases means a stronger reading of the same evidence: one
# hit on ``agnim`` and four hits on ``agnim / agne / arciṣā / śociṣā`` are not equally good
# reasons to say a verse is about fire. The step is small on purpose; it orders candidates
# inside a band and never lifts one out of it.
#
# The corroboration bonus applies only when a Sanskrit path AND the English path both fire,
# because that is the only combination where the two claims are independent. Two Sanskrit
# paths agreeing is one claim counted twice.
_SANSKRIT_TOKEN_BASE: Final = 0.80
_SANSKRIT_TOKEN_CEILING: Final = 0.92
_SANDHI_BASE: Final = 0.55
_SANDHI_CEILING: Final = 0.67
_ENGLISH_BASE: Final = 0.42
_ENGLISH_CEILING: Final = 0.58
_ALIAS_STEP: Final = 0.04
_CORROBORATION_BONUS: Final = 0.05
_SCORE_CEILING: Final = 0.95

#: Characters of context kept on each side of a hit. Small enough that the quote is the
#: evidence rather than the verse, large enough to read.
_SANSKRIT_CONTEXT_TOKENS: Final = 2
_SANDHI_CONTEXT_CHARS: Final = 25
_ENGLISH_CONTEXT_CHARS: Final = 55


class ConceptRegistryError(ValueError):
    """The concept registry is not loadable as written.

    A distinct type because every one of these is a data error in a hand-authored file,
    and the caller's only useful response is to fix the file. Nothing in this module
    repairs a registry.
    """


@dataclass(frozen=True)
class ConceptEdgeRow:
    """One registry-stated edge, either concept-to-concept or devata-to-concept.

    Both edges come from the same hand-authored file and carry the same trust class, so
    they share a row shape. They are ``SOURCE_EXPLICIT`` rather than
    ``DETERMINISTIC_DERIVED``: nothing was computed, a person wrote the statement down, and
    the evidence is the definition they wrote next to it.
    """

    predicate: str
    subject_key: str
    object_key: str
    subject_kind: str
    object_kind: str
    provenance: Provenance

    def as_row(self) -> dict[str, Any]:
        return {
            "predicate": self.predicate,
            "subject_key": self.subject_key,
            "object_key": self.object_key,
            "subject_kind": self.subject_kind,
            "object_kind": self.object_kind,
            **self.provenance.as_dict(),
        }


def fold_alias(alias: str) -> str:
    """Fold one IAST alias onto the corpus search surface.

    The registry is written in readable IAST and the corpus is searched on a folded
    surface, and the two are not the same string. ``comparison_form(...,
    SEARCH_NORMALIZED)`` casefolds, strips Vedic tone marks and editorial punctuation, and
    replaces the vocalic ``ṛ``/``ṝ``, the lateral series and every spelling of the anusvara
    with private-use sentinels. Aliases must go through the identical call, or the layer
    silently matches nothing for exactly the concepts whose names contain those sounds --
    ``ṛta``, ``pṛthivī``, ``mṛtyu``, ``amṛta``, ``ghṛta``, ``hṛd``.
    """
    return comparison_form(alias, ComparisonForm.SEARCH_NORMALIZED)


# ---------------------------------------------------------------------------
# Loading and validation
# ---------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConceptRegistryError(f"registry not found: {path}")
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ConceptRegistryError(f"{path}: expected a mapping at the top level")
    return parsed


def _devata_keys(project_root: Path) -> frozenset[str]:
    document = _read_yaml(project_root / DEVATA_REGISTRY_PATH)
    entities = document.get("entities")
    if not isinstance(entities, list) or not entities:
        raise ConceptRegistryError(f"{DEVATA_REGISTRY_PATH}: no entities to validate against")
    keys = {str(entity["entity_key"]) for entity in entities if "entity_key" in entity}
    if not keys:
        raise ConceptRegistryError(f"{DEVATA_REGISTRY_PATH}: no entity_key values found")
    return frozenset(keys)


def load_ambiguous_aliases(
    project_root: Path, *, registry_path: Path | None = None
) -> dict[tuple[str, str], str]:
    """Alias strings the registry declares ambiguous, mapped to the recorded reason.

    Keyed by ``(kind, alias)`` where kind is ``"sa"`` or ``"en"``. These are excluded from
    matching wherever they appear, and are exempt from the one-concept-per-alias rule --
    that is the whole point of the list. An ambiguous alias that is simply deleted looks
    like an oversight; one recorded here is a decision with a reason attached.
    """
    document = _read_yaml(project_root / (registry_path or CONCEPT_REGISTRY_PATH))
    declared = document.get("ambiguous_aliases") or []
    if not isinstance(declared, list):
        raise ConceptRegistryError("ambiguous_aliases must be a list")
    out: dict[tuple[str, str], str] = {}
    for entry in declared:
        kind = str(entry.get("kind", ""))
        alias = str(entry.get("alias", ""))
        reason = str(entry.get("reason", "")).strip()
        if kind not in {"sa", "en"}:
            raise ConceptRegistryError(f"ambiguous alias {alias!r}: kind must be 'sa' or 'en'")
        if not alias or not reason:
            raise ConceptRegistryError("every ambiguous alias needs both an alias and a reason")
        out[kind, alias] = reason
    return out


def load_non_triggering_aliases(
    project_root: Path, *, registry_path: Path | None = None
) -> dict[tuple[str, str, str], str]:
    """Aliases a concept owns that may not assert it alone, mapped to the recorded reason.

    Keyed by ``(concept_id, kind, alias)``. The scoping is the whole difference from
    :func:`load_ambiguous_aliases`: an ambiguous alias is contested between concepts and
    withdrawn from all of them, while one of these is uncontested and simply too weak a
    surface to carry the concept it belongs to. The same string may be perfectly sound
    elsewhere, so withdrawing it globally would destroy evidence that is not in question.

    Owner decision, section 3. The alias keeps its place in the concept's ``aliases_sa``
    in the registry file and reaches the row as ``non_triggering_aliases_sa``, so search,
    candidate generation, audit and manual review still see it. Only its authority to
    create a ``MENTIONS_ENTITY`` or ``ABOUT_CONCEPT`` edge is removed.
    """
    document = _read_yaml(project_root / (registry_path or CONCEPT_REGISTRY_PATH))
    declared = document.get("non_triggering_aliases") or []
    if not isinstance(declared, list):
        raise ConceptRegistryError("non_triggering_aliases must be a list")
    out: dict[tuple[str, str, str], str] = {}
    for entry in declared:
        concept_id = str(entry.get("concept_id", "")).strip()
        kind = str(entry.get("kind", ""))
        alias = str(entry.get("alias", ""))
        reason = str(entry.get("reason", "")).strip()
        if kind not in {"sa", "en"}:
            raise ConceptRegistryError(f"non-triggering alias {alias!r}: kind must be 'sa' or 'en'")
        if not concept_id or not alias or not reason:
            raise ConceptRegistryError(
                "every non-triggering alias needs a concept_id, an alias and a reason: a "
                "withdrawal with no stated measurement is indistinguishable from an oversight"
            )
        out[concept_id, kind, alias] = reason
    return out


def _require_text(concept_id: str, field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConceptRegistryError(f"{concept_id}: {field} must be a non-empty string")
    return " ".join(value.split())


def _alias_list(concept_id: str, field: str, value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ConceptRegistryError(f"{concept_id}: {field} must be a list")
    aliases: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConceptRegistryError(f"{concept_id}: {field} contains an empty alias")
        alias = item.strip()
        if alias in aliases:
            raise ConceptRegistryError(f"{concept_id}: {field} repeats {alias!r}")
        aliases.append(alias)
    return tuple(aliases)


def _check_acyclic(parents: Mapping[str, tuple[str, ...]]) -> None:
    """Raise if ``broader`` contains a cycle, naming the cycle.

    A cycle here is not a hypothetical. ``broader`` is written by hand across a hundred
    entries, and a graph in which fire is a kind of light is a kind of fire terminates no
    traversal: every ancestor query over it either loops forever or silently truncates, and
    the second failure mode is the one that reaches production.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict.fromkeys(parents, WHITE)
    for start in sorted(parents):
        if colour[start] != WHITE:
            continue
        stack: list[tuple[str, int]] = [(start, 0)]
        path: list[str] = []
        colour[start] = GREY
        path.append(start)
        while stack:
            node, index = stack[-1]
            ancestors = parents[node]
            if index >= len(ancestors):
                stack.pop()
                colour[node] = BLACK
                path.pop()
                continue
            stack[-1] = (node, index + 1)
            parent = ancestors[index]
            if colour[parent] == GREY:
                cycle = " -> ".join([*path[path.index(parent) :], parent])
                raise ConceptRegistryError(f"broader forms a cycle: {cycle}")
            if colour[parent] == WHITE:
                colour[parent] = GREY
                path.append(parent)
                stack.append((parent, 0))


def load_concepts(
    project_root: Path,
    *,
    allowed_node_types: frozenset[str] | None = None,
    registry_path: Path | None = None,
) -> tuple[ConceptRow, ...]:
    """Parse and validate ``data/registry/concepts.yaml``.

    ``allowed_node_types`` defaults to the frozen
    :class:`~vedagraph.semantic.ontology.SemanticNodeType` whitelist. Knowledge Model V2
    passes a wider set, because it adds entity types the frozen enum deliberately does not
    grow to hold -- ``HUMAN_CONCERN``, ``CONDITION``, ``CROP`` and the rest. It is injected
    rather than imported so that the enrichment layer keeps depending only on the semantic
    ontology, and a V2 type cannot leak into a V1 rebuild by accident.

    Every check below exists because the failure it catches is silent otherwise. A
    misspelled ``node_type`` produces a node the ontology does not know; an unresolvable
    ``broader`` produces an edge to nothing; a duplicated alias produces a concept
    assignment decided by dict ordering; a mistyped devata key produces an orphan edge
    between the two ontologies this layer exists to keep apart. None of those raise on
    their own, and all of them look like ordinary output.

    Returned sorted by ``concept_id``, with each row's alias lists sorted, so two runs over
    the same file produce byte-identical rows regardless of how the file is arranged.
    """
    path = registry_path or CONCEPT_REGISTRY_PATH
    document = _read_yaml(project_root / path)
    entries = document.get("concepts")
    if not isinstance(entries, list) or not entries:
        raise ConceptRegistryError(f"{path}: no concepts defined")
    if len(entries) > MAX_CONCEPT_NODES:
        raise ConceptRegistryError(
            f"{len(entries)} concepts exceeds MAX_CONCEPT_NODES={MAX_CONCEPT_NODES}. "
            "The concept layer is deliberately small; a lexicon belongs in the Lemma layer."
        )

    ambiguous = load_ambiguous_aliases(project_root, registry_path=path)
    non_triggering = load_non_triggering_aliases(project_root, registry_path=path)
    devata_keys = _devata_keys(project_root)
    node_types = (
        set(allowed_node_types)
        if allowed_node_types
        else {str(member) for member in SemanticNodeType}
    )

    rows: list[ConceptRow] = []
    ids: set[str] = set()
    claimed_sa: dict[str, str] = {}
    claimed_en: dict[str, str] = {}
    parents: dict[str, tuple[str, ...]] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            raise ConceptRegistryError("every concept must be a mapping")
        concept_id = str(entry.get("concept_id", "")).strip()
        if not CONCEPT_ID_PATTERN.match(concept_id):
            raise ConceptRegistryError(
                f"{concept_id!r} is not a valid concept id; expected VG:CONCEPT:<UPPER-KEBAB>"
            )
        if concept_id in ids:
            raise ConceptRegistryError(f"duplicate concept_id {concept_id}")
        ids.add(concept_id)

        node_type = str(entry.get("node_type", ""))
        if node_type not in node_types:
            raise ConceptRegistryError(
                f"{concept_id}: node_type {node_type!r} is not an allowed entity type. "
                f"Allowed: {', '.join(sorted(node_types))}"
            )

        aliases_sa = _alias_list(concept_id, "aliases_sa", entry.get("aliases_sa"))
        aliases_en = _alias_list(concept_id, "aliases_en", entry.get("aliases_en"))
        aliases_sa = tuple(a for a in aliases_sa if ("sa", a) not in ambiguous)
        aliases_en = tuple(a for a in aliases_en if ("en", a) not in ambiguous)
        # Withdrawn from assertion, kept for search. Split before the one-concept-per-alias
        # check below so that a withdrawn form cannot claim ownership of a surface it is no
        # longer allowed to assert.
        withdrawn_sa = tuple(a for a in aliases_sa if (concept_id, "sa", a) in non_triggering)
        withdrawn_en = tuple(a for a in aliases_en if (concept_id, "en", a) in non_triggering)
        aliases_sa = tuple(a for a in aliases_sa if a not in withdrawn_sa)
        aliases_en = tuple(a for a in aliases_en if a not in withdrawn_en)
        if not aliases_sa and not aliases_en:
            raise ConceptRegistryError(
                f"{concept_id}: no usable alias, so no passage can ever reach this concept"
            )

        for alias in aliases_sa:
            folded = fold_alias(alias)
            if not folded:
                raise ConceptRegistryError(f"{concept_id}: alias {alias!r} folds to nothing")
            owner = claimed_sa.get(folded)
            if owner is not None and owner != concept_id:
                raise ConceptRegistryError(
                    f"Sanskrit alias {alias!r} (folded {folded!r}) is claimed by both {owner} "
                    f"and {concept_id}. Declare it under ambiguous_aliases or delete it: an "
                    "alias shared by two concepts is decided by file order, not by evidence."
                )
            claimed_sa[folded] = concept_id

        for alias in aliases_en:
            if not ENGLISH_ALIAS_PATTERN.match(alias):
                raise ConceptRegistryError(
                    f"{concept_id}: English alias {alias!r} must be one lower-case token "
                    "(letters and internal hyphens only)"
                )
            owner = claimed_en.get(alias)
            if owner is not None and owner != concept_id:
                raise ConceptRegistryError(
                    f"English alias {alias!r} is claimed by both {owner} and {concept_id}. "
                    "Declare it under ambiguous_aliases or delete it."
                )
            claimed_en[alias] = concept_id

        broader = _alias_list(concept_id, "broader", entry.get("broader"))
        if concept_id in broader:
            raise ConceptRegistryError(f"{concept_id}: is listed as its own broader concept")
        parents[concept_id] = broader

        related = _alias_list(concept_id, "related_devatas", entry.get("related_devatas"))
        for key in related:
            if key not in devata_keys:
                raise ConceptRegistryError(
                    f"{concept_id}: related devata {key!r} is not in {DEVATA_REGISTRY_PATH}. "
                    "A deity key that does not resolve creates an orphan edge between the "
                    "concept and devata ontologies, which is the one thing this layer must "
                    "not do."
                )

        rows.append(
            ConceptRow(
                concept_id=concept_id,
                preferred_label_sa=_require_text(
                    concept_id, "preferred_label_sa", entry.get("preferred_label_sa")
                ),
                preferred_label_en=_require_text(
                    concept_id, "preferred_label_en", entry.get("preferred_label_en")
                ),
                node_type=node_type,
                aliases_sa=tuple(sorted(aliases_sa)),
                aliases_en=tuple(sorted(aliases_en)),
                broader=tuple(sorted(broader)),
                definition=_require_text(concept_id, "definition", entry.get("definition")),
                related_devatas=tuple(sorted(related)),
                # Carried through, not validated here. A CONDITION must have a kind, but
                # whether an entity IS a condition is not settled until
                # vedagraph.domain.registry applies NODE_TYPE_OVERRIDES: RAKSAS-DEMON is
                # authored CONCEPT and retyped to CONDITION there. Validating on the
                # authored type would let exactly the demon through -- which is the entity
                # the taxonomy exists to keep out of the disease list. The check therefore
                # lives at the point where the retype is known, and this layer keeps
                # depending only on the semantic ontology.
                condition_kind=str(entry.get("condition_kind", "") or "").strip(),
                non_triggering_aliases_sa=tuple(sorted(withdrawn_sa)),
                non_triggering_aliases_en=tuple(sorted(withdrawn_en)),
            )
        )

    for concept_id, broader in parents.items():
        for parent in broader:
            if parent not in ids:
                raise ConceptRegistryError(
                    f"{concept_id}: broader concept {parent!r} does not exist"
                )
    _check_acyclic(parents)

    return tuple(sorted(rows, key=lambda row: row.concept_id))


def _registry_provenance(method: str, concept: ConceptRow) -> Provenance:
    return Provenance(
        trust=TrustClass.SOURCE_EXPLICIT,
        method=method,
        score=1.0,
        evidence=(
            EvidenceSpan(
                locator=concept.concept_id,
                surface=_REGISTRY_SURFACE,
                quote=concept.definition,
            ),
        ),
        state=AssertionState.ACCEPTED,
    )


def concept_hierarchy_rows(concepts: Sequence[ConceptRow]) -> list[ConceptEdgeRow]:
    """``BROADER_THAN`` edges, from the broader concept to the narrower one.

    The registry validates the graph as acyclic at load, so this function only projects it.
    The direction follows the predicate's own definition -- "the subject is a genuine
    superordinate" -- which means the *parent* is the subject even though the child is the
    row that declares the relationship.
    """
    predicate = str(StructuralPredicate.BROADER_THAN)
    check_signature(predicate, NodeKind.CONCEPT, NodeKind.CONCEPT)
    rows = [
        ConceptEdgeRow(
            predicate=predicate,
            subject_key=parent,
            object_key=concept.concept_id,
            subject_kind=str(NodeKind.CONCEPT),
            object_kind=str(NodeKind.CONCEPT),
            provenance=_registry_provenance(_REGISTRY_METHOD_BROADER, concept),
        )
        for concept in concepts
        for parent in concept.broader
    ]
    return sorted(rows, key=lambda row: (row.subject_key, row.object_key))


def devata_association_rows(concepts: Sequence[ConceptRow]) -> list[ConceptEdgeRow]:
    """``DEVATA_ASSOCIATED_WITH`` edges, from a deity to a concept it is associated with.

    This is the only edge between the devata ontology and the concept ontology, and it is
    deliberately the weakest claim available: an association, not an identity. "Agni is
    fire" would be ``REPRESENTS``, which the frozen ontology refuses by name.
    """
    predicate = str(StructuralPredicate.DEVATA_ASSOCIATED_WITH)
    check_signature(predicate, NodeKind.DEVATA, NodeKind.CONCEPT)
    rows = [
        ConceptEdgeRow(
            predicate=predicate,
            subject_key=devata,
            object_key=concept.concept_id,
            subject_kind=str(NodeKind.DEVATA),
            object_kind=str(NodeKind.CONCEPT),
            provenance=_registry_provenance(_REGISTRY_METHOD_DEVATA, concept),
        )
        for concept in concepts
        for devata in concept.related_devatas
    ]
    return sorted(rows, key=lambda row: (row.subject_key, row.object_key))


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConceptIndex:
    """The lexicon inverted for lookup, built once per run.

    ``token`` and ``english`` are one-to-one because :func:`load_concepts` refuses a shared
    alias; that validation is what makes a plain dict correct here instead of a
    dict-of-lists with a tie-break rule nobody would remember to keep deterministic.
    """

    token: dict[str, str]
    sandhi: tuple[tuple[str, str], ...]
    english: dict[str, str]

    @property
    def alias_counts(self) -> dict[str, int]:
        return {
            "sanskrit_token": len(self.token),
            "sanskrit_sandhi": len(self.sandhi),
            "english": len(self.english),
        }


def build_index(concepts: Iterable[ConceptRow]) -> ConceptIndex:
    """Invert the lexicon into the three lookup structures matching needs."""
    token: dict[str, str] = {}
    sandhi: list[tuple[str, str]] = []
    english: dict[str, str] = {}
    for concept in concepts:
        for alias in concept.aliases_sa:
            folded = fold_alias(alias)
            token[folded] = concept.concept_id
            eligible = (
                len(folded) >= MIN_SANDHI_ALIAS_CHARS and alias not in SANDHI_SUPPRESSED_ALIASES
            )
            if eligible:
                sandhi.append((folded, concept.concept_id))
        for alias in concept.aliases_en:
            english[alias] = concept.concept_id
    return ConceptIndex(token=token, sandhi=tuple(sorted(sandhi)), english=english)


@dataclass
class _Hits:
    """Accumulated evidence for one (passage, concept) pair on one evidence path."""

    aliases: set[str]
    quote: str
    surface: str

    def add(self, alias: str, quote: str, surface: str) -> None:
        if alias not in self.aliases:
            self.aliases.add(alias)
        if not self.quote:
            self.quote = quote
            self.surface = surface


def _banded_score(base: float, ceiling: float, alias_count: int) -> float:
    return min(ceiling, base + _ALIAS_STEP * (alias_count - 1))


def _sanskrit_token_hits(mantra: MantraRecord, index: ConceptIndex) -> dict[str, _Hits]:
    tokens = mantra.surfaces.tokens
    found: dict[str, _Hits] = {}
    for position, token in enumerate(tokens):
        concept_id = index.token.get(token)
        if concept_id is None:
            continue
        window = tokens[
            max(0, position - _SANSKRIT_CONTEXT_TOKENS) : position + _SANSKRIT_CONTEXT_TOKENS + 1
        ]
        hits = found.get(concept_id)
        if hits is None:
            found[concept_id] = _Hits({token}, " ".join(window), "script_folded")
        else:
            hits.add(token, " ".join(window), "script_folded")
    return found


def _sanskrit_sandhi_hits(
    mantra: MantraRecord, index: ConceptIndex, already: set[str]
) -> dict[str, _Hits]:
    """Substring pass over the boundary-free surface, for concepts the tokens missed.

    Restricted to concepts with no token hit so that the two Sanskrit paths never both
    claim one assertion: a concept reached by both is reached by the stronger one, and
    reporting the weaker path alongside it would misdescribe the evidence.
    """
    text = mantra.surfaces.sandhi_insensitive
    found: dict[str, _Hits] = {}
    for alias, concept_id in index.sandhi:
        if concept_id in already:
            continue
        position = text.find(alias)
        if position < 0:
            continue
        quote = text[
            max(0, position - _SANDHI_CONTEXT_CHARS) : position + len(alias) + _SANDHI_CONTEXT_CHARS
        ]
        hits = found.get(concept_id)
        if hits is None:
            found[concept_id] = _Hits({alias}, quote, "sandhi_insensitive")
        else:
            hits.add(alias, quote, "sandhi_insensitive")
    return found


def _english_hits(mantra: MantraRecord, index: ConceptIndex) -> dict[str, _Hits]:
    found: dict[str, _Hits] = {}
    for translation in mantra.translations:
        lowered = translation.lower()
        for match in ENGLISH_TOKEN_PATTERN.finditer(lowered):
            concept_id = index.english.get(match.group())
            if concept_id is None:
                continue
            start = max(0, match.start() - _ENGLISH_CONTEXT_CHARS)
            end = match.end() + _ENGLISH_CONTEXT_CHARS
            quote = " ".join(translation[start:end].split())
            hits = found.get(concept_id)
            if hits is None:
                found[concept_id] = _Hits({match.group()}, quote, "translation_en")
            else:
                hits.add(match.group(), quote, "translation_en")
    return found


def _assertion(
    mantra: MantraRecord,
    concept_id: str,
    contributions: list[tuple[str, float, _Hits]],
    identity: str,
) -> tuple[float, ConceptAssertionRow]:
    contributions.sort(key=lambda item: item[0])
    paths = [path for path, _, _ in contributions]
    score = max(component for _, component, _ in contributions)
    sanskrit = any(path in {_PATH_TOKEN, _PATH_SANDHI} for path in paths)
    if sanskrit and _PATH_ENGLISH in paths:
        score = min(_SCORE_CEILING, score + _CORROBORATION_BONUS)
    # render_for_display on the way out, never before matching: the Sanskrit paths quote a
    # folded surface, and the fold's private-use sentinels are a comparison device that must
    # not reach a reader. Unrendered, 31.9% of this stage's evidence published an unassigned
    # code point that renders as nothing -- so `ṛtasya` appeared as `tasya`, a different word.
    evidence = tuple(
        EvidenceSpan(
            locator=mantra.passage_key,
            surface=hits.surface,
            quote=render_for_display(hits.quote),
        )
        for _, _, hits in contributions
    )
    matched = sorted({alias for _, _, hits in contributions for alias in hits.aliases})
    provenance = Provenance(
        trust=TrustClass.DETERMINISTIC_DERIVED,
        method=f"{_METHOD_ROOT}:{'+'.join(paths)}",
        score=score,
        evidence=evidence,
        state=AssertionState.ACCEPTED,
        run_id=identity,
        # Rendered for the same reason the quote is: a matched Sanskrit alias is a folded
        # string, and unrendered it publishes `pthivī` for `pṛthivī`.
        notes=f"matched aliases: {', '.join(render_for_display(a) for a in matched)}",
    )
    return score, ConceptAssertionRow(
        passage_key=mantra.passage_key,
        veda=mantra.veda,
        concept_id=concept_id,
        confidence=score,
        provenance=provenance,
    )


def assign_concepts(
    corpus: Corpus, concepts: Sequence[ConceptRow]
) -> tuple[list[ConceptAssertionRow], RunReport]:
    """Attach passages to concepts deterministically, with the span that supports each.

    No model is involved and none may be: this is the layer whose whole value is that it
    can be re-run and produce the same graph. Agent E's model layer writes
    ``LLM_EXTRACTED`` candidates elsewhere and does not touch these rows.

    The per-passage cap from :data:`~vedagraph.enrich.guards.MAX_CONCEPTS_PER_PASSAGE` is
    applied through :func:`~vedagraph.enrich.guards.top_k`, whose tie-break is the concept
    id rather than input order -- without that, two runs with identical scores would keep
    different concepts and the "reproducible" pipeline would not be. Everything dropped is
    counted in the report; a capped result and a small result must not look alike.
    """
    check_signature(str(StructuralPredicate.ABOUT_CONCEPT), NodeKind.PASSAGE, NodeKind.CONCEPT)
    index = build_index(concepts)
    identity = run_id(_STAGE, len(corpus.mantras), len(concepts), len(index.token))
    report = RunReport(stage=_STAGE)

    scored: list[tuple[float, ConceptAssertionRow]] = []
    #: (mantra, its candidate concepts) held between the two passes; see the cap below.
    pending: list[tuple[MantraRecord, dict[str, list[tuple[str, float, _Hits]]]]] = []
    #: How many passages each concept is attested on, corpus-wide. The cap's tie-break.
    attested: dict[str, int] = {}
    path_counts: dict[str, int] = {_PATH_TOKEN: 0, _PATH_SANDHI: 0, _PATH_ENGLISH: 0}
    covered: dict[str, set[str]] = {}
    translated: dict[str, int] = {}
    veda_totals: dict[str, int] = {}

    for mantra in corpus.mantras:
        veda_totals[mantra.veda] = veda_totals.get(mantra.veda, 0) + 1
        if mantra.has_translation:
            translated[mantra.veda] = translated.get(mantra.veda, 0) + 1

        token_hits = _sanskrit_token_hits(mantra, index)
        sandhi_hits = (
            _sanskrit_sandhi_hits(mantra, index, set(token_hits))
            if mantra.veda in SANDHI_MATCH_VEDAS
            else {}
        )
        english_hits = _english_hits(mantra, index)

        merged: dict[str, list[tuple[str, float, _Hits]]] = {}
        for concept_id, hits in token_hits.items():
            component = _banded_score(
                _SANSKRIT_TOKEN_BASE, _SANSKRIT_TOKEN_CEILING, len(hits.aliases)
            )
            merged.setdefault(concept_id, []).append((_PATH_TOKEN, component, hits))
        for concept_id, hits in sandhi_hits.items():
            component = _banded_score(_SANDHI_BASE, _SANDHI_CEILING, len(hits.aliases))
            merged.setdefault(concept_id, []).append((_PATH_SANDHI, component, hits))
        for concept_id, hits in english_hits.items():
            component = _banded_score(_ENGLISH_BASE, _ENGLISH_CEILING, len(hits.aliases))
            merged.setdefault(concept_id, []).append((_PATH_ENGLISH, component, hits))

        if not merged:
            continue

        pending.append((mantra, merged))
        for concept_id in merged:
            attested[concept_id] = attested.get(concept_id, 0) + 1

    # Second pass, because the per-passage cap needs a corpus-wide quantity to break ties
    # well. The scoring bands are coarse -- two English-evidence concepts on one passage
    # almost always tie exactly -- so the tie-break decides the outcome on 80.1% of capped
    # passages, and breaking it on the concept id alone means the alphabet decides. Measured
    # under that rule: kept concepts had mean alphabetical rank 27.8 of 89 and dropped ones
    # 60.0, and YAJNA-SACRIFICE was dropped 425 times and STOMA-PRAISE 380 times for no
    # reason but their initial letter.
    #
    # Rarity is the tie-break instead: of two equally-scored concepts, the one attested on
    # fewer passages says more about this passage. The concept id remains the final key, so
    # the result is still fully deterministic.
    for mantra, merged in pending:
        candidates: list[tuple[float, tuple[int, str]]] = []
        built: dict[str, tuple[float, ConceptAssertionRow]] = {}
        for concept_id, contributions in merged.items():
            score, row = _assertion(mantra, concept_id, contributions, identity)
            built[concept_id] = (score, row)
            candidates.append((score, (attested[concept_id], concept_id)))

        kept = top_k(candidates, MAX_CONCEPTS_PER_PASSAGE)
        if kept.dropped:
            report.cap("concepts_per_passage", kept.dropped)
            report.cap(f"concepts_per_passage:{mantra.veda}", kept.dropped)
        for _, concept_id in kept.kept:
            score, row = built[concept_id]
            scored.append((score, row))
            covered.setdefault(mantra.veda, set()).add(mantra.passage_key)
            for path, _, _ in merged[concept_id]:
                path_counts[path] += 1

    scored.sort(key=lambda item: (-item[0], item[1].passage_key, item[1].concept_id))
    if len(scored) > MAX_CONCEPT_ASSERTIONS:
        report.cap("global_assertion_cap", len(scored) - MAX_CONCEPT_ASSERTIONS)
        scored = scored[:MAX_CONCEPT_ASSERTIONS]

    rows = sorted((row for _, row in scored), key=lambda row: (row.passage_key, row.concept_id))
    report.produced = len(rows)
    report.notes = {
        "concepts": len(concepts),
        "aliases": index.alias_counts,
        "assertions_by_evidence_path": dict(sorted(path_counts.items())),
        "sandhi_match_vedas": sorted(SANDHI_MATCH_VEDAS),
        "coverage_by_veda": {
            veda: {
                "mantras": veda_totals[veda],
                "with_translation": translated.get(veda, 0),
                "with_concept": len(covered.get(veda, set())),
                "coverage": round(len(covered.get(veda, set())) / veda_totals[veda], 4),
            }
            for veda in sorted(veda_totals)
        },
        "distinct_concepts_used": len({row.concept_id for row in rows}),
    }
    return rows, report
