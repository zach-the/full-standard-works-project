#!/usr/bin/env python3
"""
find_outlying_text.py — finds all non-verse, non-heading text in annotated MD files.

"Verse text" is defined as text that immediately follows a <sub>N</sub> marker.
"Outlying text" is anything else that has non-whitespace content.

Two gap categories are reported:
  A) Gaps that follow a non-<sub> marker (h1, <poetry>, </poetry>, or file start).
     These are cleanly non-verse by definition.
  B) Chapter-boundary gaps: text between the last <sub> of a chapter and the next
     <h1>. These contain the final verse's text PLUS any trailing outlying content.
     We split on the first blank line; only the trailing portion (after the verse
     paragraph) is reported.

Usage:
    python3 bin/find_outlying_text.py <input.md> <output.txt>
"""

import re
import sys
from pathlib import Path


def label(mtype, val):
    if mtype == 'h1':
        return f"<h1>{val}</h1>"
    elif mtype == 'sub':
        return f"<sub>{val}</sub>"
    elif mtype == 'poetry_open':
        return "<poetry>"
    elif mtype == 'poetry_close':
        return "</poetry>"
    return "START"


def find_outlying(md_path, output_path):
    content = Path(md_path).read_text()

    # Collect all structural markers with positions
    markers = []
    for m in re.finditer(r'<h1>(.*?)</h1>', content):
        markers.append(('h1', m.start(), m.end(), m.group(1)))
    for m in re.finditer(r'<sub>(\d+)</sub>', content):
        markers.append(('sub', m.start(), m.end(), int(m.group(1))))
    for m in re.finditer(r'<poetry>', content):
        markers.append(('poetry_open', m.start(), m.end(), None))
    for m in re.finditer(r'</poetry>', content):
        markers.append(('poetry_close', m.start(), m.end(), None))
    markers.sort(key=lambda x: x[1])

    results = []
    prev_end = 0
    prev_mtype = 'start'
    prev_lbl = "START"
    current_chapter = None

    for mtype, start, end, val in markers:
        gap = content[prev_end:start]

        if prev_mtype == 'sub' and mtype == 'h1':
            # Chapter-boundary gap: verse text + possible trailing outlying content.
            # Split on first blank line; report only what follows.
            parts = re.split(r'\n[ \t]*\n', gap, maxsplit=1)
            if len(parts) > 1:
                trailing = parts[1].strip()
                if trailing:
                    results.append({
                        'kind': 'chapter_boundary_trailing',
                        'chapter': current_chapter or '(before first chapter)',
                        'after': prev_lbl,
                        'before': label(mtype, val),
                        'text': trailing,
                        'word_count': len(trailing.split()),
                    })

        elif prev_mtype != 'sub':
            # Cleanly non-verse gap
            stripped = gap.strip()
            if stripped:
                results.append({
                    'kind': 'non_verse_gap',
                    'chapter': current_chapter or '(before first chapter)',
                    'after': prev_lbl,
                    'before': label(mtype, val),
                    'text': stripped,
                    'word_count': len(stripped.split()),
                })

        if mtype == 'h1':
            current_chapter = val

        prev_mtype = mtype
        prev_lbl = label(mtype, val)
        prev_end = end

    # Trailing content after the very last marker
    gap = content[prev_end:].strip()
    if gap:
        results.append({
            'kind': 'trailing_end',
            'chapter': current_chapter or '(before first chapter)',
            'after': prev_lbl,
            'before': 'END',
            'text': gap,
            'word_count': len(gap.split()),
        })

    total_words = sum(r['word_count'] for r in results)

    with open(output_path, 'w') as f:
        f.write(f"Outlying text report: {md_path}\n")
        f.write(f"Total outlying blocks: {len(results)}\n")
        f.write(f"Total outlying words:  {total_words}\n")
        f.write("=" * 80 + "\n\n")

        for i, r in enumerate(results, 1):
            preview = r['text']
            if len(preview) > 400:
                preview = preview[:397] + '...'
            f.write(f"[Block {i:4d}]  words={r['word_count']:5d}  kind={r['kind']}\n")
            f.write(f"  Chapter: {r['chapter']}\n")
            f.write(f"  After:   {r['after']}\n")
            f.write(f"  Before:  {r['before']}\n")
            f.write(f"  Text:    {preview}\n")
            f.write("\n")

    return results


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input.md> <output.txt>")
        sys.exit(1)

    results = find_outlying(sys.argv[1], sys.argv[2])
    total_words = sum(r['word_count'] for r in results)
    kind_counts = {}
    for r in results:
        kind_counts[r['kind']] = kind_counts.get(r['kind'], 0) + 1
    print(f"Found {len(results)} outlying blocks ({total_words} words total) → {sys.argv[2]}")
    for k, v in sorted(kind_counts.items()):
        print(f"  {k}: {v}")
