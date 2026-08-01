"""Chat helper — xAI Grok API (OpenAI-compatible).

  chat(prompt, model=..., max_tokens=..., temperature=...)

Reads GROK_API from env or project .env. Assumes the call succeeds.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
API = "https://api.x.ai/v1/chat/completions"
MODEL = "grok-4.20-0309-non-reasoning"
TIMEOUT_S = 180


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def chat(
    prompt: str,
    *,
    max_tokens: int = 1800,
    temperature: float = 0.2,
    think: bool = False,
    model: str | None = None,
) -> str:
    del think
    _load_dotenv()
    r = requests.post(
        API,
        headers={
            "Authorization": f"Bearer {os.environ['GROK_API']}",
            "Content-Type": "application/json",
        },
        json={
            "model": model or MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=TIMEOUT_S,
    )
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    return (msg.get("content") or "").strip()
