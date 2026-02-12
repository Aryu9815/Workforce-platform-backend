
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


class DefaultStatus(str, Enum):
    """Project status enum."""
    TODO = "toda"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"




class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)

class WorkflowBase(BaseSchema):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: Optional[bool] = False
    is_system: Optional[bool] = False
    entity_type: str = Field(..., min_length=1, max_length=50)

class WorkflowCreate(WorkflowBase):
    """Project creation schema."""
    created_by: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

class WorkflowUpdate(BaseSchema):
    """Project update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = False
    is_system: Optional[bool] = False
    entity_type: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class WorkflowStateBase(BaseSchema):
    workflow_id: UUID
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    order_index: int
    is_initial: bool = False
    is_final: bool = False
    color: Optional[str] = None
    category: Optional[str] = None
    requires_assignment: Optional[bool] = False
    time_limit_hours: Optional[int] = None

class CreateWorkFlowState(WorkflowStateBase):
    created_by: Optional[str] = None

class UpdateWorkFlowState(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    is_initial: Optional[bool]
    is_final: Optional[bool]
    color: Optional[str] = None
    category: Optional[str] = None


class WorkflowTransitionBase(BaseSchema):
    workflow_id: UUID
    from_state_id: UUID
    to_state_id: UUID
    name: Optional[str] = None
    description: Optional[str] = None
    request_approval: bool = False
    approval_flow_id: Optional[UUID] = None
    auto_transition: bool = False
    condition_rules: Optional[dict] = None


class CreateWorkflowTransition(WorkflowTransitionBase):
    created_by: Optional[str] = None
    pass


class UpdateWorkflowTransition(BaseSchema):
    from_state_id: Optional[UUID] = None
    to_state_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    requires_approval: Optional[bool] = None
    approval_flow_id: Optional[UUID] = None
    auto_transition: Optional[bool] = None
    condition_rules: Optional[dict] = None
