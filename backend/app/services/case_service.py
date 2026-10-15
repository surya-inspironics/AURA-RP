import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import Case, EvidenceItem
from backend.app.services.audit_service import AuditService

VALID_STATUSES = [
    "DRAFT", "IN_VALIDATION", "READY_FOR_REVIEW", "APPROVED", "REJECTED", "EXCEPTION_RAISED", "AWAITING_EVIDENCE"
]

TRANSITIONS: Dict[str, List[str]] = {
    "DRAFT": ["IN_VALIDATION", "AWAITING_EVIDENCE"],
    "IN_VALIDATION": ["READY_FOR_REVIEW", "EXCEPTION_RAISED", "AWAITING_EVIDENCE"],
    "AWAITING_EVIDENCE": ["IN_VALIDATION", "DRAFT"],
    "READY_FOR_REVIEW": ["APPROVED", "REJECTED", "EXCEPTION_RAISED", "IN_VALIDATION"],
    "EXCEPTION_RAISED": ["IN_VALIDATION", "READY_FOR_REVIEW", "REJECTED"],
    "APPROVED": [],
    "REJECTED": ["DRAFT"]
}

class CaseService:
    @staticmethod
    def generate_case_number() -> str:
        year = datetime.now().year
        num = random.randint(1000, 9999)
        return f"AUR-{year}-{num:05d}"

    @staticmethod
    def create_case(
        db: Session,
        tenant_id: str,
        customer_name: str,
        requested_amount: float,
        tenure_months: int,
        purpose: Optional[str] = None,
        product_type: str = "Asset finance",
        priority: str = "MEDIUM",
        created_by: str = "user-system",
        owner_name: str = "M. Chen",
        owner_initials: str = "MC"
    ) -> Case:
        case_number = CaseService.generate_case_number()
        sla_hours = 48 if priority == "MEDIUM" else 24 if priority in ["HIGH", "URGENT"] else 72
        now = datetime.now(timezone.utc)
        sla_due_at = now + timedelta(hours=sla_hours)

        case = Case(
            tenant_id=tenant_id,
            case_number=case_number,
            customer_name=customer_name,
            product_type=product_type,
            requested_amount=requested_amount,
            tenure_months=tenure_months,
            purpose=purpose,
            status="IN_VALIDATION",
            priority=priority,
            owner_name=owner_name,
            owner_initials=owner_initials,
            sla_hours=sla_hours,
            sla_due_at=sla_due_at,
            created_by=created_by,
            created_at=now,
            updated_at=now
        )
        db.add(case)
        db.flush()

        AuditService.record_event(
            db=db,
            tenant_id=tenant_id,
            action="case.created",
            entity_type="case",
            entity_id=case.id,
            actor_id=created_by,
            actor_name=owner_name,
            metadata={"case_number": case_number, "customer_name": customer_name, "amount": requested_amount}
        )
        db.commit()
        db.refresh(case)
        return case

    @staticmethod
    def transition_status(
        db: Session,
        tenant_id: str,
        case_id: str,
        new_status: str,
        actor_id: str,
        actor_name: str,
        reason: Optional[str] = None
    ) -> Case:
        case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
        if not case:
            raise ValueError("Case not found")

        current_status = case.status
        allowed = TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(f"Invalid transition from {current_status} to {new_status}. Allowed: {allowed}")

        case.status = new_status
        case.updated_at = datetime.now(timezone.utc)
        db.add(case)
        db.flush()

        AuditService.record_event(
            db=db,
            tenant_id=tenant_id,
            action="case.status_changed",
            entity_type="case",
            entity_id=case.id,
            actor_id=actor_id,
            actor_name=actor_name,
            metadata={"from_status": current_status, "to_status": new_status, "reason": reason}
        )
        db.commit()
        db.refresh(case)
        return case
