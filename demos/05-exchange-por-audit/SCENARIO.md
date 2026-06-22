# Demo 05 — Cross-exchange proof-of-reserves audit

**Situation.** A risk team compares centralized-exchange reserves side by side to
understand counterparty concentration: where is custodial BTC/ETH concentrated,
and which exchanges back their numbers with an **attestation** versus only
**on-chain wallet labels**.

**Where the data came from.** Public proof-of-reserves pages (Binance, Kraken,
OKX), Coinbase's SEC custodial disclosure, and public Bitfinex wallet labels.
The `method` field records *how* each number is evidenced.

## Run it

```bash
DATA=demos/05-exchange-por-audit/reserves.json

# BTC reserves across exchanges, biggest first, with a BTC total:
python -m chainreserve reserves --data "$DATA" --asset BTC

# ETH side of the book:
python -m chainreserve reserves --data "$DATA" --asset ETH

# One venue across assets:
python -m chainreserve entity Binance --data "$DATA"

# Export the full picture as CSV for a concentration spreadsheet:
python -m chainreserve export --data "$DATA" --format csv --out por-audit.csv
```

## What you should see

For BTC, Coinbase (≈956,000) leads, then Binance (≈582,485), Bitfinex
(≈198,000), Kraken (≈142,000), OKX (≈121,000), and the rollup gives the total
custodial BTC across venues. Each line shows its `method=` so you can tell an
attestation from a label-only estimate. The `entity Binance` query returns both
its BTC and ETH rows.

## How to act

Concentration plus **evidence quality** is the read: a large balance evidenced
only by `public wallet labels (on-chain)` is weaker than one backed by a
`proof-of-reserves attestation`, and an attestation proves assets but not
*liabilities*. Check each `as_of` date for freshness and open the `source` to
confirm the attestation is current before relying on a venue's figure.
