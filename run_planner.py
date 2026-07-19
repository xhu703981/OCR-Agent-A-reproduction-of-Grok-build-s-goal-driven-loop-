"""Run global planner: goal/OBJECTIVE.md -> goal/plan.md"""

from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
MODEL = "qwen3:8b"
API = "http://localhost:11434"


def main():
    objective = (ROOT / "goal" / "OBJECTIVE.md").read_text(encoding="utf-8")  #global objective
    template = (ROOT / "goal" / "planner_prompt.md").read_text(encoding="utf-8")
    prompt = template.replace("{OBJECTIVE}", objective)

    # trust_env=False: system HTTP_PROXY breaks localhost Ollama
    s = requests.Session()
    s.trust_env = False

    r = s.post(
        f"{API}/api/chat",
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "options": {"temperature": 0.2, "num_predict": 3500},
        },
        timeout=600,
    )
    r.raise_for_status()
    plan = r.json()["message"]["content"].strip()

    out = ROOT / "goal" / "plan.md"
    out.write_text(plan + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
