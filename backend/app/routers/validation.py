from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.database.session import get_db
from backend.app.models.entities import ValidationFinding, Case
from backend.app.models.schemas import ValidationRunRequest, ValidationResult, FindingResponse
from backend.app.services.validation_service import ValidationService
from backend.app.routers.deps import get_current_tenant_and_user

router = APIRouter(prefix="/validation", tags=["Validation & Rules Engine"])

@router.post("/run", response_model=ValidationResult)
def run_validation(
    payload: ValidationRunRequest,
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    try:
        result = ValidationService.run_validation(
            db=db,
            tenant_id=tenant.id,
            case_id=payload.case_id,
            actor_id=user.id,
            actor_name=user.full_name,
            rule_version=payload.rule_version or "v1.0"
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/findings/{case_id}", response_model=List[FindingResponse])
def get_case_findings(
    case_id: str,
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    findings = db.query(ValidationFinding).filter(
        ValidationFinding.case_id == case_id,
        ValidationFinding.tenant_id == tenant.id
    ).order_by(ValidationFinding.executed_at.desc()).all()
    return findings
