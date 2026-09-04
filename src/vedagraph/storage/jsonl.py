"""Deterministic, validated JSON Lines storage."""

from collections.abc import Iterable, Iterator
from pathlib import Path

import orjson
from pydantic import BaseModel


def write_jsonl(path: Path, records: Iterable[BaseModel]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("wb") as handle:
        for record in records:
            payload = record.model_dump(mode="json", exclude_none=True)
            handle.write(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS))
            handle.write(b"\n")
            count += 1
    return count


def read_jsonl[ModelT: BaseModel](path: Path, model: type[ModelT]) -> Iterator[ModelT]:
    with path.open("rb") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield model.model_validate(orjson.loads(line))
            except Exception as error:
                raise ValueError(f"invalid {model.__name__} at {path}:{line_number}") from error
