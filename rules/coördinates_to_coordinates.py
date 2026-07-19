RULE_ID = "coördinates_to_coordinates"

CASES: list[tuple[str, str]] = [
    ("The coördinate system is used in mathematics.", "The coordinate system is used in mathematics."),
    ("He visited the Münchner museum.", "He visited the Münchner museum."),  # Negative example
    ("The weather in München is nice.", "The weather in München is nice.")   # Negative example
]

def fix_text(text: str) -> str:
    import re
    
    # Define a regex pattern to match 'ö' surrounded by word characters and part of known coordinate terms
    pattern = r'\b(\w*coördinate\w*)\b'
    
    # Replace 'ö' with 'o' in the matched patterns
    fixed_text = re.sub(pattern, lambda m: m.group(1).replace('ö', 'o'), text)
    
    return fixed_text
