"""Core engine for chainreserve.

chainreserve aggregates PUBLIC, ENTITY-LEVEL crypto market-intelligence:

  * reserves           — centralized-exchange holdings (proof-of-reserves, labels)
  * flows              — ETF / public-company treasury holdings and net flows
  * seizures           — government forfeitures (US Marshals/DOJ, BKA, NCA, ...)
  * strategic_reserves — sovereign / public-company strategic BTC reserves
  * whales             — labeled on-chain clusters (estates, exchange cold wallets)

Design constraints:
  * PUBLIC, entity-level data only. No private-individual PII; no
    deanonymization of private persons. Every record carries a public
    ``source`` URL.
  * Standard library only. Network access is OPTIONAL and best-effort
    (urllib); everything works fully offline against a bundled dataset.

The dataset is read from, in order of precedence:
  1. an explicit ``--data PATH`` (or ``data_path`` argument),
  2. the ``CHAINRESERVE_DATA`` environment variable,
  3. a sibling ``cryptoatlas`` dataset (``CRYPTOATLAS_DATA`` env or the
     ``tools/osint/cryptoatlas/data/entities.json`` convention), then
  4. the bundled ``data/entities.json`` shipped with this package.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Optional

# Tool identity (re-exported from the package __init__).
TOOL_NAME = "chainreserve"
TOOL_VERSION = "0.1.0"

# The five public-intelligence categories this tool tracks.
CATEGORIES = ("reserves", "flows", "seizures", "strategic_reserves", "whales")

# Fields that, if present in any record, MUST be a public URL. A record
# without a usable source is reported as a data-quality finding rather than
# silently trusted.
_SOURCE_FIELD = "source"

# Network calls are short and best-effort. Offline is a first-class mode.
_HTTP_TIMEOUT = 6.0
_USER_AGENT = f"{TOOL_NAME}/{TOOL_VERSION} (+https://cognis.digital; public-data aggregator)"


class DataError(Exception):
    """Raised when the entities dataset cannot be loaded or is malformed."""


@dataclass
class Record:
    """A single public, entity-level intelligence record."""

    category: str
    entity: str
    asset: str
    source: str
    fields: Dict[str, Any] = field(default_factory=dict)

    @property
    def amount(self) -> Optional[float]:
        for key in ("amount", "holdings", "net_flow_usd"):
            val = self.fields.get(key)
            if isinstance(val, (int, float)):
                return float(val)
        return None

    @property
    def unit(self) -> str:
        return str(self.fields.get("unit", ""))

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "category": self.category,
            "entity": self.entity,
            "asset": self.asset,
            "source": self.source,
        }
        out.update(self.fields)
        return out


@dataclass
class Report:
    """The result of a query: matched records plus a small rollup."""

    query: str
    records: List[Record] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    source_count: int = 0

    @property
    def rollup(self) -> Dict[str, Dict[str, float]]:
        """Sum amounts per (asset, unit) so a report is more than a list."""
        agg: Dict[str, Dict[str, float]] = {}
        for r in self.records:
            amt = r.amount
            if amt is None:
                continue
            unit = r.unit or "?"
            key = f"{r.asset}:{unit}"
            agg.setdefault(key, {"asset": r.asset, "unit": unit, "total": 0.0,
                                 "count": 0})
            agg[key]["total"] += amt
            agg[key]["count"] += 1
        return agg

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": TOOL_NAME,
            "version": TOOL_VERSION,
            "query": self.query,
            "record_count": len(self.records),
            "source_count": self.source_count,
            "rollup": list(self.rollup.values()),
            "records": [r.to_dict() for r in self.records],
            "notes": self.notes,
        }


# --------------------------------------------------------------------------- #
# Dataset loading
# --------------------------------------------------------------------------- #

def _bundled_data_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "data", "entities.json")


def _cryptoatlas_candidate() -> Optional[str]:
    """Locate a sibling cryptoatlas dataset by convention, if present."""
    env = os.environ.get("CRYPTOATLAS_DATA")
    if env and os.path.isfile(env):
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    # .../tools/osint/chainreserve/chainreserve/core.py -> tools/osint
    osint_dir = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    cand = os.path.join(osint_dir, "cryptoatlas", "data", "entities.json")
    return cand if os.path.isfile(cand) else None


def resolve_data_path(data_path: Optional[str] = None) -> str:
    """Resolve which dataset file to load, honoring the documented precedence."""
    if data_path:
        if not os.path.isfile(data_path):
            raise DataError(f"dataset not found: {data_path}")
        return data_path
    env = os.environ.get("CHAINRESERVE_DATA")
    if env:
        if not os.path.isfile(env):
            raise DataError(f"CHAINRESERVE_DATA points to a missing file: {env}")
        return env
    atlas = _cryptoatlas_candidate()
    if atlas:
        return atlas
    bundled = _bundled_data_path()
    if not os.path.isfile(bundled):
        raise DataError(f"bundled dataset missing: {bundled}")
    return bundled


def load_dataset(data_path: Optional[str] = None) -> Dict[str, Any]:
    path = resolve_data_path(data_path)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise DataError(f"invalid JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise DataError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DataError(f"dataset root must be an object: {path}")
    return data


def _records_from(data: Dict[str, Any], category: str) -> List[Record]:
    raw = data.get(category)
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise DataError(f"dataset['{category}'] must be a list")
    records: List[Record] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        entity = str(item.get("entity", "")).strip()
        asset = str(item.get("asset", "")).strip()
        source = str(item.get(_SOURCE_FIELD, "")).strip()
        extra = {k: v for k, v in item.items()
                 if k not in ("entity", "asset", _SOURCE_FIELD)}
        records.append(Record(category=category, entity=entity, asset=asset,
                              source=source, fields=extra))
    return records


def all_records(data: Dict[str, Any]) -> List[Record]:
    out: List[Record] = []
    for cat in CATEGORIES:
        out.extend(_records_from(data, cat))
    return out


# --------------------------------------------------------------------------- #
# Export (csv / graphml) + --since filter
# (serializers drafted by the local fleet, corrected here: the draft's
#  DictWriter threw on extra keys and its GraphML lacked xmlns and used
#  unescaped/colliding node ids — fixed to a namespaced, prefixed graph.)
# --------------------------------------------------------------------------- #

def _row_date(row: Dict[str, Any]) -> str:
    """First YYYY-MM-DD found in a record's time-bearing fields, else ''."""
    for k in ("event_date", "as_of", "flow_period"):
        v = str(row.get(k, "") or "")
        if len(v) >= 10 and v[4] == "-" and v[7] == "-":
            return v[:10]
    return ""


def records_to_csv(rows: List[Dict[str, Any]]) -> str:
    import csv
    import io
    base = ["category", "entity", "asset", "source"]
    extra = sorted({k for r in rows for k in r.keys() if k not in base})
    fields = base + extra
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    return buf.getvalue()


def records_to_graphml(rows: List[Dict[str, Any]]) -> str:
    from xml.sax.saxutils import escape, quoteattr
    ents = set()
    assets = set()
    edges = []
    for r in rows:
        ent = (r.get("entity") or "").strip()
        asset = (r.get("asset") or "").strip()
        if ent:
            ents.add(ent)
        if asset:
            assets.add(asset)
        if ent and asset:
            edges.append((ent, asset, r.get("category") or ""))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
           '  <key id="d0" for="node" attr.name="label" attr.type="string"/>',
           '  <key id="d1" for="node" attr.name="kind" attr.type="string"/>',
           '  <key id="d2" for="edge" attr.name="category" attr.type="string"/>',
           '  <graph edgedefault="directed">']
    for ent in sorted(ents):
        out.append(f"    <node id={quoteattr('ent:' + ent)}>"
                   f'<data key="d0">{escape(ent)}</data>'
                   f'<data key="d1">entity</data></node>')
    for asset in sorted(assets):
        out.append(f"    <node id={quoteattr('asset:' + asset)}>"
                   f'<data key="d0">{escape(asset)}</data>'
                   f'<data key="d1">asset</data></node>')
    for i, (ent, asset, cat) in enumerate(edges):
        out.append(f'    <edge id="e{i}" source={quoteattr("ent:" + ent)} '
                   f"target={quoteattr('asset:' + asset)}>"
                   f'<data key="d2">{escape(cat)}</data></edge>')
    out.append("  </graph>")
    out.append("</graphml>")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# STIX 2.1 export
#
# Each public record becomes an Observed-Data-style STIX 2.1 SDO. We model the
# tracked *entity* as an `identity` SDO and the holding/seizure/flow itself as a
# `note` SDO that references the identity and carries the public `source` URL as
# an `external_reference`. IDs are deterministic UUIDv5 values derived from the
# record content (namespaced under chainreserve) so the same dataset always
# yields the same bundle and nothing is fabricated. Strictly defensive,
# public-data-only intelligence: no indicators of attack, no offensive content.
# --------------------------------------------------------------------------- #

def _stix_uuid5(*parts: str) -> str:
    """Deterministic UUIDv5 from record parts under a fixed chainreserve NS."""
    import uuid
    ns = uuid.uuid5(uuid.NAMESPACE_URL, "https://cognis.digital/chainreserve")
    return str(uuid.uuid5(ns, "|".join(parts)))


def records_to_stix(rows: List[Dict[str, Any]],
                    created: Optional[str] = None) -> str:
    """Serialize rows as a STIX 2.1 bundle (identity + note SDOs).

    Deterministic: identical input -> identical bundle (stable UUIDv5 ids and a
    fixed `created`/`modified` timestamp unless one is supplied). Defensive,
    public-data-only — models *who holds what* with a cited public source, never
    attack indicators.
    """
    ts = created or "2026-01-01T00:00:00.000Z"
    objects: List[Dict[str, Any]] = []
    identity_ids: Dict[str, str] = {}

    for r in rows:
        entity = (r.get("entity") or "").strip()
        if not entity:
            continue
        # One identity SDO per distinct entity.
        if entity not in identity_ids:
            iid = "identity--" + _stix_uuid5("identity", entity)
            identity_ids[entity] = iid
            kind = str(r.get("kind") or "")
            # Map our entity kinds to STIX identity_class where sensible.
            if "government" in kind or "sovereign" in kind:
                identity_class = "class"
                sectors = ["government-national"]
            elif "company" in kind or "etf" in kind or "cex" in kind:
                identity_class = "organization"
                sectors = ["financial-services"]
            else:
                identity_class = "organization"
                sectors = []
            ident: Dict[str, Any] = {
                "type": "identity",
                "spec_version": "2.1",
                "id": iid,
                "created": ts,
                "modified": ts,
                "name": entity,
                "identity_class": identity_class,
            }
            if sectors:
                ident["sectors"] = sectors
            if r.get("jurisdiction"):
                ident["description"] = f"jurisdiction={r['jurisdiction']}"
            objects.append(ident)

        # The holding/flow/seizure record itself -> a note referencing identity.
        amount = None
        for k in ("amount", "holdings", "net_flow_usd"):
            v = r.get(k)
            if isinstance(v, (int, float)):
                amount = (k, v)
                break
        unit = r.get("unit") or r.get("asset") or ""
        cat = r.get("category") or ""
        date = _row_date(r) or ts[:10]
        bits = [f"category={cat}", f"asset={r.get('asset') or '-'}"]
        if amount is not None:
            bits.append(f"{amount[0]}={amount[1]:,.0f} {unit}".strip())
        for k in ("as_of", "event_date", "flow_period", "case", "program",
                  "label", "status", "method"):
            if r.get(k):
                bits.append(f"{k}={r[k]}")
        content = f"{entity} [{r.get('asset') or '-'}] — " + "; ".join(bits)

        nid = "note--" + _stix_uuid5(
            "note", cat, entity, str(r.get("asset") or ""),
            str(amount[1]) if amount else "", date)
        note: Dict[str, Any] = {
            "type": "note",
            "spec_version": "2.1",
            "id": nid,
            "created": ts,
            "modified": ts,
            "abstract": f"chainreserve:{cat}",
            "content": content,
            "object_refs": [identity_ids[entity]],
            "labels": [x for x in ["chainreserve", cat, str(r.get("asset") or "").lower()] if x],
        }
        src = r.get("source")
        if isinstance(src, str) and (src.startswith("http://") or src.startswith("https://")):
            note["external_references"] = [{
                "source_name": "chainreserve-public-source",
                "url": src,
            }]
        objects.append(note)

    bundle = {
        "type": "bundle",
        "id": "bundle--" + _stix_uuid5("bundle", *sorted(identity_ids.values())),
        "objects": objects,
    }
    return json.dumps(bundle, indent=2)


def export(fmt: str, data_path: Optional[str] = None,
           out: Optional[str] = None, since: Optional[str] = None) -> str:
    """Export the dataset as json/csv/graphml/stix; optional --since YYYY-MM-DD
    filter on time-bearing rows (rows without a date are kept)."""
    data = load_dataset(data_path)
    rows = [r.to_dict() for r in all_records(data)]
    if since:
        rows = [r for r in rows if (not _row_date(r)) or _row_date(r) >= since]
    if fmt == "json":
        text = json.dumps({"tool": TOOL_NAME, "version": TOOL_VERSION,
                           "record_count": len(rows), "records": rows}, indent=2)
    elif fmt == "csv":
        text = records_to_csv(rows)
    elif fmt == "graphml":
        text = records_to_graphml(rows)
    elif fmt == "stix":
        text = records_to_stix(rows)
    else:
        raise ValueError(f"unknown export format: {fmt!r}")
    if out:
        with open(out, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    return text


# --------------------------------------------------------------------------- #
# Queries
# --------------------------------------------------------------------------- #

def _validate_sources(records: Iterable[Record]) -> List[str]:
    notes: List[str] = []
    for r in records:
        if not r.source:
            notes.append(f"missing source for {r.category} record: {r.entity}")
        elif not (r.source.startswith("http://") or r.source.startswith("https://")):
            notes.append(f"non-URL source for {r.entity}: {r.source}")
    return notes


def _filter(records: List[Record], asset: Optional[str],
            entity: Optional[str]) -> List[Record]:
    out = records
    if asset:
        a = asset.upper()
        out = [r for r in out if r.asset.upper() == a]
    if entity:
        needle = entity.lower()
        out = [r for r in out if needle in r.entity.lower()]
    return out


def _build_report(query: str, records: List[Record]) -> Report:
    # Highest amounts first; records without an amount sink to the bottom.
    records = sorted(records, key=lambda r: (r.amount is None, -(r.amount or 0.0)))
    notes = _validate_sources(records)
    source_count = len({r.source for r in records if r.source})
    return Report(query=query, records=records, notes=notes,
                  source_count=source_count)


def query_category(category: str, data: Optional[Dict[str, Any]] = None,
                   data_path: Optional[str] = None, asset: Optional[str] = None,
                   entity: Optional[str] = None) -> Report:
    if category not in CATEGORIES:
        raise DataError(f"unknown category: {category} (have: {', '.join(CATEGORIES)})")
    data = data if data is not None else load_dataset(data_path)
    records = _filter(_records_from(data, category), asset, entity)
    return _build_report(category, records)


def query_entity(name: str, data: Optional[Dict[str, Any]] = None,
                 data_path: Optional[str] = None) -> Report:
    if not name or not name.strip():
        raise DataError("entity name is required")
    data = data if data is not None else load_dataset(data_path)
    needle = name.strip().lower()
    matches = [r for r in all_records(data) if needle in r.entity.lower()]
    return _build_report(f"entity:{name}", matches)


# --------------------------------------------------------------------------- #
# Optional, best-effort public API enrichment (graceful offline)
# --------------------------------------------------------------------------- #

def fetch_public_json(url: str, timeout: float = _HTTP_TIMEOUT) -> Optional[Any]:
    """Best-effort GET of a public JSON endpoint. Returns None when offline.

    Never raises on network failure: chainreserve is designed to run fully
    offline against the bundled dataset, so enrichment is strictly additive.
    """
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec - public data
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset, errors="replace")
        return json.loads(body)
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        return None


def enrich_btc_price(report: Report, timeout: float = _HTTP_TIMEOUT) -> Report:
    """Optionally annotate a report with a public BTC spot price (USD).

    Uses Coinbase's public spot endpoint. If unreachable, the report is
    returned unchanged with an explanatory note — offline never fails.
    """
    data = fetch_public_json(
        "https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=timeout)
    if not isinstance(data, dict):
        report.notes.append("price enrichment skipped (offline or unavailable)")
        return report
    try:
        price = float(data["data"]["amount"])
    except (KeyError, TypeError, ValueError):
        report.notes.append("price enrichment skipped (unexpected response)")
        return report
    report.notes.append(
        f"public BTC/USD spot ~{price:,.0f} "
        "(source: https://api.coinbase.com/v2/prices/BTC-USD/spot)")
    return report
