
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum
from pydantic import Field, field_validator, model_validator
from app.schemas.validators import (
    validate_name_field,
    validate_optional_str,
    validate_positive_number,
)
from app.schemas.base_schema import BaseSchema

class DefaultStatus(str, Enum):
    """Project status enum."""
    TODO = "toda"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"

class WorkflowBase(BaseSchema):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_default: Optional[bool] = False
    is_system: Optional[bool] = False
    entity_type: str = Field(..., min_length=1, max_length=50)

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=100,
            field="name",
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )

    @field_validator("entity_type")
    def validate_entity_type(cls, value):
        return validate_name_field(
            value,
            max_length=50,
            field="entity_type",
        )

class WorkflowCreate(WorkflowBase):
    """Project creation schema."""
    settings: Optional[Dict[str, Any]] = None

class WorkflowUpdate(BaseSchema):
    """Project update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = False
    is_system: Optional[bool] = False
    entity_type: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=100,
            field="name",
            is_optional=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )

    @field_validator("entity_type")
    def validate_entity_type(cls, value):
        return validate_name_field(
            value,
            max_length=50,
            field="entity_type",
            is_optional=True,
        )


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

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=100,
            field="name",
            only_letters=True
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )

    @field_validator("time_limit_hours", 'order_index')
    def validate_time_limit_hours(cls, value, info):
        return validate_positive_number(
            value,
            field=info.field_name,
            is_optional=True,
            strictly_positive=True,
        )

class CreateWorkFlowState(WorkflowStateBase):
    pass

class UpdateWorkFlowState(BaseSchema):
    name: Optional[str] = None
    description: Optional[str] = None
    order_index: Optional[int] = None
    is_initial: Optional[bool]
    is_final: Optional[bool]
    color: Optional[str] = None
    category: Optional[str] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=100,
            field="name",
            is_optional=True,
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description",
        )


class WorkflowTransitionBase(BaseSchema):
    workflow_id: UUID
    from_state_id: UUID
    to_state_id: UUID
    name: Optional[str] = None
    description: Optional[str] = None
    request_approval: bool = False
    auto_transition: bool = False
    condition_rules: Optional[dict] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_name_field(
            value,
            max_length=100,
            field="name",
            only_letters=True,
            is_optional=True
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description"
        )
    
    @model_validator(mode="after")
    def check_date_order(self):
        if self.to_state_id == self.from_state_id:
            raise ValueError("cannot transition to the same state")
        return self


class CreateWorkflowTransition(WorkflowTransitionBase):
    pass


class UpdateWorkflowTransition(BaseSchema):
    from_state_id: Optional[UUID] = None
    to_state_id: Optional[UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    requires_approval: Optional[bool] = None
    auto_transition: Optional[bool] = None
    condition_rules: Optional[dict] = None

    @field_validator("name")
    def validate_name(cls, value):
        return validate_optional_str(
            value,
            max_length=100,
            field="name",
            only_letters=True,
            is_optional=True
        )

    @field_validator("description")
    def validate_description_field(cls, value):
        return validate_optional_str(
            value,
            max_length=500,
            field="description"
        )
    
    @model_validator(mode="after")
    def check_date_order(self):
        if self.to_state_id == self.from_state_id:
            raise ValueError("cannot transition to the same state")
        return self
    

class WorkflowStateResponse(BaseSchema):
    """Workflow state response schema."""
    id: UUID
    workflow_id: UUID
    name: str
    description: Optional[str] = None
    order_index: int
    is_initial: bool = False
    is_final: bool = False
    color: Optional[str] = None
    category: Optional[str] = None
    requires_assignment: Optional[bool] = False
    time_limit_hours: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class WorkflowResponse(BaseSchema):
    """Workflow state response schema."""
    id: UUID
    name: str
    description: Optional[str] = None
    is_default: Optional[bool] = None
    is_system: Optional[bool] = None
    entity_type: str
    workflow_states: List[WorkflowStateResponse]
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

class WorkflowTransitionResponse(BaseSchema):
    """Workflow state response schema."""
    id: UUID
    workflow_id: UUID
    from_state_id: UUID
    to_state_id: UUID
    name: Optional[str] = None
    description: Optional[str] = None
    request_approval: bool = False
    auto_transition: bool = False
    condition_rules: Optional[dict] = None
    from_state_name: str 
    to_state_name: str
    created_at: datetime
    updated_at: datetime