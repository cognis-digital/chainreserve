# Demo 07 — STIX 2.1 export into a SOC / threat-intel platform

**Situation.** Your SOC ingests structured intel as **STIX 2.1**. You want
chainreserve's public entity-level records (who holds / seized / reserves what,
with a citable source) to land in your TIP (OpenCTE-style, MISP-via-STIX, or any
TAXII consumer) as first-class objects you can pivot on.

**Where the data came from.** A small mixed feed: a Coinbase reserve disclosure,
a DOJ seizure, and El Salvador's sovereign reserve — each with its public source.

## Run it

```bash
DATA=demos/07-stix-export-soc/feed.json

# Emit a STIX 2.1 bundle (identity + note SDOs) to stdout:
python -m chainreserve export --data "$DATA" --format stix

# Or write it to a file you can upload to your TIP:
python -m chainreserve export --data "$DATA" --format stix --out chainreserve.stix.json
```

Validate the bundle shape with stock Python (no third-party deps):

```bash
python -m chainreserve export --data "$DATA" --format stix \
  | python -c "import sys,json;b=json.load(sys.stdin);\
print(b['type'], len(b['objects']), 'objects');\
print(sorted({o['type'] for o in b['objects']}))"
# -> bundle 6 objects ['identity', 'note']
```

## What you should see

A single STIX `bundle` containing one **`identity`** SDO per distinct entity
(Coinbase, U.S. DOJ, El Salvador) and one **`note`** SDO per record. Each note
`object_refs` its entity's identity, summarizes the holding/seizure in its
`content`, carries `labels` like `["chainreserve","seizures","btc"]`, and pins
the public `source` URL as an `external_references[].url`. All ids are
deterministic UUIDv5 values, so re-exporting the same dataset yields a byte-for-
byte identical bundle (idempotent re-ingest).

## How to act

Upload the bundle to your TIP / push it over TAXII. Pivot on the `identity`
objects to correlate chainreserve intel with other feeds, and use each note's
`external_references` to jump straight to the authoritative public source.
Because the export is **deterministic**, you can diff two days' bundles to see
exactly which records changed. For richer routing (MISP/Sigma/Splunk/Slack), pipe
the JSON output through `chainreserve-emit` (see INTEGRATIONS.md).
