import time
import uuid
from typing import Dict, Any
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode
from backend.app.gold_loan.integrations.identity_adapter import _mask_pan

class CreditBureauAdapter(BaseAdapter):
    """
    Adapter for Credit Bureau Assessment (CIBIL / Experian / CRIF).
    Provides synthetic credit scoring, active credit facilities, overdue amounts,
    and delinquency flags for underwriting decisions.
    """
    def __init__(self):
        super().__init__(
            name="Credit Bureau (CIBIL / Experian)",
            category="Credit & Risk",
            description="Consumer Credit Bureau Score, Active Debt Obligations, and Default History",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["CIBIL_MEMBER_ID", "CIBIL_PASSWORD", "BUREAU_API_ENDPOINT"]
        )

    def fetch_credit_report(self, pan: str, customer_name: str, consent_timestamp: float) -> Dict[str, Any]:
        """Returns a synthetic development profile; no bureau is queried."""
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production credit-bureau lookup is unavailable: no provider adapter is configured")

        if self.simulated_failure == "timeout":
            raise TimeoutError("Credit Bureau inquiry timed out after 30000ms")

        if not consent_timestamp:
            raise PermissionError("Credit bureau pull requires documented borrower consent")

        # Configurable synthetic profiles
        if self.simulated_failure == "low_score":
            score = 540
            risk_category = "HIGH_RISK"
            overdue_paise = 4500000  # 45,000 INR
            defaults_count = 2
        else:
            score = 765
            risk_category = "LOW_RISK"
            overdue_paise = 0
            defaults_count = 0

        return {
            "masked_pan": _mask_pan(pan),
            "source": "SIMULATED_SAMPLE",
            "score": score,
            "risk_category": risk_category,
            "active_credit_lines": 3,
            "gold_loans_active": 1,
            "overdue_amount_paise": overdue_paise,
            "default_accounts_count": defaults_count,
            "simulation_id": f"sim_credit_{uuid.uuid4().hex[:10]}",
            "is_test_mode": True,
            "is_simulated": True,
            "provider_verified": False
        }
