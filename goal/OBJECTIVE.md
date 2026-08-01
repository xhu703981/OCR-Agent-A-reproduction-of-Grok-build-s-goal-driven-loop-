# Global Goal

Ship a **growing library of simple deterministic Python fix scripts** for common OCR artifacts in English book text — the kind of fixes that regex / light rules can handle — with **clear improvement over raw OCR**, not a perfect cleaner.

## Success bar

- **Discover many useful fixes**: mine and ship as many **safe, code-fixable** rules as practical from the samples.
- **Core of "generality" = local safety**: a fix is good when it repairs the intended local artifact **without introducing obvious new errors elsewhere** (other tokens, clean prose, currency, intentional hyphens, bibliography/dictionary notation, etc.).
  - Prefer under-fix when unsure.
  - Narrow / context-limited rules are **welcome** if negatives protect clean text.
  - Ultra-abstract "must work on every book" is **not** required.
  - **Do not hard-gate on OCRoscope score drops**; local safety is a goal property judged from evidence (CASES negatives, smoke, critic, panel), not `n_worse == 0`.
- **Do what code can do**: confusables in context, ligature glyphs, junk runs, hyphen/line joins, quotes, light punctuation, …
- **Not** “fix every OCR error” (vision, layout, math semantics, full rewrite are out).
- Residual unfixed OCR is OK.

## Approach

- Samples are **evidence** that a fix class exists; also allow **focused local patterns** when they recur or are classic OCR.
- Ship fixes as **reusable scripts** (regex / rules / light algorithms), not LLM rewrite of the full corpus.
- Bias to ship rules that pass mechanical safety (CASES + smoke gates) and look safe under critic/panel review.
- Optional: smoke / OCRoscope reports for diagnosis only.

## Non-goals

- Re-OCR from images
- LLM rewriting every page
- Perfect math restoration
- Multi-language / product UI
- Exhaustive holdout certification or zero residual errors
- Demanding every mined pack name ship before counting progress
- Hard zero OCRoscope-worse as a completion gate
