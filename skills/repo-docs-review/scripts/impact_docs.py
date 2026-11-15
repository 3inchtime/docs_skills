#!/usr/bin/env python3
"""Find candidate documentation affected by a diff; never claim exhaustive impact."""

from __future__ import annotations

import argparse
import os
import subprocess
from collections import deque
from pathlib import Path
from typing import Any

from _docs_common import InputError, emit_json, read_json, read_manifest, relative_path, repo_path, repository_root


def git(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(["git", "-C", str(root), *args], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, check=False)
    except OSError as exc:
        raise InputError(f"Cannot run Git: {exc}") from exc
    if completed.returncode:
        raise InputError(completed.stderr.decode("utf-8", errors="replace").strip() or "Git command failed")
    return completed.stdout


def changed_from_git(root: Path, base: str, head: str) -> tuple[list[str], dict[str, str]]:
    top = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel").strip())).resolve()
    if top != root:
        raise InputError("--repo must be the Git top-level directory")
    shas: dict[str, str] = {}
    for label, ref in (("base", base), ("head", head)):
        if not ref or ref.startswith("-") or "\x00" in ref:
            raise InputError(f"Invalid {label} ref")
        shas[label] = git(root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").decode().strip()
    raw = git(root, "diff", "--no-ext-diff", "--name-only", "--no-renames", "-z", shas["base"], shas["head"], "--")
    return [os.fsdecode(value) for value in raw.split(b"\x00") if value], shas


def mapping_modules(root: Path, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    source = data.get("modules")
    if not isinstance(source, list) or not source:
        raise InputError("$.modules must be a non-empty array")
    modules: dict[str, dict[str, Any]] = {}
    for i, value in enumerate(source):
        loc = f"$.modules[{i}]"
        if not isinstance(value, dict) or not isinstance(value.get("id"), str) or not value["id"].strip():
            raise InputError(f"{loc}.id must be a non-empty string")
        key = value["id"]
        if key in modules:
            raise InputError(f"{loc}.id duplicates {key}")
        refs: list[tuple[str, str]] = []
        sources = value.get("source_paths", [])
        if not isinstance(sources, list):
            raise InputError(f"{loc}.source_paths must be an array")
        refs.extend((relative_path(root, path), "source_paths") for path in sources)
        for field in ("entrypoints", "evidence"):
            items = value.get(field, [])
            if not isinstance(items, list):
                raise InputError(f"{loc}.{field} must be an array")
            for j, item in enumerate(items):
                if not isinstance(item, dict):
                    raise InputError(f"{loc}.{field}[{j}] must be an object")
                refs.append((relative_path(root, item.get("path")), field))
        page = relative_path(root, value.get("page"))
        refs.append((page, "page"))
        diagrams = value.get("diagrams", [])
        if not isinstance(diagrams, list):
            raise InputError(f"{loc}.diagrams must be an array")
        diagram_sources = []
        for j, diagram in enumerate(diagrams):
            if not isinstance(diagram, dict):
                raise InputError(f"{loc}.diagrams[{j}] must be an object")
            path = relative_path(root, diagram.get("source"))
            diagram_sources.append(path)
            refs.append((path, "diagram"))
        lists = {}
        for field in ("depends_on", "terms"):
            items = value.get(field, [])
            if not isinstance(items, list) or any(not isinstance(x, str) or not x.strip() for x in items):
                raise InputError(f"{loc}.{field} must contain non-empty strings")
            lists[field] = sorted(set(items))
        modules[key] = {"refs": refs, "page": page, "diagrams": diagram_sources, **lists}
    for key, module in modules.items():
        for dep in module["depends_on"]:
            if dep not in modules or dep == key:
                raise InputError(f"Module {key} has an unknown or self dependency: {dep}")
    return modules


def analyze(root: Path, data: dict[str, Any], manifest: str, changed: list[Any]) -> dict[str, Any]:
    files = sorted(set(relative_path(root, name) for name in changed))
    modules = mapping_modules(root, data)
    glossary = relative_path(root, data.get("glossary"))
    reasons: dict[str, list[dict[str, str]]] = {}
    mapped: set[str] = set()
    for key, module in modules.items():
        hits = []
        for path in files:
            if path == manifest:
                hits.append({"kind": "manifest_change", "path": path})
            elif path == glossary and module["terms"]:
                hits.append({"kind": "glossary_change", "path": path})
            for reference, field in module["refs"]:
                if path == reference or path.startswith(reference.rstrip("/") + "/"):
                    hit = {"kind": "direct_change", "path": path, "mapped_by": field, "reference": reference}
                    if hit not in hits:
                        hits.append(hit)
            if any(hit.get("path") == path for hit in hits):
                mapped.add(path)
        if hits:
            reasons[key] = hits
    direct = set(reasons)
    reverse: dict[str, list[str]] = {key: [] for key in modules}
    for key, module in modules.items():
        for dep in module["depends_on"]:
            reverse[dep].append(key)
    queue = deque(sorted(direct))
    expanded: set[str] = set()
    while queue:
        key = queue.popleft()
        if key in expanded:
            continue
        expanded.add(key)
        for dependent in sorted(reverse[key]):
            reason = {"kind": "dependency_change", "depends_on": key}
            if dependent not in reasons:
                reasons[dependent] = []
                queue.append(dependent)
            if reason not in reasons[dependent]:
                reasons[dependent].append(reason)
    affected = sorted(reasons)
    return {"ok": True, "changed_files": files,
            "affected_modules": [{"id": key, "impact": "direct" if key in direct else "dependency",
                                  "reasons": reasons[key]} for key in affected],
            "candidate_pages": sorted({modules[key]["page"] for key in affected}),
            "candidate_diagrams": sorted({path for key in affected for path in modules[key]["diagrams"]}),
            "candidate_terms": sorted({term for key in affected for term in modules[key]["terms"]}),
            "unmapped_changes": sorted(set(files) - mapped),
            "limits": ["Candidates use the current manifest, not complete program dependency analysis.",
                       "Unmapped changes and newly added or removed modules require manual review.",
                       "A commit diff excludes uncommitted and untracked worktree changes."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Repository root")
    parser.add_argument("--manifest", default="docs-map.json", help="Repository-relative manifest")
    parser.add_argument("--base", help="Known base commit or ref")
    parser.add_argument("--head", help="Known head commit or ref")
    parser.add_argument("--changed-files", help="Repository-relative JSON array of changed relative paths; replaces --base/--head")
    args = parser.parse_args()
    if args.changed_files and (args.base or args.head):
        parser.error("--changed-files cannot be combined with --base or --head")
    if not args.changed_files and not (args.base and args.head):
        parser.error("Provide both --base and --head, or --changed-files")
    try:
        root = repository_root(args.repo)
        data, manifest = read_manifest(root, args.manifest)
        if args.changed_files:
            changed = read_json(repo_path(root, args.changed_files, exists=True))
            if not isinstance(changed, list):
                raise InputError("Changed-files JSON must be an array of repository-relative paths")
            comparison = {"changed_files_input": relative_path(root, args.changed_files)}
        else:
            changed, comparison = changed_from_git(root, args.base, args.head)
        result = analyze(root, data, manifest, changed)
        result["comparison"] = comparison
    except InputError as exc:
        emit_json({"ok": False, "error": str(exc)})
        return 2
    emit_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
