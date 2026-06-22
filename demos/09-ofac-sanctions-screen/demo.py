#!/usr/bin/env python3
"""Demo 09 — OFAC SDN sanctions screening, fully OFFLINE.

Cross-references chainreserve's bundled PUBLIC dataset against the U.S. Treasury
OFAC SDN list using the bundled edge/air-gap datafeeds layer. Runs with NO
network: it points COGNIS_FEEDS_CACHE at the committed trimmed SDN fixture and
serves it with offline=True.

Run from the repo root:
    python demos/09-ofac-sanctions-screen/demo.py
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

# Use the committed trimmed OFAC SDN fixture so the demo runs offline.
os.environ.setdefault(
    "COGNIS_FEEDS_CACHE",
    os.path.join(REPO_ROOT, "tests", "fixtures", "feeds-cache"),
)

from chainreserve.core import all_records, load_dataset
from chainreserve.sanctions import load_sanctions_index, screen_records


def main() -> int:
    index = load_sanctions_index(offline=True)   # air-gap: cache only
    rows = [r.to_dict() for r in all_records(load_dataset())]
    hits = screen_records(rows, index)

    print("chainreserve — OFAC SDN sanctions screen (offline demo)")
    print("=" * 72)
    print(f"OFAC SDN entries indexed : {index.entry_count} "
          f"(crypto addresses: {index.address_count})")
    print(f"chainreserve records     : {len(rows)}")
    print(f"sanctions hits           : {len(hits)}")
    print("-" * 72)
    for h in hits:
        print(f"[HIT] {h.entity}  [{h.asset or '-'}]  ({h.category})")
        print(f"      matched on {h.matched_on}: {h.matched_value}")
        print(f"      SDN #{h.sdn.ent_num}  {h.sdn.name}  "
              f"program={h.sdn.program}")
    if not hits:
        print("No records matched the OFAC SDN list.")
    print("-" * 72)
    print("Source: U.S. Treasury OFAC SDN list (sdn.csv), served offline from a")
    print("cached snapshot via the bundled datafeeds edge/air-gap layer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
