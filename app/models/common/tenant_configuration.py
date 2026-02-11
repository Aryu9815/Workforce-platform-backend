from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    JSON,
    TIMESTAMP,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.db.db_connection import CommonBase

class TenantConfiguration(CommonBase):
    __tablename__ = "tenant_configuration"

    config_id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenant_master.tenant_id"), nullable=False)
    biz_config = Column(JSON, default={})
    env_config = Column(JSON, default={})
    app_config = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    tenant_metadata = Column(JSON, default={})
    audit_log = Column(JSON, default=[])
    created_date = Column(TIMESTAMP, server_default=func.now())
    updated_date = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())