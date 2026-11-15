"""Shared input handling for the documentation review commands (stdlib only)."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any


class InputError(ValueError):
    """A user input cannot be read or does not meet the command contract."""


def repository_root(value: str) -> Path:
    try:
        root = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise InputError(f"Cannot resolve repository: {exc}") from exc
    if not root.is_dir():
        raise InputError(f"Repository is not a directory: {root}")
    return root


def repo_path(root: Path, value: Any, *, exists: bool = False,
              directory_ok: bool = False) -> Path:
    """Resolve a POSIX repository-relative path, including symlink containment."""
    if not isinstance(value, str) or not value.strip():
        raise InputError("Expected a non-empty repository-relative path")
    if "\x00" in value or "\\" in value:
        raise InputError("Use a POSIX relative path without NUL or backslashes")
    rel = PurePosixPath(value)
    if rel.is_absolute() or re.match(r"^[A-Za-z]:", value) or ".." in rel.parts:
        raise InputError("Absolute paths and parent traversal are not allowed")
    if not rel.parts:
        raise InputError("A repository-relative file or directory is required")
    candidate = root.joinpath(*rel.parts)
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise InputError("Path resolves outside the repository or contains an invalid symlink") from exc
    if exists and not resolved.exists():
        raise InputError(f"Path does not exist: {value}")
    if exists and not (resolved.is_file() or (directory_ok and resolved.is_dir())):
        raise InputError(f"Expected {'file or directory' if directory_ok else 'file'}: {value}")
    return candidate


def relative_path(root: Path, value: Any) -> str:
    """Normalize lexical spelling but retain a symlink's repository-relative name."""
    candidate = repo_path(root, value)
    return candidate.relative_to(root).as_posix()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              InputError(f"Invalid JSON constant: {value}")))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputError(f"Cannot read JSON {path.name}: {exc}") from exc


def read_manifest(root: Path, name: str) -> tuple[dict[str, Any], str]:
    path = repo_path(root, name, exists=True)
    value = read_json(path)
    if not isinstance(value, dict):
        raise InputError("Manifest must be a JSON object")
    if type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise InputError("Manifest schema_version must be integer 1")
    return value, relative_path(root, name)


def emit_json(value: Any) -> None:
    # ASCII escaping also preserves unusual filenames decoded with surrogateescape.
    print(json.dumps(value, ensure_ascii=True, indent=2))
