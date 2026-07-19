RULE_ID = "ligature_to_split"

CASES: list[tuple[str, str]] = [
    ("Indirect Method of Proof. Notice: (a) it starts by assuming the negative of t' out='t Method of Proof. Notice: (a) it s tarts by assuming the negative of '",
     "Indirect Method of Proof. Notice: (a) it starts by assuming the negative of the conclusion;"),
    ("Et nos Ricus ffich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua …",
     "Et nos Ricus f fic offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua …"),
    ("K₂ or K₁₂ on P, postponing the consideration of classes of relations on P. 12 70. Properties of relations K, K₂, K₁₂-In systems (A; P; K₁, K₂; M) the relations K₁, K, are used to define properties of classes M. They are of the type specified; other restrictions on generality will…",
     "K₂ or K₁₂ on P, postponing the consideration of classes of relations on P. 12 70. Properties of relations K, K₂, K₁₂-In systems (A; P; K₁, K₂; M) the relations K₁, K, are used to define properties of classes M. They are of the type specified; other restrictions on generality will…")
]

def fix_text(text: str) -> str:
    # Define a dictionary of ligatures and their component characters
    ligatures = {
        'ffi': 'ff i',
        'ffl': 'ff l',
        'ﬁ': 'f i',
        'ﬂ': 'f l',
        'ﬅ': 's t',
        'ﬆ': 's t'
    }
    
    # Iterate over each ligature and replace it with its component characters
    for ligature, replacement in ligatures.items():
        text = text.replace(ligature, replacement)
    
    return text
