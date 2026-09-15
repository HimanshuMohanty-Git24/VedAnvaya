"""Samavedic semantic roles, and the only route by which the Samaveda can have any.

No morphological annotation of the Sāmaveda Saṃhitā exists. Three comprehensive
resources were enumerated independently for this campaign and all three are negative:
DCS's 271 corpora, UD_Sanskrit-Vedic's 57 texts and VedaWeb's 7 texts. The proof records
are in ``proofs/``.

But the Ārcika is largely Rigvedic borrowing, and our own graph already asserts the
borrowing: 1,662 of 1,844 Samavedic verses carry a deterministic reuse or parallel edge
to a Rigvedic verse. Where the letter skeleton of the Samavedic verse is *identical* to
that of the Rigvedic verse, the two are the same words, and the Rigvedic morphological
analysis of those words is the analysis of these. Nothing is inferred about the Samaveda
itself; what is transferred is a statement about a string.

The discipline is the identity requirement. Not "similar", not "a near parallel", not
"the Anukramaṇī says they correspond" — string equality of the skeletons, which is what
the graph's own ``VARIANT_OF``/``EXACT_PARALLEL_OF`` machinery calls the
SANDHI_INSENSITIVE level. Anything below that abstains, because a Samavedic verse
differs from its Rigvedic source precisely where the singers changed it, and a changed
word has a changed analysis. Section 1 of the brief forbids reusing another recension's
material because Sanskrit "looks similar"; it permits verified identical text, and that
is the only thing used here.

Two limits are stated on every row this produces:

* The verse is sung as a sāman with stobhas and a melodic text that is a different
  object from the Ārcika text. This layer says nothing about the gāna.
* The Samavedic reading is *not* independently morphologically analysed. Should an
  annotation of the Sāmaveda ever appear, these rows are the ones to re-derive first.
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib_roles as L  # noqa: E402


def run(sv_texts, rv_texts, rv_assertions, links):
    """Project Rigvedic assertions onto skeleton-identical Samavedic verses.

    ``links`` maps an SV canonical_key to a list of (rv_key, rel_type, score, match_level).
    """
    rv_skeleton = {key: L.skeleton(text) for key, text in rv_texts.items()}
    stats = collections.Counter()
    accepted = {}
    refused = {}

    for sv_key, sv_text in sv_texts.items():
        stats["passages_processed"] += 1
        sv_skeleton = L.skeleton(sv_text)
        candidates = links.get(sv_key) or []
        if not candidates:
            refused[sv_key] = {
                "reason": "NO_RIGVEDIC_PARALLEL_EDGE",
                "detail": "the graph asserts no reuse, parallel or variant edge from this "
                "verse to any Rigvedic verse, so there is no analysed text to transfer",
            }
            stats["no_parallel"] += 1
            continue
        best = None
        for rv_key, rel_type, score, match_level in candidates:
            other = rv_skeleton.get(rv_key)
            if other is None:
                continue
            identical = other == sv_skeleton
            contained = L.containment(sv_skeleton, other)
            if best is None or (identical, contained) > (best[3], best[4]):
                best = (rv_key, rel_type, score, identical, contained)
        if best is None:
            refused[sv_key] = {
                "reason": "PARALLEL_TARGET_HAS_NO_TEXT",
                "detail": "the parallel edge points at a Rigvedic verse for which no text "
                "version was retrievable",
            }
            stats["parallel_without_text"] += 1
            continue
        rv_key, rel_type, score, identical, contained = best
        if not identical:
            refused[sv_key] = {
                "reason": "SKELETON_NOT_IDENTICAL_TO_RIGVEDIC_SOURCE",
                "detail": (
                    f"closest Rigvedic parallel {rv_key} ({rel_type}) shares "
                    f"{contained:.4f} of this verse's letters but is not the same string; "
                    "a changed word has a changed analysis, so nothing is transferred"
                ),
                "rv_key": rv_key,
                "containment": round(contained, 4),
            }
            stats["not_identical"] += 1
            continue
        source_assertions = rv_assertions.get(rv_key)
        if not source_assertions:
            refused[sv_key] = {
                "reason": "IDENTICAL_BUT_RIGVEDIC_SOURCE_CARRIES_NO_ASSERTION",
                "detail": (
                    f"the text is identical to {rv_key}, but that verse yielded no "
                    "assertion either -- no finite verb with a mapped root"
                ),
                "rv_key": rv_key,
            }
            stats["identical_source_empty"] += 1
            continue
        accepted[sv_key] = {
            "rv_key": rv_key,
            "relationship": rel_type,
            "graph_score": score,
            "assertions": source_assertions,
        }
        stats["projected"] += 1
        stats["assertions"] += len(source_assertions)

    return {"accepted": accepted, "refused": refused, "stats": dict(stats)}
