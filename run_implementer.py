"""
Implementer agent loop: observe tool results → choose next tool → execute → repeat.

  python run_implementer.py

This is the "tool-using implementer" control structure:
  history of (action, result) is fed back each step — not a one-shot chat.

Edit constants below. Assume paths/data exist.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from ollama_chat import chat
from sample_data import load_train

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "goal" / "rule_pack.md"
RULES_DIR = ROOT / "rules"
MANIFEST = RULES_DIR / "manifest.json"
GAPS_PATH = ROOT / "goal" / "gaps.json"
OBJECTIVE = ROOT / "goal" / "OBJECTIVE.md"
LOG_PATH = ROOT / "goal" / "implementer_log.jsonl"
PROMPT_PATH = ROOT / "goal" / "implementer_prompt.md"

IMPLEMENTER_MODEL = "grok-4.3"
MAX_STEPS = 12
HISTORY_CHARS = 12000


def _load_manifest() -> list[str]:
    if not MANIFEST.is_file():
        return []
    data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    return list(data.get("rules") or [])


def _write_manifest(rules: list[str]) -> None:
    MANIFEST.write_text(
        json.dumps({"rules": rules}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _pack_ids() -> list[str]:
    if not PACK.is_file():
        return []
    ids = []
    for part in re.split(r"(?m)^## ", PACK.read_text(encoding="utf-8"))[1:]:
        name = part.split("\n", 1)[0].strip()
        if name and name.lower() != "notes":
            ids.append(name)
    return ids


def _gaps_text() -> str:
    if not GAPS_PATH.is_file():
        return "(none)"
    try:
        data = json.loads(GAPS_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return "(none)"
    gaps = data.get("gaps") or []
    prior = data.get("prior_gaps") or []
    lines = []
    if gaps:
        lines.append("current:\n" + "\n".join(f"- {g}" for g in gaps[:16]))
    if prior:
        lines.append("prior:\n" + "\n".join(f"- {g}" for g in prior[:12]))
    return "\n".join(lines) if lines else "(none)"


def _objective() -> str:
    if not OBJECTIVE.is_file():
        return "Ship safe OCR fix rules; n_worse==0; real corpus effect."
    for ln in OBJECTIVE.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if s and not s.startswith("#"):
            return s[:500]
    return OBJECTIVE.read_text(encoding="utf-8")[:500]


def _load_mod(rid: str):
    path = RULES_DIR / f"{rid}.py"
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location(rid, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def tool_scan_worse(args: dict) -> str:
    from goal_checklist import scan_ocr_worse

    max_lines = args.get("max_lines")
    if max_lines is not None:
        max_lines = int(max_lines)
    s = scan_ocr_worse(max_lines=max_lines, blame=True)
    return json.dumps(
        {
            "n_scanned": s["n_scanned"],
            "n_changed": s["n_changed"],
            "n_worse": s["n_worse"],
            "n_improved": s["n_improved"],
            "ok": s["ok"],
            "blame_rules": s.get("blame_rules") or [],
            "gap_lines": s.get("gap_lines") or [],
        },
        ensure_ascii=False,
    )


def tool_rule_hits(args: dict) -> str:
    rid = str(args.get("rule_id") or "").strip()
    n = int(args.get("n") or 200)
    if not rid:
        return "error: need rule_id"
    try:
        mod = _load_mod(rid)
    except Exception as e:
        return f"error: load {rid}: {e}"
    rows = load_train()
    if len(rows) > n:
        step = max(1, len(rows) // n)
        rows = [rows[i * step] for i in range(n)]
    ch = 0
    examples = []
    for r in rows:
        t = r["text"]
        try:
            out = mod.fix_text(t)
        except Exception as e:
            return f"error: fix_text raised: {e}"
        if out != t:
            ch += 1
            if len(examples) < 3:
                for i, (a, b) in enumerate(zip(t, out)):
                    if a != b:
                        lo = max(0, i - 35)
                        examples.append(
                            {
                                "id": r["id"],
                                "in": t[lo : i + 35],
                                "out": out[lo : i + 35],
                            }
                        )
                        break
    return json.dumps(
        {"rule_id": rid, "hits": ch, "sample_n": len(rows), "examples": examples},
        ensure_ascii=False,
    )


def tool_read_rule(args: dict) -> str:
    rid = str(args.get("rule_id") or "").strip()
    path = RULES_DIR / f"{rid}.py"
    if not path.is_file():
        return f"error: missing {path.name}"
    text = path.read_text(encoding="utf-8")
    if len(text) > 4000:
        text = text[:4000] + "\n…(truncated)"
    return text


def tool_write_rule(args: dict) -> str:
    """Write rule file + gate; on PASS add to manifest."""
    from run_programmer import extract_python, gate_module, dry_run

    rid = str(args.get("rule_id") or "").strip()
    code = str(args.get("code") or "")
    if not rid or not code:
        return "error: need rule_id and code"
    code = extract_python(code)
    if f'RULE_ID = "{rid}"' not in code and f"RULE_ID = '{rid}'" not in code:
        # soft inject if model forgot exact line
        if "RULE_ID" not in code:
            code = f'RULE_ID = "{rid}"\n\n' + code
    path = RULES_DIR / f"{rid}.py"
    path.write_text(code.rstrip() + "\n", encoding="utf-8")
    err = gate_module(path)
    if err:
        path.unlink(missing_ok=True)
        return f"gate FAIL: {err}"
    dry = dry_run(path, n=8)
    # ship
    man = _load_manifest()
    if rid not in man:
        man.append(rid)
        _write_manifest(man)
    return json.dumps(
        {"status": "shipped", "rule_id": rid, "gate": "PASS", "dry_run": dry[:800]},
        ensure_ascii=False,
    )


def tool_drop_rule(args: dict) -> str:
    rid = str(args.get("rule_id") or "").strip()
    man = _load_manifest()
    if rid not in man:
        return f"not in manifest: {rid} (current={man})"
    man = [x for x in man if x != rid]
    _write_manifest(man)
    return json.dumps({"dropped": rid, "manifest": man}, ensure_ascii=False)


def tool_list_manifest(args: dict) -> str:
    return json.dumps({"manifest": _load_manifest()}, ensure_ascii=False)


def tool_program_pack(args: dict) -> str:
    p = subprocess.run(
        [sys.executable, str(ROOT / "run_programmer.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = ((p.stdout or "") + (p.stderr or ""))[-2500:]
    return f"exit={p.returncode}\nmanifest={_load_manifest()}\n---\n{tail}"


TOOLS = {
    "scan_worse": tool_scan_worse,
    "rule_hits": tool_rule_hits,
    "read_rule": tool_read_rule,
    "write_rule": tool_write_rule,
    "drop_rule": tool_drop_rule,
    "list_manifest": tool_list_manifest,
    "program_pack": tool_program_pack,
}


def _parse_action(raw: str) -> dict:
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.S)
    if m:
        raw = m.group(1)
    else:
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if not m:
            raise ValueError(f"no JSON action in model output:\n{raw[:400]}")
        raw = m.group(0)
    data = json.loads(raw)
    tool = str(data.get("tool") or "").strip()
    args = data.get("args") or {}
    if not isinstance(args, dict):
        args = {}
    why = str(data.get("why") or "")
    return {"tool": tool, "args": args, "why": why}


def _format_history(steps: list[dict]) -> str:
    if not steps:
        return (
            "(none yet — if manifest empty/thin and pack non-empty: start with program_pack; "
            "else list_manifest / rule_hits / scan_worse as needed)"
        )
    parts = []
    for i, s in enumerate(steps, 1):
        res = s.get("result") or ""
        if len(res) > 1500:
            res = res[:1500] + "\n…(truncated)"
        parts.append(
            f"### step {i}\n"
            f"- tool: {s.get('tool')}\n"
            f"- why: {s.get('why')}\n"
            f"- args: {json.dumps(s.get('args') or {}, ensure_ascii=False)[:300]}\n"
            f"- result:\n{res}\n"
        )
    blob = "\n".join(parts)
    if len(blob) > HISTORY_CHARS:
        blob = "…(older truncated)…\n" + blob[-HISTORY_CHARS:]
    return blob


def decide(history: list[dict]) -> dict:
    tmpl = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = (
        tmpl.replace("{OBJECTIVE}", _objective())
        .replace("{GAPS}", _gaps_text())
        .replace("{PACK_IDS}", ", ".join(_pack_ids()) or "(empty)")
        .replace("{MANIFEST}", json.dumps(_load_manifest(), ensure_ascii=False))
        .replace("{HISTORY}", _format_history(history))
    )
    raw = chat(
        prompt,
        max_tokens=2000,
        temperature=0.15,
        think=False,
        model=IMPLEMENTER_MODEL,
    )
    return _parse_action(raw)


def run_loop() -> dict:
    """
    Core control structure:
      history = []
      loop:
        action = LLM(history + gaps + disk)
        result = execute(action)
        history.append(action, result)
    """
    history: list[dict] = []
    LOG_PATH.write_text("", encoding="utf-8")
    print(f"[implementer] start max_steps={MAX_STEPS} model={IMPLEMENTER_MODEL}")
    print(f"[implementer] manifest={_load_manifest()}")

    for step in range(1, MAX_STEPS + 1):
        try:
            action = decide(history)
        except Exception as e:
            print(f"[implementer] decide failed: {e}")
            # fallback: scan once then done
            action = {"tool": "scan_worse", "args": {}, "why": f"fallback after decide error: {e}"}

        tool = action.get("tool") or ""
        args = action.get("args") or {}
        why = action.get("why") or ""
        print(f"[implementer] step {step}/{MAX_STEPS} tool={tool} why={why[:120]}")

        if tool == "done":
            note = args.get("note") or why
            rec = {"tool": "done", "args": args, "why": why, "result": f"done: {note}"}
            history.append(rec)
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"[implementer] done: {note}")
            break

        if tool not in TOOLS:
            result = f"error: unknown tool {tool!r}; pick from {list(TOOLS)}"
        else:
            try:
                result = TOOLS[tool](args)
            except Exception as e:
                result = f"error executing {tool}: {e}"

        print(f"[implementer] result: {str(result)[:300].replace(chr(10), ' ')}")
        rec = {"tool": tool, "args": args, "why": why, "result": result}
        history.append(rec)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # Auto-stop after program_pack if manifest is thick enough
        if tool == "program_pack":
            man = _load_manifest()
            if len(man) >= 3:
                print(f"[implementer] auto-done: program_pack shipped {len(man)} rules")
                break
    else:
        print("[implementer] hit MAX_STEPS")

    summary = {
        "steps": len(history),
        "manifest": _load_manifest(),
        "log": str(LOG_PATH),
    }
    print(f"[implementer] end steps={summary['steps']} manifest={summary['manifest']}")
    return summary


def main() -> None:
    run_loop()


if __name__ == "__main__":
    main()
