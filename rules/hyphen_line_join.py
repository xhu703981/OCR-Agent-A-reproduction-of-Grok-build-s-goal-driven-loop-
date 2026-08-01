RULE_ID = "hyphen_line_join"

CASES: list[tuple[str, str]] = [
    ("The experiment was realiz -\ned successfully.", "The experiment was realized successfully."),
    ("They start -\ned the journey at dawn.", "They started the journey at dawn."),
    ("It was a well-known result in the literature.", "It was a well-known result in the literature."),
]

import re

def fix_text(text: str) -> str:
    text = re.sub(r'(\w+)\s*-\s*\n\s*([a-z])', r'\1\2', text)
    text = re.sub(r'(\w+)\s+-\s+(ed|ing|ings|tion|ions)\b', r'\1\2', text)
    return text
