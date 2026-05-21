from AeroScout.flight_data import FlightData, find_cheapest_flight


def test_find_cheapest_flight_combines_best_and_other_flights() -> None:
    response = {
        "search_metadata": {"return_date": "2026-06-08"},
        "best_flights": [
            {
                "price": 450,
                "flights": [
                    {
                        "departure_airport": {"id": "JFK", "time": "2026-06-01 08:00"},
                        "arrival_airport": {"id": "LHR", "time": "2026-06-01 20:00"},
                    }
                ],
            }
        ],
        "other_flights": [
            {
                "price": "$390",
                "flights": [
                    {
                        "departure_airport": {"id": "JFK", "time": "2026-06-01 09:00"},
                        "arrival_airport": {"id": "CDG", "time": "2026-06-01 18:00"},
                    },
                    {
                        "departure_airport": {"id": "CDG", "time": "2026-06-01 20:00"},
                        "arrival_airport": {"id": "LHR", "time": "2026-06-01 21:00"},
                    },
                ],
            }
        ],
    }

    cheapest = find_cheapest_flight(response)

    assert cheapest == FlightData(
        price=390.0,
        origin="JFK",
        destination="LHR",
        departure_date="2026-06-01",
        return_date="2026-06-08",
        stops=1,
    )


def test_find_cheapest_flight_ignores_broken_data() -> None:
    response = {
        "search_metadata": {"return_date": "2026-06-08"},
        "best_flights": [
            {"price": None, "flights": []},
            {"price": "not a price", "flights": [{"departure_airport": {"id": "JFK"}}]},
        ],
        "other_flights": [
            {
                "price": 250,
                "flights": [
                    {
                        "departure_airport": {"id": "JFK", "time": "2026-06-01 09:00"},
                        "arrival_airport": {"id": "LAX", "time": "2026-06-01 12:00"},
                    }
                ],
            }
        ],
    }

    cheapest = find_cheapest_flight(response)

    assert cheapest is not None
    assert cheapest.price == 250.0


def test_find_cheapest_flight_returns_none_when_no_valid_flights() -> None:
    assert find_cheapest_flight({"best_flights": [{"price": 0}], "other_flights": []}) is None
