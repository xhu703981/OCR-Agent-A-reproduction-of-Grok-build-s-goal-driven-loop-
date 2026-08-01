RULE_ID = "quote_ocr_broken_apostrophe"

CASES: list[tuple[str, str]] = [
    ("it ' s not ready yet", "it's not ready yet"),
    ("they ' ll arrive soon", "they'll arrive soon"),
    ("he said, ' s a fine poem", "he said, ' s a fine poem"),
]

def fix_text(text: str) -> str:
    import re
    return re.sub(r"(\w) ' (s|t|ll|re|ve|d|m)\b", r"\1'\2", text)
