#!/usr/bin/env bash
# Full annotation pipeline for the Pearl of Great Price Reader's Edition.
# Produces out/pogp/pogp.md
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

TXT="$ROOT/in/txt/readers-edition-eng-pgp.txt"
JSON="$ROOT/in/json/pearl-of-great-price-flat.json"
OUTDIR="$ROOT/out/pogp"

mkdir -p "$OUTDIR"

echo "Step 1: inserting verse markers..."
python3 "$ROOT/bin/verse_insert.py" "$TXT" "$JSON" "$OUTDIR/pogp-step1"

echo "Step 2: inserting chapter headings..."
python3 "$ROOT/bin/chapter_insertion.py" "$OUTDIR/pogp-step1.md" "$JSON" "$OUTDIR/pogp-step2.md"

echo "Step 3: verifying alignment..."
python3 "$ROOT/bin/checker.py" "$OUTDIR/pogp-step2.md" "$JSON" "$OUTDIR/differences.txt"

cp "$OUTDIR/pogp-step2.md" "$OUTDIR/pogp.md"
echo "Done. Final output: $OUTDIR/pogp.md"
