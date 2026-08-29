import os
from dotenv import load_dotenv

load_dotenv()


# ==========================================
# RAZORPAY ADAPTER
# ==========================================

class RazorpayAdapter:

    def __init__(self):

        self.key_id = os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = os.getenv("RAZORPAY_KEY_SECRET")

        if not self.key_id or not self.key_secret:
            raise ValueError(
                "RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET "
                "not found in .env"
            )

    # ======================================
    # RETRY PAYMENT
    # ======================================

    def retry_payment(
        self,
        payment_id: str,
        delay_minutes: int = 0
    ):

        print("\n========== RAZORPAY TEST ==========")

        print(f"Payment ID: {payment_id}")
        print(f"Scheduled delay: {delay_minutes} minutes")

        # ----------------------------------
        # TEST MODE
        # ----------------------------------
        # We do NOT initiate a real payment.
        # This represents the action that the
        # recovery agent wants to perform.

        return {
            "success": True,
            "provider": "razorpay",
            "mode": "test",
            "status": "ACTION_SCHEDULED",
            "payment_id": payment_id,
            "delay_minutes": delay_minutes,
            "message": (
                "Payment retry action scheduled "
                "in Razorpay test environment."
            )
        }

    # ======================================
    # REMINDER
    # ======================================

    def send_reminder(
        self,
        customer_id: str,
        amount: float
    ):

        print("\n========== PAYMENT REMINDER ==========")

        return {
            "success": True,
            "provider": "recovery_system",
            "mode": "test",
            "status": "REMINDER_SCHEDULED",
            "customer_id": customer_id,
            "amount": amount,
            "message": "Payment reminder scheduled."
        }

    # ======================================
    # ESCALATION
    # ======================================

    def escalate(
        self,
        customer_id: str,
        amount: float
    ):

        print("\n========== MERCHANT ESCALATION ==========")

        return {
            "success": True,
            "provider": "recovery_system",
            "mode": "test",
            "status": "ESCALATED",
            "customer_id": customer_id,
            "amount": amount,
            "message": "Payment case escalated to merchant."
        }