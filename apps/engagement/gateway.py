"""The only place in this codebase that calls Resend's HTTP API —
same discipline as apps.payments.gateway: one thin client, nothing
else makes the HTTP call directly."""

import requests
from django.conf import settings

RESEND_BASE_URL = "https://api.resend.com"
REQUEST_TIMEOUT_SECONDS = 15


class ResendError(Exception):
    pass


class ResendGateway:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.RESEND_API_KEY

    def send(self, *, to_email: str, from_email: str, subject: str, html: str) -> dict:
        if not self.api_key:
            raise ResendError("RESEND_API_KEY is not configured.")

        try:
            resp = requests.post(
                f"{RESEND_BASE_URL}/emails",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"from": from_email, "to": [to_email], "subject": subject, "html": html},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise ResendError(f"Network error calling Resend: {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise ResendError(f"Resend returned non-JSON response ({resp.status_code})") from exc

        if resp.status_code >= 400:
            raise ResendError(f"Resend API error ({resp.status_code}): {data.get('message', data)}")

        return data
