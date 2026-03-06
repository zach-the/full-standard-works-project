#!/usr/bin/env python3
"""
Step 3: Wrap consecutive short single-line blocks in <poetry>...</poetry> tags.

A block is "poetic" if it:
  - Is a single line (no internal newlines in the content)
  - Is short: length < 120 characters
  - Does NOT start with <h1>

Consecutive runs of poetic blocks are joined with single newlines inside
<poetry>...</poetry>, replacing the blank-line separators between them.

Usage: python3 poetry.py <input.md> <output.md>
"""

import re
import sys

if len(sys.argv) != 3:
    print("Usage: python3 poetry.py <input.md> <output.md>")
    sys.exit(1)

in_file = sys.argv[1]
out_file = sys.argv[2]

with open(in_file, encoding="utf-8") as f:
    text = f.read()

# Split on blank lines to get blocks.
# Each block is the text between double-newlines.
raw_blocks = text.split("\n\n")

POETRY_MAX_LEN = 120


def is_poetic(block):
    """True if this block qualifies as a poetry line."""
    s = block.strip()
    if not s:
        return False
    if s.startswith("<h1>"):
        return False
    # Must be a single line (no internal blank lines; allow \n within the line
    # only if it's just a single trailing/leading newline from split artifacts)
    # After stripping, there should be no newline left inside the content.
    if "\n" in s:
        return False
    if len(s) >= POETRY_MAX_LEN:
        return False
    return True


# Group consecutive poetic blocks into runs.
output_blocks = []
i = 0
while i < len(raw_blocks):
    if is_poetic(raw_blocks[i]):
        # Start a poetry run
        run = []
        while i < len(raw_blocks) and is_poetic(raw_blocks[i]):
            run.append(raw_blocks[i].strip())
            i += 1
        if len(run) == 1:
            # Single poetic block: keep as-is (don't wrap single lines)
            output_blocks.append(run[0])
        else:
            wrapped = "<poetry>\n" + "\n".join(run) + "\n</poetry>"
            output_blocks.append(wrapped)
    else:
        output_blocks.append(raw_blocks[i])
        i += 1

result = "\n\n".join(output_blocks)

with open(out_file, "w", encoding="utf-8") as f:
    f.write(result)

poetry_count = result.count("<poetry>")
print(f"Wrapped {poetry_count} poetry sections.")
print(f"Wrote {out_file}")
