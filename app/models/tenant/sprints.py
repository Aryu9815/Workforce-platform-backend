import uuid
from sqlalchemy import (
    Column, String, Text, Date, Integer, ForeignKey 
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.db_connection import TenantScopedMixin, TenantBase
from app.core.constants import PROJECT_ID


class Sprint(TenantBase, TenantScopedMixin):
    __tablename__ = "sprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey(PROJECT_ID, ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    goal = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(20), default="planned")  # planned | active | completed | cancelled
    capacity = Column(Integer, nullable=True)
    sprint_number = Column(Integer, nullable=False) 

