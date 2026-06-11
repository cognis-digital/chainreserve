# Demo 01 — Public crypto-reserve intelligence report

This scenario runs `chainreserve` against `sample-entities.json`, a small
curated set of **public, entity-level** disclosures and on-chain labels:
exchange proof-of-reserves, ETF/treasury holdings, government seizures,
sovereign strategic reserves, and labeled whale clusters.

Every record carries a public `source` URL. No private-individual PII is
involved — only published entity-level figures.

## Run it

```bash
DATA=demos/01-basic/sample-entities.json

# Centralized-exchange reserves, biggest first, with a per-asset rollup:
python -m chainreserve reserves --data "$DATA"

# ETF + public-company treasury flows as machine-readable JSON:
python -m chainreserve flows --data "$DATA" --format json

# Government seizures (US Marshals/DOJ, BKA, ...):
python -m chainreserve seizures --data "$DATA"

# Sovereign strategic reserves (El Salvador, Bhutan, ...):
python -m chainreserve reserves-strategic --data "$DATA"

# Labeled on-chain whale clusters:
python -m chainreserve whales --data "$DATA"

# Everything known about one entity, across categories:
python -m chainreserve entity Binance --data "$DATA"

# Optional, offline-safe public BTC/USD price annotation:
python -m chainreserve reserves --data "$DATA" --enrich
```

## What you should see

`reserves` lists Coinbase (≈956,000 BTC) and Binance (≈582,485 BTC), sorted by
amount, then a rollup summing the BTC across exchanges and a `sources=` count.
`flows` shows IBIT and Strategy treasury holdings with net USD flows. Each line
ends with a real public `source:` URL, and the JSON output exposes the same
`source` field per record plus a top-level `rollup`.

The tool runs fully offline against the bundled dataset; `--enrich` is the only
path that touches the network and it degrades gracefully to a note when offline.
