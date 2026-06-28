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

<!-- cognis:domains:start -->

<!-- cognis:example:start -->
## 🔎 Example output

Real, reproducible output from the tool — runs offline:

```console
$ chainreserve-emit --version
chainreserve 0.1.0
```

```console
$ chainreserve-emit --help
usage: chainreserve [-h] [--version]
                    {reserves,flows,seizures,reserves-strategic,whales,entity,categories,mcp,feeds,sanctions-screen,export} ...

Open crypto market/reserve/seizure intelligence tracker. PUBLIC, entity-level
data only; every record carries a public source URL.

positional arguments:
  {reserves,flows,seizures,reserves-strategic,whales,entity,categories,mcp,feeds,sanctions-screen,export}
    reserves            Centralized-exchange reserves (proof-of-reserves /
                        labels).
    flows               ETF and public-company treasury holdings / net flows.
    seizures            Government seizures / forfeitures (US Marshals, BKA,
                        NCA...).
    reserves-strategic  Sovereign / public strategic reserves (El Salvador,
                        Bhutan...).
    whales              Labeled on-chain whale clusters (estates, exchange
                        cold wallets).
    entity              All public records across categories for one entity.
    categories          List the tracked intelligence categories.
    mcp                 Run as an MCP server (stdio JSON-RPC).
    feeds               Manage the bundled OFAC SDN data feed
                        (list/update/get).
    sanctions-screen    Cross-reference dataset records against the OFAC SDN
                        list.
    export              Export the whole dataset (json/csv/graphml/stix).

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

> Blocks above are real `chainreserve` output — reproduce them from a clone.

**Sample result format** _(illustrative values — run on your own data for real findings):_

```
{
"findings": [
    {
        "id": "1234567890",
        "title": "Suspicious Network Activity",
        "description": "Anomalous network traffic detected from IP 192.168.1.100",
        "created": "2023-02-15T14:30:00Z"
    },
    {
        "id": "2345678901",
        "title": "Malware Detection",
        "description": "Virus detected on host with IP 10.0.0.1",
        "created": "2023-02-16T12:45:00Z"
    }
]
}
```

<!-- cognis:example:end -->

## Usage — step by step

1. **Install** from source (Python 3.9+; bundles `data/entities.json`):
   ```bash
   pip install .
   ```
2. **List** the tracked intelligence categories:
   ```bash
   chainreserve categories
   ```
3. **Query** exchange reserves, treasury flows, or seizures (filter by asset):
   ```bash
   chainreserve reserves --asset BTC --format json
   ```
4. **Look up** all public records for one entity:
   ```bash
   chainreserve entity Binance --format json
   ```
5. **Export / automate** the whole dataset for downstream pipelines
   (`json` · `csv` · `graphml` · **`stix`** — STIX 2.1 bundle):
   ```bash
   chainreserve export --format csv  --since 2024-01-01 --out reserves.csv
   chainreserve export --format stix                    --out chainreserve.stix.json
   ```
   Other subcommands: `flows`, `seizures`, `reserves-strategic`, `whales`, and `mcp` (MCP stdio server).

## Domains

**Primary domain:** AI & ML  ·  **JTF MERIDIAN division:** ATHENA-PRIME · SAGE

**Topics:** `cognis` `ai` `llm` `machine-learning` `crypto`

Part of the **Cognis Neural Suite** — 300+ source-available tools organized across 12 domains under the JTF MERIDIAN command structure. See the [suite on GitHub](https://github.com/cognis-digital) and [jtf-meridian](https://github.com/cognis-digital/jtf-meridian) for how the pieces fit together.
<!-- cognis:domains:end -->

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

## OFAC sanctions screening (real data feed)

`chainreserve` ships an edge/air-gap-deployable **data-feed ingestion layer**
and uses it to cross-reference your dataset against the U.S. Treasury **OFAC
Specially Designated Nationals (SDN)** list — the authoritative sanctions feed.
This is a real compliance enrichment, not cosmetic: every reserve / flow /
seizure / strategic-reserve / whale record is screened two ways —

- **by on-chain address** — OFAC publishes sanctioned *Digital Currency
  Addresses* in the SDN `Remarks` column; chainreserve extracts the on-chain
  addresses embedded in each record's public `source` URL / `address` field and
  flags exact matches, and
- **by entity name** — sanctioned org/person names are matched (case- and
  whitespace-normalized, exact — no fuzzy false positives) against `entity`.

Each hit carries the SDN entry number, listed name, and program (e.g. `CYBER2`,
`DPRK3`) for analyst triage. Strictly defensive / authorized-use compliance
screening over PUBLIC data.

```bash
# List this repo's relevant feed(s) and cache freshness:
python -m chainreserve feeds list

# Fetch + cache the live OFAC SDN feed (online, keyless):
python -m chainreserve feeds update ofac-sdn

# Re-serve the cached snapshot with NO network (air-gap):
python -m chainreserve feeds get ofac-sdn --offline

# Screen the dataset against the cached SDN list, offline:
python -m chainreserve sanctions-screen --offline
python -m chainreserve sanctions-screen --offline --format json
```

### Edge / air-gap workflow

The ingestion layer (`chainreserve/datafeeds.py` + the bundled catalog
`chainreserve/data_feeds_2026.json`) is **standard-library only**: it fetches
over HTTPS with a UA, caches to disk under `COGNIS_FEEDS_CACHE`
(default `~/.cache/cognis-feeds`), and re-serves **offline** so the tool keeps
working on disconnected / edge gear. For a true air gap, snapshot the cache on a
connected host and sneakernet it across:

```bash
# On a connected host: cache the feed, then bundle the cache.
python -m chainreserve feeds update ofac-sdn
python -m chainreserve.datafeeds snapshot-export ofac.tar.gz

# On the air-gapped host: import the snapshot, then screen offline.
COGNIS_FEEDS_CACHE=/opt/cognis-feeds python -m chainreserve.datafeeds snapshot-import ofac.tar.gz
COGNIS_FEEDS_CACHE=/opt/cognis-feeds python -m chainreserve sanctions-screen --offline
```

Real source (keyless): **U.S. Treasury OFAC SDN list** —
`https://www.treasury.gov/ofac/downloads/sdn.csv`
(consolidated: `https://www.treasury.gov/ofac/downloads/consolidated/cons_prim.csv`).

### Demos

Each demo is a self-contained folder with a dataset **in the real input format**
and a `SCENARIO.md` (where the data came from, the exact run command, what to
expect, and how to act):

| Demo | Use case |
|------|----------|
| [`01-basic`](demos/01-basic/SCENARIO.md) | End-to-end tour across all five categories |
| [`02-etf-flows-monthly`](demos/02-etf-flows-monthly/SCENARIO.md) | Monthly spot-ETF & treasury net-flow desk note (inflows vs. outflows) |
| [`03-government-seizures`](demos/03-government-seizures/SCENARIO.md) | Multi-jurisdiction seizure tracking (DOJ, BKA, NCA) + `--since` filter |
| [`04-sovereign-reserves`](demos/04-sovereign-reserves/SCENARIO.md) | Sovereign strategic-reserve monitor (El Salvador, Bhutan, US) + `--enrich` |
| [`05-exchange-por-audit`](demos/05-exchange-por-audit/SCENARIO.md) | Cross-exchange proof-of-reserves concentration audit |
| [`06-whale-clusters`](demos/06-whale-clusters/SCENARIO.md) | Labeled on-chain whale-cluster watch (estates, cold wallets) |
| [`07-stix-export-soc`](demos/07-stix-export-soc/SCENARIO.md) | STIX 2.1 export into a SOC / threat-intel platform |
| [`08-source-integrity-qa`](demos/08-source-integrity-qa/SCENARIO.md) | Data-quality gate: flag unsourced / non-URL records in CI |
| [`09-ofac-sanctions-screen`](demos/09-ofac-sanctions-screen/SCENARIO.md) | OFAC SDN sanctions screening (by on-chain address + entity name), fully offline |

Quick start:

```bash
python -m chainreserve reserves --data demos/01-basic/sample-entities.json
```

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

## STIX 2.1 export

`chainreserve export --format stix` serializes the dataset as a **STIX 2.1
bundle** so public entity-level intelligence can be ingested by a TIP/SOC or
pushed over TAXII. Each distinct entity becomes an `identity` SDO; each record
becomes a `note` SDO that references its identity, summarizes the
holding/seizure/flow in `content`, tags `labels` (e.g. `["chainreserve",
"seizures", "btc"]`), and pins the public `source` URL as an
`external_references[].url`. Object ids are **deterministic** UUIDv5 values, so
re-exporting the same dataset yields a byte-for-byte identical bundle
(idempotent re-ingest; diff two days to see exactly what changed).

```bash
python -m chainreserve export --format stix --data demos/07-stix-export-soc/feed.json
```

See [`demos/07-stix-export-soc/SCENARIO.md`](demos/07-stix-export-soc/SCENARIO.md)
for a full SOC walkthrough. For platform-specific routing
(MISP/Sigma/Splunk/Slack), pipe the JSON output through `chainreserve-emit`
(see [INTEGRATIONS.md](INTEGRATIONS.md)).

## Development

```bash
python -m pytest -q          # or: python -m unittest discover -s tests
```

CI runs the test suite on every push (see `.github/workflows/ci.yml`).

## Interoperability

`chainreserve` composes with the 300+ tool Cognis suite — JSON in/out and a shared
OpenAI-compatible `/v1` backbone. See **[INTEROP.md](INTEROP.md)** for the
suite map, composition patterns, and reference stacks.

## Integrations

Forward `chainreserve`'s findings to STIX/MISP/Sigma/Splunk/Elastic/Slack/webhooks via
[`cognis-connect`](https://github.com/cognis-digital/cognis-connect). See **[INTEGRATIONS.md](INTEGRATIONS.md)**.

## License

Cognis Open Collaboration License (COCL) 1.0 — see [LICENSE](LICENSE).
Source-available; free for non-commercial use.
