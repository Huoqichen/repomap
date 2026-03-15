from __future__ import annotations

from pathlib import Path

from repomap.layers import assign_layers, summarize_layers
from repomap.models import RepositoryAnalysis
from repomap.parser import IGNORED_DIRECTORIES, build_module_inventory


def analyze_repository(root_path: Path, repository_url: str, default_branch: str | None = None) -> RepositoryAnalysis:
    root_path = root_path.resolve()
    modules, detected_languages, primary_language = build_module_inventory(root_path)
    assign_layers(modules)

    return RepositoryAnalysis(
        repository_url=repository_url,
        root_path=root_path,
        default_branch=default_branch,
        tree=build_folder_tree(root_path),
        modules=modules,
        detected_languages=detected_languages,
        primary_language=primary_language,
        architecture_layers=summarize_layers(modules),
    )


def build_folder_tree(root_path: Path) -> dict:
    def walk(path: Path) -> dict:
        children: list[dict] = []
        for child in sorted(path.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
            if child.name in IGNORED_DIRECTORIES:
                continue
            if child.is_dir():
                children.append(walk(child))
            else:
                children.append({"name": child.name, "type": "file"})
        return {"name": path.name, "type": "directory", "children": children}

    return walk(root_path)
