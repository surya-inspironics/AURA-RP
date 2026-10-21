import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from backend.app.database.session import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    timezone = Column(String(100), default="UTC")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    memberships = relationship("Membership", back_populates="tenant", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="tenant", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="tenant", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    avatar_initials = Column(String(10), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")

class Membership(Base):
    __tablename__ = "memberships"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="reviewer")  # owner, admin, manager, reviewer, approver, analyst, auditor
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="memberships")
    user = relationship("User", back_populates="memberships")
    
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_user"),
    )

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    case_number = Column(String(50), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    product_type = Column(String(100), default="Asset finance")  # Commercial lending, Asset finance, Instrument-backed
    requested_amount = Column(Float, nullable=False, default=0.0)
    tenure_months = Column(Integer, nullable=False, default=12)
    purpose = Column(String(255), nullable=True)
    
    status = Column(String(50), nullable=False, default="IN_VALIDATION")  # DRAFT, IN_VALIDATION, READY_FOR_REVIEW, APPROVED, REJECTED, EXCEPTION_RAISED, AWAITING_EVIDENCE
    priority = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, URGENT
    
    owner_id = Column(String(36), nullable=True)
    owner_name = Column(String(100), default="M. Chen")
    owner_initials = Column(String(10), default="MC")
    
    sla_hours = Column(Integer, default=48)
    sla_due_at = Column(DateTime, nullable=True)
    
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="cases")
    evidence_items = relationship("EvidenceItem", back_populates="case", cascade="all, delete-orphan")
    findings = relationship("ValidationFinding", back_populates="case", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="case", cascade="all, delete-orphan")
    exceptions = relationship("ExceptionItem", back_populates="case", cascade="all, delete-orphan")

class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    loan_id = Column(String(100), nullable=False, index=True)
    idempotency_key = Column(String(40), nullable=False)
    provider_order_id = Column(String(100), nullable=True, unique=True, index=True)
    provider_payment_id = Column(String(100), nullable=True, unique=True)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    status = Column(String(40), nullable=False, default="CREATION_PENDING")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_payment_order_tenant_idempotency"),
    )

class GoldLoanCustomer(Base):
    __tablename__ = "gold_loan_customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    external_customer_reference = Column(String(100), nullable=True)
    display_name = Column(String(255), nullable=False)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    applications = relationship("GoldLoanApplication", back_populates="customer")
    __table_args__ = (UniqueConstraint("tenant_id", "external_customer_reference", name="uq_gold_customer_tenant_reference"),)

class GoldLoanApplication(Base):
    __tablename__ = "gold_loan_applications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    customer_id = Column(String(36), ForeignKey("gold_loan_customers.id", ondelete="RESTRICT"), nullable=False, index=True)
    branch_reference = Column(String(100), nullable=True)
    stage = Column(String(40), nullable=False, default="DRAFT")
    consent_status = Column(String(40), nullable=False, default="NOT_RECORDED")
    kyc_status = Column(String(40), nullable=False, default="NOT_STARTED")
    appraisal_status = Column(String(40), nullable=False, default="NOT_STARTED")
    decision_status = Column(String(40), nullable=False, default="NOT_SUBMITTED")
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    case = relationship("Case")
    customer = relationship("GoldLoanCustomer", back_populates="applications")
    consents = relationship("GoldLoanConsent", back_populates="application", cascade="all, delete-orphan")
    collateral_items = relationship("GoldLoanCollateralItem", back_populates="application", cascade="all, delete-orphan")
    valuations = relationship("GoldLoanValuation", back_populates="application", cascade="all, delete-orphan")
    events = relationship("GoldLoanWorkflowEvent", back_populates="application", cascade="all, delete-orphan")

class GoldLoanConsent(Base):
    __tablename__ = "gold_loan_consents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("gold_loan_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String(120), nullable=False)
    wording_version = Column(String(50), nullable=False)
    capture_method = Column(String(50), nullable=False)
    accepted = Column(Boolean, nullable=False)
    captured_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("GoldLoanApplication", back_populates="consents")

class GoldLoanCollateralItem(Base):
    __tablename__ = "gold_loan_collateral_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("gold_loan_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    item_reference = Column(String(50), nullable=False)
    item_type = Column(String(100), nullable=False)
    gross_weight_mg = Column(Integer, nullable=False)
    stone_deduction_mg = Column(Integer, nullable=False, default=0)
    purity_bps = Column(Integer, nullable=False)
    source = Column(String(30), nullable=False, default="MANUAL_SIMULATOR")
    is_simulated = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("GoldLoanApplication", back_populates="collateral_items")
    __table_args__ = (UniqueConstraint("application_id", "item_reference", name="uq_gold_collateral_app_item"),)

class GoldLoanValuation(Base):
    __tablename__ = "gold_loan_valuations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("gold_loan_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    result_json = Column(Text, nullable=False)
    policy_version = Column(String(50), nullable=False)
    rate_version = Column(String(100), nullable=False)
    is_simulated = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("GoldLoanApplication", back_populates="valuations")

class GoldLoanWorkflowEvent(Base):
    __tablename__ = "gold_loan_workflow_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("gold_loan_applications.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), nullable=False)
    actor_name = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    details_json = Column(Text, nullable=False, default="{}")
    is_simulated = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    application = relationship("GoldLoanApplication", back_populates="events")

class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    file_size_bytes = Column(Integer, default=0)
    storage_path = Column(String(500), nullable=False)
    sha256_checksum = Column(String(64), nullable=False)
    
    validation_status = Column(String(50), default="VALIDATING")  # PENDING, VALIDATING, VALIDATED, REJECTED, EXCEPTION
    uploaded_by_id = Column(String(36), nullable=False)
    uploaded_by_name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    case = relationship("Case", back_populates="evidence_items")

class RuleSetVersion(Base):
    __tablename__ = "ruleset_versions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    version = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    rules_json = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    effective_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ValidationFinding(Base):
    __tablename__ = "validation_findings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_id = Column(String(36), nullable=True)
    
    rule_id = Column(String(100), nullable=False)
    rule_name = Column(String(255), nullable=False)
    outcome = Column(String(50), nullable=False)  # PASSED, FAILED, WARNING, NEEDS_REVIEW
    explanation = Column(Text, nullable=False)
    severity = Column(String(20), default="MEDIUM")
    executed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    case = relationship("Case", back_populates="findings")

class Decision(Base):
    __tablename__ = "decisions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    actor_id = Column(String(36), nullable=False)
    actor_name = Column(String(100), nullable=False)
    outcome = Column(String(50), nullable=False)  # APPROVED, REJECTED, RETURNED_FOR_CORRECTION, ESCALATED
    eligible_amount = Column(Float, nullable=True)
    interest_rate = Column(Float, nullable=True)
    rationale = Column(Text, nullable=False)
    rule_version = Column(String(50), default="v1.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    case = relationship("Case", back_populates="decisions")

class ExceptionItem(Base):
    __tablename__ = "exceptions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id = Column(String(36), ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True)
    
    category = Column(String(100), nullable=False)
    severity = Column(String(20), default="HIGH")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), default="OPEN")  # OPEN, ASSIGNED, RESOLVED, ESCALATED
    owner_name = Column(String(100), default="A. Rossi")
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    case = relationship("Case", back_populates="exceptions")

class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), nullable=True)
    actor_name = Column(String(100), nullable=False, default="System")
    action = Column(String(100), nullable=False)  # case.created, evidence.uploaded, validation.executed, decision.recorded, etc.
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(50), nullable=False)
    correlation_id = Column(String(64), nullable=True)
    metadata_json = Column(Text, default="{}")
    
    prev_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    tenant = relationship("Tenant", back_populates="audit_events")

class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    plan_name = Column(String(100), default="Enterprise")
    monthly_price = Column(Float, default=2400.0)
    cases_limit = Column(Integer, default=100)
    storage_limit_mb = Column(Integer, default=102400)  # 100 GB in MB
    seats_limit = Column(Integer, default=25)
    status = Column(String(50), default="active")
    current_period_end = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(50), default="Paid")
    billing_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    pdf_url = Column(String(255), nullable=True)

class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    organization_name = Column(String(255), nullable=True)
    timezone = Column(String(100), default="Asia/Kolkata (IST)")
    default_case_owner = Column(String(100), default="Assign to team queue")
    notification_email = Column(String(255), nullable=True)
    sla_alert_hours = Column(Integer, default=24)
    require_dual_approval = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
