from openai import AsyncOpenAI
from app.ai.providers.base import BaseLLMProvider



class OpenAIProvider(BaseLLMProvider):

    def __init__(self, api_key: str, base_url: str | None = None, model: str = "gpt-4o-mini"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = model


    async def generate(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:

        response = await self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        return response.choices[0].message.content.strip()