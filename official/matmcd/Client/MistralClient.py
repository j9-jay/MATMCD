from mistralai import Mistral


class MistralClient:
    def __init__(self, api_key: str, model: str = "open-mistral-7b") -> None:
        self.client = Mistral(api_key=api_key)
        self.model = model

    def inquire_LLMs(self, prompt: str, system_prompt: str, temperature: float = 0.5):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        output = (
            self.client.chat.complete(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            .choices[0]
            .message.content
        )
        return output
