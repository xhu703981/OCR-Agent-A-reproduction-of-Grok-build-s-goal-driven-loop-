"""
Programmer: pack rule -> LLM module -> gate -> dry-run -> code critic.

Only rules that pass gate (+ critic, or soft-accept) land in rules/manifest.json.
Gate enforces local safety via CASES equality + known smoke false-positives.
Critic/soft-accept bias: ship more narrow-but-safe rules; do not demand ultra-generality.

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

PROGRAMMER_MODEL = "grok-4.3"  # stronger codegen; pack/judge use 4.20
MAX_ROUNDS = 3  # one more try per rule this re-pass
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


def _context_hints(text: str) -> str:
    """
    Cheap genre/domain cues for the code critic (not a classifier).
    Helps judge whether a dry-run edit fits the passage context.
    """
    t = text
    low = text.lower()
    tags: list[str] = []
    # music / lyrics / syllable hyphens (avoid biblio "pp." = pages)
    if re.search(
        r"(?<![A-Za-z])(mf|ff|cresc|allegro|andante|tempo|verse|chorus|sing|sung)(?![A-Za-z])",
        low,
    ) or re.search(r"(?<![A-Za-z])pp(?![A-Za-z.])", low) or re.search(
        r"\b\w{1,3}-\s+\w{1,3}-\s+\w", t
    ):
        tags.append("music/lyrics?")
    # bibliography / catalog
    if re.search(r"(?<![A-Za-z])(\d+to|\d+vo|pp\.|vol\.|ibid|op\.\s*cit)", low) or re.search(
        r"(?<![A-Za-z])(8vo|4to)(?![A-Za-z])", low
    ):
        tags.append("biblio/catalog?")
    # dictionary / glossary (abbr. with period; no trailing \b after '.')
    if re.search(r"(?<![A-Za-z])(adj|n|v|adv|pl|cf)\.(?![A-Za-z])", low) and low.count(
        "\n"
    ) < 8:
        tags.append("dictionary?")
    # Old / Middle English / scholarly diplomatic
    if re.search(r"[þðæœſÞÐÆŒ]", t) or re.search(
        r"(?<![A-Za-z])(þe|þat|ȝe|hwæt)(?![A-Za-z])", low
    ):
        tags.append("historical/OE?")
    # tables / numeric layout
    if re.search(r"(\t|\s{3,}\d|\d+\.\d+\s+\d+)", t) and sum(c.isdigit() for c in t) > 12:
        tags.append("table/numeric?")
    # code-ish / pure alnum noise
    if re.search(r"[A-Za-z]{2,}\d{3,}|\d{3,}[A-Za-z]{2,}", t) and " " not in t[:40]:
        tags.append("token/id?")
    if not tags:
        tags.append("prose?")
    return ",".join(tags)


def dry_run(path: Path, n: int = DRY_N) -> str:
    """
    Run fix_text on train snippets; report changes + context hints for the critic.
    Critic should ask: does this edit fit THIS passage's genre/domain?
    """
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
                    lo, hi = max(0, i - 55), min(len(t), i + 55)
                    lo2, hi2 = max(0, i - 55), min(len(out), i + 55)
                    book = r["id"].split(":")[0] if ":" in r["id"] else r["id"]
                    ctx = _context_hints(t)
                    # short whole-snippet head so critic sees register, not only the edit window
                    head_snip = t[:120].replace("\n", " ")
                    if len(t) > 120:
                        head_snip += "…"
                    diff = (
                        f"book={book} ctx=[{ctx}]\n"
                        f"  snippet_head: {head_snip!r}\n"
                        f"  in={t[lo:hi]!r}\n"
                        f"  out={out[lo2:hi2]!r}"
                    )
                    break
            lines.append(f"- {r['id']}: {diff}")
    head = (
        f"changed {changed}/{len(rows)} sampled snippets\n"
        "For each change, judge CONTEXT FIT: would this edit be correct in this "
        "book/passage genre (prose vs music/lyrics, biblio, dictionary, OE, table)?"
    )
    if not lines:
        return head + "\n(no changes on sample)"
    return head + "\n" + "\n".join(lines[:8])


def gate_module(path: Path) -> str | None:
    """
    Mechanical safety gate (local safety):
    - module loads; smoke does not hit known collateral failures
    - CASES must hold exactly (positives fix; negatives unchanged)
    """
    smoke_in = (
        "The number 100 and ﬁle names. \u00a31 1s. a year. well-known. "
        "suﬃcient ﬂuid deﬂection."
    )
    try:
        mod = load_module(path)
        if not callable(getattr(mod, "fix_text", None)):
            return "missing fix_text"
        smoke_out = mod.fix_text(smoke_in)
        cases = getattr(mod, "CASES", None) or []
        if len(cases) < 2:
            return "CASES: need at least 2 (include ≥1 negative that must not change)"
        for i, pair in enumerate(cases[:8]):
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                return f"CASES[{i}] malformed (want (in, out))"
            a, b = pair
            got = mod.fix_text(a)
            if got != b:
                return f"CASES[{i}] fail: in={a!r} expected={b!r} got={got!r}"
    except Exception as e:
        return f"smoke failed: {e}"
    if "\u00a31 15." in smoke_out:
        return "smoke false-positive: damaged currency '1s.'"
    if "wellknown" in smoke_out and "well-known" in smoke_in:
        return "smoke false-positive: joined 'well-known'"
    return None


def _soft_accept(verdict: str, report: str, dry: str) -> bool:
    """
    Soft-accept only when critic is over-strict about abstract purity,
    not when the rule is a hollow/instance hack.

    ALLOW soft-accept (narrow but structural): critic mainly says too specific /
    not abstract enough / would need more unseen coverage — and no damage signal.

    NEVER soft-accept: hardcoded / instance-only / zero-change / no-op / tiny
    static word-list as the whole rule (those must hard-fail or revise).
    """
    if verdict == "accept":
        return True
    if verdict not in ("reject", "revise"):
        return False
    blob = f"{report}\n{dry}".lower()

    # Hard no: collateral damage or wrong-context edits
    damage_keys = (
        "damage",
        "false positive",
        "false-positive",
        "mangles",
        "corrupt",
        "breaks negative",
        "currency",
        "wellknown",
        "1s.",
        "collateral",
        "context_fit**: bad",
        "context_fit: bad",
        "context-blind",
        "wrong context",
        "lyrics",
        "music/",
        "biblio",
        "4to",
        "8vo",
        "dictionary",
        "historical/oe",
    )
    if any(k in blob for k in damage_keys):
        return False

    # Hard no: hollow / instance / pure dict — do NOT soft-pass these
    hollow_keys = (
        "instance-only",
        "instance only",
        "instance-specific",
        "hardcoded",
        "hard-coded",
        "tiny static",
        "static word",
        "word list",
        "lookup table",
        "only the case",
        "only cases",
        "only the cases",
        "no-op",
        "noop",
        "zero change",
        "zero changes",
        "no changes on sample",
        "no changes on",
        "changed 0/",
        "changed 0 ",
        "ineffective",
        "does nothing",
    )
    if any(k in blob for k in hollow_keys):
        return False

    # Soft yes: critic only objects to insufficient abstract generality
    narrow_but_structural = (
        "too specific",
        "not general",
        "non-general",
        "not reusable",
        "would work on unseen",
        "more general",
        "broader pattern",
        "overly narrow",
        "narrow pattern",
        "not abstract",
    )
    return any(k in blob for k in narrow_but_structural)


def parse_verdict(md: str) -> tuple[str, str]:
    m = re.search(r"\*\*verdict\*\*:\s*(accept|reject|revise)", md, flags=re.I)
    v = m.group(1).lower() if m else "reject"
    return v, md


def _goal_gaps_block() -> str:
    data = json.loads(GAPS_PATH.read_text(encoding="utf-8"))
    gaps = data.get("gaps") or []
    prior = data.get("prior_gaps") or []
    if not gaps and not prior:
        return ""
    parts = ["\n\n## Open goal gaps (fix these; do not invent new exam cases)\n"]
    if gaps:
        parts.append("Current:\n" + "\n".join(f"- {g}" for g in gaps[:16]) + "\n")
    if prior:
        parts.append(
            "Prior round (anti-ratchet — still check these first):\n"
            + "\n".join(f"- {g}" for g in prior[:12])
            + "\n"
        )
    note = data.get("strategy_path")
    if note:
        parts.append(f"Strategy note path: {note}\n")
    return "".join(parts)


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

        if gate_err is None and _soft_accept(verdict, report, dry):
            if verdict != "accept":
                print(f"  soft-accept (gate+CASES ok; critic was {verdict}, no damage signal)")
            accepted = True
        else:
            feedback = f"gate: {gate_msg}\ncritic:\n{report}\ndry-run:\n{dry}"
            if gate_err:
                feedback = f"Gate failed: {gate_err}\n" + feedback

    if not accepted:
        path.unlink()
    return accepted


def _load_manifest_rules() -> list[str]:
    if not MANIFEST.is_file():
        return []
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    rules = data.get("rules") if isinstance(data, dict) else None
    return list(rules) if isinstance(rules, list) else []


def write_manifest(passed: list[str], *, attempted: list[str]) -> None:
    """
    Merge into existing manifest instead of clobbering.

    - Keep prior rules that still have rules/<id>.py and were not re-attempted.
    - Drop re-attempted failures (file already deleted by program_one).
    - Append newly passed ids (pack order for attempted; prior order for kept).
    """
    prior = _load_manifest_rules()
    att = set(attempted)
    kept: list[str] = []
    for rid in prior:
        if rid in att:
            continue
        if (RULES_DIR / f"{rid}.py").is_file():
            kept.append(rid)
    merged: list[str] = []
    seen: set[str] = set()
    for rid in kept + list(passed):
        if rid in seen:
            continue
        if not (RULES_DIR / f"{rid}.py").is_file():
            continue
        seen.add(rid)
        merged.append(rid)
    MANIFEST.write_text(
        json.dumps({"rules": merged}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"manifest merge: prior={prior} + passed={passed} → {merged}")


def _drop_blamed_worse_rules() -> list[str]:
    """
    If goal gaps blame specific rules for ocr_worse, remove them from manifest
    before re-programming. Runtime re-verifies n_worse==0 after.
    """
    if not GAPS_PATH.is_file():
        return []
    try:
        data = json.loads(GAPS_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    gaps = data.get("gaps") or []
    blob = " ".join(str(g) for g in gaps)
    if "ocr_worse" not in blob and "n_worse=" not in blob:
        return []
    blamed: list[str] = []
    for g in gaps:
        m = re.search(
            r"blame rules[^:]*:\s*(.+)$",
            str(g),
            flags=re.I,
        )
        if not m:
            continue
        for part in re.split(r"[,;]", m.group(1)):
            rid = part.strip().strip("`")
            if rid and re.match(r"^[A-Za-z0-9_]+$", rid):
                blamed.append(rid)
    if not blamed:
        return []
    prior = _load_manifest_rules()
    kept = [r for r in prior if r not in set(blamed)]
    dropped = [r for r in prior if r in set(blamed)]
    if dropped:
        MANIFEST.write_text(
            json.dumps({"rules": kept}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        for rid in dropped:
            p = RULES_DIR / f"{rid}.py"
            # keep .py on disk for history; only unship
            print(f"  unship (ocr_worse blame): {rid}")
        print(f"manifest after unship blame: {kept}")
    return dropped


def main():
    dropped = _drop_blamed_worse_rules()
    # Worse repair: unship only, then let runtime re-verify n_worse.
    # Do NOT re-program the whole pack here — write_manifest(attempted=all)
    # would wipe prior PASS rules that fail critic on a random re-roll.
    if dropped:
        print(
            f"ocr_worse unship-only done ({len(dropped)}): {dropped}; "
            "skip full pack reprogram"
        )
        print(f"manifest now: {_load_manifest_rules()}")
        return

    pack_rules = parse_pack(PACK.read_text(encoding="utf-8"))
    if ONLY_RULES:
        pack_rules = [(i, b) for i, b in pack_rules if i in set(ONLY_RULES)]

    print("pack:", [i for i, _ in pack_rules])
    print(f"programmer model: {PROGRAMMER_MODEL}")
    print(f"manifest before: {_load_manifest_rules()}")
    passed: list[str] = []
    failed: list[str] = []
    attempted: list[str] = []

    # Outer for: each rule. Inner while (in program_one): until accept.
    for rule_id, body in pack_rules:
        attempted.append(rule_id)
        print(f"\n=== program {rule_id} ===")
        if program_one(rule_id, body):
            print(f"PASS {rule_id}")
            passed.append(rule_id)
        else:
            print(f"FAIL {rule_id}")
            failed.append(rule_id)

    write_manifest(passed, attempted=attempted)
    print(f"\nthis pass passed ({len(passed)}): {passed}")
    print(f"this pass failed: {failed}")
    print(f"manifest now: {_load_manifest_rules()}")


if __name__ == "__main__":
    main()
