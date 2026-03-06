#!/usr/bin/env bash
# Full annotation pipeline for the Book of Mormon Reader's Edition.
# Produces out/bom/bom.md — source text with inline <sub>N</sub> verse markers
# and <h1>Book Chapter</h1> headings, paragraph structure intact.
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

TXT="$ROOT/in/txt/readers-edition-eng-bofm.txt"
JSON="$ROOT/in/json/book-of-mormon-flat.json"
OUTDIR="$ROOT/out/bom"

mkdir -p "$OUTDIR"

echo "Step 1: inserting verse markers..."
python3 "$ROOT/bin/verse_insert.py" "$TXT" "$JSON" "$OUTDIR/bom-step1"

echo "Step 2: inserting chapter headings..."
python3 "$ROOT/bin/chapter_insertion.py" "$OUTDIR/bom-step1.md" "$JSON" "$OUTDIR/bom-step2.md"

echo "Step 3: verifying alignment..."
python3 "$ROOT/bin/checker.py" "$OUTDIR/bom-step2.md" "$JSON" "$OUTDIR/differences.txt"

# Promote final output
cp "$OUTDIR/bom-step2.md" "$OUTDIR/bom.md"
echo "Done. Final output: $OUTDIR/bom.md"
