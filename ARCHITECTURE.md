# Architecture notes

Started in Phase 6; will grow to cover the unlock service and the
multi-tenant key too (build spec §12 lists this as a final deliverable
— starting it now while the payments reasoning is fresh).

## Why there is no Paystack webhook

**Do not add one without reading this first.**

The Paystack account this codebase pays into is **shared with Xpress
Vet Marketplace**, a separate product on the same company account.
Paystack allows exactly one webhook URL per business account per mode
(test/live), and it already points at Xpress Vet's backend. If you
point it at Academy instead, Xpress Vet's payments silently stop being
processed. If you build an Academy webhook endpoint "for completeness"
and someone later repoints the dashboard URL at it "to fix" something,
same outcome, discovered much later and much worse.

**Payment status is determined by asking Paystack, never by being
told.** See `apps/payments/services.py`:

- `verify_and_grant()` — called from the return-handler view
  (`/checkout/return/`) and from reconciliation. The query string
  Paystack redirects the learner back with is untrusted; it only says
  *which* reference to check. The actual status always comes from a
  server-side call to Paystack's verify endpoint.
- `reconcile_pending_payments()` — every 10 minutes (currently a
  management command; Phase 7 puts it on Celery beat), catches anyone
  who closed their browser or lost network before the return redirect
  completed.
- `sweep_paystack_transactions()` — daily, the safety net's safety
  net. Lists recent Paystack successes, filters to Academy-tagged
  transactions only, and flags (never auto-grants) any with no
  matching local `SUCCESS` `Payment` for a human to look at.

`grant_access()` is the single choke point all three paths funnel
through — atomic, `select_for_update()`-locked, idempotent. No other
code in the codebase creates an `Enrollment` from a `Payment`.

## The forward path

When Academy gets its own Paystack business (Sam is pursuing this in
parallel), adding a webhook becomes a small, additive change:

1. A new view that verifies the `x-paystack-signature` header (HMAC
   SHA512 over the *raw* request body, `hmac.compare_digest`) and
   calls `verify_and_grant()` — the same function the return handler
   already uses.
2. Flip `PAYSTACK_WEBHOOK_ENABLED=True` and register the URL.
3. **Verify-on-return and reconciliation keep running regardless.**
   They are not replaced by the webhook; they are the belt to its
   braces, in case the webhook itself is ever delayed or dropped.

Full detail: the payments addendum (kept alongside `xpress-academy-
build-spec.md`, not committed to this repo).
