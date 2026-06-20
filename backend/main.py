from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph_engine import calculate_ripple
from ml_engine import predict_impact
from nlp_engine import extract_incident

app = FastAPI(
    title="ASTraM Traffic Intelligence Backend",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeEventRequest(BaseModel):
    text: str


@app.get("/")
def health_check():
    return {
        "status": "ASTraM Traffic Backend is Live",
        "version": "1.0",
    }


@app.post("/api/analyze_event")
def analyze_event(request: AnalyzeEventRequest):
    extraction = extract_incident(request.text)
    predictions = predict_impact(extraction["incident_type"], extraction["location"])
    ripple_effect = calculate_ripple(
        extraction["location"],
        predictions["predicted_delay_mins"],
    )

    return {
        "extraction": extraction,
        "predictions": predictions,
        "ripple_effect": ripple_effect,
    }
