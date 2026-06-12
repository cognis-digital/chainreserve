"""Tests for chainreserve export (csv / graphml) + --since."""
import unittest
import xml.etree.ElementTree as ET

from chainreserve.core import records_to_csv, records_to_graphml, _row_date

ROWS = [
    {"category": "flows", "entity": "Strategy", "asset": "BTC",
     "source": "https://sec.gov/x", "event_date": "2026-05-01", "amount": 100},
    {"category": "seizures", "entity": "US Marshals", "asset": "BTC",
     "source": "https://justice.gov/y", "event_date": "2026-01-10"},
    {"category": "reserves", "entity": "Binance & Co", "asset": "ETH",
     "source": "https://example.org/z"},
]


class TestCSV(unittest.TestCase):
    def test_header_and_extra_keys(self):
        out = records_to_csv(ROWS)
        head = out.splitlines()[0]
        self.assertTrue(head.startswith("category,entity,asset,source"))
        self.assertIn("event_date", head)
        self.assertIn("amount", head)
        # rows with missing extra keys must not raise and must still render
        self.assertEqual(len(out.strip().splitlines()), 1 + len(ROWS))


class TestGraphML(unittest.TestCase):
    def test_valid_xml_escapes_ampersand(self):
        xml = records_to_graphml(ROWS)
        root = ET.fromstring(xml)  # raises on malformed / unescaped '&'
        ns = "{http://graphml.graphdrawing.org/xmlns}"
        g = root.find(f"{ns}graph")
        nodes = g.findall(f"{ns}node")
        edges = g.findall(f"{ns}edge")
        # 3 entities + 2 distinct assets (BTC, ETH)
        self.assertEqual(len(nodes), 5)
        self.assertEqual(len(edges), 3)


class TestSince(unittest.TestCase):
    def test_row_date_extracts_iso(self):
        self.assertEqual(_row_date(ROWS[0]), "2026-05-01")
        self.assertEqual(_row_date(ROWS[2]), "")  # no date field


if __name__ == "__main__":
    unittest.main()
