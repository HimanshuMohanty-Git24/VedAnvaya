"""Semantic-role extraction over all four Saṃhitās — shared library.

Campaign section J, agent 9. Read-only against Neo4j; nothing here writes the graph.

Three derivations, deliberately never summed:

* ``MORPHOLOGY_RULE_CASE`` — the Rigveda, from the Zurich manual annotation. That
  annotation is morphology only: no HEAD, no DEPREL, no clause boundary. Roles are
  therefore read from case inside one metrical pada, which is a heuristic and is typed
  as one. ``action_root_map.yaml`` says exactly this in its own recommendations, point 8,
  and this module does not pretend otherwise.
* ``TREEBANK_DEPREL`` — the Atharvaveda and the Yajurveda, from DCS CoNLL-U, which for
  these two corpora carries a full dependency parse. A role read off ``nsubj``/``obj``/
  ``iobj``/``obl`` is better evidence than a role inferred from a case inside a pada, so
  the two non-Rigvedic corpora get the *stronger* instrument here. That asymmetry is
  reported rather than levelled.
* ``CROSS_VEDA_TEXT_IDENTITY`` — the Samaveda, and only where an Ārcika verse's letter
  skeleton is identical to a Rigvedic verse that already carries an analysis. Same
  letters, same morphology. Anything short of identity abstains.

The role vocabulary is ``data/registry/action_predicates.yaml``, unmodified. Two roles
the brief names are not in it and are emitted as declared proposals, counted apart:
SOURCE (ablative) and GOAL (an accusative under a motion predicate, whose own
``argument_frame`` has no PATIENT slot to put it in).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

# ---------------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------------

#: Above-marks that are a Vedic tone when they sit on a vowel and a *letter* when they sit
#: on a consonant. U+0301 is both the udātta and the palatal hook of ś, and that is not a
#: theoretical problem: a blanket strip of it folds the root aś- 'seek' onto as- 'be',
#: which invents a homonym collision, which then silently suppresses every predicate on
#: the folded key. Measured here at 936 Atharvavedic and 576 Yajurvedic finite verbs
#: before the guard was added.
_AMBIGUOUS_ABOVE = frozenset("́̀̂̈")

#: Above-marks that are always a tone, whatever they sit on.
_ALWAYS_TONE = frozenset(
    "॒॑॓॔᳐᳑᳒᳚᳛᳠᳡"
)

#: Bases that can carry a tone: the vowels, plus r and l when a below-mark has already
#: made them vocalic.
_VOWELS = frozenset("aeiou")
_BELOW = frozenset("̣̥")

_PUNCT = re.compile(r"[|।॥,.;:!?\"'()\[\]\-–—/\\*_=+~`^<>{}\d\s]+")

#: Vocalic liquids and the anusvara have two spellings across our sources: Zurich writes
#: the vocalic r as r + U+0325 (ring below), DCS as U+1E5B (r + dot below). Both denote
#: one sound, so a fold key must unify them or no root joins across the two annotations.
#:
#: Applied only to the letters r, l and m, and only to the *below* mark. The macron is
#: kept: r̥ and r̥̄ are different vowels, and folding them together merges kr̥- 'make'
#: (1,207 tokens, CREATES) with kr̥̄- 'praise'/'pour' (18 tokens), which again invents a
#: collision and cost 499 Atharvavedic and 51 Yajurvedic verbs before it was caught.
_RING_BELOW = re.compile(r"([rl])\u0325")
_ANUSVARA = re.compile(r"m[\u0307\u0323]")


def fold_liquids(text: str) -> str:
    """Unify the two spellings of the vocalic liquids and of the anusvāra.

    Zurich writes the vocalic r as r + U+0325 (ring below); DCS writes it as U+1E5B
    (r + dot below). One sound, two encodings, and no root joins across the two
    annotations until they are the same string. Vowel length survives.
    """
    decomposed = unicodedata.normalize("NFD", text)
    decomposed = _RING_BELOW.sub("\\1\u0323", decomposed)
    decomposed = _ANUSVARA.sub("m\u0323", decomposed)
    return unicodedata.normalize("NFC", decomposed)


def deaccent(text: str) -> str:
    """Drop tone marks, keep every mark that is part of a letter.

    A mark is a tone only where it can be one: U+0301 on a vowel is the udātta, on an s
    it is the letter ś. This distinction is the whole reason the function is not a
    one-liner.
    """
    out: list[str] = []
    base = ""
    below: set[str] = set()
    for char in unicodedata.normalize("NFD", text):
        if not unicodedata.combining(char):
            base, below = char.lower(), set()
            out.append(char)
            continue
        if char in _ALWAYS_TONE:
            continue
        if char in _BELOW:
            below.add(char)
            out.append(char)
            continue
        if char in _AMBIGUOUS_ABOVE and (
            base in _VOWELS or (base in "rl" and below & _BELOW)
        ):
            continue
        out.append(char)
    return "".join(out)


def transliterate_if_devanagari(text: str) -> str:
    if any(0x0900 <= ord(c) < 0x0980 for c in text):
        from indic_transliteration import sanscript

        text = text.replace("ॐ", "")
        # A colon-spelled visarga: 1,451 of our 1,452 are Yajurvedic, and every one sits
        # after a Devanagari letter. Left alone it is dropped as punctuation while a real
        # visarga survives as "h", so a word-identical pair differs by one letter.
        text = re.sub(r"(?<=[ऀ-ॿ]):", "ः", text)
        text = sanscript.transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)
    return text


def skeleton(text: str) -> str:
    """Letters only, one script, no accents, no spaces. The comparison identity."""
    text = transliterate_if_devanagari(text)
    folded = unicodedata.normalize("NFC", deaccent(text)).lower()
    return _PUNCT.sub("", fold_liquids(folded))


def containment(needle: str, haystack: str) -> float:
    """Fraction of ``needle`` that SequenceMatcher can place inside ``haystack``.

    ``autojunk=False`` is not optional: with it on, SequenceMatcher treats any character
    occurring in more than 1% of a long string as junk, which for Sanskrit skeletons
    discards most of the alphabet. This project has already once calibrated a threshold
    against that broken comparator and had to redo it.
    """
    if not needle:
        return 0.0
    matcher = SequenceMatcher(None, needle, haystack, autojunk=False)
    return sum(b.size for b in matcher.get_matching_blocks()) / len(needle)


def fold_root(label: str) -> str:
    """A join key for a verbal root across the Zurich and DCS lemma conventions.

    Strips the root sign, the trailing hyphen, the scholarly sense number and every tone
    mark, then folds the vocalic liquids. It DESTROYS the sense number on purpose — this
    is the fold ``action_root_map.yaml`` warns must never be a primary key — so every
    caller here checks whether a folded key carries more than one predicate before using
    it, and abstains when it does.
    """
    label = deaccent(label).strip()
    label = label.replace("√", "").strip()
    label = label.split("~")[0]
    label = re.sub(r"[\s?]+", " ", label).strip()
    label = re.sub(r"[-‑]\s*\d*\s*$", "", label).strip()
    label = re.sub(r"\s+\d+$", "", label).strip()
    label = label.replace("-", "").replace(" ", "")
    return fold_liquids(unicodedata.normalize("NFC", label).lower())


# ---------------------------------------------------------------------------------
# The role vocabulary
# ---------------------------------------------------------------------------------

#: The five roles declared in data/registry/action_predicates.yaml. Closed.
REGISTRY_ROLES = ("AGENT", "PATIENT", "BENEFICIARY", "INSTRUMENT", "LOCATION")

#: Roles this agent proposes and does not assume. Counted separately everywhere, and
#: never folded into a registry-role total.
PROPOSED_ROLES = ("SOURCE", "GOAL")

#: The brief names RECIPIENT and ACTION. The registry already has both, under its own
#: names. Recorded here so the divergence is a rename and not a parallel vocabulary.
BRIEF_ROLE_ALIASES = {"RECIPIENT": "BENEFICIARY", "ACTION": "ActionPredicate"}

#: Case to role, for the Rigvedic pada-scoped reading. NOM and VOC are resolved against
#: the verb's person, not by case alone.
CASE_ROLE = {
    "ACC": "PATIENT",
    "DAT": "BENEFICIARY",
    "INS": "INSTRUMENT",
    "LOC": "LOCATION",
    "ABL": "SOURCE",
}

#: DCS and UD spell the same cases differently.
UD_CASE = {
    "Acc": "ACC",
    "Dat": "DAT",
    "Ins": "INS",
    "Loc": "LOC",
    "Abl": "ABL",
    "Nom": "NOM",
    "Voc": "VOC",
    "Gen": "GEN",
}

#: Moods that make a second-person clause a request rather than a statement. This is the
#: registry's own definition of the REQUESTED frame: a grammatical fact, not a reading.
REQUEST_MOODS = frozenset(
    {"IMP", "OPT", "SBJV", "SUBJ", "INJ", "PREC", "Imp", "Opt", "Sub", "Jus", "Prec"}
)

#: Predicates whose declared argument_frame has no PATIENT slot. An accusative under one
#: of these is a goal of motion, not a patient, and is emitted as the proposed GOAL role
#: rather than forced into PATIENT.
MOTION_PREDICATES = frozenset({"MOVES_TO", "FLOWS", "SHINES", "DWELLS"})

#: DEPREL to role, for the treebank corpora. Anything not listed is not a role.
#:
#: The ``obl:*`` subtypes are the treebank's own role labels and are used in preference to
#: the case heuristic. ``obl:goal`` matters most: its filler is usually an accusative, and
#: a case rule would have filed every goal of motion as a PATIENT.
DEPREL_ROLE = {
    "nsubj": "AGENT",
    "nsubj:pass": "PATIENT",
    "csubj": "AGENT",
    "obj": "PATIENT",
    "iobj": "BENEFICIARY",
    "obl:agent": "AGENT",
    "obl:goal": "GOAL",
    "obl:source": "SOURCE",
    "obl:instr": "INSTRUMENT",
    "obl:loc": "LOCATION",
    "obl:ben": "BENEFICIARY",
}

#: obl subtypes that are adverbial rather than participant, and carry no role here.
#: obl:temp is time, obl:soc is accompaniment — neither is one of the five registry roles
#: and inventing a COMITATIVE to hold obl:soc would be exactly the parallel vocabulary the
#: brief forbids.
OBL_NON_ROLE = frozenset({"obl:temp", "obl:soc", "obl:cause", "obl:mod", "obl:dir"})

#: A bare ``obl`` has no subtype, so its role comes from its case.
OBL_PREFIXES = ("obl",)

#: Negation and prohibition particles. The predicate vocabulary has no polarity field and
#: two frames only, ASSERTED and REQUESTED, so "do not harm the plants" comes out as a
#: requested SLAYS with the plants as PATIENT -- the opposite of what the verse says. Found
#: by reading a sampled row, VSM 6.22 "mā apaḥ mā oṣadhīḥ hiṃsīḥ". Until the vocabulary
#: gains polarity, every assertion in the scope of one of these carries a caution naming
#: it, so a consumer can exclude them rather than read them backwards.
NEGATION_PARTICLES = frozenset({"mā", "na", "nahi", "mo", "akir", "nakis", "mākis", "neti"})


@dataclass
class Filler:
    role: str
    surface: str
    lemma: str
    case: str | None
    upos: str | None
    filler_type: str
    entity_key: str | None = None
    entity_label: str | None = None
    proposed_role: bool = False
    evidence: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "surface": self.surface,
            "lemma": self.lemma,
            "case": self.case,
            "upos": self.upos,
            "filler_type": self.filler_type,
            "entity_key": self.entity_key,
            "entity_label": self.entity_label,
            "proposed_role": self.proposed_role,
            "evidence": self.evidence,
        }


@dataclass
class Assertion:
    predicate: str | None
    frame: str
    root_label: str
    root_lemma: str
    verb_surface: str
    verb_features: dict[str, Any]
    scope: str
    fillers: list[Filler] = field(default_factory=list)
    predicate_status: str = "MAPPED"
    cautions: list[str] = field(default_factory=list)
    derivation: str = "MORPHOLOGY_RULE_CASE"

    def as_dict(self) -> dict[str, Any]:
        return {
            "derivation": self.derivation,
            "predicate": self.predicate,
            "predicate_status": self.predicate_status,
            "frame": self.frame,
            "root_label": self.root_label,
            "root_lemma": self.root_lemma,
            "verb_surface": self.verb_surface,
            "verb_features": self.verb_features,
            "role_scope": self.scope,
            "roles": [f.as_dict() for f in self.fillers],
            "registry_role_count": sum(1 for f in self.fillers if not f.proposed_role),
            "proposed_role_count": sum(1 for f in self.fillers if f.proposed_role),
            "cautions": self.cautions,
        }


# ---------------------------------------------------------------------------------
# The root map
# ---------------------------------------------------------------------------------


class RootMap:
    """``action_root_map.yaml``, indexed two ways with the fold hazard made explicit."""

    def __init__(self, path: str) -> None:
        import yaml

        with open(path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
        self.version = doc["version"]
        self.vocabulary = doc["predicate_vocabulary"]
        self.entries = doc["roots"]
        self.by_lemma_id: dict[str, dict[str, Any]] = {}
        self.by_label: dict[str, dict[str, Any]] = {}
        fold_bucket: dict[str, set[str]] = {}
        fold_entry: dict[str, dict[str, Any]] = {}
        self.fold_members: dict[str, list[dict[str, Any]]] = {}
        for entry in self.entries:
            predicate = entry.get("predicate") or "UNMAPPED_ROOT"
            lid = entry.get("lemma_id")
            if lid:
                self.by_lemma_id[lid] = entry
            self.by_label[entry["lemma_label"]] = entry
            key = fold_root(entry["lemma_label"])
            fold_bucket.setdefault(key, set()).add(predicate)
            fold_entry.setdefault(key, entry)
            self.fold_members.setdefault(key, []).append(entry)

        # Two rules over a folded key, and the difference between them matters.
        #
        # R1: two or more *mapped* predicates on one folded key is refused outright. This
        #     is the pā-1/pā-2, vid-1/vid-2 hazard the root map names, and there is no
        #     signal in a DCS lemma to break the tie. Refusing is the only honest answer.
        # R2: one mapped predicate plus one or more senses the root map adjudicated as
        #     UNMAPPED is resolved to that predicate, and the assertion carries a caution
        #     naming the minority sense and its Rigvedic token count. Nothing is hidden:
        #     the reader sees which sense could have been meant and how rare it is.
        self.fold_mapped: dict[str, set[str]] = {
            k: {p for p in v if p != "UNMAPPED_ROOT"} for k, v in fold_bucket.items()
        }
        self.fold_ambiguous = {k for k, v in self.fold_mapped.items() if len(v) > 1}
        self.fold_predicate = {
            k: next(iter(v)) for k, v in self.fold_mapped.items() if len(v) == 1
        }
        self.fold_unmapped_minority: dict[str, str] = {}
        for key, members in self.fold_members.items():
            if key not in self.fold_predicate:
                continue
            minority = [
                f"{m['lemma_label']}({m.get('tokens')} RV tokens)"
                for m in members
                if (m.get("predicate") or "UNMAPPED_ROOT") == "UNMAPPED_ROOT"
            ]
            if minority:
                self.fold_unmapped_minority[key] = ", ".join(minority)
        self.fold_entry = fold_entry
        self.__post_init_blocklists(doc)
        self.__post_init_length_buckets()

    # --- the DCS-only vowel-length hazard -------------------------------------------
    #
    # Measured, not assumed: across all 534 DCS files fetched here, 1,651 distinct verb
    # lemmas, NOT ONE contains a long vocalic r or l. DCS writes str̥̄- as stṛ, exactly as
    # it writes str̥-. Zurich distinguishes them and the root map gives them OPPOSITE
    # predicates — str̥̄- is the ritual strewing of the barhis (ESTABLISHES, 30 tokens) and
    # str̥- is laying low (DESTROYS, 8 tokens). Resolving a DCS lemma on its spelling
    # therefore has the same shape as resolving it on root_folded: a key that looks
    # unambiguous and is not. This was found by reading a sampled row, where
    # AVŚ 14.2.22's "cárma copastr̥ṇīthána", spreading the hide, came out as DESTROYS.
    #
    # So DCS resolution runs over a length-neutral bucket, and a bucket carrying more than
    # one mapped predicate is resolved only when one sense holds at least
    # DOMINANT_SENSE_FLOOR of the bucket's Rigvedic tokens. The loser is then named on
    # every assertion, and the status says MAPPED_BY_DOMINANT_SENSE so a consumer who
    # wants none of it can drop them all in one filter.
    DOMINANT_SENSE_FLOOR = 0.95

    @staticmethod
    def length_neutral(key: str) -> str:
        decomposed = unicodedata.normalize("NFD", key)
        decomposed = re.sub(r"([rl]̣)̄", r"\1", decomposed)
        return unicodedata.normalize("NFC", decomposed)

    def __post_init_length_buckets(self) -> None:
        buckets: dict[str, list[dict[str, Any]]] = {}
        for key, members in self.fold_members.items():
            buckets.setdefault(self.length_neutral(key), []).extend(members)
        self.length_bucket = buckets
        self.length_resolution: dict[str, tuple[str | None, str, str]] = {}
        for key, members in buckets.items():
            mapped = [m for m in members if (m.get("predicate") or "UNMAPPED_ROOT") != "UNMAPPED_ROOT"]
            unmapped = [m for m in members if m not in mapped]
            predicates = {m["predicate"] for m in mapped}
            if not predicates:
                self.length_resolution[key] = (None, "UNMAPPED_ROOT_ADJUDICATED", "")
                continue
            totals: dict[str, int] = {}
            for member in mapped:
                totals[member["predicate"]] = totals.get(member["predicate"], 0) + int(
                    member.get("tokens") or 0
                )
            grand = sum(totals.values()) or 1
            top = max(totals, key=lambda p: totals[p])
            share = totals[top] / grand
            others = ", ".join(
                f"{m['lemma_label']}->{m['predicate']}({m.get('tokens')} RV tokens)"
                for m in mapped
                if m["predicate"] != top
            )
            unmapped_note = ", ".join(
                f"{m['lemma_label']}->UNMAPPED({m.get('tokens')} RV tokens)" for m in unmapped
            )
            note = "; ".join(part for part in (others, unmapped_note) if part)
            if len(predicates) == 1:
                self.length_resolution[key] = (top, "MAPPED_BY_FOLD", note)
            elif share >= self.DOMINANT_SENSE_FLOOR:
                self.length_resolution[key] = (
                    top,
                    "MAPPED_BY_DOMINANT_SENSE",
                    f"{top} holds {share:.4f} of this length-neutral key's Rigvedic root "
                    f"tokens; the senses not chosen are {note}",
                )
            else:
                self.length_resolution[key] = (
                    None,
                    "UNRESOLVED_HOMONYM_FOLD",
                    f"top sense {top} holds only {share:.4f} of the key's Rigvedic tokens; "
                    f"competing senses {note}",
                )

    def for_zurich(self, lemma_ids: list[str], lemma_label: str) -> tuple[str | None, str]:
        """Resolve a Zurich root token. lemma_id first, which is unambiguous."""
        for lid in lemma_ids or []:
            entry = self.by_lemma_id.get(lid)
            if entry:
                predicate = entry.get("predicate") or "UNMAPPED_ROOT"
                if predicate == "UNMAPPED_ROOT":
                    return None, "UNMAPPED_ROOT_ADJUDICATED"
                return predicate, "MAPPED_BY_LEMMA_ID"
        key = fold_root(lemma_label)
        if key in self.fold_ambiguous:
            return None, "UNRESOLVED_HOMONYM_FOLD"
        predicate = self.fold_predicate.get(key)
        if predicate in (None, "UNMAPPED_ROOT"):
            return None, "UNMAPPED_ROOT_BELOW_FLOOR" if predicate is None else "UNMAPPED_ROOT_ADJUDICATED"
        return predicate, "MAPPED_BY_FOLD"

    #: Preverbs that DCS folds into the lemma (parī = pari + i) but Zurich keeps as a
    #: separate token in the same pada. Longest first, so pari is tried before pra.
    PREVERBS = (
        "antar", "prati", "adhi", "abhi", "upa", "pari", "para", "anu", "apa", "api",
        "ava", "nis", "nir", "sam", "pra", "vi", "ud", "ni", "ā", "ati", "a",
    )

    #: Suffixes DCS carries on a derived stem that Zurich records as a morphological
    #: feature on the base root (ramay = CAUS of ram).
    SECONDARY_SUFFIXES = ("ay", "y", "sa", "ya")

    def __post_init_blocklists(self, doc: dict[str, Any]) -> None:
        rec = doc.get("recommendations") or {}
        self.particle_sensitive = {
            fold_root(label) for label in rec.get("consult_local_particle") or []
        }
        self.conjugation_sensitive = {
            fold_root(label) for label in rec.get("consult_secondary_conjugation") or []
        }

    def _direct(self, key: str) -> tuple[str | None, str]:
        """Zurich-side resolution by fold. Length is trusted here: Zurich writes it."""
        if key in self.fold_ambiguous:
            return None, "UNRESOLVED_HOMONYM_FOLD"
        predicate = self.fold_predicate.get(key)
        if predicate is None:
            if key in self.fold_members:
                return None, "UNMAPPED_ROOT_ADJUDICATED"
            return None, "ROOT_NOT_IN_RIGVEDIC_MAP"
        return predicate, "MAPPED_BY_FOLD"

    def _dcs_direct(self, key: str) -> tuple[str | None, str, str]:
        """DCS-side resolution, over the length-neutral bucket."""
        neutral = self.length_neutral(key)
        if neutral not in self.length_resolution:
            return None, "ROOT_NOT_IN_RIGVEDIC_MAP", ""
        return self.length_resolution[neutral]

    def for_dcs(self, lemma: str) -> tuple[str | None, str, str]:
        """Resolve a DCS lemma, which carries no scholarly sense number.

        So the fold is the only available key, and a fold that collapses two predicates
        is refused outright. That refusal is the whole point: pā-1 'protect' and pā-2
        'drink' fold together, and a layer that guessed between them would file divine
        protection and Soma-drinking under one predicate.

        Two further attempts are made when the direct fold misses, because DCS and Zurich
        lemmatise differently: DCS folds a preverb into the lemma and lists a causative
        stem as its own lemma, while Zurich keeps the preverb as a separate token and the
        causative as a feature. Each attempt is refused for the roots the registry itself
        flags as particle- or conjugation-sensitive, so the exceptions the root map
        adjudicated by hand are not overridden by a string operation here.

        Returns (predicate, status, qualifier).
        """
        key = fold_root(lemma)
        predicate, status, note = self._dcs_direct(key)
        if predicate or status in ("UNRESOLVED_HOMONYM_FOLD", "UNMAPPED_ROOT_ADJUDICATED"):
            return predicate, status, note

        blocked_after_strip = ""
        for preverb in self.PREVERBS:
            pv = fold_root(preverb)
            if not pv or not key.startswith(pv) or len(key) <= len(pv):
                continue
            base = key[len(pv):]
            cand, cand_status, cand_note = self._dcs_direct(base)
            if not cand:
                if cand_status == "UNRESOLVED_HOMONYM_FOLD" and not blocked_after_strip:
                    blocked_after_strip = f"{preverb}+{base}: {cand_note}"
                continue
            if self.length_neutral(base) in {
                self.length_neutral(k) for k in self.particle_sensitive
            }:
                return None, "REFUSED_PARTICLE_SENSITIVE_ROOT", preverb
            suffix_note = f"{preverb}; {cand_note}" if cand_note else preverb
            return cand, (
                "MAPPED_BY_PREVERB_STRIP"
                if cand_status != "MAPPED_BY_DOMINANT_SENSE"
                else "MAPPED_BY_PREVERB_STRIP_AND_DOMINANT_SENSE"
            ), suffix_note

        for suffix in self.SECONDARY_SUFFIXES:
            if not key.endswith(suffix) or len(key) <= len(suffix) + 1:
                continue
            base = key[: -len(suffix)]
            cand, cand_status, cand_note = self._dcs_direct(base)
            if not cand:
                continue
            if self.length_neutral(base) in {
                self.length_neutral(k) for k in self.conjugation_sensitive
            }:
                return None, "REFUSED_CONJUGATION_SENSITIVE_ROOT", suffix
            suffix_note = f"{suffix}; {cand_note}" if cand_note else suffix
            return cand, (
                "MAPPED_BY_SECONDARY_STEM"
                if cand_status != "MAPPED_BY_DOMINANT_SENSE"
                else "MAPPED_BY_SECONDARY_STEM_AND_DOMINANT_SENSE"
            ), suffix_note

        if blocked_after_strip:
            return None, "UNRESOLVED_HOMONYM_FOLD_AFTER_PREVERB_STRIP", blocked_after_strip
        return None, "ROOT_NOT_IN_RIGVEDIC_MAP", ""


class EntityIndex:
    """Lemma-string index of the entities a role filler may resolve to.

    Deities come from ``lexical_aliases.yaml``, ACCEPTED entries only, DO_NOT_MATCH
    suppressions honoured. Non-deity entities come from ``concepts.yaml`` via its
    ``preferred_label_sa`` stem. Matching is exact lemma-string equality after the fold;
    there is no substring search over verse text anywhere, which the lexical mention
    policy forbids.
    """

    def __init__(self, aliases_path: str, concepts_path: str) -> None:
        import yaml

        with open(aliases_path, encoding="utf-8") as handle:
            doc = yaml.safe_load(handle)
        self.deity: dict[str, tuple[str, str]] = {}
        self.suppressed: set[str] = set()
        for alias in doc["aliases"]:
            key = fold_root(alias["lemma"])
            if alias.get("alias_type") == "DO_NOT_MATCH":
                self.suppressed.add(key)
                continue
            if alias.get("review_status") != "ACCEPTED":
                continue
            self.deity.setdefault(key, (alias["entity_key"], alias["lemma"]))
        for key in self.suppressed:
            self.deity.pop(key, None)

        with open(concepts_path, encoding="utf-8") as handle:
            cdoc = yaml.safe_load(handle)
        self.concept: dict[str, tuple[str, str, str]] = {}
        for concept in cdoc["concepts"]:
            key = fold_root(concept["preferred_label_sa"])
            if key and key not in self.deity:
                self.concept.setdefault(
                    key,
                    (concept["concept_id"], concept["preferred_label_sa"], concept["node_type"]),
                )

    #: First- and second-person pronoun lemmas. These are the human worshipper and the
    #: addressed deity, and they are the single largest class the :Devata-only endpoint
    #: range cannot express: "grant to us" has a recipient, and it is not a god.
    PARTICIPANT_PRONOUNS = frozenset({"mad", "tvad", "vayam", "yusmad", "asmad", "aham", "tvam"})

    def classify(self, lemma: str, upos: str | None) -> tuple[str, str | None, str | None]:
        key = fold_root(lemma)
        if key in self.deity:
            entity_key, label = self.deity[key]
            return "DEITY", entity_key, label
        if key in self.concept:
            cid, label, node_type = self.concept[key]
            return f"CONCEPT:{node_type}", cid, label
        if key in self.PARTICIPANT_PRONOUNS or (upos == "PRON" and key in self.PARTICIPANT_PRONOUNS):
            return "RITUAL_PARTICIPANT_PRONOUN", None, None
        if upos == "PRON":
            return "PRONOUN_UNRESOLVED", None, None
        return "UNREGISTERED_NOMINAL", None, None
