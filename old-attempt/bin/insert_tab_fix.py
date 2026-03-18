import re
import sys
import os

def fix_latex_indentation(input_filepath, output_filepath=None):
    """
    Detects and fixes the LaTeX indentation problem caused by the sequence
    \chapter{...} or \subsection{...} followed by \invisiblechapter{...}
    by inserting \text{}\indent{} immediately after \invisiblechapter{...}.
    
    This version uses a robust regular expression that accounts for 
    optional \par commands and matches both \chapter and \subsection.

    Args:
        input_filepath (str): The path to the LaTeX file to read.
        output_filepath (str, optional): The path to the file where the fixed 
                                         content should be written. If None, 
                                         the input file is modified in place.
    """
    # 1. Read the entire file content
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found at path: {input_filepath}")
        return
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Define the pattern to find:
    # 1. ((?:\subsection|\\chapter)\{.*?}) - Capture Group 1: Matches and captures either \subsection{...} or \chapter{...}
    # 2. \s*(\\par\s*)* - Matches optional whitespace, followed by zero or more \par commands and surrounding whitespace.
    # 3. (\\invisiblechapter\{.*?\}) - Capture Group 2: The invisible chapter command
    
    # Pattern: Finds \subsection{...} or \chapter{...} followed by \invisiblechapter{...}
    pattern = r'((?:\\subsection|\\chapter)\{.*?})\s*(\\par\s*)*(\\invisiblechapter\{.*?\})'
    
    # Replacement string: Uses the captured groups (\1 and \3) and inserts the fix after the chapter command.
    # \1 is the chapter/subsection command
    # \3 is the \invisiblechapter command
    replacement = r'\1\n\n\3\\text{}\\indent{}'

    # Apply the substitution
    # The 're.DOTALL' flag is crucial, as it allows '.' to match newline characters across the commands.
    fixed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    if fixed_content == content:
        # Provide a warning if running on a Markdown file, as the regex is LaTeX-specific
        if input_filepath.lower().endswith(('.md', '.markdown')):
            print(f"**WARNING:** You are running this script on a Markdown file ({input_filepath}).")
            print("The pattern (matching \\subsection and \\invisiblechapter) is specific to LaTeX files.")
            print("Ensure you are running this script on the **Pandoc-generated .tex file**.")
        else:
            print(f"No changes made to {input_filepath}. Pattern not found.")
        return

    # 2. Write the fixed content
    target_filepath = output_filepath if output_filepath else input_filepath
    
    try:
        with open(target_filepath, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
            
        if output_filepath:
            print(f"Successfully fixed indentation pattern. Output written to {target_filepath}")
        else:
            print(f"Successfully fixed indentation pattern in place in {target_filepath}")

    except Exception as e:
        print(f"Error writing to file {target_filepath}: {e}")


if __name__ == '__main__':
    if len(sys.argv) == 2:
        # Usage: python fix_indentation.py <input_file.tex> (modifies in place)
        fix_latex_indentation(sys.argv[1], None) 
    elif len(sys.argv) == 3:
        # Usage: python fix_indentation.py <input_file.tex> <output_file.tex>
        fix_latex_indentation(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python fix_indentation.py <input_file.tex> [output_file.tex]")
        print("If only one file is provided, it will be modified in place.")
