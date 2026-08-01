# Plan: Build a deterministic Python library to clean common OCR artifacts in English book text

## North star
A library of useful, deterministic scripts that improve OCR text readability for English books — **many safe local fixes**, not a tiny ultra-abstract set.

## Acceptance criteria
- Scripts fix OCR artifacts with **local safety**: repair the target pattern without introducing **obvious new errors** elsewhere (clean prose, currency, intentional hyphens, scholarly abbreviations when possible)
- Narrow or focused rules are fine when negative examples hold; blind global char swaps are not
- Scripts are deterministic (not LLM rewrite at apply time)
- Prefer **more shipped working rules** with real corpus effect over a tiny perfect library
- Residual unfixed cases are OK; **obvious collateral damage** is the main failure mode (judged qualitatively + CASES/smoke/critics — **not** a hard `n_worse==0` OCRoscope gate)

## Work phases
1. Collect and analyze OCR error samples
2. Mine many fixable patterns from samples (batch = evidence; allow focused local rules)
3. Write and test scripts; gate on CASES (esp. negatives) + smoke
4. Validate scripts on a local corpus (reports optional; not a hard score gate)
5. Package and document scripts

## Verification plan
- Run scripts on a local corpus
- Check sample lines for accuracy and **no obvious new errors**
- CASES negatives + known smoke false-positives (e.g. currency `1s.`, `well-known`)
- Panel/critics may cite damage; do **not** require OCRoscope `n_worse==0`
- Log edge cases and refine scripts

## Safety rules
- Deterministic only (regex/rules/algorithms OK; no LLM rewrite at apply time)
- Prefer precision / under-fix when unsure
- Avoid damaging clean text / inventing missing content
- Do not attempt full math recovery or multi-language cleanup

## Non-goals
- Re-OCR from images
- LLM rewriting every page
- Perfect math restoration
- Multi-language / product UI
- Hard zero OCRoscope-worse gating

## Task checklist
- [x] Collect OCR error samples
- [x] Categorize error types
- [x] Write substitution rules
- [x] Write spacing and punctuation rules
- [x] Write hyphenation and word split rules
- [x] Test scripts on local corpus
- [x] Validate accuracy and readability
- [x] Package and document scripts
