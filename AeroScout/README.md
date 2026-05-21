# Aero Scout

Aero Scout is a Python automation project that monitors flight prices for predefined destinations stored in Google Sheets. It checks prices through SerpAPI Google Flights, compares new prices against the stored lowest price, updates the sheet when a better fare appears, and notifies customers through WhatsApp, SMS, and email.

## Overview

The project is designed as a small production-style automation service:

- Google Sheets is the source of truth for tracked destinations and registered users.
- Sheety exposes the Google Sheet as a REST API.
- SerpAPI Google Flights provides flight price data.
- Twilio sends WhatsApp and SMS alerts.
- SMTP sends email alerts.
- Requests Cache reduces repeated flight API calls.
- Pytest covers the parser, notification system, and Sheety integration boundary.

## Architecture

```text
Google Form -> Google Sheet users tab
Google Sheet prices tab -> Sheety API -> DataManager
DataManager -> Scheduler -> FlightSearch -> SerpAPI Google Flights
FlightSearch response -> FlightData parser -> Scheduler
Scheduler -> DataManager price update
Scheduler -> NotificationManager -> WhatsApp, SMS, Email
```

Core flow:

1. Load destinations from the `prices` tab.
2. Load customer emails from the `users` tab.
3. Search direct flights first for each destination.
4. Retry with stopover flights if no direct result exists.
5. Parse and select the cheapest valid flight.
6. Compare the new price to the stored `lowestPrice`.
7. Update Google Sheets and send alerts only when the new price is cheaper.
8. Repeat every hour by default.

## Tech Stack

- Python
- Google Sheets
- Google Forms
- Sheety API
- SerpAPI Google Flights
- Twilio WhatsApp
- Twilio SMS
- SMTP Email
- Requests
- Requests Cache
- python-dotenv
- Logging
- Pytest

## Installation

Clone the repository:

```bash
git clone https://github.com/Rahil-Mokashi/Aero-Scout-V.1.git
cd Aero-Scout-V.1
```

Create and activate a virtual environment:

```bash
py -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
py -m pip install -r AeroScout\requirements.txt
```

## Environment Setup

Create a local `.env` file from the example:

```bash
copy AeroScout\.env.example AeroScout\.env
```

Configure these values:

```env
SHEETY_BASE_URL=
SHEETY_USERNAME=
SHEETY_PASSWORD=
SHEETY_BEARER_TOKEN=

SERPAPI_API_KEY=

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=
TWILIO_SMS_FROM=
NOTIFICATION_PHONE_TO=

SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
EMAIL_FROM=

ORIGIN_AIRPORT=
FROM_DATE=
RETURN_DATE=
FROM_DAYS_AHEAD=1
RETURN_DAYS_AHEAD=8
CHECK_INTERVAL_SECONDS=3600
RUN_ONCE=false

LOG_LEVEL=INFO
LOG_FILE=logs/aero_scout.log
LOG_MAX_BYTES=1048576
LOG_BACKUP_COUNT=3
```

Notes:

- Use either `SHEETY_BEARER_TOKEN` or `SHEETY_USERNAME` plus `SHEETY_PASSWORD`.
- `ORIGIN_AIRPORT` is required, for example `JFK`, `LHR`, or `BOM`.
- Use `FROM_DATE` and `RETURN_DATE` for fixed dates.
- If dates are empty, Aero Scout uses `FROM_DAYS_AHEAD` and `RETURN_DAYS_AHEAD`.
- Set `RUN_ONCE=true` for local testing.

## Google Sheet Setup

Aero Scout expects two Google Sheet tabs:

```text
prices
users
```

The `prices` tab stores tracked destinations.

Recommended columns:

```text
city
iataCode
lowestPrice
```

The `users` tab stores customer registrations from Google Forms.

Recommended form fields:

```text
First Name
Last Name
Email
```

See `GOOGLE_FORM_SETUP.md` for the detailed setup guide.

## Demo

Run one price-check cycle:

```bash
set RUN_ONCE=true
py AeroScout\main.py
```

Run continuously with the configured interval:

```bash
py AeroScout\main.py
```

Run tests:

```bash
py -m pytest AeroScout\tests
```

Example alert:

```text
LOW PRICE ALERT

Price: $199.99
Origin: JFK
Destination: LAX
Departure: 2026-06-01
Stops: 0
```

## Folder Structure

```text
AeroScout/
  __init__.py
  main.py
  data_manager.py
  flight_search.py
  flight_data.py
  notification_manager.py
  logger.py
  requirements.txt
  .env.example
  .gitignore
  GOOGLE_FORM_SETUP.md
  README.md
  tests/
    test_data_manager.py
    test_flight_data.py
    test_notification_manager.py
```

## Testing

The test suite uses fakes for external services, so tests do not call real Google Sheets, SerpAPI, Twilio, or SMTP.

Covered areas:

- Cheapest-flight parsing
- Broken flight data handling
- Sheety request and update behavior
- Google Form email field parsing
- WhatsApp/SMS message dispatch through a fake Twilio client
- SMTP email dispatch through a fake SMTP client

## Logging

Logs are written to console and to a rotating file.

Default file:

```text
logs/aero_scout.log
```

Tracked events include:

- API failures
- Invalid API responses
- Loaded destinations and users
- Skipped sheet rows
- Price comparisons
- Price updates
- Notification success and failure

## Future Improvements

- Add a hosted deployment target such as Render, Railway, or a VPS.
- Add GitHub Actions for automated tests.
- Add richer alert templates with booking links.
- Add per-user destination preferences.
- Add retry/backoff policies for transient API failures.
- Add structured JSON logging for production observability.
- Add currency and locale configuration per user.
