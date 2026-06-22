"""Bundled real RSS and public feed sources for ASTraM.

These defaults are used when the matching environment variables are empty.
Values can be overridden with semicolon-separated URLs in `.env`.
"""

from __future__ import annotations

from urllib.parse import quote_plus


def _google_news_rss(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    )


RSS_FEEDS = [
    _google_news_rss("Bengaluru traffic when:7d"),
    _google_news_rss("Karnataka news when:7d"),
    _google_news_rss("Bengaluru news when:7d"),
]

TRAFFIC_ALERT_FEEDS = [
    _google_news_rss("Bengaluru traffic alert when:7d"),
    _google_news_rss("Bengaluru traffic police when:7d"),
    _google_news_rss("Bengaluru road closure when:7d"),
]

PUBLIC_EVENT_CALENDARS = [
    _google_news_rss("Bengaluru event when:7d"),
    _google_news_rss("Bengaluru public event when:7d"),
    _google_news_rss("Bengaluru rally when:7d"),
]

CITIZEN_REPORTS = [
    _google_news_rss("Bengaluru traffic congestion when:7d"),
    _google_news_rss("Bengaluru commuter traffic when:7d"),
    _google_news_rss("Bengaluru traffic rant when:7d"),
]

WEATHER_ALERT_FEEDS = [
    _google_news_rss("Bengaluru weather alert when:7d"),
    _google_news_rss("Karnataka weather alert when:7d"),
    _google_news_rss("Bengaluru rain alert when:7d"),
]

ROAD_CLOSURE_FEEDS = [
    _google_news_rss("Bengaluru road closure when:7d"),
    _google_news_rss("Bengaluru traffic diversion when:7d"),
    _google_news_rss("Bengaluru road work when:7d"),
]

TRAFFIC_CONGESTION_FEEDS = [
    _google_news_rss("Bengaluru traffic congestion when:7d"),
    _google_news_rss("Bengaluru traffic jam when:7d"),
    _google_news_rss("Bengaluru traffic snarls when:7d"),
]

DEFAULT_FEED_SOURCES = {
    "ASTRAM_RSS_FEEDS": RSS_FEEDS,
    "ASTRAM_TRAFFIC_ALERT_FEEDS": TRAFFIC_ALERT_FEEDS,
    "ASTRAM_PUBLIC_EVENT_CALENDARS": PUBLIC_EVENT_CALENDARS,
    "ASTRAM_CITIZEN_REPORTS": CITIZEN_REPORTS,
}
