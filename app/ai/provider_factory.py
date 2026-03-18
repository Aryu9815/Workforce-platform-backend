from fastapi import HTTPException, status
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.ollama_provider import OllamaProvider
from app.core.constants import AVAILABLE_PROVIDERS , OPENAI_API_KEY, OLLAMA_BASE_URL


class LLMProviderFactory:

    @staticmethod
    def get_provider(provider_key: str, model: str):

        provider_key = provider_key.lower()
        if provider_key not in AVAILABLE_PROVIDERS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported provider: {provider_key}"
            )

        if model not in AVAILABLE_PROVIDERS[provider_key]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{model}' not supported for provider '{provider_key}'"
            )

        # OPENAI
        if provider_key == "openai":
            api_key = OPENAI_API_KEY
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="OpenAI API key not configured"
                )

            return OpenAIProvider(
                api_key=api_key,
                model=model
            )

        # OLLAMA
        if provider_key == "ollama":
            base_url = OLLAMA_BASE_URL
            return OllamaProvider(
                base_url=base_url,
                model=model
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported LLM provider: {provider_key}"
        )