#!/usr/bin/env python3
"""
bin/dc/clean.py — removes D&C outlying text and tags section headers.

Categories handled:
  1. Front matter: everything before first <h1> → strip
  4. Section names (e.g. "Hearts of the Children"): paragraph immediately before
     "Section N" → delete
  2. "Section N" bare refs: → delete
  5. Section headers (long historical prose): everything after "Section N" → wrap
     in <header class="book-intro">

The "Section N" paragraph is used as an anchor point instead of splitting on the
first blank line. This correctly preserves verse content that spans multiple
paragraphs (e.g. D&C 31:13, 135:4).

Usage:
    python3 bin/dc/clean.py [input.md] [output.md]
Defaults:
    in:  out/dc/dc.md
    out: out/dc/dc-step3.md
"""

import re
import sys
from pathlib import Path

BARE_SECTION_REF = re.compile(r'^Section \d+\s*$')


def process_dc_gap(gap):
    """
    Process a full sub→h1 gap for D&C.

    Finds the "Section N" paragraph as an anchor:
      - Everything before the paragraph immediately preceding "Section N"
        is verse content → preserved verbatim
      - The paragraph immediately before "Section N" is the section name → deleted
      - "Section N" itself → deleted
      - Everything after "Section N" → section header → wrapped

    Returns (verse_content_str, processed_outlying_str).
    If no "Section N" is found, returns (gap, '') unchanged.
    """
    paragraphs = re.split(r'(\n[ \t]*\n)', gap)
    # Split preserving delimiters gives alternating [text, sep, text, sep, ...]
    # Easier to work with a simple list of paragraphs with their positions.

    # Re-split without preserving separators, but track positions in the original.
    para_list = []
    pos = 0
    for m in re.finditer(r'[^\n].*?(?:\n(?!\n)|$)', gap, re.DOTALL):
        pass  # too complex

    # Simpler: split on double-newlines, record each paragraph and its start pos.
    raw_paras = list(re.finditer(r'(?:(?!\n\n).)+', gap, re.DOTALL))
    # Even simpler: just split on \n\n+ and track cumulative positions.

    chunks = re.split(r'\n[ \t]*\n', gap)
    # Find index of the Section N chunk
    section_n_idx = None
    for i, chunk in enumerate(chunks):
        if BARE_SECTION_REF.match(chunk.strip()):
            section_n_idx = i
            break

    if section_n_idx is None:
        # No Section N found — no outlying content, return gap unchanged
        return gap, ''

    # Find the last non-empty chunk before Section N — that's the section name
    section_name_idx = None
    for i in range(section_n_idx - 1, -1, -1):
        if chunks[i].strip():
            section_name_idx = i
            break

    # Verse content: everything before section_name_idx
    if section_name_idx is not None:
        verse_chunks = chunks[:section_name_idx]
    else:
        verse_chunks = []

    # Reconstruct verse content preserving original spacing
    verse_content = '\n\n'.join(verse_chunks)

    # Header: everything after Section N
    header_chunks = [c.strip() for c in chunks[section_n_idx + 1:] if c.strip()]

    if not header_chunks:
        return verse_content, ''

    inner = '\n\n'.join(header_chunks)
    return verse_content, f'<header class="book-intro">\n{inner}\n</header>'


def clean(in_path, out_path):
    content = Path(in_path).read_text()

    # 1. Strip front matter
    first_h1 = content.find('<h1>')
    if first_h1 > 0:
        content = content[first_h1:]

    # 2. Collect markers
    markers = []
    for m in re.finditer(r'<sub>\d+</sub>', content):
        markers.append(('sub', m.start(), m.end()))
    for m in re.finditer(r'<h1>.*?</h1>', content):
        markers.append(('h1', m.start(), m.end()))
    markers.sort(key=lambda x: x[1])

    # 3. Walk gaps
    result = []
    prev_end = 0
    prev_mtype = None

    for mtype, start, end in markers:
        gap = content[prev_end:start]

        if prev_mtype == 'sub' and mtype == 'h1':
            verse_content, processed = process_dc_gap(gap)
            result.append(verse_content)
            result.append('\n\n')
            result.append(content[start:end])  # <h1> first
            if processed:
                result.append('\n\n')
                result.append(processed)
            result.append('\n\n')
        else:
            result.append(gap)
            result.append(content[start:end])

        prev_end = end
        prev_mtype = mtype

    result.append(content[prev_end:])
    Path(out_path).write_text(''.join(result))
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    in_path  = sys.argv[1] if len(sys.argv) > 1 else 'out/dc/dc.md'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'out/dc/dc-step3.md'
    clean(in_path, out_path)
