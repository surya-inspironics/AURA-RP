import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models.entities import (
    PaymentOrder, Case, GoldLoanCustomer, GoldLoanApplication, GoldLoanConsent,
    GoldLoanCollateralItem, GoldLoanValuation, GoldLoanWorkflowEvent,
)
from backend.app.gold_loan.integrations.payment_gateway_adapter import RazorpayProviderError
from backend.app.gold_loan.integrations.registry import adapter_registry
from backend.app.gold_loan.services.eligibility_engine import EligibilityEngine
from backend.app.gold_loan.services.custody_service import CustodyService
from backend.app.gold_loan.services.loan_servicing_engine import LoanServicingEngine
from backend.app.gold_loan.services.collections_engine import CollectionsEngine
from backend.app.routers.deps import (
    APPROVER_ROLES,
    OPERATIONAL_ROLES,
    require_any_role,
    require_authenticated_tenant_and_user,
)
from backend.app.services.audit_service import AuditService

router = APIRouter(
    prefix="/gold-loan",
    tags=["Gold Loan LOS/LMS"],
    dependencies=[Depends(require_authenticated_tenant_and_user)]
)
custody_service = CustodyService()
UNAPPROVED_PILOT_POLICY_VERSION = "UNAPPROVED-PILOT-PREVIEW"


def _require_accepted_pilot_consent(application: GoldLoanApplication) -> None:
    if application.consent_status != "RECORDED":
        raise HTTPException(
            status_code=409,
            detail="Record accepted consent before recording appraisal or valuation inputs",
        )

# Schemas
class GoldItemSchema(BaseModel):
    item_type: str = "Gold Ornament"
    gross_weight_mg: int
    stone_deduction_mg: int = 0
    purity_bps: int = 9160  # 22 Karat (91.6% purity)

class ValuationRequest(BaseModel):
    items: List[GoldItemSchema]
    ltv_scheme_pct: int = 75
    credit_limit_paise: int = 50000000
    capacity_limit_paise: int = 100000000
    product_cap_paise: int = 250000000
    exposure_limit_paise: int = 500000000

class PanVerifyRequest(BaseModel):
    pan: str
    customer_name: str

class AadhaarVerifyRequest(BaseModel):
    aadhaar_number: str
    otp: str
    consent_given: bool = False

class RepaymentOrderRequest(BaseModel):
    loan_id: str = Field(min_length=1, max_length=100)
    amount_paise: int = Field(gt=0)
    idempotency_key: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")

class RepaymentPaymentVerificationRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str

class DisbursalRequest(BaseModel):
    loan_id: str
    amount_paise: int
    beneficiary_account: str
    beneficiary_ifsc: str
    beneficiary_name: str
    maker_id: str
    checker_id: str
    idempotency_key: str

class VaultSealRequest(BaseModel):
    loan_id: str
    custodian_1_id: str
    custodian_2_id: str
    vault_rack_id: str
    item_count: int
    net_weight_mg: int

class AccrueRequest(BaseModel):
    principal_paise: int
    annual_rate_pct: float
    days: int = 1

class WaterfallRepayRequest(BaseModel):
    payment_amount_paise: int
    current_principal_paise: int
    accrued_interest_paise: int
    overdue_interest_paise: int = 0
    penal_charges_paise: int = 0

class MtmEvaluateRequest(BaseModel):
    loan_id: str
    total_outstanding_paise: int
    net_gold_weight_mg: int
    purity_bps: int = 9160

class GoldLoanApplicationCreate(BaseModel):
    case_id: str
    branch_reference: str | None = Field(default=None, max_length=100)
    external_customer_reference: str | None = Field(default=None, max_length=100)
    initial_collateral: GoldItemSchema | None = None

class GoldLoanConsentCreate(BaseModel):
    purpose: str = Field(min_length=3, max_length=120)
    wording_version: str = Field(min_length=1, max_length=50)
    accepted: bool
    capture_method: str = Field(default="STAFF_ATTESTATION", max_length=50)

class GoldLoanKycAttempt(BaseModel):
    pan_status: str = Field(max_length=40)
    aadhaar_status: str = Field(max_length=40)
    masked_pan: str | None = Field(default=None, max_length=10)
    masked_aadhaar: str | None = Field(default=None, max_length=14)

class GoldLoanAssaySimulation(BaseModel):
    device_id: str = Field(max_length=80)
    gross_weight_mg: int = Field(gt=0)
    purity_bps: int = Field(gt=0, le=10000)
    signature_checked: bool = False

class GoldLoanAppraisalRequest(BaseModel):
    items: List[GoldItemSchema] = Field(min_length=1, max_length=30)
    ltv_scheme_pct: int = Field(default=75, ge=1, le=100)
    credit_limit_paise: int = Field(default=50000000, ge=0)
    capacity_limit_paise: int = Field(default=100000000, ge=0)
    product_cap_paise: int = Field(default=250000000, ge=0)
    exposure_limit_paise: int = Field(default=500000000, ge=0)
    policy_version: str = Field(default="DEMO-POLICY-1", max_length=50)

class GoldLoanDecisionRequest(BaseModel):
    outcome: str = Field(pattern="^(REFERRED|REJECTED|APPROVED)$")
    rationale: str = Field(min_length=5, max_length=1000)

def _get_gold_application(db: Session, tenant_id: str, application_id: str) -> GoldLoanApplication:
    application = db.query(GoldLoanApplication).filter(
        GoldLoanApplication.id == application_id,
        GoldLoanApplication.tenant_id == tenant_id,
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Gold-loan application not found")
    return application

def _record_gold_event(db: Session, tenant, user, application: GoldLoanApplication, action: str, details: Dict[str, Any], simulated: bool = False):
    event = GoldLoanWorkflowEvent(
        id=str(uuid.uuid4()), tenant_id=tenant.id, application_id=application.id,
        actor_id=user.id, actor_name=user.full_name, action=action,
        details_json=json.dumps(details, sort_keys=True), is_simulated=simulated,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    AuditService.record_event(
        db=db, tenant_id=tenant.id, actor_id=user.id, actor_name=user.full_name,
        action=f"gold_loan.{action}", entity_type="gold_loan_application",
        entity_id=application.id, metadata={**details, "is_simulated": simulated},
    )
    return event

def _gold_application_response(application: GoldLoanApplication) -> Dict[str, Any]:
    return {
        "id": application.id,
        "case_id": application.case_id,
        "customer_id": application.customer_id,
        "external_customer_reference": application.customer.external_customer_reference if application.customer else None,
        "case_number": application.case.case_number if application.case else None,
        "customer_name": application.case.customer_name if application.case else None,
        "requested_amount": application.case.requested_amount if application.case else None,
        "branch_reference": application.branch_reference,
        "stage": application.stage,
        "consent_status": application.consent_status,
        "kyc_status": application.kyc_status,
        "appraisal_status": application.appraisal_status,
        "decision_status": application.decision_status,
        "collateral_items": [{
            "id": item.id, "item_reference": item.item_reference,
            "item_type": item.item_type, "gross_weight_mg": item.gross_weight_mg,
            "stone_deduction_mg": item.stone_deduction_mg, "purity_bps": item.purity_bps,
            "source": item.source, "is_simulated": item.is_simulated,
        } for item in application.collateral_items],
        "consents": [{
            "id": consent.id, "purpose": consent.purpose,
            "wording_version": consent.wording_version, "capture_method": consent.capture_method,
            "accepted": consent.accepted, "created_at": consent.created_at.isoformat(),
        } for consent in application.consents],
        "valuations": [{
            "id": value.id, "result": json.loads(value.result_json),
            "policy_version": value.policy_version, "rate_version": value.rate_version,
            "is_simulated": value.is_simulated, "created_at": value.created_at.isoformat(),
        } for value in application.valuations],
        "events": [{
            "id": event.id, "actor_name": event.actor_name, "action": event.action,
            "details": json.loads(event.details_json), "is_simulated": event.is_simulated,
            "created_at": event.created_at.isoformat(),
        } for event in sorted(application.events, key=lambda item: item.created_at)],
        "created_at": application.created_at.isoformat(),
        "updated_at": application.updated_at.isoformat(),
    }

@router.get("/applications")
def list_gold_loan_applications(ctx=Depends(require_authenticated_tenant_and_user), db: Session = Depends(get_db)):
    tenant, _, _ = ctx
    rows = db.query(GoldLoanApplication).filter(
        GoldLoanApplication.tenant_id == tenant.id
    ).order_by(GoldLoanApplication.created_at.desc()).all()
    return [_gold_application_response(row) for row in rows]

@router.get("/customers")
def list_gold_loan_customers(ctx=Depends(require_authenticated_tenant_and_user), db: Session = Depends(get_db)):
    tenant, _, _ = ctx
    customers = db.query(GoldLoanCustomer).filter(
        GoldLoanCustomer.tenant_id == tenant.id
    ).order_by(GoldLoanCustomer.created_at.desc()).all()
    return [{
        "id": customer.id,
        "external_customer_reference": customer.external_customer_reference,
        "display_name": customer.display_name,
        "application_count": len(customer.applications),
        "created_at": customer.created_at.isoformat(),
    } for customer in customers]

@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_gold_loan_application(payload: GoldLoanApplicationCreate, ctx=Depends(require_any_role(OPERATIONAL_ROLES)), db: Session = Depends(get_db)):
    tenant, user, _ = ctx
    case = db.query(Case).filter(Case.id == payload.case_id, Case.tenant_id == tenant.id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found in this workspace")
    if case.product_type.lower() != "gold loan":
        raise HTTPException(status_code=409, detail="Gold-loan workflow records require a Gold Loan case")
    existing = db.query(GoldLoanApplication).filter(GoldLoanApplication.case_id == case.id).first()
    if existing:
        return _gold_application_response(existing)
    customer_reference = payload.external_customer_reference.strip() if payload.external_customer_reference else None
    customer = None
    if customer_reference:
        customer = db.query(GoldLoanCustomer).filter(
            GoldLoanCustomer.tenant_id == tenant.id,
            GoldLoanCustomer.external_customer_reference == customer_reference,
        ).first()
    if not customer:
        customer = GoldLoanCustomer(
            tenant_id=tenant.id, external_customer_reference=customer_reference,
            display_name=case.customer_name, created_by=user.id,
        )
        db.add(customer)
        db.flush()
    application = GoldLoanApplication(
        tenant_id=tenant.id, case_id=case.id,
        customer_id=customer.id,
        branch_reference=payload.branch_reference,
        created_by=user.id, created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )
    db.add(application)
    db.flush()
    event_details = {"case_number": case.case_number, "customer_id": customer.id}
    if payload.initial_collateral:
        item = payload.initial_collateral
        if item.gross_weight_mg <= 0 or item.stone_deduction_mg < 0 or item.stone_deduction_mg > item.gross_weight_mg or item.purity_bps < 1 or item.purity_bps > 10000:
            raise HTTPException(status_code=422, detail="Initial collateral estimate has invalid weight or purity")
        db.add(GoldLoanCollateralItem(
            tenant_id=tenant.id, application_id=application.id, item_reference="ITEM-01",
            item_type=item.item_type, gross_weight_mg=item.gross_weight_mg,
            stone_deduction_mg=item.stone_deduction_mg, purity_bps=item.purity_bps,
            source="INTAKE_ESTIMATE", is_simulated=True, created_by=user.id,
        ))
        event_details["initial_collateral_estimate"] = {
            "item_type": item.item_type, "gross_weight_mg": item.gross_weight_mg,
            "purity_bps": item.purity_bps, "is_simulated": True,
        }
    _record_gold_event(db, tenant, user, application, "application.created", event_details, simulated=bool(payload.initial_collateral))
    db.commit()
    db.refresh(application)
    return _gold_application_response(application)

@router.get("/applications/{application_id}")
def get_gold_loan_application(application_id: str, ctx=Depends(require_authenticated_tenant_and_user), db: Session = Depends(get_db)):
    tenant, _, _ = ctx
    return _gold_application_response(_get_gold_application(db, tenant.id, application_id))

@router.post("/applications/{application_id}/consents")
def record_gold_loan_consent(application_id: str, payload: GoldLoanConsentCreate, ctx=Depends(require_any_role(OPERATIONAL_ROLES)), db: Session = Depends(get_db)):
    tenant, user, _ = ctx
    application = _get_gold_application(db, tenant.id, application_id)
    consent = GoldLoanConsent(
        tenant_id=tenant.id, application_id=application.id, purpose=payload.purpose.strip(),
        wording_version=payload.wording_version.strip(), capture_method=payload.capture_method.strip(),
        accepted=payload.accepted, captured_by=user.id,
    )
    db.add(consent)
    application.consent_status = "RECORDED" if payload.accepted else "DECLINED"
    application.stage = "KYC_PENDING" if payload.accepted else "DRAFT"
    _record_gold_event(db, tenant, user, application, "consent.recorded", {
        "purpose": consent.purpose, "wording_version": consent.wording_version,
        "accepted": consent.accepted, "capture_method": consent.capture_method,
    })
    db.commit()
    return {"id": consent.id, "status": application.consent_status, "created_at": consent.created_at.isoformat()}

@router.post("/applications/{application_id}/kyc-simulation")
def record_gold_loan_kyc_simulation(application_id: str, payload: GoldLoanKycAttempt, ctx=Depends(require_any_role(OPERATIONAL_ROLES)), db: Session = Depends(get_db)):
    tenant, user, _ = ctx
    application = _get_gold_application(db, tenant.id, application_id)
    if application.consent_status != "RECORDED":
        raise HTTPException(status_code=409, detail="Record accepted consent before starting verification")
    # Simulated format checks are retained as indeterminate and never clear a financial workflow gate.
    application.kyc_status = "INDETERMINATE"
    application.stage = "KYC_REVIEW"
    _record_gold_event(db, tenant, user, application, "kyc.simulation_recorded", {
        "pan_status": payload.pan_status, "aadhaar_status": payload.aadhaar_status,
        "masked_pan": payload.masked_pan, "masked_aadhaar": payload.masked_aadhaar,
        "provider_verified": False,
    }, simulated=True)
    db.commit()
    return {"status": application.kyc_status, "provider_verified": False, "is_simulated": True}

@router.post("/applications/{application_id}/assay-simulation")
def record_gold_loan_assay_simulation(application_id: str, payload: GoldLoanAssaySimulation, ctx=Depends(require_any_role(OPERATIONAL_ROLES)), db: Session = Depends(get_db)):
    tenant, user, _ = ctx
    application = _get_gold_application(db, tenant.id, application_id)
    _require_accepted_pilot_consent(application)
    item = db.query(GoldLoanCollateralItem).filter(
        GoldLoanCollateralItem.application_id == application.id,
        GoldLoanCollateralItem.item_reference == "ITEM-01",
    ).first()
    if not item:
        item = GoldLoanCollateralItem(
            tenant_id=tenant.id, application_id=application.id, item_reference="ITEM-01",
            item_type="Gold Ornament", stone_deduction_mg=0, created_by=user.id,
        )
        db.add(item)
    if item.stone_deduction_mg > payload.gross_weight_mg:
        raise HTTPException(status_code=422, detail="Simulated gross weight cannot be below the saved deduction")
    item.gross_weight_mg = payload.gross_weight_mg
    item.purity_bps = payload.purity_bps
    item.source = "DEVICE_SIMULATOR"
    item.is_simulated = True
    application.appraisal_status = "SIMULATED_INPUT_RECORDED"
    application.stage = "APPRAISAL_REVIEW"
    _record_gold_event(db, tenant, user, application, "assay.simulation_recorded", {
        "device_id": payload.device_id, "gross_weight_mg": payload.gross_weight_mg,
        "purity_bps": payload.purity_bps, "signature_checked": payload.signature_checked,
        "device_authenticated": False,
    }, simulated=True)
    db.commit()
    return {"recorded": True, "is_simulated": True, "device_authenticated": False}

@router.post("/applications/{application_id}/valuation")
def record_gold_loan_valuation(application_id: str, payload: GoldLoanAppraisalRequest, ctx=Depends(require_any_role(OPERATIONAL_ROLES)), db: Session = Depends(get_db)):
    tenant, user, role = ctx
    application = _get_gold_application(db, tenant.id, application_id)
    _require_accepted_pilot_consent(application)
    if role.lower() not in {"owner", "admin", "manager", "reviewer", "approver"}:
        raise HTTPException(status_code=403, detail="Role cannot record a valuation preview")
    items = []
    for index, item in enumerate(payload.items, start=1):
        if item.gross_weight_mg <= 0 or item.stone_deduction_mg < 0 or item.stone_deduction_mg > item.gross_weight_mg:
            raise HTTPException(status_code=422, detail=f"Collateral item {index} has invalid weights")
        if item.purity_bps < 1 or item.purity_bps > 10000:
            raise HTTPException(status_code=422, detail=f"Collateral item {index} has invalid purity")
        reference = f"ITEM-{index:02d}"
        row = db.query(GoldLoanCollateralItem).filter(
            GoldLoanCollateralItem.application_id == application.id,
            GoldLoanCollateralItem.item_reference == reference,
        ).first()
        if not row:
            row = GoldLoanCollateralItem(tenant_id=tenant.id, application_id=application.id, item_reference=reference, created_by=user.id)
            db.add(row)
        row.item_type, row.gross_weight_mg = item.item_type, item.gross_weight_mg
        row.stone_deduction_mg, row.purity_bps = item.stone_deduction_mg, item.purity_bps
        row.source, row.is_simulated = "MANUAL_SIMULATOR", True
        items.append(item.model_dump())
    rate = adapter_registry.gold_rate.get_gold_rate("24K")
    try:
        result = EligibilityEngine.calculate_valuation_and_eligibility(
            items=items, gold_rate_per_gram_paise=rate["rate_per_gram_paise"],
            rate_version=rate["rate_version"], ltv_scheme_pct=payload.ltv_scheme_pct,
            credit_limit_paise=payload.credit_limit_paise, capacity_limit_paise=payload.capacity_limit_paise,
            product_cap_paise=payload.product_cap_paise, exposure_limit_paise=payload.exposure_limit_paise,
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    valuation = GoldLoanValuation(
        tenant_id=tenant.id, application_id=application.id,
        result_json=json.dumps(result, sort_keys=True), policy_version=UNAPPROVED_PILOT_POLICY_VERSION,
        rate_version=rate["rate_version"], is_simulated=True, created_by=user.id,
    )
    db.add(valuation)
    application.appraisal_status = "SIMULATED_PREVIEW"
    application.stage = "VALUATION_REVIEW"
    _record_gold_event(db, tenant, user, application, "valuation.preview_created", {
        "valuation_id": valuation.id, "item_count": len(items),
        "policy_version": UNAPPROVED_PILOT_POLICY_VERSION, "rate_version": rate["rate_version"],
        "eligible_loan_amount_paise": result["summary"]["eligible_loan_amount_paise"],
    }, simulated=True)
    db.commit()
    return {"id": valuation.id, "result": result, "policy_version": UNAPPROVED_PILOT_POLICY_VERSION,
            "rate_version": rate["rate_version"], "is_simulated": True,
            "application": _gold_application_response(application)}

@router.post("/applications/{application_id}/decisions")
def record_gold_loan_decision(application_id: str, payload: GoldLoanDecisionRequest, ctx=Depends(require_any_role(APPROVER_ROLES)), db: Session = Depends(get_db)):
    tenant, user, role = ctx
    application = _get_gold_application(db, tenant.id, application_id)
    if role.lower() not in {"owner", "admin", "approver"}:
        raise HTTPException(status_code=403, detail="Approver role is required")
    if application.created_by == user.id:
        raise HTTPException(status_code=409, detail="Maker-checker control: the application creator cannot record its decision")
    raise HTTPException(
        status_code=409,
        detail=(
            "Gold-loan decisions are disabled until underwriting policy, identity verification, "
            "trusted assay, and an authorized gold-rate source are approved and configured"
        ),
    )

def _payment_order_response(payment_order: PaymentOrder) -> Dict[str, Any]:
    return {
        "id": payment_order.id,
        "order_id": payment_order.provider_order_id,
        "payment_id": payment_order.provider_payment_id,
        "loan_id": payment_order.loan_id,
        "amount_paise": payment_order.amount_paise,
        "currency": payment_order.currency,
        "status": payment_order.status,
        "created_at": payment_order.created_at.isoformat() if payment_order.created_at else None,
    }

# --- Live Gold Rates (public, no auth required) ---
_public_router = APIRouter(prefix="/gold-loan", tags=["Gold Loan LOS/LMS"])

@_public_router.get("/rates/live")
def get_live_gold_rates():
    """Returns live gold spot rates for 24K / 22K / 18K from a free market-data provider."""
    return adapter_registry.gold_rate.get_all_rates()

@_public_router.get("/rates/live/{karat}")
def get_live_gold_rate_for_karat(karat: str):
    """Returns live gold spot rate for a specific karat (24K, 22K, 18K)."""
    try:
        return adapter_registry.gold_rate.get_gold_rate(karat.upper())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

# --- Valuation & Eligibility ---
@router.post("/valuation/calculate")
def calculate_gold_valuation(payload: ValuationRequest):
    """
    Computes fine weight, market valuation, collateral LTV limit,
    and binding risk limits using the pure integer EligibilityEngine.
    """
    gold_rate_info = adapter_registry.gold_rate.get_gold_rate("24K")
    items_dicts = [item.dict() for item in payload.items]

    result = EligibilityEngine.calculate_valuation_and_eligibility(
        items=items_dicts,
        gold_rate_per_gram_paise=gold_rate_info["rate_per_gram_paise"],
        rate_version=gold_rate_info["rate_version"],
        ltv_scheme_pct=payload.ltv_scheme_pct,
        credit_limit_paise=payload.credit_limit_paise,
        capacity_limit_paise=payload.capacity_limit_paise,
        product_cap_paise=payload.product_cap_paise,
        exposure_limit_paise=payload.exposure_limit_paise
    )
    return result

# --- Device Gateway & Assay Station ---
@router.post("/assay/simulate-reading")
def simulate_device_reading(device_id: str, gross_weight_mg: int, purity_bps: int):
    """
    Generates a cryptographically signed instrument reading from registered device.
    """
    try:
        reading = adapter_registry.device_gateway.generate_signed_reading(
            device_id=device_id,
            gross_weight_mg=gross_weight_mg,
            purity_bps=purity_bps
        )
        return reading
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/assay/verify-reading")
def verify_device_reading(reading: Dict[str, Any]):
    """
    Verifies cryptographic signature, calibration validity, and nonce freshness.
    """
    try:
        verified = adapter_registry.device_gateway.verify_reading(reading)
        return verified
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- KYC & Customer Onboarding ---
@router.post("/kyc/verify-pan")
def verify_pan(payload: PanVerifyRequest):
    return adapter_registry.identity.verify_pan(payload.pan, payload.customer_name)

@router.post("/kyc/verify-aadhaar")
def verify_aadhaar(payload: AadhaarVerifyRequest):
    try:
        return adapter_registry.identity.verify_aadhaar_ekyc(
            aadhaar_number=payload.aadhaar_number,
            otp=payload.otp,
            consent_given=payload.consent_given
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Repayments (Money In) ---
@router.post("/repayments/create-order")
def create_repayment_order(
    payload: RepaymentOrderRequest,
    ctx=Depends(require_authenticated_tenant_and_user),
    db: Session = Depends(get_db),
):
    tenant, _, _ = ctx
    gateway = adapter_registry.payment_gateway
    try:
        gateway.assert_test_checkout_enabled()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    existing = db.query(PaymentOrder).filter(
        PaymentOrder.tenant_id == tenant.id,
        PaymentOrder.idempotency_key == payload.idempotency_key,
    ).first()
    if existing:
        if existing.loan_id != payload.loan_id.strip() or existing.amount_paise != payload.amount_paise:
            raise HTTPException(status_code=409, detail="This idempotency key is already associated with a different payment request.")
        if not existing.provider_order_id:
            raise HTTPException(
                status_code=409,
                detail="The previous Razorpay order request needs reconciliation. Do not submit a new payment request.",
            )
        return {
            **_payment_order_response(existing),
            "key_id": settings.RAZORPAY_KEY_ID,
            "idempotent_replay": True,
        }

    payment_order = PaymentOrder(
        tenant_id=tenant.id,
        loan_id=payload.loan_id.strip(),
        idempotency_key=payload.idempotency_key,
        amount_paise=payload.amount_paise,
        currency="INR",
        status="CREATION_PENDING",
    )
    db.add(payment_order)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.query(PaymentOrder).filter(
            PaymentOrder.tenant_id == tenant.id,
            PaymentOrder.idempotency_key == payload.idempotency_key,
        ).first()
        if existing and existing.loan_id == payload.loan_id.strip() and existing.amount_paise == payload.amount_paise and existing.provider_order_id:
            return {
                **_payment_order_response(existing),
                "key_id": settings.RAZORPAY_KEY_ID,
                "idempotent_replay": True,
            }
        raise HTTPException(status_code=409, detail="A payment order with this idempotency key already exists.")

    try:
        provider_order = gateway.create_payment_order(
            loan_id=payment_order.loan_id,
            amount_paise=payment_order.amount_paise,
            idempotency_key=payment_order.idempotency_key,
        )
    except RazorpayProviderError as exc:
        payment_order.status = "RECONCILIATION_REQUIRED"
        db.commit()
        raise HTTPException(
            status_code=502,
            detail="Razorpay did not confirm order creation. This request is held for reconciliation; do not retry with a new reference.",
        ) from exc

    payment_order.provider_order_id = provider_order["order_id"]
    payment_order.status = provider_order["status"]
    db.commit()
    db.refresh(payment_order)
    return {
        **_payment_order_response(payment_order),
        "key_id": settings.RAZORPAY_KEY_ID,
        "is_test_mode": True,
        "is_simulated": False,
        "provider_confirmed": False,
        "message": provider_order["message"],
    }

@router.get("/repayments/orders")
def list_repayment_orders(
    ctx=Depends(require_authenticated_tenant_and_user),
    db: Session = Depends(get_db),
):
    tenant, _, _ = ctx
    orders = db.query(PaymentOrder).filter(
        PaymentOrder.tenant_id == tenant.id
    ).order_by(PaymentOrder.created_at.desc()).limit(200).all()
    return {"orders": [_payment_order_response(order) for order in orders]}

@router.post("/repayments/verify-payment")
def verify_repayment_payment(
    payload: RepaymentPaymentVerificationRequest,
    ctx=Depends(require_authenticated_tenant_and_user),
    db: Session = Depends(get_db),
):
    tenant, _, _ = ctx
    payment_order = db.query(PaymentOrder).filter(
        PaymentOrder.tenant_id == tenant.id,
        PaymentOrder.provider_order_id == payload.order_id,
    ).first()
    if not payment_order:
        raise HTTPException(status_code=404, detail="Payment order not found in this workspace.")
    if payment_order.status == "CAPTURED":
        return _payment_order_response(payment_order)

    try:
        result = adapter_registry.payment_gateway.verify_checkout_payment(
            order_id=payload.order_id,
            payment_id=payload.payment_id,
            signature=payload.signature,
            expected_amount_paise=payment_order.amount_paise,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RazorpayProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    payment_order.provider_payment_id = result["payment_id"]
    payment_order.status = result["status"]
    db.commit()
    db.refresh(payment_order)
    return {
        **_payment_order_response(payment_order),
        "is_test_mode": True,
        "is_simulated": False,
        "provider_confirmed": result["provider_confirmed"],
        "ledger_updated": False,
        "message": result["message"],
    }

# --- Disbursals (Money Out) ---
@router.post("/disbursals/execute")
def execute_disbursal(payload: DisbursalRequest, ctx=Depends(require_any_role(APPROVER_ROLES))):
    _, user, _ = ctx
    if payload.maker_id != user.id:
        raise HTTPException(status_code=403, detail="Maker identity must match the authenticated user")
    raise HTTPException(
        status_code=409,
        detail="Disbursal is unavailable until maker and checker approvals are independently authenticated.",
    )

# --- Vault Packet Custody ---
@router.post("/vault/seal")
def seal_vault_packet(payload: VaultSealRequest, ctx=Depends(require_any_role(OPERATIONAL_ROLES))):
    _, user, _ = ctx
    if payload.custodian_1_id != user.id:
        raise HTTPException(status_code=403, detail="First custodian must match the authenticated user")
    raise HTTPException(
        status_code=409,
        detail="Vault sealing is unavailable until both custodians are independently authenticated.",
    )

# --- Servicing & Calculations ---
@router.post("/servicing/accrue")
def calculate_accrual(payload: AccrueRequest):
    accrued = LoanServicingEngine.calculate_daily_interest_accrual(
        principal_paise=payload.principal_paise,
        annual_rate_pct=payload.annual_rate_pct,
        days=payload.days
    )
    return {
        "accrued_paise": accrued,
        "accrued_inr": accrued / 100.0,
        "days": payload.days
    }

@router.post("/servicing/allocate-repayment")
def allocate_repayment(payload: WaterfallRepayRequest):
    return LoanServicingEngine.allocate_repayment_waterfall(
        payment_amount_paise=payload.payment_amount_paise,
        current_principal_paise=payload.current_principal_paise,
        accrued_interest_paise=payload.accrued_interest_paise,
        overdue_interest_paise=payload.overdue_interest_paise,
        penal_charges_paise=payload.penal_charges_paise
    )

@router.post("/collections/evaluate-mtm")
def evaluate_mtm(payload: MtmEvaluateRequest):
    gold_rate_info = adapter_registry.gold_rate.get_gold_rate("24K")
    return CollectionsEngine.evaluate_mtm_ltv(
        loan_id=payload.loan_id,
        total_outstanding_paise=payload.total_outstanding_paise,
        net_gold_weight_mg=payload.net_gold_weight_mg,
        purity_bps=payload.purity_bps,
        current_24k_rate_per_gram_paise=gold_rate_info["rate_per_gram_paise"]
    )


# ── NPA Classification ──────────────────────────────────────────────────────

class NpaClassifyRequest(BaseModel):
    loan_id: str
    dpd: int = Field(ge=0, description="Days Past Due")
    outstanding_paise: int = Field(ge=0)

@router.post("/collections/classify-npa")
def classify_npa(payload: NpaClassifyRequest):
    """
    Classifies loan asset quality per RBI NPA norms.
    Sub-Standard: DPD 90–364 days
    Doubtful:     DPD 365–729 days
    Loss:         DPD ≥ 730 days
    Gold loans (max 12 months): default at DPD 90+
    """
    dpd = payload.dpd
    if dpd < 0:
        raise HTTPException(status_code=422, detail="DPD cannot be negative")

    if dpd < 1:
        asset_class = "STANDARD"
        provision_pct = 0.4
    elif dpd < 90:
        asset_class = "SPECIAL_MENTION_ACCOUNT"
        provision_pct = 1.0
    elif dpd < 365:
        asset_class = "SUB_STANDARD"
        provision_pct = 15.0
    elif dpd < 730:
        asset_class = "DOUBTFUL_1"
        provision_pct = 25.0 if dpd < 455 else 40.0
    else:
        asset_class = "LOSS"
        provision_pct = 100.0

    provision_paise = int(payload.outstanding_paise * provision_pct / 100)
    requires_auction = dpd >= 90

    return {
        "loan_id": payload.loan_id,
        "dpd": dpd,
        "asset_class": asset_class,
        "provision_requirement_pct": provision_pct,
        "provision_amount_paise": provision_paise,
        "provision_amount_inr": provision_paise / 100.0,
        "requires_auction": requires_auction,
        "rbi_circular": "DBOD.No.BP.BC.37/21.04.048/2001-02",
        "compliance_note": "COMPLIANCE TO CONFIRM – verify applicable RBI/NHB circular for gold NBFC classification",
    }


# ── DPD Calculator ──────────────────────────────────────────────────────────

class DpdRequest(BaseModel):
    loan_id: str
    disbursement_date: str = Field(description="YYYY-MM-DD")
    last_payment_date: str | None = Field(default=None, description="YYYY-MM-DD or null if never paid")
    repayment_frequency: str = Field(default="BULLET", description="BULLET | MONTHLY | QUARTERLY")

@router.post("/servicing/calculate-dpd")
def calculate_dpd(payload: DpdRequest):
    """Calculates Days Past Due from disbursement and last payment dates."""
    from datetime import date
    today = date.today()
    try:
        disburse_dt = date.fromisoformat(payload.disbursement_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="disbursement_date must be YYYY-MM-DD")

    if payload.last_payment_date:
        try:
            last_pay_dt = date.fromisoformat(payload.last_payment_date)
        except ValueError:
            raise HTTPException(status_code=422, detail="last_payment_date must be YYYY-MM-DD")
    else:
        last_pay_dt = None

    if last_pay_dt:
        dpd = max(0, (today - last_pay_dt).days)
    else:
        dpd = max(0, (today - disburse_dt).days)

    return {
        "loan_id": payload.loan_id,
        "disbursement_date": payload.disbursement_date,
        "last_payment_date": payload.last_payment_date,
        "today": today.isoformat(),
        "dpd": dpd,
        "bucket": (
            "CURRENT" if dpd == 0 else
            "1-30 DPD" if dpd <= 30 else
            "31-60 DPD" if dpd <= 60 else
            "61-90 DPD" if dpd <= 90 else
            "SMA-2 / NPA" if dpd <= 180 else
            "DEEP_NPA"
        ),
    }


# ── Auction Trigger ─────────────────────────────────────────────────────────

class AuctionTriggerRequest(BaseModel):
    loan_id: str
    dpd: int
    collateral_value_paise: int
    outstanding_paise: int
    notice_served: bool = False
    notice_date: str | None = None

@router.post("/collections/trigger-auction")
def trigger_auction(payload: AuctionTriggerRequest):
    """
    Validates pre-conditions and schedules auction for an NPA gold loan.
    Per RBI: 30-day notice required before auction; reserve price ≥ outstanding + charges.
    """
    from datetime import date, timedelta
    errors = []
    if payload.dpd < 90:
        errors.append(f"DPD is {payload.dpd}; auction requires DPD ≥ 90")
    if not payload.notice_served:
        errors.append("30-day auction notice has not been served to borrower")

    if errors:
        raise HTTPException(status_code=409, detail="; ".join(errors))

    reserve_price_paise = int(payload.outstanding_paise * 1.05)  # 5% buffer above outstanding
    if reserve_price_paise > payload.collateral_value_paise:
        reserve_price_paise = payload.collateral_value_paise

    notice_dt = date.fromisoformat(payload.notice_date) if payload.notice_date else date.today() - timedelta(days=31)
    auction_eligible_after = notice_dt + timedelta(days=30)

    return {
        "loan_id": payload.loan_id,
        "auction_eligible": True,
        "auction_eligible_after": auction_eligible_after.isoformat(),
        "reserve_price_paise": reserve_price_paise,
        "reserve_price_inr": reserve_price_paise / 100.0,
        "collateral_value_paise": payload.collateral_value_paise,
        "outstanding_paise": payload.outstanding_paise,
        "surplus_if_sold_at_reserve_paise": max(0, reserve_price_paise - payload.outstanding_paise),
        "compliance_note": "COMPLIANCE TO CONFIRM – verify SARFAESI / RBI auction guidelines",
        "is_simulated": True,
    }


# ── Loan Closure & Gold Release ─────────────────────────────────────────────

class LoanClosureRequest(BaseModel):
    loan_id: str
    principal_paise: int
    accrued_interest_paise: int
    penal_charges_paise: int = 0
    payment_received_paise: int

@router.post("/servicing/close-and-release")
def close_and_release(payload: LoanClosureRequest):
    """
    Validates full loan closure and authorizes gold release.
    Returns a release authorization token (simulated) for vault.
    """
    import uuid as _uuid
    total_due = payload.principal_paise + payload.accrued_interest_paise + payload.penal_charges_paise
    shortfall = total_due - payload.payment_received_paise

    if shortfall > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Insufficient payment. Total due: ₹{total_due/100:.2f}, received: ₹{payload.payment_received_paise/100:.2f}, shortfall: ₹{shortfall/100:.2f}"
        )

    surplus = payload.payment_received_paise - total_due

    return {
        "loan_id": payload.loan_id,
        "status": "CLOSED",
        "total_paid_paise": payload.payment_received_paise,
        "total_due_paise": total_due,
        "surplus_refund_paise": surplus,
        "surplus_refund_inr": surplus / 100.0,
        "gold_release_authorized": True,
        "release_authorization_token": str(_uuid.uuid4()),
        "message": "Loan fully cleared. Gold release order generated. Vault dual-custody verification required.",
        "is_simulated": True,
    }
