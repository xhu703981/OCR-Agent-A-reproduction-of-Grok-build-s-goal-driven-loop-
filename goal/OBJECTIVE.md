# Global Goal

Ship a **small library of simple deterministic Python fix scripts** for common OCR artifacts in English book text — the kind of fixes that regex / light rules can handle — with **clear improvement over raw OCR**, not a perfect cleaner.

## Success bar

- **Do what code can do**: for common artifacts that regex / light algorithms can fix
  (confusables in context, ligature *glyphs*, junk runs, light hyphen/line joins, quotes, …),
  mine them and ship working scripts — *we did what we could with code*.
- **Not** “fix every OCR error” (vision, layout, math semantics, full rewrite are out).
- **Not** “ship any non-empty library” — easy code-wins left on the table count as incomplete.
- Residual errors that *need* non-code approaches are OK; unfixed *code-easy* classes are not.

## Approach

- Mine issues from **samples** (AI can help).
- Ship fixes as **reusable scripts** (regex / rules / light algorithms), not LLM rewrite of the full corpus.
- Prefer precision over aggressive cleanup; skip when unsure.
- Optional: smoke on a larger local slice when available.

## Non-goals

- Re-OCR from images
- LLM rewriting every page
- Perfect math restoration
- Multi-language / product UI
- Exhaustive holdout certification or zero false positives
