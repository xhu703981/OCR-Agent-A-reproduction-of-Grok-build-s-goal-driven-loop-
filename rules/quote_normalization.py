RULE_ID = "quote_normalization"

CASES: list[tuple[str, str]] = [
    ("He said «Hello» to her.", 'He said "Hello" to her.'),
    ('The book is titled “Great Expectations”.', 'The book is titled “Great Expectations”.'),
    ("She replied, 'That's a good idea.'", "She replied, \"That's a good idea.\"")
]

def fix_text(text: str) -> str:
    import re
    
    # Define patterns for different types of quotes
    double_quotes_pattern = re.compile(r'«|»|“|”')
    single_quotes_pattern = re.compile(r"‘|’")
    
    # Replace double quotes with "
    text = double_quotes_pattern.sub('"', text)
    
    # Replace single quotes with '
    text = single_quotes_pattern.sub("'", text)
    
    return text
