RULE_ID = "spacing_hyphenation"

CASES: list[tuple[str, str]] = [
    ("This is a test-case with a split-word like co-ordinate.", "This is a test-case with a split-word like coordinate."),
    ("Another example with hyphenation in the middle of a word: well-known.", "Another example with hyphenation in the middle of a word: well-known."),
    ("No change needed here: hyphenated-word and another-example.", "No change needed here: hyphenated-word and another-example.")
]

import re

def fix_text(text: str) -> str:
    # Regular expression to find words split by OCR spacing or hyphenation
    pattern = r'(?<=[\s,;:.!?])[-](?=[a-zA-Z])'
    
    # Replace the matched patterns with an empty string
    fixed_text = re.sub(pattern, '', text)
    
    return fixed_text
