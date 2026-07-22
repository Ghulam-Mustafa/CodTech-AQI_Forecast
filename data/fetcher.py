"""
Fetches current AQI + weather readings for a city.

Three backends are supported, controlled by Config.AQI_DATA_SOURCE:
  - "waqi"        : World Air Quality Index API (https://aqicn.org/api/) — free token
  - "openweather" : OpenWeatherMap Air Pollution + Weather APIs — free tier key
  - "mock"        : Deterministic-but-varying synthetic reading, no key required.
                     Used as the default so the app runs out of the box.

Swap AQI_DATA_SOURCE and the relevant API key in .env to go live.
"""
import math
import random
from datetime import datetime

import requests


class FetchError(Exception):
    pass


def fetch_current(city: str, lat: float, lon: float, config) -> dict:
    source = getattr(config, "AQI_DATA_SOURCE", "mock")
    if source == "waqi":
        return _fetch_waqi(city, config)
    if source == "openweather":
        return _fetch_openweather(lat, lon, config)
    return _fetch_mock(city, lat, lon)


def _fetch_waqi(city: str, config) -> dict:
    token = config.WAQI_API_TOKEN
    if not token:
        raise FetchError("WAQI_API_TOKEN is not set in the environment.")
    url = f"https://api.waqi.info/feed/{city}/?token={token}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("status") != "ok":
        raise FetchError(f"WAQI error: {payload}")
    d = payload["data"]
    iaqi = d.get("iaqi", {})
    return {
        "city": city,
        "timestamp": datetime.utcnow(),
        "aqi": d.get("aqi"),
        "pm25": iaqi.get("pm25", {}).get("v"),
        "pm10": iaqi.get("pm10", {}).get("v"),
        "no2": iaqi.get("no2", {}).get("v"),
        "o3": iaqi.get("o3", {}).get("v"),
        "co": iaqi.get("co", {}).get("v"),
        "so2": iaqi.get("so2", {}).get("v"),
        "temperature": iaqi.get("t", {}).get("v"),
        "humidity": iaqi.get("h", {}).get("v"),
        "wind_speed": iaqi.get("w", {}).get("v"),
        "wind_direction": None,
        "pressure": iaqi.get("p", {}).get("v"),
        "dominant_pollutant": d.get("dominentpol"),
    }


def _fetch_openweather(lat: float, lon: float, config) -> dict:
    key = config.OPENWEATHER_API_KEY
    if not key:
        raise FetchError("OPENWEATHER_API_KEY is not set in the environment.")
    air_url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={key}"
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={key}&units=metric"
    air = requests.get(air_url, timeout=10).json()
    weather = requests.get(weather_url, timeout=10).json()
    comp = air["list"][0]["components"]
    owm_aqi_index = air["list"][0]["main"]["aqi"]  # OWM's 1-5 scale
    approx_aqi = {1: 25, 2: 75, 3: 125, 4: 175, 5: 300}.get(owm_aqi_index, 100)
    return {
        "city": weather.get("name", "unknown"),
        "timestamp": datetime.utcnow(),
        "aqi": approx_aqi,
        "pm25": comp.get("pm2_5"),
        "pm10": comp.get("pm10"),
        "no2": comp.get("no2"),
        "o3": comp.get("o3"),
        "co": comp.get("co"),
        "so2": comp.get("so2"),
        "temperature": weather.get("main", {}).get("temp"),
        "humidity": weather.get("main", {}).get("humidity"),
        "wind_speed": weather.get("wind", {}).get("speed"),
        "wind_direction": weather.get("wind", {}).get("deg"),
        "pressure": weather.get("main", {}).get("pressure"),
        "dominant_pollutant": "pm25",
    }


def _fetch_mock(city: str, lat: float, lon: float, when: datetime = None) -> dict:
    """Generates a plausible reading with daily + seasonal structure plus noise,
    so the demo app has believable data without any external API key."""
    when = when or datetime.utcnow()
    day_of_year = when.timetuple().tm_yday
    hour = when.hour

    seasonal = 40 * math.sin((day_of_year / 365) * 2 * math.pi + 1.2) + 90
    diurnal = 20 * math.sin((hour / 24) * 2 * math.pi - 1.0)
    noise = random.gauss(0, 12)
    aqi = max(15, seasonal + diurnal + noise)

    temperature = 27 + 8 * math.sin((day_of_year / 365) * 2 * math.pi) + random.gauss(0, 1.5)
    humidity = max(10, min(95, 55 + 20 * math.sin((day_of_year / 365) * 2 * math.pi + 2) + random.gauss(0, 5)))
    wind_speed = max(0.5, 8 + random.gauss(0, 3))

    pm25 = max(5, aqi * 0.6 + random.gauss(0, 5))
    pm10 = max(10, aqi * 0.9 + random.gauss(0, 8))

    return {
        "city": city,
        "timestamp": when,
        "aqi": round(aqi, 1),
        "pm25": round(pm25, 1),
        "pm10": round(pm10, 1),
        "no2": round(max(2, 20 + random.gauss(0, 6)), 1),
        "o3": round(max(2, 30 + random.gauss(0, 8)), 1),
        "co": round(max(0.1, 0.8 + random.gauss(0, 0.2)), 2),
        "so2": round(max(1, 8 + random.gauss(0, 3)), 1),
        "temperature": round(temperature, 1),
        "humidity": round(humidity, 1),
        "wind_speed": round(wind_speed, 1),
        "wind_direction": round(random.uniform(0, 360), 1),
        "pressure": round(1008 + random.gauss(0, 4), 1),
        "dominant_pollutant": "pm25",
    }
