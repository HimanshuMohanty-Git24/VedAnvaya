"""Rigvedic semantic assertions from the Zurich manual morphological annotation.

Corrected after the Wave-3 preflight and the owner's ruling.

What changed and why
--------------------
The previous version read role fillers from morphological case inside one metrical pada.
Scored against the DCS dependency parse, that rule attached 24.8% of its fillers across a
clause boundary or to the wrong role. Widening the gate from "one finite verb" to "one
verbal anchor of any kind, and no relative pronoun" — which is what the leakage analysis
pointed at — moved the error only from 24.8% to 24.3%, and cost 18 points of recall. Not
one role reached an importable standard: the best, GOAL, was still 11.4% wrong and the
nominative-derived AGENT was 39.8% wrong.

So the Rigveda gets **no asserted role fillers**. There is no dependency parse for the
Rigveda at all, and this pipeline will not assert a role it cannot defend.

What it does emit is everything that never depended on role scope: the predicate, the
frame, the verb's surface and the verb's morphological features, all read off the verb
token itself. A predicate-only assertion claims less than before, and what it claims is
sound. The gated case-scoped fillers are still produced, but as a separate, explicitly
non-importable verification queue with their measured error rate attached — they are the
philologist's work list, not a layer.
"""
from __future__ import annotations

import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_roles as L  # noqa: E402
import clause_scope as C  # noqa: E402

TOKENS = r"D:\VedaGraph\data\knowledge\rigveda_lexical_v1\tokens.jsonl"
REGISTRY = r"D:\VedaGraph\data\registry"

FRAME_INVERTING = {"vr̥dh", "dhr̥", "sad", "vr̥t", "naś", "dhā", "randh"}

ROLES_WITHHELD = (
    "No dependency parse exists for the Rigveda. Roles read from case inside a pada were "
    "measured against the DCS parse at 24.3% wrong even under the tightened clause gate, "
    "so none is asserted. The gated candidates are in role_candidates.jsonl."
)


def load_passages():
    current_key = None
    bucket: dict[str, list[dict]] = collections.OrderedDict()
    for line in io.open(TOKENS, encoding="utf-8"):
        token = json.loads(line)
        key = token["passage_key"]
        if key != current_key:
            if current_key is not None:
                yield current_key, bucket
            current_key, bucket = key, collections.OrderedDict()
        bucket.setdefault(token.get("pada") or "?", []).append(token)
    if current_key is not None:
        yield current_key, bucket


def run() -> dict:
    rootmap = L.RootMap(os.path.join(REGISTRY, "action_root_map.yaml"))
    entities = L.EntityIndex(
        os.path.join(REGISTRY, "lexical_aliases.yaml"),
        os.path.join(REGISTRY, "concepts.yaml"),
    )
    stats = collections.Counter()
    predicate_counts = collections.Counter()
    predicate_status = collections.Counter()
    candidate_roles = collections.Counter()
    assertions_out: dict[str, list] = {}
    candidates_out: dict[str, list] = {}

    for passage_key, padas in load_passages():
        stats["passages_processed"] += 1
        assertions = []
        candidates = []
        for pada, tokens in padas.items():
            stats["tokens_processed"] += len(tokens)
            view = C.view_zurich(tokens)
            finite = [t for t in view if t.is_finite_verb]
            stats["nonfinite_root_tokens"] += sum(1 for t in view if t.is_nonfinite_verbal)
            if not finite:
                continue
            gate_ok, gate_reason = C.clause_gate(view)
            if not gate_ok:
                stats["padas_refused_by_clause_gate"] += 1
                stats["gate_reason:" + gate_reason.split(":")[0]] += 1
            for verb in finite:
                stats["finite_verb_tokens"] += 1
                raw = verb.raw
                features = raw.get("morphological_features") or {}
                predicate, status = rootmap.for_zurich(
                    raw.get("lemma_ids") or [], raw.get("normalized_lemma") or ""
                )
                predicate_status[status] += 1
                if predicate is None:
                    stats["verbs_without_predicate"] += 1
                    continue
                predicate_counts[predicate] += 1
                mood = features.get("mood")
                person = str(features.get("person") or "")
                frame = (
                    "REQUESTED" if mood in L.REQUEST_MOODS and person == "2" else "ASSERTED"
                )
                cautions = []
                base = L.fold_root(raw.get("normalized_lemma") or "")
                if base in FRAME_INVERTING and features.get("voice") != "ACT":
                    cautions.append("FRAME_MAY_INVERT_NONACTIVE_VOICE_ON_FLAGGED_ROOT")
                if person == "1":
                    cautions.append("FIRST_PERSON_AGENT_IS_THE_UNNAMED_SPEAKER")
                negators = sorted(
                    {
                        t.lemma
                        for t in view
                        if t.upos == "invariable"
                        and L.fold_root(t.lemma)
                        in {L.fold_root(n) for n in L.NEGATION_PARTICLES}
                    }
                )
                if negators:
                    cautions.append(
                        "POLARITY_NOT_MODELLED_NEGATION_PARTICLE_IN_SCOPE:"
                        + ",".join(negators)
                    )
                    stats["assertions_in_scope_of_a_negation_particle"] += 1

                assertion = L.Assertion(
                    predicate=predicate,
                    frame=frame,
                    root_label=(raw.get("lemma") or "").strip(),
                    root_lemma=raw.get("normalized_lemma") or "",
                    verb_surface=raw.get("normalized_surface") or "",
                    verb_features=features,
                    scope=f"PADA:{pada}",
                    fillers=[],
                    predicate_status=status,
                    cautions=cautions,
                    derivation="MORPHOLOGY_RULE_PREDICATE_ONLY",
                )
                record = assertion.as_dict()
                record["roles_withheld"] = True
                record["roles_withheld_reason"] = ROLES_WITHHELD
                assertions.append(record)
                stats["assertions"] += 1

                # --- the non-importable verification queue -------------------------
                if not gate_ok or len(finite) > 1:
                    if len(finite) > 1:
                        stats["candidate_scopes_refused_multiple_finite_verbs"] += 1
                    continue
                merged, refusals = C.case_scoped_roles(
                    view, verb, predicate, person, features.get("voice")
                )
                for reason in refusals:
                    stats[reason.lower()] += 1
                if not merged:
                    continue
                fillers = []
                for head, role, prefix in merged:
                    ftype, ekey, elabel = entities.classify(head.lemma, None)
                    if head.upos == "pronoun":
                        ftype = (
                            "RITUAL_PARTICIPANT_PRONOUN"
                            if L.fold_root(head.lemma) in entities.PARTICIPANT_PRONOUNS
                            else "PRONOUN_UNRESOLVED"
                        )
                        ekey = elabel = None
                    fillers.append(
                        L.Filler(
                            role=role,
                            surface=prefix + head.surface,
                            lemma=head.lemma,
                            case=head.case,
                            upos=head.upos,
                            filler_type=ftype,
                            entity_key=ekey,
                            entity_label=elabel,
                            proposed_role=role in L.PROPOSED_ROLES,
                            evidence=f"pada {pada}, {head.case} beside the finite verb, "
                            "clause gate cleared",
                        ).as_dict()
                    )
                    candidate_roles[role] += 1
                candidates.append(
                    {
                        "predicate": predicate,
                        "frame": frame,
                        "verb_surface": raw.get("normalized_surface") or "",
                        "scope": f"PADA:{pada}",
                        "role_candidates": fillers,
                    }
                )
                stats["candidate_assertions"] += 1

        if assertions:
            assertions_out[passage_key] = assertions
            stats["passages_with_assertion"] += 1
        else:
            stats["passages_without_assertion"] += 1
        if candidates:
            candidates_out[passage_key] = candidates

    return {
        "assertions": assertions_out,
        "candidates": candidates_out,
        "stats": dict(stats),
        "predicates": dict(predicate_counts),
        "predicate_status": dict(predicate_status),
        "candidate_roles": dict(candidate_roles),
        "rootmap_version": rootmap.version,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    result = run()
    summary = {k: v for k, v in result.items() if k not in ("assertions", "candidates")}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    out = sys.argv[1]
    with io.open(out, "w", encoding="utf-8") as handle:
        json.dump(result["assertions"], handle, ensure_ascii=False)
    with io.open(out.replace(".json", "_candidates.json"), "w", encoding="utf-8") as handle:
        json.dump(result["candidates"], handle, ensure_ascii=False)
    with io.open(out.replace(".json", "_summary.json"), "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False)
    print("wrote", out)
