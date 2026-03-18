#!/usr/bin/env python3
import json
import re
import sys

if len(sys.argv) != 4:
    print("Usage: python3 insert_chapters.py <input.md> <input.json> <output.md>")
    sys.exit(1)

md_file = sys.argv[1]
json_file = sys.argv[2]
output_file = sys.argv[3]

# --- Load files ---
with open(md_file, "r", encoding="utf-8") as f:
    md_text = f.read()

with open(json_file, "r", encoding="utf-8") as f:
    bom = json.load(f)

verses = bom["verses"]

# --- Find all <sub> verse tags in the MD ---
sub_pattern = re.compile(r"<sub>(\d+)</sub>")
sub_matches = list(sub_pattern.finditer(md_text))

if not sub_matches:
    print("❌ No <sub> tags found in the markdown file.")
    sys.exit(1)

# --- Determine chapter boundaries from JSON ---
chapter_starts = []  # (index_in_md, "Book Chapter")
current_chapter = None
verse_index = 0

for verse in verses:
    ref = verse["reference"]  # e.g. "1 Nephi 1:1"
    try:
        book_chapter, verse_num = ref.rsplit(":", 1)
    except ValueError:
        continue

    if book_chapter != current_chapter:
        current_chapter = book_chapter
        # Find corresponding <sub> in the markdown
        if verse_index < len(sub_matches):
            sub_match = sub_matches[verse_index]
            chapter_starts.append((sub_match.start(), book_chapter))
    verse_index += 1

# --- Insert <h1>chapter_name</h1> before those <sub> locations ---
# We go from the end of the text backward so indices don't shift
new_text = md_text
for pos, chapter_name in reversed(chapter_starts):
    insertion = f"<h1>{chapter_name}</h1>"
    new_text = new_text[:pos] + insertion + new_text[pos:]

# --- Write output ---
with open(output_file, "w", encoding="utf-8") as f:
    f.write(new_text)

print(f"✅ Chapters inserted and written to {output_file}")
print(f"Inserted {len(chapter_starts)} chapter headings.")

