# Google Form Integration

Aero Scout expects a Google Form to collect customer registrations and store the responses in the same Google Sheet exposed through Sheety.

## Google Form Fields

Create a Google Form with these questions:

- First Name
- Last Name
- Email

In the form settings, connect responses to a Google Sheet.

## Google Sheet Tabs

Use two tabs in the connected spreadsheet:

### prices

This tab stores the destinations Aero Scout monitors.

Recommended columns:

- city
- iataCode
- lowestPrice
- id

Sheety creates the `id` field automatically for each row.

### users

This tab stores Google Form registrations.

Recommended columns:

- firstName
- lastName
- email

If Google Forms creates a column named `Email Address`, Sheety may expose it as `emailAddress`. Aero Scout supports both `email` and `emailAddress`.

## Sheety Setup

1. Create a Sheety project for the Google Sheet.
2. Enable API access for both tabs:
   - `prices`
   - `users`
3. Copy the project base URL into `SHEETY_BASE_URL`.
4. Add either bearer token authentication or basic authentication in `.env`.

Example base URL:

```text
https://api.sheety.co/<username>/<projectName>
```

Aero Scout will call:

```text
GET /prices
PUT /prices/{id}
GET /users
```
