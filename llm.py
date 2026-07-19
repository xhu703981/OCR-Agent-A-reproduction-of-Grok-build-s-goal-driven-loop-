import requests
import dspy
from types import SimpleNamespace
from dspy.clients.base_lm import BaseLM

class LocalLM(BaseLM):

    def __init__(self, model="qwen3:8b", api_base = "http://localhost:11434",  temperature=0.1, max_tokens=1000):
        super().__init__(
            model=f"ollama_chat/{model}",
            model_type="chat",
            temperature=temperature,
            max_tokens=max_tokens,
            cache=False,
        )
        self.model_tag = model
        self.api_base = api_base
    

    def forward(self, prompt = None, messages = None, **kwargs):
        merged = {**self.kwargs, **kwargs}
        messages = messages or [{"role": "user", "content": prompt or ""}]
        # convert input from dspy to playload (json) that LLM reads
        payload = {
            "model": self.model_tag,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": merged.get("temperature", 0.1),
                "num_predict": merged.get("max_tokens", 800),
            },
        }

        # trust_env=False: system HTTP_PROXY breaks localhost Ollama
        s = requests.Session()
        s.trust_env = False
        r = s.post(f"{self.api_base}/api/chat", json=payload, timeout=300)
        r.raise_for_status()
        data = r.json()
        content = data.get("message", {}).get("content", "")

        # convert back to format that dspy accepts
        return SimpleNamespace(
            model=f"ollama_chat/{self.model_tag}",
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=content,
                        reasoning_content=None,
                        tool_calls=None,
                    ),
                    finish_reason=data.get("done_reason", "stop"),
                )
            ],
            usage={
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            _hidden_params={},
        )
