from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from repomap.models import LanguageSummary, ModuleInfo

IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "node_modules",
    "dist",
    "build",
    "vendor",
}

LANGUAGE_EXTENSIONS = {
    "Python": {".py", ".pyi", ".pyw"},
    "JavaScript": {".js", ".jsx", ".mjs", ".cjs"},
    "TypeScript": {".ts", ".tsx", ".mts", ".cts"},
    "Go": {".go"},
    "Rust": {".rs"},
    "Java": {".java"},
    "Kotlin": {".kt", ".kts"},
    "Scala": {".scala", ".sc"},
    "Groovy": {".groovy", ".gradle"},
    "C": {".c"},
    "C++": {".cc", ".cpp", ".cxx", ".c++", ".hh", ".hpp", ".hxx", ".ipp", ".inl"},
    "C#": {".cs", ".csx"},
    "Swift": {".swift"},
    "Objective-C": {".m", ".mm"},
    "PHP": {".php", ".phtml", ".php3", ".php4", ".php5", ".php7", ".php8"},
    "Ruby": {".rb", ".rake", ".gemspec", ".ru"},
    "Perl": {".pl", ".pm", ".t"},
    "Lua": {".lua"},
    "R": {".r"},
    "Julia": {".jl"},
    "Dart": {".dart"},
    "Shell": {".sh", ".bash", ".zsh", ".ksh", ".fish", ".command"},
    "PowerShell": {".ps1", ".psm1", ".psd1"},
    "Batch": {".bat", ".cmd"},
    "Tcl": {".tcl", ".tk"},
    "Elixir": {".ex", ".exs"},
    "Erlang": {".erl", ".hrl"},
    "Haskell": {".hs", ".lhs"},
    "OCaml": {".ml", ".mli", ".mll", ".mly"},
    "F#": {".fs", ".fsi", ".fsx"},
    "Nim": {".nim", ".nims"},
    "Zig": {".zig"},
    "Crystal": {".cr"},
    "Elm": {".elm"},
    "Clojure": {".clj", ".cljs", ".cljc"},
    "Common Lisp": {".lisp", ".lsp", ".cl"},
    "Scheme": {".scm", ".ss"},
    "Racket": {".rkt"},
    "Fortran": {".f", ".f77", ".f90", ".f95", ".f03", ".f08", ".for"},
    "COBOL": {".cob", ".cbl", ".cpy"},
    "Ada": {".adb", ".ads", ".ada"},
    "Pascal": {".pas", ".pp", ".inc"},
    "Visual Basic": {".vb", ".vbs"},
    "D": {".d", ".di"},
    "Solidity": {".sol"},
    "Move": {".move"},
    "V": {".v"},
    "Verilog": {".vh", ".sv", ".svh"},
    "VHDL": {".vhd", ".vhdl"},
    "Assembly": {".asm", ".s"},
    "SQL": {".sql", ".ddl", ".prc"},
    "GraphQL": {".graphql", ".gql"},
    "CSS": {".css", ".scss", ".sass", ".less", ".styl"},
    "HTML": {".html", ".htm", ".xhtml"},
    "XML": {".xml", ".xsd", ".xsl", ".xslt", ".svg"},
    "Vue": {".vue"},
    "Svelte": {".svelte"},
    "Astro": {".astro"},
    "Nix": {".nix"},
    "Starlark": {".bzl"},
    "Terraform": {".tf", ".tfvars"},
    "HCL": {".hcl"},
    "Bicep": {".bicep"},
    "Jsonnet": {".jsonnet", ".libsonnet"},
    "Cue": {".cue"},
    "Rego": {".rego"},
    "Puppet": {".pp"},
    "Raku": {".raku", ".rakumod", ".p6", ".pm6", ".pod6"},
    "Apex": {".cls", ".trigger"},
    "Haxe": {".hx"},
    "ReasonML": {".re", ".rei"},
    "Standard ML": {".sml", ".sig", ".fun"},
    "Awk": {".awk"},
    "AppleScript": {".applescript", ".scpt"},
}

SPECIAL_FILENAMES = {
    "dockerfile": "Dockerfile",
    "containerfile": "Dockerfile",
    "makefile": "Makefile",
    "cmakelists.txt": "CMake",
    "jenkinsfile": "Groovy",
    "vagrantfile": "Ruby",
    "gemfile": "Ruby",
    "rakefile": "Ruby",
    "brewfile": "Ruby",
    "podfile": "Ruby",
    "fastfile": "Ruby",
    "build": "Starlark",
    "workspace": "Starlark",
    "build.bazel": "Starlark",
    "workspace.bazel": "Starlark",
    "buck": "Starlark",
    "buck2": "Starlark",
    ".bashrc": "Shell",
    ".bash_profile": "Shell",
    ".bash_login": "Shell",
    ".profile": "Shell",
    ".zshrc": "Shell",
    ".kshrc": "Shell",
}

SHEBANG_LANGUAGE_HINTS = {
    "python": "Python",
    "python3": "Python",
    "node": "JavaScript",
    "deno": "TypeScript",
    "bun": "JavaScript",
    "bash": "Shell",
    "sh": "Shell",
    "zsh": "Shell",
    "ksh": "Shell",
    "fish": "Shell",
    "pwsh": "PowerShell",
    "powershell": "PowerShell",
    "ruby": "Ruby",
    "perl": "Perl",
    "php": "PHP",
    "lua": "Lua",
    "rscript": "R",
    "julia": "Julia",
    "tclsh": "Tcl",
    "wish": "Tcl",
    "groovy": "Groovy",
}

DEPENDENCY_ANALYSIS_LANGUAGES = {"Python", "JavaScript", "TypeScript", "Go"}
JS_TS_LANGUAGES = {"JavaScript", "TypeScript"}
JS_TS_EXTENSIONS = tuple(
    sorted(
        LANGUAGE_EXTENSIONS["JavaScript"] | LANGUAGE_EXTENSIONS["TypeScript"],
        key=len,
        reverse=True,
    )
)
SORTED_EXTENSION_MATCHES = sorted(
    (
        (extension, language_name)
        for language_name, extensions in LANGUAGE_EXTENSIONS.items()
        for extension in extensions
    ),
    key=lambda item: len(item[0]),
    reverse=True,
)
IMPORT_FROM_RE = re.compile(r"""(?:import|export)\s+(?:[^;]*?\s+from\s+)?["']([^"']+)["']""")
REQUIRE_RE = re.compile(r"""require\(\s*["']([^"']+)["']\s*\)""")
DYNAMIC_IMPORT_RE = re.compile(r"""import\(\s*["']([^"']+)["']\s*\)""")
GO_MODULE_RE = re.compile(r"^\s*module\s+(\S+)\s*$", re.MULTILINE)
GO_SINGLE_IMPORT_RE = re.compile(r'^\s*import\s+"([^"]+)"\s*$', re.MULTILINE)
GO_IMPORT_BLOCK_RE = re.compile(r"import\s*\((.*?)\)", re.DOTALL)
GO_IMPORT_LINE_RE = re.compile(r'^\s*(?:[\w.]+\s+)?"([^"]+)"\s*$', re.MULTILINE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def iter_source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue
        if detect_language(path):
            yield path


def detect_language(path: Path) -> str | None:
    special_name = SPECIAL_FILENAMES.get(path.name.lower())
    if special_name:
        return special_name

    name_lower = path.name.lower()
    for extension, language_name in SORTED_EXTENSION_MATCHES:
        if name_lower.endswith(extension):
            return language_name

    return _detect_language_from_shebang(path)


def build_module_inventory(root: Path) -> tuple[list[ModuleInfo], list[LanguageSummary], str | None]:
    source_files = list(iter_source_files(root))
    language_by_path = {file_path: detect_language(file_path) for file_path in source_files}

    language_counter = Counter()
    extension_counter: dict[str, set[str]] = defaultdict(set)
    for file_path, language in language_by_path.items():
        if not language:
            continue
        language_counter[language] += 1
        extension_counter[language].add(_display_extension(file_path))

    modules: list[ModuleInfo] = []
    python_files = [path for path, language in language_by_path.items() if language == "Python"]
    js_ts_files = [path for path, language in language_by_path.items() if language in JS_TS_LANGUAGES]
    go_files = [path for path, language in language_by_path.items() if language == "Go"]
    analyzed_files = set(python_files) | set(js_ts_files) | set(go_files)
    generic_files = [path for path in source_files if path not in analyzed_files]

    modules.extend(_analyze_python_modules(root, python_files))
    modules.extend(_analyze_javascript_modules(root, js_ts_files, language_by_path))
    modules.extend(_analyze_go_packages(root, go_files))
    modules.extend(_build_generic_modules(root, generic_files, language_by_path))

    languages = [
        LanguageSummary(
            name=language_name,
            file_count=language_counter[language_name],
            extensions=sorted(extension_counter[language_name]),
        )
        for language_name in sorted(language_counter, key=lambda name: (-language_counter[name], name))
    ]
    primary_language = languages[0].name if languages else None
    modules.sort(key=lambda module: (module.language, module.path))
    return modules, languages, primary_language


def module_name_from_path(root: Path, file_path: Path) -> str:
    relative = file_path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if not parts:
        return root.name
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else root.name


def parse_imports(file_path: Path, module_name: str) -> set[str]:
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return set()

    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            imports.update(_resolve_python_from_import(node, module_name))
    return imports


def parse_javascript_imports(file_path: Path) -> set[str]:
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    imports = set(IMPORT_FROM_RE.findall(source))
    imports.update(REQUIRE_RE.findall(source))
    imports.update(DYNAMIC_IMPORT_RE.findall(source))
    return imports


def parse_go_imports(file_path: Path) -> set[str]:
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    imports = set(GO_SINGLE_IMPORT_RE.findall(source))
    for block in GO_IMPORT_BLOCK_RE.findall(source):
        imports.update(GO_IMPORT_LINE_RE.findall(block))
    return imports


def read_go_module_name(root: Path) -> str | None:
    go_mod = root / "go.mod"
    if not go_mod.exists():
        return None

    match = GO_MODULE_RE.search(go_mod.read_text(encoding="utf-8", errors="ignore"))
    return match.group(1) if match else None


def _analyze_python_modules(root: Path, python_files: list[Path]) -> list[ModuleInfo]:
    module_map = {module_name_from_path(root, file_path): file_path for file_path in python_files}
    id_map = {module_name: f"python:{module_name}" for module_name in module_map}
    modules: list[ModuleInfo] = []

    for module_name, file_path in sorted(module_map.items()):
        raw_imports = sorted(parse_imports(file_path, module_name))
        resolved_modules = {
            _resolve_python_internal_module(import_name, module_map)
            for import_name in raw_imports
        }
        internal_dependencies = sorted(
            id_map[resolved_name]
            for resolved_name in resolved_modules
            if resolved_name and resolved_name != module_name
        )
        external_dependencies = sorted(
            _normalize_python_dependency(import_name)
            for import_name in raw_imports
            if _resolve_python_internal_module(import_name, module_map) is None
        )

        modules.append(
            ModuleInfo(
                id=id_map[module_name],
                name=module_name,
                path=file_path.relative_to(root).as_posix(),
                language="Python",
                imports=raw_imports,
                internal_dependencies=internal_dependencies,
                external_dependencies=sorted(set(external_dependencies)),
            )
        )

    return modules


def _analyze_javascript_modules(
    root: Path,
    script_files: list[Path],
    language_by_path: dict[Path, str | None],
) -> list[ModuleInfo]:
    alias_index: dict[str, str] = {}
    path_to_id: dict[Path, str] = {}
    display_by_path: dict[Path, str] = {}

    for file_path in sorted(script_files):
        relative = file_path.relative_to(root)
        base_name = _script_display_name(relative)
        module_id = f"{_language_slug(language_by_path[file_path] or 'script')}:{base_name}"
        resolved_path = file_path.resolve()
        path_to_id[resolved_path] = module_id
        display_by_path[resolved_path] = base_name
        alias_index[base_name] = module_id
        if base_name.endswith("/index"):
            alias_index[base_name[:-6]] = module_id

    modules: list[ModuleInfo] = []
    for file_path in sorted(script_files):
        resolved_path = file_path.resolve()
        module_id = path_to_id[resolved_path]
        display_name = display_by_path[resolved_path]
        language_name = language_by_path[file_path] or "JavaScript"
        raw_imports = sorted(parse_javascript_imports(file_path))

        internal_dependencies: set[str] = set()
        external_dependencies: set[str] = set()

        for import_name in raw_imports:
            resolved = _resolve_javascript_internal_import(root, file_path, import_name, path_to_id, alias_index)
            if resolved and resolved != module_id:
                internal_dependencies.add(resolved)
            elif not resolved:
                external_dependencies.add(_normalize_javascript_dependency(import_name))

        modules.append(
            ModuleInfo(
                id=module_id,
                name=display_name,
                path=file_path.relative_to(root).as_posix(),
                language=language_name,
                imports=raw_imports,
                internal_dependencies=sorted(internal_dependencies),
                external_dependencies=sorted(external_dependencies),
            )
        )

    return modules


def _analyze_go_packages(root: Path, go_files: list[Path]) -> list[ModuleInfo]:
    module_path = read_go_module_name(root)
    package_to_files: dict[Path, list[Path]] = defaultdict(list)
    for file_path in go_files:
        if file_path.name.endswith("_test.go"):
            continue
        package_to_files[file_path.parent].append(file_path)

    package_map: dict[str, tuple[str, str, Path]] = {}
    for package_dir in sorted(package_to_files):
        relative_dir = package_dir.relative_to(root)
        import_path = _go_import_path(module_path, relative_dir)
        package_key = import_path or relative_dir.as_posix() or "."
        module_id = f"go:{relative_dir.as_posix() or 'root'}"
        display_name = import_path or relative_dir.as_posix() or "root"
        package_map[package_key] = (module_id, display_name, package_dir)

    modules: list[ModuleInfo] = []
    for package_key, (module_id, display_name, package_dir) in sorted(package_map.items()):
        imports: set[str] = set()
        for file_path in package_to_files[package_dir]:
            imports.update(parse_go_imports(file_path))

        internal_dependencies: set[str] = set()
        external_dependencies: set[str] = set()
        for import_name in sorted(imports):
            resolved = _resolve_go_internal_import(import_name, package_map)
            if resolved and resolved != module_id:
                internal_dependencies.add(resolved)
            elif not resolved:
                external_dependencies.add(_normalize_go_dependency(import_name))

        modules.append(
            ModuleInfo(
                id=module_id,
                name=display_name,
                path=(package_dir.relative_to(root).as_posix() or "."),
                language="Go",
                imports=sorted(imports),
                internal_dependencies=sorted(internal_dependencies),
                external_dependencies=sorted(external_dependencies),
            )
        )

    return modules


def _build_generic_modules(
    root: Path,
    source_files: list[Path],
    language_by_path: dict[Path, str | None],
) -> list[ModuleInfo]:
    modules: list[ModuleInfo] = []
    for file_path in sorted(source_files):
        language_name = language_by_path[file_path]
        if not language_name:
            continue
        relative_path = file_path.relative_to(root).as_posix()
        module_id = f"{_language_slug(language_name)}:{relative_path}"
        modules.append(
            ModuleInfo(
                id=module_id,
                name=relative_path,
                path=relative_path,
                language=language_name,
                imports=[],
                internal_dependencies=[],
                external_dependencies=[],
            )
        )
    return modules


def _package_for_module(module_name: str) -> str:
    if not module_name:
        return ""
    parts = module_name.split(".")
    if len(parts) == 1:
        return module_name
    return ".".join(parts[:-1])


def _resolve_relative_base(module_name: str, level: int) -> str:
    package = _package_for_module(module_name)
    package_parts = [part for part in package.split(".") if part]
    if level <= 0:
        return package
    if level > len(package_parts):
        return ""
    return ".".join(package_parts[: len(package_parts) - level + 1])


def _resolve_python_from_import(node: ast.ImportFrom, module_name: str) -> set[str]:
    imports: set[str] = set()

    if node.level == 0:
        base = node.module or ""
    else:
        relative_base = _resolve_relative_base(module_name, node.level)
        if node.module:
            base = ".".join(part for part in [relative_base, node.module] if part)
        else:
            base = relative_base

    if base:
        imports.add(base)

    for alias in node.names:
        if alias.name == "*":
            continue
        if base:
            imports.add(f"{base}.{alias.name}")
        else:
            imports.add(alias.name)

    return imports


def _resolve_python_internal_module(import_name: str, module_map: dict[str, Path]) -> str | None:
    if import_name in module_map:
        return import_name

    parts = import_name.split(".")
    for index in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:index])
        if candidate in module_map:
            return candidate

    return None


def _normalize_python_dependency(import_name: str) -> str:
    return import_name.split(".", 1)[0]


def _resolve_javascript_internal_import(
    root: Path,
    file_path: Path,
    import_name: str,
    path_to_id: dict[Path, str],
    alias_index: dict[str, str],
) -> str | None:
    normalized_import = import_name.replace("\\", "/")

    if normalized_import.startswith(("@/", "~/")):
        candidate_base = root / normalized_import[2:]
    elif normalized_import.startswith("/"):
        candidate_base = root / normalized_import.lstrip("/")
    elif normalized_import.startswith("."):
        candidate_base = (file_path.parent / normalized_import).resolve()
    else:
        candidate_base = root / normalized_import

    resolved_path = _resolve_javascript_path(candidate_base)
    if resolved_path and resolved_path in path_to_id:
        return path_to_id[resolved_path]

    alias_key = candidate_base.relative_to(root).as_posix() if candidate_base.is_relative_to(root) else None
    if alias_key and alias_key in alias_index:
        return alias_index[alias_key]

    normalized_key = normalized_import.lstrip("./")
    return alias_index.get(normalized_key)


def _resolve_javascript_path(candidate_base: Path) -> Path | None:
    candidates = [candidate_base]
    if candidate_base.suffix:
        candidates.append(candidate_base.with_suffix(""))

    base_without_suffix = candidate_base if not candidate_base.suffix else candidate_base.with_suffix("")
    for extension in JS_TS_EXTENSIONS:
        candidates.append(base_without_suffix.with_suffix(extension))

    if candidate_base.is_dir() or not candidate_base.suffix:
        for extension in JS_TS_EXTENSIONS:
            candidates.append(candidate_base / f"index{extension}")

    seen: set[Path] = set()
    for candidate in candidates:
        normalized = candidate.resolve()
        if normalized in seen:
            continue
        seen.add(normalized)
        if normalized.exists() and normalized.is_file():
            return normalized

    return None


def _normalize_javascript_dependency(import_name: str) -> str:
    if import_name.startswith("@"):
        parts = import_name.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else import_name
    return import_name.split("/", 1)[0]


def _go_import_path(module_path: str | None, relative_dir: Path) -> str | None:
    relative_text = relative_dir.as_posix()
    if module_path:
        return module_path if relative_text == "." else f"{module_path}/{relative_text}"
    return relative_text if relative_text != "." else None


def _resolve_go_internal_import(import_name: str, package_map: dict[str, tuple[str, str, Path]]) -> str | None:
    if import_name in package_map:
        return package_map[import_name][0]
    return None


def _normalize_go_dependency(import_name: str) -> str:
    if "/" not in import_name:
        return import_name
    parts = import_name.split("/")
    return "/".join(parts[:3]) if "." in parts[0] else parts[0]


def _detect_language_from_shebang(path: Path) -> str | None:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            first_line = handle.readline(512).strip()
    except OSError:
        return None

    if not first_line.startswith("#!"):
        return None

    lower_line = first_line.lower()
    for hint, language_name in SHEBANG_LANGUAGE_HINTS.items():
        if hint in lower_line:
            return language_name
    return None


def _display_extension(path: Path) -> str:
    lower_name = path.name.lower()
    if lower_name in SPECIAL_FILENAMES:
        return path.name
    for extension, _language_name in SORTED_EXTENSION_MATCHES:
        if lower_name.endswith(extension):
            return extension
    return path.suffix.lower() or "(shebang)"


def _script_display_name(relative_path: Path) -> str:
    path_text = relative_path.as_posix()
    if path_text.endswith(".d.ts"):
        base_name = path_text[:-5]
    else:
        base_name = relative_path.with_suffix("").as_posix()
    return base_name[:-6] if base_name.endswith("/index") else base_name


def _language_slug(language_name: str) -> str:
    return NON_ALNUM_RE.sub("-", language_name.strip().lower()).strip("-") or "source"
