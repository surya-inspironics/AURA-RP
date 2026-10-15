import pytest
from backend.app.gold_loan.integrations.registry import adapter_registry
from backend.app.gold_loan.services.eligibility_engine import EligibilityEngine
from backend.app.gold_loan.services.custody_service import CustodyService
from backend.app.gold_loan.services.loan_servicing_engine import LoanServicingEngine
from backend.app.gold_loan.services.collections_engine import CollectionsEngine

def test_gold_loan_calculators_and_adapters_report_simulation_state():
    # ---------------------------------------------------------
    # STEP 1: Customer Onboarding & KYC
    # ---------------------------------------------------------
    identity = adapter_registry.identity
    pan_res = identity.verify_pan("ABCDE1234F", "Suresh Kumar")
    assert pan_res["format_valid"] is True
    assert pan_res["status"] == "SIMULATED"
    assert pan_res["provider_verified"] is False
    assert "pan" not in pan_res
    assert pan_res["masked_pan"] == "XXXXX1234F"
    bureau_res = adapter_registry.credit_bureau.fetch_credit_report(
        "ABCDE1234F", "Suresh Kumar", consent_timestamp=1.0
    )
    assert bureau_res["source"] == "SIMULATED_SAMPLE"
    assert bureau_res["masked_pan"] == "XXXXX1234F"
    assert "pan" not in bureau_res
    assert bureau_res["provider_verified"] is False

    aadhaar_res = identity.verify_aadhaar_ekyc("987654321098", "123456", consent_given=True)
    assert aadhaar_res["format_valid"] is True
    assert aadhaar_res["status"] == "SIMULATED"
    assert aadhaar_res["provider_verified"] is False
    assert aadhaar_res["masked_aadhaar"] == "XXXX-XXXX-1098"

    screening = adapter_registry.screening
    scr_res = screening.screen_individual("Suresh Kumar", "ABCDE1234F")
    assert scr_res["risk_rating"] == "LOW"
    assert scr_res["is_simulated"] is True
    assert scr_res["provider_verified"] is False
    assert scr_res["masked_pan"] == "XXXXX1234F"

    # ---------------------------------------------------------
    # STEP 2: Instrument Assay & Signed Readings
    # ---------------------------------------------------------
    gateway = adapter_registry.device_gateway
    xrf_reading = gateway.generate_signed_reading("DEV-XRF-001", gross_weight_mg=30000, purity_bps=9160)
    verified_reading = gateway.verify_reading(xrf_reading)
    assert verified_reading["verified"] is True
    assert verified_reading["purity_karat"] == 22.0

    # ---------------------------------------------------------
    # STEP 3: Gold Valuation & Eligibility
    # ---------------------------------------------------------
    items = [{
        "item_type": "Gold Chain",
        "gross_weight_mg": 30000,
        "stone_deduction_mg": 1000, # Net = 29,000 mg
        "purity_bps": 9160
    }]
    val_res = EligibilityEngine.calculate_valuation_and_eligibility(
        items=items,
        gold_rate_per_gram_paise=725000, # Rs 7,250/g -> 725 p/mg
        rate_version="SIM-RATE-TEST",
        ltv_scheme_pct=75
    )
    eligible_paise = val_res["summary"]["eligible_loan_amount_paise"]
    assert eligible_paise > 0

    # ---------------------------------------------------------
    # STEP 4: KFS & Document Digital Signing
    # ---------------------------------------------------------
    signer = adapter_registry.document_signer
    kfs = signer.generate_and_sign_kfs(
        loan_id="AURA-GL-2026-9901",
        customer_name="Suresh Kumar",
        sanctioned_amount_paise=eligible_paise,
        annual_interest_rate_pct=10.5,
        tenure_months=12
    )
    assert kfs["status"] == "SIMULATED_NOT_GENERATED_OR_SIGNED"
    assert kfs["document_created"] is False
    assert kfs["provider_signed"] is False

    # ---------------------------------------------------------
    # STEP 5: Vault Packet Dual-Control Sealing
    # ---------------------------------------------------------
    custody = CustodyService()
    packet = custody.seal_packet(
        loan_id="AURA-GL-2026-9901",
        custodian_1_id="custodian_maya_chen",
        custodian_2_id="custodian_samir_patel",
        vault_rack_id="VAULT-BAY-03-RACK-07",
        item_count=1,
        net_weight_mg=29000
    )
    assert packet["status"] == "SIMULATED_NOT_PHYSICALLY_SEALED"
    assert packet["physical_custody_confirmed"] is False
    assert packet["barcode"].startswith("AURA-PKT-")

    # ---------------------------------------------------------
    # STEP 6: Maker-Checker Disbursal Execution (Money Out)
    # ---------------------------------------------------------
    disbursal = adapter_registry.disbursal
    payout = disbursal.execute_disbursal(
        loan_id="AURA-GL-2026-9901",
        amount_paise=eligible_paise,
        beneficiary_account="501002345678",
        beneficiary_ifsc="HDFC0001234",
        beneficiary_name="Suresh Kumar",
        maker_id="maker_analyst_01",
        checker_id="checker_manager_02",
        idempotency_key="idemp_disb_gl_9901"
    )
    assert payout["status"] == "SIMULATED"
    assert payout["provider_confirmed"] is False
    assert "utr_number" not in payout

    # ---------------------------------------------------------
    # STEP 7: Daily Interest Accrual (LMS Servicing)
    # ---------------------------------------------------------
    # Accrue for 30 days at 10.5% p.a.
    accrued_30_days = LoanServicingEngine.calculate_daily_interest_accrual(
        principal_paise=eligible_paise,
        annual_rate_pct=10.5,
        days=30
    )
    assert accrued_30_days > 0

    # ---------------------------------------------------------
    # STEP 8: Borrower Repayment Waterfall Allocation
    # ---------------------------------------------------------
    # Borrower repays interest + 50% of principal
    repayment_payment = accrued_30_days + (eligible_paise // 2)
    allocation = LoanServicingEngine.allocate_repayment_waterfall(
        payment_amount_paise=repayment_payment,
        current_principal_paise=eligible_paise,
        accrued_interest_paise=accrued_30_days
    )
    assert allocation["allocated_current_interest_paise"] == accrued_30_days
    assert allocation["allocated_principal_paise"] == (eligible_paise // 2)
    assert allocation["remaining_current_interest_paise"] == 0
    assert allocation["remaining_principal_paise"] == eligible_paise - (eligible_paise // 2)

    # ---------------------------------------------------------
    # STEP 9: Mark-to-Market (MTM) LTV Revaluation & Margin Call
    # ---------------------------------------------------------
    # Test healthy position
    mtm = CollectionsEngine.evaluate_mtm_ltv(
        loan_id="AURA-GL-2026-9901",
        total_outstanding_paise=allocation["new_total_outstanding_paise"],
        net_gold_weight_mg=29000,
        purity_bps=9160,
        current_24k_rate_per_gram_paise=725000
    )
    assert mtm["current_ltv_pct"] < 50.0
    assert mtm["risk_tier"] == "HEALTHY"
    assert mtm["requires_margin_call"] is False

    # Simulate severe gold market crash triggering Margin Call
    mtm_crash = CollectionsEngine.evaluate_mtm_ltv(
        loan_id="AURA-GL-2026-9901",
        total_outstanding_paise=allocation["new_total_outstanding_paise"],
        net_gold_weight_mg=29000,
        purity_bps=9160,
        current_24k_rate_per_gram_paise=250000 # Gold drops by 65%
    )
    assert mtm_crash["requires_margin_call"] is True
    assert mtm_crash["margin_shortfall_paise"] > 0

    # ---------------------------------------------------------
    # STEP 10: Final Repayment and Vault Collateral Release
    # ---------------------------------------------------------
    final_repayment = LoanServicingEngine.allocate_repayment_waterfall(
        payment_amount_paise=allocation["remaining_principal_paise"],
        current_principal_paise=allocation["remaining_principal_paise"],
        accrued_interest_paise=0
    )
    assert final_repayment["is_loan_fully_cleared"] is True

    release = custody.release_collateral(
        barcode=packet["barcode"],
        releasing_custodian_id="custodian_maya_chen",
        witness_custodian_id="custodian_samir_patel",
        borrower_signature_ack=True,
        is_loan_fully_paid=True
    )
    assert release["status"] == "SIMULATED_NOT_PHYSICALLY_RELEASED"
    assert release["physical_custody_confirmed"] is False

    # ---------------------------------------------------------
    # STEP 11: E-Auction Recovery Settlement (for defaulted loan scenario)
    # ---------------------------------------------------------
    auction = adapter_registry.auction
    auction_res = auction.settle_auction(
        loan_id="AURA-GL-DEFAULT-01",
        total_outstanding_paise=10000000, # 100,000 INR
        net_gold_weight_mg=20000,        # 20g
        current_gold_rate_per_mg_paise=725
    )
    assert auction_res["status"] == "SIMULATED"
    assert auction_res["provider_confirmed"] is False
    assert auction_res["winning_bid_paise"] >= auction_res["reserve_price_paise"]
    assert auction_res["surplus_refund_to_borrower_paise"] > 0
