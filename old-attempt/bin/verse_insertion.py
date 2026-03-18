import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

# === USAGE ===
# python script.py input.txt input.json outputname
if len(sys.argv) != 4:
    print("Usage: python script.py <input_txt> <input_json> <output_basename>")
    sys.exit(1)

original_file = sys.argv[1]
json_file = sys.argv[2]
base_name = sys.argv[3]

output_file = f"{base_name}.md"
not_found_file = f"{base_name}.error"

# === CONFIG ===
max_workers = 8          # number of threads
min_match_tokens = 5     # minimum number of matching tokens to consider a match
debug_mode = True        # set to True to print verse text + matched snippet

# === LOAD FILES ===
with open(original_file, "r", encoding="utf-8") as f:
    original_text = f.read()

with open(json_file, "r", encoding="utf-8") as f:
    bom = json.load(f)

verses = bom["verses"]

# === PRE-TOKENIZE FULL TEXT ===
book_words = re.findall(r'\w+', original_text.lower())
book_char_indices = [m.start() for m in re.finditer(r'\w+', original_text)]

# === TOKEN FUZZY MATCH ===
def token_fuzzy_match(verse_text, min_match_tokens=min_match_tokens):
    """
    Finds best start index of verse_text in original_text using token-level matching.
    Returns character index in original_text or -1 if not found.
    """
    verse_words = re.findall(r'\w+', verse_text.lower())
    n = len(verse_words)
    best_ratio = 0
    best_start_token = -1

    for i in range(len(book_words) - n + 1):
        window = book_words[i:i + n]
        matches = sum(1 for a, b in zip(verse_words, window) if a == b)
        if matches < min_match_tokens:
            continue
        ratio = matches / n
        if ratio > best_ratio:
            best_ratio = ratio
            best_start_token = i

    if best_start_token == -1:
        return -1

    # Map the token index back to the character index
    return book_char_indices[best_start_token]

# === PROCESS EACH VERSE ===
def process_verse(verse):
    ref = verse["reference"]
    verse_text = verse["text"]
    idx = token_fuzzy_match(verse_text)
    if debug_mode and idx != -1:
        snippet_words = re.findall(r'\w+', original_text[idx:idx+200])
        snippet_preview = " ".join(snippet_words[:10])
        print(f"--- DEBUG ---\nVerse JSON text: {verse_text}\nMatched text snippet: {snippet_preview}\n--------------")
    return ref, idx

# === RUN THREADS ===
matches = []
not_found = []

with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = [executor.submit(process_verse, v) for v in verses]
    for future in as_completed(futures):
        ref, idx = future.result()
        if idx == -1:
            not_found.append(ref)
            print(f"❌ Could not find verse {ref}")
        else:
            verse_num = ref.split(":")[-1]
            matches.append((idx, verse_num))
            print(f"✅ Prepared insertion for verse {ref}")

# === INSERT MARKERS BACK-TO-FRONT (overlap-safe) ===
matches_sorted = sorted(matches, key=lambda x: x[0], reverse=True)
current_text = original_text
inserted_ranges = []

for pos, num in matches_sorted:
    if any(start <= pos <= end for start, end in inserted_ranges):
        continue
    marker = f"<sub>{num}</sub> "
    current_text = current_text[:pos] + marker + current_text[pos:]
    inserted_ranges.append((pos, pos + len(marker)))

# === WRITE OUTPUT FILES ===
with open(output_file, "w", encoding="utf-8") as f:
    f.write(current_text)

if not_found:
    with open(not_found_file, "w", encoding="utf-8") as f:
        for nf in not_found:
            f.write(nf + "\n")
    print(f"⚠️ Some verses not found. See {not_found_file}")
else:
    print("✅ All verses inserted successfully.")

