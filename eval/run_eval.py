"""
Eval pipeline: OCRoscope before/after apply_all on a sample split.

  python eval/run_eval.py

Defaults: train.jsonl (first-round protocol). Edit constants below.
Writes eval/results/{summary.json, details.jsonl}.
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sample_data import load_holdout, load_train  # noqa: E402
from eval.score import score_text  # noqa: E402

# --- config ---
SPLIT = "train"  # "train" | "holdout"
APPLY_ALL = ROOT / "rules" / "apply_all.py"
OUT_DIR = ROOT / "eval" / "results"
# Optional cap for smoke tests; None = all
MAX_N: int | None = None


def _load_fix():
    spec = importlib.util.spec_from_file_location("apply_all", APPLY_ALL)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.fix_text


def _mean(xs: list[float]) -> float:
    return float(statistics.mean(xs)) if xs else 0.0


def _median(xs: list[float]) -> float:
    return float(statistics.median(xs)) if xs else 0.0


def run() -> dict:
    rows = load_train() if SPLIT == "train" else load_holdout()
    if MAX_N is not None:
        rows = rows[:MAX_N]
    fix = _load_fix()

    details: list[dict] = []
    for r in rows:
        raw = r["text"]
        fixed = fix(raw)
        b = score_text(raw, sid=r["id"] + ":before")
        a = score_text(fixed, sid=r["id"] + ":after")
        scorable = bool(b["ok"] and a["ok"])
        dq = (
            a["ocr_quality"] - b["ocr_quality"]
            if scorable
            else None
        )
        dn = a["nonchar"] - b["nonchar"] if scorable else None
        details.append(
            {
                "id": r["id"],
                "changed": fixed != raw,
                "scorable": scorable,
                "before_quality": b["ocr_quality"],
                "after_quality": a["ocr_quality"],
                "delta_quality": dq,
                "before_nonchar": b["nonchar"],
                "after_nonchar": a["nonchar"],
                "delta_nonchar": dn,
                "n_chars_raw": len(raw),
                "n_chars_fixed": len(fixed),
            }
        )

    scored = [d for d in details if d["scorable"]]
    deltas_q = [d["delta_quality"] for d in scored]
    deltas_n = [d["delta_nonchar"] for d in scored]
    n = len(details)
    n_scored = len(scored)
    n_changed = sum(1 for d in details if d["changed"])
    n_improved = sum(1 for d in scored if d["delta_quality"] > 0)
    n_worse = sum(1 for d in scored if d["delta_quality"] < 0)
    n_same = n_scored - n_improved - n_worse

    summary = {
        "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "split": SPLIT,
        "n": n,
        "n_scored": n_scored,
        "n_unscorable": n - n_scored,
        "n_changed": n_changed,
        "change_rate": n_changed / n if n else 0.0,
        "ocr_quality": {
            "mean_before": _mean([d["before_quality"] for d in scored]),
            "mean_after": _mean([d["after_quality"] for d in scored]),
            "mean_delta": _mean(deltas_q),
            "median_delta": _median(deltas_q),
            "n_improved": n_improved,
            "n_worse": n_worse,
            "n_same_score": n_same,
            "pct_improved": 100.0 * n_improved / n_scored if n_scored else 0.0,
            "pct_worse": 100.0 * n_worse / n_scored if n_scored else 0.0,
        },
        "nonchar": {
            "mean_before": _mean([d["before_nonchar"] for d in scored]),
            "mean_after": _mean([d["after_nonchar"] for d in scored]),
            "mean_delta": _mean(deltas_n),
            "median_delta": _median(deltas_n),
        },
        "apply_all": str(APPLY_ALL),
        "manifest": str(ROOT / "rules" / "manifest.json"),
        "data_meta": str(ROOT / "data" / "download_meta.json"),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (OUT_DIR / "details.jsonl").open("w", encoding="utf-8") as f:
        for d in details:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    print("=== OCRoscope eval ===")
    print(
        f"split={SPLIT} n={n} scored={n_scored} unscorable={n - n_scored} "
        f"changed={n_changed} ({100 * n_changed / n:.1f}%)"
    )
    q = summary["ocr_quality"]
    print(
        f"quality mean: {q['mean_before']:.2f} → {q['mean_after']:.2f} "
        f"(Δ {q['mean_delta']:+.2f}, median Δ {q['median_delta']:+.2f})"
    )
    print(
        f"improved={q['n_improved']} ({q['pct_improved']:.1f}%)  "
        f"worse={q['n_worse']} ({q['pct_worse']:.1f}%)  same_score={q['n_same_score']}"
    )
    print(f"wrote {OUT_DIR / 'summary.json'}")
    print(f"wrote {OUT_DIR / 'details.jsonl'}")
    return summary


if __name__ == "__main__":
    run()
