"""Every shipped demo dataset must load, query, and export cleanly.

Guards against a demo file drifting out of the tool's real input format or a
SCENARIO referencing a category that yields nothing.
"""
import glob
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chainreserve import CATEGORIES, load_dataset, all_records
from chainreserve.core import export, _records_from

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMOS_DIR = os.path.join(REPO_ROOT, "demos")


def _demo_datasets():
    return sorted(glob.glob(os.path.join(DEMOS_DIR, "*", "*.json")))


class TestDemos(unittest.TestCase):
    def test_demos_present(self):
        # The repo ships the basic demo plus the use-case demos.
        dirs = [d for d in os.listdir(DEMOS_DIR)
                if os.path.isdir(os.path.join(DEMOS_DIR, d))]
        self.assertGreaterEqual(len(dirs), 8, dirs)

    def test_each_demo_dataset_loads_and_has_records(self):
        for path in _demo_datasets():
            with self.subTest(demo=os.path.relpath(path, REPO_ROOT)):
                data = load_dataset(path)
                recs = all_records(data)
                self.assertTrue(recs, f"no records in {path}")
                # Every category present in the file must be a list of dicts.
                for cat in CATEGORIES:
                    if cat in data:
                        self.assertIsInstance(data[cat], list)
                        # Exercise the parser so malformed rows surface here.
                        _records_from(data, cat)

    def test_each_demo_has_scenario(self):
        for path in _demo_datasets():
            scenario = os.path.join(os.path.dirname(path), "SCENARIO.md")
            self.assertTrue(os.path.isfile(scenario),
                            f"missing SCENARIO.md next to {path}")

    def test_each_demo_exports_every_format(self):
        for path in _demo_datasets():
            for fmt in ("json", "csv", "graphml", "stix"):
                with self.subTest(demo=os.path.basename(path), fmt=fmt):
                    text = export(fmt, data_path=path)
                    self.assertTrue(text.strip(), f"empty {fmt} for {path}")

    def test_clean_demos_have_no_source_notes(self):
        # All demos EXCEPT the deliberately-imperfect QA demo must be clean:
        # every record carries an http(s) source.
        for path in _demo_datasets():
            if "08-source-integrity-qa" in path.replace("\\", "/"):
                continue
            with self.subTest(demo=os.path.relpath(path, REPO_ROOT)):
                for r in all_records(load_dataset(path)):
                    self.assertTrue(
                        r.source.startswith("http"),
                        f"{os.path.basename(path)}: {r.entity} -> {r.source!r}")

    def test_qa_demo_surfaces_notes(self):
        path = os.path.join(DEMOS_DIR, "08-source-integrity-qa", "entities.json")
        from chainreserve import query_category
        report = query_category("reserves", data_path=path)
        self.assertTrue(report.notes, "QA demo should surface data-quality notes")


if __name__ == "__main__":
    unittest.main()
