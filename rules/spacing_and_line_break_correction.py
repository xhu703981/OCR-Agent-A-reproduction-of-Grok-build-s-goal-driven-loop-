import re

RULE_ID = "spacing_and_line_break_correction"

CASES: list[tuple[str, str]] = [
    ("Indirect Method of Proof. Notice: (a) it starts by assuming the negative of the conclusion; (b) it follows up the consequences of this assumption until a statement is reached which contradicts a known fact; (c) this contradiction is made the basis for asserting that the desired c…", "Indirect Method of Proof. Notice: (a) it starts by assuming the negative of the conclusion; (b) it follows up the consequences of this assumption until a statement is reached which contradicts a known fact; (c) this contradiction is made the basis for asserting that the desired conclusion is false."),
    ("Et nos Ricus ffich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua …", "Et nos Ricus ffich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua testamenti."),
    ("183 the x axis is not an asymptote to the curve y = f(x). The following is an example of the same kind in which the function f(x) does not change sign. The function where f(x): remains positive when x is positive, and it does not approach zero, since ƒ(kя) = kπ. In order to show …", "183 the x axis is not an asymptote to the curve y = f(x). The following is an example of the same kind in which the function f(x) does not change sign. The function where f(x) remains positive when x is positive, and it does not approach zero, since ƒ(kя) = kπ. In order to show that the x axis is not an asymptote, we need to consider the behavior of the function as x approaches infinity.")
]

def fix_text(text: str) -> str:
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    # Join split words
    text = re.sub(r'(\w)\s+(\w)', r'\1\2', text)
    return text
