from pydantic import BaseModel
from typing import Literal
from datetime import datetime

from razorpay_adapter import RazorpayAdapter


# ==========================================
# EXECUTION RESULT
# ==========================================

class ExecutionResult(BaseModel):
    success: bool
    action_type: str
    status: Literal[
        "EXECUTED",
        "BLOCKED",
        "FAILED"
    ]
    message: str
    executed_at: str
    provider_response: dict | None = None


# ==========================================
# RAZORPAY ADAPTER
# ==========================================

razorpay = RazorpayAdapter()


# ==========================================
# ACTION EXECUTOR
# ==========================================

def execute_action(
    action_type: Literal[
        "IMMEDIATE_RETRY",
        "DELAYED_RETRY",
        "REMINDER",
        "ESCALATE",
        "NO_ACTION"
    ],
    amount: float,
    customer_id: str,
    delay_minutes: int = 0,
    payment_id: str = "pay_test_12345"
) -> ExecutionResult:

    executed_at = datetime.now().isoformat()

    try:

        # ==================================
        # IMMEDIATE RETRY
        # ==================================

        if action_type == "IMMEDIATE_RETRY":

            response = razorpay.retry_payment(
                payment_id=payment_id,
                delay_minutes=0
            )

        # ==================================
        # DELAYED RETRY
        # ==================================

        elif action_type == "DELAYED_RETRY":

            response = razorpay.retry_payment(
                payment_id=payment_id,
                delay_minutes=delay_minutes
            )

        # ==================================
        # REMINDER
        # ==================================

        elif action_type == "REMINDER":

            response = razorpay.send_reminder(
                customer_id=customer_id,
                amount=amount
            )

        # ==================================
        # ESCALATE
        # ==================================

        elif action_type == "ESCALATE":

            response = razorpay.escalate(
                customer_id=customer_id,
                amount=amount
            )

        # ==================================
        # NO ACTION
        # ==================================

        elif action_type == "NO_ACTION":

            return ExecutionResult(
                success=True,
                action_type=action_type,
                status="EXECUTED",
                message="No recovery action required.",
                executed_at=executed_at,
                provider_response=None
            )

        else:

            return ExecutionResult(
                success=False,
                action_type=action_type,
                status="FAILED",
                message="Unknown recovery action.",
                executed_at=executed_at,
                provider_response=None
            )

        # ==================================
        # PROVIDER RESPONSE
        # ==================================

        if response.get("success"):

            return ExecutionResult(
                success=True,
                action_type=action_type,
                status="EXECUTED",
                message=response.get(
                    "message",
                    "Action executed successfully."
                ),
                executed_at=executed_at,
                provider_response=response
            )

        return ExecutionResult(
            success=False,
            action_type=action_type,
            status="FAILED",
            message=response.get(
                "message",
                "Razorpay action failed."
            ),
            executed_at=executed_at,
            provider_response=response
        )

    except Exception as e:

        return ExecutionResult(
            success=False,
            action_type=action_type,
            status="FAILED",
            message=f"Action execution failed: {str(e)}",
            executed_at=executed_at,
            provider_response=None
        )


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    result = execute_action(
        action_type="DELAYED_RETRY",
        amount=500.0,
        customer_id="CUST_2891",
        delay_minutes=30,
        payment_id="pay_test_12345"
    )

    print("\n========== EXECUTION RESULT ==========")

    print(
        result.model_dump()
    )