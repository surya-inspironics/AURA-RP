from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models.entities import PaymentOrder
from backend.app.gold_loan.integrations.payment_gateway_adapter import RazorpayProviderError
from backend.app.gold_loan.integrations.registry import adapter_registry
from backend.app.gold_loan.services.eligibility_engine import EligibilityEngine
from backend.app.gold_loan.services.custody_service import CustodyService
from backend.app.gold_loan.services.loan_servicing_engine import LoanServicingEngine
from backend.app.gold_loan.services.collections_engine import CollectionsEngine
from backend.app.routers.deps import require_authenticated_tenant_and_user

router = APIRouter(
    prefix="/gold-loan",
    tags=["Gold Loan LOS/LMS"],
    dependencies=[Depends(require_authenticated_tenant_and_user)]
)
custody_service = CustodyService()

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
def execute_disbursal(payload: DisbursalRequest):
    try:
        payout = adapter_registry.disbursal.execute_disbursal(
            loan_id=payload.loan_id,
            amount_paise=payload.amount_paise,
            beneficiary_account=payload.beneficiary_account,
            beneficiary_ifsc=payload.beneficiary_ifsc,
            beneficiary_name=payload.beneficiary_name,
            maker_id=payload.maker_id,
            checker_id=payload.checker_id,
            idempotency_key=payload.idempotency_key
        )
        return payout
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Vault Packet Custody ---
@router.post("/vault/seal")
def seal_vault_packet(payload: VaultSealRequest):
    try:
        packet = custody_service.seal_packet(
            loan_id=payload.loan_id,
            custodian_1_id=payload.custodian_1_id,
            custodian_2_id=payload.custodian_2_id,
            vault_rack_id=payload.vault_rack_id,
            item_count=payload.item_count,
            net_weight_mg=payload.net_weight_mg
        )
        return packet
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))

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
