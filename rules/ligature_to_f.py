RULE_ID = "ligature_to_f"

CASES: list[tuple[str, str]] = [
    ("The method of proof is by contradiction.", "The method of proof is by contradiction."),
    ("Et nos Ricus ffich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua …", "Et nos Ricus fich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua …"),
    ("The function where f(x): remains positive when x is positive, and it does not approach zero, since ƒ(kя) = kπ.", "The function where f(x): remains positive when x is positive, and it does not approach zero, since f(kя) = kπ.")
]

import re

def fix_text(text: str) -> str:
    # Regex to find 'ffi' followed by a lowercase 'i'
    pattern = r'\bffi(?=i\b)'
    # Replace with 'fi'
    fixed_text = re.sub(pattern, 'fi', text)
    return fixed_text
