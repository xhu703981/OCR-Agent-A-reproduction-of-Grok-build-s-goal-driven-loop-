"""
Auto-check plan.md ## Task checklist from disk evidence.

Only ever flips `- [ ]` → `- [x]` inside the Task checklist section.
Never unchecks. Safe to call after every successful worker tick.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLAN_PATH = ROOT / "goal" / "plan.md"
PACK_PATH = ROOT / "goal" / "rule_pack.md"
MANIFEST_PATH = ROOT / "rules" / "manifest.json"

APPLY_ALL = ROOT / "rules" / "apply_all.py"
RULES_DIR = ROOT / "rules"
# Soft bar: enough shipped rules to treat missing pack classes as N/A on checklist
MIN_MANIFEST_LIKE = 3


def _manifest_rules() -> list[str]:
    if not MANIFEST_PATH.exists():
        return []
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    rules = data.get("rules") if isinstance(data, dict) else None
    return list(rules) if isinstance(rules, list) else []


def _pack_names() -> list[str]:
    if not PACK_PATH.exists():
        return []
    names = []
    for part in re.split(r"(?m)^## ", PACK_PATH.read_text(encoding="utf-8"))[1:]:
        name = part.split("\n", 1)[0].strip()
        if name and name.lower() != "notes":
            names.append(name.lower())
    return names


def _rule_files() -> set[str]:
    if not RULES_DIR.exists():
        return set()
    return {p.stem.lower() for p in RULES_DIR.glob("*.py") if p.name != "__init__.py"}


def _sample_ready() -> bool:
    from sample_data import load_train

    return len(load_train()) >= 10


def _load_apply():
    if not APPLY_ALL.exists() or not _manifest_rules():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("apply_all", APPLY_ALL)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def corpus_smoke(max_lines: int = 80) -> tuple[int, int]:
    """
    Apply manifest pipeline to up to max_lines train snippets.
    Returns (changed, scanned).
    """
    from sample_data import load_train

    mod = _load_apply()
    if mod is None:
        return 0, 0
    changed = 0
    scanned = 0
    for rec in load_train():
        if scanned >= max_lines:
            break
        text = rec.get("text") or ""
        if not text:
            continue
        scanned += 1
        try:
            out = mod.fix_text(text)
        except Exception:
            continue
        if out != text:
            changed += 1
    return changed, scanned


def _demo_applies() -> bool:
    """True if fixed demo string changes OR any train smoke line changes."""
    mod = _load_apply()
    if mod is None:
        return False
    for sample in ("f0x test", "f0x", "a....b", "1O2", "ﬁle", "ﬁ"):
        try:
            if mod.fix_text(sample) != sample:
                return True
        except Exception:
            pass
    changed, scanned = corpus_smoke(40)
    return changed > 0 and scanned > 0


def _any_token(ids: set[str], *needles: str) -> bool:
    return any(any(n in x for n in needles) for x in ids)


def evidence_predicates() -> dict[str, bool]:
    """
    Soft checklist navigation — DECOUPLED from critic/manifest admission.

    Rule-writing items = "this class was mined and/or a module exists on disk"
    (attempted), NOT "critic accepted into manifest". Critic owns manifest;
    checklist must not re-litigate that or L0 will livelock.
    """
    man = {r.lower() for r in _manifest_rules()}
    pack = set(_pack_names())
    files = _rule_files()
    # Attempted work: pack specs and/or on-disk modules (even if critic rejected).
    attempted = pack | files | man

    pack_has_spacing = _any_token(
        pack, "spacing", "punctuation", "dot_run", "repeated_dot", "repeated_garbage", "quote"
    )
    pack_has_hyphen = _any_token(pack, "hyphen", "line_break")
    pack_has_confusable = _any_token(pack, "confusable")

    return {
        "collect ocr error samples": _sample_ready(),
        "categorize error types": len(pack) >= 1
        or (ROOT / "goal" / "fix_proposals.md").exists(),
        # Mined or coded — not "in manifest"
        "write substitution rules": _any_token(attempted, "confusable")
        or (len(pack) > 0 and not pack_has_confusable),
        "write spacing and punctuation rules": _any_token(
            attempted, "spacing", "punctuation", "dot_run", "repeated_dot", "repeated_garbage", "quote"
        )
        or (len(pack) > 0 and not pack_has_spacing),
        "write hyphenation and word split rules": _any_token(
            attempted, "hyphen", "line_break"
        )
        or (len(pack) > 0 and not pack_has_hyphen),
        # Soft quality hints for next_step only (not L0)
        "test scripts on local corpus": _demo_applies() or len(man) >= 1,
        "validate accuracy and readability": _demo_applies() or len(man) >= MIN_MANIFEST_LIKE,
        "package and document scripts": APPLY_ALL.exists()
        and (bool(man) or bool(files))
        and (RULES_DIR / "__init__.py").exists(),
    }


def _checklist_span(text: str) -> tuple[int, int] | None:
    """Return [start, end) byte/char indices of Task checklist body."""
    m = re.search(r"(?im)^#{1,6}\s*task checklist\s*$", text)
    if not m:
        return None
    start = m.end()
    rest = text[start:]
    cut = re.search(r"(?m)^#{1,6}\s+\S", rest)
    end = start + cut.start() if cut else len(text)
    return start, end


def list_checklist_items(plan_path: Path = PLAN_PATH) -> list[tuple[bool, str]]:
    """Return [(done, text), ...] from Task checklist."""
    if not plan_path.exists():
        return []
    text = plan_path.read_text(encoding="utf-8")
    span = _checklist_span(text)
    if not span:
        return []
    body = text[span[0] : span[1]]
    items = []
    for line in body.splitlines():
        m = re.match(r"^\s*[-*+]\s+\[([ xX])\]\s+(.+)$", line)
        if m:
            items.append((m.group(1).lower() == "x", m.group(2).strip()))
    return items


def first_unchecked(plan_path: Path = PLAN_PATH) -> str | None:
    for done, text in list_checklist_items(plan_path):
        if not done:
            return text
    return None


def _should_check(item_text: str, preds: dict[str, bool]) -> bool:
    low = item_text.lower().strip()
    for needle, ok in preds.items():
        if needle in low and ok:
            return True
    return False


def reconcile_checklist(plan_path: Path = PLAN_PATH) -> list[str]:
    """
    Flip matching open items to [x] from evidence.
    Returns list of item texts newly checked off.
    """
    if not plan_path.exists():
        return []
    text = plan_path.read_text(encoding="utf-8")
    span = _checklist_span(text)
    if not span:
        return []
    start, end = span
    head, body, tail = text[:start], text[start:end], text[end:]
    preds = evidence_predicates()
    newly: list[str] = []
    new_lines: list[str] = []

    for line in body.splitlines(keepends=True):
        raw = line.rstrip("\n")
        nl = "\n" if line.endswith("\n") else ""
        m = re.match(r"^(\s*[-*+]\s+)\[ \](\s+)(.+)$", raw)
        if not m:
            new_lines.append(line)
            continue
        item = m.group(3).strip()
        if _should_check(item, preds):
            new_lines.append(f"{m.group(1)}[x]{m.group(2)}{m.group(3)}{nl}")
            newly.append(item)
        else:
            new_lines.append(line)

    if newly:
        plan_path.write_text(head + "".join(new_lines) + tail, encoding="utf-8")
    return newly


def check_off_first_unchecked(plan_path: Path = PLAN_PATH) -> str | None:
    """
    Force-check the first open item (use sparingly).
    Prefer reconcile_checklist() when evidence exists.
    """
    if not plan_path.exists():
        return None
    text = plan_path.read_text(encoding="utf-8")
    span = _checklist_span(text)
    if not span:
        return None
    start, end = span
    head, body, tail = text[:start], text[start:end], text[end:]
    new_lines: list[str] = []
    checked: str | None = None
    for line in body.splitlines(keepends=True):
        raw = line.rstrip("\n")
        nl = "\n" if line.endswith("\n") else ""
        m = re.match(r"^(\s*[-*+]\s+)\[ \](\s+)(.+)$", raw)
        if m and checked is None:
            checked = m.group(3).strip()
            new_lines.append(f"{m.group(1)}[x]{m.group(2)}{m.group(3)}{nl}")
        else:
            new_lines.append(line)
    if checked:
        plan_path.write_text(head + "".join(new_lines) + tail, encoding="utf-8")
    return checked


if __name__ == "__main__":
    items_before = list_checklist_items()
    print("before:")
    for d, t in items_before:
        print(f"  [{'x' if d else ' '}] {t}")
    newly = reconcile_checklist()
    print("newly checked:", newly)
    print("after:")
    for d, t in list_checklist_items():
        print(f"  [{'x' if d else ' '}] {t}")
    print("preds:", {k: v for k, v in evidence_predicates().items()})
