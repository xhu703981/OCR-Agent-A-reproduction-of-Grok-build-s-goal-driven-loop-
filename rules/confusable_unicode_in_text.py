RULE_ID = "confusable_unicode_in_text"

CASES: list[tuple[str, str]] = [
    ("This is an example of ffi in text.", "This is an example of ffi in text."),
    ("The indirect method uses fi to prove.", "The indirect method uses fi to prove."),
    ("Et nos Ricus ffich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua …", "Et nos Ricus ffich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua …")
]

import re

def fix_text(text: str) -> str:
    # Define a regex pattern to match confusable Unicode ligatures
    pattern = r'\b(fi|ffi|fl)\b'
    
    # Replace the matched patterns with their standard Latin equivalents
    fixed_text = re.sub(pattern, lambda match: match.group(0).replace('ﬁ', 'fi').replace('ﬃ', 'ffi').replace('ﬂ', 'fl'), text)
    
    return fixed_text
