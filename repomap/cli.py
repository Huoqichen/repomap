from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from repomap.analyzer import analyze_repository
from repomap.graph import architecture_map_json, build_dependency_graph, graph_to_mermaid
from repomap.repository import cleanup_clone, clone_repository, detect_git_branch

app = typer.Typer(help="Analyze a GitHub repository and generate an architecture map.")
console = Console()


@app.command()
def main(
    repo_url: Annotated[str, typer.Argument(help="GitHub repository URL to analyze.")],
    branch: Annotated[str | None, typer.Option(help="Optional branch to clone.")] = None,
    clone_dir: Annotated[
        Path | None, typer.Option(help="Directory where the repository should be cloned.")
    ] = None,
    json_out: Annotated[
        Path | None, typer.Option(help="Optional file path for the JSON architecture map.")
    ] = None,
    mermaid_out: Annotated[
        Path | None, typer.Option(help="Optional file path for the Mermaid diagram.")
    ] = None,
    keep_clone: Annotated[
        bool, typer.Option(help="Keep the cloned repository when using a temporary directory.")
    ] = False,
) -> None:
    """Clone a repository, analyze its architecture, and print the result."""
    cloned_path: Path | None = None
    temporary_clone = False

    try:
        with console.status("Cloning repository...", spinner="dots"):
            cloned_path, temporary_clone = clone_repository(repo_url, clone_root=clone_dir, branch=branch)
            detected_branch = branch or detect_git_branch(cloned_path)

        with console.status("Analyzing repository...", spinner="dots"):
            analysis = analyze_repository(cloned_path, repo_url, default_branch=detected_branch)
            graph = build_dependency_graph(analysis)
            json_output = architecture_map_json(analysis, graph)
            mermaid_output = graph_to_mermaid(graph)

        console.print(Panel.fit(f"[bold]Project Architecture[/bold]\n{cloned_path}", border_style="cyan"))
        console.print(render_overview(analysis))
        console.print(render_tree(analysis.tree))

        console.print(Panel.fit("[bold]JSON Architecture Map[/bold]", border_style="green"))
        console.print_json(json_output)

        console.print(Panel.fit("[bold]Mermaid Diagram[/bold]", border_style="magenta"))
        console.print(Syntax(mermaid_output, "markdown", theme="monokai", line_numbers=False))

        if json_out:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            json_out.write_text(json_output, encoding="utf-8")
            console.print(f"[green]Saved JSON map to[/green] {json_out}")

        if mermaid_out:
            mermaid_out.parent.mkdir(parents=True, exist_ok=True)
            mermaid_out.write_text(mermaid_output, encoding="utf-8")
            console.print(f"[green]Saved Mermaid diagram to[/green] {mermaid_out}")
    except FileNotFoundError as error:
        console.print(f"[red]Missing executable:[/red] {error}")
        raise typer.Exit(code=1) from error
    except Exception as error:  # noqa: BLE001
        console.print(f"[red]Analysis failed:[/red] {error}")
        raise typer.Exit(code=1) from error
    finally:
        if cloned_path and temporary_clone and not keep_clone:
            cleanup_clone(cloned_path.parent)


def render_overview(analysis) -> Table:
    table = Table(title="Architecture Summary", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="bold")
    table.add_column("Details")
    table.add_row("Primary language", analysis.primary_language or "Unknown")
    table.add_row(
        "Detected languages",
        ", ".join(
            f"{language.name} ({language.file_count})"
            for language in analysis.detected_languages
        )
        or "None",
    )
    table.add_row(
        "Architecture layers",
        ", ".join(
            f"{layer.name} ({layer.module_count})"
            for layer in analysis.architecture_layers
            if layer.name != "Shared"
        )
        or "Shared",
    )
    return table


def render_tree(tree_data: dict) -> Tree:
    root = Tree(tree_data["name"], guide_style="bold bright_blue")
    _add_tree_nodes(root, tree_data.get("children", []))
    return root


def _add_tree_nodes(tree: Tree, children: list[dict]) -> None:
    for child in children:
        branch = tree.add(child["name"])
        if child["type"] == "directory":
            _add_tree_nodes(branch, child.get("children", []))


if __name__ == "__main__":
    app()
