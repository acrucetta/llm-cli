from abc import ABC, abstractmethod
from typing import Optional, List
from .prompts import Prompts


class Message:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class BaseProvider(ABC):
    def __init__(self, model=None):
        self.model = model

    @abstractmethod
    def query(
        self,
        prompt: str,
        file_context: Optional[str] = None,
        prompt_type: Optional[Prompts] = None,
        message_history: Optional[List[Message]] = None,
    ) -> str:
        pass
