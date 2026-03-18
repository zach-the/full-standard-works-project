#!/usr/bin/env python3
"""
bin/pogp/clean.py — removes PoGP outlying text, tags datelines and book intros.

Categories handled:
  1. Front matter: everything before first <h1> → strip
  2. Bare chapter refs ("Moses 2", "Abraham 3"): → delete
  3. Book intro prose ("The Book of Abraham\n\nTranslated from..."): → wrap in
     <header class="book-intro">
  6. Datelines ("(June–October 1830)"): → wrap in <dateline>
  9. "Joseph Smith." colophon at end of file → strip

Usage:
    python3 bin/pogp/clean.py [input.md] [output.md]
Defaults:
    in:  out/pogp/pogp.md
    out: out/pogp/pogp-step3.md
"""

import re
import sys
from pathlib import Path

BARE_REF = re.compile(r'^(?:Moses|Abraham)\s+\d+\s*$')
DATELINE  = re.compile(r'^\([^)]+\)\s*$')


def process_outlying(text):
    """
    Process the trailing outlying portion of a PoGP chapter-boundary gap.
    """
    paragraphs = re.split(r'\n[ \t]*\n', text)
    intro_paras    = []
    dateline_paras = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            continue
        if BARE_REF.match(stripped):
            pass  # delete
        elif DATELINE.match(stripped):
            dateline_paras.append(stripped)
        else:
            intro_paras.append(stripped)

    result_parts = []
    if intro_paras:
        inner = '\n\n'.join(intro_paras)
        result_parts.append(f'<header class="book-intro">\n{inner}\n</header>')
    for dt in dateline_paras:
        result_parts.append(f'<dateline>{dt}</dateline>')

    return '\n\n'.join(result_parts)


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
            parts = re.split(r'\n[ \t]*\n', gap, maxsplit=1)
            result.append(parts[0])
            result.append('\n\n')
            result.append(content[start:end])  # <h1> first

            if len(parts) > 1:
                processed = process_outlying(parts[1])
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
    final = ''.join(result)

    # 4. Strip "Joseph Smith." colophon
    final = re.sub(r'\n+Joseph Smith\.\s*$', '\n', final)

    Path(out_path).write_text(final)
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    in_path  = sys.argv[1] if len(sys.argv) > 1 else 'out/pogp/pogp.md'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'out/pogp/pogp-step3.md'
    clean(in_path, out_path)
