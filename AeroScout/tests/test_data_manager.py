import pytest
import requests

from AeroScout.data_manager import DataManager, DataManagerError


class FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> object:
        return self.payload


class FakeSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.auth: tuple[str, str] | None = None
        self.calls: list[dict[str, object]] = []
        self.responses: list[FakeResponse] = []

    def request(self, method: str, url: str, timeout: int, **kwargs: object) -> FakeResponse:
        self.calls.append({"method": method, "url": url, "timeout": timeout, **kwargs})
        return self.responses.pop(0)


def test_get_destination_data_fetches_prices(monkeypatch) -> None:
    monkeypatch.setenv("SHEETY_BASE_URL", "https://api.sheety.co/user/project")
    session = FakeSession()
    session.responses.append(FakeResponse({"prices": [{"id": 1, "iataCode": "LAX"}]}))

    manager = DataManager(session=session)

    assert manager.get_destination_data() == [{"id": 1, "iataCode": "LAX"}]
    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["url"] == "https://api.sheety.co/user/project/prices"


def test_update_lowest_price_sends_sheety_payload(monkeypatch) -> None:
    monkeypatch.setenv("SHEETY_BASE_URL", "https://api.sheety.co/user/project")
    session = FakeSession()
    session.responses.append(FakeResponse({"price": {"id": 1, "lowestPrice": 300}}))

    manager = DataManager(session=session)
    updated = manager.update_lowest_price(row_id=1, lowest_price=300)

    assert updated == {"id": 1, "lowestPrice": 300}
    assert session.calls[0]["method"] == "PUT"
    assert session.calls[0]["json"] == {"price": {"lowestPrice": 300}}


def test_get_customer_emails_supports_google_form_fields(monkeypatch) -> None:
    monkeypatch.setenv("SHEETY_BASE_URL", "https://api.sheety.co/user/project")
    session = FakeSession()
    session.responses.append(
        FakeResponse(
            {
                "users": [
                    {"emailAddress": "FIRST@example.com"},
                    {"email": "first@example.com"},
                    {"Email Address": "second@example.com"},
                ]
            }
        )
    )

    manager = DataManager(session=session)

    assert manager.get_customer_emails() == ["first@example.com", "second@example.com"]


def test_sheety_error_raises_data_manager_error(monkeypatch) -> None:
    monkeypatch.setenv("SHEETY_BASE_URL", "https://api.sheety.co/user/project")
    session = FakeSession()
    session.responses.append(FakeResponse({"error": "nope"}, status_code=500))

    manager = DataManager(session=session)

    with pytest.raises(DataManagerError):
        manager.get_destination_data()
