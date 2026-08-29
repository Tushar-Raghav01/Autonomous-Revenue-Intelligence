import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

CSV_PATH = BASE_DIR.parent / "ml" / "events.csv"

df = pd.read_csv(CSV_PATH)


ML_FEATURES = [
    "amount",
    "customer_age_days",
    "prev_payment_count",
    "prev_success_count",
    "prev_failure_count",
    "historical_success_rate",
    "days_since_last_success",
    "customer_activity_score",
    "attempt_number",
    "hours_since_failure",
    "invoice_age_days",
    "prev_recovery_actions",
    "prev_recovery_outcomes",
    "event_type",
    "failure_category",
    "payment_method",
    "gateway_provider",
    "merchant_category",
    "user_device"
]


def build_ml_features(event_data: dict):

    customer_id = event_data["customer_id"]

    customer_row = df[df["customer_id"] == customer_id]

    if customer_row.empty:
        raise ValueError(
            f"Customer {customer_id} not found in events.csv"
        )

    row = customer_row.iloc[-1]

    features = {
        # Current event
        "amount": event_data["amount"],
        "event_type": event_data["event_type"],

        # Historical customer features
        "customer_age_days": row["customer_age_days"],
        "prev_payment_count": row["prev_payment_count"],
        "prev_success_count": row["prev_success_count"],
        "prev_failure_count": row["prev_failure_count"],
        "historical_success_rate": row["historical_success_rate"],
        "days_since_last_success": row["days_since_last_success"],
        "customer_activity_score": row["customer_activity_score"],
        "hours_since_failure": row["hours_since_failure"],
        "invoice_age_days": row["invoice_age_days"],
        "prev_recovery_actions": row["prev_recovery_actions"],
        "prev_recovery_outcomes": row["prev_recovery_outcomes"],
        "merchant_category": row["merchant_category"],

        # Current request values
        "attempt_number": (
            event_data["attempt_number"]
            if event_data.get("attempt_number") is not None
            else row["attempt_number"]
        ),

        "failure_category": (
            event_data["failure_category"]
            if event_data.get("failure_category") is not None
            else row["failure_category"]
        ),

        "payment_method": (
            event_data["payment_method"]
            if event_data.get("payment_method") is not None
            else row["payment_method"]
        ),

        "gateway_provider": (
            event_data["gateway_provider"]
            if event_data.get("gateway_provider") is not None
            else row["gateway_provider"]
        ),

        "user_device": (
            event_data["user_device"]
            if event_data.get("user_device") is not None
            else row["user_device"]
        ),
    }

    return features