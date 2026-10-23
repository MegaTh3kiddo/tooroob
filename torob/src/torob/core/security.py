from enum import Enum
from typing import Optional
from fastapi import Header, HTTPException, status
from pydantic import BaseModel


class UserRole(str, Enum):
    PUBLIC = "public"
    CUSTOMER = "customer"
    SELLER = "seller"
    OPERATOR = "operator"
    ADMIN = "admin"


class AuthContext(BaseModel):
    role: UserRole = UserRole.PUBLIC
    user_id: Optional[str] = None
    shop_id: Optional[str] = None


def get_auth_context(
    x_user_role: Optional[str] = Header(None, description="Role: customer, seller, operator, admin"),
    x_user_id: Optional[str] = Header(None, description="User identifier or reporter token"),
    x_shop_id: Optional[str] = Header(None, description="Shop ID for authenticated sellers"),
) -> AuthContext:
    """Extract authenticated context from request headers (clean development & API gateway RBAC)."""
    if not x_user_role:
        return AuthContext(role=UserRole.PUBLIC, user_id=x_user_id)

    try:
        role = UserRole(x_user_role.lower().strip())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid X-User-Role: '{x_user_role}'. Allowed: {', '.join([r.value for r in UserRole])}",
        )

    return AuthContext(
        role=role,
        user_id=x_user_id or "anonymous",
        shop_id=x_shop_id,
    )


def require_admin_or_operator(
    auth: AuthContext,
) -> AuthContext:
    if auth.role not in (UserRole.ADMIN, UserRole.OPERATOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative or Operator role required for this action",
        )
    return auth


def verify_seller_ownership(
    target_shop_id: str,
    auth: AuthContext,
) -> AuthContext:
    """Verify that the caller has authority over the target shop."""
    # Admins and operators can act on any shop
    if auth.role in (UserRole.ADMIN, UserRole.OPERATOR):
        return auth

    if auth.role != UserRole.SELLER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Seller authentication required",
        )

    if not auth.shop_id or auth.shop_id != target_shop_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: You do not have permission to manage shop '{target_shop_id}'",
        )

    return auth
