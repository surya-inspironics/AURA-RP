import os
import time
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

class IntegrationMode(str, Enum):
    MOCK = "MOCK"
    SANDBOX = "SANDBOX"
    PRODUCTION = "PRODUCTION"

class AdapterHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    SIMULATED = "SIMULATED"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"

class BaseAdapter:
    """
    Abstract base class for all AURA Gold Loan external integration adapters.
    Enforces the 3-mode model (MOCK, SANDBOX, PRODUCTION), health checks,
    failure injection, correlation tracking, and production safety guards.
    """
    def __init__(
        self,
        name: str,
        category: str,
        description: str,
        default_mode: IntegrationMode = IntegrationMode.MOCK,
        required_config_keys: Optional[List[str]] = None
    ):
        self.name = name
        self.category = category
        self.description = description
        self.mode = default_mode
        self.required_config_keys = required_config_keys or []
        self.last_health_check: Optional[datetime] = datetime.now(timezone.utc)
        self.last_error: Optional[str] = None
        self.simulated_failure: Optional[str] = None  # timeout, invalid_signature, duplicate, mismatch, upstream_500
        self.connection_latency_ms: float = 12.4

    def set_mode(self, new_mode: IntegrationMode):
        """
        Switches adapter mode.
        Strict Safety Guard: PRODUCTION mode requires environment authorization and secrets.
        """
        if new_mode == IntegrationMode.PRODUCTION:
            allow_prod = os.getenv("ALLOW_PRODUCTION_INTEGRATIONS", "false").lower() == "true"
            if not allow_prod:
                raise PermissionError(
                    f"Production mode for '{self.name}' is blocked by deployment safety policy. "
                    "Set ALLOW_PRODUCTION_INTEGRATIONS=true and configure verified provider credentials in environment secrets."
                )
            # Verify required configuration keys exist
            missing = [k for k in self.required_config_keys if not os.getenv(k)]
            if missing:
                raise ValueError(
                    f"Cannot activate PRODUCTION for '{self.name}'. Missing server-side credentials: {', '.join(missing)}"
                )

        self.mode = new_mode
        self.last_error = None

    def simulate_failure(self, scenario: Optional[str]):
        """Inject failure scenario for resilience and negative test verification."""
        self.simulated_failure = scenario if scenario and scenario != "clear" else None

    def clear_simulation(self):
        """Resets any injected failure scenario."""
        self.simulated_failure = None

    def test_connection(self) -> Dict[str, Any]:
        """Report a local simulation or an unavailable provider connection."""
        start = time.time()
        self.last_health_check = datetime.now(timezone.utc)

        if self.simulated_failure == "upstream_500":
            self.last_error = f"Simulated upstream failure for {self.name}."
            return {
                "success": False,
                "status": AdapterHealthStatus.DEGRADED.value,
                "latency_ms": round((time.time() - start) * 1000, 2),
                "is_simulated": True,
                "error": self.last_error
            }

        if self.mode in [IntegrationMode.MOCK, IntegrationMode.SANDBOX]:
            self.last_error = None
            return {
                "success": False,
                "status": AdapterHealthStatus.SIMULATED.value,
                "latency_ms": round((time.time() - start) * 1000, 2),
                "is_simulated": True,
                "message": "SIMULATED — no external provider connection was attempted."
            }

        self.last_error = f"No production provider client is configured for {self.name}."
        return {
            "success": False,
            "status": AdapterHealthStatus.UNAVAILABLE.value,
            "latency_ms": round((time.time() - start) * 1000, 2),
            "error": self.last_error
        }
    def get_status(self) -> Dict[str, Any]:
        """Returns safe public status dictionary without exposing secret values."""
        if self.last_error:
            health = AdapterHealthStatus.DEGRADED
        elif self.mode == IntegrationMode.PRODUCTION:
            health = AdapterHealthStatus.NOT_CONFIGURED
        else:
            health = AdapterHealthStatus.SIMULATED

        return {
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "mode": self.mode.value,
            "health": health.value,
            "latency_ms": self.connection_latency_ms,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "last_error": self.last_error,
            "simulated_failure": self.simulated_failure,
            "is_test_mode": self.mode in [IntegrationMode.MOCK, IntegrationMode.SANDBOX],
            "required_configs": [
                {"key": k, "configured": bool(os.getenv(k))}
                for k in self.required_config_keys
            ]
        }
