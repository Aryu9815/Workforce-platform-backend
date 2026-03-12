import uuid
from sqlalchemy import (
    Column, DateTime, Integer, Numeric, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.db_connection import TenantScopedMixin, TenantBase
from app.core.constants import STAFF_PROFILE_ID, TASK_ID

class TaskWorkSession(TenantBase, TenantScopedMixin):
    __tablename__ = "task_work_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attendance_id = Column(UUID(as_uuid=True), ForeignKey("attendance_records.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(UUID(as_uuid=True), ForeignKey(TASK_ID, ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey(STAFF_PROFILE_ID, ondelete="CASCADE"), nullable=False)
    check_in = Column(DateTime(timezone=True), nullable=False)
    check_out = Column(DateTime(timezone=True), nullable=True)
    duration_hours = Column(Numeric(5,2), nullable=True)
    sequence = Column(Integer, nullable=False)