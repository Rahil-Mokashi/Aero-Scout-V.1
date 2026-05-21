"""Google Sheets access layer for Aero Scout.

The DataManager is the only module that knows about Sheety's API shape. The
rest of the app can work with plain dictionaries and email lists.
"""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from .logger import setup_logger
except ImportError:
    from logger import setup_logger


logger = setup_logger(__name__)


class DataManagerError(RuntimeError):
    """Raised when Sheety configuration or API communication fails."""


class DataManager:
    """Manage destination and user data stored in Google Sheets via Sheety."""

    EMAIL_FIELDS = ("email", "emailAddress", "email_address", "Email Address")

    def __init__(
        self,
        base_url: str | None = None,
        session: requests.Session | None = None,
        timeout: int = 30,
    ) -> None:
        load_dotenv()

        self.base_url = (base_url or os.getenv("SHEETY_BASE_URL", "")).rstrip("/")
        if not self.base_url:
            raise DataManagerError("SHEETY_BASE_URL is required.")

        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(self._build_headers())

        username = os.getenv("SHEETY_USERNAME")
        password = os.getenv("SHEETY_PASSWORD")
        if username and password:
            self.session.auth = (username, password)

    def get_destination_data(self) -> list[dict[str, Any]]:
        """Return all destinations from the `prices` tab."""
        payload = self._request("GET", "prices")
        destinations = self._extract_rows(payload, "prices")
        logger.info("Loaded %s destinations from Sheety.", len(destinations))
        return destinations

    def update_lowest_price(self, row_id: int | str, lowest_price: int | float) -> dict[str, Any]:
        """Update the stored lowest price for one destination row."""
        payload = {"price": {"lowestPrice": lowest_price}}
        response = self._request("PUT", f"prices/{row_id}", json=payload)
        logger.info("Updated lowest price for row %s to %s.", row_id, lowest_price)
        return response.get("price", response)

    def get_customer_emails(self) -> list[str]:
        """Return unique customer emails from the `users` tab.

        Google Forms often names the email column "Email Address", while Sheety
        may camel-case it to "emailAddress". We support both that form-driven
        shape and the simpler "email" field.
        """
        payload = self._request("GET", "users")
        users = self._extract_rows(payload, "users")

        emails: list[str] = []
        seen: set[str] = set()
        for user in users:
            email = self._extract_email(user)
            if email and email not in seen:
                emails.append(email)
                seen.add(email)

        logger.info("Loaded %s customer emails from Sheety.", len(emails))
        return emails

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        bearer_token = os.getenv("SHEETY_BEARER_TOKEN")
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        return headers

    def _request(self, method: str, resource: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.base_url}/{resource.lstrip('/')}"

        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("Sheety API request failed: %s %s", method, url)
            raise DataManagerError(f"Sheety {method} request failed for {url}: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            logger.exception("Sheety returned invalid JSON: %s %s", method, url)
            raise DataManagerError(f"Sheety returned invalid JSON for {url}.") from exc

        if not isinstance(data, dict):
            logger.error("Sheety returned unexpected response type: %s", type(data).__name__)
            raise DataManagerError(f"Sheety returned an unexpected response for {url}.")

        return data

    @staticmethod
    def _extract_rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
        rows = payload.get(key, [])
        if not isinstance(rows, list):
            raise DataManagerError(f"Sheety response field '{key}' must be a list.")

        return [row for row in rows if isinstance(row, dict)]

    @classmethod
    def _extract_email(cls, user: dict[str, Any]) -> str:
        for field in cls.EMAIL_FIELDS:
            value = user.get(field)
            if value:
                return str(value).strip().lower()
        return ""
