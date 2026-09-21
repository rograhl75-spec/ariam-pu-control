"""Serviço de leitura climática."""

from __future__ import annotations

import requests


class WeatherService:
    """Consulta temperatura atual na API Open-Meteo."""

    def __init__(self, latitude: float, longitude: float, timeout: int = 5):
        self.latitude = latitude
        self.longitude = longitude
        self.timeout = timeout

    def get_temperature(self, fallback: float = 24.0) -> float:
        """Obtém temperatura atual ou usa fallback em falha."""
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={self.latitude}&longitude={self.longitude}&current_weather=true"
        )
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return float(response.json()["current_weather"]["temperature"])
        except (requests.RequestException, KeyError, TypeError, ValueError):
            return fallback
