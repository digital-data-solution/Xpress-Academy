"""The only place in this codebase that calls Flutterwave's HTTP API.
No requests.post to Flutterwave anywhere else in the codebase.

Deliberately thin: initialize, verify, list transactions. No refund,
transfer, subaccount, or payout methods exist here — the Flutterwave
account belongs to Xpress Digital and Data Solutions and is shared
with its own store, so Academy code never touches account-wide state.

Responses are normalized to one shape services.py reads (amounts in
kobo, status "success", `reference`/`metadata` keys), so the payment
lifecycle code doesn't care which provider sits behind it.
"""

from decimal import Decimal

import requests
from django.conf import settings

FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"
REQUEST_TIMEOUT_SECONDS = 15


class GatewayError(Exception):
    """Raised for a transport/HTTP-level failure or a Flutterwave-reported
    error at the API-call level (bad request, auth failure, unknown
    reference, etc.) — NOT for a legitimate "transaction failed"
    business result, which callers handle themselves by reading the
    normalized status."""


def _to_kobo(amount) -> int | None:
    if amount is None:
        return None
    return int(Decimal(str(amount)) * 100)


class FlutterwaveGateway:
    def __init__(self, secret_key: str | None = None):
        self.secret_key = secret_key or settings.FLUTTERWAVE_SECRET_KEY

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method, path, **kwargs):
        url = f"{FLUTTERWAVE_BASE_URL}{path}"
        try:
            resp = requests.request(
                method, url, headers=self._headers(), timeout=REQUEST_TIMEOUT_SECONDS, **kwargs
            )
        except requests.RequestException as exc:
            # Never let the secret key leak into an error message or log line.
            raise GatewayError(f"Network error calling Flutterwave ({method} {path}): {exc}") from exc

        try:
            data = resp.json()
        except ValueError as exc:
            raise GatewayError(f"Flutterwave returned non-JSON response ({resp.status_code})") from exc

        if resp.status_code >= 400 or data.get("status") != "success":
            message = data.get("message", "Unknown Flutterwave error")
            raise GatewayError(f"Flutterwave API error ({resp.status_code}): {message}")

        return data

    def initialize_transaction(self, *, email, amount_kobo, reference, callback_url, metadata):
        payload = {
            "tx_ref": reference,
            "amount": str(Decimal(amount_kobo) / 100),
            "currency": "NGN",
            "redirect_url": callback_url,
            "customer": {"email": email},
            # Flutterwave meta values must be flat and non-null.
            "meta": {k: v for k, v in metadata.items() if v is not None},
            "customizations": {"title": "Xpress Digital Academy"},
        }
        data = self._request("POST", "/payments", json=payload)
        return {"status": True, "data": {"authorization_url": data["data"]["link"]}, "raw": data}

    def verify_transaction(self, reference):
        data = self._request("GET", "/transactions/verify_by_reference", params={"tx_ref": reference})
        txn = data.get("data") or {}
        return {"status": True, "data": self._normalize(txn), "raw": data}

    def list_transactions(self, *, from_dt, to_dt, status=None, page=1, per_page=100):
        params = {
            "from": from_dt.date().isoformat(),
            "to": to_dt.date().isoformat(),
            "page": page,
        }
        if status:
            params["status"] = "successful" if status == "success" else status
        data = self._request("GET", "/transactions", params=params)
        page_info = (data.get("meta") or {}).get("page_info") or {}
        return {
            "data": [self._normalize(txn) for txn in data.get("data") or []],
            "meta": {"total": page_info.get("total", 0), "total_pages": page_info.get("total_pages", 0)},
        }

    @staticmethod
    def _normalize(txn: dict) -> dict:
        return {
            "id": txn.get("id"),
            "status": "success" if txn.get("status") == "successful" else txn.get("status"),
            "amount": _to_kobo(txn.get("amount")),
            "currency": txn.get("currency"),
            "reference": txn.get("tx_ref", ""),
            "metadata": txn.get("meta") or {},
            "paid_at": txn.get("created_at"),
            "payment_type": txn.get("payment_type"),
        }
