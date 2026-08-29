import os
import json
import time
import requests
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# =========================================================
# ENVIRONMENT
# =========================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "").strip()


# =========================================================
# STRUCTURED RESPONSE SCHEMA
# =========================================================

class AgentRecommendation(BaseModel):
    action_type: str = Field(
        ...,
        description=(
            "Chosen action: IMMEDIATE_RETRY, DELAYED_RETRY, "
            "PAYMENT_LINK_REMINDER, ESCALATE_HUMAN, NO_ACTION"
        )
    )

    recommended_delay_minutes: int = Field(
        default=0,
        ge=0
    )

    incentive_type: Optional[str] = None

    reasoning_summary: str


# =========================================================
# FALLBACK RECOMMENDATION
# =========================================================

def fallback_recommendation() -> AgentRecommendation:
    return AgentRecommendation(
        action_type="DELAYED_RETRY",
        recommended_delay_minutes=15,
        incentive_type=None,
        reasoning_summary=(
            "Recovery probability supports a delayed retry strategy."
        )
    )


# =========================================================
# MISTRAL RECOVERY STRATEGIST
# =========================================================

def generate_recommendation_mistral(
    context: dict,
    recovery_probability: float,
    model_name: str = "mistral-small-latest",
    max_retries: int = 3
) -> AgentRecommendation:

    if not MISTRAL_API_KEY:
        print("[AEROS] MISTRAL_API_KEY not configured.")
        return fallback_recommendation()

    url = "https://api.mistral.ai/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MISTRAL_API_KEY}"
    }

    system_prompt = """
You are AEROS, an AI Revenue Recovery Strategist.

Analyze the payment recovery context and select exactly one action.

Allowed actions:
- IMMEDIATE_RETRY
- DELAYED_RETRY
- PAYMENT_LINK_REMINDER
- ESCALATE_HUMAN
- NO_ACTION

Return ONLY valid JSON.

Required JSON format:
{
  "action_type": "DELAYED_RETRY",
  "recommended_delay_minutes": 15,
  "incentive_type": null,
  "reasoning_summary": "short explanation"
}
"""

    user_prompt = (
        f"Payment Context:\n"
        f"{json.dumps(context, default=str, indent=2)}\n\n"
        f"Recovery Probability: {recovery_probability}"
    )

    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "response_format": {
            "type": "json_object"
        },
        "temperature": 0.1
    }

    for attempt in range(max_retries):

        try:

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=20
            )

            if response.status_code == 200:

                data = response.json()

                content = (
                    data
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                )

                if not content:
                    raise ValueError(
                        "Mistral returned empty response"
                    )

                parsed = json.loads(content)

                return AgentRecommendation.model_validate(parsed)

            print(
                f"[AEROS] Mistral HTTP {response.status_code}: "
                f"{response.text[:300]}"
            )

        except Exception as e:

            print(
                f"[AEROS] Mistral attempt "
                f"{attempt + 1}/{max_retries} failed: {e}"
            )

            time.sleep(0.5)

    return fallback_recommendation()


# =========================================================
# GEMINI RECOVERY STRATEGIST
# =========================================================

def generate_recommendation_gemini(
    context: dict,
    recovery_probability: float
) -> AgentRecommendation:

    if not GEMINI_API_KEY:
        print("[AEROS] GEMINI_API_KEY not configured.")
        return fallback_recommendation()

    models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite"
    ]

    system_prompt = """
You are AEROS, an AI Revenue Recovery Strategist.

Analyze the payment information and choose the best recovery action.

Allowed actions:
IMMEDIATE_RETRY
DELAYED_RETRY
PAYMENT_LINK_REMINDER
ESCALATE_HUMAN
NO_ACTION

Return ONLY valid JSON in this exact structure:

{
  "action_type": "DELAYED_RETRY",
  "recommended_delay_minutes": 15,
  "incentive_type": null,
  "reasoning_summary": "short explanation"
}
"""

    user_prompt = (
        f"{system_prompt}\n\n"
        f"Payment Context:\n"
        f"{json.dumps(context, default=str, indent=2)}\n\n"
        f"Recovery Probability: {recovery_probability}"
    )

    for model in models:

        try:

            url = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{model}:generateContent"
                f"?key={GEMINI_API_KEY}"
            )

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": user_prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }

            response = requests.post(
                url,
                json=payload,
                timeout=20
            )

            if response.status_code != 200:

                print(
                    f"[AEROS] Gemini {model} HTTP "
                    f"{response.status_code}: "
                    f"{response.text[:300]}"
                )

                continue

            data = response.json()

            candidates = data.get("candidates", [])

            if not candidates:
                print(
                    f"[AEROS] Gemini {model} returned no candidates."
                )
                continue

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            if not parts:
                continue

            content = parts[0].get("text")

            if not content:
                continue

            parsed = json.loads(content)

            return AgentRecommendation.model_validate(parsed)

        except Exception as e:

            print(
                f"[AEROS] Gemini {model} error: {e}"
            )

    # Gemini failed → Mistral fallback
    print("[AEROS] Gemini unavailable. Trying Mistral...")

    return generate_recommendation_mistral(
        context,
        recovery_probability
    )


# =========================================================
# MAIN RECOVERY STRATEGIST
# =========================================================

def generate_recommendation(
    context: dict,
    recovery_probability: float
) -> AgentRecommendation:

    """
    Main AI recovery engine.

    Priority:
    1. Gemini
    2. Mistral
    3. Safe fallback
    """

    result = generate_recommendation_gemini(
        context,
        recovery_probability
    )

    return result


# =========================================================
# AEROS CHAT ASSISTANT
# =========================================================

def chat_with_aeros(user_message: str) -> str:

    if not user_message or not user_message.strip():

        return (
            "Please enter a message. "
            "I'm AEROS, your AI Revenue Recovery Assistant."
        )

    user_message = user_message.strip()

    now_str = time.strftime(
        "%A, %d %B %Y, %I:%M %p"
    )

    system_prompt = f"""
You are AEROS, the intelligent AI assistant
inside Razorpay's AI Revenue Recovery Operating System.

Current date and time:
{now_str}

Project:
AEROS is an AI Revenue Recovery platform.

It uses:
- XGBoost ML
- Recovery probability prediction
- Gemini
- Mistral
- Payment failure analysis
- Recovery recommendations
- Policy guardrails
- Idempotency protection
- Synthetic transaction data

Your job is to help the operator.

You can answer:
- Revenue recovery questions
- Payment failure questions
- Customer questions
- AI/ML questions
- Project architecture questions
- Coding questions
- General questions

Respond naturally.

Use concise English or Hinglish depending on the user.

Do NOT pretend that an action was actually executed
unless the backend confirms execution.
"""

    # =====================================================
    # GEMINI CHAT
    # =====================================================

    if GEMINI_API_KEY:

        models = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite"
        ]

        for model in models:

            try:

                url = (
                    "https://generativelanguage.googleapis.com/"
                    f"v1beta/models/{model}:generateContent"
                    f"?key={GEMINI_API_KEY}"
                )

                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": (
                                        f"{system_prompt}\n\n"
                                        f"User:\n{user_message}"
                                    )
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 1000
                    }
                }

                response = requests.post(
                    url,
                    json=payload,
                    timeout=20
                )

                if response.status_code != 200:

                    print(
                        f"[AEROS] Gemini chat "
                        f"{model} HTTP "
                        f"{response.status_code}: "
                        f"{response.text[:300]}"
                    )

                    continue

                data = response.json()

                candidates = data.get("candidates", [])

                if not candidates:
                    continue

                parts = (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [])
                )

                if not parts:
                    continue

                reply = parts[0].get("text")

                if reply:
                    return reply.strip()

            except Exception as e:

                print(
                    f"[AEROS] Gemini chat error: {e}"
                )

    # =====================================================
    # MISTRAL CHAT FALLBACK
    # =====================================================

    if MISTRAL_API_KEY:

        try:

            url = "https://api.mistral.ai/v1/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {MISTRAL_API_KEY}"
            }

            payload = {
                "model": "mistral-small-latest",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "temperature": 0.4,
                "max_tokens": 1000
            }

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=20
            )

            if response.status_code == 200:

                data = response.json()

                reply = (
                    data
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content")
                )

                if reply:
                    return reply.strip()

            print(
                f"[AEROS] Mistral chat HTTP "
                f"{response.status_code}: "
                f"{response.text[:300]}"
            )

        except Exception as e:

            print(
                f"[AEROS] Mistral chat error: {e}"
            )

    # =====================================================
    # NO API AVAILABLE
    # =====================================================

    return (
        "⚠️ AEROS AI is currently unavailable.\n\n"
        "Please check that GEMINI_API_KEY or "
        "MISTRAL_API_KEY is correctly configured "
        "in your backend .env file."
    )