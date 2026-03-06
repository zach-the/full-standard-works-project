#!/usr/bin/env python3
"""
Section-aware verse marker insertion for the Doctrine and Covenants Reader's Edition.

The DC Reader's Edition presents sections in a different order than the JSON
(which is numerically ordered). This script builds a per-section text range map
from "Section N" headings in the source file, then performs an independent
sequential scan within each section's text range.

Usage: python3 verse_insert.py <input.txt> <input.json> <output_basename>
  Produces: <output_basename>.md   — annotated text with <sub>N</sub> markers
            <output_basename>.error — list of verses not found (if any)
"""

import json
import re
import sys

if len(sys.argv) != 4:
    print("Usage: python3 verse_insert.py <input.txt> <input.json> <output_basename>")
    sys.exit(1)

txt_file = sys.argv[1]
json_file = sys.argv[2]
base_name = sys.argv[3]

output_file = f"{base_name}.md"
not_found_file = f"{base_name}.error"

# --- Load files ---
with open(txt_file, "r", encoding="utf-8") as f:
    original_text = f.read()

with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

verses = data["verses"]

# --- Pre-tokenize full text ---
word_matches = list(re.finditer(r'\w+', original_text))
book_words = [m.group().lower() for m in word_matches]
book_char_starts = [m.start() for m in word_matches]

FINGERPRINT_LEN = 8


def char_to_token(char_pos):
    """Return the index of the first token at or after char_pos (binary search)."""
    lo, hi = 0, len(book_char_starts)
    while lo < hi:
        mid = (lo + hi) // 2
        if book_char_starts[mid] < char_pos:
            lo = mid + 1
        else:
            hi = mid
    return lo


# --- Build section token ranges from "Section N" headings ---
# Sections appear out of numerical order in the text file, so we map by number.
section_heading_re = re.compile(r'^Section (\d+)\s*$', re.MULTILINE)
# Also handle "Official Declaration" sections (OD 1 and OD 2)
od_heading_re = re.compile(r'^Official Declaration[- ]*(\d+)\s*$', re.MULTILINE)

# Collect (char_pos, section_key) for all section-like headings
heading_positions = []  # list of (char_start_of_heading_line, section_key_str)

for m in section_heading_re.finditer(original_text):
    heading_positions.append((m.start(), f"sec_{int(m.group(1))}"))

for m in od_heading_re.finditer(original_text):
    heading_positions.append((m.start(), f"od_{int(m.group(1))}"))

# Sort by text position
heading_positions.sort(key=lambda x: x[0])

# Build token ranges: section content starts after the heading line ends
section_token_ranges = {}  # key -> (token_start, token_end)
for i, (char_pos, key) in enumerate(heading_positions):
    # Content starts after this heading's newline
    content_start_char = original_text.index('\n', char_pos) + 1
    token_start = char_to_token(content_start_char)

    # Content ends at the start of the next heading (or end of file)
    if i + 1 < len(heading_positions):
        next_char = heading_positions[i + 1][0]
        token_end = char_to_token(next_char)
    else:
        token_end = len(book_words)

    section_token_ranges[key] = (token_start, token_end)


def section_key_for_ref(ref):
    """Extract the section key string from a verse reference like 'D&C 10:5'."""
    # ref format: "D&C N:V" or "OD N" (Official Declarations have no colon)
    if ':' not in ref:
        # Official Declaration: ref like "OD 1" — treat verse num as section
        parts = ref.split()
        return f"od_{int(parts[-1])}"
    sec_part = ref.rsplit(':', 1)[0]  # "D&C 10"
    sec_num = int(sec_part.split()[-1])
    return f"sec_{sec_num}"


def find_verse_start(verse_text, search_from, search_to):
    """
    Find the first occurrence of verse_text's leading tokens in book_words[search_from:search_to].
    Returns (char_index, next_search_from) or (-1, search_from) if not found.
    """
    verse_tokens = re.findall(r'\w+', verse_text.lower())
    if not verse_tokens:
        return -1, search_from

    fp_len = min(FINGERPRINT_LEN, len(verse_tokens))
    fingerprint = verse_tokens[:fp_len]
    limit = min(search_to, len(book_words) - fp_len + 1)

    for i in range(search_from, limit):
        if book_words[i:i + fp_len] == fingerprint:
            return book_char_starts[i], i + len(verse_tokens)

    return -1, search_from


# --- Per-section sequential scan ---
insertions = []   # list of (char_pos, verse_num_str)
not_found = []
section_search_pos = {}  # section_key -> current token index within section

for verse in verses:
    ref = verse["reference"]
    verse_text = verse["text"]
    verse_num = ref.split(":")[-1] if ":" in ref else ref.split()[-1]

    key = section_key_for_ref(ref)

    if key not in section_token_ranges:
        not_found.append(ref)
        print(f"❌ Section not in text: {ref}")
        continue

    token_start, token_end = section_token_ranges[key]

    # Initialize search pos for this section on first use
    if key not in section_search_pos:
        section_search_pos[key] = token_start

    char_idx, next_pos = find_verse_start(verse_text, section_search_pos[key], token_end)

    if char_idx == -1:
        not_found.append(ref)
        print(f"❌ Not found: {ref}")
    else:
        insertions.append((char_idx, verse_num))
        section_search_pos[key] = next_pos
        print(f"✅ {ref}")

# --- Insert markers back-to-front ---
result = original_text
for pos, num in reversed(sorted(insertions)):
    marker = f"<sub>{num}</sub> "
    result = result[:pos] + marker + result[pos:]

# --- Write outputs ---
with open(output_file, "w", encoding="utf-8") as f:
    f.write(result)

print(f"\nInserted {len(insertions)} verse markers → {output_file}")

if not_found:
    with open(not_found_file, "w", encoding="utf-8") as f:
        f.write("\n".join(not_found) + "\n")
    print(f"⚠️  {len(not_found)} verses not found → {not_found_file}")
else:
    print("✅ All verses found.")
