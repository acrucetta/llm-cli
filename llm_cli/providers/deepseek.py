import os
from typing import Optional, List, Generator
from .base import BaseProvider, Message
from .prompts import MAIN_PROMPT, REPL, UNIVERSAL_PRIMER, USER_PROMPT, CONCISE, Prompts
import requests
import json


class DeepSeekProvider(BaseProvider):
    def __init__(self, model="deepseek-chat"):
        super().__init__(model)
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")

    def query(
        self,
        prompt: str,
        file_context: Optional[str] = None,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
        }

        # Format the current prompt with context
        current_content = USER_PROMPT.replace("{{FILES_CONTEXT}}", file_context or "")
        current_content = current_content.replace("{{USER_QUERY}}", prompt)

        # Build messages array
        messages = []
        if message_history:
            messages.extend(
                [{"role": msg.role, "content": msg.content} for msg in message_history]
            )
        messages.append({"role": "user", "content": current_content})

        data = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": messages,
        }

        if prompt_type:
            match prompt_type:
                case Prompts.MAIN:
                    data["system"] = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    data["system"] = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    data["system"] = CONCISE
                case Prompts.REPL:
                    data["system"] = REPL 

        response = requests.post(
            "https://api.deepseek.com/chat/completions", headers=headers, json=data
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]

    def query_stream(
        self,
        prompt: str,
        file_context: Optional[str] = None,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> Generator[str, None, None]:
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
        }

        messages = []
        if message_history:
            messages.extend(
                [{"role": msg.role, "content": msg.content} for msg in message_history]
            )
        
        # Format the current prompt with context
        current_content = USER_PROMPT.replace("{{FILES_CONTEXT}}", file_context or "")
        current_content = current_content.replace("{{USER_QUERY}}", prompt)
        messages.append({"role": "user", "content": current_content})

        data = {
            "model": self.model,
            "max_tokens": 2048,
            "stream": True,
            "messages": messages,
        }

        if prompt_type:
            match prompt_type:
                case Prompts.MAIN:
                    data["system"] = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    data["system"] = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    data["system"] = CONCISE
                case Prompts.REPL:
                    data["system"] = REPL 

        response = requests.post(
            "https://api.deepseek.com/chat/completions",
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
