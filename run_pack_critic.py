"""Final critic on goal/rule_pack.md -> verified pack."""

import re
from pathlib import Path

from ollama_chat import chat

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "goal" / "rule_pack.md"
SAMPLE_N = 8
MAX_SNIP = 350


def plan_section(plan: str, title: str) -> str:
    m = re.search(rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)", plan)
    return m.group(1).strip() if m else ""


def sample_block() -> str:
    from sample_data import format_batch_md, load_holdout

    rows = load_holdout()
    if not rows:
        return "(none)"
    md, _ = format_batch_md(rows[:SAMPLE_N], max_chars=MAX_SNIP)
    return md or "(none)"


def strip_to_pack(text: str) -> str:
    """Keep # Rule pack body; drop trailing Rejected/Notes if mixed poorly."""
    i = text.find("# Rule pack")
    if i < 0:
        return text.strip() + "\n"
    text = text[i:]
    # cut at ## Rejected if present after pack rules
    m = re.search(r"(?m)^## Rejected\b", text)
    if m:
        pack_only = text[: m.start()].rstrip()
        rejected = text[m.start() :].strip()
        return pack_only + "\n", rejected
    # Notes can stay in pack file lightly — strip Notes for clean SSOT
    m = re.search(r"(?m)^## Notes\b", text)
    if m:
        return text[: m.start()].rstrip() + "\n", text[m.start() :].strip()
    return text.rstrip() + "\n", ""


def main():
    objective = (ROOT / "goal" / "OBJECTIVE.md").read_text(encoding="utf-8").strip()
    plan = (ROOT / "goal" / "plan.md").read_text(encoding="utf-8")
    pack = PACK.read_text(encoding="utf-8")
    # snapshot before critic
    (ROOT / "goal" / "rule_pack_before_critic.md").write_text(pack, encoding="utf-8")

    tmpl = (ROOT / "goal" / "pack_critic_prompt.md").read_text(encoding="utf-8")
    prompt = (
        tmpl.replace("{OBJECTIVE}", objective)
        .replace("{SAFETY}", plan_section(plan, "Safety rules"))
        .replace("{NON_GOALS}", plan_section(plan, "Non-goals"))
        .replace("{SAMPLE}", sample_block())
        .replace("{PACK}", pack)
    )
    print(f"prompt_chars={len(prompt)}")
    out = chat(prompt, max_tokens=2000)

    report_path = ROOT / "goal" / "rule_pack_critic_report.md"
    report_path.write_text(out.rstrip() + "\n", encoding="utf-8")

    pack_body, rest = strip_to_pack(out)
    pack_body = re.sub(r"(?m)^\- \*\*verdict\*\*:.*\n?", "", pack_body)
    PACK.write_text(pack_body, encoding="utf-8")
    print(out)
    print(f"\nwrote {PACK}")
    print(f"report {report_path}")
    print(f"before  goal/rule_pack_before_critic.md")
    if rest:
        print("--- critic tail (rejected/notes) kept in report only ---")


if __name__ == "__main__":
    main()
