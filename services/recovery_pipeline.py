import json

from gemini_agent import (
    PaymentContext,
    generate_recommendation
)

from guardrail_engine import (
    MerchantPolicy,
    validate_action
)

from action_executor import (
    execute_action
)

from outcome_evaluator import (
    evaluate_outcome
)

from audit_logger import (
    log_recovery_event
)


# ==========================================
# COMPLETE RECOVERY PIPELINE
# ==========================================

def run_recovery_pipeline(
    context: PaymentContext,
    recovery_probability: float,
    customer_contacts_today: int = 0,
    payment_id: str | None = None,

    # Test mode:
    simulated_payment_success: bool = True
):
    """
    Complete Revenue Recovery Agent pipeline.

    Event
      ↓
    XGBoost probability
      ↓
    AI recommendation
      ↓
    Guardrail
      ↓
    Action execution
      ↓
    Outcome evaluation
      ↓
    Audit log
    """

    # ======================================
    # 1. AI RECOMMENDATION
    # ======================================

    recommendation = generate_recommendation(
        context=context,
        recovery_probability=recovery_probability
    )

    print("\n========== AI RECOMMENDATION ==========")

    print(
        json.dumps(
            recommendation.model_dump(),
            indent=2
        )
    )

    # ======================================
    # 2. MERCHANT POLICY
    # ======================================

    policy = MerchantPolicy(
        max_retry_attempts=2,
        min_retry_interval_minutes=30,
        max_auto_action_amount=10000.0,
        max_customer_contacts_per_day=2
    )

    # ======================================
    # 3. GUARDRAIL
    # ======================================

    guardrail_result = validate_action(
        action_type=recommendation.action_type,
        amount=context.amount,
        attempt_number=context.attempt_number,
        recommended_delay_minutes=(
            recommendation.recommended_delay_minutes
        ),
        customer_contacts_today=customer_contacts_today,
        policy=policy
    )

    print("\n========== GUARDRAIL ==========")

    print(
        json.dumps(
            guardrail_result.model_dump(),
            indent=2
        )
    )

    # ======================================
    # 4. BLOCKED
    # ======================================

    if not guardrail_result.allowed:

        print("\n❌ ACTION BLOCKED")

        # Blocked action ko bhi audit karenge
        audit = log_recovery_event(
            customer_id=context.customer_id,
            amount=context.amount,
            recommendation=recommendation.model_dump(),
            guardrail=guardrail_result.model_dump(),
            execution={
                "success": False,
                "status": "BLOCKED",
                "message": "Action blocked by guardrail."
            },
            outcome={
                "status": "UNCERTAIN",
                "amount_recovered": 0.0,
                "recovery_success": False,
                "message": "No action executed."
            },
            ai_provider="Gemini/Mistral"
        )

        return {
            "success": False,
            "stage": "guardrail",
            "recommendation": recommendation.model_dump(),
            "guardrail": guardrail_result.model_dump(),
            "execution": None,
            "outcome": None,
            "audit_logged": True
        }

    # ======================================
    # 5. ACTION EXECUTION
    # ======================================

    execution_result = execute_action(
        action_type=recommendation.action_type,
        amount=context.amount,
        payment_id=payment_id,
        customer_id=context.customer_id,
        delay_minutes=(
            recommendation.recommended_delay_minutes
        )
    )

    print("\n========== EXECUTION ==========")

    print(
        json.dumps(
            execution_result.model_dump(),
            indent=2
        )
    )

    # ======================================
    # 6. OUTCOME EVALUATION
    # ======================================

    outcome_result = evaluate_outcome(
        action_success=execution_result.success,

        # Temporary simulation.
        # Later Razorpay response se aayega.
        payment_success=simulated_payment_success,

        amount=context.amount
    )

    print("\n========== OUTCOME ==========")

    print(
        json.dumps(
            outcome_result.model_dump(),
            indent=2
        )
    )

    # ======================================
    # 7. AUDIT LOG
    # ======================================

    audit_entry = log_recovery_event(
        customer_id=context.customer_id,
        amount=context.amount,
        recommendation=recommendation.model_dump(),
        guardrail=guardrail_result.model_dump(),
        execution=execution_result.model_dump(),
        outcome=outcome_result.model_dump(),
        ai_provider="Gemini/Mistral"
    )

    print("\n========== AUDIT ==========")
    print("✅ Recovery decision logged")

    # ======================================
    # 8. FINAL RESULT
    # ======================================

    final_result = {
        "success": outcome_result.recovery_success,
        "customer_id": context.customer_id,
        "amount": context.amount,
        "recovery_probability": recovery_probability,
        "recommendation": recommendation.model_dump(),
        "guardrail": guardrail_result.model_dump(),
        "execution": execution_result.model_dump(),
        "outcome": outcome_result.model_dump(),
        "audit_logged": True
    }

    print("\n========== FINAL RESULT ==========")

    print(
        json.dumps(
            final_result,
            indent=2
        )
    )

    return final_result

