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

        if case.created_by == actor_id and outcome == "APPROVED":
            raise ValueError("Maker-checker control: the application creator cannot approve their own case")

        if case.product_type.lower() == "gold loan" and outcome == "APPROVED":
            from backend.app.models.entities import GoldLoanApplication
            gold_application = db.query(GoldLoanApplication).filter(
                GoldLoanApplication.case_id == case.id,
                GoldLoanApplication.tenant_id == tenant_id,
            ).first()
            if not gold_application:
                raise ValueError("Gold-loan workflow record is required before approval")
            if gold_application.consent_status != "RECORDED" or gold_application.kyc_status != "VERIFIED" or gold_application.appraisal_status != "VERIFIED":
                raise ValueError("Gold-loan approval is blocked until consent, provider-verified KYC and trusted appraisal are complete")

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
                "maker_checker_self_approval": False
            }
        )
        db.commit()
        db.refresh(decision)
        return decision
