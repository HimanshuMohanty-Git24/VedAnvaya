"""The corrected case-scoped role rule, and the clause gate that makes it defensible.

Why this module exists
----------------------
The Wave-3 preflight scored the previous case-scoped rule against the DCS dependency
parse and it failed: 623 of 2,715 emitted fillers (23.0%) were attached across a clause
boundary and 50 more carried the wrong role. The owner's ruling is that recording that
rate is not a substitute for not emitting the error, so the rule is replaced rather than
annotated.

The previous gate refused a scope holding more than one **finite** verb. The measurement
showed the leakage comes from structures that gate cannot see:

    acl 75 · xcomp:result 56 · xcomp 34 · advcl 42 · nsubj inside a nominal 106

Every one of those is a clause headed by something other than a finite verb — a
participle, an infinitive, an absolutive, or a relative pronoun whose own verb is elided.
So the gate is widened from "one finite verb" to "one verbal anchor of any kind, and no
relative pronoun", which is not guesswork: a participle is a clause head as a matter of
morphology, and the morphology is what we have.

One normalised token view
-------------------------
The old code implemented the case rule twice, once over Zurich tokens and once over DCS
tokens, which is how the two could have drifted. Both are now projected into one
``Tok`` view and there is a single implementation of the rule. The measurement harness
scores that same implementation, so what is measured is what ships.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import lib_roles as L

#: Relative pronoun lemmas. A relative pronoun implies a relative clause; when that
#: clause's verb is elided — which is common in both corpora — there is no second verbal
#: anchor to catch, and the clause's arguments end up attributed to the main verb. This is
#: the AVŚ 1.4.4 case: "amūḥ yāḥ upa sūrye … tāḥ naḥ hinvantu", where amūḥ is the subject
#: of a verbless relative clause and the old rule made it the agent of hinvantu.
RELATIVE_LEMMAS = frozenset({"ya", "yad", "yaḥ", "yat"})

#: Nominal parts of speech that can carry a role, in either source's vocabulary.
_NOMINAL_UPOS = frozenset({"NOUN", "PROPN", "PRON", "ADJ", "NUM", "DET"})
_NOMINAL_ZURICH = frozenset({"nominal stem", "pronoun"})

#: Tokens that are a modifier rather than an independent argument, used only by the
#: agreement merge. DET/ADJ/NUM in DCS; Zurich does not distinguish an adjective from a
#: noun, so there the merge rests on agreement and adjacency alone.
_MODIFIER_UPOS = frozenset({"ADJ", "DET", "NUM"})


@dataclass(frozen=True)
class Tok:
    index: int
    surface: str
    lemma: str
    upos: str
    case: str | None
    number: str | None
    gender: str | None
    is_finite_verb: bool
    is_nonfinite_verbal: bool
    is_nominal: bool
    is_modifier: bool
    is_relative: bool
    raw: Any


def view_zurich(tokens: Iterable[dict]) -> list[Tok]:
    out = []
    for i, t in enumerate(tokens):
        pos = t.get("part_of_speech")
        feats = t.get("morphological_features") or {}
        finite = pos == "root" and "person" in feats and "non-finite" not in feats
        nonfinite = pos == "root" and not finite
        lemma = t.get("normalized_lemma") or ""
        out.append(
            Tok(
                index=i,
                surface=t.get("normalized_surface") or "",
                lemma=lemma,
                upos=pos or "",
                case=feats.get("case"),
                number=feats.get("number"),
                gender=feats.get("gender"),
                is_finite_verb=finite,
                is_nonfinite_verbal=nonfinite,
                is_nominal=pos in _NOMINAL_ZURICH,
                is_modifier=False,
                is_relative=pos == "pronoun" and L.fold_root(lemma) in
                {L.fold_root(r) for r in RELATIVE_LEMMAS},
                raw=t,
            )
        )
    return out


def view_dcs(tokens: Iterable[dict]) -> list[Tok]:
    out = []
    for i, t in enumerate(tokens):
        feats = t["feats"]
        finite = (
            t["upos"] == "VERB" and "Person" in feats and feats.get("VerbForm") != "Part"
        )
        nonfinite = t["upos"] == "VERB" and not finite
        lemma = t["lemma"]
        out.append(
            Tok(
                index=i,
                surface=t["misc"].get("Unsandhied") or t["form"],
                lemma=lemma,
                upos=t["upos"],
                case=L.UD_CASE.get(feats.get("Case") or ""),
                number=feats.get("Number"),
                gender=feats.get("Gender"),
                is_finite_verb=finite,
                is_nonfinite_verbal=nonfinite,
                is_nominal=t["upos"] in _NOMINAL_UPOS,
                is_modifier=t["upos"] in _MODIFIER_UPOS,
                is_relative=t["upos"] == "PRON" and L.fold_root(lemma) in
                {L.fold_root(r) for r in RELATIVE_LEMMAS},
                raw=t,
            )
        )
    return out


def clause_gate(view: list[Tok], anchor_gate: bool = True, relative_gate: bool = True):
    """Decide whether this scope is safe to read roles out of, with no parse.

    Returns (ok, reason). The reason is recorded on the assertion when it is not ok, so
    an abstention is never silent.
    """
    anchors = [t for t in view if t.is_finite_verb or t.is_nonfinite_verbal]
    if anchor_gate and len(anchors) > 1:
        kinds = []
        if sum(1 for t in anchors if t.is_finite_verb) > 1:
            kinds.append("a second finite verb")
        if any(t.is_nonfinite_verbal for t in anchors):
            kinds.append("a non-finite verbal form heading its own clause")
        return False, "SCOPE_HOLDS_MORE_THAN_ONE_VERBAL_ANCHOR:" + "; ".join(kinds)
    if relative_gate and any(t.is_relative for t in view):
        return False, "SCOPE_HOLDS_A_RELATIVE_PRONOUN_SO_A_SECOND_CLAUSE_EXISTS"
    return True, ""


def merge_agreeing_modifiers(picked: list[tuple[Tok, str]]) -> list[tuple[Tok, str, str]]:
    """Collapse a modifier onto the argument it agrees with.

    The preflight found 580 fillers that were a second token inside ONE argument — a
    determiner, adjective, apposition or conjunct — 406 of 423 checkable ones carrying the
    same role as the argument head. They are not wrong roles, but emitting "viśvā" and
    "rūpāṇi" as two PATIENT fillers reports one argument as two, and a :RoleFiller
    projection built on that would overcount every argument that carries an epithet.

    Merge condition: adjacent in the scope, same case, same number, same gender, same
    role. Returns (head token, role, prefix) where prefix is the merged modifier surfaces.
    """
    picked = sorted(picked, key=lambda p: p[0].index)
    out: list[tuple[Tok, str, str]] = []
    consumed: set[int] = set()
    for position, (tok, role) in enumerate(picked):
        if tok.index in consumed:
            continue
        prefix_parts: list[str] = []
        head = tok
        # look forward across immediately following picked tokens that agree
        cursor = position + 1
        while cursor < len(picked):
            nxt, nxt_role = picked[cursor]
            if (
                nxt_role == role
                and nxt.index == picked[cursor - 1][0].index + 1
                and nxt.case == head.case
                and nxt.number == head.number
                and nxt.gender == head.gender
                and (head.is_modifier or nxt.is_modifier or head.upos == nxt.upos)
            ):
                # the modifier is whichever is tagged as one; otherwise keep the later
                # token as head, which is where Vedic puts the noun after its epithet
                if head.is_modifier and not nxt.is_modifier:
                    prefix_parts.append(head.surface)
                    head = nxt
                else:
                    prefix_parts.append(nxt.surface)
                consumed.add(nxt.index)
                cursor += 1
                continue
            break
        out.append((head, role, "".join(prefix_parts)))
        consumed.add(head.index)
    return out


def case_scoped_roles(view: list[Tok], verb: Tok, predicate: str, person: str, voice: str | None):
    """Roles from morphological case, over a scope the clause gate has already cleared."""
    picked: list[tuple[Tok, str]] = []
    refusals: list[str] = []
    for tok in view:
        if tok.index == verb.index or not tok.is_nominal or tok.case is None:
            continue
        role = None
        if tok.case == "NOM" and person == "3":
            if tok.number != verb.number:
                refusals.append("NOMINATIVE_REFUSED_NUMBER_DISAGREEMENT")
                continue
            role = "PATIENT" if voice in ("PASS", "Pass") else "AGENT"
        elif tok.case == "VOC" and person == "2":
            role = "AGENT"
        elif tok.case in L.CASE_ROLE:
            role = L.CASE_ROLE[tok.case]
            if role == "PATIENT" and predicate in L.MOTION_PREDICATES:
                role = "GOAL"
        if role is None:
            continue
        picked.append((tok, role))
    return merge_agreeing_modifiers(picked), refusals
