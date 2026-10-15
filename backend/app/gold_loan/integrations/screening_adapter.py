from typing import Dict, Any
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode
from backend.app.gold_loan.integrations.identity_adapter import _mask_pan

class ScreeningAdapter(BaseAdapter):
    """
    Adapter for Anti-Money Laundering (AML), OFAC Sanctions, and Politically Exposed Persons (PEP) Screening.
    Enforces regulatory compliance before gold pledge approval.
    """
    def __init__(self):
        super().__init__(
            name="AML / Sanctions / PEP Screening",
            category="Compliance & Screening",
            description="Global Sanctions Lists, Interpol Red Notices, and PEP Registry Screening",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["AML_PROVIDER_API_KEY", "SANCTIONS_DATABASE_URL"]
        )

    def screen_individual(self, full_name: str, pan: str, country: str = "IN") -> Dict[str, Any]:
        """Returns a synthetic development scenario; no watchlist is queried."""
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production sanctions screening is unavailable: no provider adapter is configured")

        if self.simulated_failure == "timeout":
            raise TimeoutError("Sanctions screening engine timed out")

        # Failure injection: hit / sanctions match
        if self.simulated_failure == "sanctions_hit":
            return {
                "full_name": full_name,
                "masked_pan": _mask_pan(pan),
                "sanctions_matched": True,
                "pep_matched": False,
                "risk_rating": "CRITICAL_BLOCKED",
                "matched_lists": ["OFAC_SDN", "UN_CONSOLIDATED"],
                "match_score": 96.0,
                "action_required": "BLOCK_APPLICATION_REPORT_FIU",
                "is_test_mode": True,
                "is_simulated": True,
                "provider_verified": False
            }

        if self.simulated_failure == "pep_match":
            return {
                "full_name": full_name,
                "masked_pan": _mask_pan(pan),
                "sanctions_matched": False,
                "pep_matched": True,
                "risk_rating": "HIGH_PEP",
                "matched_lists": ["PEP_INDIA_DOMESTIC"],
                "match_score": 88.0,
                "action_required": "SENIOR_MANAGEMENT_APPROVAL_REQUIRED",
                "is_test_mode": True,
                "is_simulated": True,
                "provider_verified": False
            }

        return {
            "full_name": full_name,
            "masked_pan": _mask_pan(pan),
            "sanctions_matched": False,
            "pep_matched": False,
            "risk_rating": "LOW",
            "matched_lists": [],
            "match_score": 0.0,
            "action_required": "NONE",
            "is_test_mode": True,
            "is_simulated": True,
            "provider_verified": False
        }
