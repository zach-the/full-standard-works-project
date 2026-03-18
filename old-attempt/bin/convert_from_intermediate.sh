#!/usr/bin/env zsh
if [[ -z $1 ]]; then
    echo "usage: <infile.tex> <outfile.pdf>"
    exit
fi
if [[ -z $2 ]]; then
    echo "usage: <infile.tex> <outfile.pdf>"
    exit
fi
pandoc $1 -o $2 \
  --pdf-engine=xelatex \
  -V mainfont="Noto Serif" \
  -V documentclass=book \
  -V fontsize=11pt \
  -H ~/bom-project/bin/margin.tex

