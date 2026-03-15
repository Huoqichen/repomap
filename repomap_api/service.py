from __future__ import annotations

from pathlib import Path

from repomap.analyzer import analyze_repository
from repomap.graph import build_architecture_map, build_dependency_graph, graph_to_mermaid
from repomap.repository import cleanup_clone, clone_repository, detect_git_branch
from repomap_api.schemas import AnalyzeResponse, GraphStats


def analyze_remote_repository(repo_url: str, branch: str | None = None, clone_dir: str | None = None) -> AnalyzeResponse:
    cloned_path: Path | None = None
    temporary_clone = False

    try:
        target_dir = Path(clone_dir).expanduser() if clone_dir else None
        cloned_path, temporary_clone = clone_repository(repo_url, clone_root=target_dir, branch=branch)
        detected_branch = branch or detect_git_branch(cloned_path)
        analysis = analyze_repository(cloned_path, repo_url, default_branch=detected_branch)
        graph = build_dependency_graph(analysis)
        architecture_map = build_architecture_map(analysis, graph)
        mermaid = graph_to_mermaid(graph)

        return AnalyzeResponse(
            architecture_map=architecture_map,
            mermaid=mermaid,
            stats=GraphStats(
                nodes=graph.number_of_nodes(),
                edges=graph.number_of_edges(),
                layers=len(analysis.architecture_layers),
            ),
        )
    finally:
        if cloned_path and temporary_clone:
            cleanup_clone(cloned_path.parent)
