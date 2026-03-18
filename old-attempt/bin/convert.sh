#!/usr/bin/env zsh
if [[ -z $1 ]]; then
    echo "usage: <infile.md> <outfile.pdf>"
    exit
fi
if [[ -z $2 ]]; then
    echo "usage: <infile.md> <outfile.pdf>"
    exit
fi
python3 ~/bom-project/bin/unicode_subs.py $1 intermediate.md
echo "generated intermediate file intermediate.md"
echo "generating output file $2"
pandoc intermediate.md -o $2 --pdf-engine=xelatex -V mainfont="Noto Serif"
echo "removing intermediate file intermediate.md"
rm intermediate.md
