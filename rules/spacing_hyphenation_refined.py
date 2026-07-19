RULE_ID = "spacing_hyphenation_refined"

CASES: list[tuple[str, str]] = [
    ("word-continuation", "wordcontinuation"),
    ("split-word-here", "splitwordhere"),
    ("no-change-here!", "no-change-here!"),  # Negative example
]

def fix_text(text: str) -> str:
    import re
    
    # Regex pattern to match hyphen between two letters
    pattern = r"(\b\w)-(\w\b)"
    
    # Function to join matched words
    def join_words(match):
        return match.group(1) + match.group(2)
    
    # Apply the regex substitution
    fixed_text = re.sub(pattern, join_words, text)
    
    return fixed_text
