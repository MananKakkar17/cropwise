"""Configuration and external-service helpers."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from src.locations import normalise_city


def get_setting(name: str, default: str = "") -> str:
    """Read a configured environment variable without exposing a secret in logs."""
    return os.getenv(name, default)


def fetch_indian_weather(city: str) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch current Indian conditions from OpenWeather's free current-weather API."""
    api_key = get_setting("OPENWEATHER_API_KEY")
    if not api_key:
        return None, "Add OPENWEATHER_API_KEY to your .env file first."

    cleaned_city = normalise_city(city)
    if len(cleaned_city) < 2:
        return None, "Enter a valid Indian city name."

    query = urlencode({"q": f"{cleaned_city},IN", "appid": api_key, "units": "metric"})
    url = f"https://api.openweathermap.org/data/2.5/weather?{query}"
    try:
        with urlopen(url, timeout=12) as response:
            data = json.load(response)
    except HTTPError as error:
        if error.code == 401:
            return None, "Invalid OpenWeather API key. Check OPENWEATHER_API_KEY in .env."
        if error.code == 404:
            return None, f"City '{cleaned_city}' not found. Try a nearby major city."
        return None, f"Weather service error ({error.code}). Try again shortly."
    except URLError:
        return None, "No internet connection. Check your network and try again."
    except (ValueError, TimeoutError):
        return None, "Weather service timed out. Please try again."

    try:
        rain_1h = data.get("rain", {}).get("1h")
        rain_3h = data.get("rain", {}).get("3h")
        rainfall = round(float(rain_1h if rain_1h is not None else (rain_3h or 0) / 3), 1)
        icon = data["weather"][0].get("icon", "01d")
        return {
            "city": data["name"],
            "state_query": city.strip(),
            "temperature": round(data["main"]["temp"], 1),
            "feels_like": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"].title(),
            "rainfall": rainfall,
            "wind": round(data["wind"]["speed"] * 3.6, 1),
            "pressure": data["main"]["pressure"],
            "icon": icon,
            "icon_url": f"https://openweathermap.org/img/wn/{icon}@2x.png",
        }, None
    except (KeyError, IndexError, TypeError):
        return None, "The weather service returned an unexpected response. Please try again."
