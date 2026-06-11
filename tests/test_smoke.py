"""Smoke tests for chainreserve. Standard library only, no network."""

import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chainreserve import TOOL_NAME, TOOL_VERSION, CATEGORIES, query_category
from chainreserve.cli import main

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(REPO_ROOT, "demos", "01-basic", "sample-entities.json")


class TestMetadata(unittest.TestCase):
    def test_metadata(self):
        self.assertEqual(TOOL_NAME, "chainreserve")
        self.assertTrue(TOOL_VERSION)
        self.assertIn("reserves", CATEGORIES)
        self.assertIn("strategic_reserves", CATEGORIES)


class TestEngine(unittest.TestCase):
    def test_bundled_reserves_nonempty(self):
        report = query_category("reserves")
        self.assertGreater(len(report.records), 0)
        # Every record must carry a public http(s) source.
        for r in report.records:
            self.assertTrue(r.source.startswith("http"), r.entity)
        self.assertEqual(report.notes, [], report.notes)

    def test_rollup_sums_amounts(self):
        report = query_category("reserves", asset="BTC")
        roll = list(report.rollup.values())
        self.assertTrue(roll)
        self.assertEqual(roll[0]["asset"], "BTC")
        self.assertGreater(roll[0]["total"], 0.0)

    def test_records_sorted_desc_by_amount(self):
        report = query_category("reserves")
        amounts = [r.amount for r in report.records if r.amount is not None]
        self.assertEqual(amounts, sorted(amounts, reverse=True))


class TestCli(unittest.TestCase):
    def test_version_exit_zero(self):
        proc = subprocess.run(
            [sys.executable, "-m", "chainreserve", "--version"],
            cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(TOOL_VERSION, proc.stdout)

    def test_reserves_json_has_sources(self):
        proc = subprocess.run(
            [sys.executable, "-m", "chainreserve", "reserves",
             "--data", DEMO, "--format", "json"],
            cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertGreater(data["record_count"], 0)
        for rec in data["records"]:
            self.assertTrue(rec["source"].startswith("http"))

    def test_entity_query_table(self):
        self.assertEqual(main(["entity", "Binance"]), 0)

    def test_categories_exit_zero(self):
        self.assertEqual(main(["categories"]), 0)

    def test_no_command_exits_2(self):
        self.assertEqual(main([]), 2)

    def test_missing_data_exits_2(self):
        self.assertEqual(main(["reserves", "--data", "/no/such/file.json"]), 2)


if __name__ == "__main__":
    unittest.main()
