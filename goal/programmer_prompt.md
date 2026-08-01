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
    # - 2 positive (input with the bug -> fixed) — can be focused/local
    # - 1 negative (clean / lookalike that must NOT change) — LOCAL SAFETY
]

def fix_text(text: str) -> str:
    ...
    return text
```

## Requirements
- Stdlib only (`re` ok). No files/network/subprocess.
- Deterministic. Prefer under-fix when unsure.
- **Primary goal: local safety + context fit** — fix the intended OCR artifact in the right register; **do not change** negative CASES; do not damage currency `1s.`, intentional `well-known`, clean pronouns, ordinals, model names, etc.
- **Context matters**: the same glyph pattern can be correct OCR noise in modern prose and **wrong to "fix"** in music/lyrics (syllable hyphens), bibliography (`4to`, `8vo`), dictionaries (`adj.`, `cu.cm.`), or historical/OE spelling (`æ`, long-s). Prefer preconditions that **skip those contexts** when unsure.
- CASES: ≥2 positives from OCR-like **prose** (or the intended domain) **and** ≥1 negative that is a **lookalike in another context** (e.g. hyphen rule must leave `well-known` and lyric-like `be- hold` / `ma- dri` alone if your join is for broken line-words only).
- Narrow implementations are **fine**: small glyph maps, run collapsers, context-limited regex — as long as negatives + domain guards hold.
- Forbidden: replace every digit/letter globally with no context; forbidden pure identity no-op.
- Forbidden: whole-rule = only `text.replace("one unique book sentence", ...)`.
- Keep logic short and readable. **Ship a working, context-aware fix** over a perfect abstraction.

## Output
Python source only. No markdown fences. No chat.
