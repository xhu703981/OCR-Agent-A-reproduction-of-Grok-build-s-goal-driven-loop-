# Rule pack

## confusable_digit_in_number
- **precondition**: character is a digit-like letter within a numeric context (e.g., "183" with "x" or "kя")
- **transform**: replace digit-like letters with their numeric counterparts
- **negative examples**: "183" with "x" in a non-numeric context
- **priority**: high

## repeated_garbage_run
- **precondition**: a sequence of repeated characters (e.g., ".......", "----", "####") appears in a non-numeric context, is surrounded by word boundaries, and is not part of a mathematical expression or technical term
- **transform**: replace with a single instance of the character
- **negative examples**: "----" in "4----5", "####" in "####", "...." in "...."
- **priority**: high

## ligature_to_fi
- **precondition**: ligature "ﬃ" or "ﬁ" appears in a context where "fi" is expected (e.g., in a word or phrase, especially in technical or historic contexts)
- **transform**: replace ligature "ﬃ" with "fi", replace ligature "ﬁ" with "fi"
- **negative examples**: "ﬃi" (valid ligature), "ﬁ" in a title or book name, "ﬁ" in a word where "fi" is not expected
- **priority**: med

## confusable_letter_in_number
- **precondition**: character is a letter-like symbol within a numeric context (e.g., "x" in "183x", "k" in "kя", or "i" in "183i"), and the surrounding characters are digits or mathematical symbols
- **transform**: replace letter-like symbols with their numeric counterparts where contextually appropriate (e.g., "i" → "1", "k" → "k", "x" → "x")
- **negative examples**: "x" in "x is a variable", "k" in "k is a constant", "i" in "i is the imaginary unit"
- **priority**: high

## ligature_to_f
- **precondition**: ligature "ﬃ" appears in a context where "f" is expected (e.g., in a word or phrase), and is followed by a lowercase "i"
- **transform**: replace ligature "ﬃ" with "fi"
- **negative examples**: "ﬃi" (valid ligature), "ﬃ" (valid ligature), "fii" (valid spelling)
- **priority**: med

## quote_normalization
- **precondition**: quote characters are inconsistent (e.g., "«", "»", "“", "”", "'", '"') and appear in a narrative or dialogue context, not in titles or technical terms
- **transform**: normalize to a single quote style (e.g., "“”" → "\"")
- **negative examples**: "«»" in a title, "“”" in a technical term, "''" in a dialogue
- **priority**: med
