"""Flight data models and parsing helpers for Aero Scout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FlightData:
    """Represent a flight result returned by the flight search service."""

    price: float
    origin: str
    destination: str
    departure_date: str
    return_date: str
    stops: int = 0

    @property
    def is_direct(self) -> bool:
        """Return whether the itinerary is a direct flight."""
        return self.stops == 0


def find_cheapest_flight(flight_response: dict[str, Any]) -> FlightData | None:
    """Return the cheapest valid flight from SerpAPI best and other flights.

    SerpAPI can return partially populated records. This parser deliberately
    skips broken flight entries instead of raising, which keeps hourly checks
    resilient to one bad itinerary.
    """
    if not isinstance(flight_response, dict):
        return None

    candidates = _combined_flights(flight_response)
    parsed_flights = [
        flight
        for flight in (_parse_flight(candidate, flight_response) for candidate in candidates)
        if flight is not None
    ]

    if not parsed_flights:
        return None

    return min(parsed_flights, key=lambda flight: flight.price)


def _combined_flights(flight_response: dict[str, Any]) -> list[dict[str, Any]]:
    combined: list[dict[str, Any]] = []
    for key in ("best_flights", "other_flights"):
        flights = flight_response.get(key, [])
        if isinstance(flights, list):
            combined.extend(flight for flight in flights if isinstance(flight, dict))
    return combined


def _parse_flight(candidate: dict[str, Any], flight_response: dict[str, Any]) -> FlightData | None:
    price = _parse_price(candidate.get("price"))
    segments = candidate.get("flights")

    if price is None or not isinstance(segments, list) or not segments:
        return None

    valid_segments = [segment for segment in segments if isinstance(segment, dict)]
    if not valid_segments:
        return None

    first_segment = valid_segments[0]
    last_segment = valid_segments[-1]

    origin = _airport_code(first_segment.get("departure_airport"))
    destination = _airport_code(last_segment.get("arrival_airport"))
    departure_date = _date_value(first_segment.get("departure_airport"))
    return_date = _return_date(candidate, flight_response)

    if not origin or not destination or not departure_date or not return_date:
        return None

    return FlightData(
        price=price,
        origin=origin,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        stops=_stop_count(candidate, valid_segments),
    )


def _parse_price(value: Any) -> float | None:
    if isinstance(value, (int, float)) and value > 0:
        return float(value)

    if isinstance(value, str):
        normalized = value.replace("$", "").replace(",", "").strip()
        try:
            price = float(normalized)
        except ValueError:
            return None
        return price if price > 0 else None

    return None


def _airport_code(airport: Any) -> str | None:
    if not isinstance(airport, dict):
        return None

    code = airport.get("id") or airport.get("airport_id")
    if code:
        return str(code).strip().upper()

    name = airport.get("name")
    return str(name).strip() if name else None


def _date_value(airport: Any) -> str | None:
    if not isinstance(airport, dict):
        return None

    date_time = airport.get("time") or airport.get("date")
    if not date_time:
        return None

    return str(date_time).split()[0]


def _return_date(candidate: dict[str, Any], flight_response: dict[str, Any]) -> str | None:
    metadata = flight_response.get("search_metadata", {})
    if isinstance(metadata, dict) and metadata.get("return_date"):
        return str(metadata["return_date"])

    for key in ("return_date", "returnDate"):
        if candidate.get(key):
            return str(candidate[key]).split()[0]

    return None


def _stop_count(candidate: dict[str, Any], segments: list[dict[str, Any]]) -> int:
    stops = candidate.get("stops")
    if isinstance(stops, int) and stops >= 0:
        return stops

    if isinstance(stops, str) and stops.isdigit():
        return int(stops)

    layovers = candidate.get("layovers")
    if isinstance(layovers, list):
        return len(layovers)

    return max(len(segments) - 1, 0)
