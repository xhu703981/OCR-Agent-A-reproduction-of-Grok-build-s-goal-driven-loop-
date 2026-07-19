"""
Programmer: pack rule -> LLM module -> gate -> dry-run -> code critic.

Only rules that pass gate + critic land in rules/manifest.json.
Edit constants below (no CLI). Assume paths/data exist.

Control flow:
  for each rule in pack:
      while not accepted (max MAX_ROUNDS):
          codegen -> gate -> dry_run -> critic
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from ollama_chat import chat
from sample_data import format_batch_md, load_train

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "goal" / "rule_pack.md"
RULES_DIR = ROOT / "rules"
MANIFEST = RULES_DIR / "manifest.json"
REPORT_DIR = ROOT / "goal" / "prog_reports"
GAPS_PATH = ROOT / "goal" / "gaps.json"

PROGRAMMER_MODEL = "qwen2.5-coder:14b"
MAX_ROUNDS = 3
DRY_N = 12
MAX_SNIP = 280
ONLY_RULES: list[str] = []  # empty = all pack rules


def parse_pack(pack: str) -> list[tuple[str, str]]:
    rules = []
    for part in re.split(r"(?m)^## ", pack)[1:]:
        name, _, body = part.partition("\n")
        name = name.strip()
        if name and name.lower() != "notes":
            rules.append((name, body.strip()))
    return rules


def extract_python(text: str) -> str:
    text = text.strip()
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, flags=re.S)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?m)^(import |from |RULE_ID|def |CASES)", text)
    return text[m.start() :].strip() if m else text


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sample_block(n: int = 6) -> str:
    rows = load_train()
    md, _ = format_batch_md(rows[:n], max_chars=MAX_SNIP)
    return md


def dry_run(path: Path, n: int = DRY_N) -> str:
    """Run fix_text on train snippets; report changes for the critic."""
    mod = load_module(path)
    rows = load_train()
    if len(rows) > n:
        step = max(1, len(rows) // n)
        rows = [rows[i * step] for i in range(n)]
    else:
        rows = rows[:n]

    lines = []
    changed = 0
    for r in rows:
        t = r["text"]
        out = mod.fix_text(t)
        if out != t:
            changed += 1
            diff = f"len {len(t)}->{len(out)}"
            for i, (a, b) in enumerate(zip(t, out)):
                if a != b:
                    lo, hi = max(0, i - 35), min(len(t), i + 35)
                    diff = f"in={t[lo:hi]!r} out={out[lo:hi]!r}"
                    break
            lines.append(f"- {r['id']}: {diff}")
    head = f"changed {changed}/{len(rows)} sampled snippets"
    if not lines:
        return head + "\n(no changes on sample)"
    return head + "\n" + "\n".join(lines[:8])


def gate_module(path: Path) -> str | None:
    smoke_in = "The number 100 and file names. \u00a31 1s. a year. well-known."
    try:
        mod = load_module(path)
        smoke_out = mod.fix_text(smoke_in)
    except Exception as e:
        return f"smoke failed: {e}"
    if "\u00a31 15." in smoke_out:
        return "smoke false-positive: damaged currency '1s.'"
    if "wellknown" in smoke_out and "well-known" in smoke_in:
        return "smoke false-positive: joined 'well-known'"
    return None


def parse_verdict(md: str) -> tuple[str, str]:
    m = re.search(r"\*\*verdict\*\*:\s*(accept|reject|revise)", md, flags=re.I)
    v = m.group(1).lower() if m else "reject"
    return v, md


def _goal_gaps_block() -> str:
    data = json.loads(GAPS_PATH.read_text(encoding="utf-8"))
    gaps = data.get("gaps") or []
    if not gaps:
        return ""
    lines = "\n".join(f"- {g}" for g in gaps[:16])
    src = data.get("source") or "?"
    return (
        f"\n\n## Open goal gaps (source={src})\n"
        f"Address these if this rule can help.\n"
        f"{lines}\n"
    )


def generate_code(rule_id: str, body: str, feedback: str = "") -> str:
    tmpl = (ROOT / "goal" / "programmer_prompt.md").read_text(encoding="utf-8")
    prompt = (
        tmpl.replace("{RULE_ID}", rule_id)
        .replace("{RULE_BODY}", body)
        .replace("{SAMPLES}", sample_block(5))
    )
    try:
        prompt += _goal_gaps_block()
    except FileNotFoundError:
        pass
    if feedback:
        prompt += (
            f"\n\n## Critic / gate feedback from last attempt\n{feedback}\n"
            "Rewrite the full module."
        )
    raw = chat(
        prompt,
        max_tokens=1400,
        temperature=0.15,
        think=False,
        model=PROGRAMMER_MODEL,
    )
    return extract_python(raw)


def critic_code(rule_id: str, body: str, code: str, gate: str, dry: str) -> tuple[str, str]:
    tmpl = (ROOT / "goal" / "programmer_critic_prompt.md").read_text(encoding="utf-8")
    prompt = (
        tmpl.replace("{RULE_ID}", rule_id)
        .replace("{RULE_BODY}", body)
        .replace("{CODE}", code)
        .replace("{GATE}", gate)
        .replace("{DRY_RUN}", dry)
    )
    md = chat(
        prompt,
        max_tokens=900,
        temperature=0.1,
        think=False,
        model=PROGRAMMER_MODEL,
    )
    return parse_verdict(md)


def program_one(rule_id: str, body: str) -> bool:
    """
    One rule: while not accepted, keep trying (capped by MAX_ROUNDS).
    On success leave rules/<id>.py; on failure delete it.
    """
    feedback = ""
    path = RULES_DIR / f"{rule_id}.py"
    rnd = 0
    accepted = False

    while not accepted:
        rnd += 1
        if rnd > MAX_ROUNDS:
            break

        print(f"  [{rule_id}] attempt {rnd}/{MAX_ROUNDS}")
        src = generate_code(rule_id, body, feedback)
        path.write_text(src.rstrip() + "\n", encoding="utf-8")

        gate_err = gate_module(path)
        gate_msg = "PASS" if gate_err is None else f"FAIL: {gate_err}"
        print(f"  gate: {gate_msg}")
        dry = dry_run(path) if gate_err is None else "(skipped dry-run; gate failed)"
        if gate_err is None:
            print(f"  dry-run: {dry.splitlines()[0]}")

        verdict, report = critic_code(rule_id, body, src, gate_msg, dry)
        (REPORT_DIR / f"{rule_id}_r{rnd}.md").write_text(report + "\n", encoding="utf-8")
        print(f"  critic: {verdict}")

        if gate_err is None and verdict == "accept":
            accepted = True
        else:
            feedback = f"gate: {gate_msg}\ncritic:\n{report}\ndry-run:\n{dry}"
            if gate_err:
                feedback = f"Gate failed: {gate_err}\n" + feedback

    if not accepted:
        path.unlink()
    return accepted


def write_manifest(passed: list[str]) -> None:
    MANIFEST.write_text(
        json.dumps({"rules": passed}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    pack_rules = parse_pack(PACK.read_text(encoding="utf-8"))
    if ONLY_RULES:
        pack_rules = [(i, b) for i, b in pack_rules if i in set(ONLY_RULES)]

    print("pack:", [i for i, _ in pack_rules])
    print(f"programmer model: {PROGRAMMER_MODEL}")
    passed: list[str] = []
    failed: list[str] = []

    # Outer for: each rule. Inner while (in program_one): until accept.
    for rule_id, body in pack_rules:
        print(f"\n=== program {rule_id} ===")
        if program_one(rule_id, body):
            print(f"PASS {rule_id}")
            passed.append(rule_id)
        else:
            print(f"FAIL {rule_id}")
            failed.append(rule_id)

    write_manifest(passed)
    print(f"\nmanifest ({len(passed)}): {passed}")
    print(f"failed: {failed}")


if __name__ == "__main__":
    main()
