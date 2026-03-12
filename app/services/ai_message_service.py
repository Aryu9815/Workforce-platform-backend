from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.models.common.tenant_ai_settings import TenantAISettings
from app.ai.provider_factory import LLMProviderFactory
from app.ai.prompts import PROMPTS


class AIMessageService:

    async def get_tenant_settings(
        self,
        db: AsyncSession,
        tenant_id: UUID
    ) -> TenantAISettings:

        stmt = select(TenantAISettings).where(
            TenantAISettings.tenant_id == tenant_id,
            TenantAISettings.is_active == True,
            TenantAISettings.is_deleted == False
        )

        result = await db.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI settings not configured for this tenant"
            )

        return settings


    def render_prompt(
        self,
        prompt_key: str,
        variables: dict
    ) -> str:

        if prompt_key not in PROMPTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt '{prompt_key}' not found"
            )

        template = PROMPTS[prompt_key]

        return template.format(**variables)


    async def generate_message(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        message: str
    ) -> str:
        """
        Generate professional message using tenant AI settings
        """

        settings = await self.get_tenant_settings(db, tenant_id)

        prompt = self.render_prompt(
            "professional_message",
            {"message": message}
        )

        llm_client = LLMProviderFactory.get_provider(
            provider_key=settings.provider,
            model=settings.model
        )

        generated_message = await llm_client.generate(
            prompt=prompt,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )

        return generated_message


    async def regenerate_message(
        self,
        db: AsyncSession,
        tenant_id: UUID,
        message: str,
        prompt_key: str
    ) -> str:
        """
        Regenerate message using selected prompt
        """

        settings = await self.get_tenant_settings(db, tenant_id)

        prompt = self.render_prompt(
            prompt_key,
            {"message": message}
        )

        llm_client = LLMProviderFactory.get_provider(
            provider_key=settings.provider,
            model=settings.model
        )

        generated_message = await llm_client.generate(
            prompt=prompt,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )

        return generated_message