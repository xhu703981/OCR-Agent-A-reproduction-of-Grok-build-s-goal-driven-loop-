"""
Light helpers for goal runtime: corpus smoke + optional OCRoscope diagnostics.

Checklist auto-tick is minimal (plan Task checklist, never unchecks).
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "goal" / "plan.md"
MANIFEST_PATH = ROOT / "rules" / "manifest.json"
APPLY_ALL = ROOT / "rules" / "apply_all.py"
RULES_DIR = ROOT / "rules"


def _manifest_rules() -> list[str]:
    if not MANIFEST_PATH.is_file():
        return []
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    rules = data.get("rules") if isinstance(data, dict) else None
    return list(rules) if isinstance(rules, list) else []


def _load_apply():
    if not APPLY_ALL.is_file() or not _manifest_rules():
        return None
    try:
        spec = importlib.util.spec_from_file_location("apply_all", APPLY_ALL)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def corpus_smoke(max_lines: int = 80) -> tuple[int, int]:
    """Stratified sample: (changed, scanned)."""
    from sample_data import load_train

    mod = _load_apply()
    if mod is None:
        return 0, 0
    rows = load_train()
    if not rows:
        return 0, 0
    if len(rows) > max_lines:
        step = max(1, len(rows) // max_lines)
        rows = [rows[i * step] for i in range(max_lines)]
    changed = scanned = 0
    for rec in rows:
        text = rec.get("text") or ""
        if not text:
            continue
        scanned += 1
        try:
            if mod.fix_text(text) != text:
                changed += 1
        except Exception:
            continue
    return changed, scanned


def scan_ocr_worse(*, max_lines: int | None = None, blame: bool = False) -> dict:
    """
    Diagnostic only (not an L0 hard gate): among changed train lines,
    count OCRoscope quality drops.
    """
    from sample_data import load_train
    from eval.score import score_text

    mod = _load_apply()
    rules = _manifest_rules()
    out: dict = {
        "n_scanned": 0,
        "n_changed": 0,
        "n_worse": 0,
        "n_improved": 0,
        "n_same": 0,
        "blame_rules": [],
        "gap_lines": [],
        "ok": True,
    }
    if mod is None or not rules:
        return out

    rows = load_train()
    if max_lines is not None and max_lines > 0 and len(rows) > max_lines:
        step = max(1, len(rows) // max_lines)
        rows = [rows[i * step] for i in range(max_lines)]

    worse_ids: list[str] = []
    for rec in rows:
        text = rec.get("text") or ""
        if not text:
            continue
        out["n_scanned"] += 1
        try:
            fixed = mod.fix_text(text)
        except Exception:
            continue
        if fixed == text:
            continue
        out["n_changed"] += 1
        sid = rec.get("id") or "x"
        sb = score_text(text, sid=sid + ":b")
        sa = score_text(fixed, sid=sid + ":a")
        if not (sb["ok"] and sa["ok"]):
            continue
        dq = float(sa["ocr_quality"]) - float(sb["ocr_quality"])
        if dq < -0.01:
            out["n_worse"] += 1
            worse_ids.append(sid)
        elif dq > 0.01:
            out["n_improved"] += 1
        else:
            out["n_same"] += 1

    out["ok"] = out["n_worse"] == 0

    if blame and worse_ids and rules:
        rule_mods = []
        for rid in rules:
            p = RULES_DIR / f"{rid}.py"
            if not p.is_file():
                continue
            try:
                spec = importlib.util.spec_from_file_location(rid, p)
                m = importlib.util.module_from_spec(spec)
                assert spec.loader
                spec.loader.exec_module(m)
                rule_mods.append((rid, m))
            except Exception:
                continue
        by_id = {r["id"]: r["text"] for r in load_train()}
        counts: dict[str, int] = {rid: 0 for rid, _ in rule_mods}
        for sid in worse_ids[:40]:
            t = by_id.get(sid)
            if not t:
                continue
            for rid, m in rule_mods:
                try:
                    alone = m.fix_text(t)
                except Exception:
                    continue
                if alone == t:
                    continue
                sb = score_text(t, sid="b")
                sa = score_text(alone, sid="a")
                if (
                    sb["ok"]
                    and sa["ok"]
                    and float(sa["ocr_quality"]) < float(sb["ocr_quality"]) - 0.01
                ):
                    counts[rid] = counts.get(rid, 0) + 1
        ranked = sorted(counts.items(), key=lambda x: -x[1])
        out["blame_rules"] = [rid for rid, c in ranked if c > 0][:6]
    return out


def first_unchecked(plan_path: Path = PLAN_PATH) -> str | None:
    if not plan_path.is_file():
        return None
    text = plan_path.read_text(encoding="utf-8")
    m = re.search(r"(?im)^#{1,6}\s*task checklist\s*$", text)
    if not m:
        return None
    body = text[m.end() :]
    cut = re.search(r"(?m)^#{1,6}\s+\S", body)
    if cut:
        body = body[: cut.start()]
    for line in body.splitlines():
        mm = re.match(r"^\s*[-*+]\s+\[\s\]\s+(.+)$", line)
        if mm:
            return mm.group(1).strip()
    return None


def reconcile_checklist(plan_path: Path = PLAN_PATH) -> list[str]:
    """No-op auto-tick stub (plan checklist is static). Kept for runtime API."""
    return []
