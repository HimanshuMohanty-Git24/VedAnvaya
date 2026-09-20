"""Transition tests for the dependency-staleness gate. Owner round four, Phase B.

The original gate inferred staleness from the Wave 3 stamps on the nodes. Those never come
off, so every consumer read STALE_INPUT for ever and a rebuild could not be expressed at all
-- the gate could report what had been invalidated and never what had been repaired.

``classify()`` is a pure function of (current input hashes, recorded ledger entry). No clock,
no wave stamp, no filesystem read for the hash comparison itself, which is what makes every
transition below testable without a database.

The owner's required transitions, one test each:

    CURRENT     -> CURRENT        nothing changed
    CURRENT     -> STALE_INPUT    one upstream input changed
    STALE_INPUT -> CURRENT        after a successful rebuild
    BLOCKED     -> BLOCKED        the blocker persists
    NOT_APPLICABLE stays N/A
    reverting an upstream hash reproduces the earlier state
"""

from __future__ import annotations

import hashlib
import importlib
import json
import pathlib

import pytest

state = importlib.import_module("scripts.dependency_state")


def entry(inputs: dict[str, str], **extra: object) -> dict[str, object]:
    """A ledger entry with a deliberately misleading ``built_at``.

    Dated in 1999 on purpose. If the implementation ever consults a timestamp to decide
    staleness, every test here that expects CURRENT will fail -- which is the regression the
    original wave-stamp gate was.
    """
    return {
        "consumer": "test",
        "input_hashes": dict(inputs),
        "built_at": "1999-01-01T00:00:00+00:00",
        **extra,
    }


BASE = {
    "label:Devata": "n=419;keyless=0;keys=aaa",
    "type:MENTIONS_ENTITY": "n=28110;unnamed=0;pairs=bbb",
    "file:data/x.json": "ccc",
    "builder:scripts/b.py": "ddd",
}


def test_nothing_changed_stays_current() -> None:
    status, moved, reason = state.classify(dict(BASE), entry(BASE))
    assert status == "CURRENT"
    assert moved == []
    assert reason is None


def test_one_changed_upstream_input_goes_stale_and_names_it() -> None:
    """Naming the input is the point. A single blended digest would say only that
    something moved, which is not enough to decide what to rebuild."""
    current = dict(BASE) | {"type:MENTIONS_ENTITY": "n=28111;unnamed=0;pairs=zzz"}
    status, moved, _ = state.classify(current, entry(BASE))
    assert status == "STALE_INPUT"
    assert moved == ["type:MENTIONS_ENTITY"]


def test_a_changed_file_input_goes_stale() -> None:
    """The round-three ledger hashed the graph only, so editing a staging artifact a
    consumer was built from left it reading CURRENT."""
    current = dict(BASE) | {"file:data/x.json": "edited"}
    status, moved, _ = state.classify(current, entry(BASE))
    assert status == "STALE_INPUT"
    assert moved == ["file:data/x.json"]


def test_a_changed_builder_goes_stale() -> None:
    """A build script that changed leaves output that no longer reproduces."""
    current = dict(BASE) | {"builder:scripts/b.py": "rewritten"}
    status, moved, _ = state.classify(current, entry(BASE))
    assert status == "STALE_INPUT"
    assert moved == ["builder:scripts/b.py"]


def test_an_added_upstream_input_goes_stale() -> None:
    """Declaring a new input must invalidate, not be ignored.

    The comparison walks the union of both key sets, so an input the recorded build never
    saw counts as moved. Comparing only the recorded keys would let a widened declaration
    pass silently.
    """
    current = dict(BASE) | {"label:NewlyDeclared": "n=1;keyless=0;keys=eee"}
    status, moved, _ = state.classify(current, entry(BASE))
    assert status == "STALE_INPUT"
    assert moved == ["label:NewlyDeclared"]


def test_a_removed_upstream_input_goes_stale() -> None:
    current = {k: v for k, v in BASE.items() if k != "file:data/x.json"}
    status, moved, _ = state.classify(current, entry(BASE))
    assert status == "STALE_INPUT"
    assert moved == ["file:data/x.json"]


def test_rebuild_returns_to_current() -> None:
    """STALE_INPUT -> CURRENT after a rebuild, which is the transition the old gate could
    not express at all."""
    moved_graph = dict(BASE) | {"label:Devata": "n=420;keyless=0;keys=fff"}
    assert state.classify(moved_graph, entry(BASE))[0] == "STALE_INPUT"
    # The rebuild records the hashes as they now are.
    assert state.classify(moved_graph, entry(moved_graph))[0] == "CURRENT"


def test_reverting_an_upstream_hash_reproduces_the_earlier_state() -> None:
    """Explicitly required, and it only holds because the fingerprint is order-independent.

    A fingerprint built from unsorted collection order would differ after a revert even
    though the content matched, and the state would never come back.
    """
    reverted = dict(BASE)
    changed = dict(BASE) | {"label:Devata": "n=999;keyless=0;keys=ggg"}
    assert state.classify(changed, entry(BASE))[0] == "STALE_INPUT"
    assert state.classify(reverted, entry(BASE))[0] == "CURRENT"


def test_a_never_built_consumer_is_stale_with_a_reason() -> None:
    status, moved, reason = state.classify(dict(BASE), {})
    assert status == "STALE_INPUT"
    assert reason == "never built"
    assert moved == sorted(BASE)


def test_blocked_stays_blocked_whatever_the_hashes_say() -> None:
    """A blocker is about the ability to rebuild, not about whether inputs moved.

    Asserted with matching hashes so the test proves BLOCKED is not a disguised CURRENT.
    """
    blocked = entry(BASE, blocked_reason="daily LLM quota unavailable")
    status, _, reason = state.classify(dict(BASE), blocked)
    assert status == "BLOCKED"
    assert reason == "daily LLM quota unavailable"
    status, _, _ = state.classify(dict(BASE) | {"file:data/x.json": "moved"}, blocked)
    assert status == "BLOCKED"


def test_not_applicable_stays_not_applicable() -> None:
    na = entry(BASE, not_applicable_reason="no artifact exists for this consumer")
    status, _, reason = state.classify(dict(BASE) | {"label:Devata": "moved"}, na)
    assert status == "NOT_APPLICABLE"
    assert reason == "no artifact exists for this consumer"


def test_not_applicable_takes_precedence_over_blocked() -> None:
    """Both set at once is a contradiction; the order must at least be deterministic.

    N/A wins because "there is nothing to build" is a stronger statement than "it cannot be
    built right now".
    """
    both = entry(BASE, blocked_reason="b", not_applicable_reason="n")
    assert state.classify(dict(BASE), both)[0] == "NOT_APPLICABLE"


def test_a_missing_output_file_is_stale_even_when_inputs_match() -> None:
    """CURRENT claims the output exists. If it is gone, the claim is false."""
    recorded = entry(BASE, output_file="does/not/exist.json", output_hash="abc")
    status, _, reason = state.classify(dict(BASE), recorded)
    assert status == "STALE_INPUT"
    assert reason is not None and "gone" in reason


def test_a_modified_output_file_is_stale_even_when_inputs_match(
    tmp_path: pathlib.Path,
) -> None:
    """Something rewrote the artifact without rebuilding it."""
    artifact = tmp_path / "out.json"
    artifact.write_text('{"a": 1}', encoding="utf-8")
    recorded = entry(
        BASE,
        output_file=str(artifact),
        output_hash=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    )
    assert state.classify(dict(BASE), recorded)[0] == "CURRENT"
    artifact.write_text('{"a": 2}', encoding="utf-8")
    status, _, reason = state.classify(dict(BASE), recorded)
    assert status == "STALE_INPUT"
    assert reason is not None and "no longer matches" in reason


def test_the_timestamp_is_never_the_deciding_field() -> None:
    """The original defect, asserted directly.

    Every entry above is dated 1999. A gate that consulted a timestamp -- or a persistent
    wave marker -- would call all of them stale. This one reads hashes.
    """
    ancient = entry(BASE)
    assert ancient["built_at"] == "1999-01-01T00:00:00+00:00"
    assert state.classify(dict(BASE), ancient)[0] == "CURRENT"
    source = pathlib.Path("scripts/dependency_state.py").read_text(encoding="utf-8")
    body = source.split("def classify(", 1)[1].split("\ndef ", 1)[0]
    for forbidden in ("built_at", "wave3_", "datetime.now"):
        assert forbidden not in body, (
            f"classify() references {forbidden!r}; staleness must be decided by hashes alone"
        )


# ---------------------------------------------------------------------------
# Declarations
# ---------------------------------------------------------------------------


def test_every_declared_file_and_builder_input_exists() -> None:
    """A declared input that is absent hashes to "absent", which is a legitimate state --
    but a typo in a path would also hash to "absent" and look like a real finding."""
    missing: list[str] = []
    for relatives in state.CONSUMER_FILES.values():
        missing += [r for r in relatives if not pathlib.Path(r).exists()]
    for builders in state.CONSUMER_BUILDERS.values():
        missing += [b for b in builders if not pathlib.Path(b).exists()]
    # Declared OUTPUTS get the same treatment, for the same reason and one stronger: Wave 4
    # found two consumers recording the wrong file as their output, and a path typo here would
    # reproduce exactly that -- a consumer judged on a file nobody builds, which never moves
    # and so is never stale.
    for outputs in state.CONSUMER_OUTPUTS.values():
        missing += [o for o in outputs if not pathlib.Path(o).exists()]
    assert not missing, f"declared inputs that do not exist: {sorted(set(missing))}"


def test_no_two_consumers_declare_the_same_output() -> None:
    """The Wave 4 defect, pinned as a rule.

    "Visualization Lab aggregates" and "Knowledge World public projection" both recorded
    ``frontend/.world/world.raw.json``. One of them does build it; the other is a later stage
    that READS it, so it was being judged on a file its own build never touches -- permanently
    CURRENT while shipping a partition and a bundle measured on the previous world.
    """
    owner: dict[str, str] = {}
    collisions: list[str] = []
    for consumer, outputs in state.CONSUMER_OUTPUTS.items():
        for relative in outputs:
            if relative in owner:
                collisions.append(f"{relative} claimed by {owner[relative]} and {consumer}")
            owner[relative] = consumer
    assert not collisions, (
        "two consumers claim one output, so at least one is judged on a file it does not "
        f"build: {collisions}"
    )


def test_a_declared_output_that_moved_is_stale_and_says_which_file() -> None:
    """The check that would have caught the shipped bundle, exercised BAD -> FAIL.

    Written against ``classify`` directly rather than the graph, so it pins the decision and
    not the current state of the filesystem.
    """
    inputs = {"label:Mantra": "same"}
    recorded = {
        "input_hashes": dict(inputs),
        "output_hashes": {
            "pyproject.toml": "a-digest-that-is-not-the-file-s",
        },
    }
    status, moved, reason = state.classify(dict(inputs), recorded)
    assert status == "STALE_INPUT"
    assert moved == []
    assert reason is not None and "pyproject.toml" in reason

    # GOOD -> PASS, with the real digest.
    recorded["output_hashes"] = {
        "pyproject.toml": state.file_digest(pathlib.Path("pyproject.toml"))
    }
    assert state.classify(dict(inputs), recorded)[0] == "CURRENT"


def test_a_declared_output_that_vanished_is_stale_rather_than_ignored() -> None:
    recorded = {
        "input_hashes": {},
        "output_hashes": {"no/such/file.json": "whatever"},
    }
    status, _, reason = state.classify({}, recorded)
    assert status == "STALE_INPUT"
    assert reason is not None and "is gone" in reason


def test_every_consumer_with_files_or_a_builder_is_a_real_consumer() -> None:
    names = {str(c["consumer"]) for c in state.CONSUMERS}
    assert set(state.CONSUMER_FILES) <= names
    assert set(state.CONSUMER_BUILDERS) <= names


def test_the_status_report_records_unexplained_stale_separately() -> None:
    """A STALE_INPUT with neither a moved input nor a reason is a gate malfunction.

    Reported as its own field so "stale because X moved" and "stale and cannot say why" are
    never the same row.
    """
    report = pathlib.Path("data/staging/integration/dependency_status.json")
    if not report.exists():
        pytest.skip("no dependency status in this checkout")
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert "unexplained_stale" in payload
    assert payload["unexplained_stale"] == []


# --- whole-subgraph consumers -------------------------------------------------------------
#
# Wave 4 fixed the world consumers' declared OUTPUTS after 28 retired metre identities shipped
# to the browser from a stage judged on an intermediate. The same defect survived on the INPUT
# side: `export_graph_world.py` selects `MATCH (n) WHERE NOT n:Internal` -- every public label
# -- while the two world consumers between them declared five. Measured at the final closure
# sprint's baseline, 39.0% of public nodes and 68.8% of public edges were invisible to every
# declared hash, `:Chandas` among them.
#
# An enumerated label list is correct only until the next label is added, and being
# correct-until-then is how the defect arose. These pin the subgraph declaration instead.


class _StubSession:
    """Returns a scripted row per query shape. No database, no APOC."""

    def __init__(self, nodes: list[tuple[str, str]], edges: list[tuple[str, str, str]]) -> None:
        self._nodes = nodes  # (identity, label)
        self._edges = edges  # (a, type, b)

    def run(self, query: str, **_: object) -> object:
        if "UNWIND labels(n) AS label" in query:
            counts: dict[str, int] = {}
            for _identity, label in self._nodes:
                counts[label] = counts.get(label, 0) + 1
            return [{"label": k, "c": counts[k]} for k in sorted(counts)]

        class _Single:
            def __init__(self, row: dict[str, object]) -> None:
                self._row = row

            def single(self) -> dict[str, object]:
                return self._row

        if "MATCH (a)-[r]->(b)" in query:
            return _Single(
                {
                    "total": len(self._edges),
                    "unnamed": 0,
                    "pairs": [f"{a}-{t}>{b}" for a, t, b in self._edges],
                }
            )
        return _Single(
            {"total": len(self._nodes), "keyless": 0, "keys": [i for i, _ in self._nodes]}
        )


def test_the_subgraph_fingerprint_moves_when_only_a_label_changes() -> None:
    """The M10 shape exactly: a node marked :Internal, identity and edges untouched.

    This is the case an identity digest alone cannot see, and it is the case that actually
    shipped 28 malformed metre names to every reader of the Knowledge World.
    """
    nodes = [("VG:CH:GAYATRI", "Chandas"), ("VG:CH:TRISTUBH", "Chandas")]
    edges = [("VG:RV:1.1.1", "HAS_CHANDAS", "VG:CH:GAYATRI")]
    before = state.subgraph_fingerprint(_StubSession(nodes, edges), "NOT n:Internal")
    # The same nodes, one of them retired out of the public projection.
    after = state.subgraph_fingerprint(_StubSession(nodes[:1], edges), "NOT n:Internal")
    assert before != after, "retiring a public node must move the subgraph fingerprint"


def test_the_subgraph_fingerprint_sees_labels_no_consumer_enumerates() -> None:
    """A label nobody declared still moves the hash. The enumerated list could not do this."""
    base = [("VG:D:AGNI", "Devata")]
    session_before = _StubSession(base, [])
    # `Epithet` and `RitualRole` appear in no consumer's `reads_labels`.
    session_after = _StubSession([*base, ("VG:EP:JATAVEDAS", "Epithet")], [])
    assert state.subgraph_fingerprint(session_before, "NOT n:Internal") != (
        state.subgraph_fingerprint(session_after, "NOT n:Internal")
    ), "adding an undeclared public label must still move the hash"


def test_the_subgraph_fingerprint_is_stable_under_row_order() -> None:
    """Order out of Cypher is not guaranteed, so the digest must not depend on it."""
    nodes = [("b", "Devata"), ("a", "Concept")]
    forward = state.subgraph_fingerprint(_StubSession(nodes, []), "NOT n:Internal")
    reverse = state.subgraph_fingerprint(_StubSession(list(reversed(nodes)), []), "NOT n:Internal")
    assert forward == reverse


def test_an_edge_swap_of_equal_size_still_moves_the_fingerprint() -> None:
    """A count is unchanged by deleting one edge and adding another; the digest is not."""
    a = _StubSession([], [("x", "MENTIONS_ENTITY", "y")])
    b = _StubSession([], [("x", "MENTIONS_ENTITY", "z")])
    assert state.subgraph_fingerprint(a, "NOT n:Internal") != state.subgraph_fingerprint(
        b, "NOT n:Internal"
    )


def test_every_whole_graph_reader_declares_a_subgraph() -> None:
    """The three consumers whose builders read more than their enumerated labels.

    Pinned by name so that removing a declaration is a test failure rather than a silent
    return to the state where a mutation to :Chandas moved nothing.
    """
    assert set(state.CONSUMER_SUBGRAPHS) == {
        "Knowledge World public projection",
        "Visualization Lab aggregates",
        "quality evaluation",
    }
    for name, (_scope, where) in state.CONSUMER_SUBGRAPHS.items():
        assert where in {"NOT n:Internal", "true"}, f"{name} declares an unknown scope"
