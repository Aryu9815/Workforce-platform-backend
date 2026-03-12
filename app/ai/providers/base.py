from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: float
    ) -> str:
        """
        Generate response from LLM
        """
        pass