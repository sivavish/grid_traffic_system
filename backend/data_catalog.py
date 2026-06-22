"""Shared dataset access and feature engineering helpers for ASTraM."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache
from math import sqrt
from pathlib import Path
from typing import Any

DATA_PATH = Path(__file__).parent / "data" / "cleaned_astram_data.csv"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).lower()


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "NULL", "null"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    text = _normalize_key(value)
    if not text or text in {"null", "none"}:
        return None

    try:
        return datetime.fromisoformat(text.replace("z", "+00:00"))
    except ValueError:
        return None


@lru_cache(maxsize=1)
def load_cleaned_rows() -> list[dict[str, Any]]:
    with DATA_PATH.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@lru_cache(maxsize=1)
def dataset_columns() -> list[str]:
    rows = load_cleaned_rows()
    return list(rows[0].keys()) if rows else []


def row_coordinates(row: dict[str, Any]) -> tuple[float, float] | None:
    candidates = (
        (_safe_float(row.get("latitude")), _safe_float(row.get("longitude"))),
        (_safe_float(row.get("resolved_at_latitude")), _safe_float(row.get("resolved_at_longitude"))),
        (_safe_float(row.get("endlatitude")), _safe_float(row.get("endlongitude"))),
    )
    for latitude, longitude in candidates:
        if latitude is not None and longitude is not None and latitude != 0 and longitude != 0:
            return latitude, longitude
    return None


def extract_location_text(row: dict[str, Any]) -> str:
    fields = [
        "address",
        "resolved_at_address",
        "junction",
        "corridor",
        "zone",
        "police_station",
        "description",
        "comment",
        "route_path",
    ]
    for field in fields:
        value = _normalize_text(row.get(field))
        if value:
            return value
    return ""


def infer_corridor_label(row: dict[str, Any]) -> str:
    for field in ("corridor", "zone", "junction", "police_station"):
        value = _normalize_text(row.get(field))
        if value:
            return value

    address = extract_location_text(row)
    if address:
        return address.split(",")[0]

    return "Unknown Corridor"


def infer_location_label(row: dict[str, Any]) -> str:
    for field in ("junction", "corridor", "zone", "police_station", "resolved_at_address"):
        value = _normalize_text(row.get(field))
        if value:
            return value

    address = _normalize_text(row.get("address"))
    if address:
        return address.split(",")[0]

    return "Unknown Location"


def infer_time_of_day(value: Any) -> str:
    timestamp = _parse_datetime(value)
    if timestamp is None:
        return "unknown"

    hour = timestamp.hour
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def infer_incident_type(row: dict[str, Any]) -> str:
    normalized = _normalize_key(row.get("event_cause"))
    mappings = {
        "vehicle_breakdown": "breakdown",
        "accident": "accident",
        "tree_fall": "tree",
        "water_logging": "waterlogging",
        "public_event": "protest",
    }
    return mappings.get(normalized, normalized or "unknown")


def infer_severity(row: dict[str, Any]) -> str:
    priority = _normalize_key(row.get("priority"))
    if priority in {"low", "medium", "high", "critical"}:
        return priority
    if _normalize_key(row.get("requires_road_closure")) in {"true", "1", "yes"}:
        return "high"
    return "low"


def infer_vehicle_type(row: dict[str, Any]) -> str:
    value = _normalize_key(row.get("veh_type"))
    return value or "unknown"


def corridor_statistics() -> list[dict[str, Any]]:
    rows = load_cleaned_rows()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[infer_corridor_label(row)].append(row)

    stats: list[dict[str, Any]] = []
    for corridor, items in grouped.items():
        valid_delays = [
            _safe_float(item.get("resolution_time_mins"))
            for item in items
            if _safe_float(item.get("resolution_time_mins")) is not None
        ]
        closure_rate = sum(1 for item in items if _normalize_key(item.get("requires_road_closure")) in {"true", "1", "yes"}) / len(items)
        stats.append(
            {
                "corridor": corridor,
                "incident_count": len(items),
                "average_clearance_mins": round(sum(valid_delays) / len(valid_delays), 2) if valid_delays else 0.0,
                "closure_rate": round(closure_rate, 3),
                "avg_priority": Counter(infer_severity(item) for item in items).most_common(1)[0][0],
            }
        )

    stats.sort(key=lambda item: (item["incident_count"], item["average_clearance_mins"]), reverse=True)
    return stats


def location_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in load_cleaned_rows():
        label = infer_location_label(row)
        coords = row_coordinates(row)
        bucket = index.setdefault(
            label,
            {
                "label": label,
                "corridor": infer_corridor_label(row),
                "coordinates": coords,
                "count": 0,
                "rows": [],
            },
        )
        bucket["count"] += 1
        bucket["rows"].append(row)
        if bucket["coordinates"] is None and coords is not None:
            bucket["coordinates"] = coords
    return index


def nearby_locations(latitude: float | None, longitude: float | None, limit: int = 5) -> list[dict[str, Any]]:
    if latitude is None or longitude is None:
        return []

    ranked = []
    for label, info in location_index().items():
        coords = info.get("coordinates")
        if not coords:
            continue
        distance = sqrt((coords[0] - latitude) ** 2 + (coords[1] - longitude) ** 2)
        ranked.append({"location": label, "corridor": info.get("corridor", ""), "distance": distance, "coordinates": coords})

    ranked.sort(key=lambda item: item["distance"])
    return ranked[:limit]


def feature_engineering_report() -> dict[str, Any]:
    rows = load_cleaned_rows()
    used_fields = {
        "latitude",
        "longitude",
        "resolved_at_latitude",
        "resolved_at_longitude",
        "address",
        "resolved_at_address",
        "event_cause",
        "requires_road_closure",
        "created_date",
        "description",
        "veh_type",
        "corridor",
        "priority",
        "comment",
        "police_station",
        "zone",
        "junction",
        "resolution_time_mins",
        "endlatitude",
        "endlongitude",
        "status",
    }
    columns = dataset_columns()
    unused_fields = [column for column in columns if column not in used_fields]

    return {
        "row_count": len(rows),
        "column_count": len(columns),
        "used_fields": sorted(used_fields),
        "unused_fields": unused_fields,
        "top_corridors": corridor_statistics()[:10],
    }


def corridor_risk_ranking(limit: int = 10) -> list[dict[str, Any]]:
    ranking = []
    for stat in corridor_statistics():
        score = round(
            (stat["incident_count"] * 2.0)
            + (stat["closure_rate"] * 100.0)
            + (stat["average_clearance_mins"] / 2.5),
            2,
        )
        ranking.append(
            {
                "corridor": stat["corridor"],
                "risk_score": score,
                "incident_count": stat["incident_count"],
                "closure_rate": stat["closure_rate"],
                "average_clearance_mins": stat["average_clearance_mins"],
                "priority_band": "Critical" if score >= 140 else "High" if score >= 90 else "Medium" if score >= 55 else "Low",
            }
        )

    ranking.sort(key=lambda item: (item["risk_score"], item["incident_count"]), reverse=True)
    return ranking[:limit]


def command_center_overview() -> dict[str, Any]:
    rows = load_cleaned_rows()
    active_incidents = len(rows)
    critical_incidents = sum(1 for row in rows if infer_severity(row) == "critical")
    high_incidents = sum(1 for row in rows if infer_severity(row) == "high")
    average_delay = round(
        sum(_safe_float(row.get("resolution_time_mins")) or 0.0 for row in rows) / len(rows),
        2,
    ) if rows else 0.0
    affected_corridors = len({infer_corridor_label(row) for row in rows})
    average_clearance = average_delay
    current_status = (
        "Critical" if critical_incidents >= 3 else "High Alert" if high_incidents >= 8 else "Elevated" if active_incidents >= 10 else "Normal"
    )

    return {
        "active_incidents": active_incidents,
        "critical_incidents": critical_incidents,
        "high_severity_incidents": high_incidents,
        "average_delay_mins": average_delay,
        "affected_corridors": affected_corridors,
        "average_clearance_mins": average_clearance,
        "current_traffic_status": current_status,
        "corridor_risk_ranking": corridor_risk_ranking(8),
    }
