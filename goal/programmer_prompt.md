Implement ONE OCR cleanup rule as a single Python module (one rule = one program).

## Rule id
{RULE_ID}

## Spec from pack
{RULE_BODY}

## Optional real OCR snippets (use for CASES if relevant)
{SAMPLES}

## Module contract (required)
```python
RULE_ID = "{RULE_ID}"

CASES: list[tuple[str, str]] = [
    # at least 3 cases:
    # - 2 positive (input with the bug -> fixed)
    # - 1 negative (clean / lookalike that must NOT change)
]

def fix_text(text: str) -> str:
    ...
    return text
```

## Requirements
- Stdlib only (`re` ok). No files/network/subprocess.
- Deterministic. Prefer under-fix when unsure.
- Implement the **spirit** of the pack rule, but make preconditions **machine-checkable**.
- Forbidden: replace every digit/letter globally; forbidden no-op transforms.
- Avoid known false positives: do not turn currency `1s.` into `15.`; do not join `word- that` mid sentence unless there is a real line-break hyphenation.
- Keep logic short and readable.

## Output
Python source only. No markdown fences. No chat.
