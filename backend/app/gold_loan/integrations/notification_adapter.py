import time
import uuid
from typing import Dict, Any
from backend.app.gold_loan.integrations.base import BaseAdapter, IntegrationMode

class NotificationAdapter(BaseAdapter):
    """
    Adapter for Multi-Channel Borrower Notifications (SMS, Email, WhatsApp).
    Supports transactional alerts for loan disbursals, repayment confirmations,
    and regulatory margin call notices (7-day, 14-day, 21-day).
    """
    def __init__(self):
        super().__init__(
            name="Borrower Notifications (SMS / WhatsApp)",
            category="Communications",
            description="DLT-Registered Transactional SMS, WhatsApp Business, and Email Alerts",
            default_mode=IntegrationMode.SANDBOX,
            required_config_keys=["SMS_GATEWAY_AUTH", "WHATSAPP_BUSINESS_TOKEN"]
        )
        self.sent_messages = []

    def send_notification(
        self,
        recipient: str,
        channel: str,
        template_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Records a local simulation; no message is sent to a recipient."""
        if self.mode == IntegrationMode.PRODUCTION:
            raise RuntimeError("Production notifications are unavailable: no messaging provider is configured")

        if self.simulated_failure == "timeout":
            raise TimeoutError("Notification SMS/WhatsApp gateway timed out")

        msg_id = f"msg_{uuid.uuid4().hex[:10]}"
        record = {
            "message_id": msg_id,
            "recipient": recipient,
            "channel": channel.upper(),
            "template_id": template_id,
            "parameters": parameters,
            "status": "SIMULATED_NOT_SENT",
            "timestamp": time.time(),
            "is_test_mode": True,
            "is_simulated": True,
            "provider_confirmed": False,
            "message": "SIMULATED — NO NOTIFICATION SENT"
        }
        self.sent_messages.append(record)
        return record
