from fastapi import HTTPException, status

import httpx
from app.ai.providers.base import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: float
    ) -> str:

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )

        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ollama request failed")

        data = response.json()

        return data.get("response", "").strip()