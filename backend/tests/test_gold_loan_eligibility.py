import pytest
from backend.app.gold_loan.services.eligibility_engine import EligibilityEngine

def test_single_item_valuation_and_eligibility():
    """
    Scenario:
    - 1 Gold Bangle: Gross = 20,000 mg (20g), Stone = 2,000 mg (2g), Net = 18,000 mg (18g).
    - Purity: 9160 bps (22 Karat / 91.6%).
    - Fine gold weight: 18,000 * 9160 / 10000 = 16,488 mg (16.488g).
    - Rate: Rs 7,250 / g = 725,000 paise/g -> 725 paise/mg.
    - Market Value: 16,488 * 725 = 11,953,800 paise (Rs 119,538.00).
    - LTV: 75% -> Collateral Limit: 11,953,800 * 75 / 100 = 8,965,350 paise (Rs 89,653.50).
    """
    items = [{
        "item_type": "Gold Bangle",
        "gross_weight_mg": 20000,
        "stone_deduction_mg": 2000,
        "purity_bps": 9160
    }]

    result = EligibilityEngine.calculate_valuation_and_eligibility(
        items=items,
        gold_rate_per_gram_paise=725000,
        rate_version="IBJA-2026-10-15-AM",
        ltv_scheme_pct=75
    )

    summary = result["summary"]
    assert summary["total_gross_weight_mg"] == 20000
    assert summary["total_net_weight_mg"] == 18000
    assert summary["total_fine_weight_mg"] == 16488
    assert summary["total_gold_valuation_paise"] == 11953800
    assert summary["eligible_loan_amount_paise"] == 8965350
    assert summary["applied_ltv_pct"] == 75
    assert summary["compliance_status"] == "COMPLIANT"
    assert summary["binding_constraint"] == "COLLATERAL_LTV_LIMIT"

def test_binding_constraint_credit_limit():
    """
    When collateral LTV limit (Rs 200,000) exceeds borrower credit limit (Rs 100,000),
    the final eligible amount MUST be capped at the credit limit (Rs 100,000).
    """
    items = [{
        "item_type": "Gold Necklace",
        "gross_weight_mg": 50000, # 50g
        "stone_deduction_mg": 0,
        "purity_bps": 9160
    }]

    result = EligibilityEngine.calculate_valuation_and_eligibility(
        items=items,
        gold_rate_per_gram_paise=725000,
        rate_version="IBJA-2026-10-15-AM",
        ltv_scheme_pct=75,
        credit_limit_paise=10000000 # Capped at Rs 100,000
    )

    summary = result["summary"]
    assert summary["eligible_loan_amount_paise"] == 10000000
    assert summary["binding_constraint"] == "BORROWER_CREDIT_LIMIT"

def test_ltv_slab_regulatory_ceiling_flag():
    """
    If scheme LTV is set to 80% or 85% (exceeding standard RBI 75% ceiling),
    the engine MUST flag 'REQUIRES_COMPLIANCE_CONFIRMATION'.
    """
    items = [{
        "item_type": "Gold Coins",
        "gross_weight_mg": 10000,
        "stone_deduction_mg": 0,
        "purity_bps": 9990 # 24K pure
    }]

    result = EligibilityEngine.calculate_valuation_and_eligibility(
        items=items,
        gold_rate_per_gram_paise=725000,
        rate_version="IBJA-2026-10-15-AM",
        ltv_scheme_pct=85 # Slabs above 75%
    )

    summary = result["summary"]
    assert summary["compliance_status"] == "REQUIRES_COMPLIANCE_CONFIRMATION"
    assert "exceeds RBI benchmark 75% ceiling" in summary["compliance_note"]

def test_invalid_stone_deduction_rejected():
    """Stone deduction cannot exceed gross weight."""
    items = [{
        "item_type": "Gold Ring",
        "gross_weight_mg": 5000,
        "stone_deduction_mg": 6000, # Fraudulent: stone > gross
        "purity_bps": 9160
    }]

    with pytest.raises(ValueError) as exc:
        EligibilityEngine.calculate_valuation_and_eligibility(
            items=items,
            gold_rate_per_gram_paise=725000,
            rate_version="IBJA-2026-10-15-AM"
        )
    assert "Stone deduction" in str(exc.value)
