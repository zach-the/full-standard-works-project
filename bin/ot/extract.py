#!/usr/bin/env python3
"""
Step 0: Extract the Old Testament from the KJV Cambridge Paragraph Bible text.

Starts from "THE FIRST BOOK OF MOSES," heading (Genesis) and ends just before
the "* * *" separator that follows Malachi 4:6.

Usage: python3 extract.py <input.txt> <output.txt>
"""

import sys

if len(sys.argv) != 3:
    print("Usage: python3 extract.py <input.txt> <output.txt>")
    sys.exit(1)

in_file = sys.argv[1]
out_file = sys.argv[2]

with open(in_file, encoding="utf-8") as f:
    lines = f.readlines()

# Find start: first line containing "THE FIRST BOOK OF MOSES,"
start_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith("THE FIRST BOOK OF MOSES,"):
        start_idx = i
        break

if start_idx is None:
    print("ERROR: Could not find OT start marker", file=sys.stderr)
    sys.exit(1)

# Find end: first "* * *" that appears after Malachi 4:6
# ("smite the earth with a curse")
end_idx = None
found_malachi_end = False
for i, line in enumerate(lines):
    if "smite the earth with a curse" in line:
        found_malachi_end = True
    if found_malachi_end and line.strip() == "* * *":
        end_idx = i
        break

if end_idx is None:
    print("ERROR: Could not find OT end marker", file=sys.stderr)
    sys.exit(1)

print(f"OT start: line {start_idx + 1}")
print(f"OT end:   line {end_idx + 1} (exclusive)")
print(f"Lines extracted: {end_idx - start_idx}")

with open(out_file, "w", encoding="utf-8") as f:
    f.writelines(lines[start_idx:end_idx])

print(f"Wrote {out_file}")
