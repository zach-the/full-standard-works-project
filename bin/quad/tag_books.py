#!/usr/bin/env python3
"""
bin/quad/tag_books.py — inserts <h2>Book Name</h2> before the first <h1>
of each new book in a volume's step3 file.

Usage:
    python3 bin/quad/tag_books.py <input.md> <output.md>

Example:
    python3 bin/quad/tag_books.py out/ot/ot-step3.md out/ot/ot-step4.md
"""

import re
import sys
from pathlib import Path


def extract_book(h1_text):
    """
    'Genesis 1'           → 'Genesis'
    '1 Nephi 1'           → '1 Nephi'
    'Words of Mormon 1'   → 'Words of Mormon'
    'D&C 138'             → 'D&C'
    'Articles of Faith 1' → 'Articles of Faith'
    """
    tokens = h1_text.strip().split()
    return ' '.join(tokens[:-1])


def tag_books(in_path, out_path):
    content = Path(in_path).read_text()

    result = []
    prev_end = 0
    current_book = None

    for m in re.finditer(r'<h1>(.*?)</h1>', content):
        book = extract_book(m.group(1))
        gap = content[prev_end:m.start()]

        if book != current_book:
            result.append(gap)
            result.append(f'<h2>{book}</h2>\n\n')
            current_book = book
        else:
            result.append(gap)

        result.append(m.group(0))
        prev_end = m.end()

    result.append(content[prev_end:])
    Path(out_path).write_text(''.join(result))
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python3 bin/quad/tag_books.py <input.md> <output.md>')
        sys.exit(1)
    tag_books(sys.argv[1], sys.argv[2])
