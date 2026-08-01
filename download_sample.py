"""Download English book OCR samples from institutional-books-1.0.

  python download_sample.py

Writes:
  data/corpus/books_small.jsonl
  data/sample/{train,holdout,all_snippets}.jsonl
  data/download_meta.json

Needs HF_TOKEN in .env (gated dataset). Assumes paths/network work.
"""

from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv()

DATASET = "institutional/institutional-books-1.0"
OCR_MIN, OCR_MAX = 60, 88
MAX_BOOKS = 300
SNIPPETS_PER_BOOK = 10
PAGES_PER_BOOK = 20
MIN_CHARS, MAX_CHARS = 280, 900
SEED = 48


def _hf_token() -> str | None:
    return (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    )


def pages_of(row: dict) -> list[str]:
    for key in ("text_by_page_gen", "text_by_page_src"):
        v = row.get(key)
        if isinstance(v, list):
            pages = [p.strip() for p in v if isinstance(p, str) and p.strip()]
            if pages:
                return pages
    return []


def windows(text: str) -> list[str]:
    words = text.split()
    out, i = [], 0
    while i < len(words):
        chunk, n, j = [], 0, i
        while j < len(words):
            w = words[j]
            add = len(w) + (1 if chunk else 0)
            if n + add > MAX_CHARS:
                break
            chunk.append(w)
            n += add
            j += 1
        if n >= MIN_CHARS:
            out.append(" ".join(chunk))
        i = i + 1 if j == i else i + max(1, (j - i) // 2)
    return out


def sample_snippets(pages: list[str], n: int, rng: random.Random) -> list[str]:
    cands: list[str] = []
    for page in pages:
        for para in re.split(r"\n\s*\n", page):
            para = re.sub(r"\s+", " ", para).strip()
            if len(para) >= MIN_CHARS:
                cands.extend(windows(para))
    if not cands:
        return []
    return cands if len(cands) <= n else rng.sample(cands, n)


def _keep_pages(pages: list[str], rng: random.Random) -> list[str]:
    if len(pages) <= PAGES_PER_BOOK:
        return pages
    head = list(range(min(5, len(pages))))
    rest = list(range(5, len(pages)))
    k = min(PAGES_PER_BOOK - len(head), len(rest))
    pick = head + (rng.sample(rest, k) if k > 0 else [])
    return [pages[i] for i in sorted(set(pick))]


def book_from_row(row: dict, rng: random.Random) -> dict | None:
    """Return a book dict if row matches filters; None to skip."""
    lang = (row.get("language_gen") or "").lower()
    if lang not in ("", "eng"):
        return None
    score = int(row["ocr_score_gen"])
    if not (OCR_MIN <= score <= OCR_MAX):
        return None
    pages = pages_of(row)
    if len(pages) < 3:
        return None
    barcode = str(row.get("barcode_src") or row.get("barcode") or "")
    if not barcode:
        return None
    keep = _keep_pages(pages, rng)
    snips = sample_snippets(keep, SNIPPETS_PER_BOOK, rng)
    if not snips:
        return None
    return {
        "barcode": barcode,
        "ocr_score_gen": score,
        "pages": keep,
        "snippets": snips,
    }


def write_corpus(books: list[dict]) -> None:
    path = ROOT / "data" / "corpus" / "books_small.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for b in books:
            f.write(
                json.dumps(
                    {
                        "id": b["barcode"],
                        "barcode": b["barcode"],
                        "ocr_score_gen": b["ocr_score_gen"],
                        "pages": b["pages"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )


def write_samples(books: list[dict], rng: random.Random) -> tuple[int, int]:
    from sample_data import dump_snippets

    sample_dir = ROOT / "data" / "sample"
    sample_dir.mkdir(parents=True, exist_ok=True)
    snippets: list[dict[str, str]] = []
    for b in books:
        snips = b.get("snippets") or sample_snippets(
            b["pages"], SNIPPETS_PER_BOOK, rng
        )
        for i, t in enumerate(snips):
            snippets.append({"id": f"{b['barcode']}:s{i}", "text": t})
    rng.shuffle(snippets)
    n_hold = max(40, len(snippets) // 5)
    holdout, train = snippets[:n_hold], snippets[n_hold:]
    dump_snippets(sample_dir / "train.jsonl", train)
    dump_snippets(sample_dir / "holdout.jsonl", holdout)
    dump_snippets(sample_dir / "all_snippets.jsonl", train + holdout)
    return len(train), len(holdout)


def write_meta(books: list[dict], n_train: int, n_holdout: int) -> None:
    meta = {
        "dataset": DATASET,
        "ocr_score_range": [OCR_MIN, OCR_MAX],
        "n_books": len(books),
        "n_train": n_train,
        "n_holdout": n_holdout,
        "target_books": MAX_BOOKS,
        "snippets_per_book": SNIPPETS_PER_BOOK,
        "pages_per_book": PAGES_PER_BOOK,
        "books": [
            {"barcode": b["barcode"], "ocr_score_gen": b["ocr_score_gen"]}
            for b in books
        ],
    }
    (ROOT / "data" / "download_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> None:
    from datasets import load_dataset

    rng = random.Random(SEED)
    token = _hf_token()
    print(
        f"download {DATASET} token={'yes' if token else 'no'} "
        f"score=[{OCR_MIN},{OCR_MAX}] target={MAX_BOOKS}",
        flush=True,
    )

    ds = load_dataset(
        DATASET,
        split="train",
        streaming=True,
        token=token,
    )

    books: list[dict] = []
    seen: set[str] = set()
    for row in ds:
        if len(books) >= MAX_BOOKS:
            break
        b = book_from_row(row, rng)
        if b is None or b["barcode"] in seen:
            continue
        seen.add(b["barcode"])
        books.append(b)
        print(
            f"+ {len(books)}/{MAX_BOOKS} {b['barcode']} score={b['ocr_score_gen']}",
            flush=True,
        )

    write_corpus(books)
    n_train, n_hold = write_samples(books, rng)
    write_meta(books, n_train, n_hold)
    print(
        f"done: {len(books)} books, {n_train} train, {n_hold} holdout",
        flush=True,
    )


if __name__ == "__main__":
    main()
