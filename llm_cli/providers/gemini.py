import os
from typing import Optional, List, Generator
from .base import BaseProvider, Message
from .prompts import MAIN_PROMPT, REPL, UNIVERSAL_PRIMER, CONCISE, Prompts
from google import genai
from google.genai import types


class GeminiProvider(BaseProvider):
    def __init__(self, model=None):
        model = model or "gemini-2.0-flash"
        super().__init__(model)
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.client = genai.Client(api_key=self.api_key)

    def query(
        self,
        prompt: str,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> str:
        # Convert message history to Gemini format
        contents = []
        if message_history:
            for msg in message_history:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "text": msg.content})
        
        # Add current prompt
        contents.append({"role": "user", "text": prompt})

        # Handle system prompt if specified
        system_instruction = None
        if prompt_type:
            match prompt_type:
                case Prompts.MAIN:
                    system_instruction = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    system_instruction = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    system_instruction = CONCISE
                case Prompts.REPL:
                    system_instruction = REPL

        # Configure generation parameters
        config = types.GenerateContentConfig(
            max_output_tokens=2048,
            temperature=1.0,
            system_instruction=system_instruction
        )

        # Generate content
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config
        )
        
        return response.text

    def query_stream(
        self,
        prompt: str,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> Generator[str, None, None]:
        # Convert message history to Gemini format
        contents = []
        if message_history:
            for msg in message_history:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "text": msg.content})
        
        # Add current prompt
        contents.append({"role": "user", "text": prompt})

        # Handle system prompt if specified
        system_instruction = None
        if prompt_type:
            match prompt_type:
                case Prompts.MAIN:
                    system_instruction = MAIN_PROMPT
                case Prompts.UNIVERSAL_PRIMER:
                    system_instruction = UNIVERSAL_PRIMER
                case Prompts.CONCISE:
                    system_instruction = CONCISE
                case Prompts.REPL:
                    system_instruction = REPL

        # Configure generation parameters
        config = types.GenerateContentConfig(
            max_output_tokens=2048,
            temperature=1.0,
            system_instruction=system_instruction
        )

        # Generate streaming content
        response = self.client.models.generate_content_stream(
            model=self.model,
            contents=contents,
            config=config
        )

        # Stream the response
        for chunk in response:
            if chunk.text:
                yield chunk.text
