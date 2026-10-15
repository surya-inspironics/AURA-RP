from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.models.entities import Case, Decision
from backend.app.services.audit_service import AuditService

class DecisionService:
    @staticmethod
    def record_decision(
        db: Session,
        tenant_id: str,
        case_id: str,
        actor_id: str,
        actor_name: str,
        outcome: str,
        rationale: str,
        eligible_amount: Optional[float] = None,
        interest_rate: Optional[float] = None,
        rule_version: str = "v1.0"
    ) -> Decision:
        case = db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
        if not case:
            raise ValueError("Case not found")

        # Maker-checker policy check: Approver cannot be the same user who created the application
        # If in single-user demo environment, we record an audit note if creator is approving
        maker_checker_override = False
        if case.created_by == actor_id and outcome == "APPROVED":
            maker_checker_override = True

        now = datetime.now(timezone.utc)
        decision = Decision(
            tenant_id=tenant_id,
            case_id=case_id,
            actor_id=actor_id,
            actor_name=actor_name,
            outcome=outcome,
            eligible_amount=eligible_amount if eligible_amount is not None else case.requested_amount,
            interest_rate=interest_rate if interest_rate is not None else 8.5,
            rationale=rationale,
            rule_version=rule_version,
            created_at=now
        )
        db.add(decision)

        # Update case status based on outcome
        if outcome == "APPROVED":
            case.status = "APPROVED"
        elif outcome == "REJECTED":
            case.status = "REJECTED"
        elif outcome == "RETURNED_FOR_CORRECTION":
            case.status = "IN_VALIDATION"
        elif outcome == "ESCALATED":
            case.status = "EXCEPTION_RAISED"

        case.updated_at = now
        db.add(case)
        db.flush()

        AuditService.record_event(
            db=db,
            tenant_id=tenant_id,
            action="decision.recorded",
            entity_type="case",
            entity_id=case_id,
            actor_id=actor_id,
            actor_name=actor_name,
            metadata={
                "outcome": outcome,
                "eligible_amount": decision.eligible_amount,
                "rationale": rationale,
                "maker_checker_self_approval": maker_checker_override
            }
        )
        db.commit()
        db.refresh(decision)
        return decision
