from abc import ABC, abstractmethod


class BaseProvider(ABC):
    def __init__(self, model=None):
        self.model = model

    @abstractmethod
    def query(self, prompt: str) -> str:
        pass

