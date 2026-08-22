"""The only place in this codebase that calls Paystack's HTTP API —
per the payments addendum: "Put all Paystack HTTP calls behind
apps/payments/gateway.py with a thin client class. No requests.post
to Paystack anywhere else in the codebase."

Deliberately thin: initialize, verify, list transactions. No refund,
transfer, subaccount, or customer-list methods exist here — the
addendum §5 forbids calling them from Academy code at all, since they
touch account-wide state shared with Xpress Vet Marketplace.
"""

import requests
from django.conf import settings

PAYSTACK_BASE_URL = "https://api.paystack.co"
REQUEST_TIMEOUT_SECONDS = 15


class PaystackError(Exception):
    """Raised for a transport/HTTP-level failure or a Paystack-reported
    error at the API-call level (bad request, auth failure, etc.) —
    NOT for a legitimate "transaction status: failed" business result,
    which callers handle themselves by reading the response body."""


class PaystackGateway:
    def __init__(self, secret_key: str | None = None):
        self.secret_key = secret_key or settings.PAYSTACK_SECRET_KEY

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method, path, **kwargs):
        url = f"{PAYSTACK_BASE_URL}{path}"
        try:
            resp = requests.request(
                method, url, headers=self._headers(), timeout=REQUEST_TIMEOUT_SECONDS, **kwargs
            )
        except requests.RequestException as exc:
            # Never let the secret key leak into an error message or log line.
            raise PaystackError(f"Network error calling Paystack ({method} {path}): {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise PaystackError(f"Paystack returned non-JSON response ({resp.status_code})") from exc

        if resp.status_code >= 400 or not data.get("status", True):
            message = data.get("message", "Unknown Paystack error")
            raise PaystackError(f"Paystack API error ({resp.status_code}): {message}")

        return data

    def initialize_transaction(self, *, email, amount_kobo, reference, callback_url, metadata):
        payload = {
            "email": email,
            "amount": amount_kobo,
            "reference": reference,
            "callback_url": callback_url,
            "metadata": metadata,
        }
        return self._request("POST", "/transaction/initialize", json=payload)

    def verify_transaction(self, reference):
        return self._request("GET", f"/transaction/verify/{reference}")

    def list_transactions(self, *, from_dt, to_dt, status=None, page=1, per_page=100):
        params = {
            "from": from_dt.isoformat(),
            "to": to_dt.isoformat(),
            "page": page,
            "perPage": per_page,
        }
        if status:
            params["status"] = status
        return self._request("GET", "/transaction", params=params)
