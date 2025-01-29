from abc import ABC, abstractmethod
<<<<<<< HEAD
from typing import Optional, List
=======
from typing import Optional, Generator
from enum import Enum
>>>>>>> c5bf2f5a1fa8d178a4942305fdb4a1da0d9ca4b1
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

    @abstractmethod
    def query_stream(
        self,
        prompt: str,
        file_context: Optional[str] = None,
        prompt_type: Optional[Prompts] = None,
    ) -> Generator[str, None, None]:
        pass
