"""Wrapper behavior tests. Fake compiler fixtures do NOT validate Mermaid syntax."""

import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/repo-diagrams/scripts/render_diagrams.py"
SPEC = importlib.util.spec_from_file_location("render_diagrams", SCRIPT)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class RenderDiagramsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.source = self.base / "sources"
        self.source.mkdir()
        self.output = self.base / "generated"
        self.compiler = self.base / "fake mmdc"
        self.compiler.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "source=pathlib.Path(sys.argv[sys.argv.index('-i')+1])\n"
            "output=pathlib.Path(sys.argv[sys.argv.index('-o')+1])\n"
            "text=source.read_text()\n"
            "if 'FAIL' in text:\n"
            "    print('fixture compiler failure', file=sys.stderr)\n"
            "    raise SystemExit(3)\n"
            "if 'INVALID_XML' in text:\n"
            "    output.write_text('not svg')\n"
            "else:\n"
            "    output.write_text('<svg xmlns=\"http://www.w3.org/2000/svg\"><title>fixture</title></svg>')\n",
            encoding="utf-8",
        )
        self.compiler.chmod(self.compiler.stat().st_mode | stat.S_IXUSR)

    def tearDown(self):
        self.tmp.cleanup()

    def render(self):
        return renderer.render(str(self.source), str(self.output), str(self.compiler), 5)

    def snapshot(self):
        return {p.relative_to(self.output).as_posix(): p.read_bytes()
                for p in self.output.rglob("*") if p.is_file()}

    def test_nested_paths_and_stale_generated_files(self):
        (self.source / "module").mkdir()
        (self.source / "module/first.mmd").write_text("flowchart TD\n A-->B")
        (self.source / "old.mmd").write_text("flowchart TD\n A-->B")
        self.assertEqual(self.render()["count"], 2)
        self.assertTrue((self.output / "module/first.svg").is_file())
        (self.source / "old.mmd").unlink()
        self.render()
        self.assertFalse((self.output / "old.svg").exists())
        manifest = json.loads((self.output / renderer.MARKER).read_text())
        self.assertEqual(manifest["files"][0]["output"], "module/first.svg")

    def test_failure_preserves_entire_previous_output(self):
        (self.source / "a.mmd").write_text("flowchart TD\n A-->B")
        self.render()
        before = self.snapshot()
        (self.source / "b.mmd").write_text("FAIL")
        with self.assertRaises(renderer.RenderError):
            self.render()
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(list(self.base.glob(".generated.build-*")), [])

    def test_invalid_compiler_output_is_not_published(self):
        (self.source / "a.mmd").write_text("INVALID_XML")
        with self.assertRaises(renderer.RenderError):
            self.render()
        self.assertFalse(self.output.exists())

    def test_unmanaged_output_is_preserved(self):
        (self.source / "a.mmd").write_text("flowchart TD\n A-->B")
        self.output.mkdir()
        note = self.output / "notes.txt"
        note.write_text("keep me")
        with self.assertRaises(renderer.RenderError):
            self.render()
        self.assertEqual(note.read_text(), "keep me")

    def test_manual_file_in_managed_directory_is_preserved(self):
        (self.source / "a.mmd").write_text("flowchart TD\n A-->B")
        self.render()
        (self.output / "manual.txt").write_text("keep")
        with self.assertRaises(renderer.RenderError):
            self.render()
        self.assertEqual((self.output / "manual.txt").read_text(), "keep")

    def test_overlap_is_rejected(self):
        (self.source / "a.mmd").write_text("flowchart TD\n A-->B")
        for output in [self.source, self.source / "nested", self.base]:
            with self.subTest(output=output):
                with self.assertRaises(renderer.RenderError):
                    renderer.render(str(self.source), str(output), str(self.compiler), 5)

    def test_linked_source_is_rejected(self):
        outside = self.base / "outside.mmd"
        outside.write_text("flowchart TD\n A-->B")
        (self.source / "link.mmd").symlink_to(outside)
        with self.assertRaises(renderer.RenderError):
            self.render()

    def test_no_diagrams_is_not_reported_as_success(self):
        with self.assertRaises(renderer.RenderError):
            self.render()


if __name__ == "__main__":
    unittest.main()
