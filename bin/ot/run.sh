#!/usr/bin/env bash
# Full annotation pipeline for the Old Testament (KJV Cambridge Paragraph Bible).
# Produces out/ot/ot.md with <h1>Book N</h1> chapter headings and <sub>N</sub> verse markers.
set -e

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

TXT="$ROOT/in/txt/engkjvcpb.txt"
JSON="$ROOT/in/json/old-testament-flat.json"
OUTDIR="$ROOT/out/ot"

mkdir -p "$OUTDIR"

echo "Step 0: extracting OT text..."
python3 "$ROOT/bin/ot/extract.py" "$TXT" "$OUTDIR/ot-extracted.txt"

echo ""
echo "Step 1: annotating (verse markers + chapter headings)..."
python3 "$ROOT/bin/ot/annotate.py" "$OUTDIR/ot-extracted.txt" "$JSON" "$OUTDIR/ot-step1.md"

echo ""
echo "Step 2: verifying alignment (pre-poetry)..."
python3 "$ROOT/bin/checker.py" "$OUTDIR/ot-step1.md" "$JSON" "$OUTDIR/differences.txt"

echo ""
echo "Step 3: wrapping poetry blocks..."
python3 "$ROOT/bin/ot/poetry.py" "$OUTDIR/ot-step1.md" "$OUTDIR/ot-step2.md"

echo ""
echo "Step 4: verifying alignment (post-poetry)..."
python3 "$ROOT/bin/checker.py" "$OUTDIR/ot-step2.md" "$JSON" "$OUTDIR/differences-post-poetry.txt"

# Promote final output
cp "$OUTDIR/ot-step2.md" "$OUTDIR/ot.md"
echo ""
echo "Done. Final output: $OUTDIR/ot.md"

echo ""
echo "Verification counts:"
echo "  <sub> markers: $(grep -c '<sub>' "$OUTDIR/ot.md" || true)"
echo "  <h1>  markers: $(grep -c '<h1>' "$OUTDIR/ot.md" || true)"
echo "  <poetry> tags: $(grep -c '<poetry>' "$OUTDIR/ot.md" || true)"
