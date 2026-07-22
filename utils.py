"""Shared helpers for classifying AQI values (US EPA 0-500 scale)."""

AQI_BANDS = [
    (0, 50, "Good", "#00e400"),
    (51, 100, "Moderate", "#ffff00"),
    (101, 150, "Unhealthy for Sensitive Groups", "#ff7e00"),
    (151, 200, "Unhealthy", "#ff0000"),
    (201, 300, "Very Unhealthy", "#8f3f97"),
    (301, 500, "Hazardous", "#7e0023"),
]


def classify_aqi(value):
    """Return (category, hex_color) for a given AQI value.

    Bands are checked by upper bound only (ascending order) so fractional
    values like 50.4 — which sit between the integer bounds of adjacent
    bands — still resolve to the correct category instead of falling
    through a gap.
    """
    if value is None:
        return "Unknown", "#9e9e9e"
    if value < 0:
        return "Good", AQI_BANDS[0][3]
    for _, hi, category, color in AQI_BANDS:
        if value <= hi:
            return category, color
    return "Hazardous", "#7e0023"


def health_advisory(category):
    advisories = {
        "Good": "Air quality is satisfactory. Enjoy your usual outdoor activities.",
        "Moderate": "Air quality is acceptable. Unusually sensitive people should consider reducing prolonged exertion outdoors.",
        "Unhealthy for Sensitive Groups": "Sensitive groups (children, elderly, people with respiratory or heart conditions) should reduce prolonged outdoor exertion.",
        "Unhealthy": "Everyone may begin to experience health effects. Sensitive groups should avoid outdoor exertion.",
        "Very Unhealthy": "Health alert: everyone may experience more serious health effects. Avoid outdoor activity.",
        "Hazardous": "Health emergency: the entire population is likely to be affected. Stay indoors.",
        "Unknown": "No data available.",
    }
    return advisories.get(category, "No data available.")
