#!/usr/bin/env python3
"""
bin/bom/clean.py — removes BOM outlying text and tags book intros.

Categories handled:
  1. Front matter: testimonies and title page → strip; 1 Nephi intro → keep and tag
  2. Bare chapter refs (e.g. "1 Nephi 2"): short lines ending in a number → delete
  3. Book title lines (e.g. "The Second Book of Nephi"): → delete (handled by \\chapter{})
  4. Book subtitles (e.g. "His Reign and Ministry"): short lines without period → <book-heading>
  5. Book intro prose (summary paragraphs): → <header class="book-intro">
  6. Intro content placed AFTER the <h1> tag (consistent with DC/PoGP ordering)
  9. Trailing "The End" colophon → strip

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

# Book title lines — skip these (the \chapter{} heading handles them)
BOOK_TITLE = re.compile(
    r'^(?:Third|Fourth) Nephi\s*$'
    r'|^(?:The )?(?:First |Second |Third |Fourth |Fifth )?Book of \w.*$'
    r'|^The Words of Mormon\s*$',
    re.IGNORECASE,
)

# Verse continuations: paragraph spanning a blank line that is still verse content.
VERSE_CONTINUATION = re.compile(
    r'^And (?:they|I|he|she|we|it|ye|him|them)\b', re.IGNORECASE
)

# Short subtitle threshold (no trailing period = it's a heading, not a summary)
HEADING_MAX_CHARS = 100


def process_bom_intro(text):
    """
    Process BOM book intro text from a chapter-boundary gap (the portion after
    the first blank line — i.e. after the verse tail).

    - Book title lines → deleted (already in \\chapter{})
    - Bare refs → deleted
    - Short lines without trailing period → <book-heading>
    - Longer paragraphs (summaries) → <header class="book-intro">
    - Paragraphs starting with 'And [pronoun]' → verse content, preserved verbatim
    """
    paragraphs = re.split(r'\n[ \t]*\n', text)
    heading_paras = []
    intro_paras   = []
    verse_paras   = []

    for para in paragraphs:
        stripped = para.strip()
        if not stripped:
            continue
        if BARE_REF.match(stripped):
            pass  # delete
        elif BOOK_TITLE.match(stripped):
            pass  # delete — handled by \chapter{}
        elif VERSE_CONTINUATION.match(stripped):
            verse_paras.append(stripped)
        elif len(stripped) <= HEADING_MAX_CHARS and not stripped.endswith('.'):
            heading_paras.append(stripped)
        else:
            intro_paras.append(stripped)

    result_parts = []
    for h in heading_paras:
        result_parts.append(f'<book-heading>{h}</book-heading>')
    if intro_paras:
        inner = '\n\n'.join(intro_paras)
        result_parts.append(f'<header class="book-intro">\n{inner}\n</header>')
    result_parts.extend(verse_paras)

    return '\n\n'.join(result_parts)


def clean(in_path, out_path):
    content = Path(in_path).read_text()

    # 1. Extract and tag the 1 Nephi intro from the front matter, then strip front matter.
    first_h1 = content.find('<h1>')
    nephi_intro_tagged = ''
    if first_h1 > 0:
        front_matter = content[:first_h1]
        intro_start = front_matter.find('The First Book of Nephi')
        if intro_start > 0:
            intro_text = front_matter[intro_start:].strip()
            nephi_intro_tagged = process_bom_intro(intro_text)
        content = content[first_h1:]

    # If we have 1 Nephi intro, insert it between <h1>1 Nephi 1</h1> and <sub>1</sub>
    if nephi_intro_tagged:
        content = content.replace(
            '<h1>1 Nephi 1</h1>',
            f'<h1>1 Nephi 1</h1>\n\n{nephi_intro_tagged}\n\n',
            1,
        )

    # 2. Collect all structural markers (sub + h1 only)
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
            # Split on first blank line: verse tail | intro content
            parts = re.split(r'\n[ \t]*\n', gap, maxsplit=1)
            result.append(parts[0])   # verse tail verbatim
            result.append('\n\n')
            result.append(content[start:end])  # <h1> first

            if len(parts) > 1:
                processed = process_bom_intro(parts[1])
                if processed:
                    result.append('\n\n')
                    result.append(processed)
            result.append('\n\n')

        elif prev_mtype == 'sub' and mtype == 'sub':
            # Mid-chapter gap: verse text ± a mid-chapter bare ref label
            parts = re.split(r'\n[ \t]*\n', gap, maxsplit=1)
            result.append(parts[0])
            if len(parts) > 1:
                trailing = parts[1].strip()
                if BARE_REF.match(trailing):
                    pass  # delete the bare ref
                elif trailing:
                    result.append('\n\n')
                    result.append(trailing)
            result.append('\n\n')
            result.append(content[start:end])

        else:
            result.append(gap)
            result.append(content[start:end])

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
