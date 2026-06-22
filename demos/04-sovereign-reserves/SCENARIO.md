# Demo 04 — Sovereign strategic-reserve monitor

**Situation.** A macro / geopolitics desk tracks which states hold BTC at the
sovereign level and roughly how much, because sovereign accumulation (or sales)
is a structural, slow-moving demand signal distinct from ETF flows.

**Where the data came from.** El Salvador's official `bitcoin.gob.sv` dashboard,
Bhutan's Druk Holding & Investments site, and a US strategic-reserve executive
action (figure illustrative, funded from forfeited assets). All public.

## Run it

```bash
DATA=demos/04-sovereign-reserves/strategic.json

# All sovereign reserves, largest first:
python -m chainreserve reserves-strategic --data "$DATA"

# Everything about one state across categories:
python -m chainreserve entity "El Salvador" --data "$DATA"

# JSON for a tracker, with an optional offline-safe BTC/USD price note:
python -m chainreserve reserves-strategic --data "$DATA" --format json --enrich
```

## What you should see

Three sovereign holders sorted by size: the US illustrative reserve
(≈198,000 BTC), Bhutan (≈13,029 BTC) and El Salvador (≈6,089 BTC), with a BTC
rollup total. With `--enrich` and network access the report appends a public
BTC/USD spot note; offline it appends a "skipped" note instead and never fails.

## How to act

Compare each holding's `as_of` date — sovereign disclosures lag, so a stale
`as_of` means the figure may have moved. A rising El Salvador balance is the
canonical "still DCA-ing" tell; the US reserve's `program` note (forfeited-asset
funded) means its size is partly a function of the seizure pipeline in Demo 03.
Verify against each `source` before treating a number as current.
