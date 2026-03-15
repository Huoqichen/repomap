from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def clone_repository(repo_url: str, clone_root: Path | None = None, branch: str | None = None) -> tuple[Path, bool]:
    """Clone a repository and return the checkout path plus whether it is temporary."""
    temporary_clone = clone_root is None
    base_dir = Path(tempfile.mkdtemp(prefix="repograph-")) if temporary_clone else clone_root.expanduser().resolve()
    base_dir.mkdir(parents=True, exist_ok=True)

    repo_name = _repo_name_from_url(repo_url)
    destination = base_dir / repo_name
    if destination.exists():
        raise FileExistsError(f"Destination already exists: {destination}")

    command = ["git", "clone", "--depth", "1"]
    if branch:
        command.extend(["--branch", branch])
    command.extend([repo_url, str(destination)])

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip() or error.stdout.strip() or str(error)
        raise RuntimeError(f"git clone failed: {stderr}") from error

    return destination, temporary_clone


def cleanup_clone(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def detect_git_branch(repo_path: Path) -> str | None:
    command = ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        return None

    branch = result.stdout.strip()
    return branch if branch and branch != "HEAD" else None


def github_blob_url(repo_url: str, branch: str | None, relative_path: str) -> str | None:
    if "github.com/" not in repo_url or not branch:
        return None

    normalized = repo_url.removesuffix(".git").rstrip("/")
    return f"{normalized}/blob/{branch}/{relative_path}"


def _repo_name_from_url(repo_url: str) -> str:
    name = repo_url.rstrip("/").rsplit("/", 1)[-1]
    return name[:-4] if name.endswith(".git") else name
