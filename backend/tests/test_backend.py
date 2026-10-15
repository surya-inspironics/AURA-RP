import pytest
import os
import io
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database.session import Base, engine, SessionLocal
from backend.app.database.seed import seed_initial_data
from backend.app.models.entities import Tenant, User, Membership, Case, EvidenceItem
from backend.app.services.audit_service import AuditService

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_initial_data(db)
    db.close()
    yield

def test_system_health():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["operational", "healthy"]
    assert "database" in data

def test_auth_me_default():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert "tenant" in data
    assert data["tenant"]["name"] == "Northstar Bank"

def test_auth_register_and_login():
    email = f"test.analyst_{os.urandom(4).hex()}@example.com"
    register_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Test Analyst",
        "organization_name": "Acme Holdings"
    }
    reg_res = client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 200
    token_data = reg_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Test login
    login_payload = {"email": email, "password": "Password123!"}
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

def test_cross_tenant_isolation():
    """
    CRITICAL ENTERPRISE TEST:
    A user from Tenant B must NEVER read or modify cases belonging to Tenant A.
    """
    # 1. Register Tenant A
    user_a_email = f"user_a_{os.urandom(4).hex()}@example.com"
    res_a = client.post("/api/v1/auth/register", json={
        "email": user_a_email,
        "password": "Password123!",
        "full_name": "User Bank A",
        "organization_name": "Bank Alpha"
    })
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Tenant B
    user_b_email = f"user_b_{os.urandom(4).hex()}@example.com"
    res_b = client.post("/api/v1/auth/register", json={
        "email": user_b_email,
        "password": "Password123!",
        "full_name": "User Bank B",
        "organization_name": "Bank Beta"
    })
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Create confidential case in Tenant A
    create_res = client.post("/api/v1/cases/", headers=headers_a, json={
        "customer_name": "Confidential Alpha Corp",
        "requested_amount": 500000.0,
        "tenure_months": 24,
        "purpose": "Secret M&A transaction"
    })
    assert create_res.status_code == 201
    case_a_id = create_res.json()["id"]

    # 4. Attempt to access Tenant A's case using Tenant B's credentials -> MUST BE 404 (isolated)
    leak_res = client.get(f"/api/v1/cases/{case_a_id}", headers=headers_b)
    assert leak_res.status_code == 404, "SECURITY VIOLATION: Tenant B accessed Tenant A case!"

    # 5. Verify case list for Tenant B does NOT include Tenant A's case
    list_b = client.get("/api/v1/cases/", headers=headers_b)
    assert list_b.status_code == 200
    case_ids_b = [c["id"] for c in list_b.json()]
    assert case_a_id not in case_ids_b, "SECURITY VIOLATION: Tenant A case leaked in Tenant B case list!"

def test_case_lifecycle_state_machine():
    case_res = client.post("/api/v1/cases/", json={
        "customer_name": "State Machine Corp",
        "requested_amount": 150000.0,
        "tenure_months": 12,
        "purpose": "Inventory expansion"
    })
    assert case_res.status_code == 201
    case_id = case_res.json()["id"]
    assert case_res.json()["status"] == "IN_VALIDATION"

    # Valid transition: IN_VALIDATION -> READY_FOR_REVIEW
    t1 = client.post(f"/api/v1/cases/{case_id}/transition?target_status=READY_FOR_REVIEW")
    assert t1.status_code == 200
    assert t1.json()["new_status"] == "READY_FOR_REVIEW"

    # Invalid transition: READY_FOR_REVIEW directly to DRAFT (forbidden by state machine)
    t2 = client.post(f"/api/v1/cases/{case_id}/transition?target_status=DRAFT")
    assert t2.status_code == 400

def test_evidence_upload_and_checksum():
    case_res = client.post("/api/v1/cases/", json={
        "customer_name": "Evidence Testing Ltd",
        "requested_amount": 75000.0,
        "tenure_months": 12
    })
    case_id = case_res.json()["id"]

    fake_file_bytes = b"%PDF-1.4 Mock PDF Content for AURA Evidence Testing"
    upload_res = client.post(
        "/api/v1/evidence/upload",
        data={"case_id": case_id},
        files={"file": ("balance_sheet_2026.pdf", io.BytesIO(fake_file_bytes), "application/pdf")}
    )
    assert upload_res.status_code == 201
    ev_data = upload_res.json()
    assert ev_data["file_name"] == "balance_sheet_2026.pdf"
    assert len(ev_data["sha256_checksum"]) == 64
    assert ev_data["validation_status"] == "VALIDATED"

def test_validation_engine_execution():
    case_res = client.post("/api/v1/cases/", json={
        "customer_name": "Apex Industrial",
        "requested_amount": 350000.0,
        "tenure_months": 18
    })
    case_id = case_res.json()["id"]

    val_res = client.post("/api/v1/validation/run", json={"case_id": case_id, "rule_version": "v1.0"})
    assert val_res.status_code == 200
    result = val_res.json()
    assert "findings" in result
    assert result["passed_rules"] >= 3
    rule_ids = [f["rule_id"] for f in result["findings"]]
    assert "R-FIN-01" in rule_ids
    assert "R-TEN-02" in rule_ids

def test_maker_checker_decision():
    case_res = client.post("/api/v1/cases/", json={
        "customer_name": "Decisions Corp",
        "requested_amount": 200000.0,
        "tenure_months": 12
    })
    case_id = case_res.json()["id"]

    dec_res = client.post("/api/v1/decisions/", json={
        "case_id": case_id,
        "outcome": "APPROVED",
        "eligible_amount": 200000.0,
        "interest_rate": 7.8,
        "rationale": "High quality assets with verified financial reports."
    })
    assert dec_res.status_code == 201
    assert dec_res.json()["outcome"] == "APPROVED"

    # Verify case status updated to APPROVED
    detail_res = client.get(f"/api/v1/cases/{case_id}")
    assert detail_res.json()["case"]["status"] == "APPROVED"

def test_tamper_evident_audit_log_integrity():
    verify_res = client.get("/api/v1/audit/verify")
    assert verify_res.status_code == 200
    report = verify_res.json()
    assert report["is_valid"] is True
    assert report["tampered_count"] == 0
    assert report["total_events"] > 0

def test_analytics_dashboard_metrics():
    dash_res = client.get("/api/v1/analytics/dashboard")
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert "kpis" in dash
    assert "workflow" in dash
    assert "trends" in dash
    assert "funnel" in dash
    assert dash["kpis"]["open_cases"] >= 1
    assert dash["kpis"]["sla_compliance_rate"] > 0
