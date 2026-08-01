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

## Core principle: many **safe local** fixes
Samples show real errors. Propose **as many implementable rules as you can** that:
1. Fix a clear OCR artifact when the precondition matches, and
2. **Do not introduce new errors** in other local contexts (state negative examples).

### What "good" means
- **Local safety > abstract purity.** A focused rule with solid negatives beats an empty pack.
- Prefer patterns that can fire on more than one surface form, but **small families / glyph maps / run collapsers** are fine.
- Evidence quotes justify the rule; the transform need not be a grand theory of OCR.

### Prefer these families (ids)
`confusable_*`, `ligature_*`, `junk_*` / `repeated_*`, `quote_*`, `hyphen_*` / line joins,
spacing / light punctuation — plus other clear OCR classes you can name in snake_case.

### Still avoid (self-reject before proposing)
- **Unsafe** transforms: global single-char swaps (all `0`→`O`, all `1`→`I`), money/`1s.` damage, joining intentional `well-known`.
- Pure **no-op** (`ct` → `ct`).
- Opaque ids: `R001`, `rule_1`, …
- Rules that only replace one **unique proper name / one full unique sentence** with no structural pattern — unless it is a pure glyph/class map.

### How to use the batch
1. Spot every recurring or classic OCR error type you can name.
2. Write machine-checkable **precondition** + **transform** + **negative examples**.
3. Cite one evidence quote per add.
4. Prefer **Add** over Skip when the fix is safe-local; only Skip if nothing safe remains.

## Rules
1. Propose **delta only**: `add` / `refine` / `skip`.
2. At most **6** delta items; **bias toward Add** when safe (more rules is good).
3. Every add/refine: **precondition** + **transform** + **negative examples** + batch **evidence** quote.
4. Forbidden: blind global single-char swaps. Context / run / glyph maps OK.
5. **Rule ids**: descriptive snake_case (`confusable_digit_in_number`, `ligature_fi`, `junk_dot_run`, …).

## Output (Markdown only)

# Delta

## Add
### <new_rule_id>
- **precondition**: when this local pattern is present
- **transform**: what to change (keep local; do not rewrite whole sentences)
- **negative examples**: clean lookalikes that must NOT change (local safety)
- **evidence**: snippet_id + "quote"
- **local_safety**: one line — what it refuses to touch
- **priority**: high | med | low

## Refine
### <existing_rule_id>
- **change**: tighten safety or broaden useful coverage
- **precondition**: (updated full)
- **transform**: (updated full)
- **negative examples**:
- **evidence**: snippet_id + "quote"
- **priority**:

## Skip
- one line only if truly nothing safe/new remains

No chat. No full pack dump.
