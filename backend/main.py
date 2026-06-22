from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph_engine import calculate_ripple
from action_engine import generate_action_plan
from historical_engine import generate_historical_evidence
from data_catalog import command_center_overview, feature_engineering_report
from ml_engine import predict_impact
from nlp_engine import extract_incident
from route_engine import generate_route_optimization
from real_feed_engine import build_live_events, build_live_events_snapshot, get_source_health

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


@app.get("/api/event_feed")
def get_event_feed():
    return {"feed": build_live_events(include_simulated=True)}


@app.get("/api/live_events")
def get_live_events():
    return {"feed": build_live_events(include_simulated=True)}


@app.get("/api/event_feed/snapshot")
def get_event_feed_snapshot():
    return {"feed": build_live_events_snapshot()}


@app.get("/api/source_health")
def get_source_health_report():
    return get_source_health()


@app.post("/api/analyze_event")
def analyze_event(request: AnalyzeEventRequest):
    extraction = extract_incident(request.text)
    historical_evidence = generate_historical_evidence(extraction)
    predictions = predict_impact(
        extraction["incident_type"],
        extraction["location"],
        extraction.get("vehicle_type", "unknown"),
        extraction.get("severity", "low"),
        extraction.get("lanes_blocked", 0),
        extraction.get("crowd_size", "unknown"),
        extraction.get("confidence_score", 0),
    )
    route_optimization = generate_route_optimization(
        extraction,
        historical_evidence=historical_evidence,
        predicted_delay_mins=predictions["predicted_delay_mins"],
    )
    action_plan = generate_action_plan(
        extraction,
        predictions["predicted_delay_mins"],
        historical_evidence,
        route_optimization,
    )
    ripple_effect = calculate_ripple(
        extraction["location"],
        predictions["predicted_delay_mins"],
    )

    return {
        "extraction": extraction,
        "entities": extraction,
        "historical_evidence": historical_evidence,
        "predictions": predictions,
        "route_optimization": route_optimization,
        "action_plan": action_plan,
        "ripple_effect": ripple_effect,
    }


@app.get("/api/feature_report")
def get_feature_report():
    return feature_engineering_report()


@app.get("/api/command_overview")
def get_command_overview():
    return command_center_overview()
