"""Keyword-based incident extraction for the ASTraM prototype."""

INCIDENT_KEYWORDS = {
    "breakdown": "breakdown",
    "accident": "accident",
    "tree": "tree",
    "waterlogging": "waterlogging",
    "water logging": "waterlogging",
    "water-logging": "waterlogging",
    "protest": "protest",
}

LOCATION_KEYWORDS = [
    "HSR Layout",
    "Silk Board",
    "Koramangala",
    "Bellandur",
    "Marathahalli",
    "Peenya",
]


def extract_incident(text: str) -> dict:
    normalized = text.lower()

    incident_type = "unknown"
    for keyword, incident in INCIDENT_KEYWORDS.items():
        if keyword in normalized:
            incident_type = incident
            break

    location = "unknown"
    for loc in LOCATION_KEYWORDS:
        if loc.lower() in normalized:
            location = loc
            break

    return {
        "incident_type": incident_type,
        "location": location,
        "severity": "high",
    }
