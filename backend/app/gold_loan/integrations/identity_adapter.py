import re
from typing import Dict, Any
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode


def _mask_pan(pan_number: str) -> str:
    clean_pan = re.sub(r"[^A-Z0-9]", "", pan_number.upper())
    return f"XXXXX{clean_pan[-5:]}" if len(clean_pan) == 10 else "REDACTED"


class IdentityAdapter(BaseAdapter):
    """
    Adapter for Aadhaar eKYC, PAN Verification, and Central KYC (CKYC) Registry.
    Enforces Aadhaar masking (XXXX-XXXX-1234), consent recording, and NSDL format validation.
    """
    def __init__(self):
        super().__init__(
            name="Identity & KYC (Aadhaar / PAN / CKYC)",
            category="Customer Verification",
            description="Aadhaar eKYC (UIDAI simulated), PAN Verification (NSDL), and CKYC Registry Integration",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["UIDAI_AUTH_KEY", "NSDL_PAN_CLIENT_ID", "CKYC_PORTAL_TOKEN"]
        )

    def verify_pan(self, pan_number: str, customer_name: str) -> Dict[str, Any]:
        """
        Verifies 10-character PAN against NSDL.
        Format rule: 5 uppercase letters, 4 digits, 1 uppercase letter.
        Fourth character: 'P' for individual person.
        """
        if self.simulated_failure == "timeout":
            raise TimeoutError("PAN verification service timed out")

        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production PAN verification is unavailable: no provider adapter is configured")

        pan_clean = pan_number.strip().upper()
        masked_pan = _mask_pan(pan_clean)
        pan_regex = r"^[A-Z]{5}[0-9]{4}[A-Z]$"
        if not re.match(pan_regex, pan_clean):
            return {
                "masked_pan": masked_pan,
                "format_valid": False,
                "status": "INVALID_FORMAT",
                "message": "PAN must adhere to 5 letters, 4 digits, and 1 letter format",
                "is_test_mode": True,
                "is_simulated": True,
                "provider_verified": False
            }

        if self.simulated_failure == "pan_mismatch":
            return {
                "masked_pan": masked_pan,
                "format_valid": True,
                "status": "NAME_MISMATCH",
                "message": "Simulated name mismatch; no identity provider was queried",
                "is_test_mode": True,
                "is_simulated": True,
                "provider_verified": False
            }

        return {
            "masked_pan": masked_pan,
            "format_valid": True,
            "status": "SIMULATED",
            "message": "Synthetic format check only; no identity provider was queried",
            "is_test_mode": True,
            "is_simulated": True,
            "provider_verified": False
        }

    def verify_aadhaar_ekyc(self, aadhaar_number: str, otp: str, consent_given: bool) -> Dict[str, Any]:
        """
        Performs Aadhaar eKYC. Masking of the first 8 digits is MANDATORY.
        Never stores or returns unmasked 12-digit Aadhaar.
        """
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production Aadhaar eKYC is unavailable: no provider adapter is configured")

        if not consent_given:
            raise PermissionError("Aadhaar eKYC requires explicit, auditable customer consent")

        clean_num = re.sub(r"\D", "", aadhaar_number)
        if len(clean_num) != 12:
            raise ValueError("Aadhaar number must contain exactly 12 digits")

        if self.simulated_failure == "invalid_otp" or (otp != "123456" and self.mode == IntegrationMode.SANDBOX and otp != "VERIFIED"):
            return {
                "format_valid": True,
                "status": "OTP_FAILED",
                "message": "Simulated OTP failure; no identity provider was queried",
                "is_test_mode": True,
                "is_simulated": True,
                "provider_verified": False
            }

        masked_aadhaar = f"XXXX-XXXX-{clean_num[-4:]}"
        return {
            "format_valid": True,
            "status": "SIMULATED",
            "masked_aadhaar": masked_aadhaar,
            "message": "Synthetic format check only; no identity provider was queried",
            "is_test_mode": True,
            "is_simulated": True,
            "provider_verified": False
        }

    def lookup_ckyc(self, ckyc_number: str) -> Dict[str, Any]:
        """Looks up Central KYC (CKYC) registry."""
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production CKYC lookup is unavailable: no provider adapter is configured")

        if len(ckyc_number) != 14:
            raise ValueError("Central KYC identifier (CKYC) must be a 14-digit identifier")

        return {
            "status": "SIMULATED",
            "is_test_mode": True,
            "is_simulated": True,
            "provider_verified": False,
            "message": "No CKYC provider was queried"
        }
