"""Download a small OCR sample from institutional-books-1.0 into data/."""

import json
import random
import re
from pathlib import Path

from datasets import load_dataset

ROOT = Path(__file__).resolve().parent
DATASET = "institutional/institutional-books-1.0"

OCR_MIN, OCR_MAX = 78, 90
# enough for multi-epoch mining: epochs * 3 turns * batch_n snippets
MAX_BOOKS = 36
SNIPPETS_PER_BOOK = 10
PAGES_PER_BOOK = 30
MIN_CHARS, MAX_CHARS = 280, 900
SEED = 42


def pages_of(row):
    for key in ("text_by_page_gen", "text_by_page_src"):
        v = row.get(key)
        if isinstance(v, list):
            pages = [p.strip() for p in v if isinstance(p, str) and p.strip()]
            if pages:
                return pages
    return []


def windows(text):
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


def sample_snippets(pages, n, rng):
    cands = []
    for page in pages:
        for para in re.split(r"\n\s*\n", page):
            para = re.sub(r"\s+", " ", para).strip()
            if len(para) >= MIN_CHARS:
                cands.extend(windows(para))
    if not cands:
        return []
    return cands if len(cands) <= n else rng.sample(cands, n)


def main():
    rng = random.Random(SEED)
    ds = load_dataset(DATASET, split="train", streaming=True)

    books = []
    for row in ds:
        if (row.get("language_gen") or "").lower() not in ("", "eng"):
            continue  # only English books
        score = row.get("ocr_score_gen")
        if score is None or not (OCR_MIN <= int(score) <= OCR_MAX):  # too low: unfixable OCR, too high: already good
            continue
        pages = pages_of(row)
        if len(pages) < 3:
            continue
        barcode = str(row.get("barcode_src") or row.get("barcode") or "")
        if not barcode:
            continue

        if len(pages) > PAGES_PER_BOOK:
            idx = list(range(5)) + rng.sample(
                range(5, len(pages)), k=min(PAGES_PER_BOOK - 5, len(pages) - 5)
            )
            idx = sorted(set(idx))
            keep = [pages[i] for i in idx]
        else:
            idx = list(range(len(pages)))
            keep = pages

        snips = sample_snippets(keep, SNIPPETS_PER_BOOK, rng)
        if not snips:
            continue

        books.append(
            {
                "barcode": barcode,
                "title": row.get("title_src") or "",
                "ocr_score_gen": int(score),
                "ocr_score_src": row.get("ocr_score_src"),
                "page_indices_kept": idx,
                "pages": keep,
                "snippets": snips,
            }
        )
        print(f"+ {len(books)}/{MAX_BOOKS} {barcode} score={score}")
        if len(books) >= MAX_BOOKS:
            break

    corpus_dir = ROOT / "data" / "corpus"
    sample_dir = ROOT / "data" / "sample"
    corpus_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)

    with (corpus_dir / "books_small.jsonl").open("w", encoding="utf-8") as f:
        for b in books:
            f.write(
                json.dumps(
                    {
                        "id": b["barcode"],
                        "barcode": b["barcode"],
                        "title": b["title"],
                        "ocr_score_gen": b["ocr_score_gen"],
                        "pages": b["pages"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    # Pipeline samples: id + text only (metadata stays in books_small / download_meta).
    snippets = []
    for b in books:
        for i, t in enumerate(b["snippets"]):
            snippets.append({"id": f"{b['barcode']}:s{i}", "text": t})
    rng.shuffle(snippets)
    n_hold = max(8, len(snippets) // 5)
    holdout, train = snippets[:n_hold], snippets[n_hold:]

    from sample_data import dump_snippets

    dump_snippets(sample_dir / "train.jsonl", train)
    dump_snippets(sample_dir / "holdout.jsonl", holdout)
    dump_snippets(sample_dir / "all_snippets.jsonl", train + holdout)

    meta = {
        "dataset": DATASET,
        "ocr_score_range": [OCR_MIN, OCR_MAX],
        "n_books": len(books),
        "n_train": len(train),
        "n_holdout": len(holdout),
        "books": [
            {"barcode": b["barcode"], "title": b["title"], "ocr_score_gen": b["ocr_score_gen"]}
            for b in books
        ],
    }
    (ROOT / "data" / "download_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"done: {len(books)} books, {len(train)} train, {len(holdout)} holdout")


if __name__ == "__main__":
    main()
