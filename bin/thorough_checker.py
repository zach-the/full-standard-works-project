#!/usr/bin/env python3
"""
thorough_checker.py — exhaustive verse alignment checker

Checks:
  1. Verse count: MD <sub> tag count == JSON verse count
  2. Verse number sequence: each <sub>N> has the right N for that JSON position
  3. Full word comparison: every word in every verse (not a sample)
  4. Chapter heading presence: <h1>Book Chapter</h1> exists for each chapter
  5. H1 content bleed: strips heading text from verse ranges before comparing

Usage:
  python3 bin/thorough_checker.py <annotated.md> <input.json> [report.txt]
"""

import json
import re
import sys
from collections import defaultdict


def clean_verse_text(text):
    """Strip HTML block elements (with content), remaining tags, punctuation; lowercase; split."""
    # Remove full <h1>...</h1> blocks including their text content
    text = re.sub(r"<h[1-6][^>]*>.*?</h[1-6]>", "", text, flags=re.DOTALL)
    # Remove remaining HTML tags (keeps inner text for inline elements)
    text = re.sub(r"<[^>]+>", "", text)
    # Strip punctuation (keep word characters and spaces)
    text = re.sub(r"[^\w\s]", "", text)
    return text.lower().split()


def word_diff(json_words, md_words):
    """
    Return a list of (index, json_word, md_word) for every position that differs.
    Uses a simple longest-common-subsequence alignment to avoid false positives from
    shifted insertions/deletions.
    """
    # Fast path: identical
    if json_words == md_words:
        return []

    # For manageable verse sizes, do a proper LCS-based diff
    # Falls back to positional if verses are very long (>500 words) to bound cost
    jlen = len(json_words)
    mlen = len(md_words)

    if jlen <= 500 and mlen <= 500:
        return _lcs_diff(json_words, md_words)
    else:
        # Positional fallback for very long verses
        diffs = []
        for i in range(max(jlen, mlen)):
            jw = json_words[i] if i < jlen else "<MISSING>"
            mw = md_words[i] if i < mlen else "<MISSING>"
            if jw != mw:
                diffs.append((i, jw, mw))
        return diffs


def _lcs_diff(a, b):
    """
    Compute LCS table and return minimal edit-script differences as
    (position_in_a, a_word, b_word). Positions with only insertions or only
    deletions use None for the absent side.
    """
    n, m = len(a), len(b)
    # Build LCS length table
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if a[i] == b[j]:
                dp[i][j] = dp[i + 1][j + 1] + 1
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])

    diffs = []
    i = j = 0
    pos = 0
    while i < n or j < m:
        if i < n and j < m and a[i] == b[j]:
            i += 1
            j += 1
            pos += 1
        elif j < m and (i == n or dp[i + 1][j] >= dp[i][j + 1]):
            # Insertion in MD
            diffs.append((pos, "<MISSING>", b[j]))
            j += 1
        else:
            # Deletion from MD
            diffs.append((pos, a[i], "<MISSING>"))
            i += 1
            pos += 1
    return diffs


def categorize_diffs(diffs):
    """Classify a list of word diffs into substitutions, extra_words, missing_words."""
    substitutions = [(i, j, m) for i, j, m in diffs if j != "<MISSING>" and m != "<MISSING>"]
    missing_words = [(i, j, m) for i, j, m in diffs if m == "<MISSING>"]
    extra_words   = [(i, j, m) for i, j, m in diffs if j == "<MISSING>"]
    return substitutions, extra_words, missing_words


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 bin/thorough_checker.py <file.md> <file.json> [report.txt]")
        sys.exit(1)

    md_file   = sys.argv[1]
    json_file = sys.argv[2]
    report_file = sys.argv[3] if len(sys.argv) >= 4 else "thorough_report.txt"

    with open(md_file, encoding="utf-8") as f:
        md_text = f.read()
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)

    verses = data["verses"]
    json_count = len(verses)

    # ── 1. Extract <sub> markers ──────────────────────────────────────────────
    sub_pattern = re.compile(r"<sub>(\d+)</sub>")
    sub_matches = list(sub_pattern.finditer(md_text))
    md_count = len(sub_matches)

    issues = []

    # ── 2. Verse count check ──────────────────────────────────────────────────
    count_ok = md_count == json_count
    if not count_ok:
        issues.append({
            "type": "COUNT_MISMATCH",
            "detail": f"MD has {md_count} <sub> tags; JSON has {json_count} verses"
        })

    # ── 3. Verse number sequence check ───────────────────────────────────────
    n_to_check = min(md_count, json_count)
    verse_num_mismatches = []
    for i in range(n_to_check):
        actual_num = int(sub_matches[i].group(1))
        ref = verses[i]["reference"]
        expected_num = int(ref.rsplit(":", 1)[1])
        if actual_num != expected_num:
            verse_num_mismatches.append({
                "type": "VERSE_NUMBER_MISMATCH",
                "reference": ref,
                "position": i,
                "expected": expected_num,
                "actual": actual_num,
            })

    # ── 4. Chapter heading check ──────────────────────────────────────────────
    h1_pattern = re.compile(r"<h1>([^<]+)</h1>")
    h1_texts = {m.group(1).strip() for m in h1_pattern.finditer(md_text)}

    chapter_order = []
    seen_chapters = set()
    for v in verses:
        bc = v["reference"].rsplit(":", 1)[0]
        if bc not in seen_chapters:
            chapter_order.append(bc)
            seen_chapters.add(bc)

    missing_headings = [bc for bc in chapter_order if bc not in h1_texts]

    # ── 5. Full word comparison ───────────────────────────────────────────────
    word_mismatch_issues = []
    for i in range(n_to_check):
        match = sub_matches[i]
        start = match.end()
        end = sub_matches[i + 1].start() if i + 1 < n_to_check else len(md_text)

        md_words   = clean_verse_text(md_text[start:end])
        json_words = clean_verse_text(verses[i]["text"])

        diffs = word_diff(json_words, md_words)
        if not diffs:
            continue

        subs, extra, missing = categorize_diffs(diffs)
        word_mismatch_issues.append({
            "type": "WORD_MISMATCH",
            "reference": verses[i]["reference"],
            "json_words": json_words,
            "md_words": md_words,
            "diffs": diffs,
            "substitutions": subs,
            "extra_words": extra,
            "missing_words": missing,
        })

    # ── 6. Aggregate statistics ───────────────────────────────────────────────
    total_word_diffs = sum(len(i["diffs"]) for i in word_mismatch_issues)
    total_subs  = sum(len(i["substitutions"]) for i in word_mismatch_issues)
    total_extra = sum(len(i["extra_words"])   for i in word_mismatch_issues)
    total_missing = sum(len(i["missing_words"]) for i in word_mismatch_issues)

    verses_only_extra   = [i for i in word_mismatch_issues if i["extra_words"]   and not i["missing_words"] and not i["substitutions"]]
    verses_only_missing = [i for i in word_mismatch_issues if i["missing_words"] and not i["extra_words"]   and not i["substitutions"]]
    verses_mixed        = [i for i in word_mismatch_issues if i not in verses_only_extra and i not in verses_only_missing]

    # ── 7. Write report ───────────────────────────────────────────────────────
    lines = []
    def hr(char="─", width=78): lines.append(char * width)

    hr("═")
    lines.append("THOROUGH CHECKER REPORT")
    hr("═")
    lines.append(f"MD:   {md_file}")
    lines.append(f"JSON: {json_file}")
    lines.append(f"JSON verses: {json_count}  |  MD <sub> tags: {md_count}")
    lines.append("")
    hr()
    lines.append("SUMMARY")
    hr()
    lines.append(f"  Verse count match:        {'✓' if count_ok else '✗ MISMATCH'}")
    lines.append(f"  Verse number mismatches:  {len(verse_num_mismatches)}")
    lines.append(f"  Missing chapter headings: {len(missing_headings)} / {len(chapter_order)}")
    lines.append(f"  Verses with word errors:  {len(word_mismatch_issues)} / {n_to_check}  ({100*len(word_mismatch_issues)/max(n_to_check,1):.2f}%)")
    lines.append(f"    Total word-level diffs: {total_word_diffs}")
    lines.append(f"    Substitutions:          {total_subs}")
    lines.append(f"    Extra words (MD only):  {total_extra}")
    lines.append(f"    Missing words (MD):     {total_missing}")
    lines.append(f"  Verses clean:             {n_to_check - len(word_mismatch_issues)} / {n_to_check}")
    lines.append("")

    if not count_ok:
        hr()
        lines.append("COUNT MISMATCH")
        hr()
        for i in issues:
            if i["type"] == "COUNT_MISMATCH":
                lines.append(f"  {i['detail']}")
        lines.append("")

    if missing_headings:
        hr()
        lines.append(f"MISSING CHAPTER HEADINGS  ({len(missing_headings)} total)")
        hr()
        for bc in missing_headings[:60]:
            lines.append(f"  {bc}")
        if len(missing_headings) > 60:
            lines.append(f"  ... and {len(missing_headings) - 60} more")
        lines.append("")

    if verse_num_mismatches:
        hr()
        lines.append(f"VERSE NUMBER MISMATCHES  ({len(verse_num_mismatches)} total)")
        hr()
        for i in verse_num_mismatches[:30]:
            lines.append(f"  position={i['position']:5d}  ref={i['reference']:30s}  expected=<sub>{i['expected']}</sub>  got=<sub>{i['actual']}</sub>")
        if len(verse_num_mismatches) > 30:
            lines.append(f"  ... and {len(verse_num_mismatches) - 30} more")
        lines.append("")

    if word_mismatch_issues:
        hr()
        lines.append(f"WORD MISMATCHES  ({len(word_mismatch_issues)} verses affected)")
        hr()
        lines.append(f"  Pattern breakdown:")
        lines.append(f"    Only extra words in MD:   {len(verses_only_extra)}")
        lines.append(f"    Only missing words in MD: {len(verses_only_missing)}")
        lines.append(f"    Mixed / substitutions:    {len(verses_mixed)}")
        lines.append("")

        lines.append("  First 80 affected verses:")
        for issue in word_mismatch_issues[:80]:
            lines.append("")
            lines.append(f"  Ref: {issue['reference']}")
            jw_str = " ".join(issue["json_words"])
            mw_str = " ".join(issue["md_words"])
            lines.append(f"  JSON ({len(issue['json_words'])} w): {jw_str[:120]}{'…' if len(jw_str)>120 else ''}")
            lines.append(f"  MD   ({len(issue['md_words'])} w): {mw_str[:120]}{'…' if len(mw_str)>120 else ''}")
            lines.append(f"  Diffs ({len(issue['diffs'])}):")
            for idx, jw, mw in issue["diffs"][:12]:
                lines.append(f"    [{idx:4d}]  json={jw!r:25}  md={mw!r}")
            if len(issue["diffs"]) > 12:
                lines.append(f"    ... and {len(issue['diffs']) - 12} more diffs in this verse")

        if len(word_mismatch_issues) > 80:
            lines.append(f"\n  ... and {len(word_mismatch_issues) - 80} more affected verses (not shown)")
        lines.append("")

    all_clean = (count_ok and not verse_num_mismatches
                 and not missing_headings and not word_mismatch_issues)
    hr("═")
    lines.append("RESULT: ✅ ALL CHECKS PASSED" if all_clean else "RESULT: ✗ FAILURES DETECTED")
    hr("═")

    report = "\n".join(lines)
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    sys.exit(0 if all_clean else 1)


if __name__ == "__main__":
    main()
