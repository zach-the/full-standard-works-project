#!/usr/bin/env python3
import json
import re
import sys

# === Command line arguments ===
if len(sys.argv) < 3 or len(sys.argv) > 4:
    print("Usage: python3 check_md_indexed.py <file.md> <file.json> [output.txt]")
    sys.exit(1)

md_file = sys.argv[1]
json_file = sys.argv[2]
output_file = sys.argv[3] if len(sys.argv) == 4 else "differences_found.txt"

# === Load files ===
with open(md_file, "r", encoding="utf-8") as f:
    md_text = f.read()

with open(json_file, "r", encoding="utf-8") as f:
    bom = json.load(f)

verses = bom["verses"]

# === Clean text: remove HTML, punctuation, and lowercase ===
def clean_text(text):
    text = re.sub(r"<[^>]+>", "", text)  # remove HTML tags
    text = re.sub(r"[^\w\s]", "", text)  # remove punctuation
    return text.lower()  # ignore case

# === Find all <sub> insertions in MD ===
sub_pattern = re.compile(r"<sub>(\d+)</sub>")
sub_matches = list(sub_pattern.finditer(md_text))

# Build verse ranges between <sub> tags
md_verse_ranges = []
for i, match in enumerate(sub_matches):
    start = match.end()
    end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(md_text)
    md_verse_ranges.append((start, end))

# === Compare verses ===
differences = []

for verse, (start, end) in zip(verses, md_verse_ranges):
    json_text = clean_text(verse["text"])
    md_content = clean_text(md_text[start:end].strip())

    json_words = json_text.split()
    md_words = md_content.split()

    if not json_words or not md_words:
        continue  # skip empty

    min_len = min(len(json_words), len(md_words))

    # Select indices safely based on verse length
    if min_len <= 5:
        indices = list(range(min_len))
    else:
        indices = sorted(set([
            0,
            min_len // 4,
            min_len // 2,
            (3 * min_len) // 4,
            min_len - 1
        ]))

    mismatched_words = []
    for idx in indices:
        jw = json_words[idx] if idx < len(json_words) else None
        mw = md_words[idx] if idx < len(md_words) else None
        if jw != mw:
            mismatched_words.append((idx, jw, mw))

    if mismatched_words:
        differences.append({
            "reference": verse["reference"],
            "json_text": verse["text"],
            "md_text": md_text[start:end].strip(),
            "mismatched_words": mismatched_words
        })

# === Write output file ===
if differences:
    with open(output_file, "w", encoding="utf-8") as f:
        for diff in differences:
            f.write(f"Reference: {diff['reference']}\n")
            f.write(f"JSON Text: {diff['json_text']}\n")
            f.write(f"MD Text: {diff['md_text']}\n")
            f.write("Mismatched Words (index, json, md):\n")
            for idx, jword, mword in diff["mismatched_words"]:
                f.write(f"  {idx}: {jword} != {mword}\n")
            f.write("=" * 80 + "\n")
    print(f"⚠️ Differences found. See {output_file}")
else:
    print("✅ No differences found in sampled words.")

