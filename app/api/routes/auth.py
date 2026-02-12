"""
Authentication API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api.schemas import (
    UserResponse,
    TenantListResponse,
    SuccessResponse
)
from app.schemas.auth_schemas import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest
)
from app.services.auth import auth_service
from app.db.base import get_db_session , get_common_db
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_common_db)
):
    """Authenticate user and return tokens."""
    # Authenticate user
    user = await auth_service.authenticate_user(
        db,
        email=login_data.email,
        password=login_data.password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    tenants = await auth_service.get_user_tenants(db, user.id)
    if not len(tenants) > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="We couldn't find any firm linked to your account.Please contact support or your administrator to activate your access."
        )
    multiple_tenants_found = True
    tenant = tenants[0]
    # Get user agent
    user_agent = request.headers.get("User-Agent")
    
    # Create tokens
    access_token, refresh_token = await auth_service.create_tokens(
        db,
        user,
        tenant_id=tenant['id'],
        user_agent=user_agent
    )
    
    logger.info(f"User {user.id} logged in successfully")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        tenant=tenant,
        multiple_tenants_found=multiple_tenants_found
    )

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_common_db)
):
    """Register a new user."""
    try:
        user = await auth_service.register_user(
            db,
            email=register_data.email,
            password=register_data.password,
            first_name=register_data.first_name,
            last_name=register_data.last_name,
            phone=register_data.phone
        )
        
        logger.info(f"New user registered: {user.id}")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            avatar_url=user.avatar_url,
            last_login_at=user.last_login_at,
            status=user.status,
            full_name=user.full_name,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_common_db)
):
    """Refresh access token using refresh token."""
    result = await auth_service.refresh_access_token(
        db,
        refresh_token_str=refresh_data.refresh_token
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    access_token, new_refresh_token, tenant_id = result
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        tenant_id=tenant_id
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_common_db)
):
    """Logout user by revoking refresh token."""
    success = await auth_service.revoke_refresh_token(
        db,
        refresh_token_str=refresh_data.refresh_token
    )
    
    if success:
        return SuccessResponse(message="Logged out successfully")
    else:
        return SuccessResponse(message="Token already revoked or invalid")


@router.post("/change-password", response_model=SuccessResponse)
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_common_db)
):
    """Change user password."""
    user_id = getattr(request.state, 'user_id', None)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        success = await auth_service.change_password(
            db,
            user_id=user_id,
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        return SuccessResponse(message="Password changed successfully")
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_common_db)
):
    """Get current authenticated user details."""
    user_id = getattr(request.state, 'user_id', None)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    user = await auth_service.user_crud.get(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        avatar_url=user.avatar_url,
        last_login_at=user.last_login_at,
        status=user.status,
        full_name=user.full_name,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/tenants", response_model=List[TenantListResponse])
async def get_user_tenants(
    request: Request,
    db: AsyncSession = Depends(get_common_db)
):
    """Get all tenants for the current user."""
    user_id = getattr(request.state, 'user_id', None)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    tenants = await auth_service.get_user_tenants(db, user_id)
    
    return tenants

@router.post("/switch-tenant", response_model=TokenResponse)
async def switch_tenant(
    request: Request,
    tenant_id: str,
    db: AsyncSession = Depends(get_common_db)
):
    """Switch to a different tenant and get new tokens."""
    user_id = getattr(request.state, 'user_id', None)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # Get user
    user = await auth_service.user_crud.get(db, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify user has access to tenant
    user_tenants = await auth_service.get_user_tenants(db, user_id)
    tenant_ids = [str(t['id']) for t in user_tenants]
    if tenant_id not in tenant_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant"
        )
    tenant = [t for t in user_tenants if str(t['id']) == tenant_id][0]
    
    # Revoke old tokens
    await auth_service.revoke_all_user_tokens(db, user_id)
    
    # Create new tokens for the selected tenant
    user_agent = request.headers.get("User-Agent")
    access_token, refresh_token = await auth_service.create_tokens(
        db,
        user,
        tenant_id=tenant_id,
        user_agent=user_agent
    )
    
    logger.info(f"User {user_id} switched to tenant {tenant_id}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        tenant=tenant,
        multiple_tenants_found=True
    )
