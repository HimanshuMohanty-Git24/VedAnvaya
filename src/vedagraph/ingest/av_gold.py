"""Deterministic gold selection and non-positional gold matching for AV accents.

Two defects lived here and both could decide a release gate.

*Gold selection was filesystem order.* The calibration runner globbed the
probe directory and took ``probes[0]`` whenever the readers were not
byte-identical, which was all five gold lines. On c032/l19 the two readers
differ only in danda spacing; picking Q2 instead of Q1 moves the whitespace
token count from 12 to 6, trips the token/span guard, and flips the
zero-tolerance ``source_ambiguous_gold`` gate from PASS to FAIL. On c159/l02
and c430/l05 the arbitrary pick was the reading the adjudicator had
explicitly *overruled*, while the adjudicated record sat unread in a
directory the runner never looked at.

Selection is now, in strict order of authority:

  1. the adjudicated record for that line, if one exists;
  2. otherwise the reader text all probes agree on, after the declared
     tokenisation normalisation below;
  3. otherwise the text a strict majority of readers agree on, with the
     dissent recorded;
  4. otherwise nothing: the line is GOLD_UNADJUDICATED and is excluded from
     every metric rather than resolved by whichever file the OS listed first.

All filesystem discovery is sorted, and probes are ordered by their declared
reader id rather than by filename, so the same checkout yields byte-identical
metrics on any OS.

*Gold marks were paired to predictions by position.* ``gold_marks[i]`` against
``bindings[i]`` means one missed detection mis-scores every later mark on the
line: on c411/l09 the single undetected svarita on इन्द्रं turned eleven
correctly bound marks into a reported word accuracy of 0.2727. Correspondence
is now a monotonic alignment on mark class and normalised position, and it
never consults the binding it is there to measure, so a wrongly bound mark is
normally still matched and still counted against binding accuracy.

**That is not an absolute guarantee, and adversarial review found the two
holes.** Correspondence is bought at a flat ``2 * GAP_COST``, so a prediction
whose *detected position* is further than ``2 * GAP_COST / POSITION_WEIGHT``
= 0.467 of line width from its gold mark drops out as a false
positive/false negative pair, and its binding is then never scored at all.
Worse, a **uniform** displacement of every mark on a line by one word pitch
is absorbed: the alignment shifts wholesale for one flat gap charge and then
scores each shifted binding against the gold mark on the shifted word, so
every one reads correct. The break-even is about three marks at a 0.18 word
pitch, and a uniform word shift is exactly the error class av_alignment
exists to catch.

Neither hole is live on the calibration set — the real c411/l09
pre-repair failure is a *non-uniform* shift and scores 0.3636 under this
matcher, not 1.0 — but ``matched`` is therefore not a safe denominator on its
own. ``LineMetrics`` reports ``word_binding_acc_over_gold`` alongside it for
exactly this reason: a mark that escapes into a gap still counts against that
denominator.
"""

from __future__ import annotations

import json
import pathlib
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

from vedagraph.ingest.av_accent_binder import (
    AUTO_PROMOTE,
    Binding,
    aksara_clusters,
    strip_accents,
)
from vedagraph.ingest.av_alignment import cluster_demand

ANUDATTA = "॒"
SVARITA = "॑"

# ── Declared tokenisation convention ─────────────────────────────────────
#
# Readers were not given a spacing rule, and they did not invent the same
# one: Q1 wrote "लो॒के । ए॒वाहं॰ । ॰ ॥ ७ ॥" and Q2 wrote "लो॒के। ए॒वाहं॰।॰॥७॥"
# for the same ink. Both read identical akṣaras and identical accents; only
# the whitespace differs. Rather than let that decide a gate, spacing is
# declared insignificant and re-derived:
#
#   * a danda and a double danda are each a token of their own;
#   * a maximal run of Devanagari digits is one token (a verse numeral);
#   * everything else joins the run it is written in, so the abbreviation
#     sign stays attached to the word it abbreviates;
#   * whitespace carries no information.
#
# What it fixes is that the two readings become one text, so no filesystem
# order has to break the tie.
#
# It is not neutral, and an earlier draft of this comment claimed wrongly
# that it was. Ten of c032/l19's eleven accents sit in tokens 0-4, ahead of
# the first danda (which is token 5), and their indices do not move. The
# eleventh, the anudatta on ए॒वाहं॰, sits in token 6 -- *after* that danda --
# and its word index is 6 under Q1's spacing but would be 5 under Q2's raw
# spacing. The convention moves that one index, and 6 is the correct answer:
# the mark is on एवाहं॰, not on the danda. No other index moves on any of the
# sixteen gold records. What the convention must not do is move an index
# *wrongly*, and test_accent_token_indices_are_unchanged_by_spacing pins the
# eleven it produces.
_DANDA = "।"
_DOUBLE_DANDA = "॥"
_SPLIT_TOKENS = (_DANDA, _DOUBLE_DANDA)


def _is_devanagari_digit(ch: str) -> bool:
    return "०" <= ch <= "९"  # noqa: RUF001


def normalise_tokenisation(text: str) -> str:
    """Re-space a reader's line onto the declared token convention."""
    normalised = unicodedata.normalize("NFC", text)
    tokens: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            tokens.append("".join(current))
            current.clear()

    i = 0
    while i < len(normalised):
        ch = normalised[i]
        if ch.isspace():
            flush()
            i += 1
        elif ch in _SPLIT_TOKENS:
            flush()
            tokens.append(ch)
            i += 1
        elif _is_devanagari_digit(ch):
            flush()
            run = ch
            i += 1
            while i < len(normalised) and _is_devanagari_digit(normalised[i]):
                run += normalised[i]
                i += 1
            tokens.append(run)
        else:
            current.append(ch)
            i += 1
    flush()
    return " ".join(tokens)


# ── Gold marks ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class GoldMark:
    """One accent mark as a human reader placed it."""

    index: int
    word_index: int
    aksara_index: int
    mark_type: str
    norm_pos: float


def parse_gold_marks(normalised_text: str) -> list[GoldMark]:
    """Extract (word, aksara, type) for every accent in a normalised gold line.

    ``norm_pos`` is the mark's expected position along the line in [0, 1),
    measured in the same expected-printed-width units the aligner uses, so it
    is comparable with a detected mark's normalised x without either side
    knowing anything about the other.
    """
    tokens = normalised_text.split()
    token_clusters = [aksara_clusters(strip_accents(t)) for t in tokens]
    demands = [[cluster_demand(c) for c in cl] for cl in token_clusters]
    total_demand = sum(sum(d) for d in demands) or 1
    starts: list[int] = []
    running = 0
    for d in demands:
        starts.append(running)
        running += sum(d)

    marks: list[GoldMark] = []
    for wi, word in enumerate(tokens):
        for ci, ch in enumerate(word):
            if ch not in (ANUDATTA, SVARITA):
                continue
            prefix_clusters = aksara_clusters(strip_accents(word[:ci]))
            ak_idx = max(0, len(prefix_clusters) - 1)
            cell_demands = demands[wi] if wi < len(demands) else []
            before = sum(cell_demands[:ak_idx])
            own = cell_demands[ak_idx] if ak_idx < len(cell_demands) else 0
            pos = (starts[wi] + before + own / 2.0) / total_demand
            marks.append(
                GoldMark(
                    index=len(marks),
                    word_index=wi,
                    aksara_index=ak_idx,
                    mark_type="anudatta" if ch == ANUDATTA else "svarita",
                    norm_pos=pos,
                )
            )
    return marks


# ── Deterministic gold record selection ──────────────────────────────────

GoldStatus = Literal[
    "GOLD_OK",
    "GOLD_ABSENT",
    "GOLD_UNADJUDICATED",
    "GOLD_MULTIPLE_ADJUDICATED",
]


@dataclass(slots=True)
class GoldRecord:
    canvas_index: int
    line_index: int
    status: GoldStatus
    text: str = ""
    skeleton: str = ""
    source: str = ""
    record_paths: tuple[str, ...] = ()
    readers: tuple[str, ...] = ()
    dissent: tuple[str, ...] = ()
    note: str = ""

    @property
    def usable(self) -> bool:
        return self.status == "GOLD_OK"


def _read_json(path: pathlib.Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _relative(path: pathlib.Path, root: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def load_gold_record(
    canvas_index: int,
    line_index: int,
    probe_dir: pathlib.Path,
    adjudication_dir: pathlib.Path,
    repo_root: pathlib.Path,
) -> GoldRecord:
    """Select the canonical gold for one line, deterministically or not at all."""
    adjudicated = [
        (p, data)
        for p in sorted(adjudication_dir.glob("adjudicated_*.json"))
        if (data := _read_json(p)) is not None
        and data.get("canvas_index") == canvas_index
        and data.get("line_index") == line_index
        and isinstance(data.get("adjudicated_text"), str)
    ]
    if len(adjudicated) > 1:
        return GoldRecord(
            canvas_index=canvas_index,
            line_index=line_index,
            status="GOLD_MULTIPLE_ADJUDICATED",
            record_paths=tuple(_relative(p, repo_root) for p, _ in adjudicated),
            note=(
                f"{len(adjudicated)} adjudicated records claim this line; "
                "no rule chooses between them"
            ),
        )
    if adjudicated:
        path, data = adjudicated[0]
        text = normalise_tokenisation(str(data["adjudicated_text"]))
        readers = tuple(
            str(r.get("reader", "?")) for r in data.get("readers", []) if isinstance(r, dict)
        )
        dissent = tuple(
            f"{r.get('reader', '?')}: {r.get('dissent', '')}"
            for r in data.get("readers", [])
            if isinstance(r, dict) and r.get("dissent")
        )
        return GoldRecord(
            canvas_index=canvas_index,
            line_index=line_index,
            status="GOLD_OK",
            text=text,
            skeleton=strip_accents(text),
            source="ADJUDICATED",
            record_paths=(_relative(path, repo_root),),
            readers=tuple(sorted(readers)),
            dissent=dissent,
            note="canonical adjudicated record",
        )

    probes = [
        (str(data.get("reader", p.name)), p, data)
        for p in sorted(probe_dir.glob("*.json"))
        if (data := _read_json(p)) is not None
        and data.get("canvas_index") == canvas_index
        and data.get("line_index") == line_index
        and isinstance(data.get("text_devanagari"), str)
    ]
    probes.sort(key=lambda item: (item[0], item[1].name))
    if not probes:
        return GoldRecord(
            canvas_index=canvas_index,
            line_index=line_index,
            status="GOLD_ABSENT",
            note="no adjudicated record and no reader probe for this line",
        )

    grouped: dict[str, list[str]] = {}
    for reader, _, data in probes:
        text = normalise_tokenisation(str(data["text_devanagari"]))
        grouped.setdefault(text, []).append(reader)

    paths = tuple(_relative(p, repo_root) for _, p, _ in probes)
    readers = tuple(reader for reader, _, _ in probes)

    if len(grouped) == 1:
        text = next(iter(grouped))
        return GoldRecord(
            canvas_index=canvas_index,
            line_index=line_index,
            status="GOLD_OK",
            text=text,
            skeleton=strip_accents(text),
            source="PROBE_UNANIMOUS",
            record_paths=paths,
            readers=readers,
            note=(f"all {len(probes)} readers agree after the declared tokenisation normalisation"),
        )

    ranked = sorted(grouped.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    top_text, top_readers = ranked[0]
    if len(top_readers) * 2 > len(probes):
        return GoldRecord(
            canvas_index=canvas_index,
            line_index=line_index,
            status="GOLD_OK",
            text=top_text,
            skeleton=strip_accents(top_text),
            source="PROBE_MAJORITY",
            record_paths=paths,
            readers=readers,
            dissent=tuple(f"{','.join(sorted(rs))}: {t}" for t, rs in ranked[1:]),
            note=(
                f"strict majority {len(top_readers)}/{len(probes)} readers "
                f"({','.join(sorted(top_readers))}) after normalisation"
            ),
        )

    return GoldRecord(
        canvas_index=canvas_index,
        line_index=line_index,
        status="GOLD_UNADJUDICATED",
        record_paths=paths,
        readers=readers,
        dissent=tuple(f"{','.join(sorted(rs))}: {t}" for t, rs in ranked),
        note=(
            f"{len(grouped)} distinct reader texts from {len(probes)} probes "
            "with no strict majority and no adjudicated record; excluded from "
            "metrics rather than resolved by filesystem order"
        ),
    )


# ── Gold-to-prediction correspondence ────────────────────────────────────
#
# Costs are integers so no float comparison decides a pairing.
#
# POSITION_WEIGHT is set so that the largest genuine position disagreement
# seen on the gold lines (0.052 of line width on c411/l09, where the akṣara
# grid and the pixel grid drift apart across the punctuation tail) costs 156,
# comfortably under the 700 it would cost to declare the mark a false
# positive and its partner a false negative. CLASS_MISMATCH_COST sits below
# 2 x GAP_COST so a genuine anudatta/svarita swap is scored as a class error
# rather than hidden as a miss plus a spurious detection.
POSITION_WEIGHT = 3000
CLASS_MISMATCH_COST = 600
GAP_COST = 700

# If the best correspondence is not clearly better than the next one, the
# measurement itself is uncertain and says so, via
# LineMetrics.match_margin_safe. A margin of 0 means no rival pairing exists
# at all, which is the strongest case, not the weakest.
#
# Observed on the five gold lines: 678 to 1454, so this never fires there. It
# is reported rather than gated because it judges the instrument, not the
# pipeline.
MATCH_MARGIN_SAFE = 300


@dataclass(frozen=True, slots=True)
class PredMark:
    index: int
    mark_type: str
    norm_x: float


@dataclass(frozen=True, slots=True)
class MarkPair:
    kind: Literal["MATCH", "FALSE_NEGATIVE", "FALSE_POSITIVE"]
    pred_index: int | None
    gold_index: int | None


def predicted_marks(marks: list[dict[str, Any]], spans: list[tuple[int, int]]) -> list[PredMark]:
    """Detected marks with x normalised over the line's inked extent."""
    if not spans:
        return []
    left, right = spans[0][0], spans[-1][1]
    width = max(right - left, 1)
    return [
        PredMark(
            index=i,
            mark_type=str(m.get("type", "unknown")),
            norm_x=(float(m["x0"] + m["x1"]) / 2.0 - left) / width,
        )
        for i, m in enumerate(marks)
    ]


def _pair_cost(pred: PredMark, gold: GoldMark) -> int:
    cost = round(abs(pred.norm_x - gold.norm_pos) * POSITION_WEIGHT)
    if pred.mark_type != gold.mark_type:
        cost += CLASS_MISMATCH_COST
    return cost


def match_marks_to_gold(
    pred: list[PredMark], gold: list[GoldMark]
) -> tuple[list[MarkPair], int, int]:
    """Monotonic correspondence between detected and gold marks.

    Returns (pairs, total cost, margin over the best alternative pairing).
    A missing detection produces exactly one FALSE_NEGATIVE and leaves every
    other pairing intact — it does not cascade.
    """
    n, m = len(pred), len(gold)
    inf = 1 << 40
    cost = [[inf] * (m + 1) for _ in range(n + 1)]
    cost[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            here = cost[i][j]
            if here >= inf:
                continue
            if i < n and j < m:
                candidate = here + _pair_cost(pred[i], gold[j])
                if candidate < cost[i + 1][j + 1]:
                    cost[i + 1][j + 1] = candidate
            if i < n and here + GAP_COST < cost[i + 1][j]:
                cost[i + 1][j] = here + GAP_COST
            if j < m and here + GAP_COST < cost[i][j + 1]:
                cost[i][j + 1] = here + GAP_COST

    # Backward pass, so the margin is measured against complete alternatives.
    tail = [[inf] * (m + 1) for _ in range(n + 1)]
    tail[n][m] = 0
    for i in range(n, -1, -1):
        for j in range(m, -1, -1):
            if i == n and j == m:
                continue
            best = inf
            if i < n and j < m:
                nxt = tail[i + 1][j + 1]
                if nxt < inf:
                    best = min(best, _pair_cost(pred[i], gold[j]) + nxt)
            if i < n and tail[i + 1][j] < inf:
                best = min(best, GAP_COST + tail[i + 1][j])
            if j < m and tail[i][j + 1] < inf:
                best = min(best, GAP_COST + tail[i][j + 1])
            tail[i][j] = best

    total = cost[n][m]
    pairs: list[MarkPair] = []
    i, j = n, m
    while i > 0 or j > 0:
        if (
            i > 0
            and j > 0
            and cost[i][j] == cost[i - 1][j - 1] + _pair_cost(pred[i - 1], gold[j - 1])
        ):
            pairs.append(MarkPair("MATCH", i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and cost[i][j] == cost[i - 1][j] + GAP_COST:
            pairs.append(MarkPair("FALSE_POSITIVE", i - 1, None))
            i -= 1
        else:
            pairs.append(MarkPair("FALSE_NEGATIVE", None, j - 1))
            j -= 1
    pairs.reverse()

    # Margin: the cheapest complete correspondence that pairs some predicted
    # mark differently from the chosen one.
    chosen = {p.pred_index: p.gold_index for p in pairs}
    margin = 1 << 40
    for i in range(n):
        for j in range(m):
            if chosen.get(i) == j:
                continue
            head, rest = cost[i][j], tail[i + 1][j + 1]
            if head >= inf or rest >= inf:
                continue
            margin = min(margin, head + _pair_cost(pred[i], gold[j]) + rest - total)
    return pairs, total, 0 if margin >= (1 << 40) else max(margin, 0)


# ── Residual error decomposition ─────────────────────────────────────────

ERROR_CATEGORIES = (
    "DETECTION_MISS",
    "SPAN_SEGMENTATION_ERROR",
    "TOKEN_ALIGNMENT_ERROR",
    "CARRIER_ASSIGNMENT_ERROR",
    "GOLD_AMBIGUITY",
    "SOURCE_AMBIGUOUS",
    "OTHER",
)


@dataclass(slots=True)
class LineMetrics:
    """Everything measured on one gold line, with nothing averaged away."""

    matched: int = 0
    gold_total: int = 0
    detected_total: int = 0
    false_negatives: int = 0
    false_positives: int = 0
    class_correct: int = 0
    word_correct: int = 0
    aksara_correct: int = 0
    promoted: int = 0
    promoted_word_correct: int = 0
    promoted_aksara_correct: int = 0
    match_margin: int = 0
    match_margin_safe: bool = True
    errors: dict[str, int] = field(default_factory=lambda: dict.fromkeys(ERROR_CATEGORIES, 0))
    error_detail: list[str] = field(default_factory=list)

    @property
    def detection_recall(self) -> float | None:
        return self.matched / self.gold_total if self.gold_total else None

    @property
    def detection_precision(self) -> float | None:
        return self.matched / self.detected_total if self.detected_total else None

    @property
    def class_accuracy(self) -> float | None:
        return self.class_correct / self.matched if self.matched else None

    @property
    def word_binding_acc(self) -> float | None:
        return self.word_correct / self.matched if self.matched else None

    @property
    def aksara_binding_acc(self) -> float | None:
        return self.aksara_correct / self.matched if self.matched else None

    @property
    def promoted_aksara_acc(self) -> float | None:
        return self.promoted_aksara_correct / self.promoted if self.promoted else None

    @property
    def word_binding_acc_over_gold(self) -> float | None:
        """Word accuracy over every gold mark, not only the matched ones.

        The gated metric divides by matched pairs, which is the right
        denominator for "of the marks we found, how many did we place on the
        right word". It is not robust to a mark escaping correspondence
        altogether (see the module docstring), so this stricter reading is
        reported next to it: a mark that drops into a gap counts against this
        one. It is a diagnostic, not a gate.
        """
        return self.word_correct / self.gold_total if self.gold_total else None

    @property
    def aksara_binding_acc_over_gold(self) -> float | None:
        return self.aksara_correct / self.gold_total if self.gold_total else None


def score_line(
    bindings: list[Binding],
    pred: list[PredMark],
    gold: list[GoldMark],
    gold_source: str,
    unaligned_span_count: int,
) -> LineMetrics:
    """Score one line's bindings against gold, and classify every residual."""
    pairs, _, margin = match_marks_to_gold(pred, gold)
    metrics = LineMetrics(
        gold_total=len(gold),
        detected_total=len(pred),
        match_margin=margin,
        # A correspondence that is barely better than its rival is not a
        # measurement. Nothing downstream is gated on this, but a run whose
        # own scoring was uncertain must say so rather than report a number.
        match_margin_safe=margin == 0 or margin >= MATCH_MARGIN_SAFE,
    )

    for pair in pairs:
        if pair.kind == "FALSE_NEGATIVE":
            metrics.false_negatives += 1
            metrics.errors["DETECTION_MISS"] += 1
            assert pair.gold_index is not None
            g = gold[pair.gold_index]
            metrics.error_detail.append(
                f"DETECTION_MISS: gold {g.mark_type} on word {g.word_index} "
                f"aksara {g.aksara_index} was not detected"
            )
            continue
        if pair.kind == "FALSE_POSITIVE":
            metrics.false_positives += 1
            metrics.errors["OTHER"] += 1
            assert pair.pred_index is not None
            metrics.error_detail.append(
                f"OTHER (false positive): detected mark {pair.pred_index} matches no gold mark"
            )
            continue

        assert pair.pred_index is not None and pair.gold_index is not None
        metrics.matched += 1
        g = gold[pair.gold_index]
        b = bindings[pair.pred_index]
        promoted = b.state in AUTO_PROMOTE
        if promoted:
            metrics.promoted += 1
        class_ok = b.mark_type == g.mark_type
        if class_ok:
            metrics.class_correct += 1
        word_ok = b.token_offset is not None and b.token_offset == g.word_index
        aksara_ok = word_ok and b.aksara_index == g.aksara_index
        if word_ok:
            metrics.word_correct += 1
            if promoted:
                metrics.promoted_word_correct += 1
        if aksara_ok:
            metrics.aksara_correct += 1
            if promoted:
                metrics.promoted_aksara_correct += 1
        # A mark on the right carrier but of the wrong class is still an
        # incorrect binding and has to appear in the decomposition. It used to
        # be skipped here, so an anudatta/svarita swap left class_accuracy
        # below 1.0 with nothing to account for it.
        if aksara_ok and class_ok:
            continue

        category = _classify(b, g, word_ok, class_ok, unaligned_span_count)
        metrics.errors[category] += 1
        metrics.error_detail.append(
            f"{category}: detected {b.mark_type} bound to word "
            f"{b.token_offset} aksara {b.aksara_index} "
            f"({b.aksara_cluster!r}, {b.state}, {b.alignment_state or 'n/a'}); "
            f"gold {g.mark_type} word {g.word_index} aksara {g.aksara_index} "
            f"[gold source {gold_source or 'unknown'}]"
        )
    return metrics


def _classify(
    b: Binding,
    g: GoldMark,
    word_ok: bool,
    class_ok: bool,
    unaligned_span_count: int,
) -> str:
    """Which category a single incorrect binding belongs to.

    GOLD_AMBIGUITY is currently unreachable and is reported as such rather
    than left to look exercised. The only signal available for it is that the
    gold came from a strict majority, and attributing every residual on such
    a line to the readers laundered binder errors: c032/l12 is PROBE_MAJORITY
    over a verse numeral that carries no accent. Firing it properly needs the
    dissenting reader's own text re-parsed to see whether it would have made
    this particular binding correct, which is separate work.
    """
    if b.state == "SOURCE_AMBIGUOUS":
        return "SOURCE_AMBIGUOUS"
    if b.state == "NO_VALID_CARRIER" or b.alignment_state == "ALIGN_GAP_TEXT":
        return "SPAN_SEGMENTATION_ERROR"
    if unaligned_span_count and b.token_offset is None:
        return "SPAN_SEGMENTATION_ERROR"
    if not word_ok:
        return "TOKEN_ALIGNMENT_ERROR"
    if b.aksara_index != g.aksara_index:
        return "CARRIER_ASSIGNMENT_ERROR"
    if not class_ok:
        # The carrier is right and the class is wrong: a detector error, not
        # an alignment one. The class_accuracy gate is what governs these.
        return "OTHER"
    return "OTHER"


# ── Full-line exactness (reported prominently, not gated) ────────────────


def reassemble_accented_line(skeleton: str, bindings: list[Binding]) -> str:
    """Rebuild the accented line from the skeleton plus the bindings."""
    tokens = skeleton.split()
    per_cell: dict[tuple[int, int], list[str]] = {}
    # Sorted by x so two marks sharing one cell reassemble in reading order
    # rather than in whatever order the extractor happened to emit them.
    for b in sorted(bindings, key=lambda b: (b.mark_x0, b.mark_x1)):
        if b.token_offset is None or b.aksara_index is None:
            continue
        mark = ANUDATTA if b.mark_type == "anudatta" else SVARITA
        per_cell.setdefault((b.token_offset, b.aksara_index), []).append(mark)
    out: list[str] = []
    for ti, token in enumerate(tokens):
        clusters = aksara_clusters(token)
        pieces: list[str] = []
        for ci, cluster in enumerate(clusters):
            pieces.append(cluster)
            pieces.extend(per_cell.get((ti, ci), ()))
        out.append("".join(pieces))
    return " ".join(out)


@dataclass(frozen=True, slots=True)
class Exactness:
    skeleton_exact: bool
    accent_set_exact: bool
    carrier_exact: bool
    full_accented_line_exact: bool


def line_exactness(
    gold_text: str,
    gold_skeleton: str,
    skeleton: str,
    bindings: list[Binding],
    metrics: LineMetrics,
) -> Exactness:
    """The four exactness readings for one line."""
    skeleton_exact = unicodedata.normalize("NFC", skeleton) == unicodedata.normalize(
        "NFC", gold_skeleton
    )
    accent_set_exact = (
        metrics.false_negatives == 0
        and metrics.false_positives == 0
        and metrics.class_correct == metrics.matched
    )
    carrier_exact = (
        accent_set_exact
        and metrics.matched == metrics.gold_total
        and metrics.aksara_correct == metrics.gold_total
    )
    rebuilt = reassemble_accented_line(skeleton, bindings)
    full_exact = skeleton_exact and unicodedata.normalize("NFC", rebuilt) == unicodedata.normalize(
        "NFC", gold_text
    )
    return Exactness(
        skeleton_exact=skeleton_exact,
        accent_set_exact=accent_set_exact,
        carrier_exact=carrier_exact,
        full_accented_line_exact=full_exact,
    )
