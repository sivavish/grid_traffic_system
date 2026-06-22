"""Dataset intelligence engine for ASTraM.

This module converts incoming RSS/news/event signals into traffic impact
assessments using the cleaned ASTraM historical dataset.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import exp
from typing import Any

from data_catalog import (
    corridor_risk_ranking,
    infer_corridor_label,
    infer_incident_type,
    infer_location_label,
    infer_severity,
    load_cleaned_rows,
)


EVENT_TYPE_TO_CAUSE = {
    "accident": {"accident", "collision", "crash", "overturn", "road accident"},
    "breakdown": {"breakdown", "vehicle breakdown", "stalled", "disabled vehicle"},
    "rally": {"rally", "protest", "march", "bandh", "demonstration"},
    "weather": {"weather", "rain", "rainfall", "storm", "flood", "waterlogging", "monsoon"},
    "event": {"event", "festival", "concert", "yoga", "marathon", "public event"},
    "congestion": {"congestion", "traffic", "jam", "snarl", "gridlock", "slow moving"},
    "road closure": {"road closure", "closure", "diversion", "blocked", "lane closure"},
}

SEVERITY_TO_LEVEL = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}

SEVERITY_TO_PRIORITY = {
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "High",
}


@dataclass(frozen=True)
class MatchScore:
    row: dict[str, Any]
    score: float


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "NULL", "null"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_time(value: Any) -> datetime | None:
    text = str(value).strip() if value not in (None, "", "NULL", "null") else ""
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _canonical_event_type(event_type: str) -> str:
    normalized = _normalize_text(event_type)
    if not normalized:
        return "event"
    for canonical, variants in EVENT_TYPE_TO_CAUSE.items():
        if normalized == canonical or normalized in variants:
            return canonical
    return normalized


def _event_type_match_score(event_type: str, row: dict[str, Any]) -> float:
    normalized = _canonical_event_type(event_type)
    row_incident = infer_incident_type(row)
    row_cause = _normalize_text(row.get("event_cause"))

    if normalized == row_incident or normalized == row_cause:
        return 45.0

    for canonical, variants in EVENT_TYPE_TO_CAUSE.items():
        if normalized == canonical and row_cause in variants:
            return 40.0

    if normalized in {"congestion", "road closure"} and _normalize_text(row.get("requires_road_closure")) in {"true", "1", "yes"}:
        return 20.0

    return 0.0


def _location_match_score(location: str, row: dict[str, Any]) -> float:
    normalized_location = _normalize_text(location)
    if not normalized_location:
        return 0.0

    searchable_fields = ["address", "resolved_at_address", "corridor", "zone", "junction", "police_station", "description", "comment", "route_path"]
    score = 0.0
    for field in searchable_fields:
        field_value = _normalize_text(row.get(field))
        if not field_value:
            continue
        if normalized_location == field_value:
            return 35.0
        if normalized_location in field_value or field_value in normalized_location:
            score = max(score, 28.0)
            continue

        location_tokens = {token for token in normalized_location.replace("-", " ").replace(",", " ").split() if len(token) > 2}
        field_tokens = {token for token in field_value.replace("-", " ").replace(",", " ").split() if len(token) > 2}
        overlap = len(location_tokens & field_tokens)
        if overlap:
            score = max(score, min(24.0, 8.0 * overlap))

    return score


def _severity_match_score(severity: str, row: dict[str, Any]) -> float:
    normalized_severity = _normalize_text(severity)
    if not normalized_severity:
        return 0.0

    row_severity = infer_severity(row)
    if normalized_severity == row_severity:
        return 15.0

    if normalized_severity == "critical" and row_severity == "high":
        return 10.0
    if normalized_severity == "high" and row_severity == "critical":
        return 12.0
    if normalized_severity in {"high", "critical"} and _normalize_text(row.get("requires_road_closure")) in {"true", "1", "yes"}:
        return 6.0

    return 0.0


def _score_row(event_type: str, location: str, severity: str, row: dict[str, Any]) -> float:
    score = 0.0
    score += _event_type_match_score(event_type, row)
    score += _location_match_score(location, row)
    score += _severity_match_score(severity, row)

    if _normalize_text(row.get("requires_road_closure")) in {"true", "1", "yes"}:
        score += 5.0

    if _normalize_text(row.get("priority")) == "high":
        score += 4.0

    if _normalize_text(row.get("corridor")) != "non-corridor":
        score += 2.0

    return score


def _rank_matches(event_type: str, location: str, severity: str) -> list[MatchScore]:
    ranked: list[MatchScore] = []
    for row in load_cleaned_rows():
        ranked.append(MatchScore(row=row, score=_score_row(event_type, location, severity, row)))

    ranked.sort(key=lambda item: (item.score, _safe_float(item.row.get("resolution_time_mins")) or 0.0), reverse=True)
    shortlisted = [item for item in ranked if item.score >= 35.0]

    unique: list[MatchScore] = []
    seen: set[tuple[str, str, str, str]] = set()
    for item in shortlisted if shortlisted else ranked[:5]:
        row = item.row
        key = (
            _normalize_text(row.get("id")),
            _normalize_text(row.get("created_date")),
            _normalize_text(row.get("address")),
            _normalize_text(row.get("event_cause")),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    return unique[:8]


def _corridor_context(location: str, matches: list[MatchScore]) -> dict[str, Any]:
    corridor_counts = Counter(infer_corridor_label(item.row) for item in matches)
    ranking = corridor_risk_ranking(limit=25)
    location_text = _normalize_text(location)

    selected = None
    for entry in ranking:
        corridor_name = _normalize_text(entry["corridor"])
        if location_text and (location_text in corridor_name or corridor_name in location_text):
            selected = entry
            break

    if selected is None and corridor_counts:
        top_corridor = corridor_counts.most_common(1)[0][0]
        selected = next((entry for entry in ranking if _normalize_text(entry["corridor"]) == _normalize_text(top_corridor)), None)

    if selected is None:
        selected = ranking[0] if ranking else {"risk_score": 0.0, "corridor": "Unknown Corridor"}

    raw_risk_score = float(selected.get("risk_score", 0.0))
    normalized_risk_score = min(100.0, round(raw_risk_score / 3.0, 2))

    return {
        "corridor": selected.get("corridor", "Unknown Corridor"),
        "risk_score": normalized_risk_score,
        "raw_risk_score": raw_risk_score,
        "priority_band": selected.get("priority_band", "Low"),
        "supporting_corridors": list(corridor_counts.keys())[:5],
    }


def _peak_hour_risk(event_type: str, matches: list[MatchScore]) -> int:
    morning_evening = 0
    for item in matches:
        created = _parse_time(item.row.get("created_date"))
        if created is None:
            continue
        if 7 <= created.hour <= 11 or 16 <= created.hour <= 21:
            morning_evening += 1

    base = 20 if _canonical_event_type(event_type) in {"congestion", "road closure", "accident", "rally", "weather"} else 12
    density = min(35, morning_evening * 4)
    return min(100, base + density)


def _congestion_probability(event_type: str, severity: str, corridor_risk_score: float, matches: list[MatchScore]) -> int:
    event_weight = {
        "accident": 1.0,
        "breakdown": 0.82,
        "rally": 0.88,
        "weather": 0.9,
        "event": 0.7,
        "congestion": 1.0,
        "road closure": 0.95,
    }.get(_canonical_event_type(event_type), 0.72)

    severity_weight = SEVERITY_TO_LEVEL.get(_normalize_text(severity), 1) / 4.0
    match_density = min(1.0, len(matches) / 8.0)
    closure_bonus = 0.08 if any(_normalize_text(item.row.get("requires_road_closure")) in {"true", "1", "yes"} for item in matches) else 0.0

    raw_score = (corridor_risk_score / 100.0) * 0.42 + severity_weight * 0.28 + match_density * 0.18 + event_weight * 0.12 + closure_bonus
    probability = 100.0 / (1.0 + exp(-5.0 * (raw_score - 0.5)))
    return int(round(max(1.0, min(99.0, probability))))


def _resource_plan(event_type: str, severity: str, corridor_risk_score: float, congestion_probability: int, matches: list[MatchScore]) -> tuple[int, int]:
    normalized_event_type = _canonical_event_type(event_type)
    severity_level = SEVERITY_TO_LEVEL.get(_normalize_text(severity), 1)
    match_pressure = max(1, len(matches))

    officer_base = 2 + severity_level * 2
    officer_bonus = int(round((corridor_risk_score / 35.0) + (congestion_probability / 28.0) + (match_pressure / 3.0)))
    officers = min(24, officer_base + officer_bonus)

    barricade_base = 1 if normalized_event_type in {"breakdown", "event"} else 2
    if normalized_event_type in {"accident", "rally", "road closure", "weather"}:
        barricade_base += 1
    barricades = min(18, barricade_base + int(round(congestion_probability / 35.0)) + (1 if corridor_risk_score >= 90 else 0))

    if normalized_event_type == "road closure":
        officers += 2
        barricades += 2

    return max(1, officers), max(1, barricades)


def _average_clearance(matches: list[MatchScore], fallback_risk: float) -> float:
    durations = [_safe_float(item.row.get("resolution_time_mins")) for item in matches]
    durations = [value for value in durations if value is not None]
    if durations:
        return round(sum(durations) / len(durations), 2)

    return round(max(8.0, min(120.0, 18.0 + (fallback_risk / 3.5))), 2)


def _average_delay(average_clearance: float, congestion_probability: int) -> float:
    return round(max(5.0, average_clearance * (0.72 + congestion_probability / 240.0)), 2)


def _explain(event_type: str, location: str, severity: str, matches: list[MatchScore], corridor_context: dict[str, Any], congestion_probability: int, peak_hour_risk: int, average_delay: float, average_clearance: float) -> tuple[str, list[str], list[str]]:
    normalized_event_type = _canonical_event_type(event_type)
    why_event_matters = (
        f"{normalized_event_type.title()} signals in {location or 'the affected corridor'} are likely to disrupt lane capacity, response time, and through-traffic."
    )
    why_predictions = [
        f"Historical corridor risk is {round(corridor_context['risk_score'], 2)} for {corridor_context['corridor']}.",
        f"Peak-hour exposure is assessed at {peak_hour_risk}% based on similar incident timing in the cleaned dataset.",
        f"Congestion probability is {congestion_probability}% because matched incidents show comparable closure pressure and clearance times.",
        f"Average clearance is estimated at {average_clearance} minutes and average delay at {average_delay} minutes.",
    ]

    support_lines = []
    for item in matches[:5]:
        row = item.row
        support_lines.append(
            f"{infer_incident_type(row).title()} at {infer_location_label(row)} / {infer_corridor_label(row)} with priority {row.get('priority', 'Low')} and similarity {round(item.score, 1)}."
        )

    support_lines = list(dict.fromkeys(support_lines))

    if not support_lines:
        support_lines.append("No close historical match found, so the engine used corridor-level dataset risk.")

    return why_event_matters, why_predictions, support_lines


def generate_traffic_impact_assessment(incident: dict[str, Any]) -> dict[str, Any]:
    event_type = _normalize_text(incident.get("event_type"))
    location = _normalize_text(incident.get("location"))
    severity = _normalize_text(incident.get("severity"))

    matches = _rank_matches(event_type, location, severity)
    corridor_context = _corridor_context(location, matches)
    peak_hour_risk = _peak_hour_risk(event_type, matches)
    congestion_probability = _congestion_probability(event_type, severity, corridor_context["risk_score"], matches)
    recommended_officers, recommended_barricades = _resource_plan(event_type, severity, corridor_context["risk_score"], congestion_probability, matches)
    average_clearance = _average_clearance(matches, corridor_context["risk_score"])
    average_delay = _average_delay(average_clearance, congestion_probability)
    historical_matches = len(matches)
    why_event_matters, why_predictions, support_lines = _explain(
        event_type,
        location,
        severity,
        matches,
        corridor_context,
        congestion_probability,
        peak_hour_risk,
        average_delay,
        average_clearance,
    )

    return {
        "historical_matches": historical_matches,
        "corridor_risk_score": round(corridor_context["risk_score"], 2),
        "peak_hour_risk": peak_hour_risk,
        "congestion_probability": congestion_probability,
        "average_delay": average_delay,
        "average_clearance": average_clearance,
        "recommended_officers": recommended_officers,
        "recommended_barricades": recommended_barricades,
        "supporting_corridors": corridor_context["supporting_corridors"],
        "most_relevant_corridor": corridor_context["corridor"],
        "explanation": {
            "why_this_event_matters": why_event_matters,
            "why_these_predictions_were_made": why_predictions,
            "historical_incident_support": support_lines,
        },
        "historical_matches_detail": [
            {
                "incident_type": infer_incident_type(item.row),
                "location": infer_location_label(item.row),
                "corridor": infer_corridor_label(item.row),
                "priority": item.row.get("priority", "Low"),
                "clearance_mins": _safe_float(item.row.get("resolution_time_mins")) or 0.0,
                "similarity_score": round(item.score, 2),
                "event_cause": item.row.get("event_cause", "unknown"),
            }
            for item in matches[:5]
        ],
    }
