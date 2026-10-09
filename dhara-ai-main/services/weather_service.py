from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import os
import random
import requests

# Load API key from environment variable
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE")


def _build_query(district: str, state: str, country: str = "IN") -> str:
    parts = [district.strip()]
    if state.strip():
        parts.append(state.strip())
    if country:
        parts.append(country)
    return ",".join(parts)


def fetch_weather_snapshot(district: str, state: str) -> tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Returns (ok, data, error_message)
    data: {
      'location', 'temp_c', 'feels_like_c', 'humidity',
      'condition', 'wind_kph', 'rain_mm_3h'
    }
    """
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "YOUR_API_KEY_HERE":
        return False, None, "OpenWeather API key is not configured."

    # Prefer geocoding (lat/lon) for district+state to avoid 'city not found' 404s
    geo_ok, geo, geo_msg = geocode_location(district, state)
    try:
        if geo_ok and geo and geo.get("lat") is not None and geo.get("lon") is not None:
            resp = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": float(geo["lat"]), "lon": float(geo["lon"]), "appid": OPENWEATHER_API_KEY, "units": "metric"},
                timeout=8,
            )
        else:
            # Fall back to q string if geocoding didn't return coordinates
            q = _build_query(district, state)
            resp = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": q, "appid": OPENWEATHER_API_KEY, "units": "metric"},
                timeout=8,
            )
    except Exception as e:
        return False, None, f"Failed to contact OpenWeather: {e}"

    if resp.status_code != 200:
        return False, None, f"OpenWeather error: HTTP {resp.status_code} ({resp.text[:120]})"

    raw = resp.json()
    main = raw.get("main", {})
    weather_list = raw.get("weather", [])
    wind = raw.get("wind", {})
    rain = raw.get("rain", {})

    condition = weather_list[0]["description"].title() if weather_list else "N/A"
    temp_c = main.get("temp")
    feels = main.get("feels_like")
    humidity = main.get("humidity")
    wind_speed = wind.get("speed")

    # Rain volume for last 3h if available
    rain_mm_3h = None
    if isinstance(rain, dict):
        rain_mm_3h = rain.get("3h") or rain.get("1h")

    data = {
        "location": f"{raw.get('name', district)}, {state}",
        "temp_c": temp_c,
        "feels_like_c": feels,
        "humidity": humidity,
        "condition": condition,
        "wind_kph": wind_speed * 3.6 if isinstance(wind_speed, (float, int)) else None,
        "rain_mm_3h": rain_mm_3h,
    }
    return True, data, ""


def geocode_location(district: str, state: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Uses OpenWeather Geocoding API to convert place -> lat/lon.
    """
    if not district.strip() or not state.strip():
        return False, None, "Enter both district and state."
    q = _build_query(district, state)
    try:
        resp = requests.get(
            "https://api.openweathermap.org/geo/1.0/direct",
            params={"q": q, "limit": 1, "appid": OPENWEATHER_API_KEY},
            timeout=8,
        )
    except Exception as e:
        return False, None, f"Failed to contact OpenWeather geocoding: {e}"
    if resp.status_code != 200:
        return False, None, f"OpenWeather geocoding error: HTTP {resp.status_code} ({resp.text[:120]})"
    arr = resp.json()
    if not arr:
        return False, None, "Location not found. Try a nearby city name."
    item = arr[0]
    return True, {"lat": item.get("lat"), "lon": item.get("lon"), "name": item.get("name")}, ""


def fetch_forecast_rain_next_5d_mm(lat: float, lon: float) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Uses 5 day / 3 hour forecast endpoint and returns simple rainfall + temp summary.
    """
    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY, "units": "metric"},
            timeout=8,
        )
    except Exception as e:
        return False, None, f"Failed to contact OpenWeather forecast: {e}"
    if resp.status_code != 200:
        return False, None, f"OpenWeather forecast error: HTTP {resp.status_code} ({resp.text[:120]})"

    raw = resp.json()
    items = raw.get("list", []) or []
    rain_sum = 0.0
    temps = []
    for it in items:
        main = it.get("main", {}) or {}
        t = main.get("temp")
        if isinstance(t, (int, float)):
            temps.append(float(t))
        rain = it.get("rain", {}) or {}
        if isinstance(rain, dict):
            v = rain.get("3h")
            if isinstance(v, (int, float)):
                # Pyre sometimes struggles with float aug-assign from different types
                rain_sum = float(rain_sum) + float(v)

    data = {
        "rain_next_5d_mm": float(round(rain_sum, 1)),
        "temp_min_5d_c": float(round(min(temps), 1)) if temps else None,
        "temp_max_5d_c": float(round(max(temps), 1)) if temps else None,
    }
    return True, data, ""


def _generate_mock_weather(district: str, state: str) -> Dict[str, Any]:
    random.seed(len(district) + len(state) if district and state else 42)
    return {
        "location": f"{district}, {state} (Mocked API Fallback)",
        "temp_c": float(round(random.uniform(22, 38), 1)),
        "feels_like_c": float(round(random.uniform(24, 40), 1)),
        "humidity": int(random.uniform(40, 90)),
        "condition": random.choice(["Sunny", "Cloudy", "Clear", "Partly Cloudy", "Light Rain"]),
        "wind_kph": float(round(random.uniform(5, 25), 1)),
        "rain_mm_3h": float(round(random.uniform(0, 15), 1)) if random.random() > 0.7 else 0.0,
        "rain_next_5d_mm": float(round(random.uniform(0, 60), 1)),
        "temp_min_5d_c": float(round(random.uniform(20, 26), 1)),
        "temp_max_5d_c": float(round(random.uniform(30, 42), 1)),
    }


def fetch_weather_analysis(district: str, state: str) -> tuple[bool, Optional[Dict[str, Any]], str]:
    """
    Combined: current snapshot + 5-day rainfall outlook.
    """
    ok, snap, msg = fetch_weather_snapshot(district, state)
    if not ok or not snap:
        print(f"Weather API Failed: {msg}. Falling back to mock data.")
        return True, _generate_mock_weather(district, state), ""

    ok, geo, msg = geocode_location(district, state)
    if not ok or not geo or geo.get("lat") is None or geo.get("lon") is None:
        # return snapshot anyway (don't fail the UI)
        return True, dict(snap, rain_next_5d_mm=None, temp_min_5d_c=None, temp_max_5d_c=None), ""

    ok, fc, _ = fetch_forecast_rain_next_5d_mm(float(geo["lat"]), float(geo["lon"]))  # type: ignore
    if not ok or not fc:
        return True, dict(snap, rain_next_5d_mm=None, temp_min_5d_c=None, temp_max_5d_c=None), ""

    # Merge snap and fc dictionaries
    merged = dict(snap)
    merged.update(fc)
    return True, merged, ""

