#!/usr/bin/env python3
"""
bin/ot/clean.py — wraps OT Psalm superscriptions in <psalm-superscription>.

Category 7: Text appearing inside a <poetry> block, between <h1>Psalms N</h1>
and <sub>1</sub>, is a KJV psalm title/dedication. Wrap it in the tag.

Non-Psalms chapters with text before <sub>N> inside <poetry> blocks (Category 8)
are untouched — only sections headed by "Psalms N" are processed.

Usage:
    python3 bin/ot/clean.py [input.md] [output.md]
Defaults:
    in:  out/ot/ot.md
    out: out/ot/ot-step3.md
"""

import re
import sys
from pathlib import Path

PSALMS_CHAPTER = re.compile(r'^Psalms \d+$')

# Matches <poetry> tag, then any text (possibly multi-line, not containing
# <sub>) up to the first <sub>1</sub>.
SUPERSCRIPTION_RE = re.compile(
    r'(<poetry>)\n((?:(?!<sub>).)*?)(<sub>1</sub>)',
    re.DOTALL
)


def wrap_superscription(section_text):
    """Add <psalm-superscription> tags around the title, if one is present."""
    def replace_fn(m):
        between = m.group(2).strip()
        if between:
            return f'{m.group(1)}\n<psalm-superscription>{between}</psalm-superscription>\n{m.group(3)}'
        return m.group(0)

    return SUPERSCRIPTION_RE.sub(replace_fn, section_text)


def clean(in_path, out_path):
    content = Path(in_path).read_text()

    # Split on <h1> tags, keeping each tag as a separate element.
    # Odd-indexed parts are <h1>...</h1> tags; even-indexed are inter-heading content.
    parts = re.split(r'(<h1>.*?</h1>)', content)

    result = []
    current_chapter = None

    for part in parts:
        h1_match = re.match(r'<h1>(.*?)</h1>', part)
        if h1_match:
            current_chapter = h1_match.group(1)
            result.append(part)
        elif current_chapter and PSALMS_CHAPTER.match(current_chapter):
            result.append(wrap_superscription(part))
        else:
            result.append(part)

    Path(out_path).write_text(''.join(result))
    print(f"Wrote {out_path}")


if __name__ == '__main__':
    in_path  = sys.argv[1] if len(sys.argv) > 1 else 'out/ot/ot.md'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'out/ot/ot-step3.md'
    clean(in_path, out_path)
