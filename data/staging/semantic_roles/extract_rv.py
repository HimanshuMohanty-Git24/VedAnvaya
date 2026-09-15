"""Rigvedic semantic roles from the Zurich manual morphological annotation.

The annotation is morphology only. There is no dependency parse, no clause boundary and
no subject link, so a role here is read from a case inside one metrical pada. That is a
heuristic and it is typed as one: ``MORPHOLOGY_RULE_CASE``.

Three refusals are built in, each because the registry that owns the vocabulary said so:

* A pada holding more than one finite verb yields predicates and frames but no
  non-agent roles, because nothing in the annotation says which accusative belongs to
  which verb.
* A nominative is only an AGENT when its number agrees with the verb's.
* A non-active voice on one of the roots the root map flags as frame-inverting is
  recorded as a caution on the assertion, not silently resolved. An extractor that
  assigns AGENT from any nominative "will make the fire kindle the priest" — the root
  map's own words.
"""
from __future__ import annotations

import collections
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_roles as L  # noqa: E402

TOKENS = r"D:\VedaGraph\data\knowledge\rigveda_lexical_v1\tokens.jsonl"
REGISTRY = r"D:\VedaGraph\data\registry"

#: Roots whose secondary conjugation or non-active voice inverts the argument frame
#: without changing the predicate, per action_root_map.yaml recommendations.
FRAME_INVERTING = {"vr̥dh", "dhr̥", "sad", "vr̥t", "naś", "dhā", "randh"}


def load_passages():
    """Stream the 200 MB token file once, grouped by passage and pada."""
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


def is_finite(token) -> bool:
    features = token.get("morphological_features") or {}
    return (
        token.get("part_of_speech") == "root"
        and "person" in features
        and "non-finite" not in features
    )


def run() -> dict:
    rootmap = L.RootMap(os.path.join(REGISTRY, "action_root_map.yaml"))
    entities = L.EntityIndex(
        os.path.join(REGISTRY, "lexical_aliases.yaml"),
        os.path.join(REGISTRY, "concepts.yaml"),
    )
    stats = collections.Counter()
    predicate_counts = collections.Counter()
    role_counts = collections.Counter()
    filler_types = collections.Counter()
    predicate_status = collections.Counter()
    out = {}

    for passage_key, padas in load_passages():
        stats["passages_processed"] += 1
        assertions = []
        for pada, tokens in padas.items():
            stats["tokens_processed"] += len(tokens)
            verbs = [t for t in tokens if is_finite(t)]
            nonfinite = [
                t
                for t in tokens
                if t.get("part_of_speech") == "root" and not is_finite(t)
            ]
            stats["nonfinite_root_tokens"] += len(nonfinite)
            if not verbs:
                continue
            multiple = len(verbs) > 1
            if multiple:
                stats["padas_with_multiple_finite_verbs"] += 1
            for verb in verbs:
                stats["finite_verb_tokens"] += 1
                features = verb.get("morphological_features") or {}
                predicate, status = rootmap.for_zurich(
                    verb.get("lemma_ids") or [], verb.get("normalized_lemma") or ""
                )
                predicate_status[status] += 1
                if predicate is None:
                    stats["verbs_without_predicate"] += 1
                    continue
                predicate_counts[predicate] += 1
                mood = features.get("mood")
                person = str(features.get("person") or "")
                frame = (
                    "REQUESTED"
                    if mood in L.REQUEST_MOODS and person == "2"
                    else "ASSERTED"
                )
                cautions = []
                if multiple:
                    cautions.append("ROLE_SCOPE_AMBIGUOUS_MULTIPLE_FINITE_VERBS_IN_PADA")
                base = L.fold_root(verb.get("normalized_lemma") or "")
                if base in FRAME_INVERTING and features.get("voice") != "ACT":
                    cautions.append("FRAME_MAY_INVERT_NONACTIVE_VOICE_ON_FLAGGED_ROOT")
                if person == "1":
                    cautions.append("FIRST_PERSON_AGENT_IS_THE_UNNAMED_SPEAKER")
                negators = sorted(
                    {
                        t.get("normalized_lemma") or ""
                        for t in tokens
                        if t.get("part_of_speech") == "invariable"
                        and L.fold_root(t.get("normalized_lemma") or "")
                        in {L.fold_root(n) for n in L.NEGATION_PARTICLES}
                    }
                )
                if negators:
                    cautions.append(
                        "POLARITY_NOT_MODELLED_NEGATION_PARTICLE_IN_SCOPE:"
                        + ",".join(negators)
                    )
                    stats["assertions_in_scope_of_a_negation_particle"] += 1

                fillers = []
                if not multiple:
                    for token in tokens:
                        if token is verb:
                            continue
                        pos = token.get("part_of_speech")
                        if pos not in ("nominal stem", "pronoun"):
                            continue
                        tf = token.get("morphological_features") or {}
                        case = tf.get("case")
                        if case is None:
                            continue
                        role = None
                        if case == "NOM" and person == "3":
                            if tf.get("number") != features.get("number"):
                                stats["nominatives_refused_number_disagreement"] += 1
                            elif features.get("voice") == "PASS":
                                # A passive verb's nominative is the undergoer. Calling it
                                # the AGENT is precisely the inversion action_root_map.yaml
                                # warns about -- it "will make the fire kindle the priest"
                                # -- and a caution on the assertion does not undo a wrong
                                # role on the filler. Found by reading a sampled row:
                                # RV 8.48.10 'ayaṁ yaḥ somo ny adhāyy asme', this Soma
                                # which has been deposited in us, had Soma as AGENT.
                                role = "PATIENT"
                                stats["nominatives_retyped_patient_under_passive"] += 1
                            else:
                                role = "AGENT"
                        elif case == "VOC" and person == "2":
                            role = "AGENT"
                        elif case in L.CASE_ROLE:
                            role = L.CASE_ROLE[case]
                            if role == "PATIENT" and predicate in L.MOTION_PREDICATES:
                                role = "GOAL"
                        if role is None:
                            continue
                        lemma = token.get("normalized_lemma") or ""
                        ftype, ekey, elabel = entities.classify(lemma, None)
                        if pos == "pronoun":
                            ftype = (
                                "RITUAL_PARTICIPANT_PRONOUN"
                                if L.fold_root(lemma) in entities.PARTICIPANT_PRONOUNS
                                else "PRONOUN_UNRESOLVED"
                            )
                            ekey = elabel = None
                        proposed = role in L.PROPOSED_ROLES
                        fillers.append(
                            L.Filler(
                                role=role,
                                surface=token.get("normalized_surface") or "",
                                lemma=lemma,
                                case=case,
                                upos=pos,
                                filler_type=ftype,
                                entity_key=ekey,
                                entity_label=elabel,
                                proposed_role=proposed,
                                evidence=f"pada {pada}, {case} in the same pada as the finite verb",
                            )
                        )
                        role_counts[role] += 1
                        filler_types[ftype] += 1

                assertions.append(
                    L.Assertion(
                        predicate=predicate,
                        frame=frame,
                        root_label=(verb.get("lemma") or "").strip(),
                        root_lemma=verb.get("normalized_lemma") or "",
                        verb_surface=verb.get("normalized_surface") or "",
                        verb_features=features,
                        scope=f"PADA:{pada}",
                        fillers=fillers,
                        predicate_status=status,
                        cautions=cautions,
                    )
                )
        if assertions:
            out[passage_key] = assertions
            stats["passages_with_assertion"] += 1
            stats["assertions"] += len(assertions)
        else:
            stats["passages_without_assertion"] += 1

    return {
        "assertions": out,
        "stats": dict(stats),
        "predicates": dict(predicate_counts),
        "roles": dict(role_counts),
        "filler_types": dict(filler_types),
        "predicate_status": dict(predicate_status),
        "rootmap_version": rootmap.version,
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    result = run()
    print(json.dumps({k: v for k, v in result.items() if k != "assertions"},
                     ensure_ascii=False, indent=1))
    scratch = sys.argv[1] if len(sys.argv) > 1 else "rv_assertions.json"
    with io.open(scratch, "w", encoding="utf-8") as handle:
        json.dump(
            {k: [a.as_dict() for a in v] for k, v in result["assertions"].items()},
            handle,
            ensure_ascii=False,
        )
    print("wrote", scratch)
