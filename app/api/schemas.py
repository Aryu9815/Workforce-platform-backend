"""
Pydantic schemas for API request/response validation.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from enum import Enum


# ============================================
# Base Schemas
# ============================================

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """Schema with timestamp fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaginationParams(BaseSchema):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    @property
    def skip(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseSchema):
    """Paginated response wrapper."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    pages: int
    
    @classmethod
    def create(
        cls,
        items: List[Any],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse":
        pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages
        )


# ============================================
# Authentication Schemas
# ============================================

class TokenResponse(BaseSchema):
    """Token response schema."""
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    tenant: Optional[Dict[str, Any]] = None
    multiple_tenants_found: bool = False


class LoginRequest(BaseSchema):
    """Login request schema."""
    email: EmailStr
    password: str

class RegisterRequest(BaseSchema):
    """Registration request schema."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None


class RefreshTokenRequest(BaseSchema):
    """Refresh token request schema."""
    refresh_token: str


class ChangePasswordRequest(BaseSchema):
    """Change password request schema."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# ============================================
# User Schemas
# ============================================

class UserBase(BaseSchema):
    """Base user schema."""
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    """User creation schema."""
    password: str = Field(..., min_length=8)
    status: str = "active"


class UserUpdate(BaseSchema):
    """User update schema."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    status: Optional[str] = None


class UserResponse(UserBase, TimestampSchema):
    """User response schema."""
    id: UUID
    avatar_url: Optional[str] = None
    last_login_at: Optional[datetime] = None
    status: str
    full_name: str
    # 👇 add these
    staff_id: Optional[UUID] = None
    department_id: Optional[UUID] = None
    designation_id: Optional[UUID] = None


# ============================================
# Tenant Schemas
# ============================================

class TenantBase(BaseSchema):
    """Base tenant schema."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    timezone: str = "UTC"


class TenantCreate(TenantBase):
    """Tenant creation schema."""
    settings: Optional[Dict[str, Any]] = None


class TenantUpdate(BaseSchema):
    """Tenant update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    timezone: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class TenantResponse(TenantBase, TimestampSchema):
    """Tenant response schema."""
    id: UUID
    status: str
    settings: Dict[str, Any]


class TenantListResponse(BaseSchema):
    """Tenant list item response."""
    id: UUID
    name: str



class ProjectStatus(str, Enum):
    """Project status enum."""
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"


class ProjectPriority(str, Enum):
    """Project priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectBase(BaseSchema):
    """Base project schema."""
    name: str = Field(..., min_length=1, max_length=255)
    code: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANNING
    priority: ProjectPriority = ProjectPriority.MEDIUM
    project_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    currency: str = "USD"


class ProjectCreate(ProjectBase):
    """Project creation schema."""
    project_manager_id: UUID
    parent_project_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    location: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseSchema):
    """Project update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    priority: Optional[ProjectPriority] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    budget: Optional[float] = None
    cost_estimate: Optional[float] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    project_manager_id: Optional[UUID] = None


class ProjectResponse(ProjectBase, TimestampSchema):
    """Project response schema."""
    id: UUID
    parent_project_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    project_manager_id: UUID
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    cost_estimate: Optional[float] = None
    actual_cost: float
    progress_percentage: int
    is_template: bool
    deleted_at: Optional[datetime] = None
    manager_name: Optional[str] = None


# ============================================
# Task Schemas
# ============================================

class TaskPriority(str, Enum):
    """Task priority enum."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(BaseSchema):
    """Base task schema."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    task_type: Optional[str] = None
    estimated_hours: Optional[float] = None
    estimated_cost: Optional[float] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class TaskCreate(TaskBase):
    """Task creation schema."""
    project_id: UUID
    parent_task_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    assignee_ids: List[UUID] = []
    milestone: bool = False
    billable: bool = True
    location: Optional[Dict[str, Any]] = None
    custom_fields: Optional[Dict[str, Any]] = None
    tags: List[str] = []


class TaskUpdate(BaseSchema):
    """Task update schema."""
    title: Optional[str] = None
    description: Optional[str] = None
    status_id: Optional[UUID] = None
    priority: Optional[TaskPriority] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    billable: Optional[bool] = None
    tags: Optional[List[str]] = None


class TaskResponse(TaskBase, TimestampSchema):
    """Task response schema."""
    id: UUID
    project_id: UUID
    parent_task_id: Optional[UUID] = None
    status_id: Optional[UUID] = None
    status_name: Optional[str] = None
    status_color: Optional[str] = None
    actual_hours: float
    actual_cost: float
    completed_at: Optional[datetime] = None
    created_by: UUID
    progress_percentage: int
    milestone: bool
    billable: bool
    deleted_at: Optional[datetime] = None
    assignees: List[Dict[str, Any]] = []



# ============================================
# Response Wrappers
# ============================================

class SuccessResponse(BaseSchema):
    """Standard success response."""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseSchema):
    """Standard error response."""
    success: bool = False
    error: Dict[str, Any]


class DashboardStatsResponse(BaseSchema):
    """Dashboard statistics response."""
    total_staff: int
    total_projects: int
    active_tasks: int
    pending_leaves: int
    pending_reimbursements: int
    low_stock_items: int
    attendance_today: Dict[str, int]
    recent_activities: List[Dict[str, Any]]
