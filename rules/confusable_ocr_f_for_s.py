RULE_ID = "confusable_ocr_f_for_s"

CASES: list[tuple[str, str]] = [
    ("Nu me uulften þer to: þe alle þing mai wel don. ftōde me an helping.", "Nu me uulsten þer to: þe alle þing mai wel don. stōde me an helping."),
    ("The Coaft was clear. þe king ſaw it.", "The Coast was clear. þe king ſaw it."),
    ("after often soft lift left craft profit office shift safety infant inflation softly £5", "after often soft lift left craft profit office shift safety infant inflation softly £5"),
]

import re

def fix_text(text: str) -> str:
    if not any(c in text for c in "þȝſ"):
        return text
    def repl(m):
        ch = "s" if m.group(1) == "f" else "S"
        return ch + m.group(2)
    return re.sub(r"([fF])([tlkp])", repl, text)
