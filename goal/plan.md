# Plan: Build a deterministic Python library to clean common OCR artifacts in English book text

## North star
A library of precise, reusable scripts that improve OCR text readability and quality for English books.

## Acceptance criteria
- Scripts fix common OCR artifacts with **context-aware** rules (not blind global char swaps)
- Scripts are deterministic, not LLM rewrite at apply time
- Scripts are checked on holdout / larger corpus for safety
- Residual unfixed cases are OK; false positives should be rare

## Work phases
1. Collect and analyze OCR error samples
2. Mine patterns from samples (no fixed category list)
3. Write and test scripts for observed patterns
4. Validate scripts on a local corpus
5. Package and document scripts

## Verification plan
- Run scripts on a local corpus of 10+ books
- Manually check 100+ sample lines for accuracy
- Compare pre- and post-cleanup readability
- Log edge cases and refine scripts

## Safety rules
- Scripts must be deterministic (regex/rules/algorithms OK; no LLM rewrite at apply time)
- Prefer precision; skip when unsure
- Avoid damaging clean text / inventing missing content
- Do not attempt full math recovery or multi-language cleanup

## Non-goals
- Re-OCR from images
- LLM rewriting every page
- Perfect math restoration
- Multi-language / product UI

## Task checklist
- [x] Collect OCR error samples
- [x] Categorize error types
- [x] Write substitution rules
- [x] Write spacing and punctuation rules
- [x] Write hyphenation and word split rules
- [x] Test scripts on local corpus
- [x] Validate accuracy and readability
- [x] Package and document scripts
