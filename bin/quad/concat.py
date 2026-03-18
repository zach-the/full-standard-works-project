#!/usr/bin/env python3
"""
bin/quad/concat.py — concatenates all volume step4 files into quad-raw.md.

Volume order: OT → NT → BOM (with front matter) → D&C → PoGP

Usage:
    python3 bin/quad/concat.py [output.md]
Defaults:
    out: out/quad/quad-raw.md
"""

import sys
from pathlib import Path

FRONTMATTER = Path('bin/quad/bom-frontmatter.md')

VOLUMES = [
    ('ot',   'out/ot/ot-step4.md'),
    ('nt',   'out/nt/nt-step4.md'),
    ('bom',  'out/bom/bom-step4.md'),
    ('dc',   'out/dc/dc-step4.md'),
    ('pogp', 'out/pogp/pogp-step4.md'),
]


def concat(out_path):
    parts = []

    for vol, path in VOLUMES:
        p = Path(path)
        if not p.exists():
            print(f'ERROR: {path} not found — run tag_books.py first')
            raise SystemExit(1)

        content = p.read_text()

        if vol == 'bom':
            fm = FRONTMATTER.read_text()
            parts.append(fm)
            parts.append('\n\n')

        parts.append(content)
        parts.append('\n\n')
        print(f'  Added {path}')

    Path(out_path).write_text(''.join(parts))
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    out_path = sys.argv[1] if len(sys.argv) > 1 else 'out/quad/quad-raw.md'
    concat(out_path)
