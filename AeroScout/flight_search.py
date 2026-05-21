"""Flight search service integration for Aero Scout."""

from __future__ import annotations

import os
from typing import Any

import requests
import requests_cache
from dotenv import load_dotenv

try:
    from .logger import setup_logger
except ImportError:
    from logger import setup_logger


logger = setup_logger(__name__)


class FlightSearchError(RuntimeError):
    """Raised when flight search configuration or API communication fails."""


class FlightSearch:
    """Search for flights through SerpAPI Google Flights."""

    SEARCH_URL = "https://serpapi.com/search.json"

    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        cache_name: str = "aero_scout_flights_cache",
        cache_expire_seconds: int = 900,
        timeout: int = 30,
    ) -> None:
        load_dotenv()

        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        if not self.api_key:
            raise FlightSearchError("SERPAPI_API_KEY is required.")

        self.timeout = timeout
        self.session = session or requests_cache.CachedSession(
            cache_name=cache_name,
            expire_after=cache_expire_seconds,
        )

    def check_flights(
        self,
        origin: str,
        destination: str,
        from_date: str,
        return_date: str,
        is_direct: bool = True,
    ) -> dict[str, Any]:
        """Search for flights, retrying with stopovers if direct flights are empty.

        Args:
            origin: Origin airport code, such as "LON".
            destination: Destination airport code, such as "PAR".
            from_date: Outbound date in YYYY-MM-DD format.
            return_date: Return date in YYYY-MM-DD format.
            is_direct: Whether to search direct flights first.
        """
        direct_result = self._search(
            origin=origin,
            destination=destination,
            from_date=from_date,
            return_date=return_date,
            direct_only=is_direct,
        )

        if not is_direct or self._has_flights(direct_result):
            return direct_result

        return self._search(
            origin=origin,
            destination=destination,
            from_date=from_date,
            return_date=return_date,
            direct_only=False,
        )

    def _search(
        self,
        origin: str,
        destination: str,
        from_date: str,
        return_date: str,
        direct_only: bool,
    ) -> dict[str, Any]:
        params = {
            "engine": "google_flights",
            "api_key": self.api_key,
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": from_date,
            "return_date": return_date,
            "currency": "USD",
            "hl": "en",
            "type": "1",
        }

        if direct_only:
            params["max_stops"] = "0"

        try:
            response = self.session.get(self.SEARCH_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("SerpAPI request failed for %s to %s.", origin, destination)
            raise FlightSearchError(
                f"SerpAPI flight search failed for {origin} to {destination}: {exc}"
            ) from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("SerpAPI returned invalid JSON for %s to %s.", origin, destination)
            raise FlightSearchError("SerpAPI returned invalid JSON.") from exc

        if not isinstance(data, dict):
            logger.error("SerpAPI returned unexpected response type: %s", type(data).__name__)
            raise FlightSearchError("SerpAPI returned an unexpected response.")

        if "error" in data:
            logger.error("SerpAPI error for %s to %s: %s", origin, destination, data["error"])
            raise FlightSearchError(f"SerpAPI error: {data['error']}")

        data["search_metadata"] = {
            **data.get("search_metadata", {}),
            "direct_only": direct_only,
            "origin": origin,
            "destination": destination,
            "from_date": from_date,
            "return_date": return_date,
        }
        logger.info(
            "Fetched %s flight results for %s to %s.",
            "direct" if direct_only else "stopover",
            origin,
            destination,
        )
        return data

    @staticmethod
    def _has_flights(data: dict[str, Any]) -> bool:
        best_flights = data.get("best_flights") or []
        other_flights = data.get("other_flights") or []
        return bool(best_flights or other_flights)
