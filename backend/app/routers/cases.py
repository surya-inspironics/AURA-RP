from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.app.database.session import get_db
from backend.app.models.entities import Case, EvidenceItem, ValidationFinding, Decision
from backend.app.models.schemas import CaseCreate, CaseResponse, CaseUpdate
from backend.app.services.case_service import CaseService
from backend.app.routers.deps import get_current_tenant_and_user

router = APIRouter(prefix="/cases", tags=["Case Management"])

@router.get("/", response_model=List[CaseResponse])
def list_cases(
    q: Optional[str] = Query(None, description="Search term for case number or customer name"),
    status: Optional[str] = Query(None, description="Filter by case status"),
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    query = db.query(Case).filter(Case.tenant_id == tenant.id)

    if status and status != "All":
        query = query.filter(Case.status == status)

    if q:
        search_filter = f"%{q.lower()}%"
        query = query.filter(
            (Case.customer_name.ilike(search_filter)) |
            (Case.case_number.ilike(search_filter)) |
            (Case.product_type.ilike(search_filter))
        )

    cases = query.order_by(Case.created_at.desc()).all()

    # Enrich with files count
    results = []
    for c in cases:
        files_count = db.query(EvidenceItem).filter(
            EvidenceItem.case_id == c.id,
            EvidenceItem.tenant_id == tenant.id
        ).count()
        
        results.append(
            CaseResponse(
                id=c.id,
                tenant_id=c.tenant_id,
                case_number=c.case_number,
                customer_name=c.customer_name,
                product_type=c.product_type,
                requested_amount=c.requested_amount,
                tenure_months=c.tenure_months,
                purpose=c.purpose,
                status=c.status,
                priority=c.priority,
                owner_name=c.owner_name,
                owner_initials=c.owner_initials,
                sla_hours=c.sla_hours,
                sla_due_at=c.sla_due_at,
                created_by=c.created_by,
                created_at=c.created_at,
                updated_at=c.updated_at,
                files_count=files_count
            )
        )
    return results

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: CaseCreate,
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    case = CaseService.create_case(
        db=db,
        tenant_id=tenant.id,
        customer_name=payload.customer_name,
        requested_amount=payload.requested_amount,
        tenure_months=payload.tenure_months,
        purpose=payload.purpose,
        product_type=payload.product_type or "Asset finance",
        priority=payload.priority or "MEDIUM",
        created_by=user.id,
        owner_name=user.full_name,
        owner_initials=user.avatar_initials or "JD"
    )

    return CaseResponse(
        id=case.id,
        tenant_id=case.tenant_id,
        case_number=case.case_number,
        customer_name=case.customer_name,
        product_type=case.product_type,
        requested_amount=case.requested_amount,
        tenure_months=case.tenure_months,
        purpose=case.purpose,
        status=case.status,
        priority=case.priority,
        owner_name=case.owner_name,
        owner_initials=case.owner_initials,
        sla_hours=case.sla_hours,
        sla_due_at=case.sla_due_at,
        created_by=case.created_by,
        created_at=case.created_at,
        updated_at=case.updated_at,
        files_count=0
    )

@router.get("/{case_id}")
def get_case_detail(
    case_id: str,
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found in your workspace")

    evidence = db.query(EvidenceItem).filter(EvidenceItem.case_id == case.id, EvidenceItem.tenant_id == tenant.id).all()
    findings = db.query(ValidationFinding).filter(ValidationFinding.case_id == case.id, ValidationFinding.tenant_id == tenant.id).all()
    decisions = db.query(Decision).filter(Decision.case_id == case.id, Decision.tenant_id == tenant.id).all()

    return {
        "case": {
            "id": case.id,
            "case_number": case.case_number,
            "customer_name": case.customer_name,
            "product_type": case.product_type,
            "requested_amount": case.requested_amount,
            "tenure_months": case.tenure_months,
            "purpose": case.purpose,
            "status": case.status,
            "priority": case.priority,
            "owner_name": case.owner_name,
            "owner_initials": case.owner_initials,
            "sla_hours": case.sla_hours,
            "sla_due_at": case.sla_due_at,
            "created_at": case.created_at,
            "updated_at": case.updated_at
        },
        "evidence": [
            {
                "id": e.id,
                "file_name": e.file_name,
                "file_type": e.file_type,
                "file_size_bytes": e.file_size_bytes,
                "sha256_checksum": e.sha256_checksum,
                "validation_status": e.validation_status,
                "uploaded_by_name": e.uploaded_by_name,
                "created_at": e.created_at
            }
            for e in evidence
        ],
        "findings": [
            {
                "id": f.id,
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "outcome": f.outcome,
                "explanation": f.explanation,
                "severity": f.severity,
                "executed_at": f.executed_at
            }
            for f in findings
        ],
        "decisions": [
            {
                "id": d.id,
                "actor_name": d.actor_name,
                "outcome": d.outcome,
                "eligible_amount": d.eligible_amount,
                "interest_rate": d.interest_rate,
                "rationale": d.rationale,
                "rule_version": d.rule_version,
                "created_at": d.created_at
            }
            for d in decisions
        ]
    }

@router.post("/{case_id}/transition")
def transition_case_status(
    case_id: str,
    target_status: str = Query(..., description="Target status for transition"),
    reason: Optional[str] = Query(None),
    ctx=Depends(get_current_tenant_and_user),
    db: Session = Depends(get_db)
):
    tenant, user, role = ctx
    try:
        case = CaseService.transition_status(
            db=db,
            tenant_id=tenant.id,
            case_id=case_id,
            new_status=target_status,
            actor_id=user.id,
            actor_name=user.full_name,
            reason=reason
        )
        return {"status": "success", "new_status": case.status, "case_id": case.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
