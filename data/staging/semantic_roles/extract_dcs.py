"""Atharvavedic and Yajurvedic semantic roles from the DCS CoNLL-U treebank.

Two things make this the stronger half of the layer and one makes it the harder half.

Stronger: for both these corpora DCS carries a full dependency parse, so AGENT comes off
an ``nsubj`` and PATIENT off an ``obj`` rather than being inferred from a case standing
somewhere in the same metrical line. The Rigveda, which has the better *morphology*, has
no parse at all. The derivation is typed ``TREEBANK_DEPREL`` so the two never blend.

Harder: DCS files are keyed at hymn level and carry no verse number. The sentence blocks
are syntactic, not metrical — AVŚ 1.1 has four verses and seven sentence groups — so
positional assignment is wrong, and the campaign's own history says a wrong address
resolves exactly as cleanly as a right one. The verse is therefore recovered by aligning
the hymn's whole sentence sequence against the hymn's whole verse sequence as two
concatenated letter skeletons, and reading each sentence's verse off the matching blocks.
A sentence whose characters do not land predominantly inside one verse is recorded as
unresolved rather than forced into the nearest one.
"""
from __future__ import annotations

import collections
import io
import json
import os
import re
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_roles as L  # noqa: E402
import clause_scope as C  # noqa: E402

REGISTRY = r"D:\VedaGraph\data\registry"

#: A sentence must have this fraction of its own letters matched inside the hymn, and
#: this fraction of those matched letters inside one verse, to be addressed at all.
SENTENCE_MATCH_FLOOR = 0.60
VERSE_CONCENTRATION_FLOOR = 0.70
#: A whole hymn is refused if its sentence sequence does not match its verse sequence
#: this well; below it the two are not the same text and no alignment inside it is safe.
HYMN_MATCH_FLOOR = 0.70


def parse_conllu(path):
    """Yield (sent_id, text, [token dicts]) in file order."""
    meta, tokens = {}, []
    for raw in io.open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        if line.startswith("##"):
            continue
        if line.startswith("#"):
            if "=" in line:
                key, value = line[1:].split("=", 1)
                meta[key.strip()] = value.strip()
            continue
        if not line.strip():
            if tokens:
                yield meta.get("sent_id", ""), meta.get("text", ""), tokens
            meta, tokens = {}, []
            continue
        parts = line.split("\t")
        if len(parts) < 10 or not parts[0].isdigit():
            continue
        feats = {}
        if parts[5] != "_":
            for item in parts[5].split("|"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    feats[k] = v
        misc = {}
        if parts[9] != "_":
            for item in parts[9].split("|"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    misc[k] = v
        tokens.append(
            {
                "id": int(parts[0]),
                "form": parts[1],
                "lemma": parts[2],
                "upos": parts[3],
                "feats": feats,
                "head": int(parts[6]) if parts[6].isdigit() else 0,
                "deprel": parts[7],
                "misc": misc,
            }
        )
    if tokens:
        yield meta.get("sent_id", ""), meta.get("text", ""), tokens


def align_hymn(sentences, verses):
    """Map each sentence to one of ``verses``.

    ``sentences`` is a list of (sent_id, text, tokens); ``verses`` a list of
    (canonical_key, skeleton) in corpus order. Returns (assignments, diagnostics) where
    an assignment is (index, canonical_key or None, matched_fraction, concentration).
    """
    sent_skeletons = [L.skeleton(text) for _, text, _ in sentences]
    sent_concat = "".join(sent_skeletons)
    sent_offsets = []
    cursor = 0
    for skeleton in sent_skeletons:
        sent_offsets.append((cursor, cursor + len(skeleton)))
        cursor += len(skeleton)

    verse_concat = "".join(skeleton for _, skeleton in verses)
    verse_owner = []
    for key, skeleton in verses:
        verse_owner.extend([key] * len(skeleton))

    matcher = SequenceMatcher(None, sent_concat, verse_concat, autojunk=False)
    blocks = matcher.get_matching_blocks()
    # Character-level map from the sentence concatenation into the verse concatenation.
    mapped = [None] * len(sent_concat)
    for block in blocks:
        for offset in range(block.size):
            mapped[block.a + offset] = block.b + offset

    hymn_match = (
        sum(b.size for b in blocks) / len(sent_concat) if sent_concat else 0.0
    )

    assignments = []
    for index, (start, end) in enumerate(sent_offsets):
        length = end - start
        if length == 0:
            assignments.append((index, None, 0.0, 0.0, "EMPTY_SENTENCE_SKELETON"))
            continue
        hits = [mapped[p] for p in range(start, end) if mapped[p] is not None]
        fraction = len(hits) / length
        if not hits:
            assignments.append((index, None, 0.0, 0.0, "NO_MATCHED_CHARACTERS"))
            continue
        owners = collections.Counter(verse_owner[h] for h in hits)
        best, count = owners.most_common(1)[0]
        concentration = count / len(hits)
        if fraction < SENTENCE_MATCH_FLOOR:
            reason = "SENTENCE_BELOW_MATCH_FLOOR"
            best = None
        elif concentration < VERSE_CONCENTRATION_FLOOR:
            reason = "SENTENCE_SPANS_VERSE_BOUNDARY"
            best = None
        else:
            reason = "ALIGNED"
        assignments.append((index, best, fraction, concentration, reason))

    return assignments, {"hymn_match": hymn_match, "sentences": len(sentences)}


def roles_for_sentence(tokens, rootmap, entities, locator):
    """One assertion per finite verb. Roles ONLY where the treebank supplies them.

    Corrected after the Wave-3 preflight and the owner's ruling. The previous version fell
    back to a case-scoped reading wherever DCS had no parse, and that fallback was measured
    against the parse at 24.8% wrong -- 24.3% even after the clause gate was widened from
    "one finite verb" to "one verbal anchor of any kind, and no relative pronoun". No role
    reached an importable standard, so none is asserted without a parse.

    Where the parse exists the roles are the treebank's own labels, including its
    ``obl:goal`` / ``obl:source`` / ``obl:instr`` / ``obl:loc`` subtypes. Where it does not,
    the assertion carries predicate, frame, verb surface and verb features -- all read off
    the verb token, none of them dependent on role scope -- and its gated case-scoped
    fillers go to the non-importable verification queue instead.
    """
    by_head = collections.defaultdict(list)
    for token in tokens:
        by_head[token["head"]].append(token)
    parsed = any(token["deprel"] != "_" for token in tokens)
    derivation = "TREEBANK_DEPREL" if parsed else "MORPHOLOGY_RULE_PREDICATE_ONLY"
    scope = "SENTENCE_DEPENDENCY_SUBTREE" if parsed else "SENTENCE_PREDICATE_ONLY"

    assertions = []
    candidates = []
    diagnostics = collections.Counter()
    diagnostics["sentences_with_parse" if parsed else "sentences_morphology_only"] += 1
    view = C.view_dcs(tokens)
    finite = [
        token
        for token in tokens
        if token["upos"] == "VERB"
        and "Person" in token["feats"]
        and token["feats"].get("VerbForm") != "Part"
    ]
    diagnostics["nonfinite_or_participial_verb"] += sum(
        1 for t in tokens if t["upos"] == "VERB" and t not in finite
    )
    gate_ok, gate_reason = C.clause_gate(view)
    if not parsed and not gate_ok:
        diagnostics["sentences_refused_by_clause_gate"] += 1
        diagnostics["gate_reason:" + gate_reason.split(":")[0]] += 1

    for token in finite:
        feats = token["feats"]
        diagnostics["finite_verb_tokens"] += 1
        predicate, status, qualifier = rootmap.for_dcs(token["lemma"])
        diagnostics["status:" + status] += 1
        if predicate is None:
            diagnostics["verbs_without_predicate"] += 1
            diagnostics["lost_fold:" + L.fold_root(token["lemma"])] += 1
            continue
        person = str(feats.get("Person") or "")
        mood = feats.get("Mood")
        frame = "REQUESTED" if mood in L.REQUEST_MOODS and person == "2" else "ASSERTED"
        cautions = []
        if status == "MAPPED_BY_PREVERB_STRIP":
            cautions.append("PREDICATE_VIA_PREVERB_STRIP:" + str(qualifier))
        if status == "MAPPED_BY_SECONDARY_STEM":
            cautions.append("PREDICATE_VIA_SECONDARY_STEM:" + str(qualifier))
        minority = rootmap.fold_unmapped_minority.get(L.fold_root(token["lemma"]))
        if minority:
            cautions.append("FOLD_CARRIES_AN_UNMAPPED_MINORITY_SENSE:" + minority)
        if person == "1":
            cautions.append("FIRST_PERSON_AGENT_IS_THE_UNNAMED_SPEAKER")
        negators = sorted(
            {
                t["lemma"]
                for t in tokens
                if L.fold_root(t["lemma"]) in {L.fold_root(n) for n in L.NEGATION_PARTICLES}
                and t["upos"] in ("PART", "ADV", "CCONJ", "INTJ")
            }
        )
        if negators:
            cautions.append(
                "POLARITY_NOT_MODELLED_NEGATION_PARTICLE_IN_SCOPE:" + ",".join(negators)
            )
            diagnostics["assertions_in_scope_of_a_negation_particle"] += 1

        fillers = []
        if parsed:
            for child in by_head.get(token["id"], []):
                deprel = child["deprel"]
                case = L.UD_CASE.get(child["feats"].get("Case") or "")
                role = None
                if deprel in L.OBL_NON_ROLE:
                    diagnostics["obl_subtype_not_a_role:" + deprel] += 1
                    continue
                if deprel in L.DEPREL_ROLE:
                    role = L.DEPREL_ROLE[deprel]
                    if role == "AGENT" and deprel == "nsubj" and case not in (None, "NOM"):
                        diagnostics["nsubj_refused_non_nominative"] += 1
                        continue
                    if role == "AGENT" and deprel == "nsubj" and feats.get("Voice") == "Pass":
                        role = "PATIENT"
                        diagnostics["nsubj_retyped_patient_under_passive"] += 1
                elif deprel == "vocative" and person == "2":
                    role = "AGENT"
                elif deprel.split(":")[0] in L.OBL_PREFIXES and case:
                    role = L.CASE_ROLE.get(case)
                if role is None:
                    continue
                if role == "PATIENT" and predicate in L.MOTION_PREDICATES:
                    role = "GOAL"
                prefix = "".join(
                    (g["misc"].get("Unsandhied") or g["form"])
                    for g in by_head.get(child["id"], [])
                    if g["deprel"].startswith("compound")
                )
                fillers.append(
                    _filler(
                        child,
                        role,
                        case,
                        entities,
                        locator + ": deprel " + deprel + " of the finite verb",
                        prefix,
                    )
                )
                diagnostics["parse_backed_role_fillers"] += 1

        assertion = L.Assertion(
            predicate=predicate,
            frame=frame,
            root_label=token["lemma"],
            root_lemma=token["lemma"],
            verb_surface=token["misc"].get("Unsandhied") or token["form"],
            verb_features=feats,
            scope=scope,
            fillers=fillers,
            predicate_status=status,
            cautions=cautions,
            derivation=derivation,
        )
        record = assertion.as_dict()
        if not parsed:
            record["roles_withheld"] = True
            record["roles_withheld_reason"] = (
                "DCS supplies no dependency parse for this chapter. Roles read from case "
                "were measured against the parse at 24.3% wrong even under the tightened "
                "clause gate, so none is asserted. Gated candidates are in "
                "role_candidates.jsonl."
            )
        assertions.append(record)

        if not parsed and gate_ok and len(finite) == 1:
            verb_view = next(t for t in view if t.raw is token)
            merged, refusals = C.case_scoped_roles(
                view, verb_view, predicate, person, feats.get("Voice")
            )
            for reason in refusals:
                diagnostics[reason.lower()] += 1
            if merged:
                cand = []
                for head, role, prefix in merged:
                    cand.append(
                        _filler(
                            head.raw,
                            role,
                            head.case,
                            entities,
                            locator + ": " + str(head.case)
                            + " beside the finite verb, clause gate cleared",
                            prefix,
                        ).as_dict()
                    )
                    diagnostics["candidate_role:" + role] += 1
                candidates.append(
                    {
                        "predicate": predicate,
                        "frame": frame,
                        "verb_surface": token["misc"].get("Unsandhied") or token["form"],
                        "scope": scope,
                        "role_candidates": cand,
                    }
                )
                diagnostics["candidate_assertions"] += 1
        elif not parsed and len(finite) > 1:
            diagnostics["candidate_scopes_refused_multiple_finite_verbs"] += 1

    return assertions, candidates, diagnostics


def _filler(child, role, case, entities, evidence, compound_prefix=""):
    """Build one role filler.

    ``compound_prefix`` exists because DCS splits a nominal compound into one token per
    member and only the last member carries the case. Recording that last member alone
    reports "kṣitim" where the verse has "asurakṣitim" -- a fragment presented as a word.
    """
    ftype, ekey, elabel = entities.classify(child["lemma"], child["upos"])
    return L.Filler(
        role=role,
        surface=compound_prefix + (child["misc"].get("Unsandhied") or child["form"]),
        lemma=child["lemma"],
        case=case,
        upos=child["upos"],
        filler_type=ftype,
        entity_key=ekey,
        entity_label=elabel,
        proposed_role=role in L.PROPOSED_ROLES,
        evidence=evidence,
    )


def run(dcs_dir, prefix, hymn_of_file, verses_by_hymn, locator_of):
    rootmap = L.RootMap(os.path.join(REGISTRY, "action_root_map.yaml"))
    entities = L.EntityIndex(
        os.path.join(REGISTRY, "lexical_aliases.yaml"),
        os.path.join(REGISTRY, "concepts.yaml"),
    )
    stats = collections.Counter()
    predicates = collections.Counter()
    roles = collections.Counter()
    filler_types = collections.Counter()
    unresolved_reasons = collections.Counter()
    out = collections.defaultdict(list)
    candidates = collections.defaultdict(list)
    hymn_report = []

    for filename in sorted(os.listdir(dcs_dir)):
        if not filename.startswith(prefix):
            continue
        hymn = hymn_of_file(filename)
        if hymn is None:
            continue
        verses = verses_by_hymn.get(hymn)
        if not verses:
            stats["hymns_without_our_verses"] += 1
            hymn_report.append({"hymn": str(hymn), "status": "NO_MATCHING_HYMN_IN_OUR_SPINE"})
            continue
        sentences = list(parse_conllu(os.path.join(dcs_dir, filename)))
        stats["hymns_processed"] += 1
        stats["sentences_processed"] += len(sentences)
        for _, _, tokens in sentences:
            stats["tokens_processed"] += len(tokens)
        assignments, diag = align_hymn(sentences, verses)
        if diag["hymn_match"] < HYMN_MATCH_FLOOR:
            stats["hymns_refused_below_match_floor"] += 1
            unresolved_reasons["HYMN_BELOW_MATCH_FLOOR"] += len(sentences)
            hymn_report.append(
                {
                    "hymn": str(hymn),
                    "status": "REFUSED_HYMN_BELOW_MATCH_FLOOR",
                    "hymn_match": round(diag["hymn_match"], 4),
                    "sentences": len(sentences),
                }
            )
            continue
        stats["hymns_aligned"] += 1
        hymn_report.append(
            {
                "hymn": str(hymn),
                "status": "ALIGNED",
                "hymn_match": round(diag["hymn_match"], 4),
                "sentences": len(sentences),
                "verses": len(verses),
            }
        )
        for index, key, fraction, concentration, reason in assignments:
            sent_id, text, tokens = sentences[index]
            if key is None:
                stats["sentences_unresolved"] += 1
                unresolved_reasons[reason] += 1
                continue
            stats["sentences_aligned"] += 1
            locator = locator_of(filename, sent_id)
            found, found_candidates, diagnostics = roles_for_sentence(
                tokens, rootmap, entities, locator
            )
            for cand in found_candidates:
                candidates[key].append({**cand, "sent_id": sent_id, "locator": locator})
            for name, count in diagnostics.items():
                stats[name] += count
            for assertion in found:
                predicates[assertion["predicate"]] += 1
                for filler in assertion["roles"]:
                    roles[filler["role"]] += 1
                    filler_types[filler["filler_type"]] += 1
                out[key].append(
                    {
                        "assertion": assertion,
                        "sent_id": sent_id,
                        "locator": locator,
                        "align_fraction": round(fraction, 4),
                        "align_concentration": round(concentration, 4),
                        "sentence_text": text,
                    }
                )
            if not found:
                stats["sentences_yielding_no_assertion"] += 1

    return {
        "assertions": out,
        "candidates": candidates,
        "stats": dict(stats),
        "predicates": dict(predicates),
        "roles": dict(roles),
        "filler_types": dict(filler_types),
        "unresolved_reasons": dict(unresolved_reasons),
        "hymn_report": hymn_report,
    }
