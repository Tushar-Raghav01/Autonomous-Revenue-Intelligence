from pydantic import BaseModel
from typing import Literal


# ==========================================
# GUARDRAIL RESULT
# ==========================================

class GuardrailResult(BaseModel):
    allowed: bool
    reason: str


# ==========================================
# MERCHANT POLICY
# ==========================================

class MerchantPolicy(BaseModel):
    max_retry_attempts: int = 2
    min_retry_interval_minutes: int = 30
    max_auto_action_amount: float = 10000.0
    max_customer_contacts_per_day: int = 2


# ==========================================
# GUARDRAIL ENGINE
# ==========================================

def validate_action(
    action_type: Literal[
        "IMMEDIATE_RETRY",
        "DELAYED_RETRY",
        "REMINDER",
        "ESCALATE",
        "NO_ACTION"
    ],
    amount: float,
    attempt_number: int,
    recommended_delay_minutes: int,
    customer_contacts_today: int,
    policy: MerchantPolicy
) -> GuardrailResult:

    # --------------------------------------
    # NO ACTION
    # --------------------------------------

    if action_type == "NO_ACTION":
        return GuardrailResult(
            allowed=True,
            reason="AI recommended no action."
        )

    # --------------------------------------
    # AMOUNT LIMIT
    # --------------------------------------

    if amount > policy.max_auto_action_amount:

        return GuardrailResult(
            allowed=False,
            reason=(
                f"Amount ₹{amount} exceeds the "
                f"auto-action limit of "
                f"₹{policy.max_auto_action_amount}."
            )
        )

    # --------------------------------------
    # RETRY LIMIT
    # --------------------------------------

    if action_type in [
        "IMMEDIATE_RETRY",
        "DELAYED_RETRY"
    ]:

        if attempt_number >= policy.max_retry_attempts:

            return GuardrailResult(
                allowed=False,
                reason=(
                    "Maximum retry attempts reached."
                )
            )

    # --------------------------------------
    # DELAY CHECK
    # --------------------------------------

    if action_type == "DELAYED_RETRY":

        if (
            recommended_delay_minutes
            < policy.min_retry_interval_minutes
        ):

            return GuardrailResult(
                allowed=False,
                reason=(
                    f"Recommended delay "
                    f"{recommended_delay_minutes} minutes "
                    f"is below the minimum allowed delay "
                    f"of {policy.min_retry_interval_minutes} minutes."
                )
            )

    # --------------------------------------
    # CUSTOMER CONTACT LIMIT
    # --------------------------------------

    if action_type == "REMINDER":

        if (
            customer_contacts_today
            >= policy.max_customer_contacts_per_day
        ):

            return GuardrailResult(
                allowed=False,
                reason=(
                    "Daily customer contact limit reached."
                )
            )

    # --------------------------------------
    # ALL CHECKS PASSED
    # --------------------------------------

    return GuardrailResult(
        allowed=True,
        reason="Action passed all merchant guardrails."
    )


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    policy = MerchantPolicy()

    result = validate_action(
        action_type="DELAYED_RETRY",
        amount=500.0,
        attempt_number=1,
        recommended_delay_minutes=30,
        customer_contacts_today=0,
        policy=policy
    )

    print("Guardrail Result:")
    print(result.model_dump())