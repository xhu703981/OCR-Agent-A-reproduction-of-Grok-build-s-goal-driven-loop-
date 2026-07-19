RULE_ID = "hyphenated_word_split"

CASES: list[tuple[str, str]] = [
    ("This is a test of the hyphenated-word-split rule. It should fix cases like this one where words are split across lines or have extra spaces.", "This is a test of the hyphenated-word-split rule. It should fix cases like this one where words are split across lines or have extra spaces."),
    ("Here is an example of a hyphenated word that is split: long-\ndivision. This should be fixed.", "Here is an example of a hyphenated word that is split: long-division. This should be fixed."),
    ("This is a negative example where the hyphenation is intentional: well-known. It should not change.", "This is a negative example where the hyphenation is intentional: well-known. It should not change.")
]

import re

def fix_text(text: str) -> str:
    # Join hyphenated words split across lines
    text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
    # Remove extra spaces around hyphens
    text = re.sub(r'\s*-\s*', '-', text)
    return text
