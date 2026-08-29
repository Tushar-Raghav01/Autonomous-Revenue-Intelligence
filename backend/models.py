from sqlalchemy import Column, String, Integer, DateTime, Float, Text
from datetime import datetime, timezone
from backend.database import Base


class RevenueEvent(Base):
    __tablename__ = "revenue_events"

    id = Column(Integer, primary_key=True, index=True)

    event_type = Column(String, nullable=False)
    amount = Column(Float, nullable=False)

    payment_id = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)

    customer_id = Column(String, nullable=False)

    status = Column(
        String,
        nullable=False,
        default="DETECTED"
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # ==========================================
    # ML / PAYMENT CONTEXT
    # ==========================================

    failure_category = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    gateway_provider = Column(String, nullable=True)
    user_device = Column(String, nullable=True)
    attempt_number = Column(Integer, nullable=True)

    # ==========================================
    # ML PREDICTION
    # ==========================================

    recovery_probability = Column(Float, nullable=True)
    predicted_recovered = Column(Integer, nullable=True)
    priority = Column(
        String,
        nullable=True
    )

    # ==========================================
    # AI RECOVERY RESULT
    # ==========================================

    recovery_result = Column(
        Text,
        nullable=True
    )