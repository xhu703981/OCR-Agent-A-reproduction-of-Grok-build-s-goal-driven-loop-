You propose **only a delta** to the current OCR rule pack, based on a new sample batch.

## Global objective
{OBJECTIVE}

## Constraints
### Acceptance criteria
{ACCEPTANCE}

### Safety
{SAFETY}

### Non-goals
{NON_GOALS}

## Current rule pack (index — already accepted)
{PACK_INDEX}

## New batch
{BATCH}

## Rules
1. Propose **delta only**: `add` new rules, `refine` existing ids, or `skip` if nothing new.
2. Discover patterns **from this batch only** — do not invent a fixed category list or copy generic OCR taxonomies.
3. Do not restate the whole pack. Do not rediscover rules already covered unless refining.
4. Every add/refine needs a **quote from this batch** + **precondition** + **negative examples**.
5. Forbidden: global single-char swaps (all 0→O, all 1→I, …). Context-conditioned only.
6. At most **4** delta items.

## Output (Markdown only)

# Delta

## Add
### <new_rule_id>
- **precondition**:
- **transform**:
- **negative examples**:
- **evidence**: snippet_id + "quote"
- **priority**: high | med | low

## Refine
### <existing_rule_id>
- **change**: what to tighten/loosen
- **precondition**: (updated full)
- **transform**: (updated full)
- **negative examples**:
- **evidence**: snippet_id + "quote"
- **priority**:

## Skip
- one line why nothing (or nothing major) to add

No chat. No full pack dump.
