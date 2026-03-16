from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import PurePosixPath

import networkx as nx

from repomap.models import RepositoryAnalysis
from repomap.repository import github_blob_url

LAYER_COLORS = {
    "Frontend": ("#fff3bf", "#8f5b00"),
    "Backend": ("#d3f9d8", "#1b5e20"),
    "Database": ("#ffd8a8", "#8c2d04"),
    "Infrastructure": ("#d0ebff", "#0b7285"),
    "Shared": ("#f1f3f5", "#495057"),
}
MERMAID_LAYER_ORDER = ["Frontend", "Backend", "Database", "Infrastructure", "Shared"]
MERMAID_CORE_LAYERS = ["Frontend", "Backend", "Database"]
MERMAID_MAX_COMPONENTS_PER_LAYER = 10


def build_dependency_graph(analysis: RepositoryAnalysis) -> nx.DiGraph:
    graph = nx.DiGraph()

    for module in analysis.modules:
        graph.add_node(
            module.id,
            label=module.name,
            path=module.path,
            language=module.language,
            layer=module.layer,
            url=github_blob_url(analysis.repository_url, analysis.default_branch, module.path),
        )

    for module in analysis.modules:
        for dependency in module.internal_dependencies:
            if graph.has_node(dependency):
                graph.add_edge(module.id, dependency)

    return graph


def build_architecture_map(analysis: RepositoryAnalysis, graph: nx.DiGraph) -> dict:
    return {
        "repository_url": analysis.repository_url,
        "root_path": str(analysis.root_path),
        "default_branch": analysis.default_branch,
        "primary_language": analysis.primary_language,
        "detected_languages": [asdict(language) for language in analysis.detected_languages],
        "architecture_layers": [asdict(layer) for layer in analysis.architecture_layers],
        "folder_tree": analysis.tree,
        "modules": [asdict(module) for module in analysis.modules],
        "graph": {
            "nodes": [
                {
                    "id": node,
                    "label": graph.nodes[node].get("label", node),
                    "path": graph.nodes[node].get("path", ""),
                    "language": graph.nodes[node].get("language", ""),
                    "layer": graph.nodes[node].get("layer", "Shared"),
                    "url": graph.nodes[node].get("url"),
                }
                for node in sorted(graph.nodes)
            ],
            "edges": [
                {"source": source, "target": target}
                for source, target in sorted(graph.edges)
            ],
        },
    }


def architecture_map_json(analysis: RepositoryAnalysis, graph: nx.DiGraph) -> str:
    return json.dumps(build_architecture_map(analysis, graph), indent=2)


def graph_to_mermaid(graph: nx.DiGraph) -> str:
    diagrams = graph_to_mermaid_diagrams(graph)
    return diagrams[0]["chart"] if diagrams else _empty_mermaid()


def graph_to_mermaid_diagrams(graph: nx.DiGraph) -> list[dict[str, str]]:
    if not graph.nodes:
        return [{"key": "overview", "title": "Overview", "chart": _empty_mermaid()}]

    diagrams: list[dict[str, str]] = [
        {"key": "overview", "title": "Overview", "chart": _layer_overview_mermaid(graph)}
    ]

    for layer_name in MERMAID_LAYER_ORDER:
        if not any(graph.nodes[node].get("layer", "Shared") == layer_name for node in graph.nodes):
            continue
        diagrams.append(
            {
                "key": layer_name.lower(),
                "title": layer_name,
                "chart": _layer_component_mermaid(graph, layer_name),
            }
        )
    return diagrams


def _layer_overview_mermaid(graph: nx.DiGraph) -> str:
    lines = [
        '%%{init: {"theme": "neutral", "flowchart": {"curve": "basis", "htmlLabels": true}}}%%',
        "flowchart LR",
    ]
    layer_counts = _layer_counts(graph)
    active_layers = [layer for layer in MERMAID_CORE_LAYERS if layer_counts.get(layer)]
    if not active_layers:
        active_layers = [layer for layer in MERMAID_LAYER_ORDER if layer_counts.get(layer)]

    node_ids = {layer_name: f"L{index}" for index, layer_name in enumerate(active_layers)}
    for layer_name in active_layers:
        lines.append(f'    {node_ids[layer_name]}["{layer_name}<br/><sub>{layer_counts[layer_name]} modules</sub>"]')
        lines.append(f"    class {node_ids[layer_name]} {layer_name.lower()}")

    layer_edges = _layer_edges(graph, active_layers)
    for source_layer, target_layer, edge_count in layer_edges:
        lines.append(f'    {node_ids[source_layer]} -->|"{edge_count}"| {node_ids[target_layer]}')

    lines.extend(_layer_class_defs())
    return "\n".join(lines)


def _layer_component_mermaid(graph: nx.DiGraph, layer_name: str) -> str:
    lines = [
        '%%{init: {"theme": "neutral", "flowchart": {"curve": "basis", "htmlLabels": true}}}%%',
        "flowchart LR",
    ]

    component_nodes = _layer_components(graph, layer_name)
    if not component_nodes:
        return _empty_mermaid()

    component_ids = {component_name: f"C{index}" for index, component_name in enumerate(component_nodes)}
    lines.append(f'    subgraph {layer_name.lower()}["{layer_name}"]')
    lines.append("        direction LR")
    for component_name, component_meta in component_nodes.items():
        label = component_meta["short_label"].replace('"', '\\"')
        subtitle = f'{component_meta["count"]} modules'.replace('"', '\\"')
        component_id = component_ids[component_name]
        lines.append(f'        {component_id}["{label}<br/><sub>{subtitle}</sub>"]')
        lines.append(f"        class {component_id} {layer_name.lower()}")
    lines.append("    end")

    for source_component, target_component, edge_count in _component_edges(graph, layer_name, component_nodes):
        if source_component == target_component:
            continue
        lines.append(f'    {component_ids[source_component]} -->|"{edge_count}"| {component_ids[target_component]}')

    for component_name, component_meta in component_nodes.items():
        component_id = component_ids[component_name]
        url = component_meta.get("url")
        tooltip = f'Open {component_meta["path"]}'.replace('"', '\\"')
        if url:
            lines.append(f'    click {component_id} "{url}" "{tooltip}"')

    lines.extend(_layer_class_defs())
    return "\n".join(lines)


def _empty_mermaid() -> str:
    return "\n".join(
        [
            '%%{init: {"theme": "neutral", "flowchart": {"curve": "basis", "htmlLabels": true}}}%%',
            "flowchart LR",
            '    empty["No source modules found"]',
        ]
    )


def _layer_counts(graph: nx.DiGraph) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in graph.nodes:
        layer_name = graph.nodes[node].get("layer", "Shared")
        counts[layer_name] = counts.get(layer_name, 0) + 1
    return counts


def _layer_edges(graph: nx.DiGraph, included_layers: list[str]) -> list[tuple[str, str, int]]:
    edge_counts: dict[tuple[str, str], int] = {}
    included = set(included_layers)
    for source, target in graph.edges:
        source_layer = graph.nodes[source].get("layer", "Shared")
        target_layer = graph.nodes[target].get("layer", "Shared")
        if source_layer not in included or target_layer not in included or source_layer == target_layer:
            continue
        key = (source_layer, target_layer)
        edge_counts[key] = edge_counts.get(key, 0) + 1
    return sorted((source, target, count) for (source, target), count in edge_counts.items())


def _layer_components(graph: nx.DiGraph, layer_name: str) -> dict[str, dict[str, str | int]]:
    grouped: dict[str, dict[str, str | int]] = {}
    for node in sorted(graph.nodes):
        if graph.nodes[node].get("layer", "Shared") != layer_name:
            continue
        component_name = _component_name(graph.nodes[node].get("path", ""), graph.nodes[node].get("label", node))
        component = grouped.setdefault(
            component_name,
            {
                "short_label": _component_label(component_name),
                "count": 0,
                "path": graph.nodes[node].get("path", ""),
                "url": graph.nodes[node].get("url"),
            },
        )
        component["count"] = int(component["count"]) + 1
        current_path = str(component["path"])
        next_path = graph.nodes[node].get("path", "")
        if next_path and len(next_path) < len(current_path or next_path):
            component["path"] = next_path
            component["url"] = graph.nodes[node].get("url")

    ranked = sorted(
        grouped.items(),
        key=lambda item: (-int(item[1]["count"]), str(item[1]["short_label"])),
    )[:MERMAID_MAX_COMPONENTS_PER_LAYER]
    return dict(ranked)


def _component_edges(
    graph: nx.DiGraph,
    layer_name: str,
    component_nodes: dict[str, dict[str, str | int]],
) -> list[tuple[str, str, int]]:
    included = set(component_nodes)
    edge_counts: dict[tuple[str, str], int] = {}
    for source, target in graph.edges:
        if graph.nodes[source].get("layer", "Shared") != layer_name:
            continue
        if graph.nodes[target].get("layer", "Shared") != layer_name:
            continue
        source_component = _component_name(graph.nodes[source].get("path", ""), graph.nodes[source].get("label", source))
        target_component = _component_name(graph.nodes[target].get("path", ""), graph.nodes[target].get("label", target))
        if source_component not in included or target_component not in included:
            continue
        key = (source_component, target_component)
        edge_counts[key] = edge_counts.get(key, 0) + 1
    return sorted((source, target, count) for (source, target), count in edge_counts.items())


def _component_name(path: str, fallback_label: str) -> str:
    if not path:
        return fallback_label

    parts = [part for part in PurePosixPath(path).parts if part not in {"."}]
    while len(parts) > 1 and parts[0].lower() in {"src", "main", "test", "tests", "java", "kotlin", "scala", "groovy", "lib"}:
        parts = parts[1:]

    if len(parts) >= 2 and parts[0].lower() in {"apps", "packages", "services", "crates", "modules"}:
        return f"{parts[0]}/{parts[1]}"
    return parts[0] if parts else fallback_label


def _component_label(component_name: str) -> str:
    tail = component_name.split("/")[-1]
    normalized = tail.replace("-", " ").replace("_", " ").strip()
    if len(normalized) <= 10:
        return normalized.upper()
    return normalized.title()


def _layer_class_defs() -> list[str]:
    return [
        f"    classDef {layer_name.lower()} fill:{fill},stroke:{stroke},stroke-width:1px,color:#1f2933;"
        for layer_name, (fill, stroke) in LAYER_COLORS.items()
    ]
