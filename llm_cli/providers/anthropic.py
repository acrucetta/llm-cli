import os
import requests
from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    def __init__(self, model="claude-3-5-sonnet-20241022"):
        super().__init__(model)
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    def query(self, prompt: str) -> str:
        # Keep answers short.
        shortened_prompt = (
            "Your answer will be displayed in the command line, make it concice yet informative. See the prompt below.\n"
            + prompt
        )
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        data = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": shortened_prompt}],
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]

