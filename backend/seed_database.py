import os
import random
import json
import pandas as pd

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import RevenueEvent

from backend.feature_builder import build_ml_features
from backend.predictor import predictor_recovery

import sys

SERVICES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services")
)

if SERVICES_DIR not in sys.path:
    sys.path.insert(0, SERVICES_DIR)

from recovery_pipeline import run_recovery_pipeline
from gemini_agent import PaymentContext


# ==========================================
# CSV PATH
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

CSV_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "events.csv"
)


# ==========================================
# SEED DATABASE
# ==========================================

def seed_database(limit: int = 10):

    print("\n========================================")
    print("       AI REVENUE RECOVERY SEED")
    print("========================================")

    if not os.path.exists(CSV_PATH):

        print(f"❌ CSV not found: {CSV_PATH}")
        return {
            "inserted": 0,
            "skipped": 0
        }

    df = pd.read_csv(CSV_PATH)

    print(f"Total CSV records available: {len(df)}")

    # --------------------------------------
    # RANDOM EVENTS
    # --------------------------------------

    sample_size = min(limit, len(df))

    selected_rows = df.sample(
        n=sample_size,
        random_state=random.randint(
            1,
            999999
        )
    )

    db: Session = SessionLocal()

    inserted = 0
    skipped = 0

    try:

        for _, row in selected_rows.iterrows():

            payment_id = str(
                row["transaction_id"]
            )

            # ----------------------------------
            # DUPLICATE CHECK
            # ----------------------------------

            existing = (
                db.query(RevenueEvent)
                .filter(
                    RevenueEvent.payment_id
                    == payment_id
                )
                .first()
            )

            if existing:

                skipped += 1
                continue


            # ==================================
            # EVENT DATA
            # ==================================

            event_data = {

                "event_type":
                    str(row["event_type"]),

                "amount":
                    float(row["amount"]),

                "customer_id":
                    str(row["customer_id"]),

                "payment_id":
                    payment_id,

                "failure_reason":
                    str(row["failure_category"]),

                "failure_category":
                    str(row["failure_category"]),

                "payment_method":
                    str(row["payment_method"]),

                "gateway_provider":
                    str(row["gateway_provider"]),

                "user_device":
                    str(row["user_device"]),

                "attempt_number":
                    int(row["attempt_number"]),

                "historical_success_rate":
                    float(row["historical_success_rate"]),

                "prev_payment_count":
                    int(row["prev_payment_count"]),

                "prev_success_count":
                    int(row["prev_success_count"]),

                "prev_failure_count":
                    int(row["prev_failure_count"])
            }


            # ==================================
            # ML FEATURES
            # ==================================

            features = build_ml_features(
                event_data
            )

            print("\n========== FEATURES ==========")
            print(features)


            # ==================================
            # ML PREDICTION
            # ==================================

            prediction = predictor_recovery(
                features
            )

            recovery_probability = float(
                prediction[
                    "recovery_probability"
                ]
            )

            predicted_recovered = int(
                prediction[
                    "predicted_recovered"
                ]
            )

            priority = prediction[
                "priority"
            ]

            print(
                f"Recovery Probability: "
                f"{recovery_probability}"
            )

            print(
                f"Predicted Recovered: "
                f"{predicted_recovered}"
            )

            print(
                f"Priority: {priority}"
            )


            # ==================================
            # PAYMENT CONTEXT
            # ==================================

            context = PaymentContext(

                event_type=
                    event_data["event_type"],

                amount=
                    event_data["amount"],

                customer_id=
                    event_data["customer_id"],

                failure_category=
                    features["failure_category"],

                payment_method=
                    features["payment_method"],

                gateway_provider=
                    features["gateway_provider"],

                user_device=
                    features["user_device"],

                attempt_number=
                    features["attempt_number"],

                historical_success_rate=
                    features[
                        "historical_success_rate"
                    ],

                prev_payment_count=
                    features[
                        "prev_payment_count"
                    ],

                prev_success_count=
                    features[
                        "prev_success_count"
                    ],

                prev_failure_count=
                    features[
                        "prev_failure_count"
                    ]
            )


            # ==================================
            # AI RECOVERY PIPELINE
            # ==================================

            recovery_result = (
                run_recovery_pipeline(

                    context=context,

                    recovery_probability=
                        recovery_probability,

                    payment_id=
                        payment_id,

                    customer_contacts_today=0,

                    simulated_payment_success=True
                )
            )


            # ==================================
            # STATUS
            # ==================================

            if recovery_result.get(
                "outcome"
            ):

                status = recovery_result[
                    "outcome"
                ].get(
                    "status",
                    "PROCESSING"
                )

            elif recovery_result.get(
                "guardrail",
                {}
            ).get(
                "allowed"
            ) is False:

                status = "BLOCKED"

            else:

                status = "PROCESSING"


            # ==================================
            # DATABASE EVENT
            # ==================================

            event = RevenueEvent(

                event_type=
                    event_data["event_type"],

                amount=
                    event_data["amount"],

                payment_id=
                    payment_id,

                failure_reason=
                    event_data[
                        "failure_reason"
                    ],

                customer_id=
                    event_data["customer_id"],

                status=status,

                failure_category=
                    event_data[
                        "failure_category"
                    ],

                payment_method=
                    event_data[
                        "payment_method"
                    ],

                gateway_provider=
                    event_data[
                        "gateway_provider"
                    ],

                user_device=
                    event_data[
                        "user_device"
                    ],

                attempt_number=
                    event_data[
                        "attempt_number"
                    ],

                recovery_probability=
                    recovery_probability,

                predicted_recovered=
                    predicted_recovered,

                priority=
                    priority,

                recovery_result=
                    json.dumps(
                        recovery_result
                    ),

                created_at=
                    pd.to_datetime(
                        row["created_at"]
                    ).to_pydatetime()
            )


            db.add(event)

            inserted += 1

            print(
                f"✅ Added: {payment_id}"
            )


        db.commit()

        print("\n========== SEED RESULT ==========")

        print(
            f"✅ Inserted : {inserted}"
        )

        print(
            f"⏭️ Skipped  : {skipped}"
        )

        print(
            "=================================\n"
        )

        return {
            "inserted": inserted,
            "skipped": skipped
        }


    except Exception as e:

        db.rollback()

        print(
            f"❌ Seed failed: {e}"
        )

        raise


    finally:

        db.close()


# ==========================================
# DIRECT RUN
# ==========================================

if __name__ == "__main__":

    seed_database(10)