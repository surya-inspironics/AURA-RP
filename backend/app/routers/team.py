from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.database.session import get_db
from backend.app.models.entities import User, Membership
from backend.app.models.schemas import MemberInvite, MemberResponse
from backend.app.core.security import hash_password
from backend.app.services.audit_service import AuditService
from backend.app.routers.deps import get_current_tenant_and_user

router = APIRouter(prefix="/team", tags=["Team & Workspace Management"])

@router.get("/", response_model=List[MemberResponse])
def list_team_members(
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    memberships = db.query(Membership).filter(Membership.tenant_id == tenant.id).all()
    results = []
    for m in memberships:
        u = db.query(User).filter(User.id == m.user_id).first()
        if u:
            results.append(
                MemberResponse(
                    id=m.id,
                    user_id=u.id,
                    email=u.email,
                    full_name=u.full_name,
                    avatar_initials=u.avatar_initials or "TM",
                    role=m.role.capitalize(),
                    is_active=u.is_active,
                    created_at=m.created_at
                )
            )
    return results

@router.post("/invite", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    payload: MemberInvite,
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    if role not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Only workspace Owners or Administrators can invite new members")

    # Check if user already exists
    u = db.query(User).filter(User.email == payload.email.lower()).first()
    if not u:
        initials = "".join([p[0].upper() for p in payload.full_name.split()[:2]]) or "TM"
        u = User(
            email=payload.email.lower(),
            hashed_password=hash_password("AuraWelcome2026!"),
            full_name=payload.full_name,
            avatar_initials=initials,
            is_active=True
        )
        db.add(u)
        db.flush()

    existing_mem = db.query(Membership).filter(
        Membership.tenant_id == tenant.id,
        Membership.user_id == u.id
    ).first()
    if existing_mem:
        raise HTTPException(status_code=400, detail="User is already a member of this workspace")

    mem = Membership(
        tenant_id=tenant.id,
        user_id=u.id,
        role=payload.role.lower()
    )
    db.add(mem)
    db.flush()

    AuditService.record_event(
        db=db,
        tenant_id=tenant.id,
        action="team.member_invited",
        entity_type="membership",
        entity_id=mem.id,
        actor_id=user.id,
        actor_name=user.full_name,
        metadata={"invited_email": payload.email, "role": payload.role}
    )
    db.commit()

    return MemberResponse(
        id=mem.id,
        user_id=u.id,
        email=u.email,
        full_name=u.full_name,
        avatar_initials=u.avatar_initials or "TM",
        role=mem.role.capitalize(),
        is_active=u.is_active,
        created_at=mem.created_at
    )
