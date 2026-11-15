"""Exercise the offline exporter; these checks do not certify browser rendering."""

from collections import Counter
from html.parser import HTMLParser
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "repo-docs-site"
SCRIPT = SKILL / "scripts" / "build_offline.py"
spec = importlib.util.spec_from_file_location("build_offline", SCRIPT)
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class Document(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.assets = []
        self.steps = []
        self.diagram_nodes = []
        self.hidden_controls = 0
        self.inline_module_scripts = 0

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "script" and attrs.get("src"):
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.assets.append(attrs.get("href"))
        if tag == "script" and attrs.get("type") == "module" and "src" not in attrs:
            self.inline_module_scripts += 1
        if "data-flow-step" in attrs:
            self.steps.append(attrs.get("data-node-id"))
        if tag == "g" and "data-node-id" in attrs:
            self.diagram_nodes.append(attrs["data-node-id"])
        if "data-flow-controls" in attrs and "hidden" in attrs:
            self.hidden_controls += 1


class OfflineExportTests(unittest.TestCase):
    def run_export(self, *arguments):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
                              text=True, capture_output=True)

    def test_export_keeps_complete_static_content_and_inlines_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "summary.html"
            result = self.run_export("--output", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = output.read_text(encoding="utf-8")
            document = Document()
            document.feed(text)
            self.assertEqual(document.assets, [])
            self.assertEqual(len(document.steps), 5)
            self.assertEqual(set(document.steps), set(document.diagram_nodes))
            self.assertFalse([key for key, count in Counter(document.ids).items() if count > 1])
            self.assertEqual(document.hidden_controls, 1)
            self.assertEqual(document.inline_module_scripts, 1)
            self.assertIn("合成示例", text)
            self.assertIn("CSV 生成和下载入口返回均不执行", text)

    def test_existing_output_is_preserved_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "summary.html"
            output.write_text("retain existing content", encoding="utf-8")
            result = self.run_export("--output", output)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "retain existing content")
            result = self.run_export("--output", output, "--force")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("repo-flow-reader", output.read_text(encoding="utf-8"))

    def test_invalid_template_does_not_replace_output(self):
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "broken.html"
            template.write_text("<p>No resource markers</p>", encoding="utf-8")
            output = Path(directory) / "summary.html"
            output.write_text("keep", encoding="utf-8")
            result = self.run_export("--output", output, "--template", template, "--force")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), "keep")

    def test_template_cannot_overwrite_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "source.html"
            content = exporter.STYLE_MARKER + exporter.SCRIPT_MARKER
            template.write_text(content, encoding="utf-8")
            result = self.run_export("--output", template, "--template", template, "--force")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(template.read_text(), content)

    def test_missing_or_duplicate_markers_are_rejected(self):
        for template in (exporter.STYLE_MARKER,
                         exporter.STYLE_MARKER * 2 + exporter.SCRIPT_MARKER):
            with self.subTest(template=template), self.assertRaises(ValueError):
                exporter.render(template, "body{}", "void 0;")

    def test_closing_tags_are_rejected_before_inline(self):
        template = exporter.STYLE_MARKER + exporter.SCRIPT_MARKER
        for style, script in (("</style>", "void 0;"), ("body{}", "</SCRIPT>")):
            with self.subTest(style=style, script=script), self.assertRaises(ValueError):
                exporter.render(template, style, script)


if __name__ == "__main__":
    unittest.main()
