"""
Goal completion judge panel (triggered only on completed claims).

L0 cheap checks live in goal_runtime.verify.
L1: N skeptics, majority-refute.
Framing: "we did what code can do" (regex/algorithm-fixable classes).

Edit constants below. Assume paths exist.
"""

from __future__ import annotations

import importlib.util
import json
import re
from dataclasses import dataclass
from pathlib import Path

from ollama_chat import chat

ROOT = Path(__file__).resolve().parent
JUDGE_PROMPT = ROOT / "goal" / "judge_prompt.md"
JUDGE_DIR = ROOT / "goal" / "judge_reports"
OBJECTIVE_PATH = ROOT / "goal" / "OBJECTIVE.md"
PLAN_PATH = ROOT / "goal" / "plan.md"
PACK_PATH = ROOT / "goal" / "rule_pack.md"
MANIFEST_PATH = ROOT / "rules" / "manifest.json"
APPLY_ALL = ROOT / "rules" / "apply_all.py"

JUDGE_MODEL = "grok-4.20-0309-non-reasoning"
N_SKEPTICS = 3
MAX_PLAN_CHARS = 3500
MAX_EVIDENCE_CHARS = 4000
# Solo debug: python goal_judge.py
DEBUG_CLAIM = "Goal complete: deterministic OCR fix library ready."

ANGLES = [
    "Is the shipped library real (several modules in manifest, apply runs)? Incomplete pack→manifest is OK.",
    "Do demo/corpus show real safe fixes (changed text without clear collateral damage)? Residual hard OCR is OK.",
    "Scope: regex/algorithms only. Prefer achieved if local-safe effect exists; hollow identity = not achieved.",
]


@dataclass
class SkepticVote:
    skeptic_id: int
    verdict: str  # achieved | not_achieved
    gaps: list[str]
    raw: str


@dataclass
class PanelResult:
    achieved: bool
    votes: list[SkepticVote]
    gaps_summary: str
    model: str
    refute_count: int
    gap_items: list[str]


def _read_capped(path: Path, n: int) -> str:
    t = path.read_text(encoding="utf-8")
    return t if len(t) <= n else t[:n] + "\n…(truncated)"


def _manifest_blob() -> str:
    return MANIFEST_PATH.read_text(encoding="utf-8-sig").strip()


def _pack_rule_names() -> str:
    names = []
    for part in re.split(r"(?m)^## ", PACK_PATH.read_text(encoding="utf-8"))[1:]:
        name = part.split("\n", 1)[0].strip()
        if name and name.lower() != "notes":
            names.append(name)
    return ", ".join(names) if names else "(empty pack)"


def _demo_pipeline() -> str:
    spec = importlib.util.spec_from_file_location("apply_all", APPLY_ALL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sample = "f0x \u201c\ufb01le\u201d a....b 1O2"
    out = mod.fix_text(sample)
    changed = "yes" if out != sample else "no"
    return f"in:  {sample}\nout: {out}\nchanged: {changed}"


def _corpus_smoke_line() -> str:
    from goal_checklist import corpus_smoke

    changed, scanned = corpus_smoke(60)
    return (
        f"corpus_smoke: changed={changed} scanned={scanned} "
        f"(lines where apply_all != original)"
    )


def _worse_scan_line() -> str:
    from goal_checklist import scan_ocr_worse

    # Diagnostic only (not a hard gate)
    s = scan_ocr_worse(max_lines=2000, blame=False)
    return (
        f"worse_scan (diagnostic, not gating): n_worse={s['n_worse']} "
        f"n_improved={s['n_improved']} n_changed={s['n_changed']} "
        f"scanned={s['n_scanned']}"
    )


def collect_evidence() -> str:
    parts = [
        "Judge bar: useful local-safe code fixes (regex/algorithms). "
        "Core generality = do not introduce new errors elsewhere. "
        "Not all OCR; not 'pack names must all ship'.",
        f"manifest.json:\n{_manifest_blob()}",
        f"pack rule names (aspirational; missing some is OK if library works):\n"
        f"{_pack_rule_names()}",
        f"pipeline demo:\n{_demo_pipeline()}",
        _corpus_smoke_line(),
        _worse_scan_line(),
        "Note: OCRoscope worse/improved counts are diagnostic only — not a hard gate. "
        "Judge local safety qualitatively (obvious new errors), not n_worse==0.",
        "Non-goals (must not block alone): every pack id in manifest; perfect math; "
        "multi-language; Re-OCR; LLM page rewrite; zero residual unfixed OCR; ultra-abstract purity; "
        "hard OCRoscope n_worse==0.",
        "Hard fail signals: hollow identity pipeline; clear obvious collateral damage; "
        "almost no rules despite easy glyph/run evidence.",
    ]
    blob = "\n\n".join(parts)
    if len(blob) > MAX_EVIDENCE_CHARS:
        blob = blob[:MAX_EVIDENCE_CHARS] + "\n…(truncated)"
    return blob


def plan_excerpt() -> str:
    return _read_capped(PLAN_PATH, MAX_PLAN_CHARS)


def _parse_vote(text: str) -> tuple[str, list[str]]:
    """Require a JSON object with verdict + gaps. No keyword guessing."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        text = m.group(1)
    else:
        m = re.search(r"\{[^{}]*\}", text, flags=re.S)
        if not m:
            raise ValueError(f"skeptic output has no JSON object:\n{text[:500]}")
        text = m.group(0)
    data = json.loads(text)
    verdict = str(data["verdict"]).strip().lower().replace(" ", "_")
    if verdict not in ("achieved", "not_achieved"):
        raise ValueError(f"bad verdict: {verdict!r}")
    gaps = data.get("gaps") or []
    if not isinstance(gaps, list):
        raise ValueError("gaps must be a list")
    gaps = [str(g).strip() for g in gaps if str(g).strip()][:4]
    if verdict == "not_achieved" and not gaps:
        gaps = ["skeptic refuted without listing gaps"]
    return verdict, gaps


def run_skeptic(
    skeptic_id: int,
    claim: str,
    model: str,
    *,
    prior_gaps: list[str] | None = None,
) -> SkepticVote:
    tmpl = JUDGE_PROMPT.read_text(encoding="utf-8")
    angle = ANGLES[(skeptic_id - 1) % len(ANGLES)]
    if prior_gaps:
        prior_blob = "\n".join(f"- {g}" for g in prior_gaps[:12])
    else:
        prior_blob = "none"
    prompt = (
        tmpl.replace("{SKEPTIC_ID}", str(skeptic_id))
        .replace("{OBJECTIVE}", _read_capped(OBJECTIVE_PATH, 800))
        .replace("{PLAN_EXCERPT}", plan_excerpt())
        .replace("{EVIDENCE}", collect_evidence())
        .replace("{CLAIM}", claim)
        .replace("{ANGLE}", angle)
        .replace("{PRIOR_GAPS}", prior_blob)
    )
    temp = 0.15 + 0.1 * (skeptic_id - 1)  # introducing variance across skeptics
    raw = chat(prompt, model=model, max_tokens=400, temperature=temp, think=False)
    verdict, gaps = _parse_vote(raw)
    return SkepticVote(skeptic_id=skeptic_id, verdict=verdict, gaps=gaps, raw=raw)


def run_panel(
    claim: str,
    *,
    model: str | None = None,
    n: int = N_SKEPTICS,
    prior_gaps: list[str] | None = None,
) -> PanelResult:
    """Majority-refute: refute_count * 2 >= n → not achieved."""
    model = model or JUDGE_MODEL
    votes: list[SkepticVote] = []
    for i in range(1, n + 1):
        print(f"  [judge] skeptic {i}/{n} model={model}")
        v = run_skeptic(i, claim, model, prior_gaps=prior_gaps)
        votes.append(v)
        (JUDGE_DIR / f"skeptic_{i}.json").write_text(
            json.dumps(
                {
                    "skeptic_id": v.skeptic_id,
                    "verdict": v.verdict,
                    "gaps": v.gaps,
                    "raw": v.raw,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"  [judge] skeptic {i} → {v.verdict} gaps={v.gaps}")

    refute_count = sum(1 for v in votes if v.verdict == "not_achieved")
    achieved = refute_count * 2 < n

    gap_items: list[str] = []
    gap_lines: list[str] = []
    seen: set[str] = set()
    for v in votes:
        if v.verdict != "not_achieved":
            continue
        for g in v.gaps:
            key = g.lower()
            if key not in seen:
                seen.add(key)
                gap_items.append(g)
                gap_lines.append(f"- [s{v.skeptic_id}] {g}")

    if not achieved and not gap_items:
        gap_items.append("panel majority refuted with no structured gaps")
        gap_lines.append(f"- {gap_items[0]}")

    summary = (
        f"panel model={model} votes="
        + ",".join(f"s{v.skeptic_id}:{v.verdict}" for v in votes)
        + f" refute={refute_count}/{n}\n"
        + ("\n".join(gap_lines) if gap_lines else "(no gaps)")
    )
    (JUDGE_DIR / "last_panel.md").write_text(summary + "\n", encoding="utf-8")
    return PanelResult(
        achieved=achieved,
        votes=votes,
        gaps_summary=summary,
        model=model,
        refute_count=refute_count,
        gap_items=gap_items,
    )


if __name__ == "__main__":
    r = run_panel(DEBUG_CLAIM)
    print("---")
    print("ACHIEVED" if r.achieved else "NOT ACHIEVED")
    print(r.gaps_summary)
