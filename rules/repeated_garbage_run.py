RULE_ID = "repeated_garbage_run"

CASES: list[tuple[str, str]] = [
    ("This is a test with some repeated characters....", "This is a test with some repeated characters."),
    ("Another example with multiple runs!!!", "Another example with multiple runs!"),
    ("No changes here 12345 or ----", "No changes here 12345 or ----")
]

import re

def fix_text(text: str) -> str:
    # Regex pattern to match repeated characters surrounded by word boundaries
    pattern = r'\b(\w)\1+\b(?!\w)'
    # Replace with a single instance of the character
    fixed_text = re.sub(pattern, r'\1', text)
    return fixed_text
