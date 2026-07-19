RULE_ID = "hyphenation_line_break_join"

CASES: list[tuple[str, str]] = [
    ("This is a test- case.", "This is a testcase."),
    ("Another example\nwith a line break.", "Another example with a line break."),
    ("Intentional hyphenated-word should remain unchanged.", "Intentional hyphenated-word should remain unchanged.")
]

import re

def fix_text(text: str) -> str:
    # Regular expression to find hyphens or line breaks followed by a word starting with a letter
    pattern = r'([-\n])([a-zA-Z])'
    
    def replacer(match):
        # Join the hyphenated or line-broken word with the following word
        return match.group(2)
    
    # Apply the replacement
    fixed_text = re.sub(pattern, replacer, text)
    
    return fixed_text
