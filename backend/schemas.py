from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


# ==========================================
# REVENUE EVENT INPUT
# ==========================================

class RevenueEvent(BaseModel):
    event_type: Literal[
        "failed_payment",
        "checkout_abandonment",
        "overdue_invoice"
    ]

    amount: float = Field(gt=0)

    customer_id: str = Field(min_length=1)

    payment_id: str | None = None

    failure_reason: str | None = None

    # ML / AI fields
    failure_category: str | None = None
    payment_method: str | None = None
    gateway_provider: str | None = None
    user_device: str | None = None
    attempt_number: int | None = None


# ==========================================
# GUARDRAIL
# ==========================================

class GuardrailResult(BaseModel):
    allowed: bool
    reason: str


# ==========================================
# AI RECOMMENDATION
# ==========================================

class RecommendationResult(BaseModel):
    action_type: str
    recommended_delay_minutes: int
    incentive_type: str | None = None
    reasoning_summary: str


# ==========================================
# EXECUTION
# ==========================================

class ExecutionResult(BaseModel):
    success: bool
    action_type: str
    status: str
    message: str
    executed_at: datetime
    provider_response: dict


# ==========================================
# OUTCOME
# ==========================================

class OutcomeResult(BaseModel):
    status: str
    amount_recovered: float
    recovery_success: bool
    message: str
    evaluated_at: datetime


# ==========================================
# RECOVERY RESULT
# ==========================================

class RecoveryResult(BaseModel):
    success: bool

    customer_id: str | None = None
    amount: float | None = None
    recovery_probability: float | None = None

    stage: str | None = None

    recommendation: RecommendationResult
    guardrail: GuardrailResult

    execution: ExecutionResult | None = None
    outcome: OutcomeResult | None = None

    audit_logged: bool


# ==========================================
# POST /events RESPONSE
# ==========================================

class RevenueEventResponse(BaseModel):
    id: int
    event_type: str
    amount: float
    payment_id: str | None
    failure_reason: str | None
    customer_id: str
    status: str
    created_at: datetime

    # ML / AI input context
    failure_category: str | None = None
    payment_method: str | None = None
    gateway_provider: str | None = None
    user_device: str | None = None
    attempt_number: int | None = None

    # ML prediction
    recovery_probability: float
    predicted_recovered: int
    priority: str

    # Recovery pipeline
    recovery_result: RecoveryResult

    class Config:
        from_attributes = True


# ==========================================
# GET /events RESPONSE
# ==========================================
class RevenueEventListResponse(BaseModel):
    id: int
    event_type: str
    amount: float
    payment_id: str | None
    failure_reason: str | None
    customer_id: str
    status: str
    created_at: datetime

    # ==========================================
    # ML / PAYMENT CONTEXT
    # ==========================================

    failure_category: str | None = None
    payment_method: str | None = None
    gateway_provider: str | None = None
    user_device: str | None = None
    attempt_number: int | None = None

    # ==========================================
    # ML PREDICTION
    # ==========================================

    recovery_probability: float | None = None
    predicted_recovered: int | None = None
    priority: str | None = None

    # ==========================================
    # AI RECOVERY
    # ==========================================

    recovery_result: dict | None = None

    class Config:
        from_attributes = True