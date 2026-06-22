"""OFAC SDN sanctions-screening tests for chainreserve.

Standard library only and STRICTLY OFFLINE: COGNIS_FEEDS_CACHE is pointed at a
trimmed fixture and every feed read uses offline=True, so nothing touches the
network.
"""

import io
import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

FIXTURE_CACHE = os.path.join(REPO_ROOT, "tests", "fixtures", "feeds-cache")

# Point the bundled datafeeds edge layer at the trimmed fixture for ALL tests
# in this module BEFORE importing anything that reads the cache.
os.environ["COGNIS_FEEDS_CACHE"] = FIXTURE_CACHE

from chainreserve.core import all_records, load_dataset  # noqa: E402
from chainreserve.cli import main  # noqa: E402
from chainreserve.sanctions import (  # noqa: E402
    RELEVANT_FEEDS,
    SanctionsIndex,
    extract_addresses,
    load_sanctions_index,
    parse_sdn_csv,
    screen_records,
)


class TestFixturePresent(unittest.TestCase):
    def test_fixture_files_exist(self):
        self.assertTrue(os.path.isfile(os.path.join(FIXTURE_CACHE, "ofac-sdn.data")))
        self.assertTrue(os.path.isfile(os.path.join(FIXTURE_CACHE, "ofac-sdn.meta.json")))


class TestSdnParser(unittest.TestCase):
    def test_parse_extracts_addresses_and_names(self):
        idx = load_sanctions_index(offline=True)
        self.assertIsInstance(idx, SanctionsIndex)
        self.assertGreaterEqual(idx.entry_count, 5)
        self.assertGreaterEqual(idx.address_count, 4)
        # Known fixture address (Tornado Cash ETH) is indexed.
        hit = idx.match_address("0x8589427373D6D84E98730D7795D8f6f8731FDA16")
        self.assertIsNotNone(hit)
        self.assertEqual(hit.name, "TORNADO CASH")
        self.assertEqual(hit.program, "CYBER2")

    def test_name_match_is_normalized(self):
        idx = load_sanctions_index(offline=True)
        # Case/whitespace-insensitive exact match.
        self.assertIsNotNone(idx.match_name("tornado cash"))
        self.assertIsNotNone(idx.match_name("  Tornado   Cash "))
        self.assertIsNone(idx.match_name("Tornado"))  # no fuzzy false positives

    def test_parser_tolerates_addressless_rows(self):
        idx = load_sanctions_index(offline=True)
        e = idx.match_name("EXAMPLE TRADING LLC")
        self.assertIsNotNone(e)
        self.assertEqual(e.addresses, [])

    def test_parse_empty_is_safe(self):
        idx = parse_sdn_csv("")
        self.assertEqual(idx.entry_count, 0)
        self.assertEqual(idx.address_count, 0)


class TestAddressExtraction(unittest.TestCase):
    def test_extracts_from_explorer_source_url(self):
        rec = {"entity": "x", "source":
               "https://www.blockchain.com/explorer/addresses/btc/34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"}
        addrs = extract_addresses(rec)
        self.assertIn("34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo", addrs)

    def test_extracts_eth_from_address_field(self):
        rec = {"entity": "x",
               "address": "0x722122dF12D4e14e13Ac3b6895a86e84145b6967"}
        self.assertIn("0x722122dF12D4e14e13Ac3b6895a86e84145b6967",
                      extract_addresses(rec))

    def test_no_addresses_returns_empty(self):
        self.assertEqual(extract_addresses({"entity": "x", "source": "https://sec.gov/x"}), set())


class TestScreening(unittest.TestCase):
    def setUp(self):
        self.index = load_sanctions_index(offline=True)
        self.rows = [r.to_dict() for r in all_records(load_dataset())]

    def test_bundled_dataset_produces_hits(self):
        hits = screen_records(self.rows, self.index)
        self.assertGreaterEqual(len(hits), 2)
        kinds = {h.matched_on for h in hits}
        self.assertIn("address", kinds)
        self.assertIn("entity-name", kinds)

    def test_address_hit_carries_sdn_metadata(self):
        hits = screen_records(self.rows, self.index)
        addr_hits = [h for h in hits if h.matched_on == "address"]
        self.assertTrue(addr_hits)
        h = addr_hits[0]
        self.assertTrue(h.sdn.ent_num)
        self.assertTrue(h.sdn.program)
        d = h.to_dict()
        self.assertEqual(d["matched_on"], "address")
        self.assertIn("sdn_name", d)

    def test_clean_dataset_has_no_hits(self):
        clean = [{"entity": "Acme Corp", "category": "reserves", "asset": "BTC",
                  "source": "https://example.com/acme"}]
        self.assertEqual(screen_records(clean, self.index), [])


class TestRelevantFeedsRestriction(unittest.TestCase):
    def test_only_ofac_sdn_wired(self):
        self.assertEqual(RELEVANT_FEEDS, ("ofac-sdn",))


class TestCliOffline(unittest.TestCase):
    """Drive the CLI in-process; all reads are offline against the fixture."""

    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv)
        return rc, buf.getvalue()

    def test_feeds_list(self):
        rc, out = self._run(["feeds", "list"])
        self.assertEqual(rc, 0)
        self.assertIn("ofac-sdn", out)

    def test_feeds_get_offline(self):
        rc, out = self._run(["feeds", "get", "ofac-sdn", "--offline"])
        self.assertEqual(rc, 0)
        self.assertIn("TORNADO CASH", out)

    def test_feeds_rejects_unrelated_id(self):
        rc, _ = self._run(["feeds", "get", "cisa-kev", "--offline"])
        self.assertEqual(rc, 2)

    def test_sanctions_screen_table(self):
        rc, out = self._run(["sanctions-screen", "--offline"])
        self.assertEqual(rc, 0)
        self.assertIn("sanctions hits", out.lower())
        self.assertIn("[HIT]", out)

    def test_sanctions_screen_json(self):
        rc, out = self._run(["sanctions-screen", "--offline", "--format", "json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertEqual(payload["feed"], "ofac-sdn")
        self.assertGreaterEqual(payload["hit_count"], 2)
        self.assertEqual(payload["records_screened"],
                         len(all_records(load_dataset())))


class TestCliSubprocessOffline(unittest.TestCase):
    """Out-of-process run to prove no network even with a fresh interpreter."""

    def test_subprocess_sanctions_screen(self):
        env = dict(os.environ)
        env["COGNIS_FEEDS_CACHE"] = FIXTURE_CACHE
        env["PYTHONPATH"] = REPO_ROOT
        proc = subprocess.run(
            [sys.executable, "-m", "chainreserve", "sanctions-screen",
             "--offline", "--format", "json"],
            cwd=REPO_ROOT, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertGreaterEqual(payload["hit_count"], 2)


if __name__ == "__main__":
    unittest.main()
