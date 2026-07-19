"""Smoke: apply_all on train + a synthetic string."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("apply_all", ROOT / "rules" / "apply_all.py")
mod = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(mod)

print("active:", mod.active_rule_ids())

demo = 'f0x “ﬁle” a....b fooBar 1O2'
print("\nDEMO")
print(" in:", demo)
print("out:", mod.fix_text(demo))

syn = "f0x eﬃcient 1O2 a......b indefi-\nnitely \"c0de\""
print("\nSYNTHETIC")
print(" in:", repr(syn))
print("out:", repr(mod.fix_text(syn)))

from sample_data import load_train

rows = load_train()
changed = 0
shown = 0
for r in rows:
    t = r["text"]
    out = mod.fix_text(t)
    if out == t:
        continue
    changed += 1
    if shown < 5:
        shown += 1
        print(f"\n--- train {r['id']} ---")
        for i, (a, b) in enumerate(zip(t, out)):
            if a != b:
                lo, hi = max(0, i - 50), min(len(t), i + 50)
                print(" in:", repr(t[lo:hi]))
                print("out:", repr(out[lo:hi]))
                break
        if len(out) != len(t) and shown <= 5:
            # length change without zip hit at end
            pass

print(f"\ntrain: {len(rows)} snippets, changed: {changed}")
