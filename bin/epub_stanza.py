#!/usr/bin/env python3
"""
bin/epub_stanza.py — extract stanza breaks from the KJV EPUB and insert
<stanza-break/> tags into an annotated OT or NT step4 markdown file.

Stanza breaks in the EPUB are <div class='b'> elements (USFM \\b marker).
For each such element, we find the next <span class="verse" id="..."> after
it and record that verse as the insertion point.

Verse IDs use a 2-char book code + chapter + _ + verse, e.g.:
  PS19_7  → Psalms chapter 19 verse 7
  JB3_1   → Job chapter 3 verse 1

We insert <stanza-break/> immediately before the <sub>N</sub> tag for the
matching (book, chapter, verse) in the markdown file.  The tag is only
inserted when the position falls inside a <poetry>...</poetry> block.

Usage:
    python3 bin/epub_stanza.py <epub.zip> <input.md> <output.md>
Defaults:
    epub:  in/epub/engkjvcpb.epub
    in:    out/ot/ot-step4.md
    out:   out/ot/ot-step5.md
"""

import re
import sys
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Mapping: EPUB book filename (inside OEBPS/) → (our book name, 2-char code)
# Only books that have <div class='b'> stanza breaks are listed.
# ---------------------------------------------------------------------------
EPUB_BOOK_MAP = {
    # OT
    'AMO': ('Amos',             'AM'),
    'ECC': ('Ecclesiastes',     'EC'),
    'HAB': ('Habakkuk',         'HK'),
    'HOS': ('Hosea',            'HS'),
    'ISA': ('Isaiah',           'IS'),
    'JER': ('Jeremiah',         'JR'),
    'JOB': ('Job',              'JB'),
    'JOL': ('Joel',             'JL'),
    'LAM': ('Lamentations',     'LM'),
    'MAL': ('Malachi',          'ML'),
    'MIC': ('Micah',            'MC'),
    'NAM': ('Nahum',            'NM'),
    'OBA': ('Obadiah',          'OB'),
    'PRO': ('Proverbs',         'PR'),
    'PSA': ('Psalms',           'PS'),
    "SNG": ("Solomon's Song",   'SS'),
    'ZEC': ('Zechariah',        'ZC'),
    'ZEP': ('Zephaniah',        'ZP'),
    # NT
    'REV': ('Revelation',       'RV'),
}

# Regex for verse ID spans: <span class="verse" id="PS19_7">
VERSE_SPAN_RE = re.compile(r'<span[^>]*\bclass="verse"[^>]*\bid="([A-Z0-9]+)_(\d+)"')
# Regex for stanza breaks
STANZA_BREAK_RE = re.compile(r"<div\s+class='b'>")


def parse_verse_id(verse_id_str, chapter_str, book_code):
    """
    Verse id tag has the form {2-char-code}{chapter}_{verse}.
    book_code is the 2-char prefix (e.g. 'PS').
    Returns (chapter_int, verse_int) or None if parse fails.
    """
    try:
        chapter = int(chapter_str)
        verse = int(verse_id_str)
        return chapter, verse
    except ValueError:
        return None


def extract_stanza_breaks(epub_path):
    """
    Parse the EPUB and return a set of (book_name, chapter, verse) tuples
    meaning "insert <stanza-break/> before this verse."
    """
    breaks = set()

    with zipfile.ZipFile(epub_path) as zf:
        for epub_file, (book_name, book_code) in EPUB_BOOK_MAP.items():
            xhtml_path = f'OEBPS/{epub_file}.xhtml'
            try:
                html = zf.read(xhtml_path).decode('utf-8')
            except KeyError:
                continue

            if "<div class='b'>" not in html:
                continue

            # Build a combined sequence of (type, data) in document order:
            # ('verse', chapter, verse) or ('break',)
            events = []
            for m in re.finditer(
                r"(<span[^>]*\bclass=\"verse\"[^>]*\bid=\"[A-Z0-9]+_\d+\")"
                r"|(<div\s+class='b'>)",
                html
            ):
                if m.group(1):  # verse span
                    vm = VERSE_SPAN_RE.search(m.group(1))
                    if vm:
                        vid = vm.group(1)   # e.g. "PS19"
                        vnum = vm.group(2)  # e.g. "7"
                        # Strip the 2-char book code to get the chapter
                        chapter_str = vid[2:]
                        result = parse_verse_id(vnum, chapter_str, book_code)
                        if result:
                            events.append(('verse', result[0], result[1]))
                else:  # stanza break
                    events.append(('break',))

            # Walk events: for each break, find the next verse
            i = 0
            while i < len(events):
                if events[i][0] == 'break':
                    # Find next verse event
                    for j in range(i + 1, len(events)):
                        if events[j][0] == 'verse':
                            ch, vs = events[j][1], events[j][2]
                            breaks.add((book_name, ch, vs))
                            break
                i += 1

    return breaks


def insert_stanza_breaks(md_content, stanza_breaks):
    """
    Scan the markdown content and insert <stanza-break/> before <sub>N</sub>
    when (current_book, current_chapter, N) is in stanza_breaks.
    Only inserts when inside a <poetry>...</poetry> block.
    """
    # Combined pattern: h1 headings, sub tags, poetry open/close
    SCAN_RE = re.compile(
        r'(<h1>(.*?)</h1>)'
        r'|(<sub>(\d+)</sub>)'
        r'|(<poetry>)'
        r'|(</poetry>)',
        re.DOTALL,
    )

    result = []
    pos = 0
    current_book = None
    current_chapter = None
    in_poetry = False
    poetry_just_opened = False

    for m in SCAN_RE.finditer(md_content):
        result.append(md_content[pos:m.start()])
        pos = m.end()

        if m.group(1):  # <h1>Book Chapter</h1>
            h1_text = m.group(2).strip()
            tokens = h1_text.split()
            current_chapter = int(tokens[-1])
            current_book = ' '.join(tokens[:-1])
            result.append(m.group(0))

        elif m.group(3):  # <sub>N</sub>
            verse_num = int(m.group(4))
            if (in_poetry
                    and not poetry_just_opened   # skip if 1st sub after <poetry>
                    and current_book is not None
                    and (current_book, current_chapter, verse_num) in stanza_breaks):
                result.append('<stanza-break/>\n')
            poetry_just_opened = False
            result.append(m.group(0))

        elif m.group(5):  # <poetry>
            in_poetry = True
            poetry_just_opened = True
            result.append(m.group(0))

        elif m.group(6):  # </poetry>
            in_poetry = False
            poetry_just_opened = False
            result.append(m.group(0))

    result.append(md_content[pos:])
    return ''.join(result)


def run(epub_path, in_path, out_path):
    print(f'Extracting stanza breaks from {epub_path}...')
    stanza_breaks = extract_stanza_breaks(epub_path)
    print(f'  Found {len(stanza_breaks)} stanza break positions')

    content = Path(in_path).read_text()
    result = insert_stanza_breaks(content, stanza_breaks)

    inserted = result.count('<stanza-break/>')
    print(f'  Inserted {inserted} <stanza-break/> tags into {in_path}')

    Path(out_path).write_text(result)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    epub_path = sys.argv[1] if len(sys.argv) > 1 else 'in/epub/engkjvcpb.epub'
    in_path   = sys.argv[2] if len(sys.argv) > 2 else 'out/ot/ot-step4.md'
    out_path  = sys.argv[3] if len(sys.argv) > 3 else 'out/ot/ot-step5.md'
    run(epub_path, in_path, out_path)
