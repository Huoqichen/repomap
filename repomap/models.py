from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class LanguageSummary:
    name: str
    file_count: int
    extensions: list[str]


@dataclass(slots=True)
class ModuleInfo:
    id: str
    name: str
    path: str
    language: str
    imports: list[str]
    internal_dependencies: list[str]
    external_dependencies: list[str]
    layer: str = "Shared"


@dataclass(slots=True)
class LayerSummary:
    name: str
    module_count: int
    module_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RepositoryAnalysis:
    repository_url: str
    root_path: Path
    default_branch: str | None
    tree: dict
    modules: list[ModuleInfo]
    detected_languages: list[LanguageSummary]
    primary_language: str | None
    architecture_layers: list[LayerSummary]
