# Demo 09 — OFAC SDN sanctions screening (offline / air-gap)

This scenario cross-references chainreserve's PUBLIC, entity-level crypto
records against the **U.S. Treasury OFAC Specially Designated Nationals (SDN)
list** — the authoritative sanctions feed at
`https://www.treasury.gov/ofac/downloads/sdn.csv`.

It is a real compliance enrichment, not cosmetic. Every reserve / flow /
seizure / strategic-reserve / whale record is screened two ways:

1. **By on-chain address** — OFAC publishes sanctioned *Digital Currency
   Addresses* in the SDN `Remarks` column. chainreserve extracts the on-chain
   addresses embedded in each record's public `source` URL / `address` field and
   flags an exact match.
2. **By entity name** — sanctioned org/person names are matched (case- and
   whitespace-normalized, exact — no fuzzy false positives) against the
   record's `entity`.

The SDN feed is fetched, cached, and re-served **offline** through the bundled
`chainreserve.datafeeds` edge/air-gap layer (catalog feed id `ofac-sdn`).

## Run it (no network required)

```bash
# Standalone demo — uses the committed trimmed SDN fixture, fully offline:
python demos/09-ofac-sanctions-screen/demo.py

# Same thing via the CLI (uses your cached snapshot):
python -m chainreserve sanctions-screen --offline
python -m chainreserve sanctions-screen --offline --format json

# Refresh the cache from the live OFAC feed first (online), then screen offline:
python -m chainreserve feeds update ofac-sdn
python -m chainreserve sanctions-screen --offline
```

## What you should see

Two hits against the bundled dataset:

- An **entity-name** hit on the forfeited *Silk Road / Individual X cluster*.
- An **address** hit on the on-chain address `34xp4v…Twseo` embedded in a
  whale-cluster record's public blockchain-explorer `source` URL.

Each hit carries the matching SDN entry number, listed name, and program (e.g.
`CYBER2`, `DPRK3`) so an analyst can triage exposure.

> The fixture under `tests/fixtures/feeds-cache/` is a small hand-trimmed sample
> in the real OFAC SDN flat-CSV layout — **not** the full list. Run
> `chainreserve feeds update ofac-sdn` to cache the authoritative feed.
