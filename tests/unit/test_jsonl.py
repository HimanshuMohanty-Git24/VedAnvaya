from pathlib import Path

from vedagraph.config.registry import load_works
from vedagraph.models import Work
from vedagraph.storage import read_jsonl, write_jsonl


def test_validated_jsonl_roundtrip_is_deterministic(tmp_path: Path) -> None:
    records = load_works()[:2]
    output = tmp_path / "works.jsonl"
    assert write_jsonl(output, records) == 2
    first_bytes = output.read_bytes()
    assert list(read_jsonl(output, Work)) == records
    write_jsonl(output, records)
    assert output.read_bytes() == first_bytes
