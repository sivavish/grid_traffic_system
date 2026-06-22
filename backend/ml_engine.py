"""Dataset-trained impact prediction from cleaned ASTraM data."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime
from functools import lru_cache
from math import expm1, fsum, log1p
from pathlib import Path
from typing import Any

from data_catalog import (
    corridor_statistics,
    infer_corridor_label,
    infer_incident_type,
    infer_location_label,
    infer_severity,
    infer_time_of_day,
    infer_vehicle_type,
    load_cleaned_rows,
)

DATA_PATH = Path(__file__).parent / "data" / "cleaned_astram_data.csv"

INCIDENT_TYPE_TO_EVENT_CAUSE = {
    "breakdown": "vehicle_breakdown",
    "accident": "accident",
    "tree": "tree_fall",
    "waterlogging": "water_logging",
    "protest": "public_event",
}

KNOWN_LOCATIONS = [
    "HSR Layout",
    "Silk Board",
    "Koramangala",
    "Bellandur",
    "Marathahalli",
    "Peenya",
    "Mysore Road",
    "Magadi Road",
    "Bellary Road",
    "Yeshwanthpura",
    "Whitefield",
    "Electronic City",
    "Jayanagar",
    "JP Nagar",
    "Kengeri",
    "Madiwala",
    "Halasuru",
    "Basavanagudi",
    "Shivajinagar",
]

SEVERITY_LABELS = {"low", "medium", "high", "critical", "unknown"}
TIME_OF_DAY_LABELS = {"morning", "afternoon", "evening", "night", "unknown"}
TOP_VEHICLE_TYPES = 25


class LinearRegressionModel:
    def __init__(self, feature_names: list[str], weights: list[float], bias: float):
        self.feature_names = feature_names
        self.weights = weights
        self.bias = bias

    def predict_one(self, features: dict[str, float]) -> float:
        score = self.bias
        for index, feature_name in enumerate(self.feature_names):
            score += self.weights[index] * features.get(feature_name, 0.0)
        return score

    def predict(self, feature_rows: list[dict[str, float]]) -> list[float]:
        return [self.predict_one(feature_row) for feature_row in feature_rows]


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _load_cleaned_data() -> list[dict[str, Any]]:
    return load_cleaned_rows()


def _parse_datetime(value: Any) -> datetime | None:
    text = _normalize_text(value)
    if not text or text in {"null", "none"}:
        return None

    try:
        return datetime.fromisoformat(text.replace("z", "+00:00"))
    except ValueError:
        return None


def _infer_time_of_day(created_date: Any) -> str:
    timestamp = _parse_datetime(created_date)
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


def _infer_location_label(row: dict[str, Any]) -> str:
    searchable_fields = [
        "address",
        "police_station",
        "junction",
        "corridor",
        "zone",
        "resolved_at_address",
        "comment",
        "description",
    ]
    for field in searchable_fields:
        text = _normalize_text(row.get(field))
        for location in KNOWN_LOCATIONS:
            if location.lower() in text:
                return location
    return "other"


def _derive_incident_type(event_cause: Any) -> str:
    normalized_event_cause = _normalize_text(event_cause)
    for incident_type, mapped_cause in INCIDENT_TYPE_TO_EVENT_CAUSE.items():
        if normalized_event_cause == mapped_cause:
            return incident_type
    return normalized_event_cause or "unknown"


def _safe_float(value: Any) -> float | None:
    try:
        if value in (None, "", "NULL", "null"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _prepare_training_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, str]], list[float]]:
    features: list[dict[str, str]] = []
    targets: list[float] = []

    for row in rows:
        target_value = _safe_float(row.get("resolution_time_mins"))
        created_date = _parse_datetime(row.get("created_date"))
        if target_value is None or created_date is None:
            continue

        features.append(
            {
                "incident_type": infer_incident_type(row),
                "location_label": infer_location_label(row),
                "severity_label": infer_severity(row),
                "time_of_day": infer_time_of_day(created_date),
                "vehicle_type": infer_vehicle_type(row),
                "corridor_label": infer_corridor_label(row),
                "closure_flag": "1" if _normalize_text(row.get("requires_road_closure")).lower() in {"true", "1", "yes"} else "0",
                "has_comment": "1" if _normalize_text(row.get("comment")) else "0",
                "has_station": "1" if _normalize_text(row.get("police_station")) else "0",
            }
        )
        targets.append(log1p(target_value))

    return features, targets


def _feature_key(field_name: str, value: str) -> str:
    return f"{field_name}={value or 'unknown'}"


def _build_feature_dicts(feature_rows: list[dict[str, str]], vehicle_vocab: set[str]) -> list[dict[str, float]]:
    built_rows: list[dict[str, float]] = []
    for row in feature_rows:
        encoded = {
            _feature_key("incident_type", row.get("incident_type", "unknown")): 1.0,
            _feature_key("location_label", row.get("location_label", "other")): 1.0,
            _feature_key("severity_label", row.get("severity_label", "low")): 1.0,
            _feature_key("time_of_day", row.get("time_of_day", "unknown")): 1.0,
            _feature_key("corridor_label", row.get("corridor_label", "unknown")): 1.0,
            _feature_key(
                "vehicle_type",
                row.get("vehicle_type", "unknown") if row.get("vehicle_type", "unknown") in vehicle_vocab else "other",
            ): 1.0,
            "closure_flag": float(row.get("closure_flag", "0") == "1"),
            "has_comment": float(row.get("has_comment", "0") == "1"),
            "has_station": float(row.get("has_station", "0") == "1"),
        }
        built_rows.append(encoded)
    return built_rows


def _collect_feature_names(feature_rows: list[dict[str, str]]) -> tuple[list[str], set[str]]:
    vehicle_counter = Counter(row.get("vehicle_type", "unknown") or "unknown" for row in feature_rows)
    vehicle_vocab = {
        vehicle_type
        for vehicle_type, _ in vehicle_counter.most_common(TOP_VEHICLE_TYPES)
    }

    feature_names = sorted(
        {
            _feature_key("incident_type", row.get("incident_type", "unknown"))
            for row in feature_rows
        }
        | {
            _feature_key("location_label", row.get("location_label", "other"))
            for row in feature_rows
        }
        | {
            _feature_key("severity_label", row.get("severity_label", "low"))
            for row in feature_rows
        }
        | {
            _feature_key("time_of_day", row.get("time_of_day", "unknown"))
            for row in feature_rows
        }
        | {
            _feature_key("corridor_label", row.get("corridor_label", "unknown"))
            for row in feature_rows
        }
        | {
            _feature_key("vehicle_type", vehicle_type)
            for vehicle_type in vehicle_vocab
        }
        | {"vehicle_type=other", "closure_flag", "has_comment", "has_station"}
    )

    return feature_names, vehicle_vocab


def _dot(weights: list[float], feature_names: list[str], feature_row: dict[str, float], bias: float) -> float:
    score = bias
    for index, feature_name in enumerate(feature_names):
        score += weights[index] * feature_row.get(feature_name, 0.0)
    return score


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]

    for pivot_index in range(size):
        pivot_row = max(range(pivot_index, size), key=lambda row_index: abs(augmented[row_index][pivot_index]))
        if abs(augmented[pivot_row][pivot_index]) < 1e-12:
            continue
        if pivot_row != pivot_index:
            augmented[pivot_index], augmented[pivot_row] = augmented[pivot_row], augmented[pivot_index]

        pivot_value = augmented[pivot_index][pivot_index]
        for column_index in range(pivot_index, size + 1):
            augmented[pivot_index][column_index] /= pivot_value

        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = augmented[row_index][pivot_index]
            if factor == 0:
                continue
            for column_index in range(pivot_index, size + 1):
                augmented[row_index][column_index] -= factor * augmented[pivot_index][column_index]

    return [augmented[row_index][size] for row_index in range(size)]


def _fit_linear_regression(feature_rows: list[dict[str, float]], targets: list[float], feature_names: list[str]) -> LinearRegressionModel:
    if not feature_rows:
        return LinearRegressionModel([], [], 0.0)

    size = len(feature_names) + 1
    xtx = [[0.0 for _ in range(size)] for _ in range(size)]
    xty = [0.0 for _ in range(size)]

    for feature_row, target in zip(feature_rows, targets):
        row_vector = [1.0] + [feature_row.get(feature_name, 0.0) for feature_name in feature_names]
        for i in range(size):
            xty[i] += row_vector[i] * target
            for j in range(size):
                xtx[i][j] += row_vector[i] * row_vector[j]

    regularization = 1e-3
    for index in range(1, size):
        xtx[index][index] += regularization

    coefficients = _solve_linear_system(xtx, xty)
    bias = coefficients[0]
    weights = coefficients[1:]
    return LinearRegressionModel(feature_names, weights, bias)


@lru_cache(maxsize=1)
def _train_prediction_model() -> tuple[LinearRegressionModel, float]:
    rows = _load_cleaned_data()
    training_features, targets = _prepare_training_rows(rows)
    feature_names, vehicle_vocab = _collect_feature_names(training_features)
    encoded_features = _build_feature_dicts(training_features, vehicle_vocab)
    model = _fit_linear_regression(encoded_features, targets, feature_names)

    if not encoded_features:
        return model, 0.0

    predictions = [model.predict_one(feature_row) for feature_row in encoded_features]
    mean_target = fsum(targets) / len(targets)
    total_variance = fsum((target - mean_target) ** 2 for target in targets)
    residual_variance = fsum((target - prediction) ** 2 for target, prediction in zip(targets, predictions))
    score = 0.0 if total_variance == 0 else max(0.0, 1.0 - (residual_variance / total_variance))
    model._vehicle_vocab = vehicle_vocab  # type: ignore[attr-defined]
    return model, score


def _build_feature_row(incident_type: str, location: str, vehicle_type: str = "unknown", severity: str = "low") -> dict[str, float]:
    normalized_location = _normalize_text(location)
    inferred_location = "other"
    for known_location in KNOWN_LOCATIONS:
        if known_location.lower() in normalized_location:
            inferred_location = known_location
            break

    normalized_incident_type = _normalize_text(incident_type) or "unknown"
    normalized_vehicle_type = _normalize_text(vehicle_type) or "unknown"
    if normalized_vehicle_type not in {"bmtc_bus", "truck", "heavy_vehicle", "private_bus", "private_car", "lcv", "auto", "ksrtc_bus"}:
        normalized_vehicle_type = "other"

    normalized_severity = _normalize_text(severity) or "low"
    if normalized_severity not in SEVERITY_LABELS:
        normalized_severity = "low"

    corridor_label = inferred_location if inferred_location != "other" else normalized_location.split(",")[0] if normalized_location else "unknown"
    closure_flag = 1.0 if any(token in normalized_location for token in ("closure", "blocked", "jam", "stalled")) else 0.0

    feature_dict = {
        _feature_key("incident_type", normalized_incident_type): 1.0,
        _feature_key("location_label", inferred_location): 1.0,
        _feature_key("severity_label", normalized_severity): 1.0,
        _feature_key("time_of_day", "unknown"): 1.0,
        _feature_key("corridor_label", corridor_label or "unknown"): 1.0,
        _feature_key("vehicle_type", normalized_vehicle_type): 1.0,
        "closure_flag": closure_flag,
        "has_comment": 0.0,
        "has_station": 0.0,
    }
    return feature_dict


def predict_impact(
    incident_type: str,
    location: str,
    vehicle_type: str = "unknown",
    severity: str = "low",
    lanes_blocked: int = 0,
    crowd_size: str = "unknown",
    confidence_score: float = 0.0,
) -> dict:
    model, model_score = _train_prediction_model()
    feature_row = _build_feature_row(incident_type, location, vehicle_type=vehicle_type, severity=severity)
    predicted_delay = round(max(expm1(float(model.predict_one(feature_row))), 0.0), 2)

    severity_weight = {
        "low": 0.8,
        "medium": 1.0,
        "high": 1.25,
        "critical": 1.45,
    }.get(_normalize_text(severity), 1.0)
    lane_pressure = max(0, int(lanes_blocked))
    crowd_pressure = {
        "small": 0,
        "medium": 1,
        "large": 2,
        "massive": 3,
    }.get(_normalize_text(crowd_size), 0)
    delay_pressure = max(0.0, predicted_delay / 18.0)

    police_required = int(round(3 + delay_pressure * severity_weight + lane_pressure * 1.5 + crowd_pressure))
    barricades = int(round(6 + predicted_delay / 4.5 + lane_pressure * 5 + crowd_pressure * 3))

    vehicle_key = _normalize_text(vehicle_type)
    incident_key = _normalize_text(incident_type)
    tow_trucks = 0
    if vehicle_key in {"truck", "heavy_vehicle", "bmtc_bus", "ksrtc_bus", "private_bus"} or incident_key in {"breakdown", "accident"}:
        tow_trucks = 1
    if lane_pressure >= 2 or predicted_delay >= 60 or vehicle_key in {"container truck", "lorry"}:
        tow_trucks = max(tow_trucks, 2)

    clearance_bonus = lane_pressure * 6 + crowd_pressure * 4 + (10 if tow_trucks else 0)
    predicted_clearance = round(max(predicted_delay + clearance_bonus, predicted_delay * 1.08), 2)

    prediction_confidence = round(
        max(0.0, min(100.0, (model_score * 100.0 * 0.85) + confidence_score * 0.15)),
        2,
    )

    reasoning = [
        f"Model score {round(model_score * 100.0, 2)}% from cleaned dataset training.",
        f"Severity weight applied: {severity_weight}.",
        f"Lanes blocked: {lane_pressure}.",
        f"Crowd pressure bucket: {crowd_pressure}.",
    ]

    return {
        "predicted_delay_mins": predicted_delay,
        "predicted_clearance_mins": predicted_clearance,
        "model_score": round(model_score, 3),
        "prediction_confidence": prediction_confidence,
        "training_source": "cleaned_astram_data.csv",
        "police_required": police_required,
        "barricades": barricades,
        "tow_trucks": tow_trucks,
        "reasoning": reasoning,
    }
