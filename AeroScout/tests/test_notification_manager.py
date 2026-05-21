from dataclasses import dataclass
from email.message import EmailMessage

from AeroScout.notification_manager import NotificationManager


@dataclass(frozen=True)
class FakeFlight:
    price: float = 199.99
    origin: str = "JFK"
    destination: str = "LAX"
    departure_date: str = "2026-06-01"
    stops: int = 0


class FakeMessage:
    sid = "SM123"


class FakeMessages:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def create(self, body: str, from_: str, to: str) -> FakeMessage:
        self.sent.append({"body": body, "from": from_, "to": to})
        return FakeMessage()


class FakeTwilioClient:
    def __init__(self) -> None:
        self.messages = FakeMessages()


class FakeSMTP:
    sent_messages: list[EmailMessage] = []

    def __init__(self, host: str, port: int, timeout: int) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def send_message(self, message: EmailMessage) -> None:
        self.sent_messages.append(message)


def test_format_low_price_alert() -> None:
    message = NotificationManager.format_low_price_alert(FakeFlight())

    assert "LOW PRICE ALERT" in message
    assert "Price: $199.99" in message
    assert "Origin: JFK" in message
    assert "Destination: LAX" in message
    assert "Departure: 2026-06-01" in message
    assert "Stops: 0" in message


def test_send_whatsapp_uses_twilio_client(monkeypatch) -> None:
    monkeypatch.setenv("TWILIO_WHATSAPP_FROM", "+10000000000")
    monkeypatch.setenv("NOTIFICATION_PHONE_TO", "+19999999999")

    client = FakeTwilioClient()
    manager = NotificationManager(twilio_client=client)

    sid = manager.send_whatsapp(FakeFlight())

    assert sid == "SM123"
    assert client.messages.sent[0]["from"] == "whatsapp:+10000000000"
    assert client.messages.sent[0]["to"] == "whatsapp:+19999999999"


def test_send_email_uses_smtp(monkeypatch) -> None:
    FakeSMTP.sent_messages = []
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("EMAIL_FROM", "alerts@example.com")

    manager = NotificationManager(smtp_factory=FakeSMTP)

    manager.send_email(FakeFlight(), ["USER@example.com", "user@example.com"])

    assert len(FakeSMTP.sent_messages) == 1
    assert FakeSMTP.sent_messages[0]["To"] == "user@example.com"
    assert FakeSMTP.sent_messages[0]["From"] == "alerts@example.com"
