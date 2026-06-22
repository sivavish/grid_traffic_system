"""LLM-powered incident extraction for the ASTraM prototype."""

from __future__ import annotations

import json
import importlib
import os
import re
from typing import Any, Dict


def _load_optional(name: str, attribute: str):
    try:
        module = importlib.import_module(name)
    except ImportError:
        return None
    return getattr(module, attribute, None)


load_dotenv = _load_optional("dotenv", "load_dotenv")
Groq = _load_optional("groq", "Groq")

if load_dotenv is None:
    def load_dotenv() -> bool:
        return False

from prompt_templates import build_extraction_messages

load_dotenv()

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")
_GROQ_API_KEY = os.getenv("GROQ_API_KEY")
_GROQ_CLIENT = Groq(api_key=_GROQ_API_KEY) if Groq and _GROQ_API_KEY else None

DEFAULT_EXTRACTION = {
    "incident_type": "unknown",
    "location": "unknown",
    "severity": "unknown",
    "vehicle_type": "unknown",
    "crowd_size": "unknown",
    "lanes_blocked": 0,
    "impact_radius_meters": 0,
    "expected_congestion": "unknown",
    "expected_impact": "unknown",
    "confidence_score": 0,
    "explainability": [],
}

ALLOWED_SEVERITIES = {"low", "medium", "high", "critical", "unknown"}
DEFAULT_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _coerce_text(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _coerce_lanes_blocked(value: Any) -> int:
    try:
        lanes = int(float(value))
    except (TypeError, ValueError):
        return 0
    return max(lanes, 0)


def _coerce_confidence_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0

    if 0.0 <= score <= 1.0:
        score *= 100.0

    return round(max(0.0, min(score, 100.0)), 2)


def _coerce_radius(value: Any) -> float:
    try:
        radius = float(value)
    except (TypeError, ValueError):
        return 0.0
    return round(max(0.0, radius), 2)


def _coerce_explainability(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split("|") if part.strip()]
    return [str(value).strip()]


def _normalize_extraction(candidate: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(DEFAULT_EXTRACTION)
    normalized["incident_type"] = _coerce_text(candidate.get("incident_type"))
    normalized["location"] = _coerce_text(candidate.get("location"))

    severity = _coerce_text(candidate.get("severity"), "unknown").lower()
    normalized["severity"] = severity if severity in ALLOWED_SEVERITIES else "unknown"

    normalized["vehicle_type"] = _coerce_text(candidate.get("vehicle_type"))
    normalized["crowd_size"] = _coerce_text(candidate.get("crowd_size"))
    normalized["lanes_blocked"] = _coerce_lanes_blocked(candidate.get("lanes_blocked"))
    normalized["impact_radius_meters"] = _coerce_radius(candidate.get("impact_radius_meters"))
    normalized["expected_congestion"] = _coerce_text(candidate.get("expected_congestion"))
    normalized["expected_impact"] = _coerce_text(candidate.get("expected_impact"))
    normalized["confidence_score"] = _coerce_confidence_score(candidate.get("confidence_score"))
    normalized["explainability"] = _coerce_explainability(candidate.get("explainability"))

    return normalized


def _extract_json_payload(raw_text: str) -> Dict[str, Any]:
    cleaned = raw_text.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = DEFAULT_JSON_PATTERN.search(cleaned)
        if not match:
            raise ValueError("Groq response did not contain JSON")
        return json.loads(match.group(0))


def _fallback_extract(text: str) -> Dict[str, Any]:
    normalized = text.lower()

    incident_type = "unknown"
    if any(token in normalized for token in ("breakdown", "stalled", "stranded")):
        incident_type = "breakdown"
    elif any(
        token in normalized
        for token in (
            "accident",
            "crash",
            "collision",
            "hit-and-run",
            "overturned",
            "overturn",
            "rolled over",
        )
    ):
        incident_type = "accident"
    elif any(token in normalized for token in ("tree", "fallen tree", "tree fall")):
        incident_type = "tree"
    elif any(token in normalized for token in ("waterlogging", "water logging", "water-logging", "flooding")):
        incident_type = "waterlogging"
    elif any(token in normalized for token in ("protest", "crowd", "demonstration", "rally")):
        incident_type = "protest"

    location = "unknown"
    for place in ("HSR Layout", "Silk Board", "Koramangala", "Bellandur", "Marathahalli", "Peenya", "Chinnaswamy Stadium"):
        if place.lower() in normalized:
            location = place
            break

    lanes_blocked = 0
    lane_match = re.search(r"(\d+)\s+lanes?\s+blocked", normalized)
    if lane_match:
        lanes_blocked = int(lane_match.group(1))
    else:
        word_lane_match = re.search(
            r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\s+lanes?\s+are?\s+blocked\b",
            normalized,
        )
        if word_lane_match:
            word_to_number = {
                "one": 1,
                "two": 2,
                "three": 3,
                "four": 4,
                "five": 5,
                "six": 6,
                "seven": 7,
                "eight": 8,
                "nine": 9,
                "ten": 10,
            }
            lanes_blocked = word_to_number.get(word_lane_match.group(1), 0)

    vehicle_type = "unknown"
    for token in ("container truck", "truck", "bus", "car", "bike", "lorry"):
        if token and token in normalized:
            vehicle_type = token
            break

    crowd_size = "unknown"
    if any(token in normalized for token in ("huge crowd", "large crowd", "massive crowd", "gathering")):
        crowd_size = "large"

    expected_impact = "localized congestion"
    expected_congestion = "moderate"
    impact_radius_meters = 600
    if incident_type == "protest":
        expected_impact = "crowd movement disruption and route diversions"
        expected_congestion = "high"
        impact_radius_meters = 1400
    elif incident_type == "accident":
        expected_impact = "lane blockage and queue spillback"
        expected_congestion = "high"
        impact_radius_meters = 900
    elif incident_type == "waterlogging":
        expected_congestion = "high"
        impact_radius_meters = 1100

    severity = "high" if incident_type != "unknown" else "medium"
    confidence_score = 68.0 if incident_type != "unknown" else 25.0
    explainability = []
    if incident_type != "unknown":
        explainability.append(f"Detected incident pattern: {incident_type}")
    if location != "unknown":
        explainability.append(f"Matched location cue: {location}")
    if lanes_blocked:
        explainability.append(f"Parsed lane blockage count: {lanes_blocked}")
    if crowd_size != "unknown":
        explainability.append(f"Crowd signal: {crowd_size}")

    return _normalize_extraction(
        {
            "incident_type": incident_type,
            "location": location,
            "severity": severity,
            "vehicle_type": vehicle_type,
            "crowd_size": crowd_size,
            "lanes_blocked": lanes_blocked,
            "impact_radius_meters": impact_radius_meters,
            "expected_congestion": expected_congestion,
            "expected_impact": expected_impact,
            "confidence_score": confidence_score,
            "explainability": explainability,
        }
    )


def extract_incident(text: str) -> dict:
    if not text or not text.strip():
        return dict(DEFAULT_EXTRACTION)

    if _GROQ_CLIENT is None:
        return _fallback_extract(text)

    try:
        response = _GROQ_CLIENT.chat.completions.create(
            model=GROQ_MODEL,
            messages=build_extraction_messages(text),
            temperature=0,
            max_tokens=500,
        )
        raw_content = response.choices[0].message.content or ""
        parsed_content = _extract_json_payload(raw_content)
        return _normalize_extraction(parsed_content)
    except Exception:
        return _fallback_extract(text)
