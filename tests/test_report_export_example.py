"""Exercise the commands and expected results in the public walkthrough."""
import csv
import io
from pathlib import Path
import subprocess
import sys
import unittest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/report-export"


class ReportExportTests(unittest.TestCase):
    def export(self, start, end):
        return subprocess.run([sys.executable, str(EXAMPLE / "export_report.py"), start, end],
                              capture_output=True, text=True)

    def test_both_boundary_dates_are_included(self):
        result = self.export("2026-11-01", "2026-11-02")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(csv.reader(io.StringIO(result.stdout))), [
            ["date", "report_id"], ["2026-11-01", "R-001"], ["2026-11-02", "R-002"]])

    def test_empty_period_keeps_header(self):
        result = self.export("2026-12-01", "2026-12-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["date,report_id"])

    def test_invalid_date_or_range_yields_no_csv(self):
        for start, end in [("2026-11-03", "2026-11-01"), ("2026-02-30", "2026-03-01")]:
            with self.subTest(start=start, end=end):
                result = self.export(start, end)
                self.assertEqual(result.returncode, 2)
                self.assertIn("error:", result.stderr)
                self.assertEqual(result.stdout, "")
