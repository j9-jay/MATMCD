"""Local-only counterpart of inquire_LLMs; not injected into official modules."""
import httpx
from openai import OpenAI

from local_llm_runtime import CONFIG, base_url


class LocalLLMClient:
    def __init__(self, *, max_tokens, seed, sampling=None, response_callback=None):
        if not 0 < max_tokens < CONFIG["server"]["context_tokens"]:
            raise ValueError("Explicit output budget must fit the configured context")
        self.max_tokens = max_tokens
        self.seed = seed
        self.thinking = CONFIG["server"]["thinking"]
        if type(self.thinking) is not bool:
            raise ValueError("An explicit thinking mode is required")
        self.sampling = dict(sampling or {})
        if set(self.sampling) - {"top_p", "top_k", "min_p", "presence_penalty"}:
            raise ValueError("Unsupported sampling override")
        self.response_callback = response_callback
        self.last_response = None
        self.last_request = None
        self.client = OpenAI(base_url=base_url() + "/v1", api_key="local-only-not-a-secret",
                             max_retries=0, timeout=300,
                             http_client=httpx.Client(trust_env=False))

    def inquire_LLMs(self, prompt: str, system_prompt: str, temperature: float = 0.5):
        return self.inquire_messages(
            [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            temperature=temperature)

    def inquire_messages(self, messages, *, temperature):
        extra = {"chat_template_kwargs": {"enable_thinking": self.thinking}, "reasoning_format": CONFIG["server"]["reasoning_format"],
                 "cache_prompt": True}
        standard = {}
        for key, value in self.sampling.items():
            (extra if key in {"top_k", "min_p"} else standard)[key] = value
        self.last_request = dict(
            model=CONFIG["model"]["server_alias"],
            messages=messages,
            temperature=temperature, max_tokens=self.max_tokens, seed=self.seed, extra_body=extra, **standard)
        response = self.client.chat.completions.create(**self.last_request)
        self.last_response = response.model_dump()
        if self.response_callback:
            self.response_callback(self.last_response)
        choice = response.choices[0]
        if choice.finish_reason != "stop":
            raise RuntimeError(f"Incomplete local response: finish_reason={choice.finish_reason}; no retry or truncation workaround")
        message = choice.message.model_dump()
        content = message.get("content")
        if not content:
            raise RuntimeError("Final content missing")
        if self.thinking and not message.get("reasoning_content"):
            raise RuntimeError("Thinking/final content separation missing")
        if not self.thinking and (message.get("reasoning_content") or "").strip():
            raise RuntimeError("Unexpected thinking content in non-thinking mode")
        if "<think>" in content or "</think>" in content:
            raise RuntimeError("Thinking tags leaked into final answer")
        return content

    def close(self):
        self.client.close()
