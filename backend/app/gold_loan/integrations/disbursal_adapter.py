import time
import uuid
from typing import Dict, Any, Optional
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode

class DisbursalAdapter(BaseAdapter):
    """
    Adapter for Loan Disbursals (Money Out: Bank IMPS, NEFT, Core Banking payout).
    Strictly segregated from borrower repayments.
    Requires maker-checker approval, idempotency protection, status inquiry,
    reconciliation, and duplicate disbursal prevention.
    """
    def __init__(self):
        super().__init__(
            name="Bank Payout (Disbursals)",
            category="Disbursals & Banking",
            description="Core Banking / IMPS / NEFT Outbound Disbursal Rail with Maker-Checker Gates",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["BANK_PAYOUT_CLIENT_ID", "BANK_PAYOUT_SECRET", "BANK_CORPORATE_ACCOUNT"]
        )
        self.disbursals: Dict[str, Dict[str, Any]] = {}
        self.idempotency_keys: Dict[str, str] = {}

    def execute_disbursal(
        self,
        loan_id: str,
        amount_paise: int,
        beneficiary_account: str,
        beneficiary_ifsc: str,
        beneficiary_name: str,
        maker_id: str,
        checker_id: str,
        idempotency_key: str
    ) -> Dict[str, Any]:
        """
        Executes or simulates bank payout to verified borrower bank account.
        Enforces dual-control maker-checker: Maker and Checker MUST be distinct users.
        """
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production bank payout is unavailable: no bank payout provider is configured")

        if self.simulated_failure == "timeout":
            raise TimeoutError("Disbursal payout gateway request timed out after 45000ms")

        if self.simulated_failure == "upstream_500":
            raise RuntimeError("NPCI / Core Banking payout rail offline: Error 503")

        # Maker-Checker validation
        if not maker_id or not checker_id:
            raise PermissionError("Disbursal requires dual-control maker-checker approval")
        if maker_id == checker_id:
            raise PermissionError("Maker and checker cannot be the same user for loan disbursal")
        if amount_paise <= 0:
            raise ValueError("Disbursal amount must be a positive integer number of paise")
        if not idempotency_key:
            raise ValueError("Disbursal idempotency key is required")

        # IFSC format validation (e.g. HDFC0001234)
        if len(beneficiary_ifsc) != 11:
            raise ValueError(f"Invalid IFSC code '{beneficiary_ifsc}'. Indian banking requires 11 alphanumeric characters")

        # Idempotency check: prevent duplicate money transfer
        if idempotency_key in self.idempotency_keys:
            prev_payout_id = self.idempotency_keys[idempotency_key]
            existing = self.disbursals[prev_payout_id]
            return {
                **existing,
                "idempotent_replay": True,
                "message": "Duplicate disbursal request prevented. Replaying previous payout record."
            }

        # Failure injection: invalid account
        if self.simulated_failure == "invalid_account":
            raise ValueError(f"Beneficiary bank account {beneficiary_account} rejected by NPCI IMPS switch")

        payout_id = f"payout_{self.mode.lower()}_{uuid.uuid4().hex[:12]}"
        simulated = self.mode in [IntegrationMode.MOCK, IntegrationMode.SANDBOX]
        record = {
            "payout_id": payout_id,
            "loan_id": loan_id,
            "amount_paise": amount_paise,
            "currency": "INR",
            "beneficiary_account": f"XXXX{beneficiary_account[-4:]}" if len(beneficiary_account) >= 4 else beneficiary_account,
            "beneficiary_ifsc": beneficiary_ifsc,
            "beneficiary_name": beneficiary_name,
            "maker_id": maker_id,
            "checker_id": checker_id,
            "status": "PENDING" if self.simulated_failure == "payout_pending" else "SIMULATED",
            "created_at": time.time(),
            "is_test_mode": simulated,
            "is_simulated": simulated,
            "provider_confirmed": False,
            "message": "SIMULATED — NO MONEY TRANSFERRED"
        }

        self.disbursals[payout_id] = record
        self.idempotency_keys[idempotency_key] = payout_id
        return record

    def get_payout_status(self, payout_id: str) -> Dict[str, Any]:
        """Inquires status of a payout by payout_id."""
        if payout_id not in self.disbursals:
            raise KeyError(f"Payout {payout_id} not found")
        return self.disbursals[payout_id]
