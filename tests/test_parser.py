from pathlib import Path

from repomap.graph import graph_to_mermaid
from repomap.layers import detect_module_layer
from repomap.models import ModuleInfo
from repomap.parser import (
    build_module_inventory,
    detect_language,
    module_name_from_path,
    parse_go_imports,
    parse_imports,
    parse_javascript_imports,
)


def test_module_name_from_init_file() -> None:
    root = Path("repo")
    file_path = root / "pkg" / "__init__.py"
    assert module_name_from_path(root, file_path) == "pkg"


def test_parse_imports_resolves_relative_imports(tmp_path: Path) -> None:
    module_file = tmp_path / "pkg" / "feature.py"
    module_file.parent.mkdir(parents=True)
    module_file.write_text(
        "import os\nfrom . import helpers\nfrom ..core import service\n",
        encoding="utf-8",
    )

    imports = parse_imports(module_file, "pkg.feature")

    assert "os" in imports
    assert "pkg.helpers" in imports
    assert "core.service" in imports


def test_parse_javascript_imports_collects_common_forms(tmp_path: Path) -> None:
    module_file = tmp_path / "src" / "app.js"
    module_file.parent.mkdir(parents=True)
    module_file.write_text(
        '\n'.join(
            [
                'import React from "react";',
                'import { api } from "./lib/api";',
                'const db = require("../db");',
                'const lazy = import("./lazy");',
            ]
        ),
        encoding="utf-8",
    )

    imports = parse_javascript_imports(module_file)

    assert "react" in imports
    assert "./lib/api" in imports
    assert "../db" in imports
    assert "./lazy" in imports


def test_detect_language_supports_typescript_shell_and_special_files(tmp_path: Path) -> None:
    ts_file = tmp_path / "src" / "app.tsx"
    ts_file.parent.mkdir(parents=True)
    ts_file.write_text("export const App = () => null;\n", encoding="utf-8")

    shell_file = tmp_path / "scripts" / "deploy"
    shell_file.parent.mkdir(parents=True)
    shell_file.write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")

    docker_file = tmp_path / "Dockerfile"
    docker_file.write_text("FROM python:3.12-slim\n", encoding="utf-8")

    assert detect_language(ts_file) == "TypeScript"
    assert detect_language(shell_file) == "Shell"
    assert detect_language(docker_file) == "Dockerfile"


def test_parse_go_imports_handles_blocks(tmp_path: Path) -> None:
    module_file = tmp_path / "server.go"
    module_file.write_text(
        '\n'.join(
            [
                'package main',
                'import (',
                '    "fmt"',
                '    api "github.com/example/project/api"',
                ')',
            ]
        ),
        encoding="utf-8",
    )

    imports = parse_go_imports(module_file)

    assert "fmt" in imports
    assert "github.com/example/project/api" in imports


def test_build_module_inventory_includes_generic_languages_and_typescript(tmp_path: Path) -> None:
    python_file = tmp_path / "app.py"
    python_file.write_text("import os\n", encoding="utf-8")

    ts_file = tmp_path / "web" / "main.ts"
    ts_file.parent.mkdir(parents=True)
    ts_file.write_text('import "./ui";\n', encoding="utf-8")

    ts_dep = tmp_path / "web" / "ui.ts"
    ts_dep.write_text("export const ui = true;\n", encoding="utf-8")

    rust_file = tmp_path / "src" / "lib.rs"
    rust_file.parent.mkdir(parents=True)
    rust_file.write_text("fn main() {}\n", encoding="utf-8")

    modules, languages, primary_language = build_module_inventory(tmp_path)

    language_names = [language.name for language in languages]
    module_languages = {module.path: module.language for module in modules}

    assert "Python" in language_names
    assert "TypeScript" in language_names
    assert "Rust" in language_names
    assert module_languages["src/lib.rs"] == "Rust"
    assert module_languages["web/main.ts"] == "TypeScript"
    assert primary_language in {"Python", "TypeScript", "Rust"}


def test_layer_detection_uses_path_and_dependencies() -> None:
    module = ModuleInfo(
        id="javascript:web/components/button",
        name="web/components/button",
        path="web/components/button.tsx",
        language="JavaScript",
        imports=[],
        internal_dependencies=[],
        external_dependencies=["react"],
    )

    assert detect_module_layer(module) == "Frontend"


def test_graph_to_mermaid_generates_edges() -> None:
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_node(
        "javascript:api/handlers",
        label="api/handlers",
        path="api/handlers.js",
        language="JavaScript",
        layer="Backend",
        url="https://github.com/example/repo/blob/main/api/handlers.js",
    )
    graph.add_node(
        "python:core.service",
        label="core.service",
        path="core/service.py",
        language="Python",
        layer="Backend",
        url="https://github.com/example/repo/blob/main/core/service.py",
    )
    graph.add_edge("javascript:api/handlers", "python:core.service")

    mermaid = graph_to_mermaid(graph)

    assert "flowchart LR" in mermaid
    assert "api/handlers" in mermaid
    assert "core.service" in mermaid
    assert "click N0" in mermaid or "click N1" in mermaid
