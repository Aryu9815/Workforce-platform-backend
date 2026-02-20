from fastapi import Request, HTTPException, status
from functools import wraps
from typing import List, Literal

def require_permissions(
    required: List[str],
    mode: Literal["OR", "AND"] = "OR"
):
    """
    RBAC decorator for FastAPI route handlers.

    Args:
        required (List[str]): List of required permission strings.
        mode (str): "OR" → user must have *any* permission,
                    "AND" → user must have *all* permissions.
    """

    def decorator(func):

        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):

            user_permissions = getattr(request.state, "permissions", [])

            if not isinstance(user_permissions, list):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid permission structure"
                )

            # OR mode → at least one permission required
            if mode == "OR":
                if not any(perm in user_permissions for perm in required):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission (OR): {required}"
                    )

            # AND mode → all permissions required
            else:
                if not all(perm in user_permissions for perm in required):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission (AND): {required}"
                    )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator