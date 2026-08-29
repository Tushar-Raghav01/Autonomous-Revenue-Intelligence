from pathlib import Path
import joblib
import pandas as pd


BASE_DIR=Path(__file__).resolve().parent

MODEL_PATH=BASE_DIR.parent /"ml"/"xgb_recovery_pipeline.joblib"


pipeline=joblib.load(MODEL_PATH)

def predictor_recovery(event_data:dict):

    data=pd.DataFrame([event_data])

    probability=float(
        pipeline.predict_proba(data)[0][1]
    )
    prediction=pipeline.predict(data)[0]

    if probability >=0.75:
        priority="High"
    elif probability>=0.50:
        priority="Medium"
    else:
        priority="Low" 

    return {
    "recovery_probability": round(probability, 4),
    "predicted_recovered": prediction,
    "priority": priority
    }