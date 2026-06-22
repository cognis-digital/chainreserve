"""Command-line interface for chainreserve."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from chainreserve import TOOL_NAME, TOOL_VERSION
from chainreserve.core import (
    CATEGORIES,
    DataError,
    Report,
    enrich_btc_price,
    export,
    query_category,
    query_entity,
)

# Map the user-facing subcommand to the dataset category.
_SUBCOMMAND_CATEGORY = {
    "reserves": "reserves",
    "flows": "flows",
    "seizures": "seizures",
    "reserves-strategic": "strategic_reserves",
    "whales": "whales",
}


def _fmt_amount(record_dict: dict) -> str:
    for key in ("amount", "holdings", "net_flow_usd"):
        val = record_dict.get(key)
        if isinstance(val, (int, float)):
            unit = record_dict.get("unit", "")
            if key == "net_flow_usd":
                return f"{val:,.0f} USD net"
            return f"{val:,.0f} {unit}".strip()
    return "-"


def _render_table(report: Report) -> str:
    lines: List[str] = []
    lines.append(f"{TOOL_NAME} — {report.query}")
    lines.append("=" * 72)
    if not report.records:
        lines.append("No matching public records.")
    else:
        for r in report.records:
            d = r.to_dict()
            lines.append(f"{r.entity}  [{r.asset or '-'}]")
            lines.append(f"        {_fmt_amount(d)}")
            meta = []
            for k in ("kind", "jurisdiction", "as_of", "event_date",
                      "flow_period", "case", "program", "label", "status",
                      "method"):
                if d.get(k):
                    meta.append(f"{k}={d[k]}")
            if meta:
                lines.append("        " + "  ".join(meta))
            lines.append(f"        source: {r.source or '(MISSING)'}")
    lines.append("-" * 72)
    roll = report.rollup
    if roll:
        lines.append("Rollup (sum of amounts by asset):")
        for entry in roll.values():
            lines.append(
                f"        {entry['asset']}: {entry['total']:,.0f} "
                f"{entry['unit']}  (n={entry['count']})")
    lines.append(
        f"records={len(report.records)}  sources={report.source_count}")
    for note in report.notes:
        lines.append(f"note: {note}")
    return "\n".join(lines)


def _emit(report: Report, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(_render_table(report))


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--format", choices=("table", "json"), default="table",
                   help="Output format (default: table).")
    p.add_argument("--data", default=None,
                   help="Path to an entities JSON dataset (overrides defaults).")
    p.add_argument("--asset", default=None,
                   help="Filter by asset symbol (e.g. BTC, ETH).")
    p.add_argument("--enrich", action="store_true",
                   help="Best-effort public BTC/USD price annotation (offline-safe).")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Open crypto market/reserve/seizure intelligence tracker. "
                    "PUBLIC, entity-level data only; every record carries a "
                    "public source URL.",
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    sub = p.add_subparsers(dest="command")

    r = sub.add_parser("reserves",
                       help="Centralized-exchange reserves (proof-of-reserves / labels).")
    _add_common(r)

    f = sub.add_parser("flows",
                       help="ETF and public-company treasury holdings / net flows.")
    _add_common(f)

    s = sub.add_parser("seizures",
                       help="Government seizures / forfeitures (US Marshals, BKA, NCA...).")
    _add_common(s)

    sr = sub.add_parser("reserves-strategic",
                        help="Sovereign / public strategic reserves (El Salvador, Bhutan...).")
    _add_common(sr)

    w = sub.add_parser("whales",
                       help="Labeled on-chain whale clusters (estates, exchange cold wallets).")
    _add_common(w)

    e = sub.add_parser("entity",
                       help="All public records across categories for one entity.")
    e.add_argument("name", help="Entity name or substring (e.g. 'Binance').")
    _add_common(e)

    sub.add_parser("categories", help="List the tracked intelligence categories.")
    sub.add_parser("mcp", help="Run as an MCP server (stdio JSON-RPC).")

    ex = sub.add_parser("export", help="Export the whole dataset (json/csv/graphml/stix).")
    ex.add_argument("--format", choices=("json", "csv", "graphml", "stix"), default="json")
    ex.add_argument("--data", help="Path to an entities dataset JSON.")
    ex.add_argument("--out", help="Write to this file instead of stdout.")
    ex.add_argument("--since", help="Filter time-bearing rows on/after YYYY-MM-DD.")
    return p


def _run_category(args: argparse.Namespace) -> int:
    category = _SUBCOMMAND_CATEGORY[args.command]
    try:
        report = query_category(category, data_path=args.data, asset=args.asset)
    except DataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if getattr(args, "enrich", False):
        enrich_btc_price(report)
    _emit(report, args.format)
    return 0


def _run_entity(args: argparse.Namespace) -> int:
    try:
        report = query_entity(args.name, data_path=args.data)
    except DataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if getattr(args, "enrich", False):
        enrich_btc_price(report)
    _emit(report, args.format)
    return 0


def _run_categories() -> int:
    print(f"{TOOL_NAME} {TOOL_VERSION} — tracked categories")
    print("=" * 72)
    descriptions = {
        "reserves": "Centralized-exchange reserves (proof-of-reserves, on-chain labels).",
        "flows": "ETF and public-company treasury holdings and net flows.",
        "seizures": "Government seizures / forfeitures (US Marshals, BKA, NCA, ...).",
        "strategic_reserves": "Sovereign / public strategic reserves (El Salvador, Bhutan, US).",
        "whales": "Labeled on-chain whale clusters (estates, exchange cold wallets).",
    }
    for cat in CATEGORIES:
        print(f"  {cat:<20} {descriptions.get(cat, '')}")
    print("-" * 72)
    print("PUBLIC, entity-level data only. No private-individual PII.")
    return 0


def _run_export(args: argparse.Namespace) -> int:
    try:
        text = export(args.format, data_path=args.data, out=args.out, since=args.since)
    except (DataError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.out:
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command in _SUBCOMMAND_CATEGORY:
        return _run_category(args)
    if args.command == "export":
        return _run_export(args)
    if args.command == "entity":
        return _run_entity(args)
    if args.command == "categories":
        return _run_categories()
    if args.command == "mcp":
        from chainreserve.mcp_server import run_mcp_server
        run_mcp_server()
        return 0
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
