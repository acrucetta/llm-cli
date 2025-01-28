import os
from typing import Optional
from .base import BaseProvider
from .prompts import MAIN_PROMPT, UNIVERSAL_PRIMER, USER_PROMPT, CONCISE, Prompts
import requests


class DeepSeekProvider(BaseProvider):
    def __init__(self, model="claude-3-5-sonnet-20241022"):
        super().__init__(model)
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    def query(
        self,
        prompt: str,
        file_context: Optional[str] = None,
        prompt_type: Optional[Prompts] = None,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        user_prompt = USER_PROMPT.replace("{{FILES_CONTEXT}}", file_context or "")
        user_prompt = user_prompt.replace("{{USER_QUERY}}", prompt)

        data = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        if prompt_type:
            match prompt_type:
                case Prompts.MAIN:
                    data["system"] = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    data["system"] = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    data["system"] = CONCISE

        response = requests.post(
            "https://api.anthropic.com/v1/messages", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
