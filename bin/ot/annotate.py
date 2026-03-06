#!/usr/bin/env python3
"""
Step 1: Annotate the extracted OT text.

- Identifies book headings (ALL-CAPS blocks) and maps them to JSON book names.
- Replaces standalone chapter-number lines with <h1>BookName N</h1>.
- Strips Hebrew acrostic notation: (X) where X is non-ASCII.
- Replaces inline verse numbers "N " with "<sub>N</sub> ".
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
# Book heading table: last ALL-CAPS heading line → JSON book name
# ---------------------------------------------------------------------------
BOOK_HEADING_MAP = {
    "GENESIS.": "Genesis",
    "EXODUS.": "Exodus",
    "LEVITICUS.": "Leviticus",
    "NUMBERS.": "Numbers",
    "DEUTERONOMY.": "Deuteronomy",
    "THE BOOK OF JOSHUA.": "Joshua",
    "THE BOOK OF JUDGES.": "Judges",
    "THE BOOK OF RUTH.": "Ruth",
    # Samuel/Kings use alternative KJV titles
    "THE FIRST BOOK OF THE KINGS.": "1 Samuel",
    "THE SECOND BOOK OF THE KINGS.": "2 Samuel",
    "THE THIRD BOOK OF THE KINGS.": "1 Kings",
    "THE FOURTH BOOK OF THE KINGS.": "2 Kings",
    # Chronicles has two occurrences — handled via counter below
    "EZRA.": "Ezra",
    "THE BOOK OF NEHEMIAH.": "Nehemiah",
    "THE BOOK OF ESTHER.": "Esther",
    "THE BOOK OF JOB.": "Job",
    "THE BOOK OF PSALMS.": "Psalms",
    "THE PROVERBS.": "Proverbs",
    "THE PREACHER.": "Ecclesiastes",
    "THE SONG OF SOLOMON.": "Solomon's Song",
    "ISAIAH.": "Isaiah",
    "JEREMIAH.": "Jeremiah",
    "LAMENTATIONS OF JEREMIAH.": "Lamentations",
    "EZEKIEL.": "Ezekiel",
    "THE BOOK OF DANIEL.": "Daniel",
    "HOSEA.": "Hosea",
    "JOEL.": "Joel",
    "AMOS.": "Amos",
    "OBADIAH.": "Obadiah",
    "JONAH.": "Jonah",
    "MICAH.": "Micah",
    "NAHUM.": "Nahum",
    "HABAKKUK.": "Habakkuk",
    "ZEPHANIAH.": "Zephaniah",
    "HAGGAI.": "Haggai",
    "ZECHARIAH.": "Zechariah",
    "MALACHI.": "Malachi",
}

chronicles_count = 0


def identify_book(heading_lines):
    """Return the JSON book name for a list of collected ALL-CAPS heading lines."""
    global chronicles_count
    last_line = None
    for line in heading_lines:
        if line.strip():
            last_line = line.strip()
    if last_line is None:
        return None
    if last_line == "CHRONICLES.":
        chronicles_count += 1
        return "1 Chronicles" if chronicles_count == 1 else "2 Chronicles"
    return BOOK_HEADING_MAP.get(last_line)


def is_all_caps_line(line):
    """True if stripped line is non-empty, all-uppercase, and contains a letter."""
    s = line.strip()
    return bool(s) and s == s.upper() and any(c.isalpha() for c in s)


# ---------------------------------------------------------------------------
# Load JSON: build (book, chapter) → max_verse
# ---------------------------------------------------------------------------
with open(json_file, encoding="utf-8") as f:
    data = json.load(f)

chapter_map = {}    # (book, chap) → max_verse
verse_texts_map = {}  # (book, chap) → {verse_num: text}
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
# Hebrew acrostic notation stripper: (X) where X is one or more non-ASCII chars
# ---------------------------------------------------------------------------
HEBREW_RE = re.compile(r"\([^\x00-\x7F)]+\)")


def strip_hebrew(text):
    return HEBREW_RE.sub("", text)


# ---------------------------------------------------------------------------
# Spelling normalization: align TXT words with JSON words via LCS,
# use JSON spelling + TXT capitalization for mismatches.
# ---------------------------------------------------------------------------

# TXT may use Unicode typographic apostrophes (U+2018/U+2019) and hyphens
# within words ("Abram\u2019s", "Beer-sheba").  Treat them as word-internal so
# possessives and hyphenated names are single tokens.  Require the token to
# start and end with a letter to avoid matching standalone punctuation.
TXT_WORD_RE = re.compile(r"[A-Za-z]+(?:[\u2018\u2019'-][A-Za-z]+)*")

# JSON uses ASCII apostrophes and hyphens only.
JSON_WORD_RE = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")

# Keep WORD_RE as an alias used outside normalize functions (Hebrew strip etc.)
WORD_RE = TXT_WORD_RE


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
    # Tokenize TXT into alternating (non-word, word) segments
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

    # Rebuild text: buffer the non-word segment preceding each word so we can
    # suppress the trailing space when a word is deleted.
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
                # Delete: drop this word; also trim the trailing space from
                # the preceding separator so we don't get double spaces.
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
    # terminal punctuation (e.g. "moth-eaten." → "moth eaten." not "moth. eaten").
    if word_idx in pre_insertions:
        for iw in pre_insertions[word_idx]:
            out.append(" " + iw)

    # Trailing separator
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

    out = [annotated_text[: matches[0].start()]]  # text before first <sub>

    for i, match in enumerate(matches):
        vnum = int(match.group(1))
        out.append(match.group(0))  # <sub>N</sub>

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
    Strip Hebrew notation, then find and replace inline verse numbers
    "N " with "<sub>N</sub> " for each verse 1..max_verse.

    In the KJV Cambridge Paragraph Bible the only Arabic digits in chapter
    content are verse numbers, so we simply find each "N " (digit sequence
    followed by a space, not preceded by another digit) in forward order.
    """
    text = strip_hebrew(chapter_text)

    insertions = []  # (start_pos, end_pos_excl, verse_num)
    search_from = 0

    for n in range(1, max_verse + 1):
        n_str = str(n)
        n_len = len(n_str)
        pos = search_from
        found = False

        while pos < len(text) - n_len:
            # Exact digit match followed by a space
            if text[pos : pos + n_len] == n_str and text[pos + n_len] == " ":
                # Not preceded by a digit (avoid matching inside larger numbers)
                if pos > 0 and text[pos - 1].isdigit():
                    pos += 1
                    continue
                # In KJV prose, all digits are verse numbers — accept the match
                insertions.append((pos, pos + n_len + 1, n))
                search_from = pos + n_len + 1
                found = True
                break
            pos += 1

        if not found:
            print(f"  WARN: {book} {chap}:{n} not found", file=sys.stderr)

    # Apply insertions back-to-front to preserve positions
    result = text
    for start, end, n in reversed(insertions):
        result = result[:start] + f"<sub>{n}</sub> " + result[end:]

    return result


# ---------------------------------------------------------------------------
# Main processing: state machine over lines
# ---------------------------------------------------------------------------
with open(txt_file, encoding="utf-8") as f:
    lines = f.readlines()  # each line ends with '\n'

output_parts = []

STATE_SEEK = "seek"          # after * * *, before ALL-CAPS heading
STATE_HEADING = "heading"    # collecting ALL-CAPS heading lines
STATE_BOOK = "book"          # inside book content

state = STATE_SEEK
current_book = None
current_chap = None
heading_buffer = []
chap_buffer = []   # lines of current chapter content (with '\n')


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
        # Skip everything (TOC, separators, lowercase names, chapter lists)
        # until we see the start of an ALL-CAPS book heading.
        if is_all_caps_line(line) and stripped != "* * *":
            heading_buffer = [stripped]
            state = STATE_HEADING

    elif state == STATE_HEADING:
        if is_all_caps_line(line):
            heading_buffer.append(stripped)
        elif not stripped:
            # Blank line between heading lines: skip
            pass
        else:
            # Non-blank, non-ALL-CAPS → heading block is complete
            book = identify_book(heading_buffer)
            if book:
                current_book = book
                print(f"Book: {current_book}")
            else:
                print(f"WARN: Unknown heading: {heading_buffer}", file=sys.stderr)
            heading_buffer = []
            state = STATE_BOOK
            # Process the current (non-heading) line as book content
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
            # Check for chapter number embedded at end of line:
            # "...verse text. N\n" where N is the next chapter number.
            # In the CPB, some chapter breaks appear as a digit at the
            # very end of the last verse paragraph (not a standalone line).
            m = re.search(r" (\d+)$", line.rstrip("\n"))
            if m and int(m.group(1)) > 0:
                # Strip the embedded chapter number from the line
                stripped_line = line.rstrip("\n")[: -len(m.group(0))] + "\n"
                chap_buffer.append(stripped_line)
                next_chap = int(m.group(1))
                flush_chapter()
                current_chap = next_chap
                output_parts.append(f"<h1>{current_book} {current_chap}</h1>\n")
            else:
                chap_buffer.append(line)

# Flush the last chapter (Malachi 4)
flush_chapter()

# Write output
with open(out_file, "w", encoding="utf-8") as f:
    f.write("".join(output_parts))

# Count markers
result_text = "".join(output_parts)
sub_count = result_text.count("<sub>")
h1_count = result_text.count("<h1>")
print(f"\nDone. <sub> markers: {sub_count}, <h1> markers: {h1_count}")
print(f"Wrote {out_file}")
