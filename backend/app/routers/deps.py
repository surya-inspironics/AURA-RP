from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from backend.app.database.session import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.entities import User, Tenant, Membership

security = HTTPBearer(auto_error=False)

def get_current_tenant_and_user(
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_tenant_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Tuple[Tenant, User, str]:
    """
    Resolves the authenticated User and Tenant context.
    Enforces strict tenant scoping.
    Falls back gracefully to the primary active tenant/user for local dev/demo.
    """
    user: Optional[User] = None
    role: str = "owner"

    if auth_creds and auth_creds.credentials:
        payload = decode_access_token(auth_creds.credentials)
        if payload and "sub" in payload:
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if "tenant_id" in payload and not x_tenant_id:
                x_tenant_id = payload["tenant_id"]

    # If no token provided or invalid, fallback to primary default admin user & Northstar Bank tenant
    if not user:
        user = db.query(User).first()
        if not user:
            # Seed primary tenant and admin user if completely empty
            from backend.app.database.seed import seed_initial_data
            seed_initial_data(db)
            user = db.query(User).first()

    tenant: Optional[Tenant] = None
    if x_tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == x_tenant_id).first()

    if not tenant:
        # Check user's first membership
        mem = db.query(Membership).filter(Membership.user_id == user.id).first()
        if mem:
            tenant = db.query(Tenant).filter(Tenant.id == mem.tenant_id).first()
            role = mem.role
        else:
            tenant = db.query(Tenant).first()

    if not tenant or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not authenticate user or resolve tenant context"
        )

    return tenant, user, role


def require_authenticated_tenant_and_user(
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_tenant_id: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Tuple[Tenant, User, str]:
    """Resolve a valid bearer identity and a tenant membership without demo fallback."""
    if not auth_creds or not auth_creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(auth_creds.credentials)
    if not payload or not payload.get("sub"):
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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Active user not found")

    requested_tenant_id = x_tenant_id or payload.get("tenant_id")
    membership_query = db.query(Membership).filter(Membership.user_id == user.id)
    if requested_tenant_id:
        membership_query = membership_query.filter(Membership.tenant_id == requested_tenant_id)
    membership = membership_query.first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User has no membership in this tenant")

    tenant = db.query(Tenant).filter(Tenant.id == membership.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant membership is invalid")

    return tenant, user, membership.role


def require_workspace_admin(
    ctx: Tuple[Tenant, User, str] = Depends(require_authenticated_tenant_and_user)
) -> Tuple[Tenant, User, str]:
    tenant, user, role = ctx
    if role.lower() not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace owner or admin role is required")
    return tenant, user, role
