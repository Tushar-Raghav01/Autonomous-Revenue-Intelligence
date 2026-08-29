
# import sys
# import os
# import json


# # ==========================================
# # SERVICES PATH
# # ==========================================

# SERVICES_DIR = os.path.abspath(
#     os.path.join(os.path.dirname(__file__), "..", "services")
# )

# if SERVICES_DIR not in sys.path:
#     sys.path.insert(0, SERVICES_DIR)


# # ==========================================
# # FASTAPI IMPORTS
# # ==========================================

# from fastapi import FastAPI, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from sqlalchemy.orm import Session


# # ==========================================
# # SERVICES
# # ==========================================

# from recovery_pipeline import run_recovery_pipeline
# from gemini_agent import PaymentContext


# # ==========================================
# # BACKEND IMPORTS
# # ==========================================

# from backend.schemas import (
#     RevenueEventResponse,
#     RevenueEvent,
#     RevenueEventListResponse
# )

# from backend.database import (
#     Base,
#     SessionLocal,
#     engine
# )

# from backend.models import RevenueEvent as RevenueEventModel

# from backend.feature_builder import build_ml_features
# from backend.predictor import predictor_recovery

# # IMPORTANT: seed function
# from backend.seed_database import seed_database


# # ==========================================
# # DATABASE
# # ==========================================

# Base.metadata.create_all(bind=engine)


# # ==========================================
# # FASTAPI
# # ==========================================

# app = FastAPI(
#     title="AI Revenue Recovery System"
# )


# # ==========================================
# # CORS
# # ==========================================

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5173",
#         "http://127.0.0.1:5173",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ==========================================
# # DATABASE DEPENDENCY
# # ==========================================

# def get_db():
#     db = SessionLocal()

#     try:
#         yield db
#     finally:
#         db.close()


# # ==========================================
# # HEALTH CHECK
# # ==========================================

# @app.get("/health")
# def health():
#     return {
#         "status": "ok"
#     }


# # ==========================================
# # CREATE REVENUE EVENT
# # ==========================================

# @app.post(
#     "/events",
#     response_model=RevenueEventResponse
# )
# def create_event(
#     event: RevenueEvent,
#     db: Session = Depends(get_db)
# ):

#     # --------------------------------------
#     # 1. SAVE EVENT
#     # --------------------------------------

#     db_event = RevenueEventModel(
#         event_type=event.event_type,
#         amount=event.amount,
#         customer_id=event.customer_id,
#         payment_id=event.payment_id,
#         failure_reason=event.failure_reason,
#         status="DETECTED",

#         failure_category=event.failure_category,
#         payment_method=event.payment_method,
#         gateway_provider=event.gateway_provider,
#         user_device=event.user_device,
#         attempt_number=event.attempt_number
#     )

#     db.add(db_event)
#     db.commit()
#     db.refresh(db_event)

#     print("\n========== EVENT DETECTED ==========")
#     print(f"Event ID: {db_event.id}")
#     print(f"Amount: ₹{event.amount}")


#     # --------------------------------------
#     # 2. BUILD ML FEATURES
#     # --------------------------------------

#     event_data = event.model_dump()

#     features = build_ml_features(event_data)

#     print("\n========== FEATURES ==========")
#     print(features)


#     # --------------------------------------
#     # 3. XGBOOST PREDICTION
#     # --------------------------------------

#     prediction = predictor_recovery(features)

#     prediction["recovery_probability"] = float(
#         prediction["recovery_probability"]
#     )

#     prediction["predicted_recovered"] = int(
#         prediction["predicted_recovered"]
#     )

#     print("\n========== ML PREDICTION ==========")
#     print(prediction)


#     # --------------------------------------
#     # 4. BUILD PAYMENT CONTEXT
#     # --------------------------------------

#     context = PaymentContext(
#         event_type=event.event_type,
#         amount=event.amount,
#         customer_id=event.customer_id,

#         failure_category=features["failure_category"],
#         payment_method=features["payment_method"],
#         gateway_provider=features["gateway_provider"],
#         user_device=features["user_device"],
#         attempt_number=features["attempt_number"],

#         historical_success_rate=features[
#             "historical_success_rate"
#         ],

#         prev_payment_count=features[
#             "prev_payment_count"
#         ],

#         prev_success_count=features[
#             "prev_success_count"
#         ],

#         prev_failure_count=features[
#             "prev_failure_count"
#         ]
#     )


#     # --------------------------------------
#     # 5. RECOVERY AI PIPELINE
#     # --------------------------------------

#     recovery_result = run_recovery_pipeline(
#         context=context,

#         recovery_probability=prediction[
#             "recovery_probability"
#         ],

#         payment_id=event.payment_id,

#         customer_contacts_today=0,

#         # TEST MODE
#         simulated_payment_success=True
#     )

#     print("\n========== RECOVERY PIPELINE ==========")
#     print("Recovery pipeline completed")


#     # --------------------------------------
#     # 5.1 SAVE RESULTS
#     # --------------------------------------

#     db_event.recovery_probability = prediction[
#         "recovery_probability"
#     ]

#     db_event.predicted_recovered = prediction[
#         "predicted_recovered"
#     ]

#     db_event.priority = prediction[
#         "priority"
#     ]

#     db_event.recovery_result = json.dumps(
#         recovery_result
#     )


#     # --------------------------------------
#     # UPDATE STATUS
#     # --------------------------------------

#     if recovery_result.get("outcome"):

#         db_event.status = recovery_result[
#             "outcome"
#         ]["status"]

#     elif recovery_result.get(
#         "guardrail", {}
#     ).get("allowed") is False:

#         db_event.status = "BLOCKED"

#     else:

#         db_event.status = "PROCESSING"


#     db.commit()
#     db.refresh(db_event)


#     # --------------------------------------
#     # 6. FINAL RESPONSE
#     # --------------------------------------

#     return {
#         "id": db_event.id,
#         "event_type": db_event.event_type,
#         "amount": db_event.amount,
#         "payment_id": db_event.payment_id,
#         "failure_reason": db_event.failure_reason,
#         "customer_id": db_event.customer_id,
#         "status": db_event.status,
#         "created_at": db_event.created_at,

#         "failure_category": db_event.failure_category,
#         "payment_method": db_event.payment_method,
#         "gateway_provider": db_event.gateway_provider,
#         "user_device": db_event.user_device,
#         "attempt_number": db_event.attempt_number,

#         "recovery_probability": prediction[
#             "recovery_probability"
#         ],

#         "predicted_recovered": prediction[
#             "predicted_recovered"
#         ],

#         "priority": prediction[
#             "priority"
#         ],

#         "recovery_result": recovery_result
#     }


# # ==========================================
# # GET ALL EVENTS
# # ==========================================

# @app.get(
#     "/events",
#     response_model=list[RevenueEventListResponse]
# )
# def get_events(
#     db: Session = Depends(get_db)
# ):

#     events = db.query(
#         RevenueEventModel
#     ).order_by(
#         RevenueEventModel.id.desc()
#     ).all()

#     result = []

#     for event in events:

#         recovery_data = None

#         if event.recovery_result:

#             try:

#                 recovery_data = json.loads(
#                     event.recovery_result
#                 )

#             except json.JSONDecodeError:

#                 recovery_data = None


#         result.append({

#             "id": event.id,

#             "event_type": event.event_type,

#             "amount": event.amount,

#             "payment_id": event.payment_id,

#             "failure_reason": event.failure_reason,

#             "customer_id": event.customer_id,

#             "status": event.status,

#             "created_at": event.created_at,

#             "failure_category": event.failure_category,

#             "payment_method": event.payment_method,

#             "gateway_provider": event.gateway_provider,

#             "user_device": event.user_device,

#             "attempt_number": event.attempt_number,

#             "recovery_probability":
#                 event.recovery_probability,

#             "predicted_recovered":
#                 event.predicted_recovered,

#             "priority":
#                 event.priority,

#             "recovery_result":
#                 recovery_data
#         })


#     return result


# # ==========================================
# # SEED 10 RANDOM EVENTS
# # ==========================================

# @app.post("/seed/10")
# def seed_ten_events():

#     seed_database(10)

#     return {
#         "success": True,
#         "message": "10 random events added"
#     }



import sys
import os
import json


# ==========================================
# SERVICES PATH
# ==========================================

SERVICES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "services")
)

if SERVICES_DIR not in sys.path:
    sys.path.insert(0, SERVICES_DIR)


# ==========================================
# FASTAPI IMPORTS
# ==========================================

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel


# ==========================================
# SERVICES
# ==========================================

from recovery_pipeline import run_recovery_pipeline
from gemini_agent import PaymentContext


# ==========================================
# BACKEND IMPORTS
# ==========================================

from backend.schemas import (
    RevenueEventResponse,
    RevenueEvent,
    RevenueEventListResponse
)

from backend.database import (
    Base,
    SessionLocal,
    engine
)

from backend.models import RevenueEvent as RevenueEventModel

from backend.feature_builder import build_ml_features
from backend.predictor import predictor_recovery

# IMPORTANT: seed function
from backend.seed_database import seed_database


# ==========================================
# DATABASE
# ==========================================

Base.metadata.create_all(bind=engine)


# ==========================================
# FASTAPI
# ==========================================

app = FastAPI(
    title="AI Revenue Recovery System"
)


# ==========================================
# CORS
# ==========================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# DATABASE DEPENDENCY
# ==========================================

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# ==========================================
# CREATE REVENUE EVENT
# ==========================================

@app.post(
    "/events",
    response_model=RevenueEventResponse
)
def create_event(
    event: RevenueEvent,
    db: Session = Depends(get_db)
):

    # --------------------------------------
    # 1. SAVE EVENT
    # --------------------------------------

    db_event = RevenueEventModel(
        event_type=event.event_type,
        amount=event.amount,
        customer_id=event.customer_id,
        payment_id=event.payment_id,
        failure_reason=event.failure_reason,
        status="DETECTED",

        failure_category=event.failure_category,
        payment_method=event.payment_method,
        gateway_provider=event.gateway_provider,
        user_device=event.user_device,
        attempt_number=event.attempt_number
    )

    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    print("\n========== EVENT DETECTED ==========")
    print(f"Event ID: {db_event.id}")
    print(f"Amount: ₹{event.amount}")


    # --------------------------------------
    # 2. BUILD ML FEATURES
    # --------------------------------------

    event_data = event.model_dump()

    features = build_ml_features(event_data)

    print("\n========== FEATURES ==========")
    print(features)


    # --------------------------------------
    # 3. XGBOOST PREDICTION
    # --------------------------------------

    prediction = predictor_recovery(features)

    prediction["recovery_probability"] = float(
        prediction["recovery_probability"]
    )

    prediction["predicted_recovered"] = int(
        prediction["predicted_recovered"]
    )

    print("\n========== ML PREDICTION ==========")
    print(prediction)


    # --------------------------------------
    # 4. BUILD PAYMENT CONTEXT
    # --------------------------------------

    context = PaymentContext(
        event_type=event.event_type,
        amount=event.amount,
        customer_id=event.customer_id,

        failure_category=features["failure_category"],
        payment_method=features["payment_method"],
        gateway_provider=features["gateway_provider"],
        user_device=features["user_device"],
        attempt_number=features["attempt_number"],

        historical_success_rate=features[
            "historical_success_rate"
        ],

        prev_payment_count=features[
            "prev_payment_count"
        ],

        prev_success_count=features[
            "prev_success_count"
        ],

        prev_failure_count=features[
            "prev_failure_count"
        ]
    )


    # --------------------------------------
    # 5. RECOVERY AI PIPELINE
    # --------------------------------------

    recovery_result = run_recovery_pipeline(
        context=context,

        recovery_probability=prediction[
            "recovery_probability"
        ],

        payment_id=event.payment_id,

        customer_contacts_today=0,

        # TEST MODE
        simulated_payment_success=True
    )

    print("\n========== RECOVERY PIPELINE ==========")
    print("Recovery pipeline completed")


    # --------------------------------------
    # 5.1 SAVE RESULTS
    # --------------------------------------

    db_event.recovery_probability = prediction[
        "recovery_probability"
    ]

    db_event.predicted_recovered = prediction[
        "predicted_recovered"
    ]

    db_event.priority = prediction[
        "priority"
    ]

    db_event.recovery_result = json.dumps(
        recovery_result
    )


    # --------------------------------------
    # UPDATE STATUS
    # --------------------------------------

    if recovery_result.get("outcome"):

        db_event.status = recovery_result[
            "outcome"
        ]["status"]

    elif recovery_result.get(
        "guardrail", {}
    ).get("allowed") is False:

        db_event.status = "BLOCKED"

    else:

        db_event.status = "PROCESSING"


    db.commit()
    db.refresh(db_event)


    # --------------------------------------
    # 6. FINAL RESPONSE
    # --------------------------------------

    return {
        "id": db_event.id,
        "event_type": db_event.event_type,
        "amount": db_event.amount,
        "payment_id": db_event.payment_id,
        "failure_reason": db_event.failure_reason,
        "customer_id": db_event.customer_id,
        "status": db_event.status,
        "created_at": db_event.created_at,

        "failure_category": db_event.failure_category,
        "payment_method": db_event.payment_method,
        "gateway_provider": db_event.gateway_provider,
        "user_device": db_event.user_device,
        "attempt_number": db_event.attempt_number,

        "recovery_probability": prediction[
            "recovery_probability"
        ],

        "predicted_recovered": prediction[
            "predicted_recovered"
        ],

        "priority": prediction[
            "priority"
        ],

        "recovery_result": recovery_result
    }


# ==========================================
# GET ALL EVENTS
# ==========================================

@app.get(
    "/events",
    response_model=list[RevenueEventListResponse]
)
def get_events(
    db: Session = Depends(get_db)
):

    events = db.query(
        RevenueEventModel
    ).order_by(
        RevenueEventModel.id.desc()
    ).all()

    result = []

    for event in events:

        recovery_data = None

        if event.recovery_result:

            try:

                recovery_data = json.loads(
                    event.recovery_result
                )

            except json.JSONDecodeError:

                recovery_data = None


        result.append({

            "id": event.id,

            "event_type": event.event_type,

            "amount": event.amount,

            "payment_id": event.payment_id,

            "failure_reason": event.failure_reason,

            "customer_id": event.customer_id,

            "status": event.status,

            "created_at": event.created_at,

            "failure_category": event.failure_category,

            "payment_method": event.payment_method,

            "gateway_provider": event.gateway_provider,

            "user_device": event.user_device,

            "attempt_number": event.attempt_number,

            "recovery_probability":
                event.recovery_probability,

            "predicted_recovered":
                event.predicted_recovered,

            "priority":
                event.priority,

            "recovery_result":
                recovery_data
        })


    return result


# ==========================================
# SEED 10 RANDOM EVENTS
# ==========================================

@app.post("/seed/10")
def seed_ten_events():

    seed_database(10)

    return {
        "success": True,
        "message": "10 random events added"
    }

# ==========================================
# AEROS AI CHATBOT
# ==========================================

class ChatPayload(BaseModel):
    message: str


@app.post("/chat")
def chatbot_endpoint(payload: ChatPayload):

    user_msg = payload.message.strip()

    if not user_msg:
        return {
            "reply": "Please enter a message."
        }

    try:

        # Try root-level reasoning_agent.py
        try:
            from reasoning_agent import chat_with_aeros
        except ImportError:
            # Try services/reasoning_agent.py
            from services.reasoning_agent import chat_with_aeros

        reply_text = chat_with_aeros(user_msg)

        return {
            "success": True,
            "reply": reply_text
        }

    except Exception as e:

        # IMPORTANT:
        # Don't hide the actual error anymore.
        print("=" * 60)
        print("[AEROS CHAT ERROR]")
        print(str(e))
        print("=" * 60)

        return {
            "success": False,
            "reply": "AEROS AI could not generate a response.",
            "error": str(e)
        }