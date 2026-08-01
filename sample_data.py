"""
Sample snippets for the OCR pipeline.

Contract: each jsonl line is exactly {"id": str, "text": str}.
We assume paths exist and data is clean — fix data/paths manually if not.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAMPLE_DIR = ROOT / "data" / "sample"
TRAIN_PATH = SAMPLE_DIR / "train.jsonl"
HOLDOUT_PATH = SAMPLE_DIR / "holdout.jsonl"
ALL_PATH = SAMPLE_DIR / "all_snippets.jsonl"


def load_snippets(path: Path) -> list[dict[str, str]]:
    """Load jsonl → list of {id, text}. Raises if path missing or a line is bad."""
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        rows.append({"id": rec["id"], "text": rec["text"]})
    return rows


def load_train() -> list[dict[str, str]]:
    return load_snippets(TRAIN_PATH)


def load_holdout() -> list[dict[str, str]]:
    return load_snippets(HOLDOUT_PATH)


def dump_snippets(path: Path, rows: list[dict[str, str]]) -> None:
    """Write id + text per line. Parent dir must already exist."""
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"id": r["id"], "text": r["text"]}, ensure_ascii=False) + "\n")


def format_batch_md(
    rows: list[dict[str, str]],
    *,
    max_chars: int | None = None,
    start: int = 0,
    n: int | None = None,
) -> tuple[str, list[str]]:
    """
    Build markdown for LLM prompts. Returns (markdown, ids).
    """
    if n is None:
        chunk = rows[start:]
    else:
        chunk = [rows[(start + i) % len(rows)] for i in range(n)]
    parts: list[str] = []
    ids: list[str] = []
    for r in chunk:
        t = r["text"]
        if max_chars is not None and len(t) > max_chars:
            t = t[:max_chars] + "…"
        parts.append(f"### {r['id']}\n{t}")
        ids.append(r["id"])
    return "\n\n".join(parts), ids
