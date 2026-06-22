# Demo 03 — Multi-jurisdiction government seizure tracking

**Situation.** A compliance / market-structure analyst tracks large government
crypto forfeitures because supply held by agencies (US Marshals, BKA, NCA) can
become market-moving when it is auctioned or liquidated. This demo aggregates
several well-publicized seizures across the US, Germany and the UK.

**Where the data came from.** Official DOJ / US Attorney press releases, the
German BKA press page, and the UK NCA news page — all public notices. Names that
appear (e.g. case captions) are already published in those official notices;
the tool tracks the **case / agency**, not private individuals.

## Run it

```bash
DATA=demos/03-government-seizures/seizures.json

# All seizures, largest first, summed by asset:
python -m chainreserve seizures --data "$DATA"

# Everything attributed to the DOJ across cases:
python -m chainreserve entity DOJ --data "$DATA"

# Only seizures recorded on/after 2024 (drops older Silk Road / Bitfinex rows):
python -m chainreserve export --data "$DATA" --format json --since 2024-01-01
```

## What you should see

Records sort by amount: the Bitfinex recovery (≈94,636 BTC) and the Silk Road
"Individual X" forfeiture (≈69,370 BTC) lead, followed by Zhong (≈50,676),
BKA's movie2k case (≈49,857) and the NCA's Qian Zhimin case (≈61,000). The
rollup gives the **total BTC under government control** across these cases. The
`--since 2024-01-01` export keeps only the BKA and NCA rows.

## How to act

Treat agency-held coins as **latent supply**: a `status` flip from `seized` to
`forfeited` to liquidated is the lifecycle to watch, because liquidation is when
coins can reach the market. Cross-reference each `case` against its `source`
notice for the authoritative amount and current disposition before acting.
