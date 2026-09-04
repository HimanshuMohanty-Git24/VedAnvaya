"""The lexical alias registry, and the fail-closed matcher built from it.

Three rules govern this module, and none of them has an exception.

**No substring matching.** Nothing here ever asks whether an alias string occurs
inside a mantra. Sandhi, compounding and short names make that test produce
false positives at a rate no amount of later filtering repairs. A mention starts
from an annotated token and its lemma, never from scanning text.

**No fuzzy resolution.** :func:`propose_alias_candidates` exists so that
similarity has somewhere to go that is not a graph edge. It writes
``LexicalAliasCandidate`` records for a human. It cannot write an alias, and an
alias it proposes has no effect until a person moves it into the registry with
``review_status: ACCEPTED``.

**Fail closed on ambiguity.** If one lemma reaches two accepted entities, the
matcher returns ``AMBIGUOUS_LEXICAL_ENTITY`` and no edge is produced, however
frequent the lemma is.

Two further rules were added in policy v2, both to close false-positive classes the
v1 audit found and neither of them contextual:

**The lemma must be the alias's lemma.** Matching is by the annotation's stable lemma
id, and the annotators give a derived stem the *base* word's id: ``índratama-`` "most
Indra-like" and ``tákṣya-`` "to be fashioned" carry ``lemma_indra_1708`` and
``lemma_tArkzya_3741``. A shared id is therefore necessary but not sufficient; the
lemma string must agree too, or the match is ``SUPPRESSED_LEMMA_MISMATCH``.

**Declared morphology constraints are enforced.** An alias may state which
part-of-speech, gender, number or case readings of its lemma name the entity. This is
what lets ``sárasvant-`` reach Sarasvatī when feminine and Sarasvant when masculine
without any appeal to what a verse is about. Constraints are declared only where a
lemma really is shared; most aliases declare none.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from vedagraph.identity import uuid_for_urn
from vedagraph.lexical.morphology import ANNOTATION_LAYER_ID
from vedagraph.models.enums import (
    KnowledgeEntityType,
    LexicalAliasType,
    LexicalMatchStatus,
    MentionMethod,
    ReviewStatus,
)
from vedagraph.models.knowledge import KnowledgeEntity
from vedagraph.models.lexical import (
    LexicalAlias,
    LexicalAliasCandidate,
    MorphologyToken,
)
from vedagraph.normalize import fold_transcription, normalize_nfc, strip_vedic_accents

LEXICAL_ALIAS_FILE = "lexical_aliases.yaml"
MENTION_POLICY_VERSION = "rigveda-lexical-mention-policy-v2"

#: Entity families v1 accepts lexical aliases for. Ṛṣi is excluded: the canonical
#: Ṛṣi registry stores patronymic-plus-name labels (``rāhūgaṇo gotamaḥ``), and
#: reaching a single Ṛṣi from a bare lemma would mean decomposing those labels by
#: name grammar, which is exactly the inference ADR-013 forbids without a source.
ALIAS_ENTITY_TYPES: frozenset[KnowledgeEntityType] = frozenset({KnowledgeEntityType.DEVATA})


def match_key(value: str) -> str:
    """The single comparison surface used for every lexical string in this layer.

    NFC, Vedic accents removed, IAST/ISO 15919 spellings folded onto shared
    sentinels, case folded. Stem notation (``-``, ``√``) is stripped by the
    morphology parser before this is applied.
    """
    folded = fold_transcription(strip_vedic_accents(normalize_nfc(value)))
    return " ".join(folded.casefold().split()).strip("-").strip()


def lemma_match_keys(normalized_lemma: str) -> list[str]:
    """Comparison keys for one lemma, splitting the annotation's ``~`` alternants.

    ``dyú- ~ div-`` is one lexical entry the annotators wrote two ways. Both
    spellings are indexed; neither is treated as a different word.
    """
    keys = []
    for part in normalized_lemma.split("~"):
        key = match_key(part.strip().strip("-").strip())
        if key and key not in keys:
            keys.append(key)
    return keys


def alias_identity(entity_key: str, lemma: str) -> tuple[str, str]:
    """Deterministic key and URN for one lexical alias."""
    key = f"{entity_key}|{ANNOTATION_LAYER_ID}|{match_key(lemma)}"
    urn = f"urn:vedagraph:lexicalalias:{ANNOTATION_LAYER_ID.lower()}:{key.lower()}"
    return key, urn


def load_lexical_aliases(
    registry_root: Path,
    *,
    entities: dict[str, KnowledgeEntity],
) -> list[LexicalAlias]:
    """Read the reviewed registry, validating every row against the entity registry.

    An alias naming an entity that does not exist is an error, not a warning: it
    would silently disappear and take its suppression rule with it.
    """
    path = registry_root / LEXICAL_ALIAS_FILE
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    declared = str(document.get("policy_version", ""))
    if declared != MENTION_POLICY_VERSION:
        raise ValueError(
            f"{path} declares policy_version {declared!r}, expected {MENTION_POLICY_VERSION!r}"
        )
    aliases: list[LexicalAlias] = []
    seen: set[str] = set()
    for row in document.get("aliases", []):
        entity_key = str(row["entity_key"])
        entity = entities.get(entity_key)
        if entity is None:
            raise ValueError(f"{path}: lexical alias names unknown entity {entity_key}")
        if entity.entity_type not in ALIAS_ENTITY_TYPES:
            raise ValueError(
                f"{path}: {entity_key} is a {entity.entity_type.value}; "
                f"v1 accepts lexical aliases for {sorted(t.value for t in ALIAS_ENTITY_TYPES)} only"
            )
        lemma = str(row["lemma"])
        key, urn = alias_identity(entity_key, lemma)
        if key in seen:
            raise ValueError(f"{path}: duplicate lexical alias {key}")
        seen.add(key)
        aliases.append(
            LexicalAlias(
                alias_id=uuid_for_urn(urn),
                alias_key=key,
                entity_key=entity_key,
                entity_type=entity.entity_type,
                lemma=lemma,
                normalized_lemma=match_key(lemma),
                lemma_ids=sorted(str(item) for item in row.get("lemma_ids", [])),
                alias_type=LexicalAliasType(row["alias_type"]),
                review_status=ReviewStatus(row["review_status"]),
                evidence=str(row["evidence"]),
                notes=str(row["notes"]) if row.get("notes") else None,
                allowed_pos=[str(item) for item in row.get("allowed_pos", [])],
                allowed_gender=[str(item) for item in row.get("allowed_gender", [])],
                allowed_number=[str(item) for item in row.get("allowed_number", [])],
                allowed_case=[str(item) for item in row.get("allowed_case", [])],
                forbidden_features=[str(item) for item in row.get("forbidden_features", [])],
            )
        )
    return sorted(aliases, key=lambda alias: alias.alias_key)


#: Which morphology feature each ``allowed_*`` list constrains. ``allowed_pos`` is not
#: here: part of speech is a token field, not a morphosyntax feature.
_FEATURE_FIELDS: tuple[tuple[str, str], ...] = (
    ("gender", "allowed_gender"),
    ("number", "allowed_number"),
    ("case", "allowed_case"),
)


def disqualify(
    alias: LexicalAlias, token: MorphologyToken
) -> tuple[LexicalMatchStatus, str] | None:
    """Why this token may not evidence this alias, or ``None`` if it may.

    Two checks, in order. Both are deterministic properties of the annotation record;
    neither looks at the mantra's meaning, its neighbours or its traditional metadata.
    """
    alias_keys = lemma_match_keys(alias.normalized_lemma)
    token_keys = lemma_match_keys(token.normalized_lemma)
    if alias_keys and not set(alias_keys) & set(token_keys):
        # Shared lemma id, different word: a derived stem carrying the base entry's id.
        return (
            LexicalMatchStatus.SUPPRESSED_LEMMA_MISMATCH,
            f"token lemma {token.lemma!r} is not the alias lemma {alias.lemma!r}",
        )
    if alias.allowed_pos and (token.part_of_speech or "") not in alias.allowed_pos:
        return (
            LexicalMatchStatus.SUPPRESSED_FEATURE_CONSTRAINT,
            f"part of speech {token.part_of_speech!r} is not in {alias.allowed_pos}",
        )
    for feature, field_name in _FEATURE_FIELDS:
        allowed: list[str] = getattr(alias, field_name)
        if not allowed:
            continue
        value = token.morphological_features.get(feature)
        if value not in allowed:
            # A token with no value for a constrained feature fails closed.
            return (
                LexicalMatchStatus.SUPPRESSED_FEATURE_CONSTRAINT,
                f"{feature}={value!r} is not in {allowed}",
            )
    for pair in alias.forbidden_features:
        feature, _, value = pair.partition("=")
        if token.morphological_features.get(feature) == value:
            return (
                LexicalMatchStatus.SUPPRESSED_FEATURE_CONSTRAINT,
                f"{pair} is registered as disqualifying",
            )
    return None


@dataclass(frozen=True)
class AliasMatch:
    """The outcome of matching one token. ``alias`` is set only on ``MATCHED``."""

    status: LexicalMatchStatus
    alias: LexicalAlias | None = None
    method: MentionMethod | None = None
    candidates: tuple[str, ...] = ()
    reason: str = ""


class LexicalMatcher:
    """Resolves an annotated token to at most one canonical entity, or to nothing.

    Matching is attempted strongest first:

    1. ``LEMMA_ID_EXACT`` - the token and the alias share the annotation layer's own
       stable lemma identifier. No string is compared at all.
    2. ``LEMMA_NORMALIZED_EXACT`` - the token's lemma and the alias lemma have the same
       comparison key. Used only for aliases that declare no lemma id.

    Surface matching is deliberately not implemented. Every token in this layer carries
    a lemma, so surface matching would add risk and no recall.
    """

    def __init__(self, aliases: list[LexicalAlias]) -> None:
        self._suppressed_ids: set[str] = set()
        self._suppressed_lemmas: set[str] = set()
        self._unreviewed_ids: dict[str, list[str]] = defaultdict(list)
        by_id: dict[str, list[LexicalAlias]] = defaultdict(list)
        by_lemma: dict[str, list[LexicalAlias]] = defaultdict(list)
        for alias in aliases:
            if alias.alias_type is LexicalAliasType.DO_NOT_MATCH:
                # A suppression rule applies whatever its review status would allow.
                self._suppressed_ids.update(alias.lemma_ids)
                self._suppressed_lemmas.add(alias.normalized_lemma)
                continue
            if not alias.may_produce_mention:
                for lemma_id in alias.lemma_ids:
                    self._unreviewed_ids[lemma_id].append(alias.entity_key)
                continue
            for lemma_id in alias.lemma_ids:
                by_id[lemma_id].append(alias)
            if not alias.lemma_ids:
                by_lemma[alias.normalized_lemma].append(alias)
        self._by_id = dict(by_id)
        self._by_lemma = dict(by_lemma)

    @property
    def accepted_alias_count(self) -> int:
        distinct = {alias.alias_key for group in self._by_id.values() for alias in group}
        distinct |= {alias.alias_key for group in self._by_lemma.values() for alias in group}
        return len(distinct)

    @property
    def suppressed_lemma_id_count(self) -> int:
        return len(self._suppressed_ids)

    def match(self, token: MorphologyToken) -> AliasMatch:
        if self._suppressed_ids.intersection(token.lemma_ids):
            return AliasMatch(
                LexicalMatchStatus.SUPPRESSED_DO_NOT_MATCH,
                reason="lemma is registered DO_NOT_MATCH",
            )
        keys = lemma_match_keys(token.normalized_lemma)
        if self._suppressed_lemmas.intersection(keys):
            return AliasMatch(
                LexicalMatchStatus.SUPPRESSED_DO_NOT_MATCH,
                reason="lemma is registered DO_NOT_MATCH",
            )

        hits = {
            alias.alias_key: alias
            for lemma_id in token.lemma_ids
            for alias in self._by_id.get(lemma_id, ())
        }
        method = MentionMethod.LEMMA_ID_EXACT
        if not hits:
            hits = {alias.alias_key: alias for key in keys for alias in self._by_lemma.get(key, ())}
            method = MentionMethod.LEMMA_NORMALIZED_EXACT

        rejections = {key: disqualify(alias, token) for key, alias in hits.items()}
        surviving = {key: alias for key, alias in hits.items() if rejections[key] is None}
        if hits and not surviving:
            # Every alias this token reached rules it out. Report the first reason in
            # registry order so the outcome is stable across rebuilds.
            first = next(r for key in sorted(hits) if (r := rejections[key]) is not None)
            return AliasMatch(first[0], candidates=tuple(sorted(hits)), reason=first[1])
        hits = surviving

        entities = {alias.entity_key for alias in hits.values()}
        if len(entities) > 1:
            return AliasMatch(
                LexicalMatchStatus.AMBIGUOUS_LEXICAL_ENTITY,
                candidates=tuple(sorted(entities)),
                reason="one lemma reaches more than one accepted entity",
            )
        if len(entities) == 1:
            if len(token.lemma_ids) > 1 and method is MentionMethod.LEMMA_ID_EXACT:
                # The annotators themselves could not choose between two lexical
                # entries for this token. That is source ambiguity, not ours to settle.
                unmatched = [
                    lemma_id for lemma_id in token.lemma_ids if lemma_id not in self._by_id
                ]
                if unmatched:
                    return AliasMatch(
                        LexicalMatchStatus.AMBIGUOUS_SOURCE_LEMMA,
                        candidates=tuple(sorted(entities)),
                        reason=(
                            "the annotation layer assigns this token several lexical "
                            "entries and only some reach a canonical entity"
                        ),
                    )
            return AliasMatch(
                LexicalMatchStatus.MATCHED, alias=next(iter(hits.values())), method=method
            )

        pending = sorted(
            {
                entity_key
                for lemma_id in token.lemma_ids
                for entity_key in self._unreviewed_ids.get(lemma_id, ())
            }
        )
        if pending:
            return AliasMatch(
                LexicalMatchStatus.AMBIGUOUS_LEXICAL_ENTITY,
                candidates=tuple(pending),
                reason="lexical alias exists but is not reviewed as ACCEPTED",
            )
        return AliasMatch(LexicalMatchStatus.NO_LEXICAL_ALIAS, reason="no lexical alias registered")


@dataclass
class _LemmaUse:
    """Where one lemma occurs, used only to size a review candidate."""

    lemma: str
    token_count: int = 0
    mantras: set[str] = field(default_factory=set)
    lemma_ids: set[str] = field(default_factory=set)


#: The deterministic rules used to *propose* a lemma for review. They compare a
#: registry label with an annotated lemma and nothing else; they never create an alias.
CANDIDATE_RULE_VERSION = "lexical-alias-candidate-proposal-v1"


def propose_alias_candidates(
    tokens: list[MorphologyToken],
    entities: dict[str, KnowledgeEntity],
    *,
    existing: list[LexicalAlias],
) -> list[LexicalAliasCandidate]:
    """Propose lemma/entity pairings a reviewer should look at. Creates no edges.

    Two rules only, both exact after normalization:

    ``IDENTITY``
        the entity's preferred label and the lemma have the same comparison key.
    ``NOMINATIVE_VISARGA``
        the label is the lemma plus a final visarga, i.e. an a-stem nominative.

    Anything subtler (``uṣāḥ`` for ``uṣás-``, ``savitā`` for ``savitár-``) is a
    grammatical judgement and stays a human decision recorded in the registry.
    """
    inventory: dict[str, _LemmaUse] = {}
    for token in tokens:
        for key in lemma_match_keys(token.normalized_lemma):
            entry = inventory.setdefault(key, _LemmaUse(lemma=token.lemma))
            entry.token_count += 1
            entry.mantras.add(token.passage_key)
            entry.lemma_ids.update(token.lemma_ids)

    reviewed = {alias.entity_key for alias in existing}
    proposals: dict[str, LexicalAliasCandidate] = {}
    by_lemma: dict[str, list[str]] = defaultdict(list)
    for entity in entities.values():
        if entity.entity_type not in ALIAS_ENTITY_TYPES or entity.entity_key in reviewed:
            continue
        label = match_key(entity.preferred_label)
        rules = [(label, "IDENTITY")]
        if label.endswith("ḥ"):
            rules.append((label[:-1], "NOMINATIVE_VISARGA"))
        for lemma_key, rule in rules:
            use = inventory.get(lemma_key)
            if use is None:
                continue
            candidate_key = f"{entity.entity_key}|{lemma_key}"
            proposals[candidate_key] = LexicalAliasCandidate(
                candidate_key=candidate_key,
                entity_key=entity.entity_key,
                entity_type=entity.entity_type,
                entity_label=entity.preferred_label,
                lemma=use.lemma,
                normalized_lemma=lemma_key,
                lemma_ids=sorted(use.lemma_ids),
                proposal_rule=f"{CANDIDATE_RULE_VERSION}:{rule}",
                token_count=use.token_count,
                mantra_count=len(use.mantras),
            )
            by_lemma[lemma_key].append(entity.entity_key)
            break
    for candidate in proposals.values():
        candidate.competing_entity_keys = sorted(
            key for key in by_lemma[candidate.normalized_lemma] if key != candidate.entity_key
        )
    return sorted(proposals.values(), key=lambda item: item.candidate_key)
