"""One rule, one module. Contract: fix_text + CASES. Conservative."""

from __future__ import annotations

import re

RULE_ID = "spacing_between_terms"

CASES: list[tuple[str, str]] = [
    ("fooBar", "foo Bar"),
    ("fOx", "fOx"),  # do not split single-letter + Upper (e.g. after 0→O fix)
    ("dxdydz", "dxdydz"),
    ("ab12cd", "ab 12 cd"),
]


def fix_text(text: str) -> str:
    # camelCase: need 2+ lowercase before Upper (avoid fOx → f Ox)
    text = re.sub(r"([a-z]{2,})([A-Z])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z]{2,})(\d+)([A-Za-z]{2,})", r"\1 \2 \3", text)
    return text


if __name__ == "__main__":
    for inp, exp in CASES:
        out = fix_text(inp)
        assert out == exp, (inp, out, exp)
    print("ok", RULE_ID)
