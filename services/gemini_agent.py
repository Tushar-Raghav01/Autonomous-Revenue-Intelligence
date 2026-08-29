from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai
from mistralai.client import Mistral

from guardrail_engine import MerchantPolicy,validate_action

import os
import json
from typing import Optional, Literal


# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()


# ==========================================
# CUSTOM EXCEPTIONS
# ==========================================

class APIKeyNotFoundError(Exception):
    """Custom exception for missing API key."""
    pass


class ResponseValidationError(Exception):
    """Custom exception for invalid AI response."""
    pass


# ==========================================
# DATA MODELS
# ==========================================

class RecoveryAction(BaseModel):
    action_type: Literal[
        "IMMEDIATE_RETRY",
        "DELAYED_RETRY",
        "REMINDER",
        "ESCALATE",
        "NO_ACTION"
    ]

    recommended_delay_minutes: int

    incentive_type: Optional[str] = None

    reasoning_summary: str


class PaymentContext(BaseModel):
    event_type: str
    amount: float
    customer_id: str
    failure_category: str
    payment_method: str
    gateway_provider: str
    user_device: str
    attempt_number: int
    historical_success_rate: float
    prev_payment_count: int
    prev_success_count: int
    prev_failure_count: int


# ==========================================
# GEMINI CLIENT
# ==========================================

gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    raise APIKeyNotFoundError(
        "GEMINI_API_KEY not found in .env"
    )

gemini_client = genai.Client(
    api_key=gemini_api_key
)


# ==========================================
# MISTRAL CLIENT
# ==========================================

mistral_api_key = os.getenv("MISTRAL_API_KEY")

if not mistral_api_key:
    raise APIKeyNotFoundError(
        "MISTRAL_API_KEY not found in .env"
    )

mistral_client = Mistral(
    api_key=mistral_api_key
)


# ==========================================
# COMMON PROMPT
# ==========================================

def build_prompt(
    context: PaymentContext,
    recovery_probability: float
) -> str:

    return f"""
You are an AI Revenue Recovery Strategist.

Analyze the payment event and recommend the safest
and most effective recovery action.

Customer/Event Context:

{json.dumps(context.model_dump(), indent=2)}

XGBoost Recovery Probability:
{recovery_probability:.4f}

Choose exactly ONE action:

- IMMEDIATE_RETRY
- DELAYED_RETRY
- REMINDER
- ESCALATE
- NO_ACTION

Rules:

1. Recommend exactly one action.
2. Never execute a payment.
3. Consider recovery probability, failure category,
   historical behaviour, amount, and attempt number.
4. If no delay is required, use 0.
5. If no incentive is appropriate, use null.
6. Keep reasoning concise.
7. Return ONLY valid JSON.

Return JSON with exactly these keys:

{{
    "action_type": "DELAYED_RETRY",
    "recommended_delay_minutes": 30,
    "incentive_type": null,
    "reasoning_summary": "Short explanation"
}}
"""


# ==========================================
# RESPONSE CLEANER
# ==========================================

def parse_ai_response(
    raw_text: str,
    provider: str
) -> RecoveryAction:

    try:

        raw_text = raw_text.strip()

        # Remove markdown code fences if model adds them
        if raw_text.startswith("```"):

            raw_text = raw_text.replace(
                "```json", ""
            )

            raw_text = raw_text.replace(
                "```", ""
            )

            raw_text = raw_text.strip()

        result = json.loads(raw_text)

        # Same Pydantic validation for BOTH models
        return RecoveryAction.model_validate(result)

    except json.JSONDecodeError as e:

        raise ResponseValidationError(
            f"Invalid JSON response from {provider}: {str(e)}"
        )

    except Exception as e:

        raise ResponseValidationError(
            f"Invalid RecoveryAction from {provider}: {str(e)}"
        )


# ==========================================
# GEMINI GENERATOR
# ==========================================

def generate_with_gemini(
    context: PaymentContext,
    recovery_probability: float
) -> RecoveryAction:

    prompt = build_prompt(
        context,
        recovery_probability
    )

    response = gemini_client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    return parse_ai_response(
        response.text,
        "Gemini"
    )


# ==========================================
# MISTRAL FALLBACK
# ==========================================

def generate_with_mistral(
    context: PaymentContext,
    recovery_probability: float
) -> RecoveryAction:

    prompt = build_prompt(
        context,
        recovery_probability
    )

    response = mistral_client.chat.complete(
        model="mistral-small-2506",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_object"
        },
        temperature=0
    )

    raw_text = response.choices[0].message.content

    return parse_ai_response(
        raw_text,
        "Mistral"
    )


# ==========================================
# MAIN RECOMMENDATION FUNCTION
# ==========================================

def generate_recommendation(
    context: PaymentContext,
    recovery_probability: float
) -> RecoveryAction:

    # --------------------------------------
    # PRIMARY: GEMINI
    # --------------------------------------

    try:

        result = generate_with_gemini(
            context,
            recovery_probability
        )

        print("AI Provider: Gemini")

        return result

    except Exception as gemini_error:

        print(
            f"Gemini failed: {gemini_error}"
        )

        print(
            "Trying Mistral fallback..."
        )

    # --------------------------------------
    # FALLBACK: MISTRAL
    # --------------------------------------

    try:

        result = generate_with_mistral(
            context,
            recovery_probability
        )

        print(
            "AI Provider: Mistral (Fallback)"
        )

        return result

    except Exception as mistral_error:

        raise ResponseValidationError(
            "Both Gemini and Mistral failed. "
            f"Gemini error: {gemini_error}. "
            f"Mistral error: {mistral_error}"
        )


# ==========================================
# TEST RUNNER
# ==========================================
if __name__ == "__main__":

    try:

        # ======================================
        # PAYMENT CONTEXT
        # ======================================

        test_context = PaymentContext(
            event_type="failed_payment",
            amount=500.0,
            customer_id="CUST_2891",
            failure_category="bank_downtime",
            payment_method="UPI",
            gateway_provider="Razorpay",
            user_device="Mobile",
            attempt_number=1,
            historical_success_rate=0.5957,
            prev_payment_count=47,
            prev_success_count=28,
            prev_failure_count=19
        )

        # ======================================
        # XGBOOST PREDICTION
        # ======================================

        recovery_probability = 0.7846

        # ======================================
        # AI RECOMMENDATION
        # ======================================

        recommendation = generate_recommendation(
            context=test_context,
            recovery_probability=recovery_probability
        )

        print("\nAI Recommendation:")
        print(
            json.dumps(
                recommendation.model_dump(),
                indent=2
            )
        )

        # ======================================
        # GUARDRAIL POLICY
        # ======================================

        policy = MerchantPolicy(
            max_retry_attempts=2,
            min_retry_interval_minutes=30,
            max_auto_action_amount=10000.0,
            max_customer_contacts_per_day=2
        )

        # ======================================
        # GUARDRAIL VALIDATION
        # ======================================

        guardrail_result = validate_action(
            action_type=recommendation.action_type,
            amount=test_context.amount,
            attempt_number=test_context.attempt_number,
            recommended_delay_minutes=
                recommendation.recommended_delay_minutes,
            customer_contacts_today=0,
            policy=policy
        )

        # ======================================
        # FINAL DECISION
        # ======================================

        print("\nGuardrail Result:")
        print(
            json.dumps(
                guardrail_result.model_dump(),
                indent=2
            )
        )

        if guardrail_result.allowed:

            print("\n✅ ACTION APPROVED")

        else:

            print("\n❌ ACTION BLOCKED")

    except Exception as e:

        print(
            f"\nError in recovery pipeline: {e}"
        )