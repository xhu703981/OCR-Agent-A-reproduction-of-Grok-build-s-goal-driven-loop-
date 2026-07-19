"""
Goal runtime — one session, one clock.

  python goal_runtime.py

Edit constants below. Assume paths/data exist.

Goal.gaps = open work (L0/L1 reject); mirrored to goal/gaps.json for workers.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "goal" / "goal_state.json"
GAPS_PATH = ROOT / "goal" / "gaps.json"
OBJECTIVE_PATH = ROOT / "goal" / "OBJECTIVE.md"
PACK_PATH = ROOT / "goal" / "rule_pack.md"
MANIFEST_PATH = ROOT / "rules" / "manifest.json"

MIN_MANIFEST_RULES = 3
MAX_BLOCKED_STREAK = 3
MAX_GAPS = 24

FRESH = False
MAX_TICKS = 32


class Status(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"
    BLOCKED = "blocked"


@dataclass
class Goal:
    objective: str
    status: str = Status.ACTIVE.value
    round: int = 0
    last_message: str | None = None
    gaps: list[str] = field(default_factory=list)
    last_next_step: str | None = None
    last_worker: str | None = None
    blocked_streak: int = 0

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
    n = 0
    for part in re.split(r"(?m)^## ", PACK_PATH.read_text(encoding="utf-8"))[1:]:
        name = part.split("\n", 1)[0].strip()
        if name and name.lower() != "notes":
            n += 1
    return n


def count_manifest() -> int:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
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


def set_gaps(goal: Goal, items: list[str]) -> None:
    goal.gaps = _normalize_gap_items(items)
    _write_gaps_file(goal)


def clear_gaps(goal: Goal) -> None:
    goal.gaps = []
    _write_gaps_file(goal)


def _write_gaps_file(goal: Goal) -> None:
    GAPS_PATH.write_text(
        json.dumps(
            {"gaps": goal.gaps, "status": goal.status, "round": goal.round},
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
    known = set(Goal.__dataclass_fields__)
    filtered = {k: v for k, v in data.items() if k in known}
    g = Goal(**filtered)
    g.gaps = _normalize_gap_items(list(g.gaps) if g.gaps else [])
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


def apply_report(goal: Goal, kind: str, payload: str) -> Goal:
    if kind == "message":
        goal.last_message = payload
        goal.blocked_streak = 0
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
            goal.last_message = "completion rejected (L0)"
            save_goal(goal)
            print(f"[goal] gaps set (l0): {goal.gaps}")
            return goal
        print("[goal] L0 pass → opening judge panel")
        from goal_judge import JUDGE_MODEL, run_panel

        panel = run_panel(payload)
        if panel.achieved:
            goal.status = Status.COMPLETE.value
            goal.last_message = f"completed (panel ok, {panel.model}): {payload}"
            clear_gaps(goal)
            goal.blocked_streak = 0
        else:
            set_gaps(goal, panel.gap_items)
            goal.last_message = (
                f"completion rejected (L1 panel {panel.refute_count} refute, "
                f"model={JUDGE_MODEL})"
            )
            print(f"[goal] gaps set (l1): {goal.gaps}")
        save_goal(goal)
        return goal

    raise ValueError(f"unknown report kind: {kind}")


def verify(goal: Goal) -> tuple[bool, list[str]]:
    """L0: library thinness only."""
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


def _pack_rule_ids() -> list[str]:
    ids = []
    for part in re.split(r"(?m)^## ", PACK_PATH.read_text(encoding="utf-8"))[1:]:
        name = part.split("\n", 1)[0].strip()
        if name and name.lower() != "notes":
            ids.append(name)
    return ids


def _manifest_ids() -> set[str]:
    return set(json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["rules"])


def pick_worker(goal: Goal) -> str:
    refresh(goal)
    if count_pack_rules() == 0:
        return "pack"
    n_man = count_manifest()
    missing = [r for r in _pack_rule_ids() if r not in _manifest_ids()]
    if n_man < MIN_MANIFEST_RULES:
        return "programmer"
    if missing and goal.last_worker != "programmer":
        return "programmer"
    if goal.has_gaps() and goal.last_worker != "programmer":
        return "programmer"
    return "verify_only"


def run_worker(goal: Goal, name: str) -> tuple[str, str]:
    if name == "pack":
        code, out = _run_script("run_pack_turns.py")
        if code != 0:
            return "blocked", f"pack_turns failed ({code}): {out[-500:]}"
        return "message", "pack_turns finished"
    if name == "programmer":
        code, out = _run_script("run_programmer.py")
        if code != 0:
            return "blocked", f"programmer failed ({code}): {out[-500:]}"
        return "message", "programmer finished"
    if name == "verify_only":
        ok, gap_list = verify(goal)
        if ok:
            return "completed", "verify gate passed"
        set_gaps(goal, gap_list)
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
    print(f"[goal] tick {goal.round} → worker={name}")
    kind, payload = run_worker(goal, name)
    print(f"→ {kind}: {payload[:500]}")
    apply_report(goal, kind, payload)
    print(f"[goal] status={goal.status} gaps={goal.gaps}")
    return goal


def run_until_done() -> Goal:
    goal = start_goal() if FRESH else ensure_goal()
    print(f"[goal] begin status={goal.status} max_ticks={MAX_TICKS}")
    ticks = 0
    while goal.is_active() and ticks < MAX_TICKS:
        tick(goal)
        ticks += 1
        goal = load_goal()
    print(f"[goal] end status={goal.status} round={goal.round} ticks={ticks}")
    return goal


def main() -> None:
    run_until_done()


if __name__ == "__main__":
    main()
