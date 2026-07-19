RULE_ID = "ligature_ffi_to_fi"

CASES: list[tuple[str, str]] = [
    ("This is a test of ffi in a word.", "This is a test of fi in a word."),
    ("The equation was 3ffi + 2 = 5.", "The equation was 3fi + 2 = 5."),
    ("Here is an example of officiële.", "Here is an example of officiële.")
]

def fix_text(text: str) -> str:
    import re
    
    # Pattern to match 'ffi' in contexts where it's likely an OCR artifact
    pattern = r'\b\w*ffi\b'
    
    def replace_ffi(match):
        word = match.group(0)
        if "fi" in word or "f i" in word:
            return word.replace("ffi", "fi")
        return word
    
    # Apply the replacement function to all matches
    fixed_text = re.sub(pattern, replace_ffi, text)
    
    return fixed_text
