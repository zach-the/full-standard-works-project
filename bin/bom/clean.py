#!/usr/bin/env python3
"""
bin/bom/clean.py — removes BOM outlying text and tags book intros.

Categories handled:
  1. Front matter: everything before first <h1> → strip
  2. Bare chapter refs (e.g. "1 Nephi 2"): short lines ending in a number → delete
  3. Book intro prose (e.g. "The Second Book of Nephi\n\nAn account...") → wrap
     in <header class="book-intro">
  9. Trailing "The End" colophon → strip

False-positive verse content (text spanning a paragraph break that doesn't
match any known pattern) is left untouched.

Usage:
    python3 bin/bom/clean.py [input.md] [output.md]
Defaults:
    in:  out/bom/bom-step2.md
    out: out/bom/bom-step3.md
"""

import re
import sys
from pathlib import Path

# Matches BOM reader's-edition chapter references: "1 Nephi 2", "Jacob 3", etc.
BARE_REF = re.compile(
    r'^(?:\d+ )?(?:Nephi|Jacob|Enos|Jarom|Omni|Words of Mormon|Mosiah|Alma|'
    r'Helaman|Mormon|Ether|Moroni)\s+\d+\s*$'
)

# Verse continuations: a paragraph spanning a paragraph break still reads as
# verse text. These start with "And [pronoun/subject]" — the characteristic
# opening of a BOM verse continuation. Paragraphs matching this are left alone.
VERSE_CONTINUATION = re.compile(
    r'^And (?:they|I|he|she|we|it|ye|him|them)\b', re.IGNORECASE
)


def process_outlying(text):
    """
    Process the trailing outlying portion of a chapter-boundary gap.

    Bare chapter refs are deleted. Paragraphs starting with 'And [pronoun]'
    are left verbatim (they are verse content spanning a paragraph break).
    Everything else is wrapped in <header class="book-intro">.
    """
    paragraphs = re.split(r'\n[ \t]*\n', text)
    intro_paras = []
    verse_paras = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            continue
        if BARE_REF.match(stripped):
            pass  # delete
        elif VERSE_CONTINUATION.match(stripped):
            verse_paras.append(stripped)  # preserve verbatim
        else:
            intro_paras.append(stripped)  # book intro content

    result_parts = []
    if intro_paras:
        inner = '\n\n'.join(intro_paras)
        result_parts.append(f'<header class="book-intro">\n{inner}\n</header>')
    result_parts.extend(verse_paras)

    return '\n\n'.join(result_parts)


def clean(in_path, out_path):
    content = Path(in_path).read_text()

    # 1. Strip front matter (everything before first <h1>)
    first_h1 = content.find('<h1>')
    if first_h1 > 0:
        content = content[first_h1:]

    # 2. Collect all structural markers (sub + h1 only)
    markers = []
    for m in re.finditer(r'<sub>\d+</sub>', content):
        markers.append(('sub', m.start(), m.end()))
    for m in re.finditer(r'<h1>.*?</h1>', content):
        markers.append(('h1', m.start(), m.end()))
    markers.sort(key=lambda x: x[1])

    # 3. Walk gaps, processing only sub→h1 chapter-boundary gaps
    result = []
    prev_end = 0
    prev_mtype = None

    for mtype, start, end in markers:
        gap = content[prev_end:start]

        if prev_mtype == 'sub' and mtype == 'h1':
            # Split on first blank line: verse tail | outlying content
            parts = re.split(r'\n[ \t]*\n', gap, maxsplit=1)
            result.append(parts[0])  # verse tail preserved verbatim

            if len(parts) > 1:
                processed = process_outlying(parts[1])
                if processed:
                    result.append('\n\n')
                    result.append(processed)
                result.append('\n\n')
            else:
                result.append('\n\n')

        elif prev_mtype == 'sub' and mtype == 'sub':
            # Mid-chapter gap: usually just verse text, but may contain a
            # mid-chapter reader's-edition label (e.g. "1 Nephi 6" mid-chapter).
            parts = re.split(r'\n[ \t]*\n', gap, maxsplit=1)
            result.append(parts[0])  # verse text preserved verbatim
            if len(parts) > 1:
                trailing = parts[1].strip()
                if BARE_REF.match(trailing):
                    pass  # delete the bare ref
                elif trailing:
                    result.append('\n\n')
                    result.append(trailing)
                result.append('\n\n')

        else:
            result.append(gap)

        result.append(content[start:end])  # marker verbatim
        prev_end = end
        prev_mtype = mtype

    result.append(content[prev_end:])
    final = ''.join(result)

    # 4. Strip trailing "The End" colophon
    final = re.sub(r'\n+The End\s*$', '\n', final)

    Path(out_path).write_text(final)
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    in_path  = sys.argv[1] if len(sys.argv) > 1 else 'out/bom/bom-step2.md'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'out/bom/bom-step3.md'
    clean(in_path, out_path)
