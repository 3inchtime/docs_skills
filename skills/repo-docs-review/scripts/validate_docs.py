#!/usr/bin/env python3
"""Check a docs-map and its local references; this does not prove business truth."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from _docs_common import InputError, emit_json, read_json, read_manifest, repo_path, repository_root


STATUSES = {"verified", "inferred", "pending"}
REVIEW_STATUSES = {"passed", "failed", "pending"}
DIAGRAM_KINDS = {"flowchart", "sequence", "state", "er", "data-flow"}
METHODS = {"source": {"read"}, "test": {"read", "executed"},
           "runtime": {"executed", "observed"}, "business": {"read", "confirmed"}}
PLACEHOLDER = re.compile(
    r"\b(?:TODO|TBD|REPLACE_[A-Z0-9_]+)\b|\{\{[^{}\n]{1,120}\}\}"
    r"|<(?:path|file|symbol|commit|module|真实[^<>\n]*|填写[^<>\n]*|待[^<>\n]*)>"
    r"|待填写|待补充|待接入|请填写", re.I)


class Validator:
    def __init__(self, root: Path, strict: bool = False):
        self.root = root
        self.strict = strict
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def issue(self, code: str, path: str, message: str, *, warning: bool = False,
              blocking: bool = False) -> None:
        target = self.errors if not warning or (blocking and self.strict) else self.warnings
        target.append({"code": code, "path": path, "message": message})

    def text(self, obj: dict[str, Any], field: str, loc: str, *, required: bool = True) -> str | None:
        value = obj.get(field)
        if isinstance(value, str) and value.strip():
            return value
        if required or value is not None:
            self.issue("FIELD", f"{loc}.{field}", "Expected a non-empty string")
        return None

    def array(self, obj: dict[str, Any], field: str, loc: str, *, required: bool = True) -> list[Any]:
        value = obj.get(field)
        if isinstance(value, list):
            return value
        if required or value is not None:
            self.issue("FIELD", f"{loc}.{field}", "Expected an array")
        return []

    def local_path(self, value: Any, loc: str, *, directory_ok: bool = False,
                   exists: bool = True) -> None:
        try:
            repo_path(self.root, value, exists=exists, directory_ok=directory_ok)
        except InputError as exc:
            self.issue("PATH", loc, str(exc))

    def strings(self, values: list[Any], loc: str, *, unique: bool = True) -> list[str]:
        found: list[str] = []
        for i, value in enumerate(values):
            if not isinstance(value, str) or not value.strip():
                self.issue("FIELD", f"{loc}[{i}]", "Expected a non-empty string")
            elif unique and value in found:
                self.issue("DUPLICATE", f"{loc}[{i}]", f"Duplicate value: {value}")
            else:
                found.append(value)
        return found

    def critical(self, item: dict[str, Any], loc: str) -> bool:
        value = item.get("critical", True)
        if type(value) is not bool:
            self.issue("FIELD", f"{loc}.critical", "Expected a boolean")
            return True
        return value

    def state(self, item: dict[str, Any], loc: str) -> None:
        status = item.get("status")
        if not isinstance(status, str) or status not in STATUSES:
            self.issue("STATUS", f"{loc}.status", "Expected verified, inferred, or pending")
        elif status != "verified":
            self.issue("UNRESOLVED", f"{loc}.status", f"Evidence is {status}; review its scope",
                       warning=True, blocking=self.critical(item, loc))
        else:
            self.critical(item, loc)

    def placeholders(self, value: Any, loc: str, status: str | None = None,
                     critical: bool = True) -> None:
        if isinstance(value, dict):
            next_status = value.get("status", status)
            next_critical = value.get("critical", critical)
            for key, child in value.items():
                self.placeholders(child, f"{loc}.{key}", next_status, next_critical is not False)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                self.placeholders(child, f"{loc}[{i}]", status, critical)
        elif isinstance(value, str) and PLACEHOLDER.search(value):
            self.issue("PLACEHOLDER", loc,
                       "Placeholder remains; record the actual value or keep the item explicitly pending",
                       warning=status != "verified", blocking=critical)

    def evidence(self, value: Any, loc: str, seen: set[str]) -> None:
        if not isinstance(value, dict):
            self.issue("FIELD", loc, "Expected an evidence object")
            return
        key = self.text(value, "id", loc)
        if key:
            if key in seen:
                self.issue("DUPLICATE", f"{loc}.id", f"Evidence id is already used: {key}")
            seen.add(key)
        self.text(value, "statement", loc)
        self.local_path(value.get("path"), f"{loc}.path")
        self.text(value, "symbol", loc, required=False)
        kind = value.get("kind")
        method = value.get("method")
        if not isinstance(kind, str) or kind not in METHODS:
            self.issue("FIELD", f"{loc}.kind", "Expected source, test, runtime, or business")
        elif not isinstance(method, str) or method not in METHODS[kind]:
            self.issue("FIELD", f"{loc}.method", f"Allowed methods for {kind}: {sorted(METHODS[kind])}")
        self.state(value, loc)

    def diagram(self, value: Any, loc: str) -> str | None:
        if not isinstance(value, dict):
            self.issue("FIELD", loc, "Expected a diagram object")
            return None
        self.local_path(value.get("source"), f"{loc}.source")
        if "generated" in value:
            self.local_path(value["generated"], f"{loc}.generated")
        kind = value.get("kind")
        if not isinstance(kind, str) or kind not in DIAGRAM_KINDS:
            self.issue("FIELD", f"{loc}.kind", f"Expected one of {sorted(DIAGRAM_KINDS)}")
        self.strings(self.array(value, "node_ids", loc, required=False), f"{loc}.node_ids")
        return kind if isinstance(kind, str) else None

    def glossary(self, name: Any) -> set[str]:
        loc = "$.glossary"
        try:
            data = read_json(repo_path(self.root, name, exists=True))
        except InputError as exc:
            self.issue("GLOSSARY", loc, str(exc))
            return set()
        if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
            self.issue("GLOSSARY", loc, "Expected an object with schema_version 1")
            return set()
        ids: set[str] = set()
        terms = self.array(data, "terms", "glossary$")
        for i, term in enumerate(terms):
            item_loc = f"glossary$.terms[{i}]"
            if not isinstance(term, dict):
                self.issue("FIELD", item_loc, "Expected a term object")
                continue
            key = self.text(term, "id", item_loc)
            if key:
                if key in ids:
                    self.issue("DUPLICATE", f"{item_loc}.id", f"Duplicate term id: {key}")
                ids.add(key)
            for field in ("name", "definition", "scope", "project_meaning", "example"):
                self.text(term, field, item_loc)
            self.strings(self.array(term, "aliases", item_loc), f"{item_loc}.aliases")
            self.state(term, item_loc)
            refs = self.array(term, "code_refs", item_loc)
            sources = self.array(term, "sources", item_loc)
            for label, entries in (("code_refs", refs), ("sources", sources)):
                if not entries:
                    self.issue("MISSING_EVIDENCE", f"{item_loc}.{label}", "No references recorded",
                               warning=term.get("status") != "verified", blocking=self.critical(term, item_loc))
                for j, ref in enumerate(entries):
                    ref_loc = f"{item_loc}.{label}[{j}]"
                    if not isinstance(ref, dict):
                        self.issue("FIELD", ref_loc, "Expected a reference object")
                        continue
                    if label == "code_refs":
                        self.local_path(ref.get("path"), f"{ref_loc}.path")
                        self.text(ref, "symbol", ref_loc, required=False)
                    else:
                        self.text(ref, "title", ref_loc)
                        if not ref.get("path") and not ref.get("url"):
                            self.issue("FIELD", ref_loc, "Source requires a local path or an HTTP(S) URL")
                        if "path" in ref:
                            self.local_path(ref["path"], f"{ref_loc}.path")
                        if "url" in ref:
                            try:
                                parsed = urlsplit(ref["url"])
                                valid = isinstance(ref["url"], str) and parsed.scheme in {"http", "https"} and bool(parsed.netloc)
                            except (AttributeError, TypeError, ValueError):
                                valid = False
                            if not valid:
                                self.issue("FIELD", f"{ref_loc}.url", "Expected an HTTP(S) source URL")
        self.placeholders(data, "glossary$")
        return ids

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        snapshot = data.get("snapshot")
        if not isinstance(snapshot, dict):
            self.issue("FIELD", "$.snapshot", "Expected a snapshot object")
        else:
            commit = snapshot.get("commit")
            if commit is None or commit == "":
                self.issue("SNAPSHOT", "$.snapshot.commit", "Commit is not recorded", warning=True, blocking=True)
            elif not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", commit):
                self.issue("SNAPSHOT", "$.snapshot.commit", "Use the full commit SHA, or null while pending")
            worktree = snapshot.get("worktree")
            if not isinstance(worktree, str) or worktree not in {"clean", "dirty", "unknown"}:
                self.issue("FIELD", "$.snapshot.worktree", "Expected clean, dirty, or unknown")
            elif worktree == "unknown":
                self.issue("SNAPSHOT", "$.snapshot.worktree", "Worktree status is unknown", warning=True, blocking=True)
            self.text(snapshot, "captured_at", "$.snapshot")
            if worktree == "dirty" and not snapshot.get("changes"):
                self.issue("SNAPSHOT", "$.snapshot.changes", "Record the working-tree changes included in the snapshot",
                           warning=True, blocking=True)
        term_ids = self.glossary(data.get("glossary"))
        modules = self.array(data, "modules", "$")
        if not modules:
            self.issue("COVERAGE", "$.modules", "No modules are declared; coverage cannot be evaluated")
        ids: set[str] = set()
        evidence_ids: set[str] = set()
        dependencies: list[tuple[str, str, str]] = []
        for i, module in enumerate(modules):
            loc = f"$.modules[{i}]"
            if not isinstance(module, dict):
                self.issue("FIELD", loc, "Expected a module object")
                continue
            key = self.text(module, "id", loc)
            if key:
                if key in ids:
                    self.issue("DUPLICATE", f"{loc}.id", f"Duplicate module id: {key}")
                ids.add(key)
            self.text(module, "title", loc)
            self.local_path(module.get("page"), f"{loc}.page")
            source_paths = self.array(module, "source_paths", loc)
            if not source_paths:
                self.issue("COVERAGE", f"{loc}.source_paths", "Module has no source mapping")
            for j, value in enumerate(source_paths):
                self.local_path(value, f"{loc}.source_paths[{j}]", directory_ok=True)
            entrypoints = self.array(module, "entrypoints", loc)
            if not entrypoints:
                self.issue("ENTRYPOINT", f"{loc}.entrypoints", "No execution or use entrypoint recorded",
                           warning=True, blocking=True)
            for j, entry in enumerate(entrypoints):
                entry_loc = f"{loc}.entrypoints[{j}]"
                if not isinstance(entry, dict):
                    self.issue("FIELD", entry_loc, "Expected an entrypoint object")
                    continue
                self.local_path(entry.get("path"), f"{entry_loc}.path")
                self.text(entry, "symbol", entry_loc)
                self.text(entry, "trigger", entry_loc)
            diagrams = self.array(module, "diagrams", loc)
            kinds = [self.diagram(diagram, f"{loc}.diagrams[{j}]") for j, diagram in enumerate(diagrams)]
            if not {"flowchart", "data-flow"}.intersection(kinds):
                self.issue("COVERAGE", f"{loc}.diagrams", "Module needs a flowchart or actual data/use flow")
            evidence = self.array(module, "evidence", loc)
            if not evidence:
                self.issue("COVERAGE", f"{loc}.evidence", "Module has no evidence")
            for j, item in enumerate(evidence):
                self.evidence(item, f"{loc}.evidence[{j}]", evidence_ids)
            terms = self.array(module, "terms", loc)
            self.strings(terms, f"{loc}.terms")
            for j, term in enumerate(terms):
                if isinstance(term, str) and term.strip() and term not in term_ids:
                    self.issue("REFERENCE", f"{loc}.terms[{j}]", f"Unknown glossary term: {term}")
            deps = self.array(module, "depends_on", loc)
            self.strings(deps, f"{loc}.depends_on")
            for j, dep in enumerate(deps):
                if isinstance(dep, str) and dep.strip():
                    dependencies.append((key or "", dep, f"{loc}.depends_on[{j}]"))
            owner = module.get("owner")
            if owner is not None and (not isinstance(owner, str) or not owner.strip()):
                self.issue("FIELD", f"{loc}.owner", "Expected a non-empty string or null")
            review = module.get("review")
            if not isinstance(review, dict):
                self.issue("FIELD", f"{loc}.review", "Expected code, reader, and site review statuses")
            else:
                for role in ("code", "reader", "site"):
                    state = review.get(role)
                    if not isinstance(state, str) or state not in REVIEW_STATUSES:
                        self.issue("STATUS", f"{loc}.review.{role}", "Expected passed, failed, or pending")
                    elif state != "passed":
                        self.issue("REVIEW", f"{loc}.review.{role}", f"Review is {state}", warning=True, blocking=True)
        for source, target, loc in dependencies:
            if target not in ids:
                self.issue("REFERENCE", loc, f"Unknown module dependency: {target}")
            elif target == source:
                self.issue("REFERENCE", loc, "A module must not depend on itself")
        for i, item in enumerate(self.array(data, "excluded", "$", required=False)):
            loc = f"$.excluded[{i}]"
            if not isinstance(item, dict):
                self.issue("FIELD", loc, "Expected an exclusion object")
            else:
                self.local_path(item.get("path"), f"{loc}.path", exists=False, directory_ok=True)
                self.text(item, "reason", loc)
        for i, item in enumerate(self.array(data, "open_questions", "$", required=False)):
            loc = f"$.open_questions[{i}]"
            if not isinstance(item, dict):
                self.issue("FIELD", loc, "Expected {question, blocking} object")
                continue
            self.text(item, "question", loc)
            if type(item.get("blocking")) is not bool:
                self.issue("FIELD", f"{loc}.blocking", "Explicitly set blocking to true or false")
            else:
                self.issue("OPEN_QUESTION", loc, "Question remains open", warning=True, blocking=item["blocking"])
        self.placeholders(data, "$")
        return {"ok": not self.errors, "strict": self.strict,
                "counts": {"modules": len(modules), "terms": len(term_ids),
                           "errors": len(self.errors), "warnings": len(self.warnings)},
                "errors": self.errors, "warnings": self.warnings,
                "limits": ["Checks only declared module coverage and structural references.",
                           "Does not execute Mermaid, tests, commands, or browser checks.",
                           "Does not verify source symbols, business claims, freshness, or review honesty."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="Repository root")
    parser.add_argument("--manifest", default="docs-map.json", help="Repository-relative docs-map JSON")
    parser.add_argument("--strict", action="store_true", help="Block critical unresolved evidence and incomplete reviews")
    args = parser.parse_args()
    try:
        root = repository_root(args.repo)
        data, _ = read_manifest(root, args.manifest)
        result = Validator(root, args.strict).validate(data)
    except InputError as exc:
        emit_json({"ok": False, "errors": [{"code": "INPUT", "path": "$", "message": str(exc)}]})
        return 2
    emit_json(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
