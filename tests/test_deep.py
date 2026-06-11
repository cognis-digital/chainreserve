"""Deeper tests for chainreserve: data integrity, queries, MCP, offline."""

import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chainreserve import (
    CATEGORIES,
    DataError,
    all_records,
    load_dataset,
    query_category,
    query_entity,
    resolve_data_path,
)
from chainreserve.core import enrich_btc_price, fetch_public_json
from chainreserve.mcp_server import handle_request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDatasetIntegrity(unittest.TestCase):
    def test_every_record_has_public_source(self):
        data = load_dataset()
        recs = all_records(data)
        self.assertGreaterEqual(len(recs), 10)
        for r in recs:
            self.assertTrue(r.source, f"missing source: {r.category}/{r.entity}")
            self.assertTrue(r.source.startswith("https://")
                            or r.source.startswith("http://"),
                            f"non-URL source: {r.source}")

    def test_all_categories_present(self):
        data = load_dataset()
        for cat in CATEGORIES:
            self.assertIn(cat, data, cat)
            self.assertIsInstance(data[cat], list)

    def test_no_obvious_pii_keys(self):
        # Entity-level only: reject private-person PII fields if they ever creep in.
        banned = {"ssn", "email", "phone", "home_address", "passport", "dob"}
        data = load_dataset()
        for r in all_records(data):
            keys = {k.lower() for k in r.fields}
            self.assertTrue(banned.isdisjoint(keys),
                            f"PII-looking field on {r.entity}: {keys & banned}")


class TestQueries(unittest.TestCase):
    def test_asset_filter(self):
        report = query_category("reserves", asset="btc")
        self.assertTrue(all(r.asset.upper() == "BTC" for r in report.records))

    def test_unknown_category_raises(self):
        with self.assertRaises(DataError):
            query_category("nonexistent")

    def test_entity_substring(self):
        report = query_entity("Strategy")
        self.assertTrue(report.records)
        self.assertTrue(any("Strategy" in r.entity for r in report.records))

    def test_entity_empty_raises(self):
        with self.assertRaises(DataError):
            query_entity("   ")

    def test_report_to_dict_shape(self):
        d = query_category("seizures").to_dict()
        for key in ("tool", "version", "query", "record_count",
                    "source_count", "rollup", "records", "notes"):
            self.assertIn(key, d)


class TestDataPathResolution(unittest.TestCase):
    def test_env_override(self):
        path = os.path.join(REPO_ROOT, "demos", "01-basic", "sample-entities.json")
        old = os.environ.get("CHAINRESERVE_DATA")
        try:
            os.environ["CHAINRESERVE_DATA"] = path
            self.assertEqual(resolve_data_path(), path)
        finally:
            if old is None:
                os.environ.pop("CHAINRESERVE_DATA", None)
            else:
                os.environ["CHAINRESERVE_DATA"] = old

    def test_missing_explicit_path_raises(self):
        with self.assertRaises(DataError):
            load_dataset("/definitely/not/here.json")

    def test_malformed_json_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("{not valid json")
            with self.assertRaises(DataError):
                load_dataset(bad)


class TestMcp(unittest.TestCase):
    def test_initialize(self):
        resp = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(resp["result"]["serverInfo"]["name"], "chainreserve")

    def test_tools_list(self):
        resp = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertEqual(names, {"query_category", "query_entity"})

    def test_tools_call_query_category(self):
        resp = handle_request({
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "query_category",
                       "arguments": {"category": "whales"}},
        })
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertGreater(payload["record_count"], 0)
        self.assertFalse(resp["result"]["isError"])

    def test_tools_call_bad_args(self):
        resp = handle_request({
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "query_category", "arguments": {}},
        })
        self.assertIn("error", resp)

    def test_notification_returns_none(self):
        self.assertIsNone(handle_request({"method": "notifications/initialized"}))


class TestOfflineEnrichment(unittest.TestCase):
    def test_fetch_bad_url_returns_none(self):
        # Unroutable / invalid host: must not raise, must return None.
        result = fetch_public_json("http://localhost:1/nope", timeout=0.5)
        self.assertIsNone(result)

    def test_enrich_offline_adds_note_not_crash(self):
        report = query_category("reserves")
        before = len(report.records)
        enrich_btc_price(report, timeout=0.5)
        # Records unchanged; a note is appended whether online or offline.
        self.assertEqual(len(report.records), before)
        self.assertTrue(report.notes)


if __name__ == "__main__":
    unittest.main()
