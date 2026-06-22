"""Operational action planning for ASTraM."""

from __future__ import annotations

from typing import Any


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _priority_level(severity: str, predicted_delay_mins: float, route_confidence: float) -> str:
    normalized_severity = _normalize_text(severity)
    if normalized_severity == "critical" or predicted_delay_mins >= 90 or route_confidence < 45:
        return "Critical"
    if normalized_severity == "high" or predicted_delay_mins >= 45 or route_confidence < 60:
        return "High"
    if normalized_severity == "medium" or predicted_delay_mins >= 20:
        return "Medium"
    return "Low"


def generate_action_plan(
    incident: dict[str, Any],
    predicted_delay_mins: float,
    historical_evidence: dict[str, Any] | None,
    route_optimization: dict[str, Any] | None,
) -> dict[str, Any]:
    historical_evidence = historical_evidence or {}
    route_optimization = route_optimization or {}

    similar_incidents = float(historical_evidence.get("similar_incidents", 0))
    historical_confidence = float(historical_evidence.get("confidence", 0))
    route_confidence = float(route_optimization.get("route_confidence_score", 0))
    lanes_blocked = max(0, int(float(incident.get("lanes_blocked", 0) or 0)))
    crowd_size = _normalize_text(incident.get("crowd_size", "unknown"))
    crowd_pressure = {
        "small": 0,
        "medium": 1,
        "large": 2,
        "massive": 3,
        "unknown": 0,
    }.get(crowd_size, 0)

    priority_level = _priority_level(incident.get("severity", "unknown"), predicted_delay_mins, route_confidence)

    officers_required = int(round(3 + predicted_delay_mins / 12 + lanes_blocked * 1.5 + crowd_pressure * 2))
    if priority_level == "Medium":
        officers_required += 2
    elif priority_level == "High":
        officers_required += 4
    elif priority_level == "Critical":
        officers_required += 7

    officers_required += 2 if similar_incidents >= 3 else 0
    officers_required += 2 if historical_confidence >= 75 else 0

    barricades_required = int(round(6 + predicted_delay_mins / 4 + lanes_blocked * 4 + crowd_pressure * 3))
    if priority_level == "High":
        barricades_required += 4
    elif priority_level == "Critical":
        barricades_required += 8

    tow_trucks_required = 0
    incident_type = _normalize_text(incident.get("incident_type"))
    vehicle_type = _normalize_text(incident.get("vehicle_type"))
    if incident_type in {"breakdown", "accident"} or vehicle_type in {"truck", "bus", "heavy_vehicle", "private_bus"}:
        tow_trucks_required = 1
    if incident_type == "breakdown" and predicted_delay_mins >= 60:
        tow_trucks_required = 2
    if lanes_blocked >= 2 or predicted_delay_mins >= 90:
        tow_trucks_required = max(tow_trucks_required, 2)

    deployment_zones = []
    location = incident.get("location") or ""
    if location:
        deployment_zones.append(location)

    route_points = route_optimization.get("diversion_points", [])
    deployment_zones.extend(route_points[:2])
    closures = route_optimization.get("recommended_closures", [])
    deployment_zones.extend(closures[:1])
    impact_zones = route_optimization.get("impact_zones", [])
    deployment_zones.extend(zone.get("label", "") for zone in impact_zones[:2])

    seen = set()
    normalized_zones = []
    for zone in deployment_zones:
        key = _normalize_text(zone)
        if key and key not in seen:
            seen.add(key)
            normalized_zones.append(zone)

    rationale = [
        f"Priority level resolved to {priority_level} from severity, delay, and route confidence.",
        f"Lane blockage of {lanes_blocked} and crowd pressure {crowd_pressure} increased deployment intensity.",
        f"Historical confidence {historical_confidence} and similar incidents {similar_incidents} influenced officer count.",
    ]

    return {
        "officers_required": officers_required,
        "barricades_required": barricades_required,
        "tow_trucks_required": tow_trucks_required,
        "deployment_zones": normalized_zones,
        "priority_level": priority_level,
        "rationale": rationale,
    }
