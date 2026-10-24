# Architecture notes

Started in Phase 6; will grow to cover the unlock service and the
multi-tenant key too (build spec §12 lists this as a final deliverable
— starting it now while the payments reasoning is fresh).

## How payments are confirmed

Payments go through **Flutterwave**, on the account that belongs to
**Xpress Digital and Data Solutions** (Paystack was retired in October
2026: that account belonged to VETFRESH). The old Xpress Digital store
is closing, so the account's single webhook URL points at Academy.

**Payment status is determined by asking Flutterwave, never by being
told.** Three paths each learn only *which* reference (`tx_ref`) to
check, then call `verify_and_grant()`, which asks Flutterwave's
verify-by-reference endpoint for the real status:

- **Return handler** (`/checkout/return/`) — where Flutterwave sends the
  learner after paying (`?status=…&tx_ref=…`). A `cancelled` status
  shows a "you were not charged" page and verifies nothing.
- **Webhook** (`/payments/flutterwave/webhook/`) — Flutterwave's
  server-to-server `charge.completed` notice. Rejected (401) unless the
  `verif-hash` header matches `FLUTTERWAVE_SECRET_HASH`; non-`XDA-`
  references and other events are acknowledged and ignored.
- **Reconciliation** — `reconcile_pending_payments()` every 10 minutes
  for anyone whose return and webhook both went missing, and
  `sweep_flutterwave_transactions()` daily, which flags (never
  auto-grants) any Academy success with no matching local `SUCCESS`
  `Payment` for a human to look at.

The webhook is the fast path, not the source of truth. Verify-on-return
and reconciliation keep running regardless, in case it is ever delayed
or dropped.

`grant_access()` is the single choke point all three paths funnel
through — atomic, `select_for_update()`-locked, idempotent. No other
code in the codebase creates an `Enrollment` from a `Payment`.

All Flutterwave HTTP calls live in `apps/payments/gateway.py`, which
normalizes responses (amounts in kobo, `status == "success"`) so the
lifecycle code above is provider-neutral.

## Accounting note

Academy income settles into the same Flutterwave balance as the Xpress
Digital store. The store's CRM bank-statement reconciliation will show
those settlements as unmatched until academy income is booked into its
ledger.
