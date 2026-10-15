from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2)
    organization_name: Optional[str] = "Northstar Bank"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]
    tenant: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    avatar_initials: Optional[str]
    is_active: bool
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

# Tenant Schemas
class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    timezone: str
    created_at: datetime

    class Config:
        from_attributes = True

# Case Schemas
class CaseCreate(BaseModel):
    customer_name: str = Field(min_length=2)
    requested_amount: float = Field(gt=0)
    tenure_months: int = Field(gt=0, default=12)
    purpose: Optional[str] = None
    product_type: Optional[str] = "Asset finance"
    priority: Optional[str] = "MEDIUM"

class CaseUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None

class CaseResponse(BaseModel):
    id: str
    tenant_id: str
    case_number: str
    customer_name: str
    product_type: str
    requested_amount: float
    tenure_months: int
    purpose: Optional[str]
    status: str
    priority: str
    owner_name: str
    owner_initials: str
    sla_hours: int
    sla_due_at: Optional[datetime]
    created_by: str
    created_at: datetime
    updated_at: datetime
    files_count: Optional[int] = 0

    class Config:
        from_attributes = True

# Evidence Schemas
class EvidenceResponse(BaseModel):
    id: str
    tenant_id: str
    case_id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    sha256_checksum: str
    validation_status: str
    uploaded_by_name: str
    created_at: datetime

    class Config:
        from_attributes = True

# Validation Schemas
class ValidationRunRequest(BaseModel):
    case_id: str
    rule_version: Optional[str] = "v1.0"

class FindingResponse(BaseModel):
    id: str
    rule_id: str
    rule_name: str
    outcome: str
    explanation: str
    severity: str
    executed_at: datetime

    class Config:
        from_attributes = True

class ValidationResult(BaseModel):
    case_id: str
    overall_status: str
    passed_rules: int
    failed_rules: int
    warning_rules: int
    findings: List[FindingResponse]

# Decision Schemas
class DecisionCreate(BaseModel):
    case_id: str
    outcome: str = Field(pattern="^(APPROVED|REJECTED|RETURNED_FOR_CORRECTION|ESCALATED)$")
    eligible_amount: Optional[float] = None
    interest_rate: Optional[float] = None
    rationale: str = Field(min_length=5)

class DecisionResponse(BaseModel):
    id: str
    case_id: str
    actor_name: str
    outcome: str
    eligible_amount: Optional[float]
    interest_rate: Optional[float]
    rationale: str
    rule_version: str
    created_at: datetime

    class Config:
        from_attributes = True

# Audit Schemas
class AuditEventResponse(BaseModel):
    id: str
    actor_name: str
    action: str
    entity_type: str
    entity_id: str
    correlation_id: Optional[str]
    metadata: Dict[str, Any]
    prev_hash: str
    current_hash: str
    created_at: datetime

    class Config:
        from_attributes = True

# Analytics & Dashboard Schemas
class OverviewKPIs(BaseModel):
    open_cases: int
    pending_validation: int
    awaiting_decision: int
    open_exceptions: int
    total_cases: int
    sla_compliance_rate: float
    validation_pass_rate: float
    avg_processing_hours: float
    active_filters_count: int

class WorkflowDistribution(BaseModel):
    in_progress: int
    ready_for_review: int
    awaiting_evidence: int
    approved: int
    rejected: int
    exceptions: int

class TrendPoint(BaseModel):
    date: str
    submitted: int
    validated: int
    decided: int

class AnalyticsDashboard(BaseModel):
    kpis: OverviewKPIs
    workflow: WorkflowDistribution
    trends: List[TrendPoint]
    funnel: Dict[str, int]
    sla_performance: Dict[str, Any]

# Team Member Schemas
class MemberInvite(BaseModel):
    email: EmailStr
    full_name: str
    role: str = "reviewer"

class MemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    full_name: str
    avatar_initials: str
    role: str
    is_active: bool
    created_at: datetime

# Billing Schemas
class BillingSummary(BaseModel):
    plan_name: str
    monthly_price: float
    cases_used: int
    cases_limit: int
    storage_used_gb: float
    storage_limit_gb: float
    seats_used: int
    seats_limit: int
    status: str
    renewal_date: str
    invoices: List[Dict[str, Any]]
