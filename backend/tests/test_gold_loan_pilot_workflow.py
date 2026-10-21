import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)
OWNER_EMAIL = "jordan.davies@northstar.bank"
APPROVER_EMAIL = "alicia.rossi@northstar.bank"
PASSWORD = "AuraSecure2026!"


def _login(email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_application(headers: dict[str, str]) -> str:
    case = client.post(
        "/api/v1/cases/",
        headers=headers,
        json={
            "customer_name": f"Pilot Applicant {uuid.uuid4().hex[:8]}",
            "requested_amount": 50000,
            "tenure_months": 6,
            "product_type": "Gold Loan",
        },
    )
    assert case.status_code == 201
    application = client.post(
        "/api/v1/gold-loan/applications",
        headers=headers,
        json={
            "case_id": case.json()["id"],
            "initial_collateral": {
                "item_type": "Gold bangle",
                "gross_weight_mg": 25000,
                "stone_deduction_mg": 500,
                "purity_bps": 9160,
            },
        },
    )
    assert application.status_code == 201
    return application.json()["id"]


def test_pilot_appraisal_and_valuation_require_accepted_consent_and_remain_simulated():
    owner_headers = _login(OWNER_EMAIL)
    application_id = _create_application(owner_headers)
    assay_payload = {
        "device_id": "DEV-XRF-001",
        "gross_weight_mg": 25000,
        "purity_bps": 9160,
        "signature_checked": True,
    }
    valuation_payload = {
        "items": [{
            "item_type": "Gold bangle",
            "gross_weight_mg": 25000,
            "stone_deduction_mg": 500,
            "purity_bps": 9160,
        }],
        "ltv_scheme_pct": 75,
        "credit_limit_paise": 50000000,
        "policy_version": "APPROVED-POLICY-SUPPLIED-BY-CLIENT",
    }

    assay_without_consent = client.post(
        f"/api/v1/gold-loan/applications/{application_id}/assay-simulation",
        headers=owner_headers,
        json=assay_payload,
    )
    assert assay_without_consent.status_code == 409

    valuation_without_consent = client.post(
        f"/api/v1/gold-loan/applications/{application_id}/valuation",
        headers=owner_headers,
        json=valuation_payload,
    )
    assert valuation_without_consent.status_code == 409

    consent = client.post(
        f"/api/v1/gold-loan/applications/{application_id}/consents",
        headers=owner_headers,
        json={
            "purpose": "Pilot workflow test",
            "wording_version": "PILOT-TEST-1",
            "accepted": True,
            "capture_method": "STAFF_ATTESTATION",
        },
    )
    assert consent.status_code == 200

    assay = client.post(
        f"/api/v1/gold-loan/applications/{application_id}/assay-simulation",
        headers=owner_headers,
        json=assay_payload,
    )
    assert assay.status_code == 200
    assert assay.json()["is_simulated"] is True
    assert assay.json()["device_authenticated"] is False
    after_assay = client.get(
        f"/api/v1/gold-loan/applications/{application_id}",
        headers=owner_headers,
    )
    assert after_assay.status_code == 200
    assert after_assay.json()["stage"] == "APPRAISAL_REVIEW"
    assert after_assay.json()["appraisal_status"] == "SIMULATED_INPUT_RECORDED"

    valuation = client.post(
        f"/api/v1/gold-loan/applications/{application_id}/valuation",
        headers=owner_headers,
        json=valuation_payload,
    )
    assert valuation.status_code == 200
    snapshot = valuation.json()
    assert snapshot["policy_version"] == "UNAPPROVED-PILOT-PREVIEW"
    assert snapshot["is_simulated"] is True
    assert snapshot["application"]["appraisal_status"] == "SIMULATED_PREVIEW"
    assert snapshot["application"]["valuations"][-1]["policy_version"] == "UNAPPROVED-PILOT-PREVIEW"


@pytest.mark.parametrize("outcome", ["APPROVED", "REJECTED", "REFERRED"])
def test_final_gold_loan_decisions_remain_disabled_without_approved_controls(outcome: str):
    owner_headers = _login(OWNER_EMAIL)
    approver_headers = _login(APPROVER_EMAIL)
    application_id = _create_application(owner_headers)

    decision = client.post(
        f"/api/v1/gold-loan/applications/{application_id}/decisions",
        headers=approver_headers,
        json={"outcome": outcome, "rationale": "Pilot test decision"},
    )
    assert decision.status_code == 409
    assert "disabled" in decision.json()["detail"]

    application = client.get(
        f"/api/v1/gold-loan/applications/{application_id}",
        headers=owner_headers,
    )
    assert application.status_code == 200
    assert application.json()["decision_status"] == "NOT_SUBMITTED"
    assert not any(event["action"] == "decision.recorded" for event in application.json()["events"])
