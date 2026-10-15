import time
from typing import Dict, Any, List, Optional

class CollectionsEngine:
    """
    Service managing Mark-to-Market (MTM) Collateral Revaluation,
    Margin Call Triggers, and Delinquency / NPA Classification.
    """
    WARNING_LTV_THRESHOLD_PCT = 80
    MARGIN_CALL_THRESHOLD_PCT = 85
    CRITICAL_AUCTION_LTV_PCT = 90

    @classmethod
    def evaluate_mtm_ltv(
        cls,
        loan_id: str,
        total_outstanding_paise: int,
        net_gold_weight_mg: int,
        purity_bps: int,
        current_24k_rate_per_gram_paise: int
    ) -> Dict[str, Any]:
        """
        Revalues gold collateral against live market rate and computes current LTV.
        W_fine = (W_net * purity_bps) / 10000
        V_gold = W_fine * rate_per_mg
        Current LTV = (Total Outstanding / V_gold) * 100
        """
        rate_per_mg_paise = current_24k_rate_per_gram_paise // 1000
        fine_gold_mg = (net_gold_weight_mg * purity_bps) // 10000
        current_market_value_paise = fine_gold_mg * rate_per_mg_paise

        if current_market_value_paise <= 0:
            current_ltv_pct = 100.0
        else:
            current_ltv_pct = round((total_outstanding_paise / current_market_value_paise) * 100.0, 2)

        # Margin Call Check
        requires_margin_call = current_ltv_pct >= cls.MARGIN_CALL_THRESHOLD_PCT

        # Shortfall is the amount borrower needs to pay to bring LTV down to safe 75%
        target_safe_outstanding = int(current_market_value_paise * 0.75)
        shortfall_paise = max(0, total_outstanding_paise - target_safe_outstanding)

        risk_tier = "HEALTHY"
        if current_ltv_pct >= cls.CRITICAL_AUCTION_LTV_PCT:
            risk_tier = "CRITICAL_AUCTION_RISK"
        elif current_ltv_pct >= cls.MARGIN_CALL_THRESHOLD_PCT:
            risk_tier = "MARGIN_CALL_TRIGGERED"
        elif current_ltv_pct >= cls.WARNING_LTV_THRESHOLD_PCT:
            risk_tier = "WATCHLIST_WARNING"

        return {
            "loan_id": loan_id,
            "current_market_value_paise": current_market_value_paise,
            "current_market_value_inr": current_market_value_paise / 100.0,
            "total_outstanding_paise": total_outstanding_paise,
            "total_outstanding_inr": total_outstanding_paise / 100.0,
            "current_ltv_pct": current_ltv_pct,
            "risk_tier": risk_tier,
            "requires_margin_call": requires_margin_call,
            "margin_shortfall_paise": shortfall_paise,
            "margin_shortfall_inr": shortfall_paise / 100.0,
            "evaluated_at": time.time()
        }
