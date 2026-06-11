# chainreserve

**Open crypto market / reserve / seizure intelligence tracker** — part of the
[Cognis Neural Suite](https://cognis.digital).

`chainreserve` aggregates **public, entity-level** crypto-market intelligence
into one queryable surface:

- **Reserves** — centralized-exchange holdings (proof-of-reserves, on-chain labels)
- **Flows** — spot-ETF and public-company treasury holdings / net flows (e.g. IBIT, Strategy)
- **Seizures** — government forfeitures (US Marshals/DOJ, Germany's BKA, UK NCA, ...)
- **Strategic reserves** — sovereign / public strategic BTC reserves (El Salvador, Bhutan, US)
- **Whales** — labeled on-chain clusters (estates, exchange cold-wallet clusters)

It runs as a **CLI** and as a local **MCP server** (stdio JSON-RPC), with
**zero third-party dependencies** — Python standard library only.

> **Scope & ethics.** This tool aggregates **PUBLIC disclosures** (regulatory
> filings, press releases, government notices, official proof-of-reserves
> pages) and **public on-chain entity labels** only. It tracks *entities*
> (exchanges, funds, companies, governments, estates) — **not private
> individuals**. It contains **no private-individual PII** and performs **no
> deanonymization** of private persons. Every record carries a public `source`
> URL so any figure can be traced back to its origin.
>
> Figures in the bundled dataset are illustrative snapshots of public
> disclosures; verify against the cited primary source before relying on them.
> Not investment advice.

## Install

No dependencies. Clone and run, or install the console script:

```bash
pip install -e .            # provides the `chainreserve` command
# or just run it in place:
python -m chainreserve --help
```

## Usage

```bash
# Centralized-exchange reserves (biggest first, with a per-asset rollup):
python -m chainreserve reserves

# ETF + treasury flows as JSON:
python -m chainreserve flows --format json

# Government seizures:
python -m chainreserve seizures

# Sovereign / public strategic reserves:
python -m chainreserve reserves-strategic

# Labeled on-chain whale clusters:
python -m chainreserve whales

# Everything across categories for one entity:
python -m chainreserve entity Binance

# Filter any category by asset:
python -m chainreserve reserves --asset BTC

# List tracked categories:
python -m chainreserve categories
```

Common flags: `--format {table,json}`, `--data PATH` (use your own dataset),
`--asset SYMBOL`, and `--enrich` (best-effort, offline-safe public BTC/USD
price annotation).

### Demo

```bash
python -m chainreserve reserves --data demos/01-basic/sample-entities.json
```

See [`demos/01-basic/SCENARIO.md`](demos/01-basic/SCENARIO.md) for the full
walkthrough and expected output.

## Data sources

`chainreserve` reads an entities dataset, resolved in this order:

1. `--data PATH` (explicit),
2. `CHAINRESERVE_DATA` environment variable,
3. a sibling **cryptoatlas** dataset (`CRYPTOATLAS_DATA`, or the
   `tools/osint/cryptoatlas/data/entities.json` convention),
4. the bundled [`data/entities.json`](data/entities.json).

The dataset is plain JSON with five arrays (`reserves`, `flows`, `seizures`,
`strategic_reserves`, `whales`). Each record needs at least `entity`, `asset`,
and a public `source` URL. Optional public APIs are queried via `urllib` only
when you pass `--enrich`, and failure degrades gracefully — the tool is fully
functional **offline**.

## MCP server

Run as a local MCP server over stdio:

```bash
python -m chainreserve mcp
```

Wire it into Cognis.Studio, Claude Desktop, or Cursor:

```json
{ "command": "python", "args": ["-m", "chainreserve", "mcp"] }
```

Tools exposed: `query_category` and `query_entity`.

## Development

```bash
python -m pytest -q          # or: python -m unittest discover -s tests
```

CI runs the test suite on every push (see `.github/workflows/ci.yml`).

## License

Cognis Open Collaboration License (COCL) 1.0 — see [LICENSE](LICENSE).
Source-available; free for non-commercial use.
