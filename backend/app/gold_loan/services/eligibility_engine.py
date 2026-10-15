from typing import Dict, Any, List, Optional
import math

class EligibilityEngine:
    """
    Authoritative, deterministic gold valuation and eligibility engine.
    Enforces pure integer and fixed-precision arithmetic (paise, milligrams, basis points).
    No floating-point rounding errors in financial limits.
    Returns complete calculation trace, all applicable limits, and the binding constraint.
    """
    # RBI Regulatory ceiling for Gold Loans
    RBI_REGULATORY_LTV_CEILING_PCT = 75

    @classmethod
    def calculate_valuation_and_eligibility(
        cls,
        items: List[Dict[str, Any]],
        gold_rate_per_gram_paise: int,
        rate_version: str,
        ltv_scheme_pct: int = 75,
        credit_limit_paise: int = 50000000,    # Default 500,000 INR
        capacity_limit_paise: int = 100000000, # Default 1,000,000 INR
        product_cap_paise: int = 250000000,    # Default 2,500,000 INR
        exposure_limit_paise: int = 500000000  # Default 5,000,000 INR
    ) -> Dict[str, Any]:
        """
        Calculates pure gold weight, market value, collateral loan limit,
        and final eligible loan amount across binding risk limits.
        """
        if gold_rate_per_gram_paise <= 0:
            raise ValueError("Gold rate must be positive integer paise")

        rate_per_mg_paise = gold_rate_per_gram_paise // 1000

        total_gross_weight_mg = 0
        total_stone_deduction_mg = 0
        total_net_weight_mg = 0
        total_fine_weight_mg = 0
        total_gold_valuation_paise = 0
        item_traces = []

        for idx, item in enumerate(items, start=1):
            gross_mg = int(item["gross_weight_mg"])
            stone_mg = int(item.get("stone_deduction_mg", 0))
            if stone_mg > gross_mg:
                raise ValueError(f"Item #{idx}: Stone deduction ({stone_mg}mg) cannot exceed gross weight ({gross_mg}mg)")

            net_mg = gross_mg - stone_mg
            purity_bps = int(item["purity_bps"]) # e.g. 9160 for 22K, 7500 for 18K
            if purity_bps <= 0 or purity_bps > 10000:
                raise ValueError(f"Item #{idx}: Purity basis points must be between 1 and 10000")

            # W_fine = W_net * (purity_bps / 10000)
            fine_mg = (net_mg * purity_bps) // 10000

            # V_item = fine_mg * rate_per_mg
            item_valuation_paise = fine_mg * rate_per_mg_paise

            total_gross_weight_mg += gross_mg
            total_stone_deduction_mg += stone_mg
            total_net_weight_mg += net_mg
            total_fine_weight_mg += fine_mg
            total_gold_valuation_paise += item_valuation_paise

            item_traces.append({
                "item_number": idx,
                "item_type": item.get("item_type", "Ornament"),
                "gross_weight_mg": gross_mg,
                "stone_deduction_mg": stone_mg,
                "net_weight_mg": net_mg,
                "purity_bps": purity_bps,
                "purity_karat": round((purity_bps / 10000.0) * 24.0, 1),
                "fine_weight_mg": fine_mg,
                "item_valuation_paise": item_valuation_paise,
                "item_valuation_inr": item_valuation_paise / 100.0
            })

        # L_collateral = V_gold * (LTV / 100)
        collateral_limit_paise = (total_gold_valuation_paise * ltv_scheme_pct) // 100

        # Compliance Check on LTV
        compliance_flag = "COMPLIANT"
        compliance_note = "Within RBI standard 75% LTV ceiling."
        if ltv_scheme_pct > cls.RBI_REGULATORY_LTV_CEILING_PCT:
            compliance_flag = "REQUIRES_COMPLIANCE_CONFIRMATION"
            compliance_note = f"Scheme LTV ({ltv_scheme_pct}%) exceeds RBI benchmark 75% ceiling. Formal regulatory waiver required."

        # Find Minimum Binding Limit
        limits = {
            "COLLATERAL_LTV_LIMIT": collateral_limit_paise,
            "BORROWER_CREDIT_LIMIT": credit_limit_paise,
            "INCOME_CAPACITY_LIMIT": capacity_limit_paise,
            "PRODUCT_SCHEME_CAP": product_cap_paise,
            "GROUP_EXPOSURE_LIMIT": exposure_limit_paise
        }

        binding_constraint = min(limits, key=limits.get)
        eligible_amount_paise = limits[binding_constraint]

        return {
            "summary": {
                "total_items": len(items),
                "total_gross_weight_mg": total_gross_weight_mg,
                "total_gross_weight_g": total_gross_weight_mg / 1000.0,
                "total_stone_deduction_mg": total_stone_deduction_mg,
                "total_net_weight_mg": total_net_weight_mg,
                "total_net_weight_g": total_net_weight_mg / 1000.0,
                "total_fine_weight_mg": total_fine_weight_mg,
                "total_fine_weight_g": total_fine_weight_mg / 1000.0,
                "total_gold_valuation_paise": total_gold_valuation_paise,
                "total_gold_valuation_inr": total_gold_valuation_paise / 100.0,
                "applied_ltv_pct": ltv_scheme_pct,
                "eligible_loan_amount_paise": eligible_amount_paise,
                "eligible_loan_amount_inr": eligible_amount_paise / 100.0,
                "binding_constraint": binding_constraint,
                "compliance_status": compliance_flag,
                "compliance_note": compliance_note,
                "rate_version": rate_version,
                "gold_rate_per_gram_paise": gold_rate_per_gram_paise
            },
            "limits_comparison_paise": limits,
            "limits_comparison_inr": {k: v / 100.0 for k, v in limits.items()},
            "item_traces": item_traces
        }
