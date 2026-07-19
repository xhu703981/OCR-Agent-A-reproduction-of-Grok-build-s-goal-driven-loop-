You mine **precise, deterministic OCR fix proposals** from a batch of English book snippets.

## Global objective
{OBJECTIVE}

## Project constraints (from overall plan)
### Acceptance criteria
{ACCEPTANCE}

### Safety rules
{SAFETY}

### Non-goals
{NON_GOALS}

## Sample batch
{BATCH}

## Hard rules
1. **Evidence first.** Every observed issue MUST quote a short substring that actually appears in a listed snippet id. No quote → do not list it.
2. **No taxonomy parroting.** Discover issues from the batch only; do not invent fixes from a pre-set category list.
3. **No global single-char swaps.** Forbidden: replace every `0` with `O`, every `1` with `I`, etc. If confusion exists, the rule must be **context-conditioned**. State match preconditions and **negative examples**.
4. Prefer **high precision**. If you cannot state a safe precondition, put it under "Do not automate".
5. At most **5** proposals. No duplicates.

## Output (Markdown only)

# Fix proposals (draft)

## Observed issues
- `snippet_id`: "exact quote" — brief diagnosis

## Proposed scripts
### <short_name>
- **evidence**: snippet_id + quote
- **precondition**: when the rule fires (context)
- **transform**: what changes (pattern-level OK)
- **negative examples**: clean cases that must stay unchanged
- **priority**: high | med | low

## Do not automate (yet)
- ...

Stop after these sections. No chat.
