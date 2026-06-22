"""sanctions — OFAC SDN cross-reference enrichment for chainreserve.

Cross-references chainreserve's PUBLIC entity-level crypto records against the
U.S. Treasury OFAC *Specially Designated Nationals* (SDN) list — the
authoritative sanctions feed published at
``https://www.treasury.gov/ofac/downloads/sdn.csv``.

This is a REAL enrichment, not cosmetic: every reserve / flow / seizure /
strategic-reserve / whale record is checked two ways against the SDN list —

  1. by **on-chain address** — OFAC publishes sanctioned *Digital Currency
     Addresses* in the SDN ``Remarks`` column (e.g. ``Digital Currency Address
     - XBT <addr>``); chainreserve extracts the on-chain addresses embedded in
     each record's public ``source`` URL / ``address`` field and flags an exact
     match, and
  2. by **entity name** — sanctioned org/person names are matched
     case-insensitively against the record's ``entity``.

A record that matches gets a ``sanctions`` finding with the SDN entity number,
listed name, program(s) (e.g. ``CYBER2``, ``DPRK3``) and which key matched, so
an analyst can triage exposure. Strictly defensive / authorized-use compliance
screening over PUBLIC data.

The SDN feed is fetched + cached + re-served **offline** through the bundled
:mod:`chainreserve.datafeeds` edge/air-gap layer (feed id ``ofac-sdn``).
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set

# Only this repo's relevant catalog feeds may be wired in.
RELEVANT_FEEDS = ("ofac-sdn",)

# OFAC SDN flat CSV column order (headerless), per the OFAC data spec.
# ent_num, SDN_Name, SDN_Type, Program, Title, Call_Sign, Vess_type,
# Tonnage, GRT, Vess_flag, Vess_owner, Remarks
_COL_ENT_NUM = 0
_COL_NAME = 1
_COL_TYPE = 2
_COL_PROGRAM = 3
_COL_REMARKS = 11

# "Digital Currency Address - XBT 1abc...; Digital Currency Address - ETH 0x..."
_DCA_RE = re.compile(
    r"Digital Currency Address\s*-\s*([A-Za-z0-9]+)\s+([A-Za-z0-9]+)",
    re.IGNORECASE,
)

# On-chain addresses embedded in a record's public blockchain-explorer source
# URL, e.g. .../addresses/btc/<addr> or .../address/<addr> or /tx/.../<addr>.
_EXPLORER_ADDR_RE = re.compile(
    r"/(?:addresses?|account)/(?:btc|eth|[a-z]{2,5}/)?([A-Za-z0-9]{20,})",
    re.IGNORECASE,
)
# A bare BTC/ETH-looking address token (fallback for `address` fields).
_BARE_ADDR_RE = re.compile(r"\b(0x[a-fA-F0-9]{40}|(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{20,60})\b")


@dataclass
class SdnEntry:
    """One sanctioned entity parsed from the OFAC SDN list."""

    ent_num: str
    name: str
    sdn_type: str
    program: str
    addresses: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sdn_ent_num": self.ent_num,
            "sdn_name": self.name,
            "sdn_type": self.sdn_type,
            "program": self.program,
            "addresses": list(self.addresses),
        }


@dataclass
class SanctionsIndex:
    """Searchable index built from the OFAC SDN list."""

    by_address: Dict[str, SdnEntry] = field(default_factory=dict)
    by_name: Dict[str, SdnEntry] = field(default_factory=dict)
    entries: List[SdnEntry] = field(default_factory=list)

    @property
    def address_count(self) -> int:
        return len(self.by_address)

    @property
    def entry_count(self) -> int:
        return len(self.entries)

    def match_address(self, addr: str) -> Optional[SdnEntry]:
        if not addr:
            return None
        return self.by_address.get(addr.strip())

    def match_name(self, entity: str) -> Optional[SdnEntry]:
        if not entity:
            return None
        return self.by_name.get(_norm_name(entity))


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def parse_sdn_csv(text: str) -> SanctionsIndex:
    """Parse the OFAC SDN flat CSV into a :class:`SanctionsIndex`.

    The SDN CSV is headerless and quoted; crypto addresses live in the
    ``Remarks`` column as ``Digital Currency Address - <SYM> <addr>`` clauses.
    """
    idx = SanctionsIndex()
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if len(row) <= _COL_REMARKS:
            continue
        ent_num = (row[_COL_ENT_NUM] or "").strip()
        name = (row[_COL_NAME] or "").strip()
        if not ent_num or ent_num == "-0-" or not name or name == "-0-":
            continue
        sdn_type = (row[_COL_TYPE] or "").strip()
        program = (row[_COL_PROGRAM] or "").strip()
        remarks = row[_COL_REMARKS] or ""
        addrs = [m.group(2).strip() for m in _DCA_RE.finditer(remarks)]
        entry = SdnEntry(ent_num=ent_num, name=name, sdn_type=sdn_type,
                         program=program, addresses=addrs)
        idx.entries.append(entry)
        idx.by_name.setdefault(_norm_name(name), entry)
        for a in addrs:
            idx.by_address.setdefault(a, entry)
    return idx


def load_sanctions_index(*, offline: bool = False,
                         catalog: Optional[dict] = None) -> SanctionsIndex:
    """Load + parse the OFAC SDN feed via the bundled edge ingestion layer.

    ``offline=True`` serves the cached snapshot only and never touches the
    network — the air-gap path. Tests point ``COGNIS_FEEDS_CACHE`` at a trimmed
    fixture and call with ``offline=True`` so nothing hits the wire.
    """
    from chainreserve import datafeeds

    text = datafeeds.get("ofac-sdn", offline=offline, catalog=catalog)
    if isinstance(text, bytes):  # csv format -> str, but be defensive
        text = text.decode("utf-8", "replace")
    return parse_sdn_csv(text)


def extract_addresses(record: Dict[str, Any]) -> Set[str]:
    """Pull candidate on-chain addresses out of a chainreserve record.

    Looks at explicit ``address``/``wallet`` fields and at any
    blockchain-explorer ``source`` URL embedded in the record.
    """
    found: Set[str] = set()
    for key in ("address", "wallet", "addresses"):
        v = record.get(key)
        if isinstance(v, str):
            for m in _BARE_ADDR_RE.finditer(v):
                found.add(m.group(1))
        elif isinstance(v, (list, tuple)):
            for item in v:
                if isinstance(item, str):
                    found.add(item.strip())
    src = record.get("source")
    if isinstance(src, str):
        for m in _EXPLORER_ADDR_RE.finditer(src):
            found.add(m.group(1))
        for m in _BARE_ADDR_RE.finditer(src):
            found.add(m.group(1))
    return {a for a in found if a}


@dataclass
class SanctionsHit:
    """A chainreserve record that matched the OFAC SDN list."""

    entity: str
    category: str
    asset: str
    matched_on: str          # "address" | "entity-name"
    matched_value: str
    sdn: SdnEntry

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity": self.entity,
            "category": self.category,
            "asset": self.asset,
            "matched_on": self.matched_on,
            "matched_value": self.matched_value,
            **self.sdn.to_dict(),
        }


def screen_records(records: Iterable[Dict[str, Any]],
                   index: SanctionsIndex) -> List[SanctionsHit]:
    """Screen chainreserve records against the SDN index.

    Returns one :class:`SanctionsHit` per (record, match-kind). Address matches
    are exact; entity-name matches are case/whitespace-normalized exact matches
    (deliberately conservative — no fuzzy false positives).
    """
    hits: List[SanctionsHit] = []
    for rec in records:
        entity = str(rec.get("entity", "")).strip()
        category = str(rec.get("category", "")).strip()
        asset = str(rec.get("asset", "")).strip()

        for addr in sorted(extract_addresses(rec)):
            entry = index.match_address(addr)
            if entry is not None:
                hits.append(SanctionsHit(entity, category, asset,
                                         "address", addr, entry))

        entry = index.match_name(entity)
        if entry is not None:
            hits.append(SanctionsHit(entity, category, asset,
                                     "entity-name", entity, entry))
    return hits
