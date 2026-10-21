import time
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode

logger = logging.getLogger(__name__)

# USD/INR approximate conversion (updated periodically; production should use a forex feed)
_APPROX_USD_INR = 84.0

# Fallback rates in paise per gram if the live API is unavailable
_FALLBACK_RATES_PAISE = {
    "24K": 750000,   # ~7,500 INR/g
    "22K": 687000,   # ~6,870 INR/g (916/999 * 24K rate)
    "18K": 562500,   # ~5,625 INR/g (750/999 * 24K rate)
}


class GoldRateAdapter(BaseAdapter):
    """
    Fetches live gold spot prices from the free gold-api.com API (no key required).
    Falls back to static illustrative rates when the API is unreachable.
    Cache TTL: 10 minutes to respect rate limits.
    """
    _LIVE_API_URL = "https://www.goldapi.io/api/XAU/INR"
    _OROPOCKET_URL = "https://data.oropocket.com/gold-silver.json"
    _CACHE_TTL_SECONDS = 600  # 10 minutes

    def __init__(self):
        super().__init__(
            name="Gold Rate Feed (Live)",
            category="Valuation & Market Data",
            description="Live gold spot via gold-api.com (free tier) with static fallback",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=[]
        )
        self._lock = threading.Lock()
        self._cached_rates: Dict[str, int] = {}   # paise per gram
        self._cache_time: float = 0.0
        self._rate_version: str = "LIVE-PENDING"
        self._last_source: str = "NONE"

    # ------------------------------------------------------------------
    # Live fetch helpers
    # ------------------------------------------------------------------

    def _fetch_oropocket(self) -> Dict[str, int]:
        """OroPocket free endpoint returns INR buy/sell rates directly."""
        resp = httpx.get(self._OROPOCKET_URL, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        # Response shape: {"gold": {"buy": 7200, "sell": 7100, ...}, ...}
        gold = data.get("gold") or data.get("Gold") or {}
        buy_price_per_gram = float(gold.get("buy") or gold.get("rate_buy") or 0)
        if buy_price_per_gram <= 0:
            raise ValueError("OroPocket: unexpected response shape")
        rate_24k_paise = int(buy_price_per_gram * 100)
        return self._derive_all_karats(rate_24k_paise), "oropocket.com"

    def _fetch_goldpricez(self) -> tuple:
        """goldpricez.com free API returns USD; we convert using approximate forex."""
        resp = httpx.get(
            "https://goldpricez.com/api/rates/currency/inr/measure/gram",
            timeout=5.0
        )
        resp.raise_for_status()
        data = resp.json()
        # Shape: {"1g": {"24K": "7230.45", ...}}
        rates_1g = data.get("1g") or data.get("rates_1g") or {}
        price_24k_str = str(rates_1g.get("24K") or rates_1g.get("24k") or "0").replace(",", "")
        price_24k = float(price_24k_str)
        if price_24k <= 0:
            raise ValueError("goldpricez: unexpected response shape")
        rate_24k_paise = int(price_24k * 100)
        return self._derive_all_karats(rate_24k_paise), "goldpricez.com"

    @staticmethod
    def _derive_all_karats(rate_24k_paise: int) -> Dict[str, int]:
        return {
            "24K": rate_24k_paise,
            "22K": int(rate_24k_paise * 916 // 999),
            "18K": int(rate_24k_paise * 750 // 999),
        }

    def _refresh_cache(self) -> None:
        """Try multiple free providers in order; populate cache on first success."""
        if not _HTTPX_AVAILABLE:
            return
        providers = [self._fetch_oropocket, self._fetch_goldpricez]
        for provider in providers:
            try:
                rates, source = provider()
                with self._lock:
                    self._cached_rates = rates
                    self._cache_time = time.time()
                    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    self._rate_version = f"LIVE-{ts}"
                    self._last_source = source
                logger.info("Gold rates refreshed from %s: 24K=%.0f INR/g", source, rates["24K"] / 100)
                return
            except Exception as exc:
                logger.warning("Gold rate provider %s failed: %s", provider.__name__, exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_gold_rate(self, karat: str = "24K") -> Dict[str, Any]:
        """
        Returns gold rate per gram and per milligram in integer paise.
        Fetches live data with a 10-minute cache; falls back to static rates.
        """
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError(
                "Production gold rates are unavailable: no market-data provider is configured."
            )

        clean_karat = karat.upper()
        if clean_karat not in ("24K", "22K", "18K"):
            raise ValueError(f"Unsupported gold karat '{karat}'. Supported: 24K, 22K, 18K")

        if self.simulated_failure == "stale_rates":
            published_at = time.time() - (86400 * 2)
            rate_per_gram_paise = _FALLBACK_RATES_PAISE[clean_karat]
            is_stale, source = True, "STATIC_FALLBACK"
        else:
            # Refresh if cache expired
            age = time.time() - self._cache_time
            if age > self._CACHE_TTL_SECONDS or not self._cached_rates:
                self._refresh_cache()

            with self._lock:
                if self._cached_rates:
                    rate_per_gram_paise = self._cached_rates[clean_karat]
                    published_at = self._cache_time
                    source = self._last_source
                    is_stale = False
                else:
                    rate_per_gram_paise = _FALLBACK_RATES_PAISE[clean_karat]
                    published_at = time.time()
                    source = "STATIC_FALLBACK"
                    is_stale = False

        rate_version = self._rate_version if not is_stale else "STALE"
        rate_per_mg_paise = rate_per_gram_paise // 1000

        return {
            "karat": clean_karat,
            "rate_version": rate_version,
            "rate_per_gram_paise": rate_per_gram_paise,
            "rate_per_gram_inr": round(rate_per_gram_paise / 100, 2),
            "rate_per_mg_paise": rate_per_mg_paise,
            "published_at": published_at,
            "is_stale": is_stale,
            "source": source,
            "is_live": source not in ("STATIC_FALLBACK", "NONE", "SIMULATED_SAMPLE"),
            "is_test_mode": False,
            "is_simulated": source in ("STATIC_FALLBACK",),
            "provider_verified": source not in ("STATIC_FALLBACK", "NONE"),
        }

    def get_all_rates(self) -> Dict[str, Any]:
        """Returns current rates for all supported karats."""
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError(
                "Production gold rates are unavailable: no market-data provider is configured."
            )

        age = time.time() - self._cache_time
        if age > self._CACHE_TTL_SECONDS or not self._cached_rates:
            self._refresh_cache()
        with self._lock:
            rates = dict(self._cached_rates) if self._cached_rates else dict(_FALLBACK_RATES_PAISE)
            source = self._last_source if self._cached_rates else "STATIC_FALLBACK"
        return {
            "rates": {k: {"paise_per_gram": v, "inr_per_gram": round(v / 100, 2)} for k, v in rates.items()},
            "source": source,
            "is_live": source not in ("STATIC_FALLBACK", "NONE"),
            "rate_version": self._rate_version,
            "cached_at": self._cache_time,
            "cache_age_seconds": int(time.time() - self._cache_time),
        }
