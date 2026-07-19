RULE_ID = "confusable_digit_in_word_with_quotes"

CASES: list[tuple[str, str]] = [
    ('"He said, I have 0 apples."', '"He said, I have O apples."'),
    ("'She has 0 oranges.'", "'She has O oranges.'"),
    ("The temperature is 0°C.", "The temperature is 0°C."),
]

import re

def fix_text(text: str) -> str:
    # Regex pattern to find '0' surrounded by word characters and adjacent to a quotation mark
    pattern = r'(?<=[\w\'])0(?=[\w\'])'
    
    # Replace '0' with 'O' based on the pattern
    fixed_text = re.sub(pattern, 'O', text)
    
    return fixed_text
