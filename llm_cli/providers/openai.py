import os
from typing import Optional, List, Generator
from .base import BaseProvider, Message
from .prompts import MAIN_PROMPT, REPL, UNIVERSAL_PRIMER, USER_PROMPT, CONCISE, Prompts
from openai import OpenAI


class OpenAIProvider(BaseProvider):
    def __init__(self, model=None):
        super().__init__(model)
        self.model = model or "gpt-4o"
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=self.api_key)

    def query(
        self,
        prompt: str,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> str:
        # Build messages array
        messages = []

        # Add system message if prompt type is specified
        if prompt_type:
            system_content = None
            match prompt_type:
                case Prompts.MAIN:
                    system_content = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    system_content = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    system_content = CONCISE
                case Prompts.REPL:
                    system_content = REPL
            if system_content:
                messages.append({"role": "system", "content": system_content})

        # Add message history
        if message_history:
            messages.extend(
                [{"role": msg.role, "content": msg.content} for msg in message_history]
            )

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        # Generate completion
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=False
        )

        return response.choices[0].message.content

    def query_stream(
        self,
        prompt: str,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> Generator[str, None, None]:
        # Build messages array
        messages = []

        # Add system message if prompt type is specified
        if prompt_type:
            system_content = None
            match prompt_type:
                case Prompts.MAIN:
                    system_content = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    system_content = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    system_content = CONCISE
                case Prompts.REPL:
                    system_content = REPL
            if system_content:
                messages.append({"role": "system", "content": system_content})

        # Add message history
        if message_history:
            messages.extend(
                [{"role": msg.role, "content": msg.content} for msg in message_history]
            )

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        # Generate streaming completion
        response = self.client.chat.completions.create(
            model=self.model, messages=messages, stream=True
        )

        # Stream the response
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content