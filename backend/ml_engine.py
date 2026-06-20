"""Historical impact prediction from cleaned ASTraM data."""

from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent / "data" / "cleaned_astram_data.csv"

INCIDENT_TYPE_TO_EVENT_CAUSE = {
    "breakdown": "vehicle_breakdown",
    "accident": "accident",
    "tree": "tree_fall",
    "waterlogging": "water_logging",
    "protest": "public_event",
}


def _load_cleaned_data() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


def predict_impact(incident_type: str, location: str) -> dict:
    df = _load_cleaned_data()

    if incident_type == "unknown":
        predicted_delay = 45.0
    else:
        event_cause = INCIDENT_TYPE_TO_EVENT_CAUSE.get(incident_type, incident_type)
        matching = df[df["event_cause"] == event_cause]

        if matching.empty:
            matching = df[
                df["event_cause"].astype(str).str.contains(incident_type, case=False, na=False)
            ]

        if matching.empty:
            predicted_delay = 45.0
        else:
            predicted_delay = float(matching["resolution_time_mins"].mean())

    if predicted_delay > 45:
        return {
            "predicted_delay_mins": round(predicted_delay, 2),
            "police_required": 12,
            "barricades": 40,
            "tow_trucks": 1,
        }

    return {
        "predicted_delay_mins": round(predicted_delay, 2),
        "police_required": 4,
        "barricades": 10,
        "tow_trucks": 0,
    }
