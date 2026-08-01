"""
Goal runtime — dynamic worker selection (Grok Build–style loop).

  python goal_runtime.py

Not a fixed pack→program→verify assembly line. Each tick:
  pick_worker(state) → run worker → apply_report → maybe L1 panel.

Workers:
  - pack: mining script
  - implementer: **tool loop** (observe prior step results → next tool → …)
  - programmer: alias → implementer (legacy repair_target name)
  - strategist / verify_only

State drivers:
  - gaps / prior_gaps (open work; prior = last L1 reject set)
  - repair_target (pack | programmer | implementer | strategist | None)
  - gap fingerprint stall → strategist (anti-ratchet companion)
  - L1 majority-refute panel with PRIOR_GAPS (anti-ratchet in judge prompt)

Edit constants below. Assume paths/data exist.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "goal" / "goal_state.json"
GAPS_PATH = ROOT / "goal" / "gaps.json"
OBJECTIVE_PATH = ROOT / "goal" / "OBJECTIVE.md"
PACK_PATH = ROOT / "goal" / "rule_pack.md"
MANIFEST_PATH = ROOT / "rules" / "manifest.json"
APPLY_ALL = ROOT / "rules" / "apply_all.py"
STRATEGY_PATH = ROOT / "goal" / "strategy_note.md"
STRATEGY_HISTORY = ROOT / "goal" / "strategy_history.md"

MIN_MANIFEST_RULES = 3
MAX_BLOCKED_STREAK = 3
MAX_L1_REJECT_STREAK = 4  # room for strategist restructure + retry
MAX_THIN_PROGRAM_PASSES = 2
MAX_GAPS = 24
# Same gap *topic* this many L1 rejects in a row → strategist (not another nits round)
GAP_STALL_THRESHOLD = 2
# Jaccard on gap tokens; reworded but same complaint should still stall
GAP_SIMILARITY_THRESHOLD = 0.45
MAX_STRATEGIST_PASSES = 2

FRESH = False  # last: no hard n_worse gate, full remine complete 2026-07-27
MAX_TICKS = 24

_OPAQUE_NAME = re.compile(r"^R\d+$|^rule_?\d+$|^fix_?\d+$", re.I)
_OCR_CLASS = re.compile(
    r"confusable|ligature|junk|quote|hyphen|digit|unicode|garbage|"
    r"spacing|punctuation|repeated|dot_run|letter_in|word_split|"
    r"ellipsis|apostrophe|line_?break|normalization",
    re.I,
)
_GAP_CLASS_KEYS = (
    "ligature",
    "junk",
    "confusable",
    "quote",
    "hyphen",
    "digit",
    "unicode",
    "garbage",
    "spacing",
)
_GAP_STOP = frozenset(
    "the a an and or of to in on for with from that this rule pack "
    "manifest missing not present despite being from claimed listed "
    "absent still no evidence with without yet".split()
)


class Status(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    # same-gap stall without recovery after strategist budget
    NO_PROGRESS = "no_progress_paused"


@dataclass
class Goal:
    objective: str
    status: str = Status.ACTIVE.value
    round: int = 0
    last_message: str | None = None
    gaps: list[str] = field(default_factory=list)
    # Last L1 reject gaps — fed to next panel as PRIOR_GAPS (anti-ratchet)
    prior_gaps: list[str] = field(default_factory=list)
    last_next_step: str | None = None
    last_worker: str | None = None
    blocked_streak: int = 0
    # pack | programmer | strategist | None
    repair_target: str | None = None
    repair_reason: str | None = None
    l1_reject_streak: int = 0
    thin_program_passes: int = 0
    last_gap_fingerprint: str | None = None
    # sorted tokens from last L1 gaps (for Jaccard stall, not exact reword match)
    last_gap_tokens: list[str] = field(default_factory=list)
    gap_stall_streak: int = 0
    strategist_passes: int = 0

    def is_active(self) -> bool:
        return self.status == Status.ACTIVE.value

    def has_gaps(self) -> bool:
        return bool(self.gaps)


def objective_summary() -> str:
    for ln in OBJECTIVE_PATH.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            return s[:240]
    return OBJECTIVE_PATH.read_text(encoding="utf-8").strip()[:240]


def count_pack_rules() -> int:
    return len(_pack_rule_ids())


def count_manifest() -> int:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    return len(data["rules"])


def refresh(goal: Goal) -> None:
    from goal_checklist import first_unchecked, reconcile_checklist

    newly = reconcile_checklist()
    if newly:
        print(f"[checklist] checked off: {newly}")
    goal.last_next_step = first_unchecked()


def _normalize_gap_items(items: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in items or []:
        g = re.sub(r"^\s*[-*]\s*", "", str(raw)).strip()
        g = re.sub(r"^\[s\d+\]\s*", "", g, flags=re.I).strip()
        if not g or g.lower() in seen:
            continue
        seen.add(g.lower())
        out.append(g)
        if len(out) >= MAX_GAPS:
            break
    return out


def gap_token_set(gaps: list[str]) -> set[str]:
    """Content tokens from gap strings (stopwords stripped)."""
    out: set[str] = set()
    for g in gaps or []:
        for t in re.findall(r"[a-z0-9_]{3,}", g.lower()):
            if t not in _GAP_STOP:
                out.add(t)
    return out


def gap_fingerprint(gaps: list[str]) -> str:
    """Short hash of gap token set (logging / state)."""
    blob = " ".join(sorted(gap_token_set(gaps)))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


def gaps_similar(prev_tokens: list[str] | set[str], gaps: list[str]) -> bool:
    """True if new gaps are topically the same complaint (Jaccard)."""
    a = set(prev_tokens or [])
    b = gap_token_set(gaps)
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= GAP_SIMILARITY_THRESHOLD


def set_gaps(goal: Goal, items: list[str]) -> None:
    goal.gaps = _normalize_gap_items(items)
    _write_gaps_file(goal)


def clear_gaps(goal: Goal) -> None:
    goal.gaps = []
    _write_gaps_file(goal)


def _write_gaps_file(goal: Goal) -> None:
    GAPS_PATH.write_text(
        json.dumps(
            {
                "gaps": goal.gaps,
                "prior_gaps": goal.prior_gaps,
                "status": goal.status,
                "round": goal.round,
                "repair_target": goal.repair_target,
                "repair_reason": goal.repair_reason,
                "last_gap_fingerprint": goal.last_gap_fingerprint,
                "gap_stall_streak": goal.gap_stall_streak,
                "strategy_path": str(STRATEGY_PATH) if STRATEGY_PATH.is_file() else None,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def save_goal(goal: Goal) -> None:
    STATE_PATH.write_text(
        json.dumps(asdict(goal), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_gaps_file(goal)


def load_goal() -> Goal:
    data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    known = {f.name for f in fields(Goal)}
    filtered = {k: v for k, v in data.items() if k in known}
    # merge onto defaults so new fields (prior_gaps, stall, …) load on old snapshots
    base = asdict(Goal(objective=filtered.get("objective") or objective_summary()))
    base.update(filtered)
    g = Goal(**{k: base[k] for k in known})
    g.gaps = _normalize_gap_items(list(g.gaps) if g.gaps else [])
    g.prior_gaps = _normalize_gap_items(list(g.prior_gaps) if g.prior_gaps else [])
    return g


def start_goal() -> Goal:
    goal = Goal(objective=objective_summary())
    clear_gaps(goal)
    refresh(goal)
    save_goal(goal)
    return goal


def ensure_goal() -> Goal:
    try:
        g = load_goal()
    except FileNotFoundError:
        return start_goal()
    if g.is_active():
        refresh(g)
        return g
    return start_goal()


def _pack_rule_ids() -> list[str]:
    ids = []
    for part in re.split(r"(?m)^## ", PACK_PATH.read_text(encoding="utf-8"))[1:]:
        name = part.split("\n", 1)[0].strip()
        if name and name.lower() != "notes":
            ids.append(name)
    return ids


def _manifest_ids() -> set[str]:
    return set(json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))["rules"])


def _demo_changed() -> bool:
    spec = importlib.util.spec_from_file_location("apply_all", APPLY_ALL)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    sample = "f0x \u201c\ufb01le\u201d a....b 1O2"
    return mod.fix_text(sample) != sample


def _smoke_changed() -> tuple[int, int]:
    from goal_checklist import corpus_smoke

    return corpus_smoke(40)


def diagnose_l1_failure(gaps: list[str]) -> tuple[str, str]:
    """
    After L1 reject (non-stall) or L0 worse gap: pick pack vs programmer.
    Returns (repair_target, reason).
    """
    names = list(dict.fromkeys(_pack_rule_ids()))
    man = _manifest_ids()
    missing = [n for n in names if n not in man]
    n = len(names) or 1
    opaque_n = sum(1 for n_ in names if _OPAQUE_NAME.match(n_))
    classy_n = sum(1 for n_ in names if _OCR_CLASS.search(n_))
    gap_blob = " ".join(gaps).lower()
    demo_ok = _demo_changed()
    smoke_n, smoke_scan = _smoke_changed()
    library_ok = len(man) >= MIN_MANIFEST_RULES and (demo_ok or smoke_n > 0)

    if not names:
        return "pack", "empty pack after L1"
    if opaque_n * 2 >= n:
        return "pack", f"opaque pack ids ({opaque_n}/{len(names)})"
    if classy_n == 0 and len(man) < MIN_MANIFEST_RULES:
        return "pack", "pack names have no OCR-class keywords and library is thin"

    missing_classes = [
        kw
        for kw in _GAP_CLASS_KEYS
        if kw in gap_blob and not any(kw in n_.lower() for n_ in names + list(man))
    ]
    if missing_classes and not library_ok:
        return (
            "pack",
            "L1 gaps need classes absent from pack/manifest: " + ", ".join(missing_classes),
        )

    if len(man) < MIN_MANIFEST_RULES:
        return "implementer", f"library thin: manifest={len(man)} need>={MIN_MANIFEST_RULES}"
    if not demo_ok and smoke_n == 0:
        return (
            "implementer",
            f"apply is identity (smoke 0/{smoke_scan}) — tool loop for real effect",
        )

    if missing and library_ok:
        damage_ish = any(
            k in gap_blob for k in ("damage", "false positive", "mangles", "corrupt")
        )
        if damage_ish:
            return "implementer", "L1 cites collateral damage — tighten via tool loop"
        return (
            "implementer",
            "library works; residual gaps → implementer tool loop "
            f"(unshipped ok: {missing[:4]})",
        )

    if missing:
        return "implementer", f"manifest missing {len(missing)} pack rules: {missing[:6]}"

    return "implementer", "L1 gaps — implementer tool loop"


def run_strategist(goal: Goal) -> tuple[str, str]:
    """
    Structural unstick (Grok Build strategist). Writes strategy_note.md.
    Returns (next_worker, reason) where next_worker is pack|programmer.
    """
    from ollama_chat import chat

    tmpl = (ROOT / "goal" / "strategist_prompt.md").read_text(encoding="utf-8")
    hist = ""
    if STRATEGY_HISTORY.is_file():
        hist = STRATEGY_HISTORY.read_text(encoding="utf-8")[-3000:]
    prompt = (
        tmpl.replace("{OBJECTIVE}", goal.objective)
        .replace("{GAPS}", "\n".join(f"- {g}" for g in goal.gaps) or "(none)")
        .replace("{STALL}", str(goal.gap_stall_streak))
        .replace("{L1_STREAK}", str(goal.l1_reject_streak))
        .replace("{LAST_REPAIR}", f"{goal.repair_target}:{goal.repair_reason}")
        .replace("{PACK_IDS}", ", ".join(_pack_rule_ids()) or "(empty)")
        .replace(
            "{MANIFEST}",
            json.dumps(list(_manifest_ids()), ensure_ascii=False),
        )
        .replace("{HISTORY}", hist or "(none)")
    )
    print("[goal] strategist …")
    md = chat(
        prompt,
        max_tokens=900,
        temperature=0.15,
        think=False,
        model="grok-4.20-0309-non-reasoning",
    )
    STRATEGY_PATH.write_text(md.rstrip() + "\n", encoding="utf-8")
    with STRATEGY_HISTORY.open("a", encoding="utf-8") as f:
        f.write(f"\n\n--- round {goal.round} ---\n")
        f.write(md.rstrip() + "\n")

    m = re.search(
        r"(?im)^\s*##\s*next_worker\s*\n\s*(pack|programmer|implementer)\b", md
    )
    if not m:
        m = re.search(
            r"(?i)\bnext_worker\b[^\n]*\b(pack|programmer|implementer)\b", md
        )
    target = m.group(1).lower() if m else "implementer"
    if target == "programmer":
        target = "implementer"
    why_m = re.search(r"(?im)^\s*##\s*why_worker\s*\n\s*(.+)", md)
    why = why_m.group(1).strip() if why_m else "strategist default"
    print(f"[goal] strategist → next_worker={target} ({why[:120]})")
    return target, f"strategist: {why[:200]}"


def apply_report(goal: Goal, kind: str, payload: str) -> Goal:
    if kind == "message":
        goal.last_message = payload
        goal.blocked_streak = 0

        if goal.repair_target == "strategist" and goal.last_worker == "strategist":
            # strategist already set repair_target to pack|programmer in run_worker
            pass
        elif goal.repair_target == "pack" and goal.last_worker == "pack":
            goal.repair_target = "implementer"
            goal.repair_reason = "pack remine finished → implementer tool loop"
            print("[goal] repair advance: pack → implementer")
        elif goal.repair_target in ("programmer", "implementer") and goal.last_worker in (
            "programmer",
            "implementer",
        ):
            goal.repair_target = None
            goal.repair_reason = "implementer finished → re-verify"
            print("[goal] repair advance: implementer → (clear, next verify)")

        if goal.last_worker in ("programmer", "implementer"):
            if count_manifest() < MIN_MANIFEST_RULES:
                goal.thin_program_passes += 1
                print(
                    f"[goal] thin library after implementer "
                    f"({count_manifest()}<{MIN_MANIFEST_RULES}) "
                    f"passes={goal.thin_program_passes}/{MAX_THIN_PROGRAM_PASSES}"
                )
                if goal.thin_program_passes >= MAX_THIN_PROGRAM_PASSES:
                    if goal.strategist_passes < MAX_STRATEGIST_PASSES:
                        goal.repair_target = "strategist"
                        goal.repair_reason = "thin library after repeated implementer"
                        print("[goal] thin library → strategist")
                    else:
                        goal.status = Status.BLOCKED.value
                        goal.last_message = (
                            f"blocked: manifest still < {MIN_MANIFEST_RULES} "
                            f"after implementer+strategist"
                        )
                        print("[goal] BLOCKED: thin library")
            else:
                goal.thin_program_passes = 0
        refresh(goal)
        save_goal(goal)
        return goal

    if kind == "blocked":
        goal.last_message = payload
        goal.blocked_streak += 1
        set_gaps(goal, goal.gaps + [f"blocked: {payload[:200]}"])
        if goal.blocked_streak >= MAX_BLOCKED_STREAK:
            goal.status = Status.BLOCKED.value
        refresh(goal)
        save_goal(goal)
        return goal

    if kind == "completed":
        if not goal.is_active():
            goal.last_message = f"ignored completed: status is {goal.status}"
            save_goal(goal)
            return goal
        ok, gap_list = verify(goal)
        if not ok:
            set_gaps(goal, gap_list)
            target, reason = diagnose_l1_failure(gap_list)
            # empty pack still forces pack
            if count_pack_rules() == 0:
                target, reason = "pack", "L0: no pack"
            goal.repair_target = target
            goal.repair_reason = reason or "L0 reject"
            goal.last_message = f"completion rejected (L0): {reason}"
            save_goal(goal)
            print(f"[goal] gaps set (l0): {goal.gaps} repair={goal.repair_target}")
            return goal
        print("[goal] L0 pass → opening judge panel")
        from goal_judge import JUDGE_MODEL, run_panel

        panel = run_panel(payload, prior_gaps=goal.prior_gaps)
        if panel.achieved:
            goal.status = Status.COMPLETE.value
            goal.last_message = f"completed (panel ok, {panel.model}): {payload}"
            clear_gaps(goal)
            goal.prior_gaps = []
            goal.blocked_streak = 0
            goal.l1_reject_streak = 0
            goal.gap_stall_streak = 0
            goal.last_gap_fingerprint = None
            goal.repair_target = None
            goal.repair_reason = None
        else:
            # --- anti-ratchet: topic similarity + prior_gaps ---
            new_gaps = panel.gap_items
            fp = gap_fingerprint(new_gaps)
            toks = gap_token_set(new_gaps)
            if goal.last_gap_tokens and gaps_similar(goal.last_gap_tokens, new_gaps):
                goal.gap_stall_streak += 1
            else:
                goal.gap_stall_streak = 1
            goal.last_gap_fingerprint = fp
            goal.last_gap_tokens = sorted(toks)
            set_gaps(goal, new_gaps)
            # next panel will see these as PRIOR_GAPS
            goal.prior_gaps = list(goal.gaps)
            goal.l1_reject_streak += 1

            if goal.gap_stall_streak >= GAP_STALL_THRESHOLD:
                if goal.strategist_passes < MAX_STRATEGIST_PASSES:
                    goal.repair_target = "strategist"
                    goal.repair_reason = (
                        f"gap stall fingerprint={fp} "
                        f"streak={goal.gap_stall_streak}"
                    )
                    print(
                        f"[goal] L1 same-gap stall → strategist "
                        f"(fp={fp} stall={goal.gap_stall_streak})"
                    )
                else:
                    goal.status = Status.NO_PROGRESS.value
                    goal.last_message = (
                        f"no_progress: same gap fingerprint {fp} after strategist budget"
                    )
                    print("[goal] NO_PROGRESS: gap stall exhausted strategist")
            else:
                target, reason = diagnose_l1_failure(panel.gap_items)
                goal.repair_target = target
                goal.repair_reason = reason
                print(
                    f"[goal] L1 reject → diagnose repair={target} "
                    f"(l1_streak={goal.l1_reject_streak} stall={goal.gap_stall_streak}) "
                    f"reason={reason}"
                )

            goal.last_message = (
                f"completion rejected (L1 panel {panel.refute_count} refute, "
                f"model={JUDGE_MODEL}); repair={goal.repair_target}: {goal.repair_reason}"
            )
            print(f"[goal] gaps set (l1): {goal.gaps}")

            if (
                goal.is_active()
                and goal.l1_reject_streak >= MAX_L1_REJECT_STREAK
                and goal.repair_target != "strategist"
            ):
                if goal.strategist_passes < MAX_STRATEGIST_PASSES:
                    goal.repair_target = "strategist"
                    goal.repair_reason = f"L1 reject streak {goal.l1_reject_streak}"
                    print("[goal] L1 streak → strategist before block")
                else:
                    goal.status = Status.BLOCKED.value
                    goal.last_message = (
                        f"blocked: L1 rejected {goal.l1_reject_streak}×; "
                        f"{goal.repair_reason}"
                    )
                    print("[goal] BLOCKED after L1 fails + strategist budget")
        save_goal(goal)
        return goal

    raise ValueError(f"unknown report kind: {kind}")


def verify(goal: Goal) -> tuple[bool, list[str]]:
    """
    L0 gates before L1 panel:
      - pack exists, library thick enough
    Local safety ("no obvious new errors elsewhere") is judged by L1/critics
    from evidence — not a hard OCRoscope n_worse==0 gate.
    """
    refresh(goal)
    gaps: list[str] = []
    if count_pack_rules() == 0:
        gaps.append("no rule pack yet (run pack mining)")
    n_man = count_manifest()
    if n_man < MIN_MANIFEST_RULES:
        gaps.append(
            f"library too thin: manifest has {n_man} rules; need >= {MIN_MANIFEST_RULES}"
        )
    return (len(gaps) == 0, gaps)


def _run_script(script: str) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(ROOT / script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return p.returncode, ((p.stdout or "") + (p.stderr or ""))[-4000:]


def pick_worker(goal: Goal) -> str:
    """
    Dynamic choice from state (not a fixed assembly line).

    Priority:
      1. repair_target (strategist | pack | implementer/programmer)
      2. empty pack → pack
      3. thin manifest → implementer (tool loop)
      4. gaps → implementer or pack
      5. else verify
    """
    refresh(goal)

    # normalize legacy name
    if goal.repair_target == "programmer":
        goal.repair_target = "implementer"

    # --- explicit repair ---
    if goal.repair_target == "strategist":
        return "strategist"
    if goal.repair_target == "pack":
        if goal.last_worker == "pack":
            return "implementer"
        return "pack"
    if goal.repair_target == "implementer":
        if goal.last_worker in ("implementer", "programmer"):
            return "verify_only"
        return "implementer"

    # --- bootstrap from disk evidence ---
    if count_pack_rules() == 0:
        return "pack"

    n_man = count_manifest()
    if n_man < MIN_MANIFEST_RULES:
        if goal.last_worker in ("implementer", "programmer"):
            return "verify_only"
        return "implementer"

    # Open gaps (incl. ocr_worse) without repair_target → re-pick
    if goal.gaps:
        blob = " ".join(goal.gaps).lower()
        if "no rule pack" in blob or count_pack_rules() == 0:
            return "pack"
        if goal.last_worker in ("implementer", "programmer"):
            return "verify_only"
        return "implementer"

    return "verify_only"


def run_worker(goal: Goal, name: str) -> tuple[str, str]:
    if name == "pack":
        code, out = _run_script("run_pack_turns.py")
        if code != 0:
            return "blocked", f"pack_turns failed ({code}): {out[-500:]}"
        return "message", "pack_turns finished"
    if name in ("implementer", "programmer"):
        # Tool-using implementer loop (history of step results → next tool)
        code, out = _run_script("run_implementer.py")
        if code != 0:
            return "blocked", f"implementer failed ({code}): {out[-500:]}"
        return "message", "implementer finished"
    if name == "strategist":
        try:
            target, reason = run_strategist(goal)
        except Exception as e:
            return "blocked", f"strategist failed: {e}"
        goal.strategist_passes += 1
        if target == "programmer":
            target = "implementer"
        goal.repair_target = target if target in ("pack", "implementer") else "implementer"
        goal.repair_reason = reason
        # give the next worker a clean stall window after restructure
        goal.gap_stall_streak = 0
        save_goal(goal)
        return "message", f"strategist finished → repair={goal.repair_target}"
    if name == "verify_only":
        ok, gap_list = verify(goal)
        if ok:
            return "completed", "verify gate passed"
        set_gaps(goal, gap_list)
        target, reason = diagnose_l1_failure(gap_list)
        if count_pack_rules() == 0:
            target, reason = "pack", "L0: no pack"
        goal.repair_target = target
        goal.repair_reason = reason
        save_goal(goal)
        prev = goal.last_message or ""
        if prev.startswith("verify not green") and goal.last_worker == "verify_only":
            return (
                "blocked",
                "stuck on verify:\n" + "\n".join(f"- {g}" for g in gap_list),
            )
        return (
            "message",
            "verify not green yet:\n" + "\n".join(f"- {g}" for g in gap_list),
        )
    raise ValueError(f"unknown worker: {name}")


def tick(goal: Goal) -> Goal:
    if not goal.is_active():
        return goal
    goal.round += 1
    name = pick_worker(goal)
    goal.last_worker = name
    print(
        f"[goal] tick {goal.round} → worker={name} "
        f"repair={goal.repair_target!r} "
        f"stall={goal.gap_stall_streak} fp={goal.last_gap_fingerprint}"
    )
    kind, payload = run_worker(goal, name)
    print(f"→ {kind}: {payload[:500]}")
    apply_report(goal, kind, payload)
    print(
        f"[goal] status={goal.status} gaps={goal.gaps} "
        f"repair={goal.repair_target!r}"
    )
    return goal


def run_until_done() -> Goal:
    goal = start_goal() if FRESH else ensure_goal()
    print(f"[goal] begin status={goal.status} max_ticks={MAX_TICKS}")
    ticks = 0
    while goal.is_active() and ticks < MAX_TICKS:
        tick(goal)
        ticks += 1
        goal = load_goal()
    print(
        f"[goal] end status={goal.status} round={goal.round} ticks={ticks} "
        f"strategist_passes={goal.strategist_passes}"
    )
    return goal


def main() -> None:
    run_until_done()


if __name__ == "__main__":
    main()
