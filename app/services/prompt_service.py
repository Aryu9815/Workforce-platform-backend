from typing import Dict
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.tenant import PromptTemplate


class PromptService:

    async def get_prompt_by_key(
        self,
        db: AsyncSession,
        key: str
    ) -> PromptTemplate:

        stmt = select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.is_deleted == False
        )

        result = await db.execute(stmt)
        prompt = result.scalar_one_or_none()

        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt template not found"
            )

        return prompt


    async def render_prompt(
        self,
        db: AsyncSession,
        key: str,
        variables: Dict
    ) -> str:
        """
        Fetch prompt template and inject variables.
        """

        prompt_template = await self.get_prompt_by_key(db, key)

        try:
            rendered_prompt = prompt_template.template.format(**variables)
        except KeyError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing variable in prompt template: {str(e)}"
            )

        return rendered_prompt


    async def create_prompt_template(
        self,
        db: AsyncSession,
        key: str,
        template: str,
        user_id: str
    ):

        existing_stmt = select(PromptTemplate).where(
            PromptTemplate.key == key,
            PromptTemplate.is_deleted == False
        )

        result = await db.execute(existing_stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt template with this key already exists"
            )

        prompt = PromptTemplate(
            key=key,
            template=template,
            created_by=user_id
        )

        db.add(prompt)
        await db.commit()
        await db.refresh(prompt)

        return prompt


    async def update_prompt_template(
        self,
        db: AsyncSession,
        prompt_id,
        template: str,
        user_id: str
    ):

        stmt = select(PromptTemplate).where(
            PromptTemplate.id == prompt_id,
            PromptTemplate.is_deleted == False
        )

        result = await db.execute(stmt)
        prompt = result.scalar_one_or_none()

        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt template not found"
            )

        prompt.template = template
        prompt.updated_by = user_id

        await db.commit()
        await db.refresh(prompt)

        return prompt