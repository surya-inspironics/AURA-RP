import time
from typing import Dict, Any, List, Optional

class LoanServicingEngine:
    """
    Core LMS Servicing Engine for Gold Loans.
    Manages daily interest accrual, double-entry financial ledger accounting,
    and the strict repayment waterfall (Penalties -> Overdue Interest -> Current Interest -> Principal).
    """
    @classmethod
    def calculate_daily_interest_accrual(
        cls,
        principal_paise: int,
        annual_rate_pct: float,
        days: int = 1
    ) -> int:
        """
        Calculates simple daily interest in integer paise:
        daily_interest = (principal * rate) / (365 * 100) * days
        """
        if principal_paise <= 0 or annual_rate_pct <= 0:
            return 0
        accrual_paise = int((principal_paise * (annual_rate_pct / 100.0) / 365.0) * days)
        return accrual_paise

    @classmethod
    def allocate_repayment_waterfall(
        cls,
        payment_amount_paise: int,
        current_principal_paise: int,
        accrued_interest_paise: int,
        overdue_interest_paise: int = 0,
        penal_charges_paise: int = 0
    ) -> Dict[str, Any]:
        """
        Applies strict Indian lending waterfall allocation:
        Priority 1: Penal Charges / Bounce Fees
        Priority 2: Overdue Interest
        Priority 3: Current Accrued Interest
        Priority 4: Principal Balance
        """
        if payment_amount_paise <= 0:
            raise ValueError("Payment amount must be positive integer paise")

        remaining = payment_amount_paise

        # 1. Penal Charges
        allocated_penal = min(remaining, penal_charges_paise)
        remaining -= allocated_penal
        rem_penal = penal_charges_paise - allocated_penal

        # 2. Overdue Interest
        allocated_overdue = min(remaining, overdue_interest_paise)
        remaining -= allocated_overdue
        rem_overdue = overdue_interest_paise - allocated_overdue

        # 3. Current Accrued Interest
        allocated_interest = min(remaining, accrued_interest_paise)
        remaining -= allocated_interest
        rem_interest = accrued_interest_paise - allocated_interest

        # 4. Principal Balance
        allocated_principal = min(remaining, current_principal_paise)
        remaining -= allocated_principal
        rem_principal = current_principal_paise - allocated_principal

        # Any surplus beyond total debt
        surplus_credit_paise = remaining
        is_fully_paid = (rem_principal == 0 and rem_interest == 0 and rem_overdue == 0 and rem_penal == 0)

        total_outstanding_after = rem_principal + rem_interest + rem_overdue + rem_penal

        return {
            "payment_received_paise": payment_amount_paise,
            "allocated_penal_charges_paise": allocated_penal,
            "allocated_overdue_interest_paise": allocated_overdue,
            "allocated_current_interest_paise": allocated_interest,
            "allocated_principal_paise": allocated_principal,
            "surplus_advance_paise": surplus_credit_paise,
            "remaining_penal_paise": rem_penal,
            "remaining_overdue_interest_paise": rem_overdue,
            "remaining_current_interest_paise": rem_interest,
            "remaining_principal_paise": rem_principal,
            "new_total_outstanding_paise": total_outstanding_after,
            "is_loan_fully_cleared": is_fully_paid
        }
