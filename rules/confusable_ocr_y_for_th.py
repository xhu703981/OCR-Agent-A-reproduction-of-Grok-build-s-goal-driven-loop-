import re

RULE_ID = "confusable_ocr_y_for_th"

CASES: list[tuple[str, str]] = [
    ("Nu me uulften þer to: þe alle þing mai wel don. þe heze heueneliche king? yaf yow yem.", "Nu me uulften þer to: þe alle þing mai wel don. þe heze heueneliche king? þaf þow þem."),
    ("per wes al longe niht? songes and yolden yow þe yolden.", "per wes al longe niht? songes and þolden þow þe þolden."),
    ("This modern passage mentions your year yield and they.", "This modern passage mentions your year yield and they."),
]

def fix_text(text: str) -> str:
    if "þ" not in text and "ȝ" not in text:
        return text
    return re.sub(r"\by([eaou])", r"þ\1", text)
