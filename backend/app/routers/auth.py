from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.database.session import get_db
from backend.app.models.entities import User, Tenant, Membership
from backend.app.models.schemas import UserRegister, UserLogin, TokenResponse
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.routers.deps import get_current_tenant_and_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenResponse)
def register_user(data: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    user = User(
        email=data.email.lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        avatar_initials="".join([part[0].upper() for part in data.full_name.split()[:2]]),
        is_active=True
    )
    db.add(user)
    db.flush()

    org_name = data.organization_name or f"{data.full_name}'s Workspace"
    slug = org_name.lower().replace(" ", "-") + f"-{user.id[:4]}"
    tenant = Tenant(name=org_name, slug=slug)
    db.add(tenant)
    db.flush()

    membership = Membership(
        tenant_id=tenant.id,
        user_id=user.id,
        role="owner"
    )
    db.add(membership)
    db.commit()

    token = create_access_token({"sub": user.id, "tenant_id": tenant.id, "role": "owner"})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "name": user.full_name, "role": "owner"},
        "tenant": {"id": tenant.id, "name": tenant.name, "slug": tenant.slug}
    }

@router.post("/login", response_model=TokenResponse)
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    mem = db.query(Membership).filter(Membership.user_id == user.id).first()
    tenant = db.query(Tenant).filter(Tenant.id == mem.tenant_id).first() if mem else db.query(Tenant).first()
    role = mem.role if mem else "member"

    token = create_access_token({"sub": user.id, "tenant_id": tenant.id if tenant else None, "role": role})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "email": user.email, "name": user.full_name, "role": role},
        "tenant": {"id": tenant.id if tenant else "", "name": tenant.name if tenant else "", "slug": tenant.slug if tenant else ""}
    }

@router.get("/me")
def get_me(ctx=Depends(get_current_tenant_and_user)):
    tenant, user, role = ctx
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.full_name,
            "initials": user.avatar_initials,
            "role": role
        },
        "tenant": {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "timezone": tenant.timezone
        }
    }
