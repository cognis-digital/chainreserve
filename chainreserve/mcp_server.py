"""chainreserve MCP server.

Exposes the public crypto-intelligence tracker as an MCP capability over stdio
using newline-delimited JSON-RPC 2.0. Standard library only — no SDK — so it
runs anywhere Python does and can be wired into Cognis.Studio, Claude Desktop,
or Cursor as a local MCP server:

    {"command": "python", "args": ["-m", "chainreserve", "mcp"]}

Implemented methods:
  * initialize   — handshake, advertises the tools capability
  * tools/list   — describes the query tools
  * tools/call   — runs a tool and returns a report as JSON text

All data served is PUBLIC and entity-level; every record carries a source URL.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, Optional

from chainreserve import TOOL_NAME, TOOL_VERSION
from chainreserve.core import (
    CATEGORIES,
    DataError,
    query_category,
    query_entity,
)

PROTOCOL_VERSION = "2024-11-05"

_TOOLS = [
    {
        "name": "query_category",
        "description": "Query a public crypto-intelligence category "
                       "(reserves, flows, seizures, strategic_reserves, whales). "
                       "Returns entity-level records, each with a public source "
                       "URL, plus a per-asset rollup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": list(CATEGORIES),
                    "description": "Which intelligence category to query.",
                },
                "asset": {
                    "type": "string",
                    "description": "Optional asset symbol filter, e.g. BTC.",
                },
            },
            "required": ["category"],
            "additionalProperties": False,
        },
    },
    {
        "name": "query_entity",
        "description": "Return all public records across categories for one "
                       "named entity (substring match), each with a source URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Entity name or substring, e.g. 'Binance'.",
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
]


def _result(req_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _call_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "query_category":
        category = arguments.get("category")
        if not isinstance(category, str) or not category:
            raise ValueError("`category` (string) is required")
        asset = arguments.get("asset")
        report = query_category(category, asset=asset if isinstance(asset, str) else None)
    elif name == "query_entity":
        ent = arguments.get("name")
        if not isinstance(ent, str) or not ent:
            raise ValueError("`name` (string) is required")
        report = query_entity(ent)
    else:
        raise ValueError(f"unknown tool: {name}")

    payload = report.to_dict()
    return {
        "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
        "isError": False,
    }


def handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Dispatch a single JSON-RPC request. Returns None for notifications."""
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}
    is_notification = "id" not in req

    if method == "initialize":
        res = _result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": TOOL_NAME, "version": TOOL_VERSION},
        })
        return None if is_notification else res

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "ping":
        return None if is_notification else _result(req_id, {})

    if method == "tools/list":
        return _result(req_id, {"tools": _TOOLS})

    if method == "tools/call":
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            return _result(req_id, _call_tool(name, arguments))
        except (ValueError, DataError, OSError) as exc:
            return _error(req_id, -32602, str(exc))
        except Exception as exc:  # pragma: no cover - defensive
            return _error(req_id, -32603, f"internal error: {exc}")

    if is_notification:
        return None
    return _error(req_id, -32601, f"method not found: {method}")


def run_mcp_server(stdin=None, stdout=None) -> None:
    """Read newline-delimited JSON-RPC from stdin, write responses to stdout."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            stdout.write(json.dumps(_error(None, -32700, "parse error")) + "\n")
            stdout.flush()
            continue
        response = handle_request(req)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()


if __name__ == "__main__":
    run_mcp_server()
