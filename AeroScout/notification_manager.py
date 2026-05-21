"""Notification delivery services for Aero Scout."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable, Protocol

from dotenv import load_dotenv
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

try:
    from .logger import setup_logger
except ImportError:
    from logger import setup_logger


logger = setup_logger(__name__)


class FlightAlert(Protocol):
    """Small interface expected from a flight alert object."""

    price: float
    origin: str
    destination: str
    departure_date: str
    stops: int


class NotificationError(RuntimeError):
    """Raised when notification configuration or delivery fails."""


class NotificationManager:
    """Send Aero Scout notifications through WhatsApp, SMS, and email."""

    def __init__(
        self,
        twilio_client: Client | None = None,
        smtp_factory: type[smtplib.SMTP] = smtplib.SMTP,
    ) -> None:
        load_dotenv()

        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "")
        self.twilio_sms_from = os.getenv("TWILIO_SMS_FROM", "")
        self.default_phone_to = os.getenv("NOTIFICATION_PHONE_TO", "")

        self.smtp_host = os.getenv("SMTP_HOST", "")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.email_from = os.getenv("EMAIL_FROM", self.smtp_username)

        self._twilio_client = twilio_client
        self._smtp_factory = smtp_factory

    def send_whatsapp(self, flight: FlightAlert, to_number: str | None = None) -> str:
        """Send a low-price alert through Twilio WhatsApp."""
        recipient = to_number or self.default_phone_to
        if not self.twilio_whatsapp_from:
            raise NotificationError("TWILIO_WHATSAPP_FROM is required for WhatsApp alerts.")
        if not recipient:
            raise NotificationError("A recipient phone number is required for WhatsApp alerts.")

        return self._send_twilio_message(
            body=self.format_low_price_alert(flight),
            from_number=self._whatsapp_number(self.twilio_whatsapp_from),
            to_number=self._whatsapp_number(recipient),
        )

    def send_sms(self, flight: FlightAlert, to_number: str | None = None) -> str:
        """Send a low-price alert through Twilio SMS."""
        recipient = to_number or self.default_phone_to
        if not self.twilio_sms_from:
            raise NotificationError("TWILIO_SMS_FROM is required for SMS alerts.")
        if not recipient:
            raise NotificationError("A recipient phone number is required for SMS alerts.")

        return self._send_twilio_message(
            body=self.format_low_price_alert(flight),
            from_number=self.twilio_sms_from,
            to_number=recipient,
        )

    def send_email(self, flight: FlightAlert, recipients: str | Iterable[str]) -> None:
        """Send a low-price alert by SMTP email."""
        recipient_list = self._normalize_recipients(recipients)
        if not recipient_list:
            raise NotificationError("At least one email recipient is required.")
        if not self.smtp_host or not self.email_from:
            raise NotificationError("SMTP_HOST and EMAIL_FROM are required for email alerts.")

        message = EmailMessage()
        message["Subject"] = "LOW PRICE ALERT"
        message["From"] = self.email_from
        message["To"] = ", ".join(recipient_list)
        message.set_content(self.format_low_price_alert(flight))

        try:
            with self._smtp_factory(self.smtp_host, self.smtp_port, timeout=30) as smtp:
                smtp.starttls()
                if self.smtp_username and self.smtp_password:
                    smtp.login(self.smtp_username, self.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            logger.exception("Email notification failed for %s recipients.", len(recipient_list))
            raise NotificationError(f"Email notification failed: {exc}") from exc

        logger.info("Sent email notification to %s recipients.", len(recipient_list))

    @staticmethod
    def format_low_price_alert(flight: FlightAlert) -> str:
        """Create the standard low-price alert message."""
        return (
            "LOW PRICE ALERT\n\n"
            f"Price: ${flight.price:,.2f}\n"
            f"Origin: {flight.origin}\n"
            f"Destination: {flight.destination}\n"
            f"Departure: {flight.departure_date}\n"
            f"Stops: {flight.stops}"
        )

    def _send_twilio_message(self, body: str, from_number: str, to_number: str) -> str:
        client = self._get_twilio_client()

        try:
            message = client.messages.create(body=body, from_=from_number, to=to_number)
        except TwilioRestException as exc:
            logger.exception("Twilio notification failed for recipient %s.", to_number)
            raise NotificationError(f"Twilio notification failed: {exc}") from exc

        logger.info("Sent Twilio notification to %s.", to_number)
        return str(message.sid)

    def _get_twilio_client(self) -> Client:
        if self._twilio_client is not None:
            return self._twilio_client

        if not self.twilio_account_sid or not self.twilio_auth_token:
            raise NotificationError("Twilio account SID and auth token are required.")

        self._twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
        return self._twilio_client

    @staticmethod
    def _whatsapp_number(phone_number: str) -> str:
        normalized = phone_number.strip()
        if normalized.startswith("whatsapp:"):
            return normalized
        return f"whatsapp:{normalized}"

    @staticmethod
    def _normalize_recipients(recipients: str | Iterable[str]) -> list[str]:
        if isinstance(recipients, str):
            candidates = [recipients]
        else:
            candidates = list(recipients)

        normalized: list[str] = []
        seen: set[str] = set()
        for recipient in candidates:
            email = str(recipient).strip().lower()
            if email and email not in seen:
                normalized.append(email)
                seen.add(email)

        return normalized
