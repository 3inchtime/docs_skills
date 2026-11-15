"""Behavioral tests for doc-reference boundaries, strictness, and impact mapping."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "repo-docs-review" / "scripts"


class ReviewToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        for name, content in {
            "src/export.py": "def run():\n    return 'sample'\n",
            "docs/export.md": "# Synthetic test module\n",
            "docs/export.mmd": "flowchart TD\n  start --> done\n",
            "docs/export.svg": '<svg xmlns="http://www.w3.org/2000/svg"/>',
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        self.glossary = {"schema_version": 1, "terms": [{
            "id": "report-range", "name": "报告范围", "aliases": [],
            "definition": "本测试夹具使用的报告日期范围。", "scope": "Synthetic fixture only",
            "project_meaning": "为测试输入映射而设置的字段。", "example": "一天的报告范围。",
            "code_refs": [{"path": "src/export.py", "symbol": "run"}],
            "sources": [{"title": "Fixture implementation", "path": "src/export.py"}],
            "status": "verified"
        }]}
        self.manifest = {"schema_version": 1,
            "snapshot": {"commit": "a" * 40, "worktree": "clean", "captured_at": "2026-01-01T00:00:00Z"},
            "glossary": "docs/glossary.json", "excluded": [], "open_questions": [],
            "modules": [{"id": "export", "title": "Synthetic export", "page": "docs/export.md",
                "source_paths": ["src/export.py"],
                "entrypoints": [{"path": "src/export.py", "symbol": "run", "trigger": "Fixture call"}],
                "diagrams": [{"source": "docs/export.mmd", "generated": "docs/export.svg",
                              "kind": "flowchart", "node_ids": ["start", "done"]}],
                "evidence": [{"id": "export-run", "kind": "source", "path": "src/export.py",
                              "symbol": "run", "statement": "Fixture function returns a literal.",
                              "status": "verified", "method": "read"}],
                "terms": ["report-range"], "depends_on": [], "owner": None,
                "review": {"code": "passed", "reader": "passed", "site": "passed"}}]}
        self.write_inputs()

    def write_inputs(self):
        (self.root / "docs-map.json").write_text(json.dumps(self.manifest))
        (self.root / "docs/glossary.json").write_text(json.dumps(self.glossary))

    def run_tool(self, name, *args):
        result = subprocess.run([sys.executable, str(SCRIPTS / name), "--repo", str(self.root), *args],
                                capture_output=True, text=True)
        self.assertNotIn("Traceback", result.stderr, result.stderr)
        return result, json.loads(result.stdout) if result.stdout.strip() else None

    def validate(self, strict=False):
        self.write_inputs()
        return self.run_tool("validate_docs.py", *(["--strict"] if strict else []))

    def impact(self, changed):
        self.write_inputs()
        (self.root / "changed.json").write_text(json.dumps(changed))
        return self.run_tool("impact_docs.py", "--changed-files", "changed.json")

    def test_structural_success_allows_unknown_owner(self):
        result, data = self.validate(strict=True)
        self.assertEqual(result.returncode, 0, data)
        self.assertTrue(data["ok"])
        self.assertIn("Does not verify source symbols", " ".join(data["limits"]))

    def test_missing_page_is_structural_error(self):
        self.manifest["modules"][0]["page"] = "docs/missing.md"
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(x["path"] == "$.modules[0].page" for x in data["errors"]))

    def test_rejects_parent_traversal(self):
        (self.root.parent / "outside.py").write_text("secret = 1")
        self.manifest["modules"][0]["source_paths"] = ["../outside.py"]
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(x["code"] == "PATH" for x in data["errors"]))

    def test_rejects_symlink_escape(self):
        outside = self.root.parent / "outside.py"
        outside.write_text("secret = 1")
        (self.root / "src/link.py").symlink_to(outside)
        self.manifest["modules"][0]["source_paths"] = ["src/link.py"]
        result, _ = self.validate()
        self.assertEqual(result.returncode, 1)

    def test_missing_term_and_dependency_are_reported(self):
        module = self.manifest["modules"][0]
        module["terms"] = ["unknown-term"]
        module["depends_on"] = ["unknown-module"]
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(sum(x["code"] == "REFERENCE" for x in data["errors"]), 2)

    def test_duplicate_module_and_evidence_ids_are_rejected(self):
        self.manifest["modules"].append(copy.deepcopy(self.manifest["modules"][0]))
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(sum(x["code"] == "DUPLICATE" for x in data["errors"]), 2)

    def test_invalid_list_items_do_not_shift_reference_diagnostics(self):
        self.manifest["modules"][0]["terms"] = [None, "unknown-term"]
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        reference = next(x for x in data["errors"] if x["code"] == "REFERENCE")
        self.assertEqual(reference["path"], "$.modules[0].terms[1]")

    def test_sequence_only_does_not_satisfy_module_flow(self):
        self.manifest["modules"][0]["diagrams"][0]["kind"] = "sequence"
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(x["code"] == "COVERAGE" for x in data["errors"]))

    def test_pending_is_warning_unless_strict(self):
        self.manifest["modules"][0]["evidence"][0]["status"] = "pending"
        result, data = self.validate()
        self.assertEqual(result.returncode, 0, data)
        self.assertTrue(data["warnings"])
        result, data = self.validate(strict=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(x["code"] == "UNRESOLVED" for x in data["errors"]))

    def test_noncritical_inference_is_allowed_in_strict_mode(self):
        evidence = self.manifest["modules"][0]["evidence"][0]
        evidence.update(status="inferred", critical=False)
        result, data = self.validate(strict=True)
        self.assertEqual(result.returncode, 0, data)
        self.assertTrue(data["warnings"])

    def test_blocking_question_and_review_fail_strict_mode(self):
        self.manifest["open_questions"] = [{"question": "Missing business rule", "blocking": True}]
        self.manifest["modules"][0]["review"]["reader"] = "pending"
        result, data = self.validate(strict=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual({x["code"] for x in data["errors"]}, {"OPEN_QUESTION", "REVIEW"})

    def test_placeholder_cannot_be_marked_verified(self):
        self.glossary["terms"][0]["project_meaning"] = "待填写"
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(x["code"] == "PLACEHOLDER" for x in data["errors"]))

    def test_comparison_operators_and_html_are_not_placeholders(self):
        self.manifest["modules"][0]["evidence"][0]["statement"] = "Check count < limit and price > 0; show <code>limit</code>."
        result, data = self.validate(strict=True)
        self.assertEqual(result.returncode, 0, data)

    def test_braced_template_cannot_be_marked_verified(self):
        self.glossary["terms"][0]["project_meaning"] = "{{project_meaning}}"
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(any(x["code"] == "PLACEHOLDER" for x in data["errors"]))

    def test_invalid_status_types_produce_diagnostics(self):
        module = self.manifest["modules"][0]
        module["evidence"][0]["status"] = {}
        module["evidence"][0]["kind"] = []
        module["diagrams"][0]["kind"] = {}
        module["review"]["code"] = []
        self.manifest["snapshot"]["worktree"] = {}
        result, data = self.validate()
        self.assertEqual(result.returncode, 1)
        self.assertGreaterEqual(len(data["errors"]), 5)

    def test_duplicate_json_keys_are_rejected(self):
        (self.root / "docs-map.json").write_text('{"schema_version":1,"schema_version":1}')
        result, data = self.run_tool("validate_docs.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Duplicate JSON key", data["errors"][0]["message"])

    def add_dependent(self, key, dependency):
        module = copy.deepcopy(self.manifest["modules"][0])
        module.update(id=key, source_paths=[f"src/{key}.py"], page=f"docs/{key}.md",
                      depends_on=[dependency], entrypoints=[], evidence=[], diagrams=[], terms=[])
        self.manifest["modules"].append(module)

    def test_impact_propagates_through_dependencies(self):
        self.add_dependent("worker", "export")
        self.add_dependent("api", "worker")
        result, data = self.impact(["src/export.py", "new/unmapped.py"])
        self.assertEqual(result.returncode, 0, data)
        self.assertEqual([x["id"] for x in data["affected_modules"]], ["api", "export", "worker"])
        self.assertEqual(data["unmapped_changes"], ["new/unmapped.py"])
        self.assertIn("docs/api.md", data["candidate_pages"])

    def test_impact_handles_dependency_cycle_without_loop(self):
        self.add_dependent("worker", "export")
        self.manifest["modules"][0]["depends_on"] = ["worker"]
        result, data = self.impact(["src/export.py"])
        self.assertEqual(result.returncode, 0, data)
        self.assertEqual(len(data["affected_modules"]), 2)

    def test_impact_keeps_deleted_paths_and_handles_directory_mapping(self):
        self.manifest["modules"][0]["source_paths"] = ["src"]
        result, data = self.impact(["src/deleted.py", "src-extra/unrelated.py"])
        self.assertEqual(result.returncode, 0, data)
        self.assertEqual(data["affected_modules"][0]["id"], "export")
        self.assertEqual(data["unmapped_changes"], ["src-extra/unrelated.py"])

    def test_impact_rejects_changed_path_escape(self):
        result, data = self.impact(["../outside.py"])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(data["ok"])

    def test_git_diff_handles_rename_and_invalid_ref(self):
        def run(*args):
            completed = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            return completed.stdout.strip()
        run("init", "-q")
        run("config", "user.name", "Fixture")
        run("config", "user.email", "fixture@example.invalid")
        run("add", ".")
        run("commit", "-qm", "base")
        base = run("rev-parse", "HEAD")
        run("mv", "src/export.py", "src/export renamed.py")
        run("commit", "-qm", "rename")
        result, data = self.run_tool("impact_docs.py", "--base", base, "--head", "HEAD")
        self.assertEqual(result.returncode, 0, data)
        self.assertEqual(data["changed_files"], ["src/export renamed.py", "src/export.py"])
        self.assertEqual(data["affected_modules"][0]["id"], "export")
        result, data = self.run_tool("impact_docs.py", "--base", "no-such-ref", "--head", "HEAD")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(data["ok"])


if __name__ == "__main__":
    unittest.main()
