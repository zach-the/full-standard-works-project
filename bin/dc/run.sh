#!/usr/bin/env bash
# Full annotation pipeline for the Doctrine and Covenants Reader's Edition.
# Produces out/dc/dc.md
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

TXT="$ROOT/in/txt/readers-edition-eng-dc.txt"
JSON="$ROOT/in/json/doctrine-and-covenants-flat.json"
OUTDIR="$ROOT/out/dc"

mkdir -p "$OUTDIR"

echo "Step 0: reordering sections to match JSON..."
python3 "$ROOT/bin/dc/reorder.py" "$TXT" "$OUTDIR/dc-reordered.txt"

echo "Step 1: inserting verse markers..."
python3 "$ROOT/bin/verse_insert.py" "$OUTDIR/dc-reordered.txt" "$JSON" "$OUTDIR/dc-step1"

echo "Step 2: inserting chapter headings..."
python3 "$ROOT/bin/chapter_insertion.py" "$OUTDIR/dc-step1.md" "$JSON" "$OUTDIR/dc-step2.md"

echo "Step 3: verifying alignment..."
python3 "$ROOT/bin/checker.py" "$OUTDIR/dc-step2.md" "$JSON" "$OUTDIR/differences.txt"

cp "$OUTDIR/dc-step2.md" "$OUTDIR/dc.md"
echo "Done. Final output: $OUTDIR/dc.md"
