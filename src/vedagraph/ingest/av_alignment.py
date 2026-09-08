"""Deterministic sequence alignment between image word spans and skeleton tokens.

The binder used to assume ``span[i] -> token[i]``. That assumption is false in
the 1856 print, and its failure is silent: on canvas 411 line 9 two
free-standing visarga dot-pairs each occupy a rule span of their own, every
carrier after them shifts by a word, and the binder still reported every mark
``BOUND_EXACT``. Word-binding accuracy there was 0.2727, and akṣara accuracy
0.1818, at ``auto_promote_frac = 1.0``.

This module replaces the positional assumption with a global monotonic
sequence alignment over five operations — match, many-to-one, one-to-many,
gap-in-image, gap-in-text — scored on source-derived structural features
only:

  * span width against the token's expected printed width
  * inter-span gap against the line's own median gap
  * Devanagari orthographic structure: cluster count, punctuation class,
    digits, and the detached visarga tail this fount sets clear of the rule

No digital Atharvaveda text is consulted; the skeleton is the transcription
under test and the spans come from the scan's sirorekha column profile.

The alignment does not merely produce a mapping. For every token it also
reports how much cheaper the chosen assignment was than the best alternative
assignment for that same token, computed by forward-backward dynamic
programming over the whole line. Where that margin is small the token is
``ALIGN_AMBIGUOUS`` and nothing downstream may auto-promote through it. That
is the mechanism which stops a later stage becoming more certain than an
unresolved earlier one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AlignmentState = Literal[
    "ALIGN_EXACT",
    "ALIGN_UNAMBIGUOUS",
    "ALIGN_MANY_TO_ONE",
    "ALIGN_ONE_TO_MANY",
    "ALIGN_GAP_IMAGE",
    "ALIGN_GAP_TEXT",
    "ALIGN_AMBIGUOUS",
]

# Only these may feed automatic accent promotion.
#
# ALIGN_ONE_TO_MANY is deliberately excluded even though it is a resolved
# alignment: one rule span covering two tokens means the image never showed
# where one word ended and the next began, so a mark inside that span cannot
# be attributed to either token without guessing.
SAFE_ALIGNMENT_STATES: frozenset[str] = frozenset(
    {"ALIGN_EXACT", "ALIGN_UNAMBIGUOUS", "ALIGN_MANY_TO_ONE"}
)

UNRESOLVED_ALIGNMENT_STATES: frozenset[str] = frozenset(
    {"ALIGN_GAP_IMAGE", "ALIGN_GAP_TEXT", "ALIGN_AMBIGUOUS"}
)

# ── Expected printed width, in demand units where one aksara is 100 ───────
#
# Measured from the punctuation spans of the calibration set's gold lines,
# where the identity of a span is not in question: the terminal narrow runs
# after the last word are the danda, the double danda and the verse numeral,
# in that order, on every line. Across c032/l12, c032/l19, c159/l02,
# c411/l09 and c430/l05:
#
#   danda        14-18 px      aksara cell  75-128 px, mean ~99
#   double danda 35-42 px
#   abbrev dot   42 px
#   digit        47-67 px
#
# Only the ratios matter: the pixels-per-demand-unit scale is fitted per line
# (twice; see _refine_scale) because line density varies across the volume.
_DEMAND_AKSARA = 100
_DEMAND_DANDA = 16
_DEMAND_DOUBLE_DANDA = 39
_DEMAND_ABBREV_DOT = 42
_DEMAND_DIGIT = 55
_DEMAND_AVAGRAHA = 55
_DEMAND_OTHER_PUNCT = 30

_DANDA = "।"
_DOUBLE_DANDA = "॥"
_ABBREV_DOT = "॰"
_AVAGRAHA = "ऽ"
_VISARGA = "ः"  # noqa: RUF001

# ── Cost model (integers; no float comparison decides an alignment) ───────
#
# Width residual is expressed in aksara-widths and scaled by 1000, so a cost
# of 1000 means "this span is one whole aksara wider or narrower than the
# token it would carry". Per-cluster printed width varies by about +-20%
# within a single line (75-112 px on c411/l09 alone), so residuals of a few
# hundred are normal and the model must not treat them as evidence.
_COST_UNIT = 1000

# A merge or a split is a structural claim about the print, and the two are
# not equally plausible, so they are not priced alike.
#
# Merging says the cast rule broke inside a word, or that the fount set a
# glyph clear of it. Both are common here — a 2 px break inside
# सध्रीचीर्विश्वा, 11 px after an avagraha, every visarga dot-pair — so the
# charge sits below the width cost of one aksara: two spans that together fit
# the token beat matching one of them and paying an aksara of residual.
_MERGE_PENALTY = 150

# Splitting says the opposite: that a word boundary exists where the rule ran
# continuously. Since the span extractor already bridges breaks under 14 px
# and every genuine word gap in the volume measures 20-60 px, that requires
# the boundary to have printed with no gap at all. It is priced level with
# dropping a span outright, because it is claiming a defect of the same order.
#
# Be straight about the provenance of this number: it was raised from 150
# after observing behaviour on two of the five gold lines, so it is a
# constant selected with the calibration set in view. At 150 the model
# preferred to split the double-danda span into a danda plus a double danda
# over matching each to its own span, because a danda is 16 demand units
# against a +-20% width noise floor and the width residual could not tell the
# two readings apart; it reported ALIGN_AMBIGUOUS on the well-aligned
# punctuation tails of c411/l09 and c430/l05.
#
# What keeps it from being a fit to those two lines is the size of the
# margin, which was measured by sweep: the gate flips between 445 and 450,
# and 900 sits 2.0x above that, chosen for the physical reason above rather
# than for the flip point. Anything from 630 to 1170 gives identical metrics.
_SPLIT_PENALTY = 900

# Dropping a span or a token entirely is the last resort: above the cost of
# any plausible merge or split, and it grows with the size of what is dropped.
_GAP_BASE = 900

# Gap evidence. A gap is informative only at the extremes. Measured on the
# gold lines, intra-word breaks in the cast rule run 0.48-0.51 of the line's
# median gap and the narrowest genuine word boundary runs 0.61, so between
# 0.4 and 0.6 the model says nothing rather than inventing a threshold. This
# is why the repair is not "change the gap constant": at the point where the
# two populations meet, the gap carries no information and the width and
# orthographic evidence has to decide.
_GAP_WEIGHT = 600
_GAP_MERGE_FREE = 0.6
_GAP_BOUNDARY_FREE = 0.4

# A token ending in visarga is expected to print a detached narrow tail: this
# fount sets the dot-pair clear of the sirorekha, so it forms its own rule
# span. When a merge is exactly that — token ends in visarga, tail span is
# narrow, internal gap no wider than the line median — it is not a structural
# claim at all and pays no merge penalty.
#
# The exemption does fire on the chosen path, on both visarga merges of
# c411/l09. But sweeping this constant from 0 to 500 moves no gate metric by
# a single digit, and neither does _MERGE_PENALTY from 0 to 5000: those two
# only become jointly load-bearing if the penalty rises above 900 *and* this
# exemption is disabled at the same time. The calibration set cannot test
# either of them, and this comment should not be read as evidence that it
# does.
_VISARGA_TAIL_MAX_DEMAND = 40

_MAX_MERGE = 3
_MAX_SPLIT = 3

# Below this margin (in cost units) the second-best assignment for a token is
# close enough that the choice is not evidence. Half the width cost of one
# aksara: if reassigning a token's spans changes the whole line's cost by less
# than half an aksara of ink, the ink did not decide it.
MARGIN_SAFE = 500

# A merge is only a resolved alignment if the merged extent actually fits the
# token. Beyond one aksara of width residual it has stopped explaining split
# ink and started absorbing a neighbour, so it is reported ALIGN_AMBIGUOUS
# instead of ALIGN_MANY_TO_ONE.
#
# Found by an adversarial case, not by the gold lines: with three spans on two
# tokens, dropping a spare 200 px span cost 2900 while swallowing it into the
# next token cost 2790, so the model absorbed a whole extra word, called the
# line safe, and promoted a mark sitting on ink the skeleton never accounted
# for — the same silent failure this repair exists to remove. The two costs
# are near parity because both scale with the same span width, so the fit of
# the merge itself has to be judged separately from its price.
_MERGE_FIT_MAX = 1000

# ── Line-level alignment health guard (declared before running) ───────────
#
# A superficially high per-mark promotion rate must not override a bad line
# alignment, so these are evaluated on the line as a whole and, when any of
# them fails, every mark on the line loses promotability regardless of its
# own state.
LINE_GUARD_MIN_SAFE_TOKEN_FRACTION = 0.80
LINE_GUARD_MAX_UNRESOLVED_OPS = 0
LINE_GUARD_MAX_COST_PER_TOKEN = 2000


def _is_devanagari_digit(ch: str) -> bool:
    return "०" <= ch <= "९" or ch.isdigit()  # noqa: RUF001


def cluster_demand(cluster: str) -> int:
    """Expected printed width of one aksara cluster, in demand units."""
    if not cluster:
        return 0
    if cluster == _DANDA:
        return _DEMAND_DANDA
    if cluster == _DOUBLE_DANDA:
        return _DEMAND_DOUBLE_DANDA
    if cluster == _ABBREV_DOT:
        return _DEMAND_ABBREV_DOT
    if cluster == _AVAGRAHA:
        return _DEMAND_AVAGRAHA
    if len(cluster) == 1 and _is_devanagari_digit(cluster):
        return _DEMAND_DIGIT
    if len(cluster) == 1 and not cluster.isalpha():
        return _DEMAND_OTHER_PUNCT
    return _DEMAND_AKSARA


def token_demand(clusters: list[str]) -> int:
    """Expected printed width of a whole token, in demand units."""
    return sum(cluster_demand(c) for c in clusters)


def _expects_detached_tail(clusters: list[str]) -> bool:
    """True when the token's last cluster carries a visarga."""
    return bool(clusters) and _VISARGA in clusters[-1]


@dataclass(frozen=True, slots=True)
class TokenAlignment:
    """How one skeleton token was matched to the image's rule spans."""

    token_index: int
    span_indices: tuple[int, ...]
    state: AlignmentState
    margin: int
    note: str = ""

    @property
    def safe(self) -> bool:
        return self.state in SAFE_ALIGNMENT_STATES


@dataclass(slots=True)
class LineAlignment:
    """The alignment of one printed line, with its health indicators."""

    tokens: tuple[TokenAlignment, ...]
    span_to_tokens: dict[int, tuple[int, ...]]
    unaligned_spans: tuple[int, ...]
    total_cost: int
    cost_per_token: int
    safe_token_fraction: float
    unresolved_ops: int
    many_to_one_ops: int
    one_to_many_ops: int
    token_count: int
    span_count: int
    line_safe: bool
    line_note: str
    scale: float
    guard: dict[str, float | int | bool] = field(default_factory=dict)

    def token_alignment(self, token_index: int) -> TokenAlignment | None:
        for t in self.tokens:
            if t.token_index == token_index:
                return t
        return None

    def tokens_for_span(self, span_index: int) -> tuple[int, ...]:
        return self.span_to_tokens.get(span_index, ())


def _span_width(span: tuple[int, int]) -> int:
    return span[1] - span[0]


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


class _Model:
    """Per-line cost model. Deterministic: integer costs all the way down."""

    def __init__(
        self,
        spans: list[tuple[int, int]],
        token_clusters: list[list[str]],
        scale: float,
    ) -> None:
        self.spans = spans
        self.clusters = token_clusters
        self.demands = [token_demand(c) for c in token_clusters]
        self.scale = scale if scale > 0 else 1.0
        # One aksara of printed ink, in pixels, at this line's scale.
        self.aksara_px = max(1.0, self.scale * _DEMAND_AKSARA)
        self.gaps = [float(spans[i + 1][0] - spans[i][1]) for i in range(len(spans) - 1)]
        self.median_gap = _median(self.gaps) or 1.0

    def _width_cost(self, width: float, demand: int) -> int:
        expected = self.scale * demand
        return round(abs(width - expected) / self.aksara_px * _COST_UNIT)

    def _merged_width(self, i: int, i2: int) -> int:
        return self.spans[i2 - 1][1] - self.spans[i][0]

    def _gap_ratio(self, between: int) -> float:
        """Gap between span ``between`` and span ``between + 1``, over median."""
        if 0 <= between < len(self.gaps):
            return self.gaps[between] / self.median_gap
        return 1.0

    def _merge_gap_cost(self, i: int, i2: int) -> int:
        cost = 0
        for b in range(i, i2 - 1):
            excess = self._gap_ratio(b) - _GAP_MERGE_FREE
            if excess > 0:
                cost += round(_GAP_WEIGHT * excess)
        return cost

    def _boundary_cost(self, i2: int) -> int:
        """Charge for declaring a token boundary after span ``i2 - 1``."""
        if i2 - 1 >= len(self.gaps):
            return 0
        deficit = _GAP_BOUNDARY_FREE - self._gap_ratio(i2 - 1)
        if deficit > 0:
            return round(_GAP_WEIGHT * deficit)
        return 0

    def merge_fit(self, i: int, i2: int, j: int) -> int:
        """How badly the merged extent of spans[i:i2] misfits token j."""
        return self._width_cost(float(self._merged_width(i, i2)), self.demands[j])

    def _is_structural_tail_merge(self, i: int, i2: int, j: int) -> bool:
        """A two-span merge that is exactly this fount's detached visarga."""
        if i2 - i != 2:
            return False
        if not _expects_detached_tail(self.clusters[j]):
            return False
        if _span_width(self.spans[i2 - 1]) > self.scale * _VISARGA_TAIL_MAX_DEMAND:
            return False
        return self._gap_ratio(i2 - 2) <= 1.0

    def op_cost(self, i: int, i2: int, j: int, j2: int) -> int:
        n_spans, n_tokens = i2 - i, j2 - j
        if n_spans == 0:
            # Token with no span at all.
            return _GAP_BASE + self._width_cost(0.0, self.demands[j])
        if n_tokens == 0:
            # Span with no token at all.
            return _GAP_BASE + round(_span_width(self.spans[i]) / self.aksara_px * _COST_UNIT)
        if n_spans == 1 and n_tokens == 1:
            return self._width_cost(
                float(_span_width(self.spans[i])), self.demands[j]
            ) + self._boundary_cost(i2)
        if n_tokens == 1:
            penalty = (
                0 if self._is_structural_tail_merge(i, i2, j) else _MERGE_PENALTY * (n_spans - 1)
            )
            return (
                self._width_cost(float(self._merged_width(i, i2)), self.demands[j])
                + penalty
                + self._merge_gap_cost(i, i2)
                + self._boundary_cost(i2)
            )
        return (
            self._width_cost(float(_span_width(self.spans[i])), sum(self.demands[j:j2]))
            + _SPLIT_PENALTY * (n_tokens - 1)
            + self._boundary_cost(i2)
        )


def _operations(n_spans: int, n_tokens: int) -> list[tuple[int, int, int, int]]:
    """Every candidate operation, in a fixed deterministic order."""
    ops: list[tuple[int, int, int, int]] = []
    seen: set[tuple[int, int, int, int]] = set()

    def add(op: tuple[int, int, int, int]) -> None:
        if op not in seen:
            seen.add(op)
            ops.append(op)

    for i in range(n_spans + 1):
        for j in range(n_tokens + 1):
            if i < n_spans and j < n_tokens:
                for k in range(1, _MAX_MERGE + 1):
                    if i + k <= n_spans:
                        add((i, i + k, j, j + 1))
                for k in range(2, _MAX_SPLIT + 1):
                    if j + k <= n_tokens:
                        add((i, i + 1, j, j + k))
            if i < n_spans:
                add((i, i + 1, j, j))  # gap in text: span carries no token
            if j < n_tokens:
                add((i, i, j, j + 1))  # gap in image: token has no span
    return ops


_INF = 1 << 40


def _fit_scale(spans: list[tuple[int, int]], token_clusters: list[list[str]]) -> float:
    """First-pass pixels per demand unit, as a ratio of medians.

    Deliberately not a ratio of sums. A sum ratio is inflated by exactly the
    ink that should not be there: on a line with one spare span it read 1.4
    px per demand unit instead of 0.8, so every token looked as though it
    ought to be wider than it was printed and absorbing the spare span became
    the cheap reading. The median is unmoved by a minority of spans or tokens
    that have no counterpart, which is the whole population this pass has to
    survive. The correspondence-based refinement then runs on top of it.
    """
    span_median = _median([float(_span_width(s)) for s in spans])
    demand_median = _median([float(token_demand(c)) for c in token_clusters])
    if demand_median <= 0 or span_median <= 0:
        return 1.0
    return span_median / demand_median


def _one_to_one_ratios(model: _Model, path: list[tuple[int, int, int, int]]) -> list[float]:
    """Pixels per demand unit, measured on pass one's one-to-one matches."""
    return [
        _span_width(model.spans[i]) / model.demands[j]
        for i, i2, j, j2 in path
        if i2 - i == 1 and j2 - j == 1 and model.demands[j] > 0
    ]


def _refine_scale(ratios: list[float], fallback: float) -> float:
    """Median pixels-per-demand-unit over the one-to-one matches of pass one.

    A single 1:1 pair is a direct measurement of this line's own pitch and
    beats any ratio of aggregates, both of which are biased: a ratio of sums
    is inflated by ink with no token behind it, a ratio of medians is skewed
    whenever the span and token populations differ in size. So one pair is
    enough to prefer. Exactly two passes run, so the result stays a fixed
    function of the input.
    """
    if not ratios:
        return fallback
    return _median(ratios) or fallback


def _solve(
    model: _Model, n_spans: int, n_tokens: int
) -> tuple[list[list[int]], list[list[int]], list[tuple[int, int, int, int]]]:
    ops = _operations(n_spans, n_tokens)
    from_cell: dict[tuple[int, int], list[tuple[int, int, int, int]]] = {}
    for candidate in ops:
        from_cell.setdefault((candidate[0], candidate[2]), []).append(candidate)

    forward = [[_INF] * (n_tokens + 1) for _ in range(n_spans + 1)]
    choice: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    forward[0][0] = 0
    for i in range(n_spans + 1):
        for j in range(n_tokens + 1):
            here = forward[i][j]
            if here >= _INF:
                continue
            for oi, oi2, oj, oj2 in from_cell.get((i, j), ()):
                total = here + model.op_cost(oi, oi2, oj, oj2)
                if total < forward[oi2][oj2]:
                    forward[oi2][oj2] = total
                    choice[(oi2, oj2)] = (oi, oi2, oj, oj2)

    backward = [[_INF] * (n_tokens + 1) for _ in range(n_spans + 1)]
    backward[n_spans][n_tokens] = 0
    for i in range(n_spans, -1, -1):
        for j in range(n_tokens, -1, -1):
            if i == n_spans and j == n_tokens:
                continue
            best = _INF
            for oi, oi2, oj, oj2 in from_cell.get((i, j), ()):
                rest = backward[oi2][oj2]
                if rest >= _INF:
                    continue
                total = model.op_cost(oi, oi2, oj, oj2) + rest
                if total < best:
                    best = total
            backward[i][j] = best

    path: list[tuple[int, int, int, int]] = []
    cell = (n_spans, n_tokens)
    while cell != (0, 0):
        op: tuple[int, int, int, int] | None = choice.get(cell)
        if op is None:
            break
        path.append(op)
        cell = (op[0], op[2])
    path.reverse()
    return forward, backward, path


def _empty_alignment(n_spans: int, n_tokens: int) -> LineAlignment:
    note = "no tokens to align" if n_tokens == 0 else "no rule spans to align"
    return LineAlignment(
        tokens=tuple(TokenAlignment(j, (), "ALIGN_GAP_IMAGE", 0, note) for j in range(n_tokens)),
        span_to_tokens={},
        unaligned_spans=tuple(range(n_spans)),
        total_cost=0,
        cost_per_token=0,
        safe_token_fraction=0.0,
        unresolved_ops=max(n_spans, n_tokens),
        many_to_one_ops=0,
        one_to_many_ops=0,
        token_count=n_tokens,
        span_count=n_spans,
        line_safe=False,
        line_note=note,
        scale=1.0,
        guard={"line_safe": False},
    )


def align_line(spans: list[tuple[int, int]], token_clusters: list[list[str]]) -> LineAlignment:
    """Align image word spans to skeleton tokens, with per-token confidence.

    ``token_clusters`` is the aksara-cluster decomposition of each token, as
    produced by ``av_accent_binder.aksara_clusters``. It is passed in rather
    than computed here so this module stays free of the binder's imports.
    """
    n_spans, n_tokens = len(spans), len(token_clusters)
    if n_tokens == 0 or n_spans == 0:
        return _empty_alignment(n_spans, n_tokens)

    coarse = _fit_scale(spans, token_clusters)
    first = _Model(spans, token_clusters, coarse)
    _, _, first_path = _solve(first, n_spans, n_tokens)
    ratios = _one_to_one_ratios(first, first_path)
    # Without a single 1:1 pair there is no direct measurement of this line's
    # pitch, so a merge's fit cannot be verified and must not be trusted.
    direct_scale_evidence = bool(ratios)
    model = _Model(spans, token_clusters, _refine_scale(ratios, coarse))
    forward, backward, path = _solve(model, n_spans, n_tokens)
    total_cost = forward[n_spans][n_tokens]

    # Per token, the best total line cost for each distinct span assignment,
    # so the margin is a property of the whole line and not of a local choice.
    by_token: dict[int, dict[tuple[int, ...], int]] = {j: {} for j in range(n_tokens)}
    for oi, oi2, oj, oj2 in _operations(n_spans, n_tokens):
        head, tail = forward[oi][oj], backward[oi2][oj2]
        if head >= _INF or tail >= _INF:
            continue
        total = head + model.op_cost(oi, oi2, oj, oj2) + tail
        assigned = tuple(range(oi, oi2))
        for j in range(oj, oj2):
            bucket = by_token[j]
            if assigned not in bucket or total < bucket[assigned]:
                bucket[assigned] = total

    chosen: dict[int, tuple[tuple[int, ...], int, int]] = {}
    for oi, oi2, oj, oj2 in path:
        for j in range(oj, oj2):
            chosen[j] = (tuple(range(oi, oi2)), oi2 - oi, oj2 - oj)

    token_alignments: list[TokenAlignment] = []
    span_to_tokens: dict[int, list[int]] = {}
    unresolved = many_to_one = one_to_many = 0
    for j in range(n_tokens):
        assigned, n_sp, n_tk = chosen.get(j, ((), 0, 1))
        ranked = sorted(by_token[j].items(), key=lambda kv: (kv[1], kv[0]))
        best_cost = ranked[0][1] if ranked else total_cost
        # There is always a rival assignment: reading the token as a gap is
        # itself a candidate, so `runner_up` is never _INF in practice. A
        # margin of 0 therefore means one thing only — an exact tie between
        # two readings of the ink — which is why the runner must not filter
        # zeros out of the minimum it reports.
        runner_up = next((c for key, c in ranked if key != assigned), _INF)
        margin = 0 if runner_up >= _INF else runner_up - best_cost
        note = ""
        state: AlignmentState
        if not assigned:
            state = "ALIGN_GAP_IMAGE"
            note = "token has no rule span in the image"
        elif margin < MARGIN_SAFE:
            state = "ALIGN_AMBIGUOUS"
            note = (
                f"second-best span assignment is only {margin} cost units "
                f"dearer (safe margin {MARGIN_SAFE})"
            )
        elif n_tk > 1:
            state = "ALIGN_ONE_TO_MANY"
            note = f"one rule span covers {n_tk} tokens"
        elif n_sp > 1:
            fit = (
                model.merge_fit(assigned[0], assigned[-1] + 1, j)
                if direct_scale_evidence
                else _MERGE_FIT_MAX + 1
            )
            if fit > _MERGE_FIT_MAX:
                state = "ALIGN_AMBIGUOUS"
                note = (
                    f"{n_sp} spans merged onto this token misfit it by {fit} "
                    f"cost units (limit {_MERGE_FIT_MAX}); this is absorption, "
                    "not split ink"
                )
            else:
                state = "ALIGN_MANY_TO_ONE"
                note = f"{n_sp} rule spans carry this token (fit {fit})"
        elif model.op_cost(assigned[0], assigned[0] + 1, j, j + 1) <= _COST_UNIT // 2:
            state = "ALIGN_EXACT"
        else:
            state = "ALIGN_UNAMBIGUOUS"
            note = "width residual above half an aksara but no rival assignment"
        if state in UNRESOLVED_ALIGNMENT_STATES:
            unresolved += 1
        if state == "ALIGN_MANY_TO_ONE":
            many_to_one += 1
        if state == "ALIGN_ONE_TO_MANY":
            one_to_many += 1
        token_alignments.append(TokenAlignment(j, assigned, state, margin, note))
        for si in assigned:
            span_to_tokens.setdefault(si, []).append(j)

    unaligned = tuple(si for si in range(n_spans) if si not in span_to_tokens)
    unresolved += len(unaligned)

    safe_fraction = sum(1 for t in token_alignments if t.safe) / n_tokens
    cost_per_token = round(total_cost / n_tokens)

    reasons: list[str] = []
    if safe_fraction < LINE_GUARD_MIN_SAFE_TOKEN_FRACTION:
        reasons.append(
            f"safe token fraction {safe_fraction:.4f} < {LINE_GUARD_MIN_SAFE_TOKEN_FRACTION}"
        )
    if unresolved > LINE_GUARD_MAX_UNRESOLVED_OPS:
        reasons.append(
            f"{unresolved} unresolved alignment operations > {LINE_GUARD_MAX_UNRESOLVED_OPS}"
        )
    if cost_per_token > LINE_GUARD_MAX_COST_PER_TOKEN:
        reasons.append(f"alignment cost/token {cost_per_token} > {LINE_GUARD_MAX_COST_PER_TOKEN}")

    return LineAlignment(
        tokens=tuple(token_alignments),
        span_to_tokens={k: tuple(v) for k, v in span_to_tokens.items()},
        unaligned_spans=unaligned,
        total_cost=total_cost,
        cost_per_token=cost_per_token,
        safe_token_fraction=round(safe_fraction, 4),
        unresolved_ops=unresolved,
        many_to_one_ops=many_to_one,
        one_to_many_ops=one_to_many,
        token_count=n_tokens,
        span_count=n_spans,
        line_safe=not reasons,
        line_note="; ".join(reasons),
        scale=round(model.scale, 6),
        guard={
            "safe_token_fraction": round(safe_fraction, 4),
            "unresolved_ops": unresolved,
            "cost_per_token": cost_per_token,
            "min_safe_token_fraction": LINE_GUARD_MIN_SAFE_TOKEN_FRACTION,
            "max_unresolved_ops": LINE_GUARD_MAX_UNRESOLVED_OPS,
            "max_cost_per_token": LINE_GUARD_MAX_COST_PER_TOKEN,
            "line_safe": not reasons,
        },
    )
