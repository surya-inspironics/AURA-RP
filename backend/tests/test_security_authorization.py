from datetime import timedelta
import io
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token, hash_password
from backend.app.database.session import SessionLocal
from backend.app.main import app
from backend.app.models.entities import Case, Membership, PaymentOrder, Tenant, User


client = TestClient(app)
PASSWORD = "BatchTwoSecure2026!"


def create_member(email: str, role: str = "member", active: bool = True):
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "northstar-bank").one()
        user = User(
            email=email,
            hashed_password=hash_password(PASSWORD),
            full_name=f"Test {role.title()}",
            avatar_initials="TT",
            is_active=active,
        )
        db.add(user)
        db.flush()
        membership = Membership(tenant_id=tenant.id, user_id=user.id, role=role)
        db.add(membership)
        db.commit()
        return user.id, tenant.id, membership.id
    finally:
        db.close()


def login(email: str, password: str = PASSWORD) -> tuple[dict, dict]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response, {"Authorization": f"Bearer {response.json()['access_token']}"} if response.status_code == 200 else {}


def register_tenant(email: str) -> tuple[str, str]:
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": PASSWORD,
        "full_name": "Second Tenant Owner",
        "organization_name": f"Tenant {uuid.uuid4().hex[:8]}",
    })
    assert response.status_code == 200
    return response.json()["access_token"], response.json()["tenant"]["id"]


def test_protected_routes_reject_missing_invalid_and_expired_tokens():
    protected_paths = ["/api/v1/auth/me", "/api/v1/cases/", "/api/v1/billing/summary"]
    for path in protected_paths:
        assert client.get(path, headers={}).status_code == 401
    assert client.post("/api/v1/cases/", json={
        "customer_name": "Unauthenticated Applicant",
        "requested_amount": 10000,
        "tenure_months": 3,
        "product_type": "Gold Loan",
    }).status_code == 401
    assert client.post("/api/v1/gold-loan/applications", json={
        "case_id": "unauthenticated-case",
    }).status_code == 401

    invalid = client.get("/api/v1/cases/", headers={"Authorization": "Bearer invalid"})
    assert invalid.status_code == 401

    token_without_tenant = create_access_token({"sub": "unbound-user"})
    missing_tenant = client.get(
        "/api/v1/cases/",
        headers={"Authorization": f"Bearer {token_without_tenant}"},
    )
    assert missing_tenant.status_code == 401

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "jordan.davies@northstar.bank").one()
        membership = db.query(Membership).filter(Membership.user_id == user.id).one()
        expired_token = create_access_token(
            {"sub": user.id, "tenant_id": membership.tenant_id},
            expires_delta=timedelta(seconds=-1),
        )
    finally:
        db.close()
    expired = client.get("/api/v1/cases/", headers={"Authorization": f"Bearer {expired_token}"})
    assert expired.status_code == 401


def test_login_token_resolves_persisted_user_and_role_and_ignores_role_claim():
    email = f"member_{uuid.uuid4().hex[:8]}@example.com"
    user_id, tenant_id, _ = create_member(email, "member")
    login_response, member_headers = login(email)
    assert login_response.status_code == 200
    profile = client.get("/api/v1/auth/me", headers=member_headers)
    assert profile.status_code == 200
    assert profile.json()["user"]["id"] == user_id
    assert profile.json()["user"]["role"] == "member"
    assert profile.json()["tenant"]["id"] == tenant_id

    elevated_claim_token = create_access_token({
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": "owner",
    })
    elevated_headers = {"Authorization": f"Bearer {elevated_claim_token}"}
    elevated_profile = client.get("/api/v1/auth/me", headers=elevated_headers)
    assert elevated_profile.status_code == 200
    assert elevated_profile.json()["user"]["role"] == "member"
    assert client.get("/api/v1/billing/summary", headers=elevated_headers).status_code == 403


def test_login_and_requests_require_active_membership():
    email = f"orphan_{uuid.uuid4().hex[:8]}@example.com"
    db = SessionLocal()
    try:
        db.add(User(
            email=email,
            hashed_password=hash_password(PASSWORD),
            full_name="Orphan User",
            is_active=True,
        ))
        db.commit()
    finally:
        db.close()
    assert login(email)[0].status_code == 403

    inactive_email = f"inactive_{uuid.uuid4().hex[:8]}@example.com"
    user_id, _, membership_id = create_member(inactive_email)
    login_response, headers = login(inactive_email)
    assert login_response.status_code == 200
    db = SessionLocal()
    try:
        db.query(Membership).filter(Membership.id == membership_id).delete()
        db.commit()
    finally:
        db.close()
    assert client.get("/api/v1/cases/", headers=headers).status_code == 403

    second_email = f"disabled_{uuid.uuid4().hex[:8]}@example.com"
    disabled_user_id, _, _ = create_member(second_email)
    disabled_login, disabled_headers = login(second_email)
    assert disabled_login.status_code == 200
    db = SessionLocal()
    try:
        db.query(User).filter(User.id == disabled_user_id).update({"is_active": False})
        db.commit()
    finally:
        db.close()
    assert client.get("/api/v1/cases/", headers=disabled_headers).status_code == 401


def test_tenant_claim_and_x_tenant_header_cannot_switch_workspaces():
    _, foreign_tenant_id = register_tenant(f"foreign_{uuid.uuid4().hex[:8]}@example.com")
    login_response, owner_headers = login("jordan.davies@northstar.bank", "AuraSecure2026!")
    assert login_response.status_code == 200

    forged_claim = create_access_token({
        "sub": login_response.json()["user"]["id"],
        "tenant_id": foreign_tenant_id,
        "role": "owner",
    })
    assert client.get(
        "/api/v1/cases/",
        headers={"Authorization": f"Bearer {forged_claim}"},
    ).status_code == 403

    assert client.get(
        "/api/v1/cases/",
        headers={**owner_headers, "X-Tenant-ID": foreign_tenant_id},
    ).status_code == 403


def test_case_and_evidence_ids_are_tenant_scoped():
    foreign_email = f"foreign_owner_{uuid.uuid4().hex[:8]}@example.com"
    foreign_token, foreign_tenant_id = register_tenant(foreign_email)
    foreign_headers = {"Authorization": f"Bearer {foreign_token}"}

    created_case = client.post("/api/v1/cases/", headers=foreign_headers, json={
        "customer_name": "Tenant Scoped Evidence",
        "requested_amount": 25000,
        "tenure_months": 12,
    })
    assert created_case.status_code == 201
    case_id = created_case.json()["id"]
    uploaded = client.post(
        "/api/v1/evidence/upload",
        headers=foreign_headers,
        data={"case_id": case_id},
        files={"file": ("proof.pdf", io.BytesIO(b"%PDF-test"), "application/pdf")},
    )
    assert uploaded.status_code == 201
    evidence_id = uploaded.json()["id"]

    local_owner_response, local_owner_headers = login("jordan.davies@northstar.bank", "AuraSecure2026!")
    assert local_owner_response.status_code == 200
    assert client.get(f"/api/v1/cases/{case_id}", headers=local_owner_headers).status_code == 404
    assert client.get(
        f"/api/v1/evidence/{evidence_id}/download",
        headers=local_owner_headers,
    ).status_code == 404

    db = SessionLocal()
    try:
        assert db.query(Case).filter(Case.id == case_id, Case.tenant_id == foreign_tenant_id).one()
    finally:
        db.close()


def test_member_cannot_elevate_role_or_change_privileged_workspace_data():
    email = f"member_{uuid.uuid4().hex[:8]}@example.com"
    create_member(email, "member")
    member_login, member_headers = login(email)
    assert member_login.status_code == 200

    invite = client.post("/api/v1/team/invite", headers=member_headers, json={
        "email": "new-admin@example.com",
        "full_name": "Injected Admin",
        "role": "admin",
    })
    assert invite.status_code == 403
    assert client.put("/api/v1/system/settings", headers=member_headers, json={
        "organization_name": "Changed Tenant",
    }).status_code == 403
    assert client.get("/api/v1/billing/summary", headers=member_headers).status_code == 403

    owner_response, owner_headers = login("jordan.davies@northstar.bank", "AuraSecure2026!")
    assert owner_response.status_code == 200
    invalid_owner_invite = client.post("/api/v1/team/invite", headers=owner_headers, json={
        "email": "owner-transfer@example.com",
        "full_name": "Attempted Owner",
        "role": "owner",
    })
    assert invalid_owner_invite.status_code == 422


def test_owner_operations_and_member_read_access_remain_compatible():
    owner_response, owner_headers = login("jordan.davies@northstar.bank", "AuraSecure2026!")
    assert owner_response.status_code == 200
    assert client.post(
        "/api/v1/integrations/gold_rate/mode",
        headers=owner_headers,
        json={"mode": "PRODUCTION"},
    ).status_code == 403
    assert client.post(
        "/api/v1/integrations/gold_rate/simulate-failure",
        headers=owner_headers,
        json={"scenario": "upstream_500"},
    ).status_code == 403
    created = client.post("/api/v1/cases/", headers=owner_headers, json={
        "customer_name": "Authorized Owner Case",
        "requested_amount": 12000,
        "tenure_months": 12,
    })
    assert created.status_code == 201

    email = f"reader_{uuid.uuid4().hex[:8]}@example.com"
    create_member(email, "member")
    member_response, member_headers = login(email)
    assert member_response.status_code == 200
    assert client.get("/api/v1/cases/", headers=member_headers).status_code == 200
    assert client.get(f"/api/v1/cases/{created.json()['id']}", headers=member_headers).status_code == 200
    assert client.post("/api/v1/cases/", headers=member_headers, json={
        "customer_name": "Unauthorized Member Case",
        "requested_amount": 1000,
        "tenure_months": 1,
    }).status_code == 403

    admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    create_member(admin_email, "admin")
    admin_login, admin_headers = login(admin_email)
    assert admin_login.status_code == 200
    assert client.get("/api/v1/billing/summary", headers=admin_headers).status_code == 200
    assert client.put("/api/v1/system/settings", headers=admin_headers, json={
        "organization_name": "Authorized Admin Workspace",
    }).status_code == 200


def test_authenticated_owner_can_create_gold_loan_case_and_application():
    owner_login, owner_headers = login("jordan.davies@northstar.bank", "AuraSecure2026!")
    assert owner_login.status_code == 200

    case_response = client.post("/api/v1/cases/", headers=owner_headers, json={
        "customer_name": "Authenticated Gold Loan Applicant",
        "requested_amount": 50000,
        "tenure_months": 6,
        "product_type": "Gold Loan",
    })
    assert case_response.status_code == 201
    case = case_response.json()

    application_response = client.post("/api/v1/gold-loan/applications", headers=owner_headers, json={
        "case_id": case["id"],
        "initial_collateral": {
            "item_type": "Gold bangle",
            "gross_weight_mg": 25000,
            "stone_deduction_mg": 500,
            "purity_bps": 9160,
        },
    })
    assert application_response.status_code == 201
    application = application_response.json()
    assert application["case_id"] == case["id"]
    assert application["customer_name"] == "Authenticated Gold Loan Applicant"
    assert application["collateral_items"][0]["gross_weight_mg"] == 25000


def test_payment_and_billing_data_cannot_be_read_through_another_tenant_context():
    owner_response, owner_headers = login("jordan.davies@northstar.bank", "AuraSecure2026!")
    assert owner_response.status_code == 200
    tenant_id = owner_response.json()["tenant"]["id"]
    db = SessionLocal()
    try:
        db.add(PaymentOrder(
            tenant_id=tenant_id,
            loan_id="PRIVATE-LOAN-1",
            idempotency_key=uuid.uuid4().hex,
            provider_order_id=f"order_{uuid.uuid4().hex}",
            amount_paise=12345,
            status="CREATION_PENDING",
        ))
        db.commit()
    finally:
        db.close()

    _, foreign_tenant_id = register_tenant(f"payment_foreign_{uuid.uuid4().hex[:8]}@example.com")
    assert client.get(
        "/api/v1/billing/summary",
        headers={**owner_headers, "X-Tenant-ID": foreign_tenant_id},
    ).status_code == 403
    assert client.get(
        "/api/v1/gold-loan/repayments/orders",
        headers={**owner_headers, "X-Tenant-ID": foreign_tenant_id},
    ).status_code == 403
    foreign_token, _ = register_tenant(f"payment_reader_{uuid.uuid4().hex[:8]}@example.com")
    foreign_orders = client.get(
        "/api/v1/gold-loan/repayments/orders",
        headers={"Authorization": f"Bearer {foreign_token}"},
    )
    assert foreign_orders.status_code == 200
    assert all(order["loan_id"] != "PRIVATE-LOAN-1" for order in foreign_orders.json()["orders"])


def test_decisions_use_authenticated_approver_and_enforce_maker_checker():
    maker_email = f"maker_{uuid.uuid4().hex[:8]}@example.com"
    maker_id, _, _ = create_member(maker_email, "analyst")
    maker_login, maker_headers = login(maker_email)
    assert maker_login.status_code == 200
    case_response = client.post("/api/v1/cases/", headers=maker_headers, json={
        "customer_name": "Maker Checker Case",
        "requested_amount": 75000,
        "tenure_months": 12,
    })
    assert case_response.status_code == 201
    case_id = case_response.json()["id"]

    approver_login, approver_headers = login("alicia.rossi@northstar.bank", "AuraSecure2026!")
    assert approver_login.status_code == 200
    approver_id = approver_login.json()["user"]["id"]
    impersonation = client.post("/api/v1/decisions/", headers=maker_headers, json={
        "case_id": case_id,
        "outcome": "APPROVED",
        "eligible_amount": 75000,
        "interest_rate": 7.5,
        "rationale": "Attempted approver impersonation",
        "actor_id": approver_id,
        "actor_name": "Alicia Rossi",
    })
    assert impersonation.status_code == 403

    approved = client.post("/api/v1/decisions/", headers=approver_headers, json={
        "case_id": case_id,
        "outcome": "APPROVED",
        "eligible_amount": 75000,
        "interest_rate": 7.5,
        "rationale": "Approved by authenticated separate approver",
        "actor_id": maker_id,
    })
    assert approved.status_code == 201
    db = SessionLocal()
    try:
        from backend.app.models.entities import Decision

        decision = db.query(Decision).filter(Decision.case_id == case_id).one()
        assert decision.actor_id == approver_id
    finally:
        db.close()


def test_request_supplied_checker_and_custodian_ids_cannot_authorize_simulated_actions():
    owner_response, owner_headers = login("jordan.davies@northstar.bank", "AuraSecure2026!")
    assert owner_response.status_code == 200
    user_id = owner_response.json()["user"]["id"]
    other_id = login("alicia.rossi@northstar.bank", "AuraSecure2026!")[0].json()["user"]["id"]

    disbursal = client.post("/api/v1/gold-loan/disbursals/execute", headers=owner_headers, json={
        "loan_id": "UNSCOPED-LOAN",
        "amount_paise": 10000,
        "beneficiary_account": "123456789012",
        "beneficiary_ifsc": "HDFC0001234",
        "beneficiary_name": "Test User",
        "maker_id": user_id,
        "checker_id": other_id,
        "idempotency_key": uuid.uuid4().hex,
    })
    assert disbursal.status_code == 409

    spoofed_maker = client.post("/api/v1/gold-loan/disbursals/execute", headers=owner_headers, json={
        "loan_id": "UNSCOPED-LOAN",
        "amount_paise": 10000,
        "beneficiary_account": "123456789012",
        "beneficiary_ifsc": "HDFC0001234",
        "beneficiary_name": "Test User",
        "maker_id": other_id,
        "checker_id": user_id,
        "idempotency_key": uuid.uuid4().hex,
    })
    assert spoofed_maker.status_code == 403

    vault = client.post("/api/v1/gold-loan/vault/seal", headers=owner_headers, json={
        "loan_id": "UNSCOPED-LOAN",
        "custodian_1_id": user_id,
        "custodian_2_id": other_id,
        "vault_rack_id": "RACK-01",
        "item_count": 1,
        "net_weight_mg": 1000,
    })
    assert vault.status_code == 409
