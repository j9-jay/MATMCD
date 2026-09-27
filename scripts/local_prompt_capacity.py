"""Measure exact pinned GGUF chat tokens without generating an answer."""
import hashlib

import httpx

from local_llm_runtime import CONFIG, base_url


class PromptCapacityError(ValueError):
    pass


def measure_messages(messages, *, max_tokens, client=None):
    owned = client is None
    client = client or httpx.Client(base_url=base_url(), trust_env=False, timeout=60)
    try:
        response = client.post("/apply-template", json={"messages": messages,
                               "chat_template_kwargs": {"enable_thinking": CONFIG["server"]["thinking"]}})
        response.raise_for_status()
        prompt = response.json()["prompt"]
        response = client.post("/tokenize", json={"content": prompt, "add_special": True, "parse_special": True})
        response.raise_for_status()
        count = len(response.json()["tokens"])
        context = CONFIG["server"]["context_tokens"]
        # Reserve one additional position rather than let the runtime shorten an
        # explicit output budget. This is an admission guard, not truncation.
        return {"prompt_tokens": count, "reserved_output_tokens": max_tokens,
                "context_tokens": context, "required_with_one_token_guard": count + max_tokens + 1,
                "fits": count + max_tokens + 1 <= context,
                "input_alone_fits": count < context,
                "maximum_output_with_guard": max(0, context - count - 1),
                "formatted_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "generation_performed": False, "prompt_truncated": False}
    finally:
        if owned:
            client.close()


def require_capacity(messages, *, max_tokens):
    result = measure_messages(messages, max_tokens=max_tokens)
    if not result["fits"]:
        raise PromptCapacityError(f"Unchanged prompt {result['prompt_tokens']} + output {max_tokens} + guard 1 exceeds context {result['context_tokens']}")
    return result
