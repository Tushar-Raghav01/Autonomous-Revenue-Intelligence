from pydantic import BaseModel
from typing import Literal
from datetime import datetime


# ==========================================
# OUTCOME RESULT
# ==========================================

class RecoveryOutcome(BaseModel):
    status: Literal[
        "RECOVERED",
        "NOT_RECOVERED",
        "UNCERTAIN"
    ]

    amount_recovered: float
    recovery_success: bool
    message: str
    evaluated_at: str


# ==========================================
# OUTCOME EVALUATOR
# ==========================================

def evaluate_outcome(
    action_success: bool,
    payment_success: bool,
    amount: float
) -> RecoveryOutcome:

    evaluated_at = datetime.now().isoformat()

    # --------------------------------------
    # PAYMENT RECOVERED
    # --------------------------------------

    if action_success and payment_success:

        return RecoveryOutcome(
            status="RECOVERED",
            amount_recovered=amount,
            recovery_success=True,
            message=(
                f"Payment successfully recovered. "
                f"₹{amount} recovered."
            ),
            evaluated_at=evaluated_at
        )

    # --------------------------------------
    # ACTION EXECUTED BUT PAYMENT FAILED
    # --------------------------------------

    if action_success and not payment_success:

        return RecoveryOutcome(
            status="NOT_RECOVERED",
            amount_recovered=0.0,
            recovery_success=False,
            message=(
                "Recovery action was executed, "
                "but payment was not recovered."
            ),
            evaluated_at=evaluated_at
        )

    # --------------------------------------
    # ACTION RESULT UNKNOWN
    # --------------------------------------

    return RecoveryOutcome(
        status="UNCERTAIN",
        amount_recovered=0.0,
        recovery_success=False,
        message=(
            "Action result could not be confirmed. "
            "Reconciliation required."
        ),
        evaluated_at=evaluated_at
    )


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    # Simulate successful recovery

    result = evaluate_outcome(
        action_success=True,
        payment_success=True,
        amount=500.0
    )

    print("Outcome Result:")
    print(result.model_dump())