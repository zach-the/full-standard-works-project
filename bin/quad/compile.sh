#!/bin/bash
# bin/quad/compile.sh — compile quad-latex.md to quad.pdf via XeLaTeX
#
# Usage:
#   bash bin/quad/compile.sh [input.md] [output.pdf]
# Defaults:
#   in:  out/quad/quad-latex.md
#   out: out/quad/quad.pdf

set -e

INPUT="${1:-out/quad/quad-latex.md}"
OUTPUT="${2:-out/quad/quad.pdf}"

echo "Compiling $INPUT → $OUTPUT"
echo "(running twice for TOC and cross-references)"

# First pass (LaTeX needs two runs for TOC page numbers)
pandoc "$INPUT" \
  -o "$OUTPUT" \
  --pdf-engine=xelatex \
  --pdf-engine-opt="-interaction=nonstopmode" \
  -V mainfont="Noto Serif" \
  -V documentclass=book \
  -V fontsize=11pt \
  -V lang=en \
  -H bin/quad/margin.tex \
  -B bin/quad/toc-include.tex

echo "First pass done. Running second pass for correct TOC page numbers..."

# Second pass
pandoc "$INPUT" \
  -o "$OUTPUT" \
  --pdf-engine=xelatex \
  --pdf-engine-opt="-interaction=nonstopmode" \
  -V mainfont="Noto Serif" \
  -V documentclass=book \
  -V fontsize=11pt \
  -V lang=en \
  -H bin/quad/margin.tex \
  -B bin/quad/toc-include.tex

echo "Done: $OUTPUT"
