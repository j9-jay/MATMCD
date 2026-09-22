import time
from llamaapi import LlamaAPI


class LlamaClient:
    def __init__(self, api_key: str, model: str = "llama3.1-8b") -> None:
        self.model = model
        self.client = LlamaAPI(api_key)

    def inquire_LLMs(self, prompt: str, system_prompt: str, temperature: float = 0.5):
        api_request_json = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        }

        while True:
            try:
                response = self.client.run(api_request_json)
                output = response.json()["choices"][0]["message"]["content"]
                return output
            except Exception as e:
                print(f"Error occurred: {e}")
                print("Retrying after 10 seconds...")
                time.sleep(10)
