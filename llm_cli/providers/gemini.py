import os
from typing import Optional, List, Generator
from .base import BaseProvider, Message
from .prompts import MAIN_PROMPT, REPL, UNIVERSAL_PRIMER, CONCISE, Prompts
import requests
import json


class GeminiProvider(BaseProvider):
    def __init__(self, model=None):
        model = model or "gemini-2.0-flash"
        super().__init__(model)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    def query(
        self,
        prompt: str,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> str:
        headers = {
            "Content-Type": "application/json",
        }

        # Convert message history to Gemini format
        contents = []
        if message_history:
            for msg in message_history:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        # Add the current prompt
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        data = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 2048,
                "temperature": 1.0,
            },
        }

        # Add system prompt if specified
        if prompt_type:
            system_prompt = None
            match prompt_type:
                case Prompts.MAIN:
                    system_prompt = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    system_prompt = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    system_prompt = CONCISE
                case Prompts.REPL:
                    system_prompt = REPL

            if system_prompt:
                # Gemini uses system instructions in a different format
                data["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        response_json = response.json()
        return response_json["candidates"][0]["content"]["parts"][0]["text"]

    def query_stream(
        self,
        prompt: str,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> Generator[str, None, None]:
        headers = {
            "Content-Type": "application/json",
        }

        # Convert message history to Gemini format
        contents = []
        if message_history:
            for msg in message_history:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        # Add the current prompt
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        data = {
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 2048,
                "temperature": 1.0,
            },
        }

        # Add system prompt if specified
        if prompt_type:
            system_prompt = None
            match prompt_type:
                case Prompts.MAIN:
                    system_prompt = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    system_prompt = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    system_prompt = CONCISE
                case Prompts.REPL:
                    system_prompt = REPL

            if system_prompt:
                # Gemini uses system instructions in a different format
                data["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        url = f"{self.base_url}/{self.model}:streamGenerateContent?key={self.api_key}"
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()

        for chunk in response.iter_lines():
            if chunk:
                chunk_text = chunk.decode("utf-8")
                if chunk_text.startswith("data: "):
                    # Remove the "data: " prefix
                    json_str = chunk_text[6:]
                    if json_str == "[DONE]":
                        break

                    try:
                        chunk_data = json.loads(json_str)
                        if (
                            "candidates" in chunk_data
                            and len(chunk_data["candidates"]) > 0
                        ):
                            candidate = chunk_data["candidates"][0]
                            if (
                                "content" in candidate
                                and "parts" in candidate["content"]
                                and len(candidate["content"]["parts"]) > 0
                            ):
                                part = candidate["content"]["parts"][0]
                                if "text" in part:
                                    yield part["text"]
                    except json.JSONDecodeError:
                        continue
