import numpy as np
import pandas as pd
import random
from datetime import datetime, timedelta


# =========================================================
# CONFIGURATION
# =========================================================

SEED = 42
TOTAL_RECORDS = 10000
TOTAL_CUSTOMERS = 2500

np.random.seed(SEED)
random.seed(SEED)


# =========================================================
# REALISTIC MASTER DATA
# =========================================================

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun",
    "Ishaan", "Reyansh", "Kabir", "Rohan", "Kunal",
    "Ananya", "Diya", "Saanvi", "Kavya", "Riya",
    "Aadhya", "Meera", "Ira", "Sneha", "Pooja"
]

LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Patel", "Singh",
    "Kumar", "Reddy", "Nair", "Joshi", "Chopra",
    "Rao", "Bhat", "Kulkarni", "Mehta", "Malhotra"
]

DOMAINS = [
    "gmail.com",
    "outlook.com",
    "yahoo.com",
    "company.in",
    "enterprise.in"
]

GATEWAYS = [
    "Razorpay",
    "Cashfree",
    "PayU",
    "Stripe",
    "CCAvenue"
]

MERCHANT_CATEGORIES = [
    "E-commerce Retail",
    "EdTech",
    "SaaS",
    "B2B Wholesale"
]

DEVICES = [
    "Mobile",
    "Desktop",
    "Tablet"
]


# =========================================================
# EVENT DISTRIBUTION
# =========================================================

EVENT_TYPES = [
    "failed_payment",
    "checkout_abandonment",
    "overdue_invoice"
]

EVENT_PROBABILITIES = [
    0.55,   # failed payment
    0.30,   # checkout abandonment
    0.15    # overdue invoice
]


# =========================================================
# FAILURE TYPES
# =========================================================

FAILURE_TYPES = [
    "insufficient_funds",
    "network_error",
    "bank_downtime",
    "expired_card",
    "user_timeout"
]

FAILURE_ENCODING = {
    "expired_card": 0,
    "insufficient_funds": 1,
    "network_error": 2,
    "user_timeout": 3,
    "bank_downtime": 4
}


# =========================================================
# HELPER
# =========================================================

def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


# =========================================================
# 1. CREATE CUSTOMER PROFILES
#
# Each customer gets a persistent behaviour profile.
# This makes repeated events for the same customer realistic.
# =========================================================

customers = {}

for i in range(TOTAL_CUSTOMERS):

    customer_id = f"CUST_{1000 + i}"

    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    age_days = random.randint(30, 1500)

    # Customer quality / reliability
    reliability = np.random.beta(7, 3)

    # Activity level
    activity = np.random.beta(4, 2)

    # Some customers are high-value
    customer_segment = np.random.choice(
        ["low", "medium", "high"],
        p=[0.45, 0.40, 0.15]
    )

    if customer_segment == "low":
        typical_amount = np.random.uniform(500, 3000)

    elif customer_segment == "medium":
        typical_amount = np.random.uniform(3000, 15000)

    else:
        typical_amount = np.random.uniform(15000, 80000)

    customers[customer_id] = {
        "customer_id": customer_id,
        "customer_name": f"{first_name} {last_name}",
        "customer_email": (
            f"{first_name.lower()}."
            f"{last_name.lower()}"
            f"{random.randint(1, 99)}@"
            f"{random.choice(DOMAINS)}"
        ),
        "customer_phone": (
            f"+91{random.randint(6000000000, 9999999999)}"
        ),
        "customer_age_days": age_days,
        "reliability": reliability,
        "activity": activity,
        "segment": customer_segment,
        "typical_amount": typical_amount,

        # Persistent payment history
        "prev_payment_count": random.randint(2, 50),
        "prev_success_count": 0,
        "prev_failure_count": 0,

        # Recovery history
        "prev_recovery_actions": random.randint(0, 3),
        "prev_recovery_outcomes": 0,

        # Last successful payment
        "days_since_last_success": random.randint(1, 180)
    }


# =========================================================
# 2. INITIALIZE CUSTOMER PAYMENT HISTORY
# =========================================================

for customer in customers.values():

    total_payments = customer["prev_payment_count"]

    success_rate = clamp(
        np.random.normal(
            customer["reliability"],
            0.08
        ),
        0.20,
        0.98
    )

    success_count = int(
        round(total_payments * success_rate)
    )

    success_count = min(
        success_count,
        total_payments
    )

    failure_count = total_payments - success_count

    customer["prev_success_count"] = success_count
    customer["prev_failure_count"] = failure_count

    actions = customer["prev_recovery_actions"]

    if actions > 0:

        recovery_rate = clamp(
            customer["reliability"] + 0.05,
            0.20,
            0.95
        )

        outcomes = np.random.binomial(
            actions,
            recovery_rate
        )

        customer["prev_recovery_outcomes"] = outcomes


# =========================================================
# 3. GENERATE EVENTS
# =========================================================

records = []

start_date = datetime.now() - timedelta(days=90)


for i in range(TOTAL_RECORDS):

    # -----------------------------------------------------
    # Select customer
    # -----------------------------------------------------

    customer_id = random.choice(
        list(customers.keys())
    )

    customer = customers[customer_id]

    # -----------------------------------------------------
    # Event type
    # -----------------------------------------------------

    event_type = np.random.choice(
        EVENT_TYPES,
        p=EVENT_PROBABILITIES
    )

    # -----------------------------------------------------
    # Merchant / gateway
    # -----------------------------------------------------

    merchant_category = random.choice(
        MERCHANT_CATEGORIES
    )

    gateway_provider = random.choice(
        GATEWAYS
    )

    user_device = random.choice(
        DEVICES
    )

    # -----------------------------------------------------
    # Payment method based on event
    # -----------------------------------------------------

    if event_type == "overdue_invoice":

        payment_method = random.choices(
            [
                "Bank Transfer / NEFT",
                "NetBanking",
                "Credit Card"
            ],
            weights=[0.65, 0.20, 0.15]
        )[0]

    elif event_type == "failed_payment":

        payment_method = random.choices(
            [
                "UPI",
                "Credit Card",
                "Debit Card",
                "NetBanking"
            ],
            weights=[0.40, 0.30, 0.18, 0.12]
        )[0]

    else:

        payment_method = random.choices(
            [
                "UPI",
                "Credit Card",
                "Debit Card",
                "NetBanking",
                "Wallet"
            ],
            weights=[0.38, 0.27, 0.15, 0.12, 0.08]
        )[0]

    # =====================================================
    # AMOUNT
    # =====================================================

    base_amount = customer["typical_amount"]

    if event_type == "checkout_abandonment":

        amount = base_amount * np.random.lognormal(
            mean=0,
            sigma=0.35
        )

        amount = clamp(
            amount,
            499,
            25000
        )

    elif event_type == "failed_payment":

        amount = base_amount * np.random.lognormal(
            mean=0,
            sigma=0.40
        )

        amount = clamp(
            amount,
            500,
            50000
        )

    else:

        # Invoice customers generally have larger amounts
        amount = max(
            base_amount,
            np.random.uniform(15000, 30000)
        )

        amount *= np.random.lognormal(
            mean=0,
            sigma=0.45
        )

        amount = clamp(
            amount,
            10000,
            100000
        )

    amount = round(amount, 2)

    # =====================================================
    # FAILURE CATEGORY
    # =====================================================

    if event_type == "failed_payment":

        failure_category = np.random.choice(
            FAILURE_TYPES,
            p=[
                0.30,  # insufficient funds
                0.22,  # network
                0.18,  # bank downtime
                0.15,  # expired card
                0.15   # timeout
            ]
        )

    elif event_type == "checkout_abandonment":

        failure_category = "user_timeout"

    else:

        failure_category = "insufficient_funds"

    failure_category_encoded = (
        FAILURE_ENCODING[failure_category]
    )

    # =====================================================
    # ATTEMPT NUMBER
    # =====================================================

    if event_type == "failed_payment":

        attempt_number = random.choices(
            [1, 2, 3, 4, 5],
            weights=[0.50, 0.25, 0.13, 0.08, 0.04]
        )[0]

    elif event_type == "checkout_abandonment":

        attempt_number = random.choice([1, 1, 1, 2])

    else:

        attempt_number = 1

    # =====================================================
    # HOURS SINCE FAILURE
    # =====================================================

    if event_type == "failed_payment":

        hours_since_failure = np.random.exponential(
            scale=12
        )

        hours_since_failure = clamp(
            hours_since_failure,
            0.1,
            96
        )

    elif event_type == "checkout_abandonment":

        hours_since_failure = np.random.exponential(
            scale=8
        )

        hours_since_failure = clamp(
            hours_since_failure,
            0.1,
            72
        )

    else:

        hours_since_failure = np.random.uniform(
            24,
            240
        )

    hours_since_failure = round(
        hours_since_failure,
        2
    )

    # =====================================================
    # INVOICE AGE
    # =====================================================

    if event_type == "overdue_invoice":

        invoice_age_days = random.randint(
            1,
            90
        )

    else:

        invoice_age_days = 0

    # =====================================================
    # CUSTOMER HISTORY
    # =====================================================

    prev_payment_count = customer[
        "prev_payment_count"
    ]

    prev_success_count = customer[
        "prev_success_count"
    ]

    prev_failure_count = customer[
        "prev_failure_count"
    ]

    historical_success_rate = (
        prev_success_count /
        max(prev_payment_count, 1)
    )

    historical_success_rate = round(
        historical_success_rate,
        4
    )

    customer_activity_score = round(
        customer["activity"] * 10,
        2
    )

    days_since_last_success = customer[
        "days_since_last_success"
    ]

    prev_recovery_actions = customer[
        "prev_recovery_actions"
    ]

    prev_recovery_outcomes = customer[
        "prev_recovery_outcomes"
    ]

    # =====================================================
    # RECOVERY PROBABILITY
    #
    # This represents realistic business behaviour.
    # The ML model will learn these relationships.
    # =====================================================

    score = 0.45

    # Customer reliability
    score += (
        historical_success_rate - 0.50
    ) * 0.35

    # Customer activity
    score += (
        customer_activity_score / 10
    ) * 0.15

    # Previous recovery performance
    if prev_recovery_actions > 0:

        recovery_rate = (
            prev_recovery_outcomes /
            prev_recovery_actions
        )

        score += (
            recovery_rate - 0.50
        ) * 0.15

    # -----------------------------------------------------
    # Event-specific behaviour
    # -----------------------------------------------------

    if event_type == "failed_payment":

        if failure_category == "bank_downtime":
            score += 0.24

        elif failure_category == "network_error":
            score += 0.18

        elif failure_category == "insufficient_funds":
            score -= 0.10

        elif failure_category == "expired_card":
            score -= 0.18

        elif failure_category == "user_timeout":
            score += 0.05

        # Multiple retries usually indicate difficulty
        score -= (
            max(attempt_number - 1, 0)
            * 0.045
        )

    elif event_type == "checkout_abandonment":

        # Recent abandonment is easier to recover
        score += 0.12

        # Recovery probability decreases with time
        score -= (
            hours_since_failure / 72
        ) * 0.15

    else:

        # Older invoices are harder to recover
        score -= (
            invoice_age_days / 90
        ) * 0.22

        # High-value B2B customers may be more recoverable
        if amount > 50000:
            score += 0.05

    # -----------------------------------------------------
    # Recency of previous successful payment
    # -----------------------------------------------------

    if days_since_last_success <= 30:

        score += 0.08

    elif days_since_last_success > 180:

        score -= 0.10

    # -----------------------------------------------------
    # Amount effect
    # -----------------------------------------------------

    if amount < 2000:

        score += 0.04

    elif amount > 75000:

        score -= 0.06

    # -----------------------------------------------------
    # Random real-world noise
    # -----------------------------------------------------

    score += np.random.normal(
        loc=0,
        scale=0.07
    )

    recovery_probability = clamp(
        score,
        0.03,
        0.97
    )

    # =====================================================
    # TARGET
    # =====================================================

    recovered = np.random.binomial(
        1,
        recovery_probability
    )

    # =====================================================
    # TIMESTAMP
    #
    # More events during normal business hours.
    # =====================================================

    event_time = (
        start_date +
        timedelta(
            minutes=random.randint(
                0,
                90 * 24 * 60
            )
        )
    )

    # =====================================================
    # UPDATE CUSTOMER HISTORY
    #
    # This is important because future events for this
    # customer depend on previous events.
    # =====================================================

    customer["prev_payment_count"] += 1

    if recovered:

        customer["prev_success_count"] += 1

        customer["days_since_last_success"] = 0

    else:

        customer["prev_failure_count"] += 1

        customer["days_since_last_success"] += random.randint(
            1,
            7
        )

    # Recovery action happened for some events
    if random.random() < 0.35:

        customer["prev_recovery_actions"] = min(
            customer["prev_recovery_actions"] + 1,
            5
        )

        if recovered:

            customer["prev_recovery_outcomes"] = min(
                customer["prev_recovery_outcomes"] + 1,
                customer["prev_recovery_actions"]
            )

    # =====================================================
    # RECORD
    # =====================================================

    record = {

        # -----------------------------
        # Metadata
        # -----------------------------

        "event_id":
            f"EV_{100000 + i}",

        "transaction_id":
            f"TXN_{202600000 + i}",

        "customer_id":
            customer_id,

        "customer_name":
            customer["customer_name"],

        "customer_email":
            customer["customer_email"],

        "customer_phone":
            customer["customer_phone"],

        "merchant_category":
            merchant_category,

        "gateway_provider":
            gateway_provider,

        "payment_method":
            payment_method,

        "user_device":
            user_device,

        "event_type":
            event_type,

        "failure_category":
            failure_category,

        "created_at":
            event_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        # -----------------------------
        # EXACT 14 ML FEATURES
        # -----------------------------

        "amount":
            amount,

        "customer_age_days":
            customer["customer_age_days"],

        "prev_payment_count":
            prev_payment_count,

        "prev_success_count":
            prev_success_count,

        "prev_failure_count":
            prev_failure_count,

        "historical_success_rate":
            historical_success_rate,

        "days_since_last_success":
            days_since_last_success,

        "customer_activity_score":
            customer_activity_score,

        "failure_category_encoded":
            failure_category_encoded,

        "attempt_number":
            attempt_number,

        "hours_since_failure":
            hours_since_failure,

        "invoice_age_days":
            invoice_age_days,

        "prev_recovery_actions":
            prev_recovery_actions,

        "prev_recovery_outcomes":
            prev_recovery_outcomes,

        # -----------------------------
        # TARGET
        # -----------------------------

        "recovered":
            recovered
    }

    records.append(record)


# =========================================================
# 4. CREATE DATAFRAME
# =========================================================

df = pd.DataFrame(records)


# =========================================================
# 5. SAFETY CHECKS
# =========================================================

ML_FEATURES = [
    "amount",
    "customer_age_days",
    "prev_payment_count",
    "prev_success_count",
    "prev_failure_count",
    "historical_success_rate",
    "days_since_last_success",
    "customer_activity_score",
    "failure_category_encoded",
    "attempt_number",
    "hours_since_failure",
    "invoice_age_days",
    "prev_recovery_actions",
    "prev_recovery_outcomes"
]

required_columns = ML_FEATURES + ["recovered"]

missing = [
    col
    for col in required_columns
    if col not in df.columns
]

if missing:
    raise ValueError(
        f"Missing columns: {missing}"
    )


# =========================================================
# 6. SAVE DATASET
# =========================================================

df.to_csv(
    "events.csv",
    index=False
)


# =========================================================
# 7. DATASET REPORT
# =========================================================

print("\n" + "=" * 70)
print("REALISTIC SYNTHETIC DATASET GENERATED")
print("=" * 70)

print(
    f"Total Records       : {len(df)}"
)

print(
    f"Unique Customers    : {df['customer_id'].nunique()}"
)

print(
    f"Dataset Shape       : {df.shape}"
)

print("\nEvent Distribution:")
print(
    df["event_type"]
    .value_counts(normalize=True)
    .round(3)
)

print("\nRecovery Distribution:")
print(
    df["recovered"]
    .value_counts(normalize=True)
    .round(3)
)

print("\nAverage Amount by Event:")
print(
    df.groupby("event_type")["amount"]
    .mean()
    .round(2)
)

print("\nML Features:")
for feature in ML_FEATURES:
    print("  ✓", feature)

print("\nFile Saved:")
print("  events.csv")

print("=" * 70)