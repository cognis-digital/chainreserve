# Demo 06 — Labeled on-chain whale-cluster watch

**Situation.** A flow analyst watches a short list of **labeled** large clusters
whose movements precede or explain market events: a government-forfeited cluster,
a bankruptcy-estate trustee's distribution wallets, and an exchange cold-wallet
cluster. The goal is situational awareness of *known* entity-attributed supply.

**Where the data came from.** Public block-explorer address pages
(blockchain.com) and the Mt. Gox trustee site. These are **public on-chain
labels for entities** (an estate, an agency, an exchange) — the tool performs no
deanonymization and tracks no private individuals.

## Run it

```bash
DATA=demos/06-whale-clusters/whales.json

# Labeled clusters, largest first, with a BTC total:
python -m chainreserve whales --data "$DATA"

# JSON (each record's source is the explorer/official URL for the label):
python -m chainreserve whales --data "$DATA" --format json

# Pull a single estate across the dataset:
python -m chainreserve entity "Mt. Gox" --data "$DATA"
```

## What you should see

Three clusters sorted by size: the Binance cold-wallet cluster (≈248,597 BTC),
the Mt. Gox estate (≈135,000 BTC), and the forfeited Silk Road cluster
(≈69,370 BTC), with a BTC rollup. Each record's `source` links to the explorer
address (or official trustee page) backing the label.

## How to act

Movement out of a **trustee** cluster (Mt. Gox) is potential creditor
distribution = sell pressure; movement out of a **forfeited** cluster maps to the
seizure-disposition lifecycle in Demo 03; exchange cold-wallet rebalancing is
usually benign. Always re-verify the current balance on the linked explorer —
labels are durable but balances change block by block.
