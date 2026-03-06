#!/usr/bin/env python3
"""
Sequential verse marker insertion for the Book of Mormon Reader's Edition.

Inserts <sub>N</sub> markers into the source text at the start of each verse,
preserving all original paragraph structure, casing, and punctuation.

Uses a linear sequential scan (O(N+M)) rather than a global best-match search,
which enforces correct verse ordering and avoids false positives.

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
# Each entry: (lowercase_word, char_start_in_original_text)
word_matches = list(re.finditer(r'\w+', original_text))
book_words = [m.group().lower() for m in word_matches]
book_char_starts = [m.start() for m in word_matches]

FINGERPRINT_LEN = 8  # number of leading tokens used to identify a verse start

def find_verse_start(verse_text, search_from):
    """
    Find the first occurrence of verse_text's leading tokens in book_words,
    starting at token index search_from (enforces ordering).

    Returns (char_index, next_search_from) where next_search_from is advanced
    past the full verse token count (not just the fingerprint) to prevent
    phrases inside the matched verse from being re-matched for the next verse.
    Returns (-1, search_from) if not found.
    """
    verse_tokens = re.findall(r'\w+', verse_text.lower())
    if not verse_tokens:
        return -1, search_from

    fp_len = min(FINGERPRINT_LEN, len(verse_tokens))
    fingerprint = verse_tokens[:fp_len]
    limit = len(book_words) - fp_len + 1

    for i in range(search_from, limit):
        if book_words[i:i + fp_len] == fingerprint:
            # Advance past the full verse length so internal phrases
            # cannot be matched as the start of the next verse.
            return book_char_starts[i], i + len(verse_tokens)

    return -1, search_from


# --- Sequential scan ---
insertions = []   # list of (char_pos, verse_num_str)
not_found = []
search_pos = 0    # token index; advances monotonically

for verse in verses:
    ref = verse["reference"]
    verse_text = verse["text"]
    verse_num = ref.split(":")[-1]

    char_idx, next_pos = find_verse_start(verse_text, search_pos)

    if char_idx == -1:
        not_found.append(ref)
        print(f"❌ Not found: {ref}")
    else:
        insertions.append((char_idx, verse_num))
        search_pos = next_pos
        print(f"✅ {ref}")

# --- Insert markers back-to-front (index-shift safe) ---
result = original_text
for pos, num in reversed(insertions):
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
