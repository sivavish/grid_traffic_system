"""Ripple-effect propagation for ASTraM.

The model uses cleaned incident coordinates and nearby historical locations to
project impact across 15, 30, 45, and 60 minute horizons.
"""

from __future__ import annotations

from typing import Any

from data_catalog import load_cleaned_rows, nearby_locations, row_coordinates


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _find_reference_row(source_node: str) -> dict[str, Any] | None:
    normalized_source = _normalize_text(source_node)
    for row in load_cleaned_rows():
        text_candidates = [
            row.get("address"),
            row.get("resolved_at_address"),
            row.get("junction"),
            row.get("corridor"),
            row.get("zone"),
            row.get("police_station"),
            row.get("description"),
            row.get("comment"),
        ]
        for candidate in text_candidates:
            if normalized_source and normalized_source in _normalize_text(candidate):
                return row
    return None


def _horizon_radius_meters(delay_mins: float, horizon_mins: int, crowd_multiplier: float, lane_multiplier: float) -> float:
    base = max(300.0, delay_mins * 18.0)
    horizon_scale = {15: 0.55, 30: 0.85, 45: 1.15, 60: 1.45}.get(horizon_mins, 1.0)
    return round(base * horizon_scale * crowd_multiplier * lane_multiplier, 2)


def _secondary_delay(delay_mins: float, horizon_mins: int, proximity_factor: float, severity_factor: float) -> float:
    decay = {15: 0.32, 30: 0.46, 45: 0.58, 60: 0.68}.get(horizon_mins, 0.4)
    return round(max(0.0, delay_mins * decay * proximity_factor * severity_factor), 2)


def _incident_intensity(row: dict[str, Any] | None, delay_mins: float) -> tuple[float, float]:
    if row is None:
        return 1.0, 1.0

    lane_count = 0.0
    for field_name in ("comment", "description", "junction"):
        text = _normalize_text(row.get(field_name))
        if "two lanes" in text or "2 lanes" in text:
            lane_count = max(lane_count, 2.0)
        elif "three lanes" in text or "3 lanes" in text:
            lane_count = max(lane_count, 3.0)
        elif "one lane" in text or "1 lane" in text:
            lane_count = max(lane_count, 1.0)

    closure_multiplier = 1.12 if _normalize_text(row.get("requires_road_closure")) in {"true", "1", "yes"} else 1.0
    severity_multiplier = 1.0 + min(0.45, delay_mins / 180.0)
    lane_multiplier = 1.0 + min(0.35, lane_count * 0.08)
    crowd_multiplier = 1.0 + (0.18 if _normalize_text(row.get("event_cause")) == "public_event" else 0.0)
    return severity_multiplier * closure_multiplier, lane_multiplier * crowd_multiplier


def calculate_ripple(source_node: str, delay_mins: float) -> list[dict[str, Any]]:
    reference_row = _find_reference_row(source_node)
    coordinates = row_coordinates(reference_row) if reference_row else None
    if coordinates is None:
        return []

    close_locations = nearby_locations(coordinates[0], coordinates[1], limit=6)
    severity_factor, lane_crowd_factor = _incident_intensity(reference_row, delay_mins)
    ripple_rows: list[dict[str, Any]] = []

    for horizon in (15, 30, 45, 60):
        for index, nearby_item in enumerate(close_locations[:4]):
            distance = float(nearby_item.get("distance", 0.0))
            proximity_factor = max(0.55, 1.0 - (distance / 0.12))
            expected_delay = _secondary_delay(delay_mins, horizon, proximity_factor, severity_factor)
            radius = _horizon_radius_meters(delay_mins, horizon, lane_crowd_factor, severity_factor)

            ripple_rows.append(
                {
                    "label": f"{horizon} Minute Impact Zone",
                    "horizon_mins": horizon,
                    "node": nearby_item.get("location", source_node),
                    "corridor": nearby_item.get("corridor", ""),
                    "coordinates": nearby_item.get("coordinates") or coordinates,
                    "radius_meters": radius,
                    "secondary_delay_mins": expected_delay,
                    "confidence": round(max(20.0, min(98.0, 72.0 + (proximity_factor * 12.0) + (severity_factor * 6.0) - index * 3.0)), 2),
                    "reason": f"Ripple projected from historical proximity and corridor similarity over the {horizon}-minute horizon.",
                }
            )

    return ripple_rows
