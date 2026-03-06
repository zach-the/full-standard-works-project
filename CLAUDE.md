# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo processes LDS scripture texts — annotating plain-text editions with verse and chapter markers derived from structured JSON data, then verifying alignment. The output is Markdown with `<sub>N</sub>` verse markers and `<h1>Book Chapter</h1>` headings suitable for downstream rendering.

## Core Scripts (`bin/`)

All scripts are run directly with Python 3. No build step or dependencies beyond the standard library.

### `bin/chapter_insertion.py`
Scans an annotated MD file for `<sub>1</sub>` markers (verse 1 of each chapter) and inserts `<h1>Book Chapter</h1>` immediately before them.
```bash
python3 bin/chapter_insertion.py <annotated.md> <input.json> <output.md>
```

### `bin/checker.py` *(do not modify)*
Verifies alignment between an annotated MD and the JSON. Samples words at fixed positions (0%, 25%, 50%, 75%, 100%) within each verse range and reports mismatches.
```bash
python3 bin/checker.py <annotated.md> <input.json> [differences.txt]
```

### `bin/verse_insertion.py`
General-purpose fuzzy verse insertion (O(N×M), slow). Suitable for small texts or as a fallback. Not used in the BOM pipeline.

## Book of Mormon Pipeline (`bin/bom/`)

Run the full pipeline:
```bash
bash bin/bom/run.sh
# Output: out/bom/bom.md
```

Or step by step:
```bash
# Step 1: insert verse markers (sequential scan, ~0.6s for 6604 verses)
python3 bin/bom/verse_insert.py in/txt/readers-edition-eng-bofm.txt in/json/book-of-mormon-flat.json out/bom/bom-step1

# Step 2: insert chapter headings
python3 bin/chapter_insertion.py out/bom/bom-step1.md in/json/book-of-mormon-flat.json out/bom/bom-step2.md

# Step 3: verify (should report no differences)
python3 bin/checker.py out/bom/bom-step2.md in/json/book-of-mormon-flat.json out/bom/differences.txt
```

## Data Layout

```
in/
  epub/   — source EPUBs (KJV Bible, Book of Mormon, D&C, Pearl of Great Price)
  txt/    — plain-text equivalents of the EPUBs
  json/   — flat verse JSON files (one per volume)
```

### JSON format

Each JSON file has the shape:
```json
{ "verses": [ { "reference": "1 Nephi 1:1", "text": "..." }, ... ] }
```

References follow the pattern `"Book Name Chapter:Verse"`. The `rsplit(":", 1)` split is used throughout to separate book+chapter from verse number.

## Architecture Notes

- **Primary goal**: preserve the paragraphed structure of the input text files. All insertions are into the original text — no text is replaced or reworded. Casing and punctuation from the text files take precedence over the JSON.
- **`bin/bom/verse_insert.py`** pre-tokenizes the book text once, then for each verse (in order) scans forward from the last matched position using the verse's leading 8 tokens as a fingerprint. After a match, `search_pos` advances by the full verse token count (not just the fingerprint) to prevent phrases embedded within a verse from being falsely matched as the start of the next verse. Results are inserted back-to-front to avoid index shifting.
- **`bin/chapter_insertion.py`** advances a sequential pointer through `<sub>` matches, looking only for `<sub>1</sub>` to locate chapter starts.
- **`bin/checker.py`** zips JSON verses with extracted MD verse ranges (text between consecutive `<sub>` tags) and does sampled word comparison rather than full-text diff, to handle minor formatting differences.
