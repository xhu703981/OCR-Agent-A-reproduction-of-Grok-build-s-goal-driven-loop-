"""
Merge step: run only rules listed in manifest.json (passed the gate).

Not LLM merge — just call each module's fix_text in order.
Assume manifest + rule modules exist.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

DIR = Path(__file__).resolve().parent
MANIFEST = DIR / "manifest.json"


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def active_rule_ids() -> list[str]:
    data = json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    return list(data["rules"])


def fix_text(text: str) -> str:
    for rid in active_rule_ids():
        mod = _load(DIR / f"{rid}.py")
        text = mod.fix_text(text)
    return text


if __name__ == "__main__":
    demo = 'f0x “ﬁle” a....b fooBar 1O2'
    print("active:", active_rule_ids())
    print("in :", demo)
    print("out:", fix_text(demo))
