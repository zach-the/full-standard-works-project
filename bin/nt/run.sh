#!/usr/bin/env bash
# Full annotation pipeline for the New Testament (KJV Cambridge Paragraph Bible).
# Produces out/nt/nt.md with <h1>Book N</h1> chapter headings and <sub>N</sub> verse markers.
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

TXT="$ROOT/in/txt/engkjvcpb.txt"
JSON="$ROOT/in/json/new-testament-flat.json"
OUTDIR="$ROOT/out/nt"

mkdir -p "$OUTDIR"

echo "Step 0: extracting NT text..."
python3 "$ROOT/bin/nt/extract.py" "$TXT" "$OUTDIR/nt-extracted.txt"

echo ""
echo "Step 1: annotating (verse markers + chapter headings)..."
python3 "$ROOT/bin/nt/annotate.py" "$OUTDIR/nt-extracted.txt" "$JSON" "$OUTDIR/nt-step1.md"

echo ""
echo "Step 2: verifying alignment (pre-poetry)..."
python3 "$ROOT/bin/checker.py" "$OUTDIR/nt-step1.md" "$JSON" "$OUTDIR/differences.txt"

echo ""
echo "Step 3: wrapping poetry blocks..."
python3 "$ROOT/bin/ot/poetry.py" "$OUTDIR/nt-step1.md" "$OUTDIR/nt-step2.md"

echo ""
echo "Step 4: verifying alignment (post-poetry)..."
python3 "$ROOT/bin/checker.py" "$OUTDIR/nt-step2.md" "$JSON" "$OUTDIR/differences-post-poetry.txt"

# Promote final output
cp "$OUTDIR/nt-step2.md" "$OUTDIR/nt.md"
echo ""
echo "Done. Final output: $OUTDIR/nt.md"

echo ""
echo "Verification counts:"
echo "  <sub> markers: $(grep -c '<sub>' "$OUTDIR/nt.md" || true)"
echo "  <h1>  markers: $(grep -c '<h1>' "$OUTDIR/nt.md" || true)"
echo "  <poetry> tags: $(grep -c '<poetry>' "$OUTDIR/nt.md" || true)"
