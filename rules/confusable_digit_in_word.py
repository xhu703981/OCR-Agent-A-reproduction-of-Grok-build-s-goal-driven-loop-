import re

RULE_ID = "confusable_digit_in_word"

CASES: list[tuple[str, str]] = [
    ("This is a test0word.", "This is a testOword."),
    ("Another example with 0 in the middle.", "Another example with O in the middle."),
    ("No change here 123 or 0.5", "No change here 123 or 0.5"),
]

def fix_text(text: str) -> str:
    # Regex pattern to find '0' surrounded by word characters
    pattern = r"(?<=\w)'0'(?=\w)"
    return re.sub(pattern, "'O'", text)

# Example usage
if __name__ == "__main__":
    for input_text, expected_output in CASES:
        result = fix_text(input_text)
        assert result == expected_output, f"Expected {expected_output}, but got {result}"
    print("All test cases passed.")
