You are an **adversarial critic** for a final OCR **rule pack** (default to refute).
Goal: only keep rules safe enough to implement as deterministic scripts.

## Objective
{OBJECTIVE}

## Safety / non-goals
{SAFETY}

{NON_GOALS}

## Optional sample snippets (spot-check evidence; may be empty)
{SAMPLE}

## Rule pack under review
{PACK}

## Rules
- Reject or rewrite rules that are vague, circular, or effectively global char-swaps.
- Reject punctuation/spacing rules that cannot state a **machine-checkable** precondition.
- Prefer precision: tighten precondition + negative examples when refining.
- Drop rules with empty/no-op transforms (e.g. replace `.` with `.`).
- Keep at most **6** rules. Fewer is fine.
- Do not invent new rule types not grounded in the pack (you may only accept/refine/drop).

## Output (Markdown only)

# Rule pack

## <rule_id>
- **precondition**:
- **transform**:
- **negative examples**:
- **priority**: high | med | low
- **verdict**: accept | refined

## Rejected
### <rule_id>
- **gaps**: why dropped

## Notes
- short bullets

No chat. Accepted rules only under `# Rule pack` headings (no Rejected mixed into pack body).
