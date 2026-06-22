"""Prompt templates for the ASTraM NLP pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from social_feed_ingestion import build_feed_snapshot


EXTRACTION_SYSTEM_PROMPT = (
    "You are an incident extraction engine for Bengaluru traffic operations. "
    "Read raw unstructured text from traffic police reports, citizen reports, news alerts, or social media style posts. "
    "Return only valid JSON with these keys exactly: incident_type, location, severity, vehicle_type, crowd_size, lanes_blocked, impact_radius_meters, expected_congestion, expected_impact, confidence_score, explainability. "
    "Use concise normalized values. If a value is unknown, set it to unknown for strings or 0 for numeric fields. "
    "Severity must be one of low, medium, high, critical, or unknown. confidence_score must be a number from 0 to 100. explainability must be a short list of evidence phrases."
)

EXTRACTION_USER_PROMPT = (
    "Extract structured incident information from the following text:\n\n{text}\n\n"
    "Return only JSON. Do not add markdown, commentary, or code fences."
)


def build_extraction_messages(text: str):
    return [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": EXTRACTION_USER_PROMPT.format(text=text.strip())},
    ]


def build_event_feed_simulation() -> list[dict[str, str]]:
    return build_feed_snapshot()