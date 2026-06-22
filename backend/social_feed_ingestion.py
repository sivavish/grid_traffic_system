"""Intelligence feed ingestion for ASTraM.

This module normalizes multiple feed sources into a single tagged event stream.
The adapter pattern allows future Instagram, Facebook, and X integrations to be
registered without changing downstream code.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
import xml.etree.ElementTree as ET

FeedItem = dict[str, str]

SOURCE_LABELS = {
    "rss": "News",
    "calendar": "Public Event",
    "alert": "Traffic Alert",
    "citizen": "Citizen Report",
    "social": "Social Media",
}

SOURCE_RELIABILITY = {
    "rss": 92,
    "calendar": 88,
    "alert": 96,
    "citizen": 72,
    "social": 64,
    "simulated": 55,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_time(minutes_ago: int) -> str:
    return (_utc_now() - timedelta(minutes=minutes_ago)).isoformat()


def _normalize_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _read_sources(env_name: str) -> list[str]:
    raw_value = os.getenv(env_name, "")
    if not raw_value:
        return []

    return [item.strip() for item in raw_value.split(";") if item.strip()]


def _fetch_url_text(url: str, timeout: float = 4.0) -> str | None:
    try:
        with urlopen(url, timeout=timeout) as response:
            payload = response.read()
    except (URLError, ValueError, TimeoutError):
        return None

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("latin-1", errors="ignore")


def _build_item(source: str, text: str, minutes_ago: int, source_type: str, source_url: str = "", simulated: bool = False) -> FeedItem:
    return {
        "source": source,
        "source_name": source,
        "source_type": source_type,
        "event_category": source,
        "timestamp": _iso_time(minutes_ago),
        "text": text,
        "source_url": source_url,
        "verification_status": "Simulated" if simulated else "Verified",
        "data_origin": "Simulated" if simulated else "Real Data",
        "is_simulated": "true" if simulated else "false",
        "confidence_score": str(SOURCE_RELIABILITY.get(source_type, 70)),
        "reliability_score": str(SOURCE_RELIABILITY.get(source_type, 70)),
        "original_link": source_url,
    }


def _default_simulated_items() -> list[FeedItem]:
    return [
        _build_item("Traffic Police", "A container truck has overturned near Silk Board Junction. Two lanes are blocked and congestion is building toward HSR Layout.", 4, "alert", source_url="https://www.google.com/maps/search/Silk+Board+Junction", simulated=True),
        _build_item("Citizen Report", "Crowd movement near Chinnaswamy Stadium is slowing traffic on key approaches. Officers are redirecting pedestrians.", 11, "citizen", source_url="https://www.google.com/maps/search/Chinnaswamy+Stadium", simulated=True),
        _build_item("News", "Water logging reported on the Bellandur corridor after heavy rain, with slow moving traffic in both directions.", 17, "rss", source_url="https://news.google.com", simulated=True),
        _build_item("Social Media", "Minor collision at HSR Layout service road is causing a bus and several bikes to crawl through the junction.", 23, "social", source_url="https://x.com/search?q=HSR%20Layout%20traffic", simulated=True),
    ]


def _load_rss_feed(url: str) -> list[FeedItem]:
    raw_xml = _fetch_url_text(url)
    if not raw_xml:
        return []

    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return []

    feed_items: list[FeedItem] = []
    for index, item in enumerate(root.findall(".//item")):
        title = _normalize_text(item.findtext("title"), "Traffic update")
        description = _normalize_text(item.findtext("description"), title)
        feed_items.append(_build_item("News", f"{title}. {description}".strip(), 8 + index * 6, "rss", source_url=url))
    return feed_items


def _load_json_feed(url: str, source_label: str, source_type: str, text_keys: tuple[str, ...]) -> list[FeedItem]:
    raw_json = _fetch_url_text(url)
    if not raw_json:
        return []

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return []

    entries = payload if isinstance(payload, list) else payload.get("items", []) if isinstance(payload, dict) else []
    feed_items: list[FeedItem] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue

        text = ""
        for key in text_keys:
            text = _normalize_text(entry.get(key))
            if text:
                break
        if not text:
            continue

        timestamp = _normalize_text(entry.get("timestamp") or entry.get("created_at") or entry.get("time"))
        if not timestamp:
            timestamp = _iso_time(10 + index * 5)

        feed_items.append(
            {
                "source": source_label,
                "source_name": source_label,
                "source_type": source_type,
                "event_category": source_label,
                "timestamp": timestamp,
                "text": text,
                "source_url": url,
                "verification_status": "Verified",
                "data_origin": "Real Data",
                "is_simulated": "false",
                "confidence_score": str(SOURCE_RELIABILITY.get(source_type, 70)),
                "reliability_score": str(SOURCE_RELIABILITY.get(source_type, 70)),
                "original_link": url,
            }
        )
    return feed_items


def _load_text_file(path_value: str, source_label: str, source_type: str) -> list[FeedItem]:
    path = Path(path_value)
    if not path.exists():
        return []

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [_build_item(source_label, line, 15 + index * 4, source_type, source_url=path.as_uri(), simulated=True) for index, line in enumerate(lines)]


def _collect_external_sources() -> list[FeedItem]:
    feed_items: list[FeedItem] = []

    for url in _read_sources("ASTRAM_RSS_FEEDS"):
        feed_items.extend(_load_rss_feed(url))

    for url in _read_sources("ASTRAM_PUBLIC_EVENT_CALENDARS"):
        feed_items.extend(_load_json_feed(url, "Public Event", "calendar", ("summary", "title", "text", "description")))

    for url in _read_sources("ASTRAM_TRAFFIC_ALERT_FEEDS"):
        feed_items.extend(_load_json_feed(url, "Traffic Alert", "alert", ("message", "text", "description", "summary")))

    for url in _read_sources("ASTRAM_CITIZEN_REPORTS"):
        feed_items.extend(_load_json_feed(url, "Citizen Report", "citizen", ("report", "message", "text", "description")))

    social_feed_path = os.getenv("ASTRAM_SIMULATED_SOCIAL_POSTS_FILE", "")
    if social_feed_path:
        feed_items.extend(_load_text_file(social_feed_path, "Social Media", "social"))

    return feed_items


def build_intelligence_feed(include_simulated: bool = True) -> list[FeedItem]:
    feed_items = _collect_external_sources()
    if include_simulated:
        feed_items.extend(_default_simulated_items())

    deduped: list[FeedItem] = []
    seen: set[tuple[str, str]] = set()
    for item in feed_items:
        key = (_normalize_text(item.get("source_name")), _normalize_text(item.get("text")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda entry: entry.get("timestamp", ""), reverse=True)
    return deduped


def build_feed_snapshot() -> list[FeedItem]:
    return build_intelligence_feed(include_simulated=True)
