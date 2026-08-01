RULE_ID = "confusable_ocr_minimu_n_for_m"

CASES: list[tuple[str, str]] = [
    ("þe alle þing mai wel don imun end", "þe alle þing mai wel don imum end"),
    ("hæhliche fungen clarckes imun fair", "hæhliche fungen clarckes imum fair"),
    ("the mountain awehluyawe", "the mountain awehluyawe"),
]

import re

def fix_text(text: str) -> str:
    if not re.search(r"[ſþæ]", text):
        return text
    def _sub(m):
        return m.group(1) + "m"
    return re.sub(r"(?<=[bcdfghjklmnpqrstvwxyz])([ui])n\b", _sub, text)
