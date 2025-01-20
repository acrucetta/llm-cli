import os
from typing import Optional
from .base import BaseProvider, SYSTEM_PROMPT
import requests


class AnthropicProvider(BaseProvider):
    def __init__(self, model="claude-3-5-sonnet-20241022"):
        super().__init__(model)
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    def query(
        self,
        prompt: str,
        file_context: Optional[str] = None,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        shortened_prompt = SYSTEM_PROMPT.replace(
            "{{FILES_CONTEXT}}", file_context or ""
        )
        shortened_prompt = shortened_prompt.replace("{{USER_QUERY}}", prompt)

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
