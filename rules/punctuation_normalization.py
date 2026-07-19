"""One rule, one module. Contract: fix_text + CASES. Safe subset only."""

from __future__ import annotations

import re

RULE_ID = "punctuation_normalization"

CASES: list[tuple[str, str]] = [
    ('“hi”', '"hi"'),
    ("a....b", "a...b"),
    ("ok", "ok"),
]


def fix_text(text: str) -> str:
    text = text.replace("“", '"').replace("”", '"').replace("„", '"')
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("''", '"')
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\.{4,}", "...", text)
    text = re.sub(r"…{2,}", "...", text)
    return text


if __name__ == "__main__":
    for inp, exp in CASES:
        out = fix_text(inp)
        assert out == exp, (inp, out, exp)
    print("ok", RULE_ID)
