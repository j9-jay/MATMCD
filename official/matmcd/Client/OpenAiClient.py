from openai import OpenAI


class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4") -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def inquire_LLMs(self, prompt: str, system_prompt: str, temperature: float = 0.5):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        output = (
            self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            .choices[0]
            .message.content
        )
        return output
