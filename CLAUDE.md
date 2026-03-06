# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo processes LDS scripture texts — annotating plain-text editions with verse and chapter markers derived from structured JSON data, then verifying alignment. The output is Markdown with `<sub>N</sub>` verse markers and `<h1>Book Chapter</h1>` headings suitable for downstream rendering.

## Scripts and Usage

All scripts live in `bin/` and are run directly with Python 3. No build step or dependencies beyond the standard library.

### Step 1: Insert verse markers

```bash
python3 bin/verse_insertion.py <input.txt> <input.json> <output_basename>
# Produces: <output_basename>.md  (annotated text)
#           <output_basename>.error  (unmatched verses, if any)
```

Fuzzy token-matches each verse from the JSON into the text and inserts `<sub>N</sub>` before the matched position. Uses 8 threads (`max_workers`). Matching threshold: `min_match_tokens = 5`.

### Step 2: Insert chapter headings

```bash
python3 bin/chapter_insertion_fixed.py <annotated.md> <input.json> <output.md>
```

Scans the annotated MD for `<sub>1</sub>` markers (verse 1 of each chapter) and inserts `<h1>Book Chapter</h1>` immediately before them. **Use `chapter_insertion_fixed.py`, not `chapter_insertion.py`** — the original has a positional index bug.

### Step 3: Verify alignment

```bash
python3 bin/checker.py <annotated.md> <input.json> [differences.txt]
```

Samples words at fixed positions (0%, 25%, 50%, 75%, 100%) within each verse range and reports mismatches. Default output file: `differences_found.txt`.

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

- **verse_insertion.py** pre-tokenizes the entire book text once, then matches each verse by sliding a token window and computing exact-token overlap ratio. Results are inserted back-to-front to avoid index shifting.
- **chapter_insertion_fixed.py** advances a sequential pointer through `<sub>` matches, looking only for `<sub>1</sub>` to locate chapter starts — avoiding the off-by-one error in the original.
- **checker.py** zips JSON verses with extracted MD verse ranges (text between consecutive `<sub>` tags) and does sampled word comparison rather than full-text diff, to handle minor formatting differences.
