#!/usr/bin/env python3
"""Check this package's constrained skill metadata, local references and Python syntax."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"repo-docs", "repo-diagrams", "repo-docs-site", "business-glossary", "repo-docs-review"}
LINK = re.compile(r"\[[^\]\n]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")


def run() -> list[str]:
    errors = []
    dirs = {p.name: p for p in (ROOT / "skills").iterdir() if p.is_dir()}
    if set(dirs) != EXPECTED:
        errors.append(f"Skill directories differ: expected {sorted(EXPECTED)}, got {sorted(dirs)}")
    for name, directory in sorted(dirs.items()):
        path = directory / "SKILL.md"
        if not path.is_file():
            errors.append(f"{name}: missing SKILL.md")
            continue
        text = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        if not match:
            errors.append(f"{name}: missing YAML frontmatter")
            continue
        header = match.group(1)
        keys = re.findall(r"^([a-zA-Z_][\w-]*):", header, re.M)
        if sorted(keys) != ["description", "name"]:
            errors.append(f"{name}: frontmatter must contain only name and description")
        skill_name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", header, re.M)
        if not skill_name or skill_name.group(1) != name or len(name) > 64:
            errors.append(f"{name}: invalid or mismatched name")
        description = re.search(r"^description:\s*(.+?)(?=\n[a-zA-Z_][\w-]*:|\Z)", header, re.M | re.S)
        if not description or len(description.group(1).strip()) < 30 or len(description.group(1).strip()) > 1024:
            errors.append(f"{name}: description must explain its task and triggers within 1024 characters")
        if len(text.splitlines()) > 500:
            errors.append(f"{name}: move detail out of SKILL.md (over 500 lines)")
        if "[TODO" in text or "TODO:" in text:
            errors.append(f"{name}: unfinished initializer placeholder")
        metadata = directory / "agents/openai.yaml"
        if not metadata.is_file():
            errors.append(f"{name}: missing agents/openai.yaml")
        else:
            fields = {}
            for line in metadata.read_text(encoding="utf-8").splitlines():
                item = re.match(r"  (display_name|short_description|default_prompt):\s*(.+)$", line)
                if item:
                    try:
                        fields[item.group(1)] = json.loads(item.group(2))
                    except ValueError:
                        errors.append(f"{name}: UI string {item.group(1)} must be JSON-compatible double-quoted YAML")
            if not all(fields.get(key) for key in ("display_name", "short_description", "default_prompt")):
                errors.append(f"{name}: incomplete UI metadata")
            if not 25 <= len(fields.get("short_description", "")) <= 64:
                errors.append(f"{name}: short_description must have 25–64 characters")
            if "$" + name not in fields.get("default_prompt", ""):
                errors.append(f"{name}: default_prompt must name ${name}")
    for path in ROOT.rglob("*.md"):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for target in LINK.findall(text):
            target = target.strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("#") or "{{" in target:
                continue
            local = (path.parent / unquote(parsed.path)).resolve()
            if not local.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing local link {target}")
    for path in ROOT.rglob("*.py"):
        if ".git" not in path.parts:
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                errors.append(f"{path.relative_to(ROOT)}: {exc}")
    for path in (ROOT / "skills").rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
    return errors


if __name__ == "__main__":
    found = run()
    for item in found:
        print(item, file=sys.stderr)
    if found:
        raise SystemExit(1)
    print(f"Validated {len(EXPECTED)} skills: metadata, local references, JSON and Python syntax.")
