from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from backend.app.database.session import get_db
from backend.app.models.entities import Decision, Case
from backend.app.models.schemas import DecisionCreate, DecisionResponse
from backend.app.services.decision_service import DecisionService
from backend.app.routers.deps import get_current_tenant_and_user, APPROVER_ROLES, require_any_role

router = APIRouter(prefix="/decisions", tags=["Decision Records"])

@router.post("/", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
def record_decision(
    payload: DecisionCreate,
    ctx=Depends(require_any_role(APPROVER_ROLES)),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    try:
        decision = DecisionService.record_decision(
            db=db,
            tenant_id=tenant.id,
            case_id=payload.case_id,
            actor_id=user.id,
            actor_name=user.full_name,
            outcome=payload.outcome,
            rationale=payload.rationale,
            eligible_amount=payload.eligible_amount,
            interest_rate=payload.interest_rate
        )
        return decision
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{case_id}", response_model=List[DecisionResponse])
def get_decisions_for_case(
    case_id: str,
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    decisions = db.query(Decision).filter(
        Decision.case_id == case_id,
        Decision.tenant_id == tenant.id
    ).order_by(Decision.created_at.desc()).all()
    return decisions
