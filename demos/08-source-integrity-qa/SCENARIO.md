# Demo 08 — Source-integrity QA (catching unsourced records)

**Situation.** chainreserve's core promise is that **every figure is traceable
to a public source**. Before you publish a report or ingest a third-party
dataset, you want to flag any record that is missing a source or carries a
non-URL placeholder — so a number never gets trusted silently.

**Where the data came from.** This dataset is **deliberately imperfect**: one
well-sourced Coinbase row, one row with an empty `source`, and one row whose
`source` is free text ("see internal wiki page 42") rather than a URL.

## Run it

```bash
DATA=demos/08-source-integrity-qa/entities.json

# Table view — note the per-record source line and the trailing `note:` lines:
python -m chainreserve reserves --data "$DATA"

# JSON — inspect the top-level "notes" array programmatically:
python -m chainreserve reserves --data "$DATA" --format json
```

A quick CI-style gate that fails when any record is missing a clean source:

```bash
python -m chainreserve reserves --data "$DATA" --format json \
  | python -c "import sys,json;n=json.load(sys.stdin)['notes'];\
print('\n'.join(n));\
sys.exit(1 if n else 0)"
# prints the data-quality notes and exits non-zero
```

## What you should see

The table prints all three records (Coinbase shows a real `source:` URL; the
other two show `source: (MISSING)` or the raw placeholder), and below the
separator chainreserve appends data-quality **notes**:

```
note: missing source for reserves record: ExampleExchange (unverified)
note: non-URL source for PlaceholderVenue (bad-source): see internal wiki page 42
```

The JSON output exposes the same strings in its top-level `notes` array.

## How to act

Treat a non-empty `notes` array as a **blocking finding** in a pipeline: either
backfill the public `source` URL for the flagged entity or drop the record
before publishing. Wire the snippet above into CI so an unsourced figure can
never reach a report. A clean dataset (e.g. `demos/01-basic`) returns
`notes: []`.
