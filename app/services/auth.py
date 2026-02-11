"""
Authentication service for user management and JWT handling.
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
import logging
from app.models.common import User, TenantMaster, RefreshToken
from app.models.tenant import TenantUserRole, RolePermission, Permission
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.core.config import settings
from app.services.crud import CRUDService

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self):
        self.user_crud = CRUDService(User)
        self.tenant_crud = CRUDService(TenantMaster)
    
    async def authenticate_user(
        self,
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate a user with email and password."""
        # Get user by email
        user = await self.user_crud.get_by_field(db, field="email", value=email)
        
        if not user:
            logger.warning(f"Authentication failed: User not found for email {email}")
            return None
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            logger.warning(f"Authentication failed: Account locked for user {user.id}")
            return None
        
        # Verify password
        if not verify_password(password, user.password_hash):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
                logger.warning(f"Account locked for user {user.id} due to multiple failed attempts")
            
            await db.flush()
            logger.warning(f"Authentication failed: Invalid password for user {user.id}")
            return None
        
        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        await db.flush()
        
        logger.info(f"User {user.id} authenticated successfully")
        return user
    
    async def register_user(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None
    ) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = await self.user_crud.get_by_field(db, field="email", value=email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        print('PAASDD', password, len(password))
        # Validate password
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
        hash_pw = hash_password(password)
        print('hash', hash_pw)
        # Create user
        user_data = {
            "email": email,
            "password_hash": hash_pw,
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "status": "active"
        }
        
        user = await self.user_crud.create(db, obj_in=user_data)
        logger.info(f"New user registered: {user.id}")
        
        return user
    
    async def create_tokens(
        self,
        db: AsyncSession,
        user: User,
        tenant_id: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[str, str]:
        """Create access and refresh tokens for a user."""
        # Get user permissions
        # permissions = await self.get_user_permissions(db, user.id, tenant_id)
        
        # Create tokens
        access_token = create_access_token(
            user_id=str(user.id),
            email=user.email,
            tenant_id=tenant_id,
            # permissions=permissions
        )
        
        refresh_token_str = create_refresh_token(
            user_id=str(user.id),
            tenant_id=tenant_id
        )
        
        # Store refresh token in database
        refresh_token = RefreshToken(
            user_id=user.id,
            tenant_id=tenant_id,
            token=access_token,  # Store partial for reference
            refresh_token=refresh_token_str,
            token_expires_at=datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            refresh_expires_at=datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            user_agent=user_agent
        )
        
        db.add(refresh_token)
        await db.flush()
        
        logger.info(f"Tokens created for user {user.id}")
        return access_token, refresh_token_str
    
    async def refresh_access_token(
        self,
        db: AsyncSession,
        refresh_token_str: str
    ) -> Optional[Tuple[str, str, str]]:
        """Refresh access token using refresh token."""
        # Verify refresh token
        token_data = verify_token(refresh_token_str, token_type="refresh")
        if not token_data:
            logger.warning("Token refresh failed: Invalid refresh token")
            return None
        
        # Check if refresh token exists in database and is not revoked
        query = select(RefreshToken).where(
            and_(
                RefreshToken.refresh_token == refresh_token_str,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.refresh_expires_at > datetime.utcnow()
            )
        )
        result = await db.execute(query)
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            logger.warning("Token refresh failed: Refresh token not found or expired")
            return None
        
        # Get user
        user = await self.user_crud.get(db, db_token.user_id)
        if not user or user.status != "active":
            logger.warning("Token refresh failed: User not found or inactive")
            return None
        
        # Revoke old refresh token
        db_token.revoked_at = datetime.utcnow()
        
        # Create new tokens
        access_token, new_refresh_token = await self.create_tokens(
            db,
            user,
            tenant_id=str(db_token.tenant_id) if db_token.tenant_id else None,
            user_agent=db_token.user_agent
        )
        
        logger.info(f"Tokens refreshed for user {user.id}")
        return access_token, new_refresh_token, str(db_token.tenant_id) if db_token.tenant_id else None
    
    async def revoke_refresh_token(
        self,
        db: AsyncSession,
        refresh_token_str: str
    ) -> bool:
        """Revoke a refresh token (logout)."""
        query = select(RefreshToken).where(RefreshToken.refresh_token == refresh_token_str)
        result = await db.execute(query)
        db_token = result.scalar_one_or_none()
        
        if not db_token:
            return False
        
        db_token.revoked_at = datetime.utcnow()
        await db.flush()
        
        logger.info(f"Refresh token revoked for user {db_token.user_id}")
        return True
    
    async def revoke_all_user_tokens(
        self,
        db: AsyncSession,
        user_id: str
    ) -> int:
        """Revoke all refresh tokens for a user."""
        query = select(RefreshToken).where(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None)
            )
        )
        result = await db.execute(query)
        tokens = result.scalars().all()
        
        count = 0
        for token in tokens:
            token.revoked_at = datetime.utcnow()
            count += 1
        
        await db.flush()
        logger.info(f"Revoked {count} tokens for user {user_id}")
        return count
    
    async def get_user_permissions(
        self,
        db: AsyncSession,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get all permissions for a user in a tenant."""
        if not tenant_id:
            return []
        
        # Get user's roles in tenant
        query = select(TenantUserRole).where(
            and_(
                TenantUserRole.user_id == user_id,
                TenantUserRole.tenant_id == tenant_id
            )
        )
        result = await db.execute(query)
        user_roles = result.scalars().all()
        
        if not user_roles:
            return []
        
        # Get permissions for all roles
        role_ids = [ur.role_id for ur in user_roles]
        
        query = select(Permission.code).join(
            RolePermission,
            Permission.id == RolePermission.permission_id
        ).where(
            RolePermission.role_id.in_(role_ids)
        ).distinct()
        
        result = await db.execute(query)
        permissions = [row[0] for row in result.all()]
        
        return permissions
    
    
    async def change_password(
        self,
        db: AsyncSession,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> bool:
        """Change user password."""
        user = await self.user_crud.get(db, user_id)
        if not user:
            return False
        
        # Verify current password
        if not verify_password(current_password, user.password_hash):
            return False
        
        # Validate new password
        if len(new_password) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
        
        # Update password
        user.password_hash = hash_password(new_password)
        await db.flush()
        
        # Revoke all tokens for security
        await self.revoke_all_user_tokens(db, user_id)
        
        logger.info(f"Password changed for user {user_id}")
        return True
    
    async def reset_password(
        self,
        db: AsyncSession,
        user_id: str,
        new_password: str
    ) -> bool:
        """Reset user password (admin function)."""
        user = await self.user_crud.get(db, user_id)
        if not user:
            return False
        
        # Validate new password
        if len(new_password) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
        
        # Update password
        user.password_hash = hash_password(new_password)
        await db.flush()
        
        # Revoke all tokens for security
        await self.revoke_all_user_tokens(db, user_id)
        
        logger.info(f"Password reset for user {user_id}")
        return True

    async def get_user_tenants(
        self,
        db: AsyncSession,
        user_id: str
    ):        
        user = await self.user_crud.get(db, user_id)
        if not user:
            None
        tenants = []
        for tenant_id in user.tenant_ids:
            result = await db.execute(select(TenantMaster).where(TenantMaster.tenant_id == tenant_id, TenantMaster.is_deleted == False))
            tenant = result.scalar_one_or_none()
            tenants.append({
                "id":tenant.tenant_id, 
                "name":tenant.tenant_name,
            })
        return tenants

        
# Global auth service instance
auth_service = AuthService()
