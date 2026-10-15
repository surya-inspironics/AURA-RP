from typing import Dict, List, Any, Optional
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode
from backend.app.gold_loan.integrations.payment_gateway_adapter import PaymentGatewayAdapter
from backend.app.gold_loan.integrations.disbursal_adapter import DisbursalAdapter
from backend.app.gold_loan.integrations.identity_adapter import IdentityAdapter
from backend.app.gold_loan.integrations.credit_bureau_adapter import CreditBureauAdapter
from backend.app.gold_loan.integrations.screening_adapter import ScreeningAdapter
from backend.app.gold_loan.integrations.gold_rate_adapter import GoldRateAdapter
from backend.app.gold_loan.integrations.device_gateway_adapter import DeviceGatewayAdapter
from backend.app.gold_loan.integrations.document_signer_adapter import DocumentSignerAdapter
from backend.app.gold_loan.integrations.notification_adapter import NotificationAdapter
from backend.app.gold_loan.integrations.auction_adapter import AuctionAdapter

class AdapterRegistry:
    """
    Central Singleton Registry managing all 10 Gold Loan external integration adapters.
    Provides typed lookups, safe status reporting, mode switching,
    and failure injection for administrative control and test suites.
    """
    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}

        # Instantiate singletons
        self.payment_gateway = PaymentGatewayAdapter()
        self.disbursal = DisbursalAdapter()
        self.identity = IdentityAdapter()
        self.credit_bureau = CreditBureauAdapter()
        self.screening = ScreeningAdapter()
        self.gold_rate = GoldRateAdapter()
        self.device_gateway = DeviceGatewayAdapter()
        self.document_signer = DocumentSignerAdapter()
        self.notification = NotificationAdapter()
        self.auction = AuctionAdapter()

        self._register(self.payment_gateway)
        self._register(self.disbursal)
        self._register(self.identity)
        self._register(self.credit_bureau)
        self._register(self.screening)
        self._register(self.gold_rate)
        self._register(self.device_gateway)
        self._register(self.document_signer)
        self._register(self.notification)
        self._register(self.auction)

    def _register(self, adapter: BaseAdapter):
        self._adapters[adapter.name] = adapter

    def get_adapter(self, name: str) -> Optional[BaseAdapter]:
        # Support lookup by full name or category
        if name in self._adapters:
            return self._adapters[name]
        for a in self._adapters.values():
            if a.name.lower() == name.lower() or a.category.lower() == name.lower():
                return a
        return None

    def get_all_statuses(self) -> List[Dict[str, Any]]:
        return [adapter.get_status() for adapter in self._adapters.values()]

    def set_mode(self, adapter_name: str, mode: IntegrationMode) -> Dict[str, Any]:
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise KeyError(f"Adapter '{adapter_name}' not found in registry")
        adapter.set_mode(mode)
        return adapter.get_status()

    def simulate_failure(self, adapter_name: str, scenario: Optional[str]) -> Dict[str, Any]:
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise KeyError(f"Adapter '{adapter_name}' not found in registry")
        adapter.simulate_failure(scenario)
        return adapter.get_status()

    def test_connection(self, adapter_name: str) -> Dict[str, Any]:
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise KeyError(f"Adapter '{adapter_name}' not found in registry")
        return adapter.test_connection()

# Global singleton instance
adapter_registry = AdapterRegistry()
