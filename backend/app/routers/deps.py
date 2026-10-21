from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Tuple, Set
from backend.app.database.session import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.entities import User, Tenant, Membership

security = HTTPBearer(auto_error=False)


WorkspaceContext = Tuple[Tenant, User, str]

WORKSPACE_ADMIN_ROLES = {"owner", "admin"}
APPROVER_ROLES = {"owner", "admin", "approver"}
OPERATIONAL_ROLES = {"owner", "admin", "manager", "reviewer", "analyst", "approver"}


def require_authenticated_tenant_and_user(
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_tenant_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not auth_creds or not auth_creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(auth_creds.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(User).filter(
        User.id == payload["sub"],
        User.is_active.is_(True)
    ).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_tenant_id = payload["tenant_id"]
    if x_tenant_id and x_tenant_id != token_tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context does not match the authenticated session")

    membership = db.query(Membership).filter(
        Membership.user_id == user.id,
        Membership.tenant_id == token_tenant_id,
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no membership in this tenant")

    tenant = db.query(Tenant).filter(Tenant.id == token_tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership is invalid")

    return tenant, user, membership.role


get_current_tenant_and_user = require_authenticated_tenant_and_user


def require_workspace_admin(
    ctx: WorkspaceContext = Depends(require_authenticated_tenant_and_user)
) -> WorkspaceContext:
    tenant, user, role = ctx
    if role.lower() not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace owner or admin role is required")
    return tenant, user, role


def require_any_role(allowed_roles: Set[str]):
    def dependency(
        ctx: WorkspaceContext = Depends(require_authenticated_tenant_and_user),
    ) -> WorkspaceContext:
        tenant, user, role = ctx
        if role.lower() not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your workspace role cannot perform this action")
        return tenant, user, role

    return dependency
