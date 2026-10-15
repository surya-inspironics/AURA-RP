import time
from typing import Dict, Any
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode

class GoldRateAdapter(BaseAdapter):
    """Static development rates for integer valuation tests; not an IBJA feed."""
    def __init__(self):
        super().__init__(
            name="Gold Rate Simulator",
            category="Valuation & Market Data",
            description="Static illustrative rates; no market-data provider is connected",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["IBJA_FEED_API_KEY", "GOLD_FEED_URL"]
        )
        # Rates stored in paise per gram (100 paise = 1 INR)
        # e.g., 7250 INR/g = 725,000 paise/g
        self.latest_rates = {
            "24K": 725000,  # 7,250 INR per gram (pure 999 fineness)
            "22K": 664100,  # 6,641 INR per gram (916 fineness)
            "18K": 543750,  # 5,437.50 INR per gram (750 fineness)
        }
        self.last_published_timestamp = time.time()
        self.rate_version = "SIM-RATE-2026-10-15"

    def get_gold_rate(self, karat: str = "24K") -> Dict[str, Any]:
        """
        Returns gold rate per gram and per milligram in integer paise.
        Rate per mg = rate_per_gram / 1000.
        """
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production gold rates are unavailable: no market-data provider is configured")

        if self.simulated_failure == "stale_rates":
            # Simulate rates older than 24h
            published_at = time.time() - (86400 * 2)
            is_stale = True
        else:
            published_at = self.last_published_timestamp
            is_stale = (time.time() - published_at) > 86400

        clean_karat = karat.upper()
        if clean_karat not in self.latest_rates:
            raise ValueError(f"Unsupported gold karat '{karat}'. Supported: 24K, 22K, 18K")

        rate_per_gram_paise = self.latest_rates[clean_karat]
        # Integer division for paise per milligram with high precision: 1 mg = rate_per_gram / 1000
        rate_per_mg_paise = rate_per_gram_paise // 1000

        return {
            "karat": clean_karat,
            "rate_version": self.rate_version,
            "rate_per_gram_paise": rate_per_gram_paise,
            "rate_per_gram_inr": rate_per_gram_paise / 100.0,
            "rate_per_mg_paise": rate_per_mg_paise,
            "published_at": published_at,
            "is_stale": is_stale,
            "source": "SIMULATED_SAMPLE",
            "is_test_mode": True,
            "is_simulated": True,
            "provider_verified": False
        }
