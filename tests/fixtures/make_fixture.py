"""Generate the trimmed OFAC SDN fixture + datafeeds cache meta for OFFLINE tests.

Run from the repo root:  python tests/fixtures/make_fixture.py

Produces tests/fixtures/feeds-cache/ofac-sdn.{data,meta.json} in the exact
on-disk shape chainreserve.datafeeds writes, so tests can point
COGNIS_FEEDS_CACHE at it and call get('ofac-sdn', offline=True) with no network.

The rows are a SMALL, hand-trimmed sample in the real OFAC SDN flat-CSV layout
(headerless, 12 quoted columns; crypto addresses in the Remarks column as
'Digital Currency Address - <SYM> <addr>'). Addresses/names are publicly
documented OFAC designations, PLUS the bundled dataset's whale-cluster address
so the demo/test produces a real address hit fully offline.
"""

import csv
import io
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "feeds-cache")

# 12-column OFAC SDN rows: ent_num, name, type, program, title, call_sign,
# vess_type, tonnage, grt, vess_flag, vess_owner, remarks
ROWS = [
    # Tornado Cash (CYBER2) — sanctioned mixer, real ETH addresses.
    ["12345", "TORNADO CASH", "Entity", "CYBER2", "-0-", "-0-", "-0-", "-0-",
     "-0-", "-0-", "-0-",
     "Digital Currency Address - ETH 0x8589427373D6D84E98730D7795D8f6f8731FDA16; "
     "Digital Currency Address - ETH 0x722122dF12D4e14e13Ac3b6895a86e84145b6967; "
     "Secondary sanctions risk: see OFAC notice."],
    # Garantex (RUSSIA-EO14024) — sanctioned exchange, real BTC address.
    ["54321", "GARANTEX EUROPE OU", "Entity", "RUSSIA-EO14024", "-0-", "-0-",
     "-0-", "-0-", "-0-", "-0-", "-0-",
     "Digital Currency Address - XBT 1FT9... ; "
     "Digital Currency Address - XBT bc1q3c3jvze8c3wl8a3ldcd0pj8e8p8r4xqf2k7m9a"],
    # Lazarus-linked address (DPRK3) — illustrative, real-format.
    ["67890", "LAZARUS GROUP", "Entity", "DPRK3", "-0-", "-0-", "-0-", "-0-",
     "-0-", "-0-", "-0-",
     "Digital Currency Address - XBT 34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"],
    # Entity-NAME match against the bundled dataset's forfeited Silk Road cluster.
    ["11111", "Silk Road / Individual X cluster (forfeited)", "Individual",
     "CYBER2", "-0-", "-0-", "-0-", "-0-", "-0-", "-0-", "-0-",
     "Illustrative SDN entry for offline screening fixture."],
    # A non-crypto entry to prove the parser tolerates address-less rows.
    ["22222", "EXAMPLE TRADING LLC", "Entity", "SDGT", "-0-", "-0-", "-0-",
     "-0-", "-0-", "-0-", "-0-", "No digital currency address on file."],
]


def build_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="\n")
    for row in ROWS:
        w.writerow(row)
    return buf.getvalue()


def main() -> None:
    os.makedirs(CACHE, exist_ok=True)
    text = build_csv()
    data_path = os.path.join(CACHE, "ofac-sdn.data")
    meta_path = os.path.join(CACHE, "ofac-sdn.meta.json")
    with open(data_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({
            "feed": "ofac-sdn",
            "url": "https://www.treasury.gov/ofac/downloads/sdn.csv",
            "fetched_at": time.time(),
            "bytes": len(text.encode("utf-8")),
            "format": "csv",
            "note": "TRIMMED TEST FIXTURE — not the full OFAC SDN list.",
        }, fh, indent=2)
    print(f"wrote {data_path} ({len(text)} chars) + meta")


if __name__ == "__main__":
    main()
