"""Application entry point and scheduler for Aero Scout."""

from __future__ import annotations

import os
import time
from datetime import date, timedelta
from typing import Any

from dotenv import load_dotenv

try:
    from .data_manager import DataManager
    from .flight_data import FlightData, find_cheapest_flight
    from .flight_search import FlightSearch
    from .logger import setup_logger
    from .notification_manager import NotificationError, NotificationManager
except ImportError:
    from data_manager import DataManager
    from flight_data import FlightData, find_cheapest_flight
    from flight_search import FlightSearch
    from logger import setup_logger
    from notification_manager import NotificationError, NotificationManager


DEFAULT_CHECK_INTERVAL_SECONDS = 60 * 60
logger = setup_logger(__name__)


class AeroScoutApp:
    """Coordinate sheet reads, flight searches, price updates, and alerts."""

    def __init__(
        self,
        data_manager: DataManager | None = None,
        flight_search: FlightSearch | None = None,
        notification_manager: NotificationManager | None = None,
    ) -> None:
        load_dotenv()

        self.data_manager = data_manager or DataManager()
        self.flight_search = flight_search or FlightSearch()
        self.notification_manager = notification_manager or NotificationManager()

        self.origin_airport = os.getenv("ORIGIN_AIRPORT", "").strip().upper()
        if not self.origin_airport:
            raise ValueError("ORIGIN_AIRPORT is required.")

        self.from_date = os.getenv("FROM_DATE") or self._date_from_today("FROM_DAYS_AHEAD", 1)
        self.return_date = os.getenv("RETURN_DATE") or self._date_from_today("RETURN_DAYS_AHEAD", 8)

    def run_once(self) -> None:
        """Run one complete price-check cycle."""
        logger.info("Starting Aero Scout price check.")
        destinations = self.data_manager.get_destination_data()
        customer_emails = self.data_manager.get_customer_emails()

        for destination in destinations:
            self._check_destination(destination, customer_emails)

        logger.info("Finished Aero Scout price check.")

    def run_forever(self, interval_seconds: int = DEFAULT_CHECK_INTERVAL_SECONDS) -> None:
        """Run the price-check cycle forever with a fixed sleep interval."""
        while True:
            self.run_once()
            time.sleep(interval_seconds)

    def _check_destination(self, destination: dict[str, Any], customer_emails: list[str]) -> None:
        row_id = destination.get("id")
        destination_code = self._destination_code(destination)
        stored_lowest_price = self._stored_lowest_price(destination)

        if not row_id or not destination_code or stored_lowest_price is None:
            logger.warning("Skipping incomplete destination row: %s", destination)
            return

        flight_response = self.flight_search.check_flights(
            origin=self.origin_airport,
            destination=destination_code,
            from_date=self.from_date,
            return_date=self.return_date,
            is_direct=True,
        )
        cheapest_flight = find_cheapest_flight(flight_response)

        if cheapest_flight is None or cheapest_flight.price >= stored_lowest_price:
            logger.info(
                "No cheaper flight found for %s. Stored price: %s.",
                destination_code,
                stored_lowest_price,
            )
            return

        self.data_manager.update_lowest_price(row_id, cheapest_flight.price)
        logger.info(
            "New low price found for %s: %s down from %s.",
            destination_code,
            cheapest_flight.price,
            stored_lowest_price,
        )
        self._send_price_alerts(cheapest_flight, customer_emails)

    def _send_price_alerts(self, flight: FlightData, customer_emails: list[str]) -> None:
        if customer_emails:
            try:
                self.notification_manager.send_email(flight, customer_emails)
            except NotificationError:
                logger.exception("Email alert failed.")

        for sender in (self.notification_manager.send_whatsapp, self.notification_manager.send_sms):
            try:
                sender(flight)
            except NotificationError:
                logger.exception("Phone alert failed.")
                continue

    @staticmethod
    def _destination_code(destination: dict[str, Any]) -> str:
        value = destination.get("iataCode") or destination.get("iata_code")
        return str(value).strip().upper() if value else ""

    @staticmethod
    def _stored_lowest_price(destination: dict[str, Any]) -> float | None:
        value = destination.get("lowestPrice") or destination.get("lowest_price")
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _date_from_today(env_name: str, default_days: int) -> str:
        days = int(os.getenv(env_name, str(default_days)))
        return (date.today() + timedelta(days=days)).isoformat()


def main() -> None:
    """Run the Aero Scout automation workflow."""
    load_dotenv()

    interval_seconds = int(os.getenv("CHECK_INTERVAL_SECONDS", str(DEFAULT_CHECK_INTERVAL_SECONDS)))
    run_once = os.getenv("RUN_ONCE", "false").strip().lower() in {"1", "true", "yes"}

    app = AeroScoutApp()
    if run_once:
        logger.info("Running Aero Scout once.")
        app.run_once()
        return

    logger.info("Running Aero Scout every %s seconds.", interval_seconds)
    app.run_forever(interval_seconds=interval_seconds)


if __name__ == "__main__":
    main()
