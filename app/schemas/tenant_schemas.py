from uuid import UUID
from app.schemas.base_schema import BaseSchema

class TenantListResponse(BaseSchema):
    """Tenant list item response."""
    id: UUID
    name: str