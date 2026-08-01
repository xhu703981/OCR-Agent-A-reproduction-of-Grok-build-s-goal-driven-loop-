# ocr-agent

Local OCR post-processing: **mine rules from book snippets → program deterministic Python fixes → apply + eval**.

## Data flow

```
HF Institutional Books
        │  download_sample.py
        ▼
data/corpus/books_small.jsonl
        │  (same script builds snippets)
        ▼
data/sample/train.jsonl  (+ holdout.jsonl)
        │  sample_data.load_train()
        ▼
┌───────────────────────────────────────────┐
│  goal_runtime.py  (pick worker by state)  │
│                                           │
│  pack        run_pack_turns.py            │
│              → goal/rule_pack.md          │
│                                           │
│  implementer run_implementer.py           │
│              tools: program_pack / write  │
│              → rules/*.py + manifest.json │
│                                           │
│  verify L0   thick library?               │
│  L1 panel    goal_judge.py (skeptics)     │
│  strategist  same-gap stall unstick       │
└───────────────────────────────────────────┘
        │
        ▼
rules/apply_all.py  (manifest order only)
        │
        ▼
eval/run_eval.py  (OCRoscope before/after — diagnostic)
```

## Entry points

| Command | Role |
|--------|------|
| `python download_sample.py` | Stream HF books → corpus + train/holdout (edit `MAX_BOOKS` in file) |
| `python goal_runtime.py` | Full goal loop (set `FRESH` in file if remine) |
| `python run_pack_turns.py` | Pack mining only |
| `python run_implementer.py` | Tool-loop implementer only |
| `python run_programmer.py` | Pack→modules (also a tool of implementer) |
| `python rules/apply_all.py` | Smoke demo |
| `python eval/run_eval.py` | Train OCRoscope report |

## Contracts

- Snippets: `{"id": str, "text": str}` per jsonl line (`sample_data.py`).
- Rule module: `RULE_ID`, `CASES`, `fix_text(text) -> str`.
- Only `rules/manifest.json` rules run at apply time.
- Goal safety: **no obvious new errors elsewhere** (prompts + CASES + critics) — not a hard `n_worse==0` gate.

## Layout

```
data/           corpora + samples (gitignored)
goal/           OBJECTIVE, plan, prompts, rule_pack, state
rules/          active modules + apply_all + manifest
eval/           score + run_eval
goal_runtime.py orchestrator
```

## Config

- API: `.env` with `GROK_API=...` (and `HF_TOKEN` for download).
- Models: edit constants in `ollama_chat.py`, `run_programmer.py`, `goal_judge.py`, `run_implementer.py`.
