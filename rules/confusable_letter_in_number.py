RULE_ID = "confusable_letter_in_number"

CASES: list[tuple[str, str]] = [
    ("183x", "183x"),
    ("kя", "kя"),
    ("i is the imaginary unit", "i is the imaginary unit")
]

import re

def fix_text(text: str) -> str:
    # Define a regex pattern to find letter-like symbols within numeric context
    pattern = r'(?<=\d|[()+\-*/])[ikx](?=\d|[()+\-*/])'
    
    # Replace 'i' with '1', 'k' remains as is, 'x' remains as is
    def replace_match(match):
        char = match.group(0)
        if char == 'i':
            return '1'
        return char
    
    fixed_text = re.sub(pattern, replace_match, text)
    
    return fixed_text
