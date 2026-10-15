import uuid
from typing import Dict, Any
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode

class AuctionAdapter(BaseAdapter):
    """In-memory auction simulator; it does not list collateral or settle real bids."""
    def __init__(self):
        super().__init__(
            name="E-Auction & Recovery Gateway",
            category="Collections & Recovery",
            description="Collateral E-Auction Integration with Reserve Price Controls and Borrower Surplus Settlement",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["EAUCTION_PORTAL_KEY", "AUCTION_SETTLEMENT_ESCROW"]
        )

    def settle_auction(
        self,
        loan_id: str,
        total_outstanding_paise: int,
        net_gold_weight_mg: int,
        current_gold_rate_per_mg_paise: int
    ) -> Dict[str, Any]:
        """Calculates illustrative auction values without initiating a real auction."""
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production auction settlement is unavailable: no auction provider is configured")

        if self.simulated_failure == "timeout":
            raise TimeoutError("E-Auction gateway timed out")

        # Reserve price = Net weight * Market rate per mg
        reserve_price_paise = net_gold_weight_mg * current_gold_rate_per_mg_paise

        # Winning bid simulation (typically 102% of reserve price in competitive auctions)
        winning_bid_paise = int(reserve_price_paise * 1.02)

        surplus_refund_paise = max(0, winning_bid_paise - total_outstanding_paise)
        deficit_paise = max(0, total_outstanding_paise - winning_bid_paise)

        return {
            "loan_id": loan_id,
            "simulation_id": f"sim_auc_{uuid.uuid4().hex[:8]}",
            "reserve_price_paise": reserve_price_paise,
            "winning_bid_paise": winning_bid_paise,
            "total_outstanding_paise": total_outstanding_paise,
            "surplus_refund_to_borrower_paise": surplus_refund_paise,
            "deficit_recovery_paise": deficit_paise,
            "status": "SIMULATED",
            "is_test_mode": True,
            "is_simulated": True,
            "provider_confirmed": False,
            "message": "SIMULATED — NO AUCTION OR SETTLEMENT OCCURRED"
        }
