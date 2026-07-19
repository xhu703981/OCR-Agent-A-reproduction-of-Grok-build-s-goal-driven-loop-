"""Minimal local Ollama chat helper."""

import requests

MODEL = "qwen3:8b"
API = "http://localhost:11434"


def chat(
    prompt: str,
    *,
    max_tokens: int = 1800,
    temperature: float = 0.2,
    think: bool = False,
    model: str | None = None,
) -> str:
    s = requests.Session()
    s.trust_env = False  # system proxy breaks localhost
    r = s.post(
        f"{API}/api/chat",
        json={
            "model": model or MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": think,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        },
        timeout=600,
    )
    r.raise_for_status()
    msg = r.json().get("message") or {}
    content = (msg.get("content") or "").strip()
    if not content and msg.get("thinking"):
        content = str(msg["thinking"]).strip()
    return content
