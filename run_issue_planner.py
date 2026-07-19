"""
Issue planner (Grok-style propose → verify):
  draft proposals from batch, then adversarial critic.
Writes:
  goal/fix_proposals_draft.md
  goal/fix_proposals.md   (verified)
"""

import re
from pathlib import Path

from ollama_chat import chat

ROOT = Path(__file__).resolve().parent

BATCH_N = 12
MAX_SNIP_CHARS = 420


def plan_section(plan: str, title: str) -> str:
    pat = rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pat, plan)
    return m.group(1).strip() if m else ""


def load_batch():
    from sample_data import format_batch_md, load_train

    rows = load_train()
    return format_batch_md(rows[:BATCH_N], max_chars=MAX_SNIP_CHARS)


def fill(template: str, **kw) -> str:
    out = template
    for k, v in kw.items():
        out = out.replace("{" + k + "}", v)
    return out


def main():
    objective = (ROOT / "goal" / "OBJECTIVE.md").read_text(encoding="utf-8").strip()
    plan = (ROOT / "goal" / "plan.md").read_text(encoding="utf-8")
    batch_md, ids = load_batch()
    acceptance = plan_section(plan, "Acceptance criteria")
    safety = plan_section(plan, "Safety rules")
    non_goals = plan_section(plan, "Non-goals")

    # --- 1) propose ---
    draft_prompt = fill(
        (ROOT / "goal" / "issue_planner_prompt.md").read_text(encoding="utf-8"),
        OBJECTIVE=objective,
        ACCEPTANCE=acceptance,
        SAFETY=safety,
        NON_GOALS=non_goals,
        BATCH=batch_md,
    )
    print(f"draft prompt_chars={len(draft_prompt)} batch={ids}")
    draft = chat(draft_prompt, max_tokens=1600)
    draft_path = ROOT / "goal" / "fix_proposals_draft.md"
    draft_path.write_text(draft + "\n", encoding="utf-8")
    print(f"wrote {draft_path}")

    # --- 2) verify (adversarial) ---
    critic_prompt = fill(
        (ROOT / "goal" / "proposal_critic_prompt.md").read_text(encoding="utf-8"),
        OBJECTIVE=objective,
        SAFETY=safety,
        NON_GOALS=non_goals,
        BATCH=batch_md,
        DRAFT=draft,
    )
    print(f"critic prompt_chars={len(critic_prompt)}")
    verified = chat(critic_prompt, max_tokens=1800)
    out = ROOT / "goal" / "fix_proposals.md"
    out.write_text(verified + "\n", encoding="utf-8")
    print(verified)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
