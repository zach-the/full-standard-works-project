#!/usr/bin/env python3
"""
bin/quad/concat.py — concatenates all volume step4 files into quad-raw.md.

Volume order: OT → NT → BOM (with front matter) → D&C → PoGP

Each volume is preceded by 2 blank sheets (4 pages) and a full-spread title
page (blank verso + centered-title recto).  The entire document ends with
3 blank sheets (6 pages).

Usage:
    python3 bin/quad/concat.py [output.md]
Defaults:
    out: out/quad/quad-raw.md
"""

import sys
from pathlib import Path

FRONTMATTER = Path('bin/quad/bom-frontmatter.md')

VOLUMES = [
    ('ot',   'out/ot/ot-step5.md',   'The Old Testament'),
    ('nt',   'out/nt/nt-step5.md',   'The New Testament'),
    ('bom',  'out/bom/bom-step4.md', 'The Book of Mormon'),
    ('dc',   'out/dc/dc-step4.md',   'The Doctrine and Covenants'),
    ('pogp', 'out/pogp/pogp-step4.md', 'The Pearl of Great Price'),
]

# One blank page (empty, no header/footer)
BLANK_PAGE = '\\null\\thispagestyle{empty}\\newpage\n'

# 4 blank pages = 2 blank sheets
BLANK_TWO_SHEETS = BLANK_PAGE * 4

# 6 blank pages = 3 blank sheets
BLANK_THREE_SHEETS = BLANK_PAGE * 6


def latex_block(content):
    """Wrap raw LaTeX in a Pandoc pass-through fenced block."""
    return f'\n\n```{{=latex}}\n{content}```\n\n'


def volume_title_spread(title):
    """
    Full-spread title page:
      page 1 — blank verso
      page 2 — title centered vertically (recto)
    """
    title_recto = (
        '\\thispagestyle{empty}\n'
        '\\vspace*{\\fill}\n'
        '{\\centering\\fontsize{48}{60}\\selectfont\\scshape '
        f'{title}\\par}}\n'
        '\\vspace*{\\fill}\n'
        '\\newpage\n'
    )
    latex = BLANK_PAGE + title_recto
    return latex_block(latex)


def concat(out_path):
    parts = []

    for vol, path, title in VOLUMES:
        p = Path(path)
        if not p.exists():
            print(f'ERROR: {path} not found — run tag_books.py first')
            raise SystemExit(1)

        content = p.read_text()

        # 2 blank sheets + title spread before every volume
        parts.append(latex_block(BLANK_TWO_SHEETS))
        parts.append(volume_title_spread(title))

        if vol == 'bom':
            fm = FRONTMATTER.read_text()
            parts.append(fm)
            parts.append('\n\n')

        parts.append(content)
        parts.append('\n\n')
        print(f'  Added {path}')

    # 3 blank sheets at the very end
    parts.append(latex_block(BLANK_THREE_SHEETS))

    Path(out_path).write_text(''.join(parts))
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'out/quad/quad-raw.md'
    concat(out_path)
