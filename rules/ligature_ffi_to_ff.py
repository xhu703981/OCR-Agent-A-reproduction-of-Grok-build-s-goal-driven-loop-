RULE_ID = "ligature_ffi_to_ff"

CASES: list[tuple[str, str]] = [
    ("The function f(x) is defined as y = x^2.", "The function f(x) is defined as y = x^2."),
    ("This is a test of ffi in a technical context.", "This is a test of ff in a technical context."),
    ("In German, the word 'Straße' contains an ffi ligature.", "In German, the word 'Straße' contains an ffi ligature.")
]

def fix_text(text: str) -> str:
    import re
    
    # Define a regex pattern to match 'ffi' surrounded by word characters
    pattern = r'\bffi\b'
    
    # Replace 'ffi' with 'ff' only if it is not part of a known ligature
    def replace_ffi(match):
        # List of known ligatures that should not be replaced
        known_ligatures = ["Straße", "café", "façade"]
        
        # Get the matched word
        word = match.group(0)
        
        # Check if the word is in the list of known ligatures
        if word in known_ligatures:
            return word
        
        # Otherwise, replace 'ffi' with 'ff'
        return word.replace("ffi", "ff")
    
    # Apply the regex substitution with the custom replacement function
    fixed_text = re.sub(pattern, replace_ffi, text)
    
    return fixed_text
