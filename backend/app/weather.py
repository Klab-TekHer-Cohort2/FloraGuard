import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from typing import Any

from .config import Settings

logger = logging.getLogger("floraguard.weather")


class OpenMeteoWeather:
    """Small Open-Meteo client; it has no API key or fabricated fallback."""

    endpoint = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout_seconds: float = 4):
        self.timeout_seconds = timeout_seconds

    def current(self, latitude: float | None, longitude: float | None) -> dict[str, Any]:
        if latitude is None or longitude is None:
            return self._unavailable("Coordinates are not available.")
        query = urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m",
                "timezone": "UTC",
            }
        )
        try:
            with urlopen(f"{self.endpoint}?{query}", timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            current = payload["current"]
            temperature = current["temperature_2m"]
            humidity = current["relative_humidity_2m"]
            if temperature is None or humidity is None:
                raise ValueError("Weather provider omitted temperature or humidity.")
            return {
                "status": "available",
                "temperature": float(temperature),
                "humidity": float(humidity),
                "observed_at": current.get("time"),
                "source": "Open-Meteo",
            }
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Weather lookup unavailable: %s", exc)
            return self._unavailable("Weather provider could not be reached.")

    @staticmethod
    def _unavailable(reason: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "temperature": None,
            "humidity": None,
            "observed_at": None,
            "source": "Open-Meteo",
            "reason": reason,
        }


def weather_client(settings: Settings) -> OpenMeteoWeather:
    return OpenMeteoWeather(settings.weather_timeout_seconds)
