from __future__ import annotations

from collections import Counter, defaultdict

from repomap.models import LayerSummary, ModuleInfo

LAYER_ORDER = ["Frontend", "Backend", "Database", "Infrastructure", "Shared"]

KEYWORD_SCORES = {
    "Frontend": {
        "frontend",
        "client",
        "ui",
        "web",
        "app",
        "pages",
        "views",
        "components",
        "hooks",
        "styles",
        "browser",
    },
    "Backend": {
        "backend",
        "server",
        "api",
        "service",
        "services",
        "handler",
        "handlers",
        "controller",
        "controllers",
        "route",
        "routes",
        "core",
        "cmd",
        "internal",
    },
    "Database": {
        "db",
        "database",
        "migration",
        "migrations",
        "schema",
        "orm",
        "store",
        "storage",
        "sql",
    },
    "Infrastructure": {
        "infra",
        "infrastructure",
        "deploy",
        "deployment",
        "docker",
        "k8s",
        "kubernetes",
        "terraform",
        "helm",
        "config",
        "scripts",
        "ops",
        ".github",
    },
}

DEPENDENCY_HINTS = {
    "Frontend": {
        "react",
        "next",
        "vue",
        "nuxt",
        "svelte",
        "angular",
        "redux",
        "vite",
        "tailwindcss",
    },
    "Backend": {
        "express",
        "koa",
        "fastify",
        "nestjs",
        "flask",
        "django",
        "gin",
        "fiber",
        "chi",
        "echo",
        "grpc",
    },
    "Database": {
        "postgres",
        "mysql",
        "sqlite",
        "mongodb",
        "mongoose",
        "redis",
        "sqlalchemy",
        "prisma",
        "sequelize",
        "typeorm",
        "gorm",
    },
    "Infrastructure": {
        "docker",
        "kubernetes",
        "terraform",
        "aws",
        "azure",
        "gcp",
        "ansible",
        "github.com/aws/aws-sdk-go",
        "github.com/hashicorp/terraform-plugin-sdk",
    },
}


def assign_layers(modules: list[ModuleInfo]) -> list[ModuleInfo]:
    for module in modules:
        module.layer = detect_module_layer(module)
    return modules


def summarize_layers(modules: list[ModuleInfo]) -> list[LayerSummary]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for module in modules:
        grouped[module.layer].append(module.id)

    summaries: list[LayerSummary] = []
    for layer_name in LAYER_ORDER:
        if layer_name in grouped:
            summaries.append(
                LayerSummary(
                    name=layer_name,
                    module_count=len(grouped[layer_name]),
                    module_ids=sorted(grouped[layer_name]),
                )
            )
    return summaries


def detect_module_layer(module: ModuleInfo) -> str:
    parts = _tokenize_path(module.path) + _tokenize_name(module.name)
    score = Counter()

    for layer_name, keywords in KEYWORD_SCORES.items():
        score[layer_name] += sum(2 for part in parts if part in keywords)

    for dependency in module.external_dependencies:
        normalized = dependency.lower()
        for layer_name, hints in DEPENDENCY_HINTS.items():
            if normalized in hints or any(normalized.startswith(f"{hint}/") for hint in hints):
                score[layer_name] += 3

    if module.language == "Go" and any(part in {"cmd", "internal"} for part in parts):
        score["Backend"] += 2

    if score:
        best_layer, best_value = score.most_common(1)[0]
        if best_value > 0:
            return best_layer

    return "Shared"


def _tokenize_path(path: str) -> list[str]:
    return [token for token in path.replace("\\", "/").lower().replace(".", "/").split("/") if token]


def _tokenize_name(name: str) -> list[str]:
    return [token for token in name.lower().replace(":", "/").replace(".", "/").split("/") if token]
