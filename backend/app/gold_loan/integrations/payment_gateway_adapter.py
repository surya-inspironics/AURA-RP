import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from backend.app.core.config import settings
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode


class RazorpayProviderError(RuntimeError):
    """A provider response could not be completed or verified safely."""


class PaymentGatewayAdapter(BaseAdapter):
    """Razorpay test-mode order creation and payment verification."""

    API_BASE_URL = "https://api.razorpay.com/v1"

    def __init__(self):
        super().__init__(
            name="Payment Gateway (Repayments)",
            category="Repayments & Webhooks",
            description="Razorpay test-mode repayment checkout and provider verification",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"]
        )

    def assert_test_checkout_enabled(self) -> None:
        if self.mode != IntegrationMode.SANDBOX:
            raise RuntimeError("Razorpay checkout is currently restricted to SANDBOX mode.")
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            raise RuntimeError("Razorpay test credentials are not configured on the server.")
        if not settings.RAZORPAY_KEY_ID.startswith("rzp_test_"):
            raise RuntimeError("Razorpay checkout requires a test key; live charging is disabled.")

    def get_status(self) -> dict[str, Any]:
        status = super().get_status()
        key_id_configured = bool(settings.RAZORPAY_KEY_ID)
        key_secret_configured = bool(settings.RAZORPAY_KEY_SECRET)
        status["required_configs"] = [
            {"key": "RAZORPAY_KEY_ID", "configured": key_id_configured},
            {"key": "RAZORPAY_KEY_SECRET", "configured": key_secret_configured},
        ]
        if not key_id_configured or not key_secret_configured:
            status["health"] = "NOT_CONFIGURED"
        elif not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_ID.startswith("rzp_test_"):
            status["health"] = "UNAVAILABLE"
            status["last_error"] = "Only Razorpay test credentials are accepted by this checkout."
        else:
            status["health"] = "DEGRADED" if self.last_error else "SIMULATED"
        status["is_test_mode"] = True
        return status

    def test_connection(self) -> dict[str, Any]:
        self.last_health_check = datetime.now(timezone.utc)
        try:
            response = self._request("GET", "/orders?count=1")
        except (RazorpayProviderError, RuntimeError) as exc:
            self.last_error = str(exc)
            return {
                "success": False,
                "status": "DEGRADED" if settings.RAZORPAY_KEY_ID else "NOT_CONFIGURED",
                "latency_ms": 0,
                "is_simulated": False,
                "is_test_mode": True,
                "error": self.last_error,
            }
        if not isinstance(response.get("items"), list):
            self.last_error = "Razorpay test API returned an unexpected health-check response."
            return {
                "success": False,
                "status": "DEGRADED",
                "latency_ms": 0,
                "is_simulated": False,
                "is_test_mode": True,
                "error": self.last_error,
            }
        self.last_error = None
        return {
            "success": True,
            "status": "HEALTHY",
            "latency_ms": 0,
            "is_simulated": False,
            "is_test_mode": True,
            "message": "Razorpay test API is reachable. No payment was created.",
        }

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self.assert_test_checkout_enabled()
        key_id = settings.RAZORPAY_KEY_ID
        key_secret = settings.RAZORPAY_KEY_SECRET
        if not key_id or not key_secret:
            raise RuntimeError("Razorpay test credentials are not configured on the server.")

        credentials = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("ascii")
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.API_BASE_URL}{path}",
            data=body,
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json",
            },
            method=method,
        )

        try:
            with urlopen(request, timeout=20) as response:
                response_body = response.read()
        except HTTPError as exc:
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
                description = error_payload.get("error", {}).get("description", "Provider rejected the request.")
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                description = "Provider rejected the request."
            raise RazorpayProviderError(f"Razorpay request failed (HTTP {exc.code}): {description}") from exc
        except URLError as exc:
            raise RazorpayProviderError("Could not reach Razorpay; payment status was not confirmed.") from exc
        except TimeoutError as exc:
            raise RazorpayProviderError("Razorpay request timed out; payment status was not confirmed.") from exc

        try:
            result = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RazorpayProviderError("Razorpay returned an invalid response.") from exc
        if not isinstance(result, dict):
            raise RazorpayProviderError("Razorpay returned an invalid response.")
        return result

    def create_payment_order(self, loan_id: str, amount_paise: int, idempotency_key: str) -> dict[str, Any]:
        self.assert_test_checkout_enabled()
        if amount_paise <= 0:
            raise ValueError("Repayment amount must be a positive integer number of paise.")
        if not idempotency_key or len(idempotency_key) > 40:
            raise ValueError("Payment-order idempotency key must contain 1 to 40 characters.")
        if not loan_id.strip():
            raise ValueError("Loan reference is required.")
        if self.simulated_failure == "timeout":
            raise RazorpayProviderError("Razorpay request timed out; payment status was not confirmed.")
        if self.simulated_failure == "upstream_500":
            raise RazorpayProviderError("Razorpay is temporarily unavailable.")

        provider_order = self._request("POST", "/orders", {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": idempotency_key,
            "notes": {"loan_id": loan_id.strip()},
        })
        if (
            not provider_order.get("id")
            or provider_order.get("amount") != amount_paise
            or provider_order.get("currency") != "INR"
            or provider_order.get("receipt") != idempotency_key
        ):
            raise RazorpayProviderError("Razorpay order response did not match the requested amount and reference.")

        return {
            "order_id": provider_order["id"],
            "loan_id": loan_id.strip(),
            "amount_paise": amount_paise,
            "currency": "INR",
            "status": "ORDER_CREATED",
            "is_test_mode": True,
            "is_simulated": False,
            "provider_confirmed": False,
            "message": "Razorpay test order created; no live funds can be collected.",
        }

    def verify_checkout_payment(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
        expected_amount_paise: int,
    ) -> dict[str, Any]:
        self.assert_test_checkout_enabled()
        if not order_id or not payment_id or not signature:
            raise ValueError("Razorpay order, payment, and signature values are required.")

        key_secret = settings.RAZORPAY_KEY_SECRET
        if not key_secret:
            raise RuntimeError("Razorpay test credentials are not configured on the server.")
        signed_data = f"{order_id}|{payment_id}".encode("utf-8")
        expected_signature = hmac.new(key_secret.encode("utf-8"), signed_data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_signature, signature):
            raise ValueError("Razorpay payment signature is invalid.")

        payment = self._request("GET", f"/payments/{quote(payment_id, safe='')}")
        if (
            payment.get("id") != payment_id
            or payment.get("order_id") != order_id
            or payment.get("amount") != expected_amount_paise
            or payment.get("currency") != "INR"
        ):
            raise ValueError("Razorpay payment does not match the stored order amount and currency.")

        provider_status = payment.get("status")
        if provider_status not in {"captured", "authorized", "failed"}:
            raise ValueError("Razorpay has not returned a final supported payment status.")

        status = {
            "captured": "CAPTURED",
            "authorized": "AUTHORIZED",
            "failed": "FAILED",
        }[provider_status]
        return {
            "order_id": order_id,
            "payment_id": payment_id,
            "amount_paise": expected_amount_paise,
            "currency": "INR",
            "status": status,
            "is_test_mode": True,
            "is_simulated": False,
            "provider_confirmed": status == "CAPTURED",
            "ledger_updated": False,
            "message": (
                "Razorpay confirmed this test payment as captured; no live funds or loan ledger were changed."
                if status == "CAPTURED"
                else f"Razorpay test payment status: {status.lower()}; no loan ledger was changed."
            ),
        }
