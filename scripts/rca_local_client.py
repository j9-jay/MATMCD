"""Recorded local generation with exact-token admission and no retries."""
import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from local_llm_client import LocalLLMClient
from local_llm_runtime import CONFIG
from local_prompt_capacity import measure_messages, PromptCapacityError


@contextmanager
def approved_log_summary_sampling(client):
    """Apply the approved D07 override only during log-summary calls."""
    from project_paths import PROJECT
    profile = json.loads((PROJECT / "configs/local_rca_execution.json").read_text(encoding="utf-8"))["log_summary_sampling"]
    if profile["status"] != "USER_APPROVED_VALIDATED" or profile["overrides"] != {"presence_penalty": 1.5}:
        raise RuntimeError("Log generation requires the explicitly approved D07 profile")
    previous = client.sampling
    client.sampling = dict(previous, **profile["overrides"])
    try:
        yield
    finally:
        client.sampling = previous


class RecordedLocalClient(LocalLLMClient):
    def __init__(self, directory, *, max_tokens, seed, sampling):
        super().__init__(max_tokens=max_tokens, seed=seed, sampling=sampling)
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        self.counter = 0
        self.phase = "unspecified"

    def inquire_messages(self, messages, *, temperature):
        self.counter += 1
        path = self.directory / f"call_{self.counter:07d}.json"
        record = {"phase": self.phase, "messages": messages, "temperature": temperature,
                  "model": CONFIG["model"], "server": CONFIG["server"], "max_tokens": self.max_tokens,
                  "seed": self.seed, "sampling": self.sampling, "status": "PENDING", "attempt": 1}
        record["started_utc"] = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        self.last_request = self.last_response = None
        def save():
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        save()
        try:
            record["capacity"] = measure_messages(messages, max_tokens=self.max_tokens)
            if not record["capacity"]["fits"]:
                record["status"] = "BLOCKED_CAPACITY"
                raise PromptCapacityError(str(record["capacity"]))
            content = super().inquire_messages(messages, temperature=temperature)
            record["status"] = "COMPLETE"
            return content
        except Exception as error:
            if record["status"] != "BLOCKED_CAPACITY":
                record["status"] = "FAILED"
            record["error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            record.update(seconds=time.monotonic() - started, request=self.last_request, response=self.last_response)
            save()


def llamaindex_local_llm(client, *, context_window):
    from llama_index.core.base.llms.types import LLMMetadata, CompletionResponse, ChatResponse, ChatMessage, MessageRole
    from llama_index.core.llms.custom import CustomLLM
    from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
    from llama_index.core.constants import DEFAULT_TEMPERATURE
    from pydantic import PrivateAttr

    class LocalRcaLLM(CustomLLM):
        _client: object = PrivateAttr()

        def __init__(self):
            super().__init__()
            self._client = client

        @property
        def metadata(self):
            return LLMMetadata(context_window=context_window, num_output=client.max_tokens,
                               is_chat_model=True, model_name=CONFIG["model"]["server_alias"])

        @llm_chat_callback()
        def chat(self, messages, **kwargs):
            if kwargs:
                raise ValueError(f"Unexpected synthesis overrides: {sorted(kwargs)}")
            converted = [{"role": message.role.value, "content": message.content} for message in messages]
            if any(not isinstance(message["content"], str) for message in converted):
                raise ValueError("Only unmodified text messages are supported")
            content = self._client.inquire_messages(converted, temperature=DEFAULT_TEMPERATURE)
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=content))

        @llm_completion_callback()
        def complete(self, prompt, formatted=False, **kwargs):
            if kwargs:
                raise ValueError(f"Unexpected synthesis overrides: {sorted(kwargs)}")
            return CompletionResponse(text=self._client.inquire_messages(
                [{"role": "user", "content": prompt}], temperature=DEFAULT_TEMPERATURE))

        @llm_completion_callback()
        def stream_complete(self, prompt, formatted=False, **kwargs):
            raise RuntimeError("Released RCA summary is non-streaming")

    return LocalRcaLLM()
