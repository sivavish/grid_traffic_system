"""Historical evidence lookup for ASTraM incidents."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from data_catalog import infer_corridor_label, infer_location_label, infer_severity, load_cleaned_rows

DATA_PATH = Path(__file__).parent / "data" / "cleaned_astram_data.csv"

INCIDENT_TYPE_TO_EVENT_CAUSE = {
    "breakdown": "vehicle_breakdown",
    "accident": "accident",
    "tree": "tree_fall",
    "waterlogging": "water_logging",
    "protest": "public_event",
}

SEVERITY_TO_PRIORITY = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "High",
}


@lru_cache(maxsize=1)
def _load_cleaned_data() -> list[dict[str, Any]]:
    return load_cleaned_rows()


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, "", "NULL", "null"):
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "NULL", "null"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _time_of_day_bucket(value: Any) -> str:
    parsed = value if isinstance(value, datetime) else _parse_datetime(value)
    if parsed is None:
        return "unknown"

    hour = parsed.hour
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _is_truthy(value: Any) -> bool:
    return _normalize_text(value) in {"true", "1", "yes", "y"}


def _match_location_score(row: dict[str, Any], location: str) -> float:
    if not location or location == "unknown":
        return 0.0

    normalized_location = _normalize_text(location)
    searchable_columns = ["address", "police_station", "junction", "corridor", "zone", "description", "comment"]

    for column in searchable_columns:
        if normalized_location and normalized_location in _normalize_text(row.get(column)):
            return 1.0

    return 0.0


def _severity_to_priority(severity: str) -> str:
    return SEVERITY_TO_PRIORITY.get(_normalize_text(severity), "Low")


def _score_row(row: dict[str, Any], incident_type: str, location: str, severity: str, time_of_day: str) -> float:
    score = 0.0

    event_cause = INCIDENT_TYPE_TO_EVENT_CAUSE.get(_normalize_text(incident_type), _normalize_text(incident_type))
    if event_cause and _normalize_text(row.get("event_cause")) == _normalize_text(event_cause):
        score += 40.0

    score += 30.0 * _match_location_score(row, location)

    if _normalize_text(row.get("corridor")) and _normalize_text(location) and _normalize_text(row.get("corridor")) in _normalize_text(location):
        score += 10.0

    if _normalize_text(row.get("requires_road_closure")) in {"true", "1", "yes"}:
        score += 6.0

    if _normalize_text(row.get("priority")) == _normalize_text(_severity_to_priority(severity)):
        score += 15.0

    row_time_bucket = _time_of_day_bucket(row.get("created_date"))
    if time_of_day != "unknown" and row_time_bucket == time_of_day:
        score += 15.0

    return score


def find_similar_incidents(incident: dict, reference_time: Any = None, limit: int = 5) -> list[dict[str, Any]]:
    rows = _load_cleaned_data()
    if not rows:
        return []

    time_of_day = _time_of_day_bucket(reference_time) if reference_time is not None else "unknown"

    scored_rows = []
    for row in rows:
        score = _score_row(
            row,
            incident.get("incident_type", "unknown"),
            incident.get("location", "unknown"),
            incident.get("severity", "unknown"),
            time_of_day,
        )
        enriched = dict(row)
        enriched["similarity_score"] = score
        scored_rows.append(enriched)

    scored_rows.sort(
        key=lambda row: (
            row.get("similarity_score", 0.0),
            _safe_float(row.get("resolution_time_mins")) or float("inf"),
        ),
        reverse=True,
    )

    shortlisted = [row for row in scored_rows if row.get("similarity_score", 0.0) >= 45.0]
    if not shortlisted:
        shortlisted = scored_rows[:limit]

    return shortlisted[:limit]


def _strategy_from_matches(incident_type: str, matches: list[dict[str, Any]]) -> str:
    if not matches:
        return {
            "breakdown": "Dispatch tow support and keep at least one lane moving where possible.",
            "accident": "Deploy police control, barricades, and diversion support immediately.",
            "tree": "Clear the obstruction, secure the area, and reroute traffic around the fallen tree.",
            "waterlogging": "Coordinate drainage response, close the affected stretch, and reroute vehicles.",
            "protest": "Apply crowd control, maintain police presence, and create a managed diversion route.",
        }.get(_normalize_text(incident_type), "Monitor the corridor and escalate to field response if conditions worsen.")

    vehicle_types = [row.get("veh_type", "") for row in matches if row.get("veh_type")]
    dominant_vehicle = Counter(_normalize_text(item) for item in vehicle_types).most_common(1)
    dominant_vehicle_value = dominant_vehicle[0][0] if dominant_vehicle else ""
    closed_fraction = sum(1 for row in matches if _is_truthy(row.get("requires_road_closure"))) / len(matches)

    if _normalize_text(incident_type) == "breakdown":
        if any(token in dominant_vehicle_value for token in ("bus", "heavy_vehicle", "truck", "lorry")) or closed_fraction > 0.3:
            return "Deploy tow support, coordinate mechanic assistance, and preserve one-lane movement if safe."
        return "Clear the stalled vehicle quickly and keep traffic flowing with temporary lane discipline."

    if _normalize_text(incident_type) == "accident":
        return "Send traffic police to secure the scene, place barricades, and manage detours until clearance."

    if _normalize_text(incident_type) == "tree":
        return "Coordinate civic clearance crews, secure the road edge, and restore movement after debris removal."

    if _normalize_text(incident_type) == "waterlogging":
        return "Coordinate drainage response, mark the affected segment, and reroute vehicles away from standing water."

    if _normalize_text(incident_type) == "protest":
        return "Maintain crowd control, use traffic diversions, and keep a visible police presence on the corridor."

    return "Use field verification and staged traffic diversion until the corridor is stabilized."


def _resolution_from_matches(incident_type: str, matches: list[dict[str, Any]]) -> str:
    normalized_incident_type = _normalize_text(incident_type)
    if not matches:
        return {
            "breakdown": "Tow Truck Deployment",
            "accident": "Police Control",
            "tree": "Civic Clearance",
            "waterlogging": "Drainage Response",
            "protest": "Crowd Management",
        }.get(normalized_incident_type, "Staged Traffic Diversion")

    vehicle_types = [row.get("veh_type", "") for row in matches if row.get("veh_type")]
    dominant_vehicle = Counter(_normalize_text(item) for item in vehicle_types).most_common(1)
    dominant_vehicle_value = dominant_vehicle[0][0] if dominant_vehicle else ""
    road_closure_ratio = sum(1 for row in matches if _is_truthy(row.get("requires_road_closure"))) / len(matches)

    if normalized_incident_type == "breakdown":
        if road_closure_ratio >= 0.3 or any(token in dominant_vehicle_value for token in ("truck", "bus", "lorry", "heavy_vehicle")):
            return "Tow Truck Deployment"
        return "Lane Clearance"

    if normalized_incident_type == "accident":
        return "Police Control"
    if normalized_incident_type == "tree":
        return "Civic Clearance"
    if normalized_incident_type == "waterlogging":
        return "Drainage Response"
    if normalized_incident_type == "protest":
        return "Crowd Management"

    return "Staged Traffic Diversion"


def generate_historical_evidence(incident: dict, reference_time: Any = None) -> dict:
    matches = find_similar_incidents(incident, reference_time=reference_time)

    if not matches:
        return {
            "similar_incidents": 0,
            "average_delay": 0,
            "average_clearance_time": 0,
            "confidence": 0,
            "most_common_resolution": _resolution_from_matches(incident.get("incident_type", "unknown"), matches),
            "common_response_strategy": _strategy_from_matches(incident.get("incident_type", "unknown"), matches),
            "matched_corridors": [],
            "matched_locations": [],
            "top_matches": [],
            "explainability": ["No sufficiently similar historical incidents found in the cleaned dataset."],
        }

    durations = [
        _safe_float(row.get("resolution_time_mins"))
        for row in matches
        if _safe_float(row.get("resolution_time_mins")) is not None
    ]
    average_minutes = round(sum(durations) / len(durations), 2) if durations else 0.0
    confidence = round(min(100.0, sum(row.get("similarity_score", 0.0) for row in matches) / len(matches)), 2)

    return {
        "similar_incidents": len(matches),
        "average_delay": average_minutes,
        "average_clearance_time": average_minutes,
        "confidence": confidence,
        "most_common_resolution": _resolution_from_matches(incident.get("incident_type", "unknown"), matches),
        "common_response_strategy": _strategy_from_matches(incident.get("incident_type", "unknown"), matches),
        "matched_corridors": list(dict.fromkeys(infer_corridor_label(row) for row in matches))[:5],
        "matched_locations": list(dict.fromkeys(infer_location_label(row) for row in matches))[:5],
        "top_matches": [
            {
                "incident_type": row.get("event_cause", "unknown"),
                "location": infer_location_label(row),
                "corridor": infer_corridor_label(row),
                "priority": row.get("priority", "Low"),
                "clearance_mins": _safe_float(row.get("resolution_time_mins")) or 0,
                "similarity_score": row.get("similarity_score", 0),
            }
            for row in matches[:5]
        ],
        "explainability": [
            f"Top match priority buckets: {', '.join(sorted({infer_severity(row) for row in matches}))}.",
            f"Similar incidents share {len({infer_corridor_label(row) for row in matches})} corridors.",
            f"Observed clearance times averaged {average_minutes} minutes across the matched rows.",
        ],
    }
