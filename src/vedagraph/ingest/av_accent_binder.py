"""Bind accent-mark x extents to aksara carriers in a transcribed skeleton.

Takes the output of extract_atharvaveda_accents.extract_line() — a list of
marks with x0/x1 positions in block pixel coordinates — and maps each mark to
its carrier aksara in the supplied skeleton text.

The binding is purely geometric: it does not interpret Sanskrit phonology,
consult any external resource, or treat a modern transcription as truth.
The 1856 page image, via the word spans derived from its sirorekha column
profile, is the only evidence used.

Span-to-token mapping is delegated to av_alignment, which performs a global
monotonic sequence alignment. It used to be the identity map ``span[i] ->
token[i]``, and that was the pipeline's most dangerous defect: on canvas 411
line 9 two free-standing visarga dot-pairs each took a token slot, shifting
every later carrier by a word, and the binder reported all eleven marks
BOUND_EXACT at auto_promote_frac 1.0 while akṣara accuracy was 0.1818.

Confidence propagates rather than resets. Every binding's state is the
weakest of three independently computed judgements — the aksara-cell
placement, the carrier token's alignment state, and the line-level alignment
health — so no stage can report more certainty than an unresolved stage
before it.

States (only BOUND_EXACT / BOUND_UNAMBIGUOUS may be promoted automatically):
  BOUND_EXACT            mark center well within one aksara cell
  BOUND_UNAMBIGUOUS      single-aksara token; the carrier cannot be anything else
  MULTIPLE_CANDIDATES    mark center within margin of an aksara boundary
  ALIGNMENT_UNSAFE       carrier token's span alignment is not a safe state
  LINE_ALIGNMENT_UNSAFE  the line as a whole failed the alignment health guard
  NO_VALID_CARRIER       mark center outside every aligned word span
  MARK_CLASS_UNCERTAIN   extractor flagged an ambiguous shape (passed in)
  SOURCE_AMBIGUOUS       token/span count mismatch; skeleton not aligned to image
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

from vedagraph.ingest.av_alignment import (
    SAFE_ALIGNMENT_STATES,
    LineAlignment,
    align_line,
)

BindingState = Literal[
    "BOUND_EXACT",
    "BOUND_UNAMBIGUOUS",
    "MULTIPLE_CANDIDATES",
    "ALIGNMENT_UNSAFE",
    "LINE_ALIGNMENT_UNSAFE",
    "NO_VALID_CARRIER",
    "MARK_CLASS_UNCERTAIN",
    "SOURCE_AMBIGUOUS",
]

AUTO_PROMOTE: frozenset[BindingState] = frozenset({"BOUND_EXACT", "BOUND_UNAMBIGUOUS"})

# Confidence lattice, strongest first. A binding's state is the weakest of the
# judgements made about it, which is how "a later stage cannot become more
# certain than an unresolved earlier stage" is enforced concretely. Exact
# numeric multiplication is not used: the states are ordered and combining
# them takes the minimum.
_CONFIDENCE_ORDER: tuple[BindingState, ...] = (
    "BOUND_EXACT",
    "BOUND_UNAMBIGUOUS",
    "MULTIPLE_CANDIDATES",
    "ALIGNMENT_UNSAFE",
    "LINE_ALIGNMENT_UNSAFE",
    "NO_VALID_CARRIER",
    "MARK_CLASS_UNCERTAIN",
    "SOURCE_AMBIGUOUS",
)
_CONFIDENCE_RANK: dict[str, int] = {s: i for i, s in enumerate(_CONFIDENCE_ORDER)}


def weakest(*states: BindingState) -> BindingState:
    """The least confident of the given states, per the declared lattice."""
    return max(states, key=lambda s: _CONFIDENCE_RANK[s])


# Fraction of cell width within which a mark center is considered ambiguous
# between two adjacent aksara cells. Measured on canvas n32: bar centres sit
# +3 to +31px right of aksara centre on ~120px cells, so 0.15 is the margin.
BOUNDARY_MARGIN = 0.15

# Maximum fractional mismatch between token count and span count before the
# whole line is declared SOURCE_AMBIGUOUS. At > 0.30 there is no stable 1:1
# pairing and any assignment would be a guess. This remains a coarse
# pre-filter ahead of the sequence alignment, not the alignment itself.
MAX_TOKEN_SPAN_MISMATCH = 0.30

# Tolerance for a mark center that falls just outside a span edge (pixels).
# Geometry is imperfect: a bar can sit a few px past the inked rule edge.
SPAN_EDGE_TOLERANCE = 20

_HALANTA = "्"  # virama
_ANUSVARA = "ं"  # anusvara
_VISARGA = "ः"  # visarga  # noqa: RUF001
_CHANDRABINDU = "ँ"  # chandrabindu
_NUKTA = "़"  # nukta


def _is_vowel_sign(c: str) -> bool:
    # aa-matra through au-matra, plus syllabic vocalic l/ll matras
    return "ा" <= c <= "ौ" or c in "ॢॣ"


def _is_consonant(c: str) -> bool:
    return "क" <= c <= "ह" or "क़" <= c <= "य़"


def _is_vowel(c: str) -> bool:
    # Short a through au, plus vocalic r/l/rr/ll
    return "अ" <= c <= "औ" or c in "ॠॡ"


def aksara_clusters(word: str) -> list[str]:
    """Split a Devanagari word into aksara (glyph) clusters.

    Covers: consonant clusters joined by halanta, vowel signs, anusvara /
    visarga / chandrabindu modifiers, nukta, and standalone vowels. Punctuation
    and digits are returned as single-character clusters.

    Designed for the 1856 Roth-Whitney typography; handles the conjuncts and
    matras observed in the scanned pages.
    """
    text = unicodedata.normalize("NFC", word)
    clusters: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if _is_consonant(c):
            cluster = c
            i += 1
            # Consume halanta + following consonant(s): conjunct cluster.
            # Example: ब् + र → ब्र; ह् + म → ह्म
            while i + 1 < len(text) and text[i] == _HALANTA and _is_consonant(text[i + 1]):
                cluster += text[i] + text[i + 1]
                i += 2
            # Nukta modifies the preceding consonant, stays in cluster
            if i < len(text) and text[i] == _NUKTA:
                cluster += text[i]
                i += 1
            # Vowel sign (matra) or syllabic matra
            if i < len(text) and _is_vowel_sign(text[i]):
                cluster += text[i]
                i += 1
            # Modifiers: anusvara, visarga, chandrabindu
            while i < len(text) and text[i] in (_ANUSVARA, _VISARGA, _CHANDRABINDU):
                cluster += text[i]
                i += 1
            # Final halanta (virāma) that is NOT followed by a consonant: the
            # syllable ends on a bare consonant, e.g. म् in स्ताम्. Consume it
            # here so it does not become a phantom cluster of its own.
            if (
                i < len(text)
                and text[i] == _HALANTA
                and (i + 1 >= len(text) or not _is_consonant(text[i + 1]))
            ):
                cluster += text[i]
                i += 1
            clusters.append(cluster)
        elif _is_vowel(c):
            cluster = c
            i += 1
            # A standalone vowel can carry anusvara/visarga
            while i < len(text) and text[i] in (_ANUSVARA, _VISARGA, _CHANDRABINDU):
                cluster += text[i]
                i += 1
            clusters.append(cluster)
        else:
            # Punctuation, digits, danda (।), double danda (॥), etc.
            clusters.append(c)
            i += 1
    return clusters


def strip_accents(text: str) -> str:
    """Remove Vedic accent marks (U+0951, U+0952) from text."""
    anudatta = "॒"
    svarita = "॑"
    # Also strip Vedic Extensions U+1CD0-U+1CFF in case a reader used them
    return "".join(
        c
        for c in unicodedata.normalize("NFC", text)
        if c not in (anudatta, svarita) and not (0x1CD0 <= ord(c) < 0x1D00)
    )


def _tokenise(skeleton: str) -> list[str]:
    return skeleton.split()


@dataclass(slots=True)
class Binding:
    mark_type: str  # "anudatta" | "svarita"
    mark_x0: int
    mark_x1: int
    word_index: int | None  # index into the effective (aligned) spans
    word_token: str | None  # the word text
    aksara_index: int | None  # 0-based index within word's aksara clusters
    aksara_cluster: str | None  # the aksara cluster string
    char_offset: int | None  # char offset in the full skeleton string
    token_offset: int | None  # token index in the token list
    state: BindingState
    note: str = field(default="")
    alignment_state: str = field(default="")
    alignment_margin: int = field(default=0)
    cell_state: BindingState = field(default="BOUND_EXACT")


def _mark_center(mark: dict[str, Any]) -> float:
    return float(mark["x0"] + mark["x1"]) / 2.0


def _find_word_span(center: float, word_spans: list[tuple[int, int]]) -> tuple[int | None, bool]:
    """Index of the span containing center, and whether the hit was inside it.

    A False second element means the span was only reached by the edge
    tolerance, which is weaker evidence and is propagated as such.
    """
    for i, (x0, x1) in enumerate(word_spans):
        if x0 <= center <= x1:
            return i, True
    if not word_spans:
        return None, False
    # Allow a small overshoot — a mark's bar can sit just past the rule edge
    best = min(
        range(len(word_spans)),
        key=lambda i: min(abs(center - word_spans[i][0]), abs(center - word_spans[i][1])),
    )
    gap = min(abs(center - word_spans[best][0]), abs(center - word_spans[best][1]))
    if gap <= SPAN_EDGE_TOLERANCE:
        return best, False
    return None, False


def _aksara_cell(center: float, x0: int, x1: int, n: int) -> tuple[int | None, BindingState]:
    """Which aksara cell (0-indexed) contains center within [x0, x1].

    Returns (index, state) where state reflects placement confidence:
    BOUND_EXACT means the center is well inside the cell, away from both edges.
    MULTIPLE_CANDIDATES means it is within BOUNDARY_MARGIN of a neighbour cell.

    A single-aksara token returns BOUND_UNAMBIGUOUS rather than BOUND_EXACT:
    the carrier is certain because there is no other cell it could be, which
    is a different and weaker claim than a centred hit in a multi-cell word.
    """
    if n == 0:
        return None, "NO_VALID_CARRIER"
    if n == 1:
        return 0, "BOUND_UNAMBIGUOUS"
    cell_w = (x1 - x0) / n
    if cell_w <= 0:
        return 0, "BOUND_UNAMBIGUOUS"
    raw = (center - x0) / cell_w
    idx = max(0, min(int(raw), n - 1))
    frac = raw - int(raw)
    near_left = frac < BOUNDARY_MARGIN and idx > 0
    near_right = frac > 1.0 - BOUNDARY_MARGIN and idx < n - 1
    if near_left or near_right:
        return idx, "MULTIPLE_CANDIDATES"
    return idx, "BOUND_EXACT"


# When a span is more than ARTIFACT_RATIO times narrower than BOTH its
# immediate neighbours it is an isolated ink artifact in a word gap, not a
# real word. Real dandas (~14 px) have narrower neighbours so the ratio
# stays below the threshold even though they too are small.
_ARTIFACT_RATIO = 20.0


def _filter_artifact_spans(
    spans: list[tuple[int, int]],
) -> tuple[list[tuple[int, int]], list[dict[str, object]]]:
    """Remove isolated tiny spans whose both neighbours are ARTIFACT_RATIO times wider.

    Returns the surviving spans and a record of every span dropped. The threshold
    is known to be fragile, so a removal is never allowed to be invisible: a
    dropped span shifts every later token assignment on its line, and a filter
    that silently deletes a real word is indistinguishable in the output from a
    line the reader mistranscribed. The removals are carried out to the caller
    and land in the line's alignment guard, so a production run can be asked how
    often the filter fired and on what.
    """
    if len(spans) < 3:
        return spans, []
    widths = [x1 - x0 for x0, x1 in spans]
    result = []
    removed: list[dict[str, object]] = []
    for i, s in enumerate(spans):
        w = widths[i]
        if w <= 0:
            removed.append(
                {"span_index": i, "x0": s[0], "x1": s[1], "width": w, "reason": "EMPTY_SPAN"}
            )
            continue
        left_w = widths[i - 1] if i > 0 else widths[i + 1]
        right_w = widths[i + 1] if i < len(spans) - 1 else widths[i - 1]
        ratio = min(left_w, right_w) / w
        if ratio > _ARTIFACT_RATIO:
            # both neighbours are >RATIO x wider — artifact
            removed.append(
                {
                    "span_index": i,
                    "x0": s[0],
                    "x1": s[1],
                    "width": w,
                    "ratio": round(ratio, 2),
                    "reason": "ARTIFACT_RATIO",
                }
            )
            continue
        result.append(s)
    return result, removed


def _source_ambiguous_bindings(marks: list[dict[str, Any]], note: str) -> list[Binding]:
    return [
        Binding(
            mark_type=m.get("type", "unknown"),
            mark_x0=m["x0"],
            mark_x1=m["x1"],
            word_index=None,
            word_token=None,
            aksara_index=None,
            aksara_cluster=None,
            char_offset=None,
            token_offset=None,
            state="SOURCE_AMBIGUOUS",
            note=note,
        )
        for m in marks
    ]


def bind_line_detailed(
    marks: list[dict[str, Any]],
    skeleton: str,
    word_spans: list[tuple[int, int]],
) -> tuple[list[Binding], LineAlignment | None]:
    """Bind marks to carriers and return the line alignment alongside them.

    marks     — dicts with keys {type, x0, x1}, as from extract_line()["marks"]
    skeleton  — accent-free line text (space-separated words/tokens)
    word_spans — list of (x0, x1) in block pixel coords, from extract_line()

    Two guards stand between a mark and automatic promotion. The coarse
    count guard still declares the whole line SOURCE_AMBIGUOUS when token and
    span counts cannot be reconciled at all. Past it, the sequence alignment's
    own line-level health guard applies: a line whose alignment is unhealthy
    yields no promotable marks however confident each individual placement
    looks, because a high per-mark promotion rate on a misaligned line is
    exactly the silent failure this pipeline is required not to produce.
    """
    tokens = _tokenise(skeleton)
    # Filter isolated artifact spans before alignment so a small ink blob in
    # a large word gap cannot shift every subsequent token assignment.
    effective_spans, artifact_removals = _filter_artifact_spans(word_spans)
    n_tokens, n_spans = len(tokens), len(effective_spans)

    max_mismatch = max(1, round(max(n_tokens, n_spans, 1) * MAX_TOKEN_SPAN_MISMATCH))
    if abs(n_tokens - n_spans) > max_mismatch:
        note = (
            f"token/span mismatch: {n_tokens} tokens vs {n_spans} spans "
            f"(threshold {max_mismatch}); skeleton not aligned to image"
        )
        return _source_ambiguous_bindings(marks, note), None

    token_aksaras: list[list[str]] = [aksara_clusters(t) for t in tokens]
    alignment = align_line(effective_spans, token_aksaras)
    # Instrumentation, not a decision: the guard dict already carries this line's
    # diagnostics, and the artifact filter's firings belong with them.
    alignment.guard["artifact_spans_removed"] = len(artifact_removals)
    if artifact_removals:
        alignment.guard["artifact_ratio_threshold"] = _ARTIFACT_RATIO

    char_offset_at: list[int] = []
    offset = 0
    for t in tokens:
        char_offset_at.append(offset)
        offset += len(t) + 1  # +1 for the inter-word space

    # The line-level judgement, computed once and applied to every mark.
    line_state: BindingState = "BOUND_EXACT" if alignment.line_safe else "LINE_ALIGNMENT_UNSAFE"

    bindings: list[Binding] = []
    for m in marks:
        if m.get("state") == "MARK_CLASS_UNCERTAIN":
            bindings.append(
                Binding(
                    mark_type=m.get("type", "unknown"),
                    mark_x0=m["x0"],
                    mark_x1=m["x1"],
                    word_index=None,
                    word_token=None,
                    aksara_index=None,
                    aksara_cluster=None,
                    char_offset=None,
                    token_offset=None,
                    state="MARK_CLASS_UNCERTAIN",
                    cell_state="MARK_CLASS_UNCERTAIN",
                )
            )
            continue

        center = _mark_center(m)
        wi, inside = _find_word_span(center, effective_spans)

        if wi is None:
            bindings.append(
                Binding(
                    mark_type=m["type"],
                    mark_x0=m["x0"],
                    mark_x1=m["x1"],
                    word_index=None,
                    word_token=None,
                    aksara_index=None,
                    aksara_cluster=None,
                    char_offset=None,
                    token_offset=None,
                    state="NO_VALID_CARRIER",
                    note=f"mark center {center:.0f} outside all {n_spans} effective spans",
                    cell_state="NO_VALID_CARRIER",
                )
            )
            continue

        carriers = alignment.tokens_for_span(wi)
        if not carriers:
            bindings.append(
                Binding(
                    mark_type=m["type"],
                    mark_x0=m["x0"],
                    mark_x1=m["x1"],
                    word_index=wi,
                    word_token=None,
                    aksara_index=None,
                    aksara_cluster=None,
                    char_offset=None,
                    token_offset=None,
                    state=weakest("NO_VALID_CARRIER", line_state),
                    note=(
                        f"span {wi} aligned to no token (ALIGN_GAP_TEXT); "
                        "the image shows ink the skeleton does not account for"
                    ),
                    alignment_state="ALIGN_GAP_TEXT",
                    cell_state="NO_VALID_CARRIER",
                )
            )
            continue

        if len(carriers) > 1:
            names = ", ".join(tokens[t] for t in carriers)
            bindings.append(
                Binding(
                    mark_type=m["type"],
                    mark_x0=m["x0"],
                    mark_x1=m["x1"],
                    word_index=wi,
                    word_token=None,
                    aksara_index=None,
                    aksara_cluster=None,
                    char_offset=None,
                    token_offset=None,
                    state=weakest("ALIGNMENT_UNSAFE", line_state),
                    note=(
                        f"span {wi} carries {len(carriers)} tokens ({names}); "
                        "the image never showed where one word ended"
                    ),
                    alignment_state="ALIGN_ONE_TO_MANY",
                    cell_state="MULTIPLE_CANDIDATES",
                )
            )
            continue

        ti = carriers[0]
        token_alignment = alignment.token_alignment(ti)
        assert token_alignment is not None  # ti came from this alignment
        token = tokens[ti]
        aksaras = token_aksaras[ti]

        # The carrier cell grid spans the whole extent the token was aligned
        # to, which for a many-to-one token is wider than any single span.
        assigned = token_alignment.span_indices
        grid_x0 = effective_spans[assigned[0]][0]
        grid_x1 = effective_spans[assigned[-1]][1]
        ak_idx, cell_state = _aksara_cell(center, grid_x0, grid_x1, len(aksaras))

        if not inside and cell_state in AUTO_PROMOTE:
            # Reached only by the edge tolerance: the cell index is an
            # extrapolation past the inked rule, not a containment.
            #
            # This tested `== "BOUND_EXACT"` and so never fired for a
            # single-aksara token, because _aksara_cell returns
            # BOUND_UNAMBIGUOUS when n == 1. A mark sitting up to
            # SPAN_EDGE_TOLERANCE px outside every inked span was therefore
            # auto-promoted without a note, and single-aksara tokens are
            # common here: ते, च, म, the dandas and every verse numeral.
            cell_state = "MULTIPLE_CANDIDATES"

        align_state: BindingState = (
            "BOUND_EXACT" if token_alignment.state in SAFE_ALIGNMENT_STATES else "ALIGNMENT_UNSAFE"
        )
        state = weakest(cell_state, align_state, line_state)

        char_off: int | None = None
        ak_str: str | None = None
        if ak_idx is not None and ak_idx < len(aksaras):
            ak_str = aksaras[ak_idx]
            char_off = char_offset_at[ti] + sum(len(a) for a in aksaras[:ak_idx])

        note = ""
        if state != cell_state:
            note = f"cell {cell_state} weakened to {state} by {token_alignment.state}" + (
                "" if alignment.line_safe else " and an unsafe line alignment"
            )

        bindings.append(
            Binding(
                mark_type=m["type"],
                mark_x0=m["x0"],
                mark_x1=m["x1"],
                word_index=wi,
                word_token=token,
                aksara_index=ak_idx,
                aksara_cluster=ak_str,
                char_offset=char_off,
                token_offset=ti,
                state=state,
                note=note,
                alignment_state=token_alignment.state,
                alignment_margin=token_alignment.margin,
                cell_state=cell_state,
            )
        )

    return bindings, alignment


def bind_line(
    marks: list[dict[str, Any]],
    skeleton: str,
    word_spans: list[tuple[int, int]],
) -> list[Binding]:
    """Bind a list of extracted marks to their carriers in the skeleton."""
    bindings, _ = bind_line_detailed(marks, skeleton, word_spans)
    return bindings


def binding_summary(bindings: list[Binding]) -> dict[str, Any]:
    """Aggregate counts over a list of Binding records."""
    total = len(bindings)
    by_state: dict[str, int] = {}
    for b in bindings:
        by_state[b.state] = by_state.get(b.state, 0) + 1
    promotable = sum(1 for b in bindings if b.state in AUTO_PROMOTE)
    return {
        "total_marks": total,
        "promotable": promotable,
        "promotable_fraction": round(promotable / total, 4) if total else None,
        "by_state": dict(sorted(by_state.items())),
        "ambiguous_or_failed": total - promotable,
    }
