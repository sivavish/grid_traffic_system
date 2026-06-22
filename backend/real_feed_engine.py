"""Live event intelligence for ASTraM.

The engine aggregates multiple real source adapters into a consistent schema
that includes source attribution, published time, confidence, verification
status, and a normalized event type. Simulated fallback items are only used
when every configured source fails or returns no items.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from html import unescape
import xml.etree.ElementTree as ET

from feed_sources import DEFAULT_FEED_SOURCES

EventItem = dict[str, Any]

SOURCE_CONFIDENCE = {
    "rss": 92,
    "traffic_alert": 97,
    "public_event": 86,
    "citizen_report": 70,
    "simulated": 55,
}

SOURCE_LABELS = {
    "rss": "News",
    "traffic_alert": "Traffic Police",
    "public_event": "Public Event",
    "citizen_report": "Citizen Report",
    "simulated": "Simulated",
}

EVENT_CLASSIFICATION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Road Closure", ("road closure", "closed", "closure", "diversion", "diverted", "lane closure", "traffic block", "blockage", "repair work", "road work", "maintenance")),
    ("Accident", ("accident", "crash", "collision", "overturn", "overturned", "pile-up", "hit and run", "injured", "fatal", "multi-vehicle")),
    ("Breakdown", ("breakdown", "stalled", "stranded", "vehicle failure", "mechanical failure", "bus breakdown", "lorry breakdown", "flat tyre")),
    ("Weather", ("weather", "rain", "rainfall", "shower", "storm", "thunderstorm", "lightning", "hail", "flood", "waterlogging", "monsoon", "yellow alert", "red alert")),
    ("Rally", ("rally", "protest", "march", "demonstration", "dharna", "agitation", "procession", "bandh")),
    ("Event", ("event", "festival", "concert", "yoga day", "marathon", "expo", "fair", "celebration", "launch", "inauguration", "public event")),
    ("Congestion", ("traffic", "congestion", "jam", "snarl", "snarls", "gridlock", "slow moving", "slow-moving", "queue", "heavy traffic", "crawling")),
]

_LAST_REFRESH_AT = ""
_LAST_HEALTH = {
    "real_sources_active": 0,
    "failed_sources": 0,
    "last_refresh": "",
    "events_collected": 0,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_timestamp(minutes_ago: int) -> str:
    return (_utc_now() - timedelta(minutes=minutes_ago)).isoformat()


def _normalize_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _read_sources(env_name: str) -> list[str]:
    raw_value = os.getenv(env_name, "").strip()
    if raw_value:
        return [item.strip() for item in re.split(r"[;\n,]", raw_value) if item.strip()]

    return list(DEFAULT_FEED_SOURCES.get(env_name, []))


def _fetch_text(url: str, timeout: float = 5.0) -> str | None:
    try:
        with urlopen(url, timeout=timeout) as response:
            payload = response.read()
    except (URLError, ValueError, TimeoutError, OSError):
        return None

    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return payload.decode("latin-1", errors="ignore")


def _strip_html(value: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(cleaned).split())


def _confidence_for(source_type: str, simulated: bool) -> int:
    if simulated:
        return SOURCE_CONFIDENCE["simulated"]
    return SOURCE_CONFIDENCE.get(source_type, 72)


def _parse_timestamp(value: str | None) -> str:
    if not value:
        return ""

    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, IndexError):
        return _normalize_text(value)


def _classify_event(title: str, description: str) -> str:
    haystack = f"{title} {description}".lower()
    for event_type, keywords in EVENT_CLASSIFICATION_RULES:
        if any(keyword in haystack for keyword in keywords):
            return event_type
    return "Event"


def _build_event(
    *,
    title: str,
    description: str,
    source: str,
    source_url: str,
    published_time: str,
    confidence: int,
    verification_status: str,
    event_type: str,
    simulated: bool,
    source_type: str,
) -> EventItem:
    return {
        "title": title,
        "description": description,
        "source": source,
        "source_name": source,
        "source_type": source_type,
        "source_url": source_url,
        "original_link": source_url,
        "timestamp": published_time,
        "published_time": published_time,
        "confidence": confidence,
        "confidence_score": confidence,
        "reliability_score": confidence,
        "verification_status": verification_status,
        "event_type": event_type,
        "data_origin": "Simulated" if simulated else "Real Data",
        "is_simulated": simulated,
    }


def _default_simulated_events() -> list[EventItem]:
    now = _utc_now()
    simulated_rows = [
        (
            "Traffic Police Alert",
            "A container truck has overturned near Silk Board Junction. Two lanes are blocked and congestion is building toward HSR Layout.",
            "Traffic Police",
            "traffic_alert",
            "incident",
            "https://www.google.com/maps/search/Silk+Board+Junction",
            -4,
        ),
        (
            "Citizen Report",
            "Crowd movement near Chinnaswamy Stadium is slowing traffic on key approaches. Officers are redirecting pedestrians.",
            "Citizen Report",
            "citizen_report",
            "event",
            "https://www.google.com/maps/search/Chinnaswamy+Stadium",
            -11,
        ),
        (
            "News Alert",
            "Water logging reported on the Bellandur corridor after heavy rain, with slow moving traffic in both directions.",
            "News",
            "rss",
            "weather",
            "https://news.google.com",
            -17,
        ),
        (
            "Public Event",
            "A scheduled political rally is expected near Freedom Park and may affect adjoining corridors.",
            "Public Event",
            "public_event",
            "event",
            "https://www.google.com/maps/search/Freedom+Park+Bengaluru",
            -23,
        ),
    ]

    events: list[EventItem] = []
    for title, description, source, source_type, event_type, source_url, minutes_ago in simulated_rows:
        events.append(
            _build_event(
                title=title,
                description=description,
                source=source,
                source_url=source_url,
                published_time=(now + timedelta(minutes=minutes_ago)).isoformat(),
                confidence=_confidence_for("simulated", True),
                verification_status="Simulated",
                event_type=event_type,
                simulated=True,
                source_type=source_type,
            )
        )
    return events


def _load_rss_feed(url: str) -> list[EventItem]:
    raw_xml = _fetch_text(url)
    if not raw_xml:
        return []

    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return []

    events: list[EventItem] = []
    for index, item in enumerate(root.findall(".//item")):
        title = _normalize_text(item.findtext("title"), "Traffic update")
        description = _strip_html(_normalize_text(item.findtext("description"), title))
        link = _normalize_text(item.findtext("link"), url)
        source_element = item.find("source")
        source_name = _normalize_text(source_element.text if source_element is not None else None, "News")
        source_url = _normalize_text(source_element.attrib.get("url") if source_element is not None else None, link)
        published_time = _parse_timestamp(item.findtext("pubDate") or item.findtext("published") or item.findtext("updated"))
        if not published_time:
            published_time = _iso_timestamp(8 + index * 6)

        event_type = _classify_event(title, description)
        verification_status = "Verified"
        confidence = _confidence_for("rss", False)
        events.append(
            _build_event(
                title=title,
                description=description,
                source=source_name,
                source_url=source_url or link,
                published_time=published_time,
                confidence=confidence,
                verification_status=verification_status,
                event_type=event_type,
                simulated=False,
                source_type="rss",
            )
        )
    return events


def _load_json_feed(url: str, source: str, source_type: str, event_type: str, text_keys: tuple[str, ...]) -> list[EventItem]:
    raw_json = _fetch_text(url)
    if not raw_json:
        return []

    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return []

    entries = payload if isinstance(payload, list) else payload.get("items", []) if isinstance(payload, dict) else []
    events: list[EventItem] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue

        title = _normalize_text(entry.get("title") or entry.get("name") or entry.get("summary"), source)
        description = ""
        for key in text_keys:
            description = _normalize_text(entry.get(key))
            if description:
                break
        if not description:
            description = title

        source_url = _normalize_text(entry.get("url") or entry.get("link") or url, url)
        timestamp = _parse_timestamp(entry.get("timestamp") or entry.get("created_at") or entry.get("time") or entry.get("published_time") or entry.get("published_at"))
        if not timestamp:
            timestamp = _iso_timestamp(10 + index * 5)

        simulated = source_type == "citizen_report"
        verification_status = "Unverified" if simulated else "Verified"
        if source_type == "public_event":
            verification_status = "Verified"
        classification = _classify_event(title, description)

        events.append(
            _build_event(
                title=title,
                description=description,
                source=source,
                source_url=source_url,
                published_time=timestamp,
                confidence=_confidence_for(source_type, simulated),
                verification_status=verification_status,
                event_type=classification if event_type == "event" else event_type,
                simulated=False,
                source_type=source_type,
            )
        )
    return events


def _count_configured_sources() -> int:
    return sum(len(_read_sources(env_name)) for env_name in DEFAULT_FEED_SOURCES)


def _collect_live_sources() -> tuple[list[EventItem], dict[str, Any]]:
    events: list[EventItem] = []
    real_sources_active = 0
    failed_sources = 0

    for url in _read_sources("ASTRAM_RSS_FEEDS"):
        try:
            source_events = _load_rss_feed(url)
        except Exception:
            source_events = []
        if source_events:
            real_sources_active += 1
            events.extend(source_events)
        else:
            failed_sources += 1

    for url in _read_sources("ASTRAM_TRAFFIC_ALERT_FEEDS"):
        try:
            source_events = _load_json_feed(url, "BTP Traffic Alert", "traffic_alert", "incident", ("message", "description", "summary", "text"))
        except Exception:
            source_events = []
        if source_events:
            real_sources_active += 1
            events.extend(source_events)
        else:
            failed_sources += 1

    for url in _read_sources("ASTRAM_PUBLIC_EVENT_CALENDARS"):
        try:
            source_events = _load_json_feed(url, "Public Event Calendar", "public_event", "event", ("summary", "description", "text", "details"))
        except Exception:
            source_events = []
        if source_events:
            real_sources_active += 1
            events.extend(source_events)
        else:
            failed_sources += 1

    for url in _read_sources("ASTRAM_CITIZEN_REPORTS"):
        try:
            source_events = _load_json_feed(url, "Citizen Report", "citizen_report", "report", ("report", "message", "description", "text"))
        except Exception:
            source_events = []
        if source_events:
            real_sources_active += 1
            events.extend(source_events)
        else:
            failed_sources += 1

    health = {
        "real_sources_active": real_sources_active,
        "failed_sources": failed_sources,
        "last_refresh": _utc_now().isoformat(),
        "events_collected": len(events),
        "configured_sources": _count_configured_sources(),
    }
    return events, health


def _dedupe_and_sort(events: list[EventItem]) -> list[EventItem]:
    deduped: list[EventItem] = []
    seen: set[tuple[str, str]] = set()
    for item in events:
        key = (_normalize_text(item.get("source_url")), _normalize_text(item.get("title")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda entry: entry.get("published_time") or entry.get("timestamp", ""), reverse=True)
    return deduped


def build_live_events(include_simulated: bool = True) -> list[EventItem]:
    live_events, health = _collect_live_sources()
    global _LAST_REFRESH_AT, _LAST_HEALTH
    _LAST_REFRESH_AT = health["last_refresh"]
    _LAST_HEALTH = health

    if not live_events and include_simulated:
        return _dedupe_and_sort(_default_simulated_events())

    return _dedupe_and_sort(live_events)


def build_live_events_snapshot() -> list[EventItem]:
    return build_live_events(include_simulated=True)


def get_source_health() -> dict[str, Any]:
    live_events, health = _collect_live_sources()
    global _LAST_REFRESH_AT, _LAST_HEALTH
    _LAST_REFRESH_AT = health["last_refresh"]
    health["events_collected"] = len(live_events)
    _LAST_HEALTH = health
    return {
        "real_sources_active": health["real_sources_active"],
        "failed_sources": health["failed_sources"],
        "last_refresh": health["last_refresh"],
        "events_collected": len(live_events),
    }
