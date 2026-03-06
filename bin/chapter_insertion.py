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

# --- Track position in markdown as we go ---
chapter_starts = []
current_chapter = None
sub_index = 0  # where we are in the markdown

for verse in verses:
    ref = verse.get("reference")
    if not ref:
        continue

    try:
        book_chapter, verse_num = ref.rsplit(":", 1)
    except ValueError:
        continue

    # new chapter boundary
    if book_chapter != current_chapter:
        current_chapter = book_chapter

        # find the next <sub>1</sub> *after our current index*
        found_pos = None
        for i in range(sub_index, len(sub_matches)):
            if sub_matches[i].group(1) == "1":
                found_pos = sub_matches[i].start()
                sub_index = i + 1
                break

        if found_pos is not None:
            chapter_starts.append((found_pos, book_chapter))

# --- Insert <h1> tags in reverse order ---
new_text = md_text
for pos, chapter_name in reversed(chapter_starts):
    new_text = new_text[:pos] + f"<h1>{chapter_name}</h1>" + new_text[pos:]

# --- Write output ---
with open(output_file, "w", encoding="utf-8") as f:
    f.write(new_text)

print(f"✅ Chapters inserted and written to {output_file}")
print(f"Inserted {len(chapter_starts)} chapter headings.")

