import pytest
import hmac
import hashlib
import uuid
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.database.session import Base, engine
from backend.app.gold_loan.integrations.base import IntegrationMode
from backend.app.gold_loan.integrations.registry import adapter_registry

client = TestClient(app)


@pytest.fixture(autouse=True)
def authenticated_default_client(isolated_test_state):
    from backend.app.core.security import create_access_token
    from backend.app.database.session import SessionLocal
    from backend.app.models.entities import Membership, User

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "jordan.davies@northstar.bank").first()
        membership = db.query(Membership).filter(Membership.user_id == user.id).first()
        token = create_access_token({"sub": user.id, "tenant_id": membership.tenant_id})
    finally:
        db.close()
    client.headers.update({"Authorization": f"Bearer {token}"})


def test_gold_loan_and_integration_routes_require_authentication():
    assert client.get("/api/v1/integrations/", headers={"Authorization": ""}).status_code == 401
    response = client.post(
        "/api/v1/gold-loan/kyc/verify-pan",
        json={"pan": "ABCDE1234F", "customer_name": "Test User"},
        headers={"Authorization": ""},
    )
    assert response.status_code == 401


def test_registry_contains_all_10_adapters():
    statuses = adapter_registry.get_all_statuses()
    assert len(statuses) == 10
    names = [s["name"] for s in statuses]
    assert "Payment Gateway (Repayments)" in names
    assert "Bank Payout (Disbursals)" in names
    assert "Identity & KYC (Aadhaar / PAN / CKYC)" in names
    assert "Credit Bureau (CIBIL / Experian)" in names
    assert "AML / Sanctions / PEP Screening" in names
    assert "Gold Rate Feed (Live)" in names
    assert "Gold Assay Device Gateway" in names
    assert "E-Sign & E-Stamp (NeSL / Aadhaar)" in names
    assert "Borrower Notifications (SMS / WhatsApp)" in names
    assert "E-Auction & Recovery Gateway" in names

def test_production_mode_safety_guard():
    """
    CRITICAL SAFETY REQUIREMENT:
    A user cannot simply toggle an adapter to PRODUCTION without server-side
    ALLOW_PRODUCTION_INTEGRATIONS=true and required credentials in environment.
    """
    with pytest.raises(PermissionError) as exc_info:
        adapter_registry.set_mode("Payment Gateway (Repayments)", IntegrationMode.PRODUCTION)
    assert "blocked by deployment safety policy" in str(exc_info.value)

def test_payment_gateway_repayment_flow_and_provider_verification(monkeypatch):
    pg = adapter_registry.payment_gateway
    pg.clear_simulation()
    pg.set_mode(IntegrationMode.SANDBOX)
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "unit-test-secret")
    requests = []

    def fake_request(method, path, payload=None):
        requests.append((method, path, payload))
        if method == "POST":
            return {
                "id": "order_test_unit",
                "amount": 5000000,
                "currency": "INR",
                "receipt": "idemp_repay_key_001",
            }
        return {
            "id": "pay_test_unit",
            "order_id": "order_test_unit",
            "amount": 5000000,
            "currency": "INR",
            "status": "captured",
        }

    monkeypatch.setattr(pg, "_request", fake_request)
    order = pg.create_payment_order(
        loan_id="LOAN-2026-001",
        amount_paise=5000000,
        idempotency_key="idemp_repay_key_001"
    )
    assert order["order_id"] == "order_test_unit"
    assert order["status"] == "ORDER_CREATED"
    assert order["amount_paise"] == 5000000
    assert order["is_test_mode"] is True
    assert order["is_simulated"] is False
    assert order["provider_confirmed"] is False
    assert requests == [(
        "POST",
        "/orders",
        {
            "amount": 5000000,
            "currency": "INR",
            "receipt": "idemp_repay_key_001",
            "notes": {"loan_id": "LOAN-2026-001"},
        },
    )]

    payment_id = "pay_test_unit"
    signature = hmac.new(
        b"unit-test-secret",
        f"order_test_unit|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    verified = pg.verify_checkout_payment(
        order_id="order_test_unit",
        payment_id=payment_id,
        signature=signature,
        expected_amount_paise=5000000,
    )
    assert verified["status"] == "CAPTURED"
    assert verified["provider_confirmed"] is True
    assert verified["ledger_updated"] is False
    assert requests[-1] == ("GET", "/payments/pay_test_unit", None)


def test_payment_gateway_rejects_invalid_signature_and_order_mismatch(monkeypatch):
    pg = adapter_registry.payment_gateway
    pg.clear_simulation()
    pg.set_mode(IntegrationMode.SANDBOX)
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "unit-test-secret")
    monkeypatch.setattr(pg, "_request", lambda method, path, payload=None: {
        "id": "pay_test_unit",
        "order_id": "order_test_unit",
        "amount": 1000000,
        "currency": "INR",
        "status": "captured",
    })

    with pytest.raises(ValueError, match="signature is invalid"):
        pg.verify_checkout_payment("order_test_unit", "pay_test_unit", "bad-signature", 1000000)

    signature = hmac.new(
        b"unit-test-secret",
        b"order_test_unit|pay_test_unit",
        hashlib.sha256,
    ).hexdigest()
    with pytest.raises(ValueError, match="does not match"):
        pg.verify_checkout_payment("order_test_unit", "pay_test_unit", signature, 2000000)

def test_repayment_orders_are_persisted_and_tenant_scoped(monkeypatch):
    Base.metadata.create_all(bind=engine)
    pg = adapter_registry.payment_gateway
    pg.clear_simulation()
    pg.set_mode(IntegrationMode.SANDBOX)
    monkeypatch.setattr(settings, "RAZORPAY_KEY_ID", "rzp_test_unit")
    monkeypatch.setattr(settings, "RAZORPAY_KEY_SECRET", "unit-test-secret")
    provider_calls = []

    def create_provider_order(loan_id, amount_paise, idempotency_key):
        provider_calls.append(idempotency_key)
        return {
            "order_id": f"order_test_{idempotency_key}",
            "loan_id": loan_id,
            "amount_paise": amount_paise,
            "currency": "INR",
            "status": "ORDER_CREATED",
            "is_test_mode": True,
            "is_simulated": False,
            "provider_confirmed": False,
            "message": "test order",
        }

    monkeypatch.setattr(pg, "create_payment_order", create_provider_order)
    email_a = f"payments_a_{uuid.uuid4().hex[:8]}@example.com"
    response_a = client.post("/api/v1/auth/register", json={
        "email": email_a,
        "password": "Password123!",
        "full_name": "Payments A",
        "organization_name": f"Payment Tenant A {uuid.uuid4().hex[:6]}",
    })
    assert response_a.status_code == 200
    headers_a = {"Authorization": f"Bearer {response_a.json()['access_token']}"}
    idempotency_key = uuid.uuid4().hex
    order_payload = {
        "loan_id": "LOAN-TEST-001",
        "amount_paise": 250000,
        "idempotency_key": idempotency_key,
    }

    created = client.post("/api/v1/gold-loan/repayments/create-order", headers=headers_a, json=order_payload)
    replay = client.post("/api/v1/gold-loan/repayments/create-order", headers=headers_a, json=order_payload)
    assert created.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["order_id"] == created.json()["order_id"]
    assert provider_calls == [idempotency_key]

    order_list = client.get("/api/v1/gold-loan/repayments/orders", headers=headers_a)
    assert order_list.status_code == 200
    assert order_list.json()["orders"][0]["order_id"] == created.json()["order_id"]

    monkeypatch.setattr(pg, "verify_checkout_payment", lambda **kwargs: {
        "order_id": kwargs["order_id"],
        "payment_id": kwargs["payment_id"],
        "amount_paise": 250000,
        "currency": "INR",
        "status": "CAPTURED",
        "is_test_mode": True,
        "is_simulated": False,
        "provider_confirmed": True,
        "ledger_updated": False,
        "message": "Test capture verified.",
    })
    verified = client.post(
        "/api/v1/gold-loan/repayments/verify-payment",
        headers=headers_a,
        json={
            "order_id": created.json()["order_id"],
            "payment_id": "pay_test_api",
            "signature": "verified-by-mocked-provider",
        },
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "CAPTURED"
    persisted_capture = client.get("/api/v1/gold-loan/repayments/orders", headers=headers_a)
    assert persisted_capture.json()["orders"][0]["payment_id"] == "pay_test_api"
    assert persisted_capture.json()["orders"][0]["status"] == "CAPTURED"

    email_b = f"payments_b_{uuid.uuid4().hex[:8]}@example.com"
    response_b = client.post("/api/v1/auth/register", json={
        "email": email_b,
        "password": "Password123!",
        "full_name": "Payments B",
        "organization_name": f"Payment Tenant B {uuid.uuid4().hex[:6]}",
    })
    headers_b = {"Authorization": f"Bearer {response_b.json()['access_token']}"}
    other_tenant_orders = client.get("/api/v1/gold-loan/repayments/orders", headers=headers_b)
    assert other_tenant_orders.status_code == 200
    assert other_tenant_orders.json()["orders"] == []

def test_disbursal_adapter_maker_checker_and_idempotency():
    disbursal = adapter_registry.disbursal
    disbursal.clear_simulation()

    # Maker and checker cannot be identical
    with pytest.raises(PermissionError) as exc:
        disbursal.execute_disbursal(
            loan_id="L-DISB-01",
            amount_paise=10000000,
            beneficiary_account="123456789012",
            beneficiary_ifsc="HDFC0001234",
            beneficiary_name="Rajesh Sharma",
            maker_id="user_admin_01",
            checker_id="user_admin_01", # VIOLATION: Same user
            idempotency_key="idemp_disb_01"
        )
    assert "Maker and checker cannot be the same user" in str(exc.value)

    # Valid maker-checker disbursal
    payout = disbursal.execute_disbursal(
        loan_id="L-DISB-01",
        amount_paise=10000000,
        beneficiary_account="123456789012",
        beneficiary_ifsc="HDFC0001234",
        beneficiary_name="Rajesh Sharma",
        maker_id="user_maker_01",
        checker_id="user_checker_02",
        idempotency_key="idemp_disb_01"
    )
    assert payout["status"] == "SIMULATED"
    assert "utr_number" not in payout
    assert payout["provider_confirmed"] is False
    assert payout["message"] == "SIMULATED — NO MONEY TRANSFERRED"
    assert payout["beneficiary_account"] == "XXXX9012" # Masked account

    # Duplicate disbursal prevention with same idempotency key
    replay = disbursal.execute_disbursal(
        loan_id="L-DISB-01",
        amount_paise=10000000,
        beneficiary_account="123456789012",
        beneficiary_ifsc="HDFC0001234",
        beneficiary_name="Rajesh Sharma",
        maker_id="user_maker_01",
        checker_id="user_checker_02",
        idempotency_key="idemp_disb_01"
    )
    assert replay["idempotent_replay"] is True
    assert replay["payout_id"] == payout["payout_id"]


def test_providerless_financial_flows_reject_production_mode(monkeypatch):
    from backend.app.gold_loan.integrations.identity_adapter import IdentityAdapter
    from backend.app.gold_loan.integrations.disbursal_adapter import DisbursalAdapter
    from backend.app.gold_loan.integrations.payment_gateway_adapter import PaymentGatewayAdapter
    from backend.app.gold_loan.integrations.device_gateway_adapter import DeviceGatewayAdapter
    from backend.app.gold_loan.integrations.gold_rate_adapter import GoldRateAdapter
    from backend.app.gold_loan.integrations.credit_bureau_adapter import CreditBureauAdapter
    from backend.app.gold_loan.integrations.screening_adapter import ScreeningAdapter
    from backend.app.gold_loan.integrations.document_signer_adapter import DocumentSignerAdapter
    from backend.app.gold_loan.integrations.notification_adapter import NotificationAdapter
    from backend.app.gold_loan.integrations.auction_adapter import AuctionAdapter

    monkeypatch.setenv("ALLOW_PRODUCTION_INTEGRATIONS", "true")
    required_keys = [
        "UIDAI_AUTH_KEY", "NSDL_PAN_CLIENT_ID", "CKYC_PORTAL_TOKEN",
        "BANK_PAYOUT_CLIENT_ID", "BANK_PAYOUT_SECRET", "BANK_CORPORATE_ACCOUNT",
        "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
        "DEVICE_GATEWAY_CERT_PATH", "DEVICE_GATEWAY_SECRET", "IBJA_FEED_API_KEY",
        "GOLD_FEED_URL", "CIBIL_MEMBER_ID", "CIBIL_PASSWORD", "BUREAU_API_ENDPOINT",
        "AML_PROVIDER_API_KEY", "SANCTIONS_DATABASE_URL", "NESL_CLIENT_ID",
        "ESIGN_ASP_ID", "ESIGN_AUTH_TOKEN", "SMS_GATEWAY_AUTH",
        "WHATSAPP_BUSINESS_TOKEN", "EAUCTION_PORTAL_KEY", "AUCTION_SETTLEMENT_ESCROW",
    ]
    for key in required_keys:
        monkeypatch.setenv(key, "configured-for-guard-test")

    identity = IdentityAdapter()
    identity.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="no provider adapter is configured"):
        identity.verify_pan("ABCDE1234F", "Test User")

    disbursal = DisbursalAdapter()
    disbursal.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="no bank payout provider is configured"):
        disbursal.execute_disbursal(
            "L-1", 10000, "1234", "HDFC0001234", "Test User", "maker", "checker", "idemp-1"
        )

    payment = PaymentGatewayAdapter()
    payment.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="restricted to SANDBOX"):
        payment.create_payment_order("L-1", 10000, "idemp-1")

    device = DeviceGatewayAdapter()
    device.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="authenticated instrument gateway"):
        device.generate_signed_reading("DEV-XRF-001", 30000, 9160)

    rates = GoldRateAdapter()
    rates.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="no market-data provider"):
        rates.get_gold_rate()
    with pytest.raises(RuntimeError, match="no market-data provider"):
        rates.get_all_rates()

    bureau = CreditBureauAdapter()
    bureau.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="no provider adapter"):
        bureau.fetch_credit_report("ABCDE1234F", "Test User", 1.0)

    screening = ScreeningAdapter()
    screening.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="no provider adapter"):
        screening.screen_individual("Test User", "ABCDE1234F")

    signer = DocumentSignerAdapter()
    signer.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="no signing provider"):
        signer.generate_and_sign_kfs("L-1", "Test User", 10000, 10.0, 12)

    notification = NotificationAdapter()
    notification.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="no messaging provider"):
        notification.send_notification("0000000000", "SMS", "test", {})

    auction = AuctionAdapter()
    auction.set_mode(IntegrationMode.PRODUCTION)
    with pytest.raises(RuntimeError, match="no auction provider"):
        auction.settle_auction("L-1", 10000, 1000, 10)


def test_sandbox_connection_check_does_not_claim_provider_connectivity():
    result = adapter_registry.identity.test_connection()
    assert result["status"] == "SIMULATED"
    assert result["success"] is False
    assert result["is_simulated"] is True


def test_device_gateway_reading_signature_and_replay_protection():
    gateway = adapter_registry.device_gateway
    gateway.clear_simulation()

    # Generate valid signed reading from registered device DEV-XRF-001
    reading = gateway.generate_signed_reading(
        device_id="DEV-XRF-001",
        gross_weight_mg=45000, # 45 grams
        purity_bps=9160        # 22 Karat (91.6%)
    )
    assert reading["signature"] is not None
    assert reading["is_simulated"] is True

    # Verify reading at backend boundary
    verified = gateway.verify_reading(reading)
    assert verified["verified"] is True
    assert verified["purity_karat"] == 22.0
    assert verified["gross_weight_mg"] == 45000
    assert verified["is_simulated"] is True
    assert verified["provider_authenticated"] is False

    # Replay attack attempt: Using same reading / nonce a second time must FAIL
    with pytest.raises(ValueError) as exc:
        gateway.verify_reading(reading)
    assert "Replay detected" in str(exc.value)

    # Tampered gross weight attempt: Changing payload without valid HMAC key must FAIL
    tampered_reading = gateway.generate_signed_reading("DEV-XRF-001", 30000, 9160)
    tampered_reading["gross_weight_mg"] = 99999 # Fraudulent weight injection
    with pytest.raises(ValueError) as exc:
        gateway.verify_reading(tampered_reading)
    assert "tampered with" in str(exc.value)

    stale_reading = gateway.generate_signed_reading("DEV-XRF-001", 30000, 9160)
    stale_reading["timestamp"] -= 301
    with pytest.raises(ValueError, match="timestamp"):
        gateway.verify_reading(stale_reading)
