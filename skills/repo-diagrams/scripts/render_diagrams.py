#!/usr/bin/env python3
"""Compile a Mermaid directory with an existing mmdc and publish after success.

Python 3.10+; standard library only. This wrapper does not install Mermaid CLI
and cannot validate diagram semantics against application code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import uuid
import xml.etree.ElementTree as ET


MARKER = ".repo-diagrams-output.json"
GENERATOR = "repo-diagrams/render_diagrams.py"


class RenderError(Exception):
    """A user-actionable input, compiler, or publication error."""


def safe_relative(value: object) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise RenderError("Invalid generated-file path in output marker")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("..", ".") for part in path.parts):
        raise RenderError("Output marker contains an unsafe relative path")
    if path.suffix != ".svg" or ":" in value:
        raise RenderError("Output marker may list only relative SVG paths")
    return Path(*path.parts)


def inspect_output(output: Path) -> None:
    """Refuse to replace files that were not produced by this wrapper."""
    if output.is_symlink():
        raise RenderError("Output directory must not be a symbolic link")
    if not output.exists():
        return
    if not output.is_dir():
        raise RenderError("Output path is not a directory")
    if not any(output.iterdir()):
        return
    marker = output / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise RenderError("Non-empty output directory is not managed by this script; choose an empty dedicated directory")
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RenderError(f"Cannot read output marker: {exc}") from exc
    if not isinstance(data, dict) or data.get("generator") != GENERATOR or data.get("schema_version") != 1:
        raise RenderError("Output marker does not identify a supported generated directory")
    rows = data.get("files")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise RenderError("Output marker has an invalid files list")
    allowed_files = {Path(MARKER)}
    allowed_dirs: set[Path] = set()
    for row in rows:
        relative = safe_relative(row.get("output"))
        allowed_files.add(relative)
        allowed_dirs.update(p for p in relative.parents if p != Path("."))
    for entry in output.rglob("*"):
        relative = entry.relative_to(output)
        if entry.is_symlink():
            raise RenderError(f"Output contains a symbolic link: {relative}")
        allowed = allowed_dirs if entry.is_dir() else allowed_files
        if relative not in allowed:
            raise RenderError(f"Output contains an unmanaged item: {relative}; move it before rebuilding")


def discover(source: Path) -> list[Path]:
    files: list[Path] = []
    outputs: set[str] = set()
    for current, dirs, names in os.walk(source, followlinks=False):
        for name in dirs:
            if (Path(current) / name).is_symlink():
                raise RenderError(f"Input contains a symbolic-link directory: {Path(current, name).relative_to(source)}")
        for name in names:
            path = Path(current) / name
            if path.suffix.lower() != ".mmd":
                continue
            if path.is_symlink() or not path.is_file():
                raise RenderError(f"Diagram input must be a regular file: {path.relative_to(source)}")
            relative = path.relative_to(source)
            # Do not produce colliding outputs on case-insensitive systems.
            target = relative.with_suffix(".svg").as_posix().casefold()
            if target in outputs:
                raise RenderError(f"Diagram names produce colliding output paths: {relative}")
            outputs.add(target)
            files.append(relative)
    if not files:
        raise RenderError("Input directory contains no .mmd files; no output was changed")
    return sorted(files, key=lambda p: p.as_posix())


def resolve_compiler(command: str) -> str:
    executable = shutil.which(command)
    if executable is None:
        raise RenderError("mmdc was not found; supply --mmdc with an installed Mermaid CLI executable. This script does not install dependencies.")
    return executable


def verify_svg(path: Path) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise RenderError(f"Compiler did not produce a non-empty SVG: {path.name}")
    try:
        tag = ET.parse(path).getroot().tag
    except (OSError, ET.ParseError) as exc:
        raise RenderError(f"Compiler produced invalid XML for {path.name}: {exc}") from exc
    if tag not in ("svg", "{http://www.w3.org/2000/svg}svg"):
        raise RenderError(f"Compiler output is not an SVG document: {path.name}")


def publish(staged: Path, output: Path) -> None:
    # Keep the previous directory until the new directory has been moved in.
    # Concurrent writers to this same output directory are not supported.
    inspect_output(output)
    backup: Path | None = None
    if output.exists():
        backup = output.with_name(f".{output.name}.previous-{uuid.uuid4().hex}")
        output.rename(backup)
    try:
        staged.rename(output)
    except OSError:
        if backup is not None:
            backup.rename(output)
        raise
    if backup is not None:
        try:
            shutil.rmtree(backup)
        except OSError as exc:
            print(f"warning: new SVGs are published; previous generated output remains at {backup}: {exc}", file=sys.stderr)


def render(source_arg: str, output_arg: str, mmdc: str, timeout: float) -> dict:
    source = Path(source_arg).expanduser().resolve(strict=True)
    raw_output = Path(output_arg).expanduser().absolute()
    if raw_output.is_symlink():
        raise RenderError("Output directory must not be a symbolic link")
    output = raw_output.resolve()
    if not source.is_dir():
        raise RenderError("Input must be a directory")
    if source == output or source in output.parents or output in source.parents:
        raise RenderError("Input and output directories must not overlap")
    inspect_output(output)
    files = discover(source)
    compiler = resolve_compiler(mmdc)
    output.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{output.name}.build-", dir=output.parent))
    rows = []
    try:
        for relative in files:
            src = source / relative
            dest_relative = relative.with_suffix(".svg")
            dest = staged / dest_relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            before = hashlib.sha256(src.read_bytes()).hexdigest()
            try:
                result = subprocess.run(
                    [compiler, "-i", str(src), "-o", str(dest)],
                    capture_output=True, text=True, timeout=timeout, check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise RenderError(f"Mermaid compiler timed out for {relative} after {timeout:g}s") from exc
            if result.returncode:
                detail = (result.stderr or result.stdout).strip()
                raise RenderError(f"Mermaid compiler failed for {relative} (exit {result.returncode})\n{detail}")
            verify_svg(dest)
            if hashlib.sha256(src.read_bytes()).hexdigest() != before:
                raise RenderError(f"Input changed while compiling: {relative}; rerun against a stable snapshot")
            rows.append({"source": relative.as_posix(), "output": dest_relative.as_posix(), "source_sha256": before})
        # Also detect changes to earlier diagrams during later compilations.
        if discover(source) != files:
            raise RenderError("Input diagram set changed during compilation; rerun")
        for row in rows:
            if hashlib.sha256((source / row["source"]).read_bytes()).hexdigest() != row["source_sha256"]:
                raise RenderError(f"Input changed during compilation: {row['source']}; rerun")
        manifest = {
            "schema_version": 1, "generator": GENERATOR,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
            "files": rows,
        }
        (staged / MARKER).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        publish(staged, output)
        return {"status": "rendered", "count": len(rows), "output": str(output), "files": rows,
                "scope": "SVG generation only; visual review and code-semantic review remain separate"}
    finally:
        if staged.exists():
            shutil.rmtree(staged)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Directory containing Mermaid .mmd files")
    parser.add_argument("--output", required=True, help="Empty or script-managed dedicated SVG output directory")
    parser.add_argument("--mmdc", default="mmdc", help="Installed Mermaid CLI executable, not a shell command")
    parser.add_argument("--timeout", type=float, default=60, help="Timeout in seconds per diagram (default: 60)")
    args = parser.parse_args(argv)
    if not 0 < args.timeout < float("inf"):
        parser.error("--timeout must be a finite positive number")
    try:
        result = render(args.input, args.output, args.mmdc, args.timeout)
    except (RenderError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
