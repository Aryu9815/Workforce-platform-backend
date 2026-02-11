from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    JSON,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.db_connection import CommonBase
import uuid

class TenantMaster(CommonBase):
    __tablename__ = "tenant_master"

    tenant_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_name = Column(String(255), nullable=False, unique=True)
    contact_person = Column(String(255))
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    tenant_metadata = Column(JSON, default={})
    created_date = Column(TIMESTAMP, server_default=func.now())
    updated_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    audit_log = Column(JSON, default=[])