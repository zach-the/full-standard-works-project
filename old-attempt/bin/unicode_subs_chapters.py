#!/usr/bin/env python3
import re
import sys

# === Unicode subscript map ===
SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 format_bom_text.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # --- Read input ---
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    # --- 1️⃣ Replace <sub>number</sub> with LaTeX unicode subscripts ---
    def replace_sub(match):
        unicode_sub = match.group(1).translate(SUBSCRIPT_MAP)
        # smaller inline formatting for LaTeX text blocks
        return r"\text{\scriptsize{ " + unicode_sub + r" }}"

    text = re.sub(r"<sub>(\d+)</sub>", replace_sub, text)

    # --- 2️⃣ Replace inline <h1>Chapter title</h1> with \invisiblechapter{title} ---
    # This allows invisible chapter markers that update headers & gutter labels
    def replace_h1(match):
        chapter_name = match.group(1).strip()
        return r"\invisiblechapter{" + chapter_name + r"}"

    text = re.sub(r"<h1>(.*?)</h1>", replace_h1, text, flags=re.DOTALL)

    # --- Write output ---
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ Converted subscripts and inserted invisible chapters → {output_file}")

if __name__ == "__main__":
    main()

