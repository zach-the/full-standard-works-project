#!/usr/bin/env python3
"""
Step 0: Extract the New Testament from the KJV Cambridge Paragraph Bible text.

Starts from "THE GOSPEL ACCORDING TO" (Matthew heading) and ends just before
the "* * *" separator that follows Revelation 22:21.

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

# Find start: "THE GOSPEL ACCORDING TO" heading for Matthew (well past the OT)
start_idx = None
for i, line in enumerate(lines):
    if i < 50000:
        continue  # skip OT section
    if line.strip() == "THE GOSPEL ACCORDING TO":
        start_idx = i
        break

if start_idx is None:
    print("ERROR: Could not find NT start marker", file=sys.stderr)
    sys.exit(1)

# Find end: first "* * *" after Revelation 22:20 ("Even so, come, Lord Jesus")
# which is unique to Revelation and precedes the final verse 22:21.
end_idx = None
found_rev_end = False
for i, line in enumerate(lines):
    if "Even so, come, Lord Jesus" in line:
        found_rev_end = True
    if found_rev_end and line.strip() == "* * *":
        end_idx = i
        break

if end_idx is None:
    print("ERROR: Could not find NT end marker", file=sys.stderr)
    sys.exit(1)

print(f"NT start: line {start_idx + 1}")
print(f"NT end:   line {end_idx + 1} (exclusive)")
print(f"Lines extracted: {end_idx - start_idx}")

with open(out_file, "w", encoding="utf-8") as f:
    f.writelines(lines[start_idx:end_idx])

print(f"Wrote {out_file}")
