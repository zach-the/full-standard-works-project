#!/usr/bin/env python3
"""
bin/quad/convert.py — converts custom tags in quad-raw.md to LaTeX.

Tag → LaTeX mapping:
  <h2>Book</h2>               → \chapter{DisplayName}
  <h1>Book N</h1>             → \invisiblechapter{Book N} + \subsection*{Chapter N} (OT/NT/DC/PoGP)
                                 \invisiblechapter{Book N}                           (BOM)
  <sub>N</sub>                → \extramarks{Chapter:N}{Chapter:N}\text{\scriptsize{ ₁ }}
  <header class="book-intro"> → \begin{bookintro} ... \end{bookintro}
  </header>                   → (end of bookintro)
  <dateline>...</dateline>    → \dateline{...}
  <psalm-superscription>...</psalm-superscription>
                              → \psalmsuper{...}
  <poetry>                    → \begin{poetry}
  </poetry>                   → \end{poetry}

Usage:
    python3 bin/quad/convert.py [input.md] [output.md]
Defaults:
    in:  out/quad/quad-raw.md
    out: out/quad/quad-latex.md
"""

import re
import sys
from pathlib import Path

# Unicode subscript digits
SUBSCRIPT_MAP = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


def to_subscript(n):
    return str(n).translate(SUBSCRIPT_MAP)


# Volume detection by book name
OT_BOOKS = {
    'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
    'Joshua', 'Judges', 'Ruth', '1 Samuel', '2 Samuel',
    '1 Kings', '2 Kings', '1 Chronicles', '2 Chronicles',
    'Ezra', 'Nehemiah', 'Esther', 'Job', 'Psalms', 'Proverbs',
    'Ecclesiastes', "Solomon's Song", 'Isaiah', 'Jeremiah',
    'Lamentations', 'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos',
    'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk', 'Zephaniah',
    'Haggai', 'Zechariah', 'Malachi',
}

NT_BOOKS = {
    'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans',
    '1 Corinthians', '2 Corinthians', 'Galatians', 'Ephesians',
    'Philippians', 'Colossians', '1 Thessalonians', '2 Thessalonians',
    '1 Timothy', '2 Timothy', 'Titus', 'Philemon', 'Hebrews',
    'James', '1 Peter', '2 Peter', '1 John', '2 John', '3 John',
    'Jude', 'Revelation',
}

BOM_BOOKS = {
    '1 Nephi', '2 Nephi', 'Jacob', 'Enos', 'Jarom', 'Omni',
    'Words of Mormon', 'Mosiah', 'Alma', 'Helaman',
    '3 Nephi', '4 Nephi', 'Mormon', 'Ether', 'Moroni',
}

DC_BOOKS = {'D&C'}

POGP_BOOKS = {
    'Moses', 'Abraham',
    'Joseph Smith\u2014History',   # em-dash
    'Joseph Smith\u2014Matthew',
    'Articles of Faith',
}

# Display names for \chapter{} (where abbreviation differs from full name)
CHAPTER_DISPLAY_NAMES = {
    # D&C / OT
    'D&C': 'Doctrine and Covenants',
    "Solomon's Song": "Song of Solomon",
    # BOM full titles
    '1 Nephi':          'The First Book of Nephi',
    '2 Nephi':          'The Second Book of Nephi',
    'Jacob':            'The Book of Jacob',
    'Enos':             'The Book of Enos',
    'Jarom':            'The Book of Jarom',
    'Omni':             'The Book of Omni',
    'Words of Mormon':  'The Words of Mormon',
    'Mosiah':           'The Book of Mosiah',
    'Alma':             'The Book of Alma',
    'Helaman':          'The Book of Helaman',
    '3 Nephi':          'The Book of Nephi',
    '4 Nephi':          'The Book of Nephi',
    'Mormon':           'The Book of Mormon',
    'Ether':            'The Book of Ether',
    'Moroni':           'The Book of Moroni',
}

# Books that get a \subsection* chapter heading (all except BOM)
SUBSECTION_VOLUMES = OT_BOOKS | NT_BOOKS | DC_BOOKS | POGP_BOOKS


def get_volume(book):
    if book in OT_BOOKS:
        return 'ot'
    if book in NT_BOOKS:
        return 'nt'
    if book in BOM_BOOKS:
        return 'bom'
    if book in DC_BOOKS:
        return 'dc'
    if book in POGP_BOOKS:
        return 'pogp'
    return 'unknown'


def latex_escape(text):
    """Escape LaTeX special characters in text used in commands."""
    return text.replace('&', r'\&')


def extract_book(h1_text):
    tokens = h1_text.strip().split()
    return ' '.join(tokens[:-1])


def extract_chapter_num(h1_text):
    return h1_text.strip().split()[-1]


def fix_poetry_linebreaks(text):
    """Format poetry blocks with the hanging-indent indentation logic.

    Within each \\begin{poetry}...\\end{poetry} block, lines are assigned
    an indent level:

      - Line 1 of each verse (the \\vnum{N} line): normal (no indent)
      - Lines at even positions within a verse (2nd, 4th, ...): always indented
      - Lines at odd positions > 1 (3rd, 5th, ...): normal, UNLESS the line
        is the last line of its verse AND the verse is not the last verse in
        the poetry block → force indented.

    Verses are delimited by lines starting with \\vnum{.
    Each poetry block is treated as one stanza.
    """
    INDENT = '\\hspace*{2.5em}'

    def process_block(m):
        inner = m.group(1)
        raw_lines = [l.strip() for l in inner.split('\n') if l.strip()]
        if not raw_lines:
            return '\\begin{poetry}\n\\end{poetry}'

        # Group lines into verses; lines before the first \vnum form verse 0.
        verses = []
        current = []
        for line in raw_lines:
            if line.startswith(r'\vnum{') and current:
                verses.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            verses.append(current)

        n_verses = len(verses)
        out_parts = []

        for vi, verse_lines in enumerate(verses):
            is_last_verse = (vi == n_verses - 1)
            n_lines = len(verse_lines)
            parts = []

            for li, line in enumerate(verse_lines):
                position = li + 1   # 1-indexed within this verse
                is_last_line = (li == n_lines - 1)

                if position == 1:
                    do_indent = False
                elif position % 2 == 0:
                    do_indent = True
                else:
                    # Odd position > 1: force indent if last-in-verse but
                    # not last-in-stanza (i.e., more verses follow).
                    do_indent = is_last_line and not is_last_verse

                if not parts:
                    parts.append(line)
                elif do_indent:
                    parts.append(f'\\\\\n{INDENT}{line}')
                else:
                    parts.append(f'\\\\\n{line}')

            out_parts.append(''.join(parts))

        return '\\begin{poetry}\n\n' + '\n\n'.join(out_parts) + '\n\n\\end{poetry}'

    return re.sub(
        r'\\begin\{poetry\}(.*?)\\end\{poetry\}',
        process_block,
        text,
        flags=re.DOTALL,
    )


def convert(in_path, out_path):
    content = Path(in_path).read_text()

    result = []
    pos = 0
    current_chapter = None       # e.g. "Genesis 1"
    pending_margin_label = None  # BOM: label to emit right before next verse 1

    # Combined pattern for all tags we handle
    TAG_RE = re.compile(
        r'(<h2>(.*?)</h2>)'
        r'|(<h1>(.*?)</h1>)'
        r'|(<sub>(\d+)</sub>)'
        r'|(<header class="book-intro">)'
        r'|(</header>)'
        r'|(<dateline>(.*?)</dateline>)'
        r'|(<psalm-superscription>(.*?)</psalm-superscription>)'
        r'|(<book-heading>(.*?)</book-heading>)'
        r'|(<poetry>)'
        r'|(</poetry>)',
        re.DOTALL,
    )

    for m in TAG_RE.finditer(content):
        # Emit everything before this tag verbatim
        result.append(content[pos:m.start()])
        pos = m.end()

        full = m.group(0)

        if m.group(1):  # <h2>Book</h2>
            book = m.group(2).strip()
            display = latex_escape(CHAPTER_DISPLAY_NAMES.get(book, book))
            result.append(f'\n\n\\chapter{{{display}}}\n\n')

        elif m.group(3):  # <h1>Book N</h1>
            h1_text = m.group(4).strip()
            current_chapter = h1_text
            book = extract_book(h1_text)
            chap_num = extract_chapter_num(h1_text)
            vol = get_volume(book)

            h1_safe = latex_escape(h1_text)
            # All volumes: emit running head mark now
            margin = f'\\chapmark{{{h1_safe}}}'
            # BOM: schedule margin note for right before verse 1
            if vol == 'bom':
                pending_margin_label = h1_safe

            if vol == 'dc':
                sub = f'\\subsection*{{Section {chap_num}}}'
            elif vol in ('ot', 'nt', 'pogp'):
                sub = f'\\subsection*{{Chapter {chap_num}}}'
            else:  # bom — reader's edition sections, no displayed heading
                sub = ''

            # DC: add every 10th section (and the last, 138) to the TOC
            toc_entry = ''
            if vol == 'dc':
                n = int(chap_num)
                if n % 10 == 0 or n == 138:
                    toc_entry = f'\\addcontentsline{{toc}}{{section}}{{Section {chap_num}}}\n'

            if sub:
                result.append(f'\n\n{toc_entry}{sub}\n\n{margin} ')
            else:
                result.append(f'\n\n{toc_entry}{margin} ')

        elif m.group(5):  # <sub>N</sub>
            verse_num = m.group(6)
            sub_char = to_subscript(int(verse_num))
            # BOM: emit the pending margin label right before the first verse
            if pending_margin_label is not None:
                result.append(f'\\bommarginlabel{{{pending_margin_label}}}')
                pending_margin_label = None
            result.append(f'\\vnum{{{sub_char}}}')

        elif m.group(7):  # <header class="book-intro">
            result.append('\n\n\\begin{bookintro}\n')

        elif m.group(8):  # </header>
            result.append('\n\\end{bookintro}\n\n')

        elif m.group(9):  # <dateline>...</dateline>
            inner = m.group(10).strip()
            result.append(f'\n\n\\dateline{{{inner}}}\n\n')

        elif m.group(11):  # <psalm-superscription>...</psalm-superscription>
            inner = m.group(12).strip()
            result.append(f'\n\n\\psalmsuper{{{inner}}}\n\n')

        elif m.group(13):  # <book-heading>...</book-heading>
            inner = m.group(14).strip()
            result.append(f'\n\n\\bookheading{{{inner}}}\n\n')

        elif m.group(15):  # <poetry>
            result.append('\n\n\\begin{poetry}\n\n')

        elif m.group(16):  # </poetry>
            result.append('\n\n\\end{poetry}\n\n')

    result.append(content[pos:])

    final = fix_poetry_linebreaks(''.join(result))

    # Insert explicit \vspace between consecutive poetry stanza blocks.
    # \addvspace in the environment end-code gets absorbed by Pandoc's \par
    # injections; \vspace between the blocks is reliable.
    final = re.sub(
        r'(\\end\{poetry\})(\s*\\begin\{poetry\})',
        r'\1\n\n\\vspace{0.1em}\2',
        final,
    )

    Path(out_path).write_text(final)
    print(f'Wrote {out_path}')


if __name__ == '__main__':
    in_path  = sys.argv[1] if len(sys.argv) > 1 else 'out/quad/quad-raw.md'
    out_path = sys.argv[2] if len(sys.argv) > 2 else 'out/quad/quad-latex.md'
    convert(in_path, out_path)
