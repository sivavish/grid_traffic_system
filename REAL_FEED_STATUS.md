# REAL_FEED_STATUS

## Summary

The live feed engine now prefers real RSS/public sources and only falls back to simulated items when every configured source fails.

Probe result from the current workspace environment:

- Real Sources Active: 3
- Failed Sources: 9
- Events Retrieved: 263
- Simulated Events Remaining: 0
- Last Refresh: 2026-06-21T07:19:34.675398+00:00

## Configured Sources

The bundled defaults are defined in [backend/feed_sources.py](backend/feed_sources.py).

### RSS Feeds

- Bengaluru traffic
- Karnataka news
- Bengaluru news

### Traffic Alerts

- Bengaluru traffic alert
- Bengaluru traffic police
- Bengaluru road closure

### Public Events

- Bengaluru event
- Bengaluru public event
- Bengaluru rally

### Citizen Reports

- Bengaluru traffic congestion
- Bengaluru commuter traffic
- Bengaluru traffic rant

### Additional Bundled Topics

- Weather alerts
- Road closures
- Traffic congestion

## Working Sources

The current runtime probe returned real items from these sources:

- India Today
- The News Minute
- Udayavani
- The New Indian Express
- The Hindu
- Deccan Herald
- News18
- MSN
- The Times of India

## Failed Sources

Nine configured URLs returned no usable entries in the current probe run. These are still valid live URLs, but they did not contribute items in this refresh window.

## Event Retrieved

The engine collected 263 real items and normalized them into the ASTraM live feed schema.

## Simulated Fallback

Simulated items were not used because real sources returned data successfully.
