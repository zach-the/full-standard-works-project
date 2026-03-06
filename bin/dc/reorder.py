#!/usr/bin/env python3
"""
Reorder DC text file sections to match the JSON's numerical section order.

The Reader's Edition presents sections in a non-numerical order for thematic
or historical reasons. This script extracts each "Section N" block and writes
a new file with sections in ascending numerical order, so the generic
verse_insert.py can do a simple sequential scan.

Usage: python3 reorder.py <input.txt> <output.txt>
"""

import re
import sys

if len(sys.argv) != 3:
    print("Usage: python3 reorder.py <input.txt> <output.txt>")
    sys.exit(1)

in_file = sys.argv[1]
out_file = sys.argv[2]

with open(in_file, "r", encoding="utf-8") as f:
    text = f.read()

# Find all "Section N" heading positions
heading_re = re.compile(r'^(Section (\d+))\s*$', re.MULTILINE)
matches = list(heading_re.finditer(text))

if not matches:
    print("No 'Section N' headings found.")
    sys.exit(1)

# Everything before the first "Section N" heading is the preamble
preamble = text[:matches[0].start()].rstrip('\n') + '\n'

# Extract each section block: from heading start to just before the next heading
sections = {}  # sec_num (int) -> full block text (heading + content)
for i, m in enumerate(matches):
    sec_num = int(m.group(2))
    block_start = m.start()
    block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
    sections[sec_num] = text[block_start:block_end]

# Write output in ascending section order
ordered_nums = sorted(sections.keys())
print(f"Reordering {len(ordered_nums)} sections...")

with open(out_file, "w", encoding="utf-8") as f:
    f.write(preamble)
    f.write('\n')
    for num in ordered_nums:
        f.write(sections[num])

print(f"✅ Written to {out_file}")
