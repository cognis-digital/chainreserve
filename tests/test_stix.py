"""Tests for chainreserve STIX 2.1 bundle export."""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chainreserve.core import records_to_stix, export

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(REPO_ROOT, "demos", "01-basic", "sample-entities.json")

ROWS = [
    {"category": "reserves", "entity": "Binance", "asset": "BTC",
     "kind": "cex", "amount": 582485.0, "unit": "BTC", "as_of": "2026-05-01",
     "jurisdiction": "global",
     "source": "https://www.binance.com/en/proof-of-reserves"},
    {"category": "reserves", "entity": "Binance", "asset": "ETH",
     "kind": "cex", "amount": 4210000.0, "unit": "ETH", "as_of": "2026-05-01",
     "source": "https://www.binance.com/en/proof-of-reserves"},
    {"category": "seizures", "entity": "U.S. DOJ", "asset": "BTC",
     "kind": "government_seizure", "amount": 94636.0, "unit": "BTC",
     "event_date": "2022-02-08", "case": "Bitfinex 2016 hack recovery",
     "source": "https://www.justice.gov/opa/pr/x"},
    # A row with no usable source must still produce a valid SDO (no ext ref).
    {"category": "whales", "entity": "Unlabeled cluster", "asset": "BTC",
     "amount": 100.0, "unit": "BTC", "source": "not-a-url"},
]


class TestStixShape(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(records_to_stix(ROWS))

    def test_bundle_envelope(self):
        self.assertEqual(self.bundle["type"], "bundle")
        self.assertTrue(self.bundle["id"].startswith("bundle--"))

    def test_spec_version_on_every_sdo(self):
        for o in self.bundle["objects"]:
            self.assertEqual(o["spec_version"], "2.1", o)

    def test_one_identity_per_distinct_entity(self):
        idents = [o for o in self.bundle["objects"] if o["type"] == "identity"]
        names = {i["name"] for i in idents}
        # Binance, U.S. DOJ, Unlabeled cluster = 3 distinct entities
        self.assertEqual(len(idents), 3)
        self.assertEqual(names, {"Binance", "U.S. DOJ", "Unlabeled cluster"})

    def test_one_note_per_row(self):
        notes = [o for o in self.bundle["objects"] if o["type"] == "note"]
        self.assertEqual(len(notes), len(ROWS))

    def test_notes_reference_their_identity(self):
        ident_ids = {o["id"] for o in self.bundle["objects"]
                     if o["type"] == "identity"}
        for o in self.bundle["objects"]:
            if o["type"] == "note":
                self.assertEqual(len(o["object_refs"]), 1)
                self.assertIn(o["object_refs"][0], ident_ids)

    def test_public_source_becomes_external_reference(self):
        notes = {o["abstract"]: o for o in self.bundle["objects"]
                 if o["type"] == "note"}
        # A seizure note carries its DOJ public source URL.
        seiz = [o for o in self.bundle["objects"]
                if o["type"] == "note" and "seizures" in o["abstract"]][0]
        self.assertEqual(seiz["external_references"][0]["url"],
                         "https://www.justice.gov/opa/pr/x")

    def test_non_url_source_omits_external_reference(self):
        bad = [o for o in self.bundle["objects"]
               if o["type"] == "note" and "whales" in o["abstract"]][0]
        self.assertNotIn("external_references", bad)

    def test_all_ids_unique(self):
        ids = [o["id"] for o in self.bundle["objects"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_deterministic(self):
        a = records_to_stix(ROWS)
        b = records_to_stix(ROWS)
        self.assertEqual(a, b)


class TestStixExportPath(unittest.TestCase):
    def test_export_stix_from_dataset(self):
        text = export("stix", data_path=DEMO)
        bundle = json.loads(text)
        self.assertEqual(bundle["type"], "bundle")
        self.assertTrue(any(o["type"] == "identity" for o in bundle["objects"]))
        self.assertTrue(any(o["type"] == "note" for o in bundle["objects"]))

    def test_cli_export_stix(self):
        proc = subprocess.run(
            [sys.executable, "-m", "chainreserve", "export",
             "--format", "stix", "--data", DEMO],
            cwd=REPO_ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        bundle = json.loads(proc.stdout)
        self.assertEqual(bundle["type"], "bundle")


if __name__ == "__main__":
    unittest.main()
