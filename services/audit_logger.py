import json
from datetime import datetime
from pathlib import Path


# ==========================================
# AUDIT LOG FILE
# ==========================================

AUDIT_FILE = Path(__file__).parent / "audit_logs.json"


# ==========================================
# AUDIT LOGGER
# ==========================================

def log_recovery_event(
    customer_id: str,
    amount: float,
    recommendation: dict,
    guardrail: dict,
    execution: dict,
    outcome: dict,
    ai_provider: str = "Gemini"
):
    """
    Store complete recovery decision trail.

    Flow:
    AI Decision
        ↓
    Guardrail
        ↓
    Execution
        ↓
    Outcome
    """

    audit_entry = {
        "timestamp": datetime.now().isoformat(),

        "customer_id": customer_id,

        "amount": amount,

        "ai_provider": ai_provider,

        "recommendation": recommendation,

        "guardrail": guardrail,

        "execution": execution,

        "outcome": outcome
    }

    # --------------------------------------
    # READ EXISTING LOGS
    # --------------------------------------

    if AUDIT_FILE.exists():

        try:

            with open(
                AUDIT_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                logs = json.load(file)

        except (json.JSONDecodeError, OSError):

            logs = []

    else:

        logs = []

    # --------------------------------------
    # ADD NEW EVENT
    # --------------------------------------

    logs.append(audit_entry)

    # --------------------------------------
    # SAVE
    # --------------------------------------

    with open(
        AUDIT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            logs,
            file,
            indent=2
        )

    return audit_entry


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    recommendation = {
        "action_type": "DELAYED_RETRY",
        "recommended_delay_minutes": 30,
        "incentive_type": None,
        "reasoning_summary": (
            "High recovery probability and "
            "temporary bank downtime."
        )
    }

    guardrail = {
        "allowed": True,
        "reason": (
            "Action passed all merchant guardrails."
        )
    }

    execution = {
        "success": True,
        "action_type": "DELAYED_RETRY",
        "status": "EXECUTED",
        "message": (
            "Retry scheduled after 30 minutes."
        )
    }

    outcome = {
        "status": "RECOVERED",
        "amount_recovered": 500.0,
        "recovery_success": True,
        "message": (
            "Payment successfully recovered."
        )
    }

    result = log_recovery_event(
        customer_id="CUST_2891",
        amount=500.0,
        recommendation=recommendation,
        guardrail=guardrail,
        execution=execution,
        outcome=outcome,
        ai_provider="Gemini"
    )

    print("Audit log created successfully:")

    print(
        json.dumps(
            result,
            indent=2
        )
    )