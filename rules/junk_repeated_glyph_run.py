RULE_ID = "junk_repeated_glyph_run"

CASES: list[tuple[str, str]] = [
    ("the rain-makers wwww coming one after another in the sky", "the rain-makers w coming one after another in the sky"),
    ("footnote marker ³³³³ after the word caldel-liht", "footnote marker ³ after the word caldel-liht"),
    ("visit www.example.com for more details", "visit www.example.com for more details"),
]

import re

_RARE = "wyaelimnuv"
_SUPER = {"¹", "ª", "³", "º"}

def _collapse_run(m: re.Match) -> str:
    s = m.group(0)
    if len(s) >= 4 and s[0] in _RARE:
        return s[0]
    if len(s) >= 3 and s[0] in _SUPER:
        return s[0]
    return s

def fix_text(text: str) -> str:
    pattern = r"(?<![A-Za-z0-9])([" + re.escape(_RARE) + r"])\1{3,}(?![A-Za-z0-9])|(?<![A-Za-z0-9])([" + re.escape("".join(_SUPER)) + r"])\2{2,}(?![A-Za-z0-9])"
    return re.sub(pattern, _collapse_run, text)
