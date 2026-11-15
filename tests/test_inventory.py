import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/repo-docs/scripts/inventory.py"
spec = importlib.util.spec_from_file_location("inventory", SCRIPT)
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class InventoryTests(unittest.TestCase):
    def test_git_ignores_generated_and_never_reads_secret_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            (root / ".gitignore").write_text("ignored/\n")
            (root / "main.py").write_text("TOP_SECRET_DO_NOT_COPY = 'confidential'\n")
            (root / "ignored").mkdir()
            (root / "ignored/private.py").write_text("secret")
            (root / "node_modules").mkdir()
            (root / "node_modules/a.js").write_text("vendor")
            report = inventory.collect(root)
            self.assertEqual(report["entrypoint_candidates"], ["main.py"])
            self.assertNotIn("ignored/private.py", report["files"])
            self.assertNotIn("node_modules/a.js", report["files"])
            self.assertNotIn("TOP_SECRET_DO_NOT_COPY", json.dumps(report))
            self.assertEqual(report["snapshot"]["worktree"], "dirty")
            self.assertIn("main.py", report["snapshot"]["changes"])

    def test_symlink_outside_scope_and_truncation(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            (root / "a.py").write_text("a")
            (root / "b.py").write_text("b")
            secret = Path(outside) / "private.py"
            secret.write_text("secret")
            (root / "external.py").symlink_to(secret)
            report = inventory.collect(root, 1)
            self.assertTrue(report["limits"]["truncated"])
            self.assertEqual(report["limits"]["eligible_file_count"], 2)
            self.assertEqual(report["omitted_counts"]["symlink-outside-repo-or-unresolvable"], 1)

    def test_remote_credentials_are_removed(self):
        self.assertEqual(inventory.clean_remote("https://user:password@example.com/owner/repo.git?token=secret#fragment"), "https://example.com/owner/repo.git")
        self.assertEqual(inventory.clean_remote("git@example.com:owner/repo.git"), "example.com:owner/repo.git")

    def test_existing_unrelated_file_is_preserved_and_owned_report_updates(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "report.json"
            target.write_text('{"project":"preserve"}')
            with self.assertRaises(ValueError):
                inventory.write_output(target, {"tool": inventory.TOOL})
            self.assertEqual(json.loads(target.read_text())["project"], "preserve")
            target.unlink()
            inventory.write_output(target, {"tool": inventory.TOOL, "version": 1})
            inventory.write_output(target, {"tool": inventory.TOOL, "version": 2})
            self.assertEqual(json.loads(target.read_text())["version"], 2)


if __name__ == "__main__":
    unittest.main()
