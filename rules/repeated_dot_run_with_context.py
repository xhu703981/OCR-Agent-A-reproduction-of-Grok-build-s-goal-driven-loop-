RULE_ID = "repeated_dot_run_with_context"

CASES: list[tuple[str, str]] = [
    ("This is a test.......", "This is a test."),
    ("Another example............", "Another example."),
    ("Et nos Ricus ffich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua ....", "Et nos Ricus ffich offic principał curie metro dubliñ suprascript' Roberto & henrico supvisorib3 p testatorem deputat' ex certe causis anm nĩm juste moventib; ad exequend et disponend circa funalia & sepultura ipius Joħis Whylde. testatoris ac alia pagend put ipe testator in sua ....")
]

import re

def fix_text(text: str) -> str:
    # Define patterns for citations and mathematical expressions
    citation_pattern = r'\(.*?\)'
    math_expression_pattern = r'[0-9]+[a-zA-Z]*\s*=\s*[0-9a-zA-Z\s.]+'
    
    # Find all matches of citations and mathematical expressions
    citations = re.findall(citation_pattern, text)
    math_expressions = re.findall(math_expression_pattern, text)
    
    # Replace sequences of 5+ dots with a single dot if not in citation or math expression
    def replace_dots(match):
        line = match.group(0)
        if any(cit in line for cit in citations) or any(math_expr in line for math_expr in math_expressions):
            return line
        else:
            return re.sub(r'\.{5,}', '.', line)
    
    # Split text into lines and process each line
    fixed_lines = [replace_dots(re.match(r'.*', line)) if re.match(r'.*', line) else line for line in text.split('\n')]
    
    # Join the lines back together
    return '\n'.join(fixed_lines)
