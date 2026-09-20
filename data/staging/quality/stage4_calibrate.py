"""Stage 4: calibration, and independent checks on the layers whose confidence is 1.0.

The product's `confidence` property is treated by clients as a probability: the graph API
exposes `min_confidence` and a researcher who filters on it believes they have raised
precision. This stage measures whether the number behaves like one.

Three measurements, each grounded outside the pipeline that produced the claim:

* the alias-matched layers are scored from stage 3, which used published human annotation;
* metre is scored by counting the syllables in the verse, because a metre name is a claim
  about syllable count and the text settles it without anyone's opinion;
* per-verse attribution is scored against itself, by finding mantras that carry both a
  source-explicit value and an inherited one and asking whether the two agree.

Metre needs a stated tolerance and gets one. Vedic metre is counted on the restored text,
where hiatus and disyllabic readings recover syllables that the transmitted sandhied
saṃhitā spelling has lost, so a correct triṣṭubh routinely counts 43 rather than 44. A
tolerance band is therefore reported rather than a single pass/fail, and only a gross
divergence is called a defect.
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib_align import deaccent, to_iast  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1])

#: Nominal syllable totals of the metres that carry a fixed count. Metres whose count is
#: variable, or which are defined by a pattern rather than a total, are excluded rather
#: than given a number they do not have.
METRE_SYLLABLES = {
    "gayatri": 24, "gāyatrī": 24,
    "anustubh": 32, "anuṣṭubh": 32, "ānuṣṭubham": 32, "anustup": 32,
    "tristubh": 44, "triṣṭubh": 44,
    "jagati": 48, "jagatī": 48,
    "pankti": 40, "paṅkti": 40,
    "brhati": 36, "bṛhatī": 36, "brhatī": 36,
    "satobrhati": 36, "satobṛhatī": 36,
    "usnih": 28, "uṣṇih": 28, "usnih_": 28,
    "kakubh": 28,
    "mahapankti": 48, "mahāpaṅkti": 48,
    "sakvari": 56, "śakvarī": 56,
    "atijagati": 52, "atijagatī": 52,
    "atisakvari": 60, "atiśakvarī": 60,
    "asti": 64, "aṣṭi": 64,
    "atyasti": 68, "atyaṣṭi": 68,
    "dhrti": 72, "dhṛti": 72,
    "atidhrti": 76, "atidhṛti": 76,
    "viraj": 40, "virāj": 40,
    "dvipada_viraj": 20, "dvipadā virāj": 20,
    "ekapada": 8,
    "prastarapankti": 44, "prastārapaṅkti": 44,
}

_VOWELS = re.compile(r"ai|au|[aāiīuūṛṝḷḹeo]")


def syllables(text: str) -> int:
    """Count vowel nuclei in an IAST or Devanagari verse.

    A syllable in Sanskrit is one vowel nucleus, so counting nuclei counts syllables.
    The two-character vowels are matched first so *ai* and *au* are not counted twice.
    """
    folded = deaccent(to_iast(text or "")).lower()
    folded = re.sub(r"[|।॥\d]", " ", folded)
    return len(_VOWELS.findall(folded))


def fold_metre(label: str) -> str:
    return deaccent(label or "").lower().strip().replace(" ", "_")


def bucket_accuracy(rows: list[dict]) -> dict:
    """Observed accuracy of a bucket, counting only the rows the reference could decide."""
    counts = collections.Counter(row["verdict"] for row in rows)
    strict_ok = counts["CONFIRMED"]
    lexical_ok = counts["CONFIRMED"] + counts["CONFIRMED_VIA_UNSOUND_ALIAS"]
    refuted = counts["REFUTED"]
    decided = lexical_ok + refuted
    strict_decided = strict_ok + counts["CONFIRMED_VIA_UNSOUND_ALIAS"] + refuted
    return {
        "edges": len(rows),
        "adjudicated": decided,
        "undecided_partial_annotation": counts["UNDECIDED_PARTIAL_ANNOTATION"],
        "not_adjudicable": counts["NOT_ADJUDICABLE"],
        "confirmed_own_lemma": strict_ok,
        "confirmed_via_unsound_alias": counts["CONFIRMED_VIA_UNSOUND_ALIAS"],
        "refuted": refuted,
        "lexical_precision": round(lexical_ok / decided, 4) if decided else None,
        "strict_precision": round(strict_ok / strict_decided, 4) if strict_decided else None,
        "fp_classes": dict(
            collections.Counter(r["fp_class"] for r in rows if r.get("fp_class"))
        ),
    }


def main() -> None:
    scores = json.loads((SCRATCH / "stage3_scores.json").read_text(encoding="utf-8"))
    graph = json.loads((SCRATCH / "stage2_graph.json").read_text(encoding="utf-8"))
    per_mantra = scores["per_mantra"]

    out: dict[str, object] = {}

    # ------------------------------------------------------------- calibration proper
    calibration = []

    def add_buckets(layer: str, key_of, nominal_of, label: str) -> None:
        groups: dict[object, list[dict]] = collections.defaultdict(list)
        for row in scores["scored"][layer]:
            groups[key_of(row)].append(row)
        for bucket_key, rows in sorted(groups.items(), key=lambda kv: str(kv[0])):
            calibration.append(
                {
                    "layer": layer,
                    "bucket": str(bucket_key),
                    "bucket_axis": label,
                    "nominal_confidence": nominal_of(bucket_key, rows),
                    **bucket_accuracy(rows),
                }
            )

    add_buckets(
        "about_concept",
        lambda r: (r["strata"]["confidence"], r["strata"]["method"]),
        lambda k, rows: k[0],
        "confidence x method",
    )
    add_buckets(
        "mentions_devata",
        lambda r: (r["veda"], r["strata"]["certainty"], r["strata"]["tier"]),
        lambda k, rows: None,
        "veda x referent_certainty x quality_tier",
    )
    add_buckets(
        "mentions_entity",
        lambda r: (r["strata"]["method"], r["strata"]["tier"]),
        lambda k, rows: None,
        "method x quality_tier",
    )
    out["calibration"] = calibration

    # per-alias calibration: the axis a per-row sample cannot see
    per_alias = []
    for layer in ("about_concept", "mentions_entity", "mentions_devata"):
        groups: dict[tuple, list[dict]] = collections.defaultdict(list)
        for row in scores["scored"][layer]:
            for form in row["claimed_forms"] or ["<none>"]:
                groups[(row["entity_key"], form)].append(row)
        for (entity, alias), rows in groups.items():
            summary = bucket_accuracy(rows)
            if summary["adjudicated"] >= 5:
                per_alias.append(
                    {"layer": layer, "entity_key": entity, "alias": alias, **summary}
                )
    per_alias.sort(key=lambda r: (r["lexical_precision"] or 1.0, -r["adjudicated"]))
    out["per_alias_precision"] = per_alias

    # ------------------------------------------- does DEITY_CERTAIN mean what it says?
    # The referent rule's own stated basis for "certain" is a vocative address. The
    # treebank annotates case by hand, so the rule can be tested against its own
    # criterion rather than against a proxy.
    certainty_rows = []
    for row in graph["mentions_devata"]:
        bucket = per_mantra.get(row["key"])
        if bucket is None:
            continue
        claimed = {(f or "").lower() for f in (row["forms"] or [])}
        from lib_align import deaccent as _deaccent

        claimed = {_deaccent(f) for f in claimed}
        cases = set()
        for token in bucket["tokens"]:
            if token["form"] in claimed:
                for part in (token["feats"] or "").split("|"):
                    if part.startswith("Case="):
                        cases.add(part.split("=", 1)[1])
        certainty_rows.append(
            {
                "canonical_key": row["key"],
                "veda": row["key"].split(":")[1],
                "devata": row["devata"],
                "certainty": row["certainty"],
                "basis": row["basis"],
                "tier": row["tier"],
                "graph_claimed_roles": row["roles"],
                "human_cases": sorted(cases),
                "human_token_found": bool(cases),
                "human_says_vocative": "Voc" in cases,
            }
        )
    by_certainty: dict[str, dict] = {}
    for row in certainty_rows:
        if not row["human_token_found"]:
            continue
        entry = by_certainty.setdefault(
            f"{row['certainty']}|{row['basis']}",
            {"n": 0, "human_vocative": 0},
        )
        entry["n"] += 1
        if row["human_says_vocative"]:
            entry["human_vocative"] += 1
    for entry in by_certainty.values():
        entry["vocative_share"] = round(entry["human_vocative"] / entry["n"], 4)
    out["certainty_rows"] = certainty_rows
    out["certainty_vs_human_case"] = by_certainty

    # ------------------------------------------------------------- metre, independently
    verse_text: dict[str, str] = {}
    for row in graph["texts"]:
        if len(row["text"] or "") > len(verse_text.get(row["key"], "")):
            verse_text[row["key"]] = row["text"]

    metre_rows = []
    for row in graph["has_chandas"]:
        nominal = METRE_SYLLABLES.get(fold_metre(row["label"])) or METRE_SYLLABLES.get(
            fold_metre(row["chandas"] or "").split(":")[-1]
        )
        counted = syllables(verse_text.get(row["key"], ""))
        if nominal is None:
            verdict = "METRE_HAS_NO_FIXED_COUNT"
            delta = None
        else:
            delta = counted - nominal
            if abs(delta) <= 1:
                verdict = "AGREES"
            elif abs(delta) <= 3:
                verdict = "AGREES_WITHIN_RESTORATION_TOLERANCE"
            else:
                verdict = "GROSS_DIVERGENCE"
        metre_rows.append(
            {
                "canonical_key": row["key"],
                "veda": row["key"].split(":")[1],
                "chandas": row["chandas"],
                "label": row["label"],
                "tier": row["tier"],
                "precision_axis": row["precision"],
                "confidence": row["confidence"],
                "nominal_syllables": nominal,
                "counted_syllables": counted,
                "delta": delta,
                "verdict": verdict,
            }
        )
    out["metre_rows"] = metre_rows
    metre_by_tier: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    for row in metre_rows:
        metre_by_tier[f"{row['tier']}|{row['precision_axis']}"][row["verdict"]] += 1
    out["metre_by_tier"] = {
        key: dict(value) for key, value in sorted(metre_by_tier.items())
    }

    # ------------------------------------------------- attribution: inherited vs explicit
    def attribution_conflict(rows: list[dict], value_key: str) -> dict:
        by_key: dict[str, list[dict]] = collections.defaultdict(list)
        for row in rows:
            by_key[row["key"]].append(row)
        both = agree = disagree = 0
        examples = []
        for key, group in by_key.items():
            explicit = {r[value_key] for r in group if r["tier"] == "TIER_A"}
            inherited = {r[value_key] for r in group if r["tier"] == "TIER_B"}
            if not explicit or not inherited:
                continue
            both += 1
            if explicit & inherited:
                agree += 1
            else:
                disagree += 1
                if len(examples) < 40:
                    examples.append(
                        {
                            "canonical_key": key,
                            "source_explicit": sorted(explicit),
                            "inherited": sorted(inherited),
                        }
                    )
        return {
            "mantras_carrying_both": both,
            "agree": agree,
            "disagree": disagree,
            "inheritance_agreement": round(agree / both, 4) if both else None,
            "examples": examples,
        }

    out["attribution_overlap"] = {
        "has_devata": attribution_conflict(graph["has_devata"], "devata"),
        "has_rishi": attribution_conflict(graph["has_rishi"], "rishi"),
        "has_chandas": attribution_conflict(graph["has_chandas"], "chandas"),
    }

    # dedication against what the verse itself names, per tier
    lemma_sets = scores["entity_lemma_sets"]
    dedication = []
    for row in graph["has_devata"]:
        bucket = per_mantra.get(row["key"])
        if bucket is None:
            continue
        lemmas = set(bucket["lemmas"])
        target = set(lemma_sets.get(row["devata"], {}))
        other = {
            entity
            for entity, entity_lemmas in lemma_sets.items()
            if entity.startswith("VG:DEVATA:") and lemmas & set(entity_lemmas)
        }
        dedication.append(
            {
                "canonical_key": row["key"],
                "veda": row["key"].split(":")[1],
                "devata": row["devata"],
                "tier": row["tier"],
                "precision_axis": row["precision"],
                "scope": row["scope"],
                "confidence": row["confidence"],
                "dedicatee_named_in_verse": bool(lemmas & target),
                "other_deity_named": sorted(other - {row["devata"]})[:4],
                "bridged": bool(target),
                "verse_coverage": bucket["verse_coverage"],
            }
        )
    out["dedication_rows"] = dedication
    ded_by_tier: dict[str, dict] = {}
    for row in dedication:
        if not row["bridged"] or row["verse_coverage"] < 0.80:
            continue
        key = f"{row['tier']}|{row['precision_axis']}|{row['scope']}"
        entry = ded_by_tier.setdefault(
            key, {"n": 0, "dedicatee_named": 0, "only_another_deity_named": 0}
        )
        entry["n"] += 1
        if row["dedicatee_named_in_verse"]:
            entry["dedicatee_named"] += 1
        elif row["other_deity_named"]:
            entry["only_another_deity_named"] += 1
    for entry in ded_by_tier.values():
        entry["named_share"] = round(entry["dedicatee_named"] / entry["n"], 4)
    out["dedication_by_tier"] = ded_by_tier

    # --------------------------------------- morphology-rule assertions vs human FEATS
    feat_case = {
        "Nom": "NOM", "Acc": "ACC", "Ins": "INS", "Dat": "DAT", "Abl": "ABL",
        "Gen": "GEN", "Loc": "LOC", "Voc": "VOC",
    }
    morph_rows = []
    for row in graph["semantic_assertions"]:
        props = row["props"]
        if props.get("derivation") != "MORPHOLOGY_RULE":
            continue
        bucket = per_mantra.get(row["key"])
        if bucket is None:
            continue
        surface = deaccent(props.get("verb_surface") or "").lower()
        token = next((t for t in bucket["tokens"] if t["form"] == surface), None)
        claimed_root = deaccent(props.get("root") or "").lower()
        result = {
            "canonical_key": row["key"],
            "assertion_id": props.get("assertion_id"),
            "predicate": props.get("predicate"),
            "tier": props.get("quality_tier"),
            "verb_surface": props.get("verb_surface"),
            "claimed_root": props.get("root"),
            "claimed_verb_features": props.get("verb_features"),
            "claimed_agent_case": props.get("agent_case"),
        }
        if token is None:
            result["verdict"] = "VERB_TOKEN_NOT_IN_HUMAN_ANNOTATION"
            morph_rows.append(result)
            continue
        feats = dict(
            part.split("=", 1) for part in (token["feats"] or "").split("|") if "=" in part
        )
        result["human_lemma"] = token["lemma"]
        result["human_upos"] = token["upos"]
        result["human_feats"] = token["feats"]
        root_ok = claimed_root and (
            token["lemma"] == claimed_root
            or token["lemma"].startswith(claimed_root)
            or claimed_root.startswith(token["lemma"])
        )
        claimed_person = (props.get("verb_features") or "").split("/")[0]
        human_person = feats.get("Person")
        person_ok = (
            claimed_person.isdigit()
            and human_person is not None
            and claimed_person == human_person
        )
        result["root_agrees"] = bool(root_ok)
        result["person_agrees"] = bool(person_ok)
        result["human_is_verb"] = token["upos"] in {"VERB", "AUX"}
        result["verdict"] = (
            "AGREES" if root_ok and (person_ok or human_person is None)
            else "DISAGREES"
        )
        morph_rows.append(result)
    out["morphology_rows"] = morph_rows
    out["morphology_summary"] = {
        "assertions_scored": len(morph_rows),
        "verdicts": dict(collections.Counter(r["verdict"] for r in morph_rows)),
        "root_agrees": sum(1 for r in morph_rows if r.get("root_agrees")),
        "root_disagrees": sum(
            1 for r in morph_rows if r.get("root_agrees") is False
        ),
        "person_agrees": sum(1 for r in morph_rows if r.get("person_agrees")),
        "human_says_not_a_verb": sum(
            1 for r in morph_rows if r.get("human_is_verb") is False
        ),
    }
    # the stripped-vocalic-r defect, measured rather than asserted from one example
    out["root_defect"] = {
        "single_letter_roots": dict(
            collections.Counter(
                r["claimed_root"] for r in morph_rows
                if r.get("claimed_root") and len(r["claimed_root"]) == 1
            )
        ),
        "note": (
            "A one-character Sanskrit verbal root is almost always a stripped vocalic "
            "letter: kr (kr-with-below-ring) stored as k. Same class as the "
            "SEARCH_DERIVATIVE defect Agent 2 found."
        ),
    }

    (SCRATCH / "stage4_calibration.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8"
    )

    print("== calibration buckets:", len(calibration))
    for row in calibration:
        if row["adjudicated"] >= 30:
            print(
                "  {:16s} {:56s} nominal={} n={:5d} lexical={} strict={}".format(
                    row["layer"], row["bucket"][:56], row["nominal_confidence"],
                    row["adjudicated"], row["lexical_precision"], row["strict_precision"],
                )
            )
    print("== metre by tier")
    for key, value in out["metre_by_tier"].items():
        print("  ", key, value)
    print("== attribution overlap")
    for key, value in out["attribution_overlap"].items():
        print("  ", key, {k: v for k, v in value.items() if k != "examples"})
    print("== dedication by tier")
    for key, value in ded_by_tier.items():
        print("  ", key, value)
    print("== morphology", out["morphology_summary"])
    print("== single-letter roots", out["root_defect"]["single_letter_roots"])
    print("== certainty vs human case")
    for key, value in sorted(by_certainty.items()):
        print("  {:44s} {}".format(key, value))
    print("== per-alias rows:", len(per_alias))
    for row in per_alias[:12]:
        print(
            "   {:16s} {:34s} {:14s} n={:4d} lexical={} strict={}".format(
                row["layer"], row["entity_key"][:34], row["alias"][:14],
                row["adjudicated"], row["lexical_precision"], row["strict_precision"],
            )
        )


if __name__ == "__main__":
    main()
