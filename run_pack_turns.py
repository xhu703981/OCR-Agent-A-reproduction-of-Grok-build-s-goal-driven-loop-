"""
Multi-epoch rule mining (memory = goal/rule_pack.md).

Each epoch: TURNS_PER_EPOCH delta turns (propose → critic → upsert), then merge.
After all epochs: optional final pack critic. Does not run programmer.

Personal project: edit constants below if something breaks — no CLI, no soft fallbacks.
"""

from __future__ import annotations

import re
from pathlib import Path

from ollama_chat import chat
from sample_data import format_batch_md, load_train

ROOT = Path(__file__).resolve().parent
PACK_PATH = ROOT / "goal" / "rule_pack.md"
TURNS_DIR = ROOT / "goal" / "turns"

N_EPOCHS = 3
TURNS_PER_EPOCH = 3
BATCH_N = 10
MAX_SNIP_CHARS = 400
RESUME_PACK = False


def plan_section(plan: str, title: str) -> str:
    m = re.search(rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)", plan)
    return m.group(1).strip() if m else ""


def fill(template: str, **kw) -> str:
    out = template
    for k, v in kw.items():
        out = out.replace("{" + k + "}", v)
    return out


def pack_index(pack: str) -> str:
    lines = []
    for b in re.split(r"(?m)^## ", pack)[1:]:
        name, _, body = b.partition("\n")
        name = name.strip()
        if name.lower() == "notes":
            continue
        pre = ""
        m = re.search(r"\*\*precondition\*\*:\s*(.+)", body)
        if m:
            pre = m.group(1).strip()[:120]
        pri = ""
        m = re.search(r"\*\*priority\*\*:\s*(\w+)", body)
        if m:
            pri = m.group(1)
        lines.append(f"- `{name}` [{pri or '?'}]: {pre or '—'}")
    return "\n".join(lines) if lines else "(empty)"


def extract_section(md: str, title: str) -> str:
    m = re.search(rf"(?ms)^## {re.escape(title)}\s*\n(.*?)(?=^## |\Z)", md)
    return m.group(1).strip() if m else ""


def parse_apply_rules(verified: str) -> list[tuple[str, str]]:
    apply = extract_section(verified, "Apply")
    rules = []
    for p in re.split(r"(?m)^### ", apply)[1:]:
        name, _, body = p.partition("\n")
        name = name.strip()
        if name:
            rules.append((name, body.strip()))
    return rules


def drop_with_context_dupes(pack: str) -> str:
    parts = re.split(r"(?m)^## ", pack)
    head, sections, order = parts[0], {}, []
    for part in parts[1:]:
        name, _, body = part.partition("\n")
        name = name.strip()
        sections[name] = body
        order.append(name)
    for name in list(sections):
        if name.endswith("_with_context"):
            base = name[: -len("_with_context")]
            if base in sections:
                del sections[name]
                order.remove(name)
    out = [head.rstrip()]
    for name in order:
        if name in sections and name.lower() != "notes":
            out.append(f"## {name}\n{sections[name].rstrip()}")
    return "\n\n".join(out).rstrip() + "\n"


def upsert_pack(pack: str, rules: list[tuple[str, str]]) -> str:
    for name, body in rules:
        section = f"## {name}\n{body.strip()}\n"
        pat = rf"(?ms)^## {re.escape(name)}\s*\n.*?(?=^## |\Z)"
        if re.search(pat, pack):
            pack = re.sub(pat, section + "\n", pack)
        else:
            pack = pack.rstrip() + "\n\n" + section
    return pack.rstrip() + "\n"


def strip_to_rule_pack(text: str) -> str:
    """LLM may chat; keep from '# Rule pack' and drop trailing Notes."""
    i = text.find("# Rule pack")
    if i >= 0:
        text = text[i:]
    m = re.search(r"(?m)^## Notes\b", text)
    if m:
        text = text[: m.start()]
    return drop_with_context_dupes(text.rstrip() + "\n")


def one_delta_turn(
    *,
    epoch: int,
    turn: int,
    global_turn: int,
    rows: list,
    pack: str,
    objective: str,
    acceptance: str,
    safety: str,
    non_goals: str,
    delta_t: str,
    critic_t: str,
) -> str:
    bmd, ids = format_batch_md(
        rows, max_chars=MAX_SNIP_CHARS, start=global_turn * BATCH_N, n=BATCH_N
    )
    idx = pack_index(pack)
    tag = f"e{epoch}_t{turn}"
    print(f"\n===== EPOCH {epoch} TURN {turn}/{TURNS_PER_EPOCH} (global={global_turn}) =====")
    print(f"batch={ids}")
    print(f"pack_index:\n{idx}")

    draft = chat(
        fill(
            delta_t,
            OBJECTIVE=objective,
            ACCEPTANCE=acceptance,
            SAFETY=safety,
            NON_GOALS=non_goals,
            PACK_INDEX=idx,
            BATCH=bmd,
        ),
        max_tokens=1400,
    )
    (TURNS_DIR / f"{tag}_delta_draft.md").write_text(draft + "\n", encoding="utf-8")

    verified = chat(
        fill(
            critic_t,
            OBJECTIVE=objective,
            SAFETY=safety,
            NON_GOALS=non_goals,
            PACK_INDEX=idx,
            BATCH=bmd,
            DRAFT=draft,
        ),
        max_tokens=1600,
    )
    (TURNS_DIR / f"{tag}_delta_verified.md").write_text(verified + "\n", encoding="utf-8")

    applied = parse_apply_rules(verified)
    print(f"apply {len(applied)}: {[n for n, _ in applied]}")
    pack = upsert_pack(pack, applied)
    PACK_PATH.write_text(pack, encoding="utf-8")
    print(f"pack now:\n{pack_index(pack)}")
    return pack


def reconcile(pack: str, objective: str, safety: str, non_goals: str, recon_t: str) -> str:
    raw = chat(
        fill(
            recon_t,
            OBJECTIVE=objective,
            SAFETY=safety,
            NON_GOALS=non_goals,
            PACK=pack,
        ),
        max_tokens=2000,
    )
    return strip_to_rule_pack(raw)


def main():
    TURNS_DIR.mkdir(parents=True, exist_ok=True)

    objective = (ROOT / "goal" / "OBJECTIVE.md").read_text(encoding="utf-8").strip()
    plan = (ROOT / "goal" / "plan.md").read_text(encoding="utf-8")
    acceptance = plan_section(plan, "Acceptance criteria")
    safety = plan_section(plan, "Safety rules")
    non_goals = plan_section(plan, "Non-goals")
    delta_t = (ROOT / "goal" / "delta_prompt.md").read_text(encoding="utf-8")
    critic_t = (ROOT / "goal" / "delta_critic_prompt.md").read_text(encoding="utf-8")
    recon_t = (ROOT / "goal" / "reconcile_prompt.md").read_text(encoding="utf-8")

    rows = load_train()
    pack = PACK_PATH.read_text(encoding="utf-8") if RESUME_PACK else "# Rule pack\n"
    if not RESUME_PACK:
        PACK_PATH.write_text(pack, encoding="utf-8")

    print(
        f"train={len(rows)} epochs={N_EPOCHS} turns/epoch={TURNS_PER_EPOCH} "
        f"batch_n={BATCH_N} resume={RESUME_PACK}"
    )

    global_turn = 0
    for epoch in range(1, N_EPOCHS + 1):
        print(f"\n EPOCH {epoch}/{N_EPOCHS} ")
        for turn in range(1, TURNS_PER_EPOCH + 1):
            pack = one_delta_turn(
                epoch=epoch,
                turn=turn,
                global_turn=global_turn,
                rows=rows,
                pack=pack,
                objective=objective,
                acceptance=acceptance,
                safety=safety,
                non_goals=non_goals,
                delta_t=delta_t,
                critic_t=critic_t,
            )
            global_turn += 1

        print(f"\n===== MERGE after epoch {epoch} =====")
        (TURNS_DIR / f"e{epoch}_pre_merge.md").write_text(pack, encoding="utf-8")
        pack = reconcile(pack, objective, safety, non_goals, recon_t)
        PACK_PATH.write_text(pack, encoding="utf-8")
        (TURNS_DIR / f"e{epoch}_post_merge.md").write_text(pack, encoding="utf-8")
        print(f"merged pack:\n{pack_index(pack)}")

    print(f"\n===== DONE pack → {PACK_PATH} =====")
    from run_pack_critic import main as pack_critic_main

    pack_critic_main()


if __name__ == "__main__":
    main()
