import os
from typing import Optional, List, Generator
from .base import BaseProvider, Message
from .prompts import MAIN_PROMPT, REPL, UNIVERSAL_PRIMER, USER_PROMPT, CONCISE, Prompts
import requests
import json


class AnthropicProvider(BaseProvider):
    def __init__(self, model=None):
        self.model = model or "claude-3.7-sonnet"
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    def query(
        self,
        prompt: str,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        # Build messages array
        messages = []
        if message_history:
            messages.extend(
                [{"role": msg.role, "content": msg.content} for msg in message_history]
            )
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": messages,
        }

        # Set the system prompt based on the prompt_type
        if prompt_type:
            prompt_value_map = {
                "main": MAIN_PROMPT,
                "primer": UNIVERSAL_PRIMER,
                "concise": CONCISE,
                "repl": REPL
            }
            data["system"] = prompt_value_map.get(prompt_type.value, REPL)

        response = requests.post(
            "https://api.anthropic.com/v1/messages", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]

    def query_stream(
        self,
        prompt: str,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> Generator[str, None, None]:
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        messages = []
        if message_history:
            messages.extend(
                [{"role": msg.role, "content": msg.content} for msg in message_history]
            )
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "max_tokens": 2048,
            "stream": True,
            "messages": messages,
        }

        # Set the system prompt based on the prompt_type
        if prompt_type:
            prompt_value_map = {
                "main": MAIN_PROMPT,
                "primer": UNIVERSAL_PRIMER,
                "concise": CONCISE,
                "repl": REPL
            }
            data["system"] = prompt_value_map.get(prompt_type.value, REPL)

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data,
            stream=True,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line_text = line.decode("utf-8")
                if not line_text.startswith("data: "):
                    continue

                json_str = line_text.replace("data: ", "")
                json_response = json.loads(json_str)

                if json_response["type"] == "content_block_delta":
                    delta = json_response["delta"]
                    if delta["type"] == "text_delta":
                        text = delta["text"]
                        yield text
