#!/usr/bin/env python3
"""
Step 1: Annotate the extracted NT text.

- Identifies book headings (ALL-CAPS blocks) and maps them to JSON book names.
- Replaces standalone chapter-number lines with <h1>BookName N</h1>.
- Strips pilcrow colophons: lines starting with the paragraph mark (U+00B6).
- Replaces inline verse numbers "N " with "<sub>N</sub> ".
- Normalizes spelling to match JSON (JSON spelling + TXT capitalization, via LCS).
- Skips inter-book TOC sections (between "* * *" and the ALL-CAPS heading).

Usage: python3 annotate.py <extracted.txt> <input.json> <output.md>
"""

import difflib
import json
import re
import sys

if len(sys.argv) != 4:
    print("Usage: python3 annotate.py <extracted.txt> <input.json> <output.md>")
    sys.exit(1)

txt_file = sys.argv[1]
json_file = sys.argv[2]
out_file = sys.argv[3]

# ---------------------------------------------------------------------------
# Book heading table: last ALL-CAPS heading line -> JSON book name
# ---------------------------------------------------------------------------
BOOK_HEADING_MAP = {
    "S. MATTHEW.": "Matthew",
    "S. MARK.": "Mark",
    "S. LUKE.": "Luke",
    "S. JOHN.": "John",           # Gospel of John (distinct from "JOHN." epistles)
    "THE ACTS OF THE APOSTLES.": "Acts",
    "ROMANS.": "Romans",
    # CORINTHIANS. appears twice -> counter
    "GALATIANS.": "Galatians",
    "EPHESIANS.": "Ephesians",
    "PHILIPPIANS.": "Philippians",
    "COLOSSIANS.": "Colossians",
    # THESSALONIANS. appears twice -> counter
    # TIMOTHY. appears twice -> counter
    "TITUS.": "Titus",
    "PHILEMON.": "Philemon",
    "HEBREWS.": "Hebrews",
    "JAMES.": "James",
    # PETER. appears twice -> counter
    # JOHN. appears three times -> counter (1 John, 2 John, 3 John)
    "JUDE.": "Jude",
    "S. JOHN THE DIVINE.": "Revelation",
}

# Counters for multi-occurrence headings
corinthians_count = 0
thessalonians_count = 0
timothy_count = 0
peter_count = 0
john_epistle_count = 0


def identify_book(heading_lines):
    """Return the JSON book name for a list of collected ALL-CAPS heading lines."""
    global corinthians_count, thessalonians_count, timothy_count
    global peter_count, john_epistle_count
    last_line = None
    for line in heading_lines:
        if line.strip():
            last_line = line.strip()
    if last_line is None:
        return None
    if last_line == "CORINTHIANS.":
        corinthians_count += 1
        return "1 Corinthians" if corinthians_count == 1 else "2 Corinthians"
    if last_line == "THESSALONIANS.":
        thessalonians_count += 1
        return "1 Thessalonians" if thessalonians_count == 1 else "2 Thessalonians"
    if last_line == "TIMOTHY.":
        timothy_count += 1
        return "1 Timothy" if timothy_count == 1 else "2 Timothy"
    if last_line == "PETER.":
        peter_count += 1
        return "1 Peter" if peter_count == 1 else "2 Peter"
    if last_line == "JOHN.":
        john_epistle_count += 1
        return {1: "1 John", 2: "2 John", 3: "3 John"}.get(john_epistle_count)
    return BOOK_HEADING_MAP.get(last_line)


def is_all_caps_line(line):
    """True if stripped line is non-empty, all-uppercase, and contains a letter."""
    s = line.strip()
    return bool(s) and s == s.upper() and any(c.isalpha() for c in s)


# ---------------------------------------------------------------------------
# Load JSON: build (book, chapter) -> max_verse and verse texts
# ---------------------------------------------------------------------------
with open(json_file, encoding="utf-8") as f:
    data = json.load(f)

chapter_map = {}    # (book, chap) -> max_verse
verse_texts_map = {}  # (book, chap) -> {verse_num: text}
for v in data["verses"]:
    ref = v["reference"]
    book_ch, verse_str = ref.rsplit(":", 1)
    m = re.match(r"^(.+)\s+(\d+)$", book_ch)
    book = m.group(1)
    chap = int(m.group(2))
    vnum = int(verse_str)
    key = (book, chap)
    if key not in chapter_map or chapter_map[key] < vnum:
        chapter_map[key] = vnum
    verse_texts_map.setdefault(key, {})[vnum] = v["text"]

# ---------------------------------------------------------------------------
# Pilcrow colophon stripper (¶ lines at end of epistles)
# ---------------------------------------------------------------------------
PILCROW_RE = re.compile(r"^\u00b6.*\n?", re.MULTILINE)


def strip_colophons(text):
    return PILCROW_RE.sub("", text)


# ---------------------------------------------------------------------------
# Spelling normalization via LCS alignment
# ---------------------------------------------------------------------------

# TXT may use Unicode typographic apostrophes (U+2018/U+2019) and hyphens
# within words. Treat them as word-internal so possessives and hyphenated
# names are single tokens. Require start and end to be a letter.
TXT_WORD_RE = re.compile(r"[A-Za-z]+(?:[\u2018\u2019'-][A-Za-z]+)*")

# JSON uses ASCII apostrophes and hyphens only, but also the ae ligature (Ææ)
# for proper names like "Judæa", "Cæsar", "Alphæus", etc.
JSON_WORD_RE = re.compile(r"[A-Za-z\u00c6\u00e6]+(?:['-][A-Za-z\u00c6\u00e6]+)*")

WORD_RE = TXT_WORD_RE  # alias used elsewhere


def apply_casing(json_word, txt_word):
    """Apply TXT-word capitalization style to the JSON spelling."""
    if not json_word:
        return json_word
    if txt_word and txt_word[0].isupper():
        return json_word[0].upper() + json_word[1:]
    return json_word.lower()


def normalize_verse_text(txt_text, json_words):
    """
    Given a verse's TXT text and a list of JSON word strings (lowercase),
    return the text with JSON spellings and TXT capitalization applied.

    Uses SequenceMatcher (LCS) alignment:
      equal   -> keep TXT word
      replace -> use JSON spelling + TXT capitalization
      delete  -> drop TXT word
      insert  -> add JSON word before the next TXT word
    """
    segments = []
    pos = 0
    for m in TXT_WORD_RE.finditer(txt_text):
        if m.start() > pos:
            segments.append((False, txt_text[pos:m.start()]))
        segments.append((True, m.group()))
        pos = m.end()
    if pos < len(txt_text):
        segments.append((False, txt_text[pos:]))

    txt_words = [s[1] for s in segments if s[0]]
    txt_lower = [w.lower() for w in txt_words]

    if not txt_words or not json_words:
        return txt_text

    sm = difflib.SequenceMatcher(None, txt_lower, json_words, autojunk=False)

    word_ops = {}       # txt_word_idx -> replacement str, or None (delete)
    pre_insertions = {} # txt_word_idx -> list of json words to insert before

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i in range(i1, i2):
                word_ops[i] = txt_words[i]
        elif tag == "replace":
            n_t, n_j = i2 - i1, j2 - j1
            n_c = min(n_t, n_j)
            for k in range(n_c):
                word_ops[i1 + k] = apply_casing(json_words[j1 + k], txt_words[i1 + k])
            for k in range(n_c, n_t):
                word_ops[i1 + k] = None  # delete extra TXT words
            if n_j > n_c:
                pre_insertions.setdefault(i2, []).extend(json_words[j1 + n_c : j2])
        elif tag == "delete":
            for i in range(i1, i2):
                word_ops[i] = None
        elif tag == "insert":
            pre_insertions.setdefault(i1, []).extend(json_words[j1:j2])

    out = []
    word_idx = 0
    pending_sep = ""

    for is_word, text in segments:
        if not is_word:
            pending_sep += text
        else:
            replacement = word_ops.get(word_idx)
            ins = pre_insertions.get(word_idx, [])

            if replacement is None and not ins:
                out.append(pending_sep.rstrip(" "))
            else:
                out.append(pending_sep)
                for iw in ins:
                    out.append(iw + " ")
                if replacement is not None:
                    out.append(replacement)

            pending_sep = ""
            word_idx += 1

    # Post-insertions go BEFORE the trailing separator so they precede any
    # terminal punctuation (e.g. "moth-eaten." -> "moth eaten." not "moth. eaten").
    if word_idx in pre_insertions:
        for iw in pre_insertions[word_idx]:
            out.append(" " + iw)

    out.append(pending_sep)

    return "".join(out)


def normalize_chapter_text(annotated_text, verse_texts):
    """
    Apply normalize_verse_text() to each verse span delimited by <sub>N</sub>.
    verse_texts: dict {verse_num: json_text}
    """
    sub_pat = re.compile(r"<sub>(\d+)</sub>")
    matches = list(sub_pat.finditer(annotated_text))
    if not matches:
        return annotated_text

    out = [annotated_text[: matches[0].start()]]

    for i, match in enumerate(matches):
        vnum = int(match.group(1))
        out.append(match.group(0))

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(annotated_text)
        verse_text = annotated_text[start:end]

        json_text = verse_texts.get(vnum, "")
        if json_text:
            json_words = JSON_WORD_RE.findall(json_text.lower())
            verse_text = normalize_verse_text(verse_text, json_words)

        out.append(verse_text)

    return "".join(out)


# ---------------------------------------------------------------------------
# Verse annotation for a single chapter
# ---------------------------------------------------------------------------

def annotate_chapter(chapter_text, book, chap, max_verse):
    """
    Strip colophons, then find and replace inline verse numbers
    "N " with "<sub>N</sub> " for each verse 1..max_verse.
    """
    text = strip_colophons(chapter_text)

    insertions = []
    search_from = 0

    for n in range(1, max_verse + 1):
        n_str = str(n)
        n_len = len(n_str)
        pos = search_from
        found = False

        while pos < len(text) - n_len:
            if text[pos : pos + n_len] == n_str and text[pos + n_len] == " ":
                if pos > 0 and text[pos - 1].isdigit():
                    pos += 1
                    continue
                insertions.append((pos, pos + n_len + 1, n))
                search_from = pos + n_len + 1
                found = True
                break
            pos += 1

        if not found:
            print(f"  WARN: {book} {chap}:{n} not found", file=sys.stderr)

    result = text
    for start, end, n in reversed(insertions):
        result = result[:start] + f"<sub>{n}</sub> " + result[end:]

    return result


# ---------------------------------------------------------------------------
# Main processing: state machine over lines
# ---------------------------------------------------------------------------
with open(txt_file, encoding="utf-8") as f:
    lines = f.readlines()

output_parts = []

STATE_SEEK = "seek"
STATE_HEADING = "heading"
STATE_BOOK = "book"

state = STATE_SEEK
current_book = None
current_chap = None
heading_buffer = []
chap_buffer = []


def flush_chapter():
    """Annotate accumulated chapter content and append to output."""
    global chap_buffer
    if current_chap is None or not chap_buffer:
        chap_buffer = []
        return
    chapter_text = "".join(chap_buffer)
    max_v = chapter_map.get((current_book, current_chap), 0)
    if max_v:
        annotated = annotate_chapter(chapter_text, current_book, current_chap, max_v)
        verse_texts = verse_texts_map.get((current_book, current_chap), {})
        annotated = normalize_chapter_text(annotated, verse_texts)
        output_parts.append(annotated)
    else:
        print(f"  WARN: {current_book} {current_chap} not in JSON", file=sys.stderr)
        output_parts.append(chapter_text)
    chap_buffer = []


for line in lines:
    stripped = line.strip()

    if state == STATE_SEEK:
        if is_all_caps_line(line) and stripped != "* * *":
            heading_buffer = [stripped]
            state = STATE_HEADING

    elif state == STATE_HEADING:
        if is_all_caps_line(line):
            heading_buffer.append(stripped)
        elif not stripped:
            pass
        else:
            book = identify_book(heading_buffer)
            if book:
                current_book = book
                print(f"Book: {current_book}")
            else:
                print(f"WARN: Unknown heading: {heading_buffer}", file=sys.stderr)
            heading_buffer = []
            state = STATE_BOOK
            if stripped.isdigit() and int(stripped) > 0:
                flush_chapter()
                current_chap = int(stripped)
                output_parts.append(f"<h1>{current_book} {current_chap}</h1>\n")
            elif stripped == "* * *":
                state = STATE_SEEK
            else:
                chap_buffer.append(line)

    elif state == STATE_BOOK:
        if stripped == "* * *":
            flush_chapter()
            current_chap = None
            state = STATE_SEEK
        elif stripped.isdigit() and int(stripped) > 0:
            flush_chapter()
            current_chap = int(stripped)
            output_parts.append(f"<h1>{current_book} {current_chap}</h1>\n")
        else:
            m = re.search(r" (\d+)$", line.rstrip("\n"))
            if m and int(m.group(1)) > 0:
                stripped_line = line.rstrip("\n")[: -len(m.group(0))] + "\n"
                chap_buffer.append(stripped_line)
                next_chap = int(m.group(1))
                flush_chapter()
                current_chap = next_chap
                output_parts.append(f"<h1>{current_book} {current_chap}</h1>\n")
            else:
                chap_buffer.append(line)

# Flush the last chapter (Revelation 22)
flush_chapter()

with open(out_file, "w", encoding="utf-8") as f:
    f.write("".join(output_parts))

result_text = "".join(output_parts)
sub_count = result_text.count("<sub>")
h1_count = result_text.count("<h1>")
print(f"\nDone. <sub> markers: {sub_count}, <h1> markers: {h1_count}")
print(f"Wrote {out_file}")
