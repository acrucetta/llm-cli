from abc import ABC, abstractmethod
from typing import Optional, Generator
from enum import Enum
from .prompts import Prompts


class BaseProvider(ABC):
    def __init__(self, model=None):
        self.model = model

    @abstractmethod
    def query(
        self,
        prompt: str,
        file_context: Optional[str] = None,
        prompt_type: Optional[Prompts] = None,
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
