from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.schemas.common_schemas import BaseSchema

class TaskWorkStartRequest(BaseModel):
    task_id: UUID


class TaskWorkResponse(BaseSchema):
    id: UUID
    task_id: UUID
    task_name: Optional[str] = None
    attendance_id: UUID
    check_in: datetime
    check_out: Optional[datetime]
    duration_hours: Optional[float]
    sequence: int

    class Config:
        orm_mode = True