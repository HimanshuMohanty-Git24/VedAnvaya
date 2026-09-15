"""Stage 3: score the graph's claims against published human annotation.

The adjudicator is the Treebank of Vedic Sanskrit (UD_Sanskrit-Vedic, CC BY-SA 4.0):
27,182 sentences, human-validated lemmas and morphology, annotated by Scarlata,
Ackermann, Hellwig, Biagetti and Sellmer. No model of ours decides anything here.

Why the claim is decomposed rather than scored whole
----------------------------------------------------
Every alias-matching layer in this graph makes a compound claim: *surface form A occurs
in this verse, and A is a form of the word this entity names.* Scored as one unit it
cannot be acted on, and worse, it manufactures defects: our registry prints the deity of
the waters as ``āpaḥ`` and the treebank prints its lemma as ``ap``, which is the same
word under two citation conventions. A first pass of this script reported 196 devata
mentions as refuted, and almost all of them were that.

So it is scored in three separate places:

H1  OCCURRENCE   Does a human-annotated token with this surface form exist in this verse?
                 A failure here is a phantom: the pipeline matched a string that is not a
                 word of this verse. Decided per edge, no bridge needed.
H2  RESOLUTION   Given the token exists, is its human lemma the lemma that surface form
                 carries everywhere else in 206,440 human-annotated words? A failure here
                 is a surface that is ambiguous in the corpus and was resolved one way.
                 Decided per edge against a table built from the treebank alone.
H3  SOUNDNESS    Is that lemma the word this entity actually names? This is the only part
                 that needs judgement about our registry, it is decided once per alias
                 rather than once per edge, and the whole table is written out so a
                 reader can check it. 1,668 rows, not 31,000.

H3 is deliberately last and deliberately small, because it is the only step this agent
cannot ground in someone else's annotation.
"""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib_align import containment, deaccent, parse_conllu, skeleton  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1])
VERSE_COVERAGE_FLOOR = 0.80
ALIAS_PURITY_FLOOR = 0.80
ZURICH_LEMMA = re.compile(r"\(([^;()]+)-;")


def norm(text: str) -> str:
    return deaccent(text or "").lower().strip()


#: Folding used ONLY to test whether two citation conventions name the same word.
#: Never used for token matching, where these distinctions are the letters themselves.
_FOLD = str.maketrans(
    {
        "ā": "a", "ī": "i", "ū": "u", "ṛ": "r", "ṝ": "r",
        "ḷ": "l", "ṃ": "m", "ṁ": "m", "ḥ": "", "ś": "s",
        "ṣ": "s", "ñ": "n", "ṅ": "n", "ṇ": "n", "ṭ": "t",
        "ḍ": "d", "ḱ": "k", "ē": "e", "ō": "o",
    }
)


def fold(text: str) -> str:
    return norm(text).translate(_FOLD).rstrip("-")


def same_word(left: str, right: str) -> bool:
    """Two citation forms plausibly name one word: a shared fold or a 3-char stem."""
    a, b = fold(left), fold(right)
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = sorted((a, b), key=len)
    return len(shorter) >= 3 and longer.startswith(shorter)


def main() -> None:
    alignment = json.loads((SCRATCH / "stage1_alignment.json").read_text(encoding="utf-8"))
    graph = json.loads((SCRATCH / "stage2_graph.json").read_text(encoding="utf-8"))

    # ------------------------------------------------ the human annotation, indexed
    sentences = []
    for split in ("train", "dev", "test"):
        sentences.extend(parse_conllu(SCRATCH / f"sa_vedic-ud-{split}.conllu"))

    form_lemmas: dict[str, collections.Counter] = collections.defaultdict(
        collections.Counter
    )
    words = 0
    for sentence in sentences:
        for form, lemma in zip(sentence.forms, sentence.lemmas):
            form_lemmas[norm(form)][norm(lemma)] += 1
            words += 1

    aligned = [r for r in alignment["records"] if r["align_status"] == "ALIGNED"]
    per_mantra: dict[str, dict] = {}
    for record in aligned:
        bucket = per_mantra.setdefault(
            record["canonical_key"],
            {
                "lemmas": collections.Counter(),
                "tokens": [],
                "sent_ids": [],
                "annotators": set(),
                "veda": record["canonical_key"].split(":")[1],
            },
        )
        bucket["sent_ids"].append(record["sent_id"])
        bucket["annotators"].update(record["annotators"])
        for form, lemma, upos, feats in zip(
            record["forms"], record["lemmas"], record["upos"], record["feats"]
        ):
            bucket["lemmas"][norm(lemma)] += 1
            bucket["tokens"].append(
                {"form": norm(form), "lemma": norm(lemma), "upos": upos, "feats": feats}
            )

    verse_text: dict[str, str] = {}
    for row in graph["texts"]:
        if len(row["text"] or "") > len(verse_text.get(row["key"], "")):
            verse_text[row["key"]] = row["text"]
    for key, bucket in per_mantra.items():
        verse = skeleton(verse_text.get(key, ""))
        annotated = "".join(token["form"] for token in bucket["tokens"])
        bucket["verse_coverage"] = round(containment(verse, annotated), 4) if verse else 0.0
        bucket["annotators"] = sorted(bucket["annotators"])
    covered = {
        key for key, b in per_mantra.items() if b["verse_coverage"] >= VERSE_COVERAGE_FLOOR
    }

    # ------------------------------------------------ registries and the two bridges
    entities: dict[str, dict] = {}
    for row in graph["devatas"]:
        entities[row["key"]] = {
            "kind": "DEVATA",
            "label": row["label_iast"],
            "aliases": row["aliases"] or [],
        }
    for row in graph["concepts"]:
        entities[row["key"]] = {
            "kind": "CONCEPT",
            "label": row["label_sa"],
            "aliases": row["aliases_sa"] or [],
        }

    # Bridge 1 (deities): the Zurich/VedaWeb lemma the graph already cites in its own
    # evidence for every Rigvedic mention. A third published annotation project, so the
    # deity-to-lemma link is not this agent's string surgery.
    zurich: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in graph["mentions_devata"]:
        for item in json.loads(row["evidence"] or "[]"):
            for match in ZURICH_LEMMA.finditer(item.get("quote", "")):
                zurich[row["devata"]][norm(match.group(1))] += 1
    zurich_bridge = {key: counter.most_common(1)[0][0] for key, counter in zurich.items()}

    # Bridge 1b (hand-curated): two citation conventions that name one word. Only the
    # entries whose grounds do not begin REJECTED are applied.
    allomorph_file = pathlib.Path(__file__).parent / "bridge_allomorphs.json"
    allomorphs: dict[str, str] = {}
    allomorph_doc = json.loads(allomorph_file.read_text(encoding="utf-8"))
    for entry in allomorph_doc["allomorphs"]:
        if not entry["grounds"].startswith("REJECTED"):
            allomorphs[entry["entity_key"]] = norm(entry["human_lemma"])

    # Bridge 2 (aliases): what lemma each surface form carries in the human corpus.
    alias_rows = []
    for key, entity in sorted(entities.items()):
        for alias in entity["aliases"]:
            observed = form_lemmas.get(norm(alias), collections.Counter())
            occurrences = sum(observed.values())
            if occurrences == 0:
                alias_rows.append(
                    {
                        "entity_key": key,
                        "entity_kind": entity["kind"],
                        "entity_label": entity["label"],
                        "alias": alias,
                        "treebank_occurrences": 0,
                        "dominant_human_lemma": None,
                        "dominant_share": None,
                        "human_lemmas_observed": {},
                        "h2_verdict": "UNATTESTED_AS_A_TOKEN",
                        "h3_verdict": "UNDECIDABLE_NO_ATTESTATION",
                    }
                )
                continue
            dominant, count = observed.most_common(1)[0]
            share = count / occurrences
            h2 = "UNAMBIGUOUS_SURFACE" if share >= ALIAS_PURITY_FLOOR else "AMBIGUOUS_SURFACE"
            if same_word(dominant, entity["label"]):
                h3 = "SOUND_OWN_LEMMA"
            elif key in zurich_bridge and same_word(dominant, zurich_bridge[key]):
                h3 = "SOUND_BY_ZURICH_LEMMA"
            elif key in allomorphs and same_word(dominant, allomorphs[key]):
                h3 = "SOUND_BY_CURATED_ALLOMORPH"
            else:
                h3 = "REGISTRY_SYNONYM_EXPANSION"
            alias_rows.append(
                {
                    "entity_key": key,
                    "entity_kind": entity["kind"],
                    "entity_label": entity["label"],
                    "alias": alias,
                    "treebank_occurrences": occurrences,
                    "dominant_human_lemma": dominant,
                    "dominant_share": round(share, 4),
                    "human_lemmas_observed": dict(observed.most_common(6)),
                    "h2_verdict": h2,
                    "h3_verdict": h3,
                }
            )
    alias_index = {(r["entity_key"], norm(r["alias"])): r for r in alias_rows}

    # An entity's human lemma set: every route, each carrying where it came from.
    lemma_set: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for key, entity in entities.items():
        if key in zurich_bridge:
            lemma_set[key][zurich_bridge[key]] = "ZURICH_ANNOTATION"
        if key in allomorphs:
            lemma_set[key][allomorphs[key]] = "CURATED_ALLOMORPH"
        for row in alias_rows:
            if row["entity_key"] != key or row["dominant_human_lemma"] is None:
                continue
            if row["h3_verdict"].startswith("SOUND"):
                lemma_set[key].setdefault(
                    row["dominant_human_lemma"], "ALIAS_DOMINANT_LEMMA"
                )
        for lemma in list(form_lemmas):
            if lemma == fold(entity["label"] or "") and lemma:
                lemma_set[key].setdefault(lemma, "LABEL_EXACT")

    # Word inventory of our own canonical text, per verse. Used to separate a pipeline
    # artifact from a limit of the reference: the treebank is unsandhied, so a sandhied
    # alias such as apo (for apah before a voiced sound) can never be one of its tokens.
    # If the alias is a whole word of our text and the reference simply does not carry
    # that form, the edge is UNDECIDED here rather than refuted. If it is not a word of
    # our text either, the pipeline matched inside a word and that is a real defect.
    own_words: dict[str, set[str]] = {}
    for mantra_key, text in verse_text.items():
        own_words[mantra_key] = {
            norm(word) for word in re.split(r"[\s|।॥]+", deaccent(text or "")) if word
        }

    # ------------------------------------------------ per-edge adjudication
    def adjudicate(key: str, entity_key: str, claimed: list[str]) -> dict:
        bucket = per_mantra.get(key)
        if bucket is None:
            return {"h1": "NO_ANNOTATION", "h2": None, "verdict": "NOT_ADJUDICABLE"}
        # H1: is any claimed surface form a human-annotated token of this verse?
        token = None
        used = None
        for form in claimed or []:
            candidate = next(
                (t for t in bucket["tokens"] if t["form"] == norm(form)), None
            )
            if candidate is not None:
                token, used = candidate, form
                break
        if token is None:
            # the entity's own lemma may still be present under a form the registry
            # does not list, which is a recall fact and not an occurrence failure
            own = [
                lemma for lemma in bucket["lemmas"] if lemma in lemma_set.get(entity_key, {})
            ]
            if own:
                return {
                    "h1": "LEMMA_PRESENT_FORM_NOT_LISTED",
                    "h2": "CONSISTENT",
                    "verdict": "CONFIRMED",
                    "human_lemma": own[0],
                }
            if bucket["verse_coverage"] < VERSE_COVERAGE_FLOOR:
                return {
                    "h1": "UNDECIDED",
                    "h2": None,
                    "verdict": "UNDECIDED_PARTIAL_ANNOTATION",
                    "verse_coverage": bucket["verse_coverage"],
                }
            words_here = own_words.get(key, set())
            if any(norm(form) in words_here for form in claimed or []):
                return {
                    "h1": "SANDHI_FORM_ABSENT_FROM_UNSANDHIED_REFERENCE",
                    "h2": None,
                    "verdict": "UNDECIDED_REFERENCE_CANNOT_SEE_THIS_FORM",
                    "verse_coverage": bucket["verse_coverage"],
                }
            return {
                "h1": "PHANTOM_TOKEN",
                "h2": None,
                "verdict": "REFUTED",
                "fp_class": "MATCHED_INSIDE_A_WORD_NOT_A_WORD",
                "verse_coverage": bucket["verse_coverage"],
            }
        # H2: did the surface resolve to the lemma it carries everywhere else?
        alias_row = alias_index.get((entity_key, norm(used)))
        expected = alias_row["dominant_human_lemma"] if alias_row else None
        in_entity_set = token["lemma"] in lemma_set.get(entity_key, {})
        if in_entity_set:
            return {
                "h1": "TOKEN_PRESENT",
                "h2": "CONSISTENT",
                "verdict": "CONFIRMED",
                "human_lemma": token["lemma"],
                "claimed_form": used,
            }
        if expected is not None and token["lemma"] == expected:
            return {
                "h1": "TOKEN_PRESENT",
                "h2": "CONSISTENT",
                "verdict": "CONFIRMED_VIA_UNSOUND_ALIAS",
                "fp_class": "REGISTRY_ALIAS_NOT_THE_ENTITY_LEMMA",
                "human_lemma": token["lemma"],
                "claimed_form": used,
            }
        return {
            "h1": "TOKEN_PRESENT",
            "h2": "RESOLVED_TO_ANOTHER_WORD",
            "verdict": "REFUTED",
            "fp_class": "AMBIGUOUS_SURFACE_WRONG_WORD",
            "human_lemma": token["lemma"],
            "human_upos": token["upos"],
            "expected_lemma": expected,
            "claimed_form": used,
        }

    scored: dict[str, list[dict]] = {}

    def score(name, rows, entity_of, forms_of, strata_of) -> None:
        results = []
        for row in rows:
            entity_key = entity_of(row)
            claimed = forms_of(row) or []
            outcome = adjudicate(row["key"], entity_key, claimed)
            alias_h2 = sorted(
                {
                    alias_index[(entity_key, norm(f))]["h2_verdict"]
                    for f in claimed
                    if (entity_key, norm(f)) in alias_index
                }
            )
            alias_h3 = sorted(
                {
                    alias_index[(entity_key, norm(f))]["h3_verdict"]
                    for f in claimed
                    if (entity_key, norm(f)) in alias_index
                }
            )
            results.append(
                {
                    "canonical_key": row["key"],
                    "veda": row["key"].split(":")[1],
                    "entity_key": entity_key,
                    "claimed_forms": claimed,
                    "strata": strata_of(row),
                    "alias_h2": alias_h2,
                    "alias_h3": alias_h3,
                    **outcome,
                }
            )
        scored[name] = results
        print("-- {}: {}".format(name, len(results)))
        print("   verdicts:", dict(collections.Counter(r["verdict"] for r in results)))
        print(
            "   fp classes:",
            dict(collections.Counter(r["fp_class"] for r in results if r.get("fp_class"))),
        )

    def about_forms(row) -> list[str]:
        entity = entities.get(row["concept"]) or {}
        quotes = " ".join(
            item.get("quote", "") for item in json.loads(row["evidence"] or "[]")
        )
        folded = skeleton(quotes)
        spaced = " " + " ".join(norm(w) for w in deaccent(quotes).lower().split()) + " "
        return [
            alias
            for alias in entity.get("aliases", [])
            if " " + norm(alias) + " " in spaced or norm(alias) in folded
        ]

    score(
        "mentions_devata", graph["mentions_devata"], lambda r: r["devata"],
        lambda r: r["forms"],
        lambda r: {"tier": r["tier"], "certainty": r["certainty"], "basis": r["basis"],
                   "method": r["method"]},
    )
    score(
        "mentions_entity", graph["mentions_entity"], lambda r: r["entity"],
        lambda r: r["aliases"],
        lambda r: {"tier": r["tier"], "method": r["method"],
                   "theonym_ambiguous": r["theonym_ambiguous"]},
    )
    score(
        "about_concept", graph["about_concept"], lambda r: r["concept"], about_forms,
        lambda r: {"confidence": r["confidence"], "method": r["method"],
                   "tier": r["tier"], "evidence_basis": r["evidence_basis"]},
    )

    # ------------------------------------------------ recall, with FN classes
    def recall(layer: str, kind: str) -> dict:
        asserted: dict[str, set[str]] = collections.defaultdict(set)
        for row in scored[layer]:
            asserted[row["canonical_key"]].add(row["entity_key"])
        universe = {
            key: set(lemma_set[key])
            for key, entity in entities.items()
            if entity["kind"] == kind and lemma_set.get(key)
        }
        alias_forms = {
            key: {norm(a) for a in entity["aliases"]} for key, entity in entities.items()
        }
        found = 0
        fn_classes: collections.Counter = collections.Counter()
        misses: list[dict] = []
        per_veda: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
        for key in sorted(covered):
            bucket = per_mantra[key]
            for entity_key, lemmas in universe.items():
                hit = next(
                    (t for t in bucket["tokens"] if t["lemma"] in lemmas), None
                )
                if hit is None:
                    continue
                if entity_key in asserted.get(key, set()):
                    found += 1
                    per_veda[bucket["veda"]][0] += 1
                    continue
                per_veda[bucket["veda"]][1] += 1
                listed = hit["form"] in alias_forms.get(entity_key, set())
                fn_class = (
                    "ALIAS_LISTED_BUT_NOT_MATCHED" if listed
                    else "INFLECTION_ABSENT_FROM_ALIAS_LIST"
                )
                fn_classes[fn_class] += 1
                if len(misses) < 500:
                    misses.append(
                        {
                            "canonical_key": key,
                            "veda": bucket["veda"],
                            "entity_key": entity_key,
                            "human_form": hit["form"],
                            "human_lemma": hit["lemma"],
                            "fn_class": fn_class,
                        }
                    )
        missed = sum(fn_classes.values())
        return {
            "covered_verses": len(covered),
            "entities_bridged": len(universe),
            "human_attested_pairs": found + missed,
            "asserted_by_graph": found,
            "missed_by_graph": missed,
            "recall": round(found / (found + missed), 4) if found + missed else None,
            "fn_classes": dict(fn_classes),
            "by_veda": {
                veda: {
                    "found": c[0], "missed": c[1],
                    "recall": round(c[0] / (c[0] + c[1]), 4) if c[0] + c[1] else None,
                }
                for veda, c in sorted(per_veda.items())
            },
            "miss_sample": misses,
        }

    recalls = {
        "mentions_devata": recall("mentions_devata", "DEVATA"),
        "about_concept": recall("about_concept", "CONCEPT"),
        "mentions_entity": recall("mentions_entity", "CONCEPT"),
    }
    for name, value in recalls.items():
        print("-- recall {}: {} ({}/{}) fn={}".format(
            name, value["recall"], value["asserted_by_graph"],
            value["human_attested_pairs"], value["fn_classes"]))

    (SCRATCH / "stage3_scores.json").write_text(
        json.dumps(
            {
                "treebank": {
                    "human_annotated_words": words,
                    "sentences": len(sentences),
                    "distinct_surface_forms": len(form_lemmas),
                },
                "coverage": {
                    "mantras_with_annotation": len(per_mantra),
                    "covered_at_floor": len(covered),
                    "floor": VERSE_COVERAGE_FLOOR,
                    "covered_by_veda": dict(
                        collections.Counter(per_mantra[k]["veda"] for k in covered)
                    ),
                },
                "zurich_bridge": zurich_bridge,
                "entity_lemma_sets": {k: v for k, v in lemma_set.items() if v},
                "allomorph_bridge_applied": allomorphs,
                "alias_rows": alias_rows,
                "scored": scored,
                "recall": recalls,
                "per_mantra": {
                    k: {
                        "veda": b["veda"], "verse_coverage": b["verse_coverage"],
                        "annotators": b["annotators"], "sent_ids": b["sent_ids"],
                        "lemmas": dict(b["lemmas"]), "tokens": b["tokens"],
                    }
                    for k, b in per_mantra.items()
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print("alias rows:", len(alias_rows))
    print("alias H2:", dict(collections.Counter(r["h2_verdict"] for r in alias_rows)))
    print("alias H3:", dict(collections.Counter(r["h3_verdict"] for r in alias_rows)))
    print("zurich bridge entries:", len(zurich_bridge))
    print("covered verses:", len(covered), "of", len(per_mantra))


if __name__ == "__main__":
    main()
