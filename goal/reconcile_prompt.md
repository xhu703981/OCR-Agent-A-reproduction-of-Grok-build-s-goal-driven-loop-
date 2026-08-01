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
- Prefer clearer negatives (local safety) over abstract purity.
- Drop only: vague / global-swap / no-op / pure unique-name-only rules.
- Keep **many** useful rules: at most **12** active rules (discovery > tiny perfect set).
- Do not invent rules absent from the pack; you may only merge/drop/tighten.

## Output (Markdown only)

# Rule pack

## <rule_id>
- **precondition**:
- **transform**:
- **negative examples**:
- **priority**: high | med | low

## Notes
- bullets: what merged/dropped and why (esp. safety drops)

No chat. Each distinct pattern once only.
