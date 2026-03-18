import re
import sys

# Map digits to Unicode subscripts
SUBSCRIPT_MAP = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 sub2unicode.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Read input file
    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    # Replace <sub>number</sub> with Unicode subscripts
    def replace_sub(match):
        # Convert digits to Unicode subscripts
        unicode_sub = match.group(1).translate(SUBSCRIPT_MAP)
        # Wrap the Unicode subscript in a LaTeX command to make it smaller
        # \text{} is needed because this will be inserted into a text block,
        # and \tiny is a LaTeX font size modifier.
        return r"\text{\scriptsize{ " + unicode_sub + r" }}" 

    text = re.sub(r"<sub>(\d+)</sub>", replace_sub, text)

    # Write output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"✅ Converted subscripts written to {output_file}")

if __name__ == "__main__":
    main()
