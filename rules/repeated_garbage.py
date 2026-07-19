import re

RULE_ID = "repeated_garbage"

CASES: list[tuple[str, str]] = [
    ("This is a test....", "This is a test."),
    ("Another example.....", "Another example."),
    ("No change needed here.", "No change needed here.")
]

def fix_text(text: str) -> str:
    # Regular expression to find sequences of repeated characters longer than 5
    pattern = re.compile(r'(.)\1{4,}')
    
    # Replace the sequence with a single instance of the character
    fixed_text = pattern.sub(r'\1', text)
    
    return fixed_text
