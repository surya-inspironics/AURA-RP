import hmac
import hashlib
import secrets
import time
import uuid
from typing import Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode

class DeviceGatewayAdapter(BaseAdapter):
    """
    Adapter for Physical Gold Assay Devices (XRF Spectrometer, Legal-Metrology Precision Balance, Density Balance).
    Enforces registered device authentication, calibration certificate validity,
    cryptographic HMAC signatures on readings, nonce replay protection,
    and disallows manual staff overrides.
    """
    def __init__(self):
        super().__init__(
            name="Gold Assay Device Gateway",
            category="Hardware & Assay",
            description="Signed Readings Gateway for XRF Analyzers & Legal-Metrology Balances with Calibration Checks",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["DEVICE_GATEWAY_CERT_PATH", "DEVICE_GATEWAY_SECRET"]
        )
        self.device_secret = settings.DEVICE_GATEWAY_SECRET or secrets.token_urlsafe(32)

        # Registered test devices
        self.registered_devices = {
            "DEV-XRF-001": {
                "device_id": "DEV-XRF-001",
                "device_type": "XRF_ANALYZER",
                "model": "Thermo Scientific Niton DXL",
                "serial_number": "DXL-99841",
                "calibration_valid_until": time.time() + (86400 * 180),  # Valid 6 months
                "is_active": True
            },
            "DEV-SCALE-002": {
                "device_id": "DEV-SCALE-002",
                "device_type": "METROLOGY_SCALE",
                "model": "Mettler Toledo ME204",
                "serial_number": "MT-77401",
                "calibration_valid_until": time.time() + (86400 * 90),
                "is_active": True
            }
        }
        self.used_nonces = set()

    def generate_signed_reading(
        self,
        device_id: str,
        gross_weight_mg: int,
        purity_bps: int,  # 9160 bps = 91.6% (22K)
        reading_type: str = "XRF_SPOT"
    ) -> Dict[str, Any]:
        """
        Simulator helper: creates a tamper-proof signed payload from a registered instrument.
        """
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production device readings must arrive from an authenticated instrument gateway")
        if device_id not in self.registered_devices:
            raise KeyError(f"Device '{device_id}' is not registered with AURA Device Gateway")

        device = self.registered_devices[device_id]
        if not device["is_active"]:
            raise PermissionError(f"Device '{device_id}' is inactive")
        nonce = str(uuid.uuid4())
        timestamp = time.time()

        payload_str = f"{device_id}:{gross_weight_mg}:{purity_bps}:{reading_type}:{nonce}:{timestamp}"
        signature = hmac.new(
            self.device_secret.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return {
            "device_id": device_id,
            "device_type": device["device_type"],
            "model": device["model"],
            "serial_number": device["serial_number"],
            "gross_weight_mg": gross_weight_mg,
            "purity_bps": purity_bps,
            "reading_type": reading_type,
            "nonce": nonce,
            "timestamp": timestamp,
            "signature": signature,
            "is_simulated": True,
            "calibration_valid": time.time() < device["calibration_valid_until"]
        }

    def verify_reading(self, reading: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingests and verifies signed reading at backend boundary:
        1. Validates device registration.
        2. Validates calibration certificate.
        3. Enforces nonce replay protection.
        4. Verifies cryptographic signature.
        5. Rejects simulated readings in production financial processing.
        """
        device_id = reading.get("device_id")
        if device_id not in self.registered_devices:
            raise PermissionError(f"Unregistered device {device_id}: Assay readings rejected")

        device = self.registered_devices[device_id]
        if not device["is_active"]:
            raise PermissionError(f"Device '{device_id}' is inactive")

        timestamp = reading.get("timestamp")
        if not isinstance(timestamp, (int, float)) or abs(time.time() - timestamp) > 300:
            raise ValueError("Reading timestamp is missing, stale, or outside the permitted clock skew")
        if reading.get("gross_weight_mg", 0) <= 0:
            raise ValueError("Reading gross weight must be positive")
        if not 0 < reading.get("purity_bps", 0) <= 10000:
            raise ValueError("Reading purity must be between 1 and 10000 basis points")

        # Calibration check
        if time.time() > device["calibration_valid_until"] or self.simulated_failure == "expired_calibration":
            raise ValueError(f"Calibration certificate for device {device_id} has EXPIRED. Recalibration mandatory.")

        # Replay protection
        nonce = reading.get("nonce")
        if not nonce or nonce in self.used_nonces:
            raise ValueError("Replay detected: Instrument reading nonce has already been consumed")

        # Signature verification
        expected_str = f"{device_id}:{reading['gross_weight_mg']}:{reading['purity_bps']}:{reading['reading_type']}:{nonce}:{reading['timestamp']}"
        expected_sig = hmac.new(
            self.device_secret.encode("utf-8"),
            expected_str.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if self.simulated_failure == "invalid_signature" or not hmac.compare_digest(expected_sig, reading.get("signature", "")):
            raise ValueError("Cryptographic verification failed: Reading payload has been tampered with")

        # Reject simulated in PRODUCTION
        if self.mode == IntegrationMode.PRODUCTION and reading.get("is_simulated"):
            raise ValueError("PRODUCTION SECURITY GATE: Simulated device reading rejected for live financial disbursal")

        self.used_nonces.add(nonce)

        return {
            "verified": True,
            "device_id": device_id,
            "gross_weight_mg": reading["gross_weight_mg"],
            "purity_bps": reading["purity_bps"],
            "purity_karat": round((reading["purity_bps"] / 10000.0) * 24.0, 1),
            "is_simulated": reading.get("is_simulated", False),
            "provider_authenticated": not reading.get("is_simulated", False),
            "timestamp": reading["timestamp"]
        }
