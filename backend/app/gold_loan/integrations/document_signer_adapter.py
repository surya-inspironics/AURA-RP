from typing import Dict, Any
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode

class DocumentSignerAdapter(BaseAdapter):
    """
    Adapter for Digital E-Signing (Aadhaar e-Sign) and Digital E-Stamping (NeSL).
    Generates and digitally seals Sanction Letters, Key Fact Statements (KFS),
    Pledge Agreements, and Pawn Tickets.
    """
    def __init__(self):
        super().__init__(
            name="E-Sign & E-Stamp (NeSL / Aadhaar)",
            category="Legal & Documentation",
            description="Digital E-Stamping and Aadhaar e-Sign for Sanction Letter, KFS, and Pawn Ticket",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["NESL_CLIENT_ID", "ESIGN_ASP_ID", "ESIGN_AUTH_TOKEN"]
        )

    def generate_and_sign_kfs(
        self,
        loan_id: str,
        customer_name: str,
        sanctioned_amount_paise: int,
        annual_interest_rate_pct: float,
        tenure_months: int
    ) -> Dict[str, Any]:
        """Returns a simulator marker; this adapter does not generate or sign documents."""
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production document signing is unavailable: no signing provider is configured")

        if self.simulated_failure == "timeout":
            raise TimeoutError("NeSL digital stamping service timed out")

        return {
            "document_type": "KEY_FACT_STATEMENT_KFS",
            "status": "SIMULATED_NOT_GENERATED_OR_SIGNED",
            "document_created": False,
            "provider_signed": False,
            "is_test_mode": True,
            "is_simulated": True,
            "message": "No KFS document, e-stamp, or signature was created"
        }
