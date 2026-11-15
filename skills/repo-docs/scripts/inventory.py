#!/usr/bin/env python3
"""Collect file-name evidence for repository documentation, without reading source contents."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit, urlunsplit

TOOL = "repo-docs.inventory"
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".next", ".astro", "vendor", "target"}
MANIFESTS = {"go.mod", "go.work", "package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts", "Gemfile", "composer.json", "mix.exs"}
LOCKS = {"go.sum", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock", "Pipfile.lock", "Cargo.lock", "composer.lock", "Gemfile.lock"}
TASKS = {"Makefile", "makefile", "Justfile", "justfile", "Taskfile.yml", "Taskfile.yaml", "tox.ini", "noxfile.py"}
LANGUAGES = {".go": "Go", ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro", ".sql": "SQL"}
ENTRY_WORDS = re.compile(r"(^|[/_.-])(main|routes?|router|handlers?|controllers?|consumers?|workers?|jobs?|cron|cli|commands?|webhooks?)([/_.-]|$)", re.I)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=False)


def clean_remote(value: str) -> str:
    """Keep repository identity while dropping URL credentials, query and fragment."""
    if "://" in value:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if ":" in host:
            host = "[" + host + "]"
        if parsed.port:
            host += ":" + str(parsed.port)
        return urlunsplit((parsed.scheme, host, parsed.path, "", ""))
    return value.split("?", 1)[0].split("#", 1)[0].rsplit("@", 1)[-1]


def snapshot(repo: Path) -> dict:
    def read(*args: str) -> str | None:
        result = git(repo, *args)
        return result.stdout.decode("utf-8", "replace").strip() if result.returncode == 0 else None
    status = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=normal")
    remote = read("config", "--get", "remote.origin.url")
    return {
        "commit": read("rev-parse", "--verify", "HEAD"),
        "branch": read("symbolic-ref", "--quiet", "--short", "HEAD"),
        "worktree": ("dirty" if status.stdout else "clean") if status.returncode == 0 else "unknown",
        "changes": status.stdout.replace(b"\0", b"\n").decode("utf-8", "replace").strip() if status.returncode == 0 and status.stdout else None,
        "remote": clean_remote(remote) if remote else None,
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def collect(repo: Path, max_files: int = 20000, include_generated: bool = False) -> dict:
    if not repo.is_dir():
        raise ValueError("--repo must be an existing directory")
    if max_files < 1:
        raise ValueError("--max-files must be positive")
    repo = repo.resolve()
    probe = git(repo, "rev-parse", "--is-inside-work-tree")
    is_git = probe.returncode == 0 and probe.stdout.strip() == b"true"
    if is_git:
        listed = git(repo, "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", ".")
        if listed.returncode:
            raise ValueError("git ls-files failed; file coverage is unknown")
        raw_paths = sorted(set(os.fsdecode(x) for x in listed.stdout.split(b"\0") if x))
        mode = "git-tracked-and-unignored"
        snap = snapshot(repo)
    else:
        raw_paths = []
        for directory, dirs, files in os.walk(repo, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d != ".git" and (include_generated or d not in SKIP_DIRS))
            raw_paths.extend((Path(directory) / name).relative_to(repo).as_posix() for name in files)
        raw_paths.sort()
        mode = "filesystem-without-gitignore"
        snap = {"commit": None, "branch": None, "worktree": "unknown", "changes": None, "remote": None, "captured_at": datetime.now(timezone.utc).isoformat()}
    files = []
    omitted: Counter = Counter()
    for raw in raw_paths:
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts:
            omitted["outside-requested-scope"] += 1
            continue
        if ".git" in path.parts or (not include_generated and any(x in SKIP_DIRS for x in path.parts)):
            omitted["generated-or-vendored-directory"] += 1
            continue
        local = repo / raw
        try:
            local.resolve().relative_to(repo)
        except (ValueError, RuntimeError, OSError):
            omitted["symlink-outside-repo-or-unresolvable"] += 1
            continue
        if not local.is_file():
            omitted["missing-file-or-submodule-directory"] += 1
            continue
        files.append(path.as_posix())
    total = len(files)
    chosen = files[:max_files]
    def names(pool: set[str]) -> list[str]:
        return [f for f in chosen if PurePosixPath(f).name in pool]
    return {
        "tool": TOOL,
        "schema_version": 1,
        "repo": str(repo),
        "snapshot": snap,
        "discovery_mode": mode,
        "limits": {"max_files": max_files, "truncated": total > max_files, "eligible_file_count": total, "emitted_file_count": len(chosen)},
        "excluded_directory_names": sorted({".git"} if include_generated else SKIP_DIRS),
        "omitted_counts": dict(sorted(omitted.items())),
        "file_names_sha256": hashlib.sha256("\0".join(files).encode("utf-8", "surrogateescape")).hexdigest(),
        "language_file_counts": dict(sorted(Counter(LANGUAGES[PurePosixPath(f).suffix] for f in chosen if PurePosixPath(f).suffix in LANGUAGES).items())),
        "manifests": names(MANIFESTS),
        "lockfiles": names(LOCKS),
        "task_files": names(TASKS),
        "project_rules": [f for f in chosen if PurePosixPath(f).name in {"AGENTS.md", "CONTRIBUTING.md"}],
        "runtime_and_ci_candidates": [f for f in chosen if PurePosixPath(f).name.startswith(("Dockerfile", "Containerfile", "docker-compose", "compose.")) or f.startswith(".github/workflows/") or PurePosixPath(f).name in {".nvmrc", ".tool-versions", ".python-version"}],
        "entrypoint_candidates": [f for f in chosen if ENTRY_WORDS.search(f) and PurePosixPath(f).suffix in LANGUAGES],
        "files": chosen,
        "interpretation": "File-name inventory only. Candidates are not confirmed modules or reachable entrypoints. No source contents were read and no project command was executed. The filename hash is not a content or correctness check.",
    }


def write_output(path: Path, report: dict) -> None:
    if path.is_symlink():
        raise ValueError("output must not be a symlink")
    if path.exists():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError("output already exists and is not an inventory report") from exc
        if not isinstance(previous, dict) or previous.get("tool") != TOOL:
            raise ValueError("refusing to overwrite a file not produced by this inventory tool")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".inventory-", suffix=".json", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(report, stream, ensure_ascii=True, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="Write or update an inventory report; otherwise print JSON")
    parser.add_argument("--max-files", type=int, default=20000)
    parser.add_argument("--include-generated", action="store_true", help="Include default vendor/build directories; .git remains excluded")
    args = parser.parse_args()
    try:
        report = collect(args.repo, args.max_files, args.include_generated)
        if args.output:
            write_output(args.output, report)
            print(f"Inventory saved: {args.output}")
        else:
            print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(f"inventory: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
