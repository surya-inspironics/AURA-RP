import time
import uuid
from typing import Dict, Any, Optional

class CustodyService:
    """
    Service managing Vault Custody Packets for Pledged Gold Collateral.
    Enforces dual-control maker-checker sealing: Two distinct branch custodians must sign.
    In-memory development simulator; it cannot verify or change physical custody.
    """
    def __init__(self):
        self.packets: Dict[str, Dict[str, Any]] = {}

    def seal_packet(
        self,
        loan_id: str,
        custodian_1_id: str,
        custodian_2_id: str,
        vault_rack_id: str,
        item_count: int,
        net_weight_mg: int
    ) -> Dict[str, Any]:
        """Creates a simulated packet record; no physical seal or custody event occurs."""
        if not custodian_1_id or not custodian_2_id:
            raise PermissionError("Vault packet sealing requires dual-control custody authorization")

        if custodian_1_id == custodian_2_id:
            raise PermissionError("Custodian 1 and Custodian 2 must be different branch officers")

        barcode = f"AURA-PKT-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        packet_record = {
            "barcode": barcode,
            "loan_id": loan_id,
            "vault_rack_id": vault_rack_id,
            "item_count": item_count,
            "net_weight_mg": net_weight_mg,
            "custodian_1_id": custodian_1_id,
            "custodian_2_id": custodian_2_id,
            "status": "SIMULATED_NOT_PHYSICALLY_SEALED",
            "sealed_at": time.time(),
            "unsealed_at": None,
            "released_to": None,
            "is_simulated": True,
            "physical_custody_confirmed": False,
            "message": "SIMULATED — NO PHYSICAL CUSTODY EVENT RECORDED"
        }
        self.packets[barcode] = packet_record
        return packet_record

    def release_collateral(
        self,
        barcode: str,
        releasing_custodian_id: str,
        witness_custodian_id: str,
        borrower_signature_ack: bool,
        is_loan_fully_paid: bool
    ) -> Dict[str, Any]:
        """Returns a simulated release result; it cannot release physical collateral."""
        if barcode not in self.packets:
            raise KeyError(f"Vault packet '{barcode}' not found")

        if not is_loan_fully_paid:
            raise PermissionError("Collateral cannot be released: Loan balance has not been fully cleared")

        if releasing_custodian_id == witness_custodian_id:
            raise PermissionError("Release requires two distinct custodians for unsealing verification")

        if not borrower_signature_ack:
            raise PermissionError("Borrower physical handover receipt and digital signature required")

        packet = self.packets[barcode]
        packet["status"] = "SIMULATED_NOT_PHYSICALLY_RELEASED"
        packet["is_simulated"] = True
        packet["physical_custody_confirmed"] = False
        packet["message"] = "SIMULATED — NO PHYSICAL COLLATERAL WAS RELEASED"
        return packet
