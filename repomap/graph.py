from __future__ import annotations

import json
from dataclasses import asdict

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
    lines = [
        '%%{init: {"theme": "neutral", "flowchart": {"curve": "basis", "htmlLabels": true}}}%%',
        "flowchart LR",
    ]
    if not graph.nodes:
        lines.append('    empty["No source modules found"]')
        return "\n".join(lines)

    node_ids = {node: f"N{index}" for index, node in enumerate(sorted(graph.nodes))}
    grouped_nodes: dict[str, list[str]] = {}
    for node in sorted(graph.nodes):
        layer = graph.nodes[node].get("layer", "Shared")
        grouped_nodes.setdefault(layer, []).append(node)

    for layer_name in ["Frontend", "Backend", "Database", "Infrastructure", "Shared"]:
        if layer_name not in grouped_nodes:
            continue
        subgraph_id = layer_name.replace(" ", "_")
        lines.append(f'    subgraph {subgraph_id}["{layer_name}"]')
        lines.append("        direction TB")
        for node in grouped_nodes[layer_name]:
            label = graph.nodes[node].get("label", node).replace('"', '\\"')
            language = graph.nodes[node].get("language", "")
            node_id = node_ids[node]
            lines.append(f'        {node_id}["{label}<br/><sub>{language}</sub>"]')
            lines.append(f"        class {node_id} {layer_name.lower()}")
        lines.append("    end")

    for source, target in sorted(graph.edges):
        lines.append(f"    {node_ids[source]} --> {node_ids[target]}")

    for node in sorted(graph.nodes):
        node_id = node_ids[node]
        path = graph.nodes[node].get("path", "")
        url = graph.nodes[node].get("url") or path
        tooltip = f'Open {path}'.replace('"', '\\"')
        lines.append(f'    click {node_id} "{url}" "{tooltip}"')

    for layer_name, (fill, stroke) in LAYER_COLORS.items():
        lines.append(
            f"    classDef {layer_name.lower()} fill:{fill},stroke:{stroke},stroke-width:1px,color:#1f2933;"
        )

    return "\n".join(lines)
