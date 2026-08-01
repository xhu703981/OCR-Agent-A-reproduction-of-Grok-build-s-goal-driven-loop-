RULE_ID = "junk_dot_run"

CASES: list[tuple[str, str]] = [
    ("See the entry..Sec. 12 for details.", "See the entry. Sec. 12 for details."),
    ("population has marked..Every material interest", "population has marked. Every material interest"),
    ("The version is 3.10.12 and stable.", "The version is 3.10.12 and stable."),
]

import re

def fix_text(text: str) -> str:
    def _collapse(m: re.Match) -> str:
        return f"{m.group(1)}. {m.group(2)}"
    return re.sub(r"(\w)[ .\-\t]{2,}[ .\-\t]*([A-Z0-9])", _collapse, text)
