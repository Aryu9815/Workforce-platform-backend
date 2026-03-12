from uuid import UUID
from pydantic import BaseModel, Field



class GenerateMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class GenerateMessageResponse(BaseModel):
    old_message: str | None = None
    generated_message: str