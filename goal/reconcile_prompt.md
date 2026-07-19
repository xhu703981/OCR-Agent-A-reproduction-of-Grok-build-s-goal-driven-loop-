You **reconcile** an OCR rule pack after several mining turns.

## Objective
{OBJECTIVE}

## Safety / non-goals
{SAFETY}

{NON_GOALS}

## Current pack (full)
{PACK}

## Task
- Deduplicate near-identical rules (e.g. `foo` and `foo_with_context` → **one** rule only).
- After merge, the duplicate id must **not** appear again.
- Prefer tighter precondition + clearer negatives.
- Drop vague / global-swap / empty-punctuation rules.
- Keep at most **6** active rules.
- Do not invent rules absent from the pack.

## Output (Markdown only)

# Rule pack

## <rule_id>
- **precondition**:
- **transform**:
- **negative examples**:
- **priority**: high | med | low

## Notes
- bullets: what merged/dropped

No chat. Each distinct pattern once only.
