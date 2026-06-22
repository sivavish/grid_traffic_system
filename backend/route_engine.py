"""Traffic diversion planning for the ASTraM command center."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from data_catalog import corridor_statistics, load_cleaned_rows, nearby_locations, row_coordinates


@dataclass(frozen=True)
class RoutePlan:
    route_a: str
    route_b: str
    route_c: str
    split_percentages: list[int]
    recommended_closures: list[str]
    diversion_points: list[str]
    route_lines: list[dict[str, Any]]
    epicenter_coordinates: list[float]
    base_confidence: float


LOCATION_COORDS = {
    "silk board junction": [12.9175, 77.6234],
    "silk board": [12.9175, 77.6234],
    "hsr layout": [12.9121, 77.6446],
    "hsr junction": [12.9121, 77.6446],
    "bellandur": [12.9304, 77.6784],
    "bellandur gate": [12.9304, 77.6784],
    "marathahalli": [12.9569, 77.7011],
    "koramangala": [12.9352, 77.6245],
    "peenya": [13.0166, 77.5054],
    "mysore road": [12.9490, 77.5298],
    "whitefield": [12.9698, 77.7500],
    "electronic city": [12.8456, 77.6603],
    "jayanagar": [12.9250, 77.5938],
    "jp nagar": [12.9081, 77.5850],
    "kengeri": [12.9178, 77.4834],
    "yeshwanthpura": [13.0238, 77.5530],
    "yeshwanthpur": [13.0238, 77.5530],
}

ROUTE_LIBRARY = {
    "silk board junction": RoutePlan(
        route_a="Outer Ring Road",
        route_b="Sarjapur Road",
        route_c="HSR Service Road",
        split_percentages=[50, 30, 20],
        recommended_closures=["Silk Board Flyover Entry"],
        diversion_points=["HSR Junction", "Agara Signal"],
        route_lines=[
            {
                "label": "Outer Ring Road",
                "color": "#22c55e",
                "coordinates": [[12.9175, 77.6234], [12.9304, 77.6784], [12.9569, 77.7011]],
            },
            {
                "label": "Sarjapur Road",
                "color": "#f59e0b",
                "coordinates": [[12.9175, 77.6234], [12.9240, 77.6520], [12.9382, 77.6815]],
            },
            {
                "label": "HSR Service Road",
                "color": "#38bdf8",
                "coordinates": [[12.9175, 77.6234], [12.9138, 77.6356], [12.9121, 77.6446]],
            },
        ],
        epicenter_coordinates=[12.9175, 77.6234],
        base_confidence=94.0,
    ),
    "hsr layout": RoutePlan(
        route_a="Outer Ring Road",
        route_b="Sarjapur Road",
        route_c="Bellandur Inner Loop",
        split_percentages=[48, 32, 20],
        recommended_closures=["HSR Flyover Ramp"],
        diversion_points=["Agara Signal", "Bellandur Gate"],
        route_lines=[
            {
                "label": "Outer Ring Road",
                "color": "#22c55e",
                "coordinates": [[12.9121, 77.6446], [12.9304, 77.6784], [12.9569, 77.7011]],
            },
            {
                "label": "Sarjapur Road",
                "color": "#f59e0b",
                "coordinates": [[12.9121, 77.6446], [12.9238, 77.6630], [12.9382, 77.6815]],
            },
            {
                "label": "Bellandur Inner Loop",
                "color": "#38bdf8",
                "coordinates": [[12.9121, 77.6446], [12.9221, 77.6638], [12.9304, 77.6784]],
            },
        ],
        epicenter_coordinates=[12.9121, 77.6446],
        base_confidence=92.0,
    ),
    "bellandur": RoutePlan(
        route_a="Outer Ring Road",
        route_b="Sarjapur Road",
        route_c="Old Airport Road",
        split_percentages=[45, 35, 20],
        recommended_closures=["Bellandur Gate Entry"],
        diversion_points=["Marathahalli Bridge", "Agara Junction"],
        route_lines=[
            {
                "label": "Outer Ring Road",
                "color": "#22c55e",
                "coordinates": [[12.9304, 77.6784], [12.9569, 77.7011], [12.9698, 77.7500]],
            },
            {
                "label": "Sarjapur Road",
                "color": "#f59e0b",
                "coordinates": [[12.9304, 77.6784], [12.9418, 77.6894], [12.9569, 77.7011]],
            },
            {
                "label": "Old Airport Road",
                "color": "#38bdf8",
                "coordinates": [[12.9304, 77.6784], [12.9352, 77.6445], [12.9476, 77.6295]],
            },
        ],
        epicenter_coordinates=[12.9304, 77.6784],
        base_confidence=88.0,
    ),
    "marathahalli": RoutePlan(
        route_a="Outer Ring Road",
        route_b="Varthur Road",
        route_c="Old Airport Road",
        split_percentages=[46, 32, 22],
        recommended_closures=["Marathahalli Bridge Entry"],
        diversion_points=["Doddanekundi Signal", "Bellandur Gate"],
        route_lines=[
            {
                "label": "Outer Ring Road",
                "color": "#22c55e",
                "coordinates": [[12.9569, 77.7011], [12.9698, 77.7500], [12.9857, 77.7600]],
            },
            {
                "label": "Varthur Road",
                "color": "#f59e0b",
                "coordinates": [[12.9569, 77.7011], [12.9657, 77.7231], [12.9698, 77.7500]],
            },
            {
                "label": "Old Airport Road",
                "color": "#38bdf8",
                "coordinates": [[12.9569, 77.7011], [12.9410, 77.6890], [12.9304, 77.6784]],
            },
        ],
        epicenter_coordinates=[12.9569, 77.7011],
        base_confidence=89.0,
    ),
    "koramangala": RoutePlan(
        route_a="Inner Ring Road",
        route_b="100 Feet Road",
        route_c="Ejipura Main Road",
        split_percentages=[44, 34, 22],
        recommended_closures=["Koramangala 80 Feet Road Entry"],
        diversion_points=["Sony Signal", "Adugodi Signal"],
        route_lines=[
            {
                "label": "Inner Ring Road",
                "color": "#22c55e",
                "coordinates": [[12.9352, 77.6245], [12.9415, 77.6328], [12.9475, 77.6390]],
            },
            {
                "label": "100 Feet Road",
                "color": "#f59e0b",
                "coordinates": [[12.9352, 77.6245], [12.9299, 77.6157], [12.9237, 77.6072]],
            },
            {
                "label": "Ejipura Main Road",
                "color": "#38bdf8",
                "coordinates": [[12.9352, 77.6245], [12.9276, 77.6205], [12.9218, 77.6215]],
            },
        ],
        epicenter_coordinates=[12.9352, 77.6245],
        base_confidence=86.0,
    ),
    "peenya": RoutePlan(
        route_a="Tumkur Road",
        route_b="Chord Road",
        route_c="Magadi Road",
        split_percentages=[52, 28, 20],
        recommended_closures=["Peenya 2nd Stage Entry"],
        diversion_points=["Jalahalli Cross", "Goraguntepalya"],
        route_lines=[
            {
                "label": "Tumkur Road",
                "color": "#22c55e",
                "coordinates": [[13.0166, 77.5054], [13.0238, 77.5530], [13.0324, 77.5338]],
            },
            {
                "label": "Chord Road",
                "color": "#f59e0b",
                "coordinates": [[13.0166, 77.5054], [13.0251, 77.5291], [13.0324, 77.5338]],
            },
            {
                "label": "Magadi Road",
                "color": "#38bdf8",
                "coordinates": [[13.0166, 77.5054], [13.0045, 77.5188], [12.9892, 77.5503]],
            },
        ],
        epicenter_coordinates=[13.0166, 77.5054],
        base_confidence=87.0,
    ),
    "mysore road": RoutePlan(
        route_a="Magadi Road",
        route_b="Outer Ring Road",
        route_c="Kengeri Main Road",
        split_percentages=[49, 31, 20],
        recommended_closures=["Mysore Road Entry Ramp"],
        diversion_points=["Kengeri Junction", "BHEL Circle"],
        route_lines=[
            {
                "label": "Magadi Road",
                "color": "#22c55e",
                "coordinates": [[12.9490, 77.5298], [12.9580, 77.5629], [12.9842, 77.5747]],
            },
            {
                "label": "Outer Ring Road",
                "color": "#f59e0b",
                "coordinates": [[12.9490, 77.5298], [12.9630, 77.5400], [12.9820, 77.5199]],
            },
            {
                "label": "Kengeri Main Road",
                "color": "#38bdf8",
                "coordinates": [[12.9490, 77.5298], [12.9360, 77.5187], [12.9178, 77.4834]],
            },
        ],
        epicenter_coordinates=[12.9490, 77.5298],
        base_confidence=84.0,
    ),
    "whitefield": RoutePlan(
        route_a="Varthur Road",
        route_b="Old Madras Road",
        route_c="Outer Ring Road",
        split_percentages=[47, 33, 20],
        recommended_closures=["Whitefield Main Road Entry"],
        diversion_points=["Hope Farm Junction", "ITPL Main Gate"],
        route_lines=[
            {
                "label": "Varthur Road",
                "color": "#22c55e",
                "coordinates": [[12.9698, 77.7500], [12.9569, 77.7011], [12.9304, 77.6784]],
            },
            {
                "label": "Old Madras Road",
                "color": "#f59e0b",
                "coordinates": [[12.9698, 77.7500], [12.9788, 77.7242], [12.9850, 77.7083]],
            },
            {
                "label": "Outer Ring Road",
                "color": "#38bdf8",
                "coordinates": [[12.9698, 77.7500], [12.9569, 77.7011], [12.9304, 77.6784]],
            },
        ],
        epicenter_coordinates=[12.9698, 77.7500],
        base_confidence=85.0,
    ),
    "electronic city": RoutePlan(
        route_a="Hosur Road",
        route_b="Bommanahalli Main Road",
        route_c="Bannerghatta Road",
        split_percentages=[46, 34, 20],
        recommended_closures=["Electronic City Elevated Ramp"],
        diversion_points=["Bommanahalli Junction", "Silk Board Junction"],
        route_lines=[
            {
                "label": "Hosur Road",
                "color": "#22c55e",
                "coordinates": [[12.8456, 77.6603], [12.8648, 77.6530], [12.8895, 77.6408]],
            },
            {
                "label": "Bommanahalli Main Road",
                "color": "#f59e0b",
                "coordinates": [[12.8456, 77.6603], [12.8577, 77.6494], [12.8691, 77.6427]],
            },
            {
                "label": "Bannerghatta Road",
                "color": "#38bdf8",
                "coordinates": [[12.8456, 77.6603], [12.8765, 77.6290], [12.9114, 77.6000]],
            },
        ],
        epicenter_coordinates=[12.8456, 77.6603],
        base_confidence=84.0,
    ),
    "jayanagar": RoutePlan(
        route_a="Inner Ring Road",
        route_b="RV Road",
        route_c="Bannerghatta Road",
        split_percentages=[42, 36, 22],
        recommended_closures=["Jayanagar 4th Block Entry"],
        diversion_points=["South End Circle", "Adugodi Signal"],
        route_lines=[
            {
                "label": "Inner Ring Road",
                "color": "#22c55e",
                "coordinates": [[12.9250, 77.5938], [12.9302, 77.6040], [12.9352, 77.6245]],
            },
            {
                "label": "RV Road",
                "color": "#f59e0b",
                "coordinates": [[12.9250, 77.5938], [12.9190, 77.5890], [12.9145, 77.5650]],
            },
            {
                "label": "Bannerghatta Road",
                "color": "#38bdf8",
                "coordinates": [[12.9250, 77.5938], [12.9150, 77.6030], [12.9114, 77.6000]],
            },
        ],
        epicenter_coordinates=[12.9250, 77.5938],
        base_confidence=83.0,
    ),
    "jp nagar": RoutePlan(
        route_a="Bannerghatta Road",
        route_b="Outer Ring Road",
        route_c="Kanakapura Road",
        split_percentages=[44, 34, 22],
        recommended_closures=["JP Nagar 6th Phase Entry"],
        diversion_points=["Banashankari Junction", "Dairy Circle"],
        route_lines=[
            {
                "label": "Bannerghatta Road",
                "color": "#22c55e",
                "coordinates": [[12.9081, 77.5850], [12.9114, 77.6000], [12.9175, 77.6234]],
            },
            {
                "label": "Outer Ring Road",
                "color": "#f59e0b",
                "coordinates": [[12.9081, 77.5850], [12.9145, 77.5650], [12.9250, 77.5938]],
            },
            {
                "label": "Kanakapura Road",
                "color": "#38bdf8",
                "coordinates": [[12.9081, 77.5850], [12.8955, 77.5894], [12.8800, 77.5600]],
            },
        ],
        epicenter_coordinates=[12.9081, 77.5850],
        base_confidence=82.0,
    ),
    "kengeri": RoutePlan(
        route_a="Mysore Road",
        route_b="Magadi Road",
        route_c="Nagarbhavi Main Road",
        split_percentages=[48, 32, 20],
        recommended_closures=["Kengeri Main Road Entry"],
        diversion_points=["Ullal Junction", "Bidadi Road Merge"],
        route_lines=[
            {
                "label": "Mysore Road",
                "color": "#22c55e",
                "coordinates": [[12.9178, 77.4834], [12.9360, 77.5187], [12.9490, 77.5298]],
            },
            {
                "label": "Magadi Road",
                "color": "#f59e0b",
                "coordinates": [[12.9178, 77.4834], [12.9304, 77.5000], [12.9490, 77.5298]],
            },
            {
                "label": "Nagarbhavi Main Road",
                "color": "#38bdf8",
                "coordinates": [[12.9178, 77.4834], [12.9330, 77.5004], [12.9559, 77.5458]],
            },
        ],
        epicenter_coordinates=[12.9178, 77.4834],
        base_confidence=81.0,
    ),
    "yeshwanthpura": RoutePlan(
        route_a="Tumkur Road",
        route_b="Bellary Road",
        route_c="Magadi Road",
        split_percentages=[51, 29, 20],
        recommended_closures=["Yeshwanthpura Circle Entry"],
        diversion_points=["Goraguntepalya", "Jalahalli Cross"],
        route_lines=[
            {
                "label": "Tumkur Road",
                "color": "#22c55e",
                "coordinates": [[13.0238, 77.5530], [13.0180, 77.5555], [13.0324, 77.5338]],
            },
            {
                "label": "Bellary Road",
                "color": "#f59e0b",
                "coordinates": [[13.0238, 77.5530], [13.0360, 77.5893], [13.0634, 77.5933]],
            },
            {
                "label": "Magadi Road",
                "color": "#38bdf8",
                "coordinates": [[13.0238, 77.5530], [13.0100, 77.5707], [12.9892, 77.5503]],
            },
        ],
        epicenter_coordinates=[13.0238, 77.5530],
        base_confidence=83.0,
    ),
}

DEFAULT_PLAN = RoutePlan(
    route_a="Outer Ring Road",
    route_b="Neighbourhood Bypass",
    route_c="Service Road Diversion",
    split_percentages=[50, 30, 20],
    recommended_closures=["Incident Approach Lane"],
    diversion_points=["Nearest Signal", "Alternate Junction"],
    route_lines=[
        {
            "label": "Outer Ring Road",
            "color": "#22c55e",
            "coordinates": [[12.9300, 77.6400], [12.9410, 77.6560], [12.9560, 77.6710]],
        },
        {
            "label": "Neighbourhood Bypass",
            "color": "#f59e0b",
            "coordinates": [[12.9300, 77.6400], [12.9240, 77.6540], [12.9180, 77.6680]],
        },
        {
            "label": "Service Road Diversion",
            "color": "#38bdf8",
            "coordinates": [[12.9300, 77.6400], [12.9200, 77.6320], [12.9100, 77.6240]],
        },
    ],
    epicenter_coordinates=[12.9300, 77.6400],
    base_confidence=72.0,
)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _resolve_plan(location: str) -> RoutePlan:
    normalized_location = _normalize_text(location)
    for key, plan in ROUTE_LIBRARY.items():
        if key in normalized_location:
            return plan
    return DEFAULT_PLAN


def _adjust_split_percentages(base_splits: list[int], severity: str, predicted_delay_mins: float, historical_similarity: float) -> list[int]:
    severity_multiplier = {
        "low": -4,
        "medium": 0,
        "high": 6,
        "critical": 10,
    }.get(_normalize_text(severity), 0)

    delay_pressure = 0
    if predicted_delay_mins >= 90:
        delay_pressure = 8
    elif predicted_delay_mins >= 45:
        delay_pressure = 5
    elif predicted_delay_mins >= 20:
        delay_pressure = 2

    history_pressure = 4 if historical_similarity >= 75 else 2 if historical_similarity >= 45 else 0
    route_a = min(70, max(35, base_splits[0] + severity_multiplier + delay_pressure + history_pressure))
    route_b = min(40, max(20, base_splits[1] - max(0, severity_multiplier // 2)))
    route_c = max(10, 100 - route_a - route_b)

    total = route_a + route_b + route_c
    if total != 100:
        route_c += 100 - total

    return [route_a, route_b, route_c]


def _route_confidence(historical_confidence: float, similar_incidents: float, predicted_delay_mins: float, candidate_count: int) -> float:
    delay_bonus = min(12.0, predicted_delay_mins / 8.0)
    candidate_bonus = min(8.0, candidate_count * 1.5)
    confidence = 46.0 + historical_confidence * 0.35 + similar_incidents * 3.0 + delay_bonus + candidate_bonus
    return round(max(0.0, min(confidence, 100.0)), 2)


def _route_lines(epicenter_coords: list[float], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    palette = ["#3b82f6", "#60a5fa", "#93c5fd"]
    route_lines: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates[:3]):
        coords = candidate.get("coordinates")
        if not coords:
            continue
        route_lines.append(
            {
                "label": candidate.get("corridor") or candidate.get("location") or f"Diversion {index + 1}",
                "color": palette[index % len(palette)],
                "coordinates": [epicenter_coords, coords],
            }
        )
    return route_lines


def _impact_zones(epicenter_coords: list[float], predicted_delay_mins: float, historical_confidence: float) -> list[dict[str, Any]]:
    confidence_pressure = 1.0 + min(0.4, historical_confidence / 250.0)
    horizon_scales = {15: 0.55, 30: 0.85, 45: 1.15, 60: 1.45}
    zones = []
    for horizon, scale in horizon_scales.items():
        zones.append(
            {
                "label": f"{horizon} Minute Impact Zone",
                "radius_meters": round(max(500.0, predicted_delay_mins * 20.0 * scale * confidence_pressure), 2),
                "color": {15: "#f59e0b", 30: "#fde047", 45: "#fde047", 60: "#fde047"}[horizon],
                "coordinates": epicenter_coords,
            }
        )
    return zones


def _resolve_epicenter(incident: dict[str, Any]) -> tuple[list[float], str, str, list[dict[str, Any]]]:
    location_text = str(incident.get("location") or "").strip()
    normalized_location = _normalize_text(location_text)
    matches = []
    for row in load_cleaned_rows():
        searchable = [row.get("address"), row.get("resolved_at_address"), row.get("corridor"), row.get("junction"), row.get("zone"), row.get("police_station"), row.get("description"), row.get("comment")]
        if normalized_location and any(normalized_location in _normalize_text(item) for item in searchable):
            matches.append(row)
    if matches:
        best_row = matches[0]
        coords = row_coordinates(best_row)
        if coords:
            corridor = str(best_row.get("corridor") or best_row.get("zone") or best_row.get("junction") or location_text or "Unknown Corridor")
            label = str(best_row.get("junction") or best_row.get("resolved_at_address") or corridor)
            return [coords[0], coords[1]], corridor, label, matches

    rows = load_cleaned_rows()
    if rows:
        fallback = rows[0]
        coords = row_coordinates(fallback)
        if coords:
            corridor = str(fallback.get("corridor") or fallback.get("zone") or fallback.get("junction") or location_text or "Unknown Corridor")
            label = str(fallback.get("junction") or fallback.get("resolved_at_address") or corridor)
            return [coords[0], coords[1]], corridor, label, matches

    return [12.9300, 77.6400], location_text or "Unknown Corridor", location_text or "Unknown Location", matches


def _recent_corridors(matches: list[dict[str, Any]], epicenter_corridor: str) -> list[str]:
    ranked = OrderedDict()
    for row in matches:
        corridor = str(row.get("corridor") or row.get("zone") or row.get("junction") or row.get("police_station") or "").strip()
        if corridor and _normalize_text(corridor) != _normalize_text(epicenter_corridor):
            ranked.setdefault(corridor, 0)
            ranked[corridor] += 1

    for stat in corridor_statistics():
        corridor = stat["corridor"]
        if _normalize_text(corridor) != _normalize_text(epicenter_corridor):
            ranked.setdefault(corridor, 0)

    return list(ranked.keys())


def _diversion_candidates(epicenter_coords: list[float], epicenter_location: str, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nearby = nearby_locations(epicenter_coords[0], epicenter_coords[1], limit=8)
    candidates: list[dict[str, Any]] = []
    for item in nearby:
        if _normalize_text(item.get("location")) == _normalize_text(epicenter_location):
            continue
        candidates.append(item)

    for row in matches:
        coords = row_coordinates(row)
        if not coords:
            continue
        candidates.append({"location": str(row.get("junction") or row.get("resolved_at_address") or row.get("corridor") or "Diversion"), "corridor": str(row.get("corridor") or row.get("zone") or row.get("junction") or ""), "distance": 0.0, "coordinates": [coords[0], coords[1]]})

    unique: list[dict[str, Any]] = []
    seen = set()
    for item in candidates:
        key = _normalize_text(item.get("location") or item.get("corridor"))
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def _resource_splits(incident: dict[str, Any], predicted_delay_mins: float, historical_confidence: float, closure_rate: float) -> list[int]:
    severity = _normalize_text(incident.get("severity", "low"))
    base = {"low": 0.9, "medium": 1.05, "high": 1.22, "critical": 1.4}.get(severity, 1.0)
    lane_pressure = max(0, int(float(incident.get("lanes_blocked", 0) or 0)))
    delay_pressure = max(1.0, predicted_delay_mins / 20.0)
    history_pressure = 1.0 + min(0.35, historical_confidence / 300.0)
    closure_pressure = 1.0 + min(0.2, closure_rate)

    raw_scores = [45.0 * base * delay_pressure * history_pressure, 28.0 * base * (1.0 + lane_pressure * 0.25) * closure_pressure, 18.0 * base * (1.0 + min(0.75, lane_pressure * 0.3))]
    total = sum(raw_scores)
    if total <= 0:
        return [50, 30, 20]

    splits = [round(score / total * 100.0) for score in raw_scores]
    delta = 100 - sum(splits)
    splits[0] += delta
    return splits


def generate_route_optimization(
    incident: dict[str, Any],
    historical_evidence: dict[str, Any] | None = None,
    predicted_delay_mins: float = 0.0,
) -> dict[str, Any]:
    historical_evidence = historical_evidence or {}
    epicenter_coords, epicenter_corridor, epicenter_label, matches = _resolve_epicenter(incident)
    close_candidates = _diversion_candidates(epicenter_coords, epicenter_label, matches)
    corridor_candidates = _recent_corridors(matches, epicenter_corridor)

    route_names = [epicenter_corridor]
    for corridor in corridor_candidates:
        if corridor not in route_names:
            route_names.append(corridor)
        if len(route_names) == 3:
            break
    while len(route_names) < 3:
        route_names.append(f"Diversion {len(route_names) + 1}")

    closure_candidates = [str(row.get("resolved_at_address") or row.get("junction") or row.get("address") or row.get("corridor") or "") for row in matches if _normalize_text(row.get("requires_road_closure")) in {"true", "1", "yes"}]
    if not closure_candidates and close_candidates:
        closure_candidates.append(str(close_candidates[0].get("location") or close_candidates[0].get("corridor") or ""))

    diversion_points = [str(item.get("location") or item.get("corridor")) for item in close_candidates[:3] if item.get("location") or item.get("corridor")]
    unique_closures: list[str] = []
    seen_closure = set()
    for item in closure_candidates:
        key = _normalize_text(item)
        if key and key not in seen_closure:
            seen_closure.add(key)
            unique_closures.append(item)

    unique_diversions: list[str] = []
    seen_diversion = set()
    for item in diversion_points:
        key = _normalize_text(item)
        if key and key not in seen_diversion:
            seen_diversion.add(key)
            unique_diversions.append(item)

    similar_incidents = float(historical_evidence.get("similar_incidents", 0))
    historical_confidence = float(historical_evidence.get("confidence", 0))
    closure_rate = sum(1 for row in matches if _normalize_text(row.get("requires_road_closure")) in {"true", "1", "yes"}) / len(matches) if matches else 0.0

    split_percentages = _resource_splits(incident, predicted_delay_mins, historical_confidence, closure_rate)
    route_confidence_score = _route_confidence(historical_confidence, similar_incidents, predicted_delay_mins, len(close_candidates))

    route_lines = _route_lines(epicenter_coords, close_candidates)
    if not route_lines:
        route_lines = [{"label": route_names[0], "color": "#22c55e", "coordinates": [epicenter_coords, [epicenter_coords[0] + 0.01, epicenter_coords[1] + 0.01]]}]

    impact_zones = _impact_zones(epicenter_coords, predicted_delay_mins, historical_confidence)

    route_rationale = {
        "location_match": epicenter_label,
        "historical_similarity": historical_confidence,
        "similar_incidents": similar_incidents,
        "candidate_diversions": unique_diversions,
        "closure_triggers": unique_closures,
    }

    return {
        "route_a": route_names[0],
        "route_b": route_names[1],
        "route_c": route_names[2],
        "split_percentages": split_percentages,
        "recommended_closures": unique_closures[:3],
        "diversion_points": unique_diversions[:3],
        "route_confidence_score": route_confidence_score,
        "route_lines": route_lines,
        "epicenter_coordinates": epicenter_coords,
        "impact_zones": impact_zones,
        "route_rationale": route_rationale,
        "top_diversions": unique_diversions[:3],
    }
