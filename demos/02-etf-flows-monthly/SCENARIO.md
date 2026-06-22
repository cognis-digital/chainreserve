# Demo 02 — Monthly spot-ETF & treasury flow tracking

**Situation.** You run a monthly desk note summarizing where institutional BTC/ETH
exposure sits and which vehicles gained or shed coins last month. Sources are
public issuer fact sheets and SEC filings (8-K / 10-Q). Each fund's holdings and
net USD flow for the period are captured as one record.

**Where the data came from.** Public issuer product pages (iShares, Fidelity,
ARK, Grayscale) and EDGAR filings for the treasury holders (Strategy, Tesla).
Every record carries the public `source` URL.

## Run it

```bash
DATA=demos/02-etf-flows-monthly/flows.json

# Net flows, biggest holders first, with a per-asset BTC/ETH rollup:
python -m chainreserve flows --data "$DATA"

# Just the ETH-denominated vehicles:
python -m chainreserve flows --data "$DATA" --asset ETH

# Machine-readable for a dashboard or spreadsheet:
python -m chainreserve flows --data "$DATA" --format json
python -m chainreserve export --data "$DATA" --format csv --out flows-2026-05.csv
```

## What you should see

Records sort by the raw holdings figure, so `ETHE` (≈1,850,000 ETH) sorts to the
top, then the BTC vehicles led by `IBIT` (≈612,000 BTC) and `Strategy`
(≈592,100 BTC). The rollup keeps BTC and ETH on **separate lines** (it sums by
asset+unit), so use the rollup — not raw row order — to compare BTC holders.
Negative `net_flow_usd` (GBTC, ARKB, ETHE) flags **outflows** — the month's
redemptions. The `--asset ETH` filter isolates the lone ETH vehicle.

## How to act

Watch the **sign** of `net_flow_usd`, not just holdings: a fund can hold a large
balance while bleeding shares. A cluster of negative flows across issuers in the
same month is a demand-softening signal; isolated GBTC/ETHE outflows are usually
the long-running rotation out of legacy trusts. Always re-confirm a figure
against its `source` filing before publishing.
