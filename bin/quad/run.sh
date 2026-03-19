#!/bin/bash
# bin/quad/run.sh — full quad PDF pipeline from step3 files to PDF
#
# Stages:
#   1. tag_books: insert <h2> book markers in each step3 file → step4
#   2. concat:    combine all volumes into quad-raw.md
#   3. convert:   convert tags to LaTeX → quad-latex.md
#   4. compile:   pandoc + xelatex → quad.pdf

set -e
cd "$(dirname "$0")/../.."  # run from project root

echo "=== Stage 1: tag_books ==="
python3 bin/quad/tag_books.py out/ot/ot-step3.md   out/ot/ot-step4.md
python3 bin/quad/tag_books.py out/nt/nt-step3.md   out/nt/nt-step4.md
python3 bin/quad/tag_books.py out/bom/bom-step3.md out/bom/bom-step4.md
python3 bin/quad/tag_books.py out/dc/dc-step3.md   out/dc/dc-step4.md
python3 bin/quad/tag_books.py out/pogp/pogp-step3.md out/pogp/pogp-step4.md

echo ""
echo "=== Stage 1b: epub_stanza (OT + NT) ==="
python3 bin/epub_stanza.py in/epub/engkjvcpb.epub out/ot/ot-step4.md out/ot/ot-step5.md
python3 bin/epub_stanza.py in/epub/engkjvcpb.epub out/nt/nt-step4.md out/nt/nt-step5.md

echo ""
echo "=== Stage 2: concat ==="
python3 bin/quad/concat.py out/quad/quad-raw.md

echo ""
echo "=== Stage 3: convert ==="
python3 bin/quad/convert.py out/quad/quad-raw.md out/quad/quad-latex.md

echo ""
echo "=== Stage 4: compile ==="
bash bin/quad/compile.sh out/quad/quad-latex.md out/quad/quad.pdf

echo ""
echo "Done: out/quad/quad.pdf"
