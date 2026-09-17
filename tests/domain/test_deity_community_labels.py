"""``display_label`` is the product's one universal text slot, so it must hold text.

All 12 ``:Internal :DeityCommunity`` nodes landed with an INTEGER ``display_label`` (0-11).
Neo4j does not coerce: a graph-wide ``toLower(n.display_label)`` raises a type error the
moment it reaches one of them, and two benchmark probes died on exactly that. The graph's
own ``community_id`` is a STRING (``'0'``), so the importer coerced the match property and
not the display label -- which is why nothing caught it.

Two generators produced it together and both are fixed:

* ``data/staging/communities/build_communities_staging.py`` emitted ``community_id`` as a
  Python ``int`` and no ``display_label`` at all;
* ``scripts/wave3_import_plan.py`` set ``display_label_field="community_id"``.

BAD -> FAIL and GOOD -> PASS are both asserted here against the staging record, so the pair
cannot drift back.
"""

from __future__ import annotations

import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
COMMUNITIES = REPO / "data" / "staging" / "communities" / "communities.jsonl"
IMPORT_PLAN = REPO / "scripts" / "wave3_import_plan.py"
BUILD = REPO / "data" / "staging" / "communities" / "build_communities_staging.py"


def _rows() -> list[dict[str, object]]:
    if not COMMUNITIES.exists():  # pragma: no cover - staging artifact absent
        pytest.skip("communities.jsonl is not in this checkout")
    lines = COMMUNITIES.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def _lower(value: object) -> str:
    """What a Cypher ``toLower(n.display_label)`` does, and what it does to an integer."""
    if not isinstance(value, str):
        raise TypeError(
            f"toLower() expects a string; got {type(value).__name__} {value!r}. "
            "Neo4j raises here rather than coercing, and the whole query dies."
        )
    return value.lower()


def test_an_integer_display_label_is_what_broke_the_probes() -> None:
    """BAD -> FAIL: the exact value that shipped. GOOD -> PASS: the replacement."""
    with pytest.raises(TypeError):
        _lower(0)
    assert _lower("DEITY_COMMUNITY_0") == "deity_community_0"


def test_the_staging_build_emits_a_string_display_label() -> None:
    rows = _rows()
    assert rows, "no community records staged"
    for row in rows:
        label = row.get("display_label")
        assert isinstance(label, str), (
            f"community {row.get('community_id')!r} has a non-string display_label "
            f"{label!r}; display_label is the product's one universal text slot"
        )
        assert _lower(label)


def test_the_label_is_an_identifier_and_not_a_name() -> None:
    """The node's own interpretation_warning forbids naming it.

    "This community has no name and must not be given one in a product surface. Naming it
    would convert a co-occurrence statistic into a theological claim." So the fix may not
    be to invent "the Agni community"; it has to be a renderable identifier.
    """
    for row in _rows():
        assert row["display_label"] == f"DEITY_COMMUNITY_{row['community_id']}"


def test_the_import_plan_reads_the_string_and_not_the_integer_id() -> None:
    """The other half of the pair. Fixing one generator alone changes nothing."""
    plan = IMPORT_PLAN.read_text(encoding="utf-8")
    block = plan[plan.index("COMMUNITIES_ARTIFACT_NODES") :][:1200]
    assert 'display_label_field="display_label"' in block
    assert 'display_label_field="community_id"' not in block
    assert '"display_label": f"DEITY_COMMUNITY_' in BUILD.read_text(encoding="utf-8")
