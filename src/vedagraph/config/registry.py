"""Typed YAML registry loading."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from vedagraph.models import (
    CorpusBuildConfig,
    FullCorpusBuildConfig,
    Source,
    SourceArtifact,
    TextVersionDescriptor,
    Work,
)


def _load_list[ModelT: BaseModel](path: Path, key: str, model: type[ModelT]) -> list[ModelT]:
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get(key), list):
        raise ValueError(f"{path} must contain a '{key}' list")
    return [model.model_validate(item) for item in payload[key]]


def load_sources(path: Path = Path("data/registry/sources.yaml")) -> list[Source]:
    return _load_list(path, "sources", Source)


def load_works(path: Path = Path("data/registry/works.yaml")) -> list[Work]:
    return _load_list(path, "works", Work)


def load_source_artifacts(
    path: Path = Path("data/registry/source_artifacts.yaml"),
) -> list[SourceArtifact]:
    return _load_list(path, "source_artifacts", SourceArtifact)


def load_text_versions(
    path: Path = Path("data/registry/text_versions.yaml"),
) -> list[TextVersionDescriptor]:
    return _load_list(path, "text_versions", TextVersionDescriptor)


def load_build_config(path: Path) -> CorpusBuildConfig:
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return CorpusBuildConfig.model_validate(payload)


def load_full_build_config(path: Path) -> FullCorpusBuildConfig:
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    return FullCorpusBuildConfig.model_validate(payload)
