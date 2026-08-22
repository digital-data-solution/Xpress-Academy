# Xpress Digital Academy

Self-paced online course platform. Django 5 LMS. See `xpress-academy-build-spec.md`
(kept alongside this repo, not committed) for the full spec and phase plan.

**Status: Phase 7 — Engagement complete.** Everything through payments
(Phase 6), plus real Celery + the email send-gate + Resend + every
scheduled task from build spec §5 — including finally putting Phase
6's reconciliation on an actual schedule. No hard stops remain; still
building straight through per the owner's direction — see *What's
next* at the bottom.

## Stack

Django 5.1, Python 3.13 (spec calls for 3.12 — see *Deviations* below),
PostgreSQL (Supabase in prod; SQLite locally by default), WhiteNoise,
Gunicorn on Render.

## Getting started (Windows)

```powershell
cd C:\Dev\xpress-academy
python -m venv venv
.\venv\Scripts\pip install -r requirements\dev.txt
copy .env.example .env
# .env already has a generated DJANGO_SECRET_KEY checked in for this
# machine's local dev — real deploys must set their own via env vars.
.\venv\Scripts\python manage.py migrate
.\venv\Scripts\python manage.py createsuperuser
.\venv\Scripts\python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` (path comes from `DJANGO_ADMIN_URL_PATH`
in `.env` — change it before any real deploy, see §10 of the build spec).

Health check: `http://127.0.0.1:8000/healthz/`

## Authoring a course (Phase 2)

Everything is created through admin — no custom CMS exists or is
planned. The path: **Programme** → **Course** (has an inline for
Modules, drag-reorderable) → open a **Module** to add its **Lessons**
(also inline, drag-reorderable) → open a **Lesson** for the full
rich-text body / video ID / attachment fields. **Resources** (the
one-page downloadables) attach to either a Course or a Module — pick
exactly one, the model enforces it.

To see this working end-to-end against real content, seed the actual
breeder-track curriculum:

```powershell
.\venv\Scripts\python manage.py seed_demo_course
```

Creates the Organization (if missing), the "Dog Breeding Courses"
programme, the 8-module "Practical Dog Breeding for Nigerian Breeders"
course with one placeholder video lesson per module (module 1's lesson
marked as a sales-page preview), one sample downloadable resource, and
(as of Phase 4) a sample `QuestionBank` with 3 real judgement-style
questions plus a module-1 quiz using them — enough to see the whole
authoring chain, not just catalog. Safe to re-run — it's idempotent
and leaves existing data alone if the course already exists. The
course seeds `is_published = False` on purpose; flip it in admin once
real content is in.

## Learning as an enrolled student (Phase 3)

There's no self-serve enrollment yet — a learner is enrolled by hand
in admin (**Enrollment** → add, pick the user and course; `source`
defaults to `MANUAL`). Once enrolled, they log in at `/account/login/`
and land on `/dashboard/`, which lists their courses with a progress
bar and a "Continue" link to wherever they left off.

- `/learn/<course_slug>/` — curriculum, with locked modules shown
  greyed-out and a plain-English reason ("Complete the previous module
  first", "Unlocks in 3 days")
- `/learn/<course_slug>/<lesson_slug>/` — the lesson itself, with a
  "Mark complete" button and prev/next navigation
- A lesson with `is_preview=True` is viewable by anyone, logged in or
  not — this is what will let the (Phase 8) sales page show a real
  lesson to a prospect. Critically, if the visitor *is* actually
  enrolled, they still get their real progress/unlock context on that
  lesson — preview is a fallback for someone with no enrollment, never
  an override for someone who has one. (This exact ordering was a real
  bug caught in testing — see *Deviations* below.)

Module unlocking is entirely computed in
`apps/enrollment/services.py::is_module_unlocked()` — nothing is
stored. `IMMEDIATE`, `SEQUENTIAL` (previous module's every lesson
complete), and `DRIP_DAYS` (N days after `enrollment.started_at`) are
all implemented and tested. `requires_quiz_pass_to_advance` and
`Course.requires_final_assessment` are now both enforced too (Phase 4
filled in the extension points Phase 3 left open) — see
`is_module_completed()` / `is_course_complete()`.

No real video playback exists yet (Bunny Stream is a later-phase
integration) — a `VIDEO` lesson currently renders a placeholder
showing its `video_id`. `TEXT`, `PDF`/`DOWNLOAD` (with the attachment
link), and `LIVE` (placeholder, Phase 7 wires scheduling) all render
for real.

## Quizzes (Phase 4)

Author in admin: **Question Bank** → add **Questions** (with inline
**Choices** — mark the correct one(s)) → **Quiz** (pick `MODULE` scope
+ a module, or `FINAL` scope + a course; set `question_count`,
`pass_mark`, `max_attempts` — 0 is unlimited, `time_limit_minutes` — 0
is untimed). A quiz's link shows up automatically on the curriculum
page next to its module, or under "Final assessment" for the course.

**Bulk import**: open a Question Bank in admin and click "Import
questions (CSV)" (top-right). Columns are documented on that page —
it's deliberately spreadsheet-shaped (fill in Excel/Sheets, export
CSV) since that's how the course-content briefs already produce quiz
questions with explanations. Bad rows are skipped with a reported
reason, not a failed import.

**Attempt lifecycle** (`apps/assessment/services.py`): questions are
drawn from the bank and **snapshotted onto the Attempt at start** —
choices, correct answers, everything — and grading only ever reads
that snapshot, never the live Question/Choice rows (tested: editing a
question after an attempt starts doesn't change that attempt's grade).
Each answer **autosaves immediately** via a small fetch() call as the
learner picks it (fire-and-forget, tolerates a dropped connection
silently) — this is the same "don't lose a mid-quiz answer to a bad
connection" principle behind the JAMB-pilot planning notes, applied
here to the actual CBT engine. The final "Submit quiz" button also
re-saves whatever's currently checked in the form before grading, so
it's correct even with JS off or if every autosave failed — there's no
single point of failure for "did the answer actually get recorded."

**Grading**: MCQ/TRUE_FALSE are binary. MULTI_SELECT gets partial
credit — `max(0, correct_selected − incorrect_selected) / total_correct`,
capped at 1.0 — full marks only for selecting the exact correct set.
This formula isn't in the spec (§4 says snapshot-and-grade-server-side
but not the scoring rule); flagging it as a decision under
*Deviations*. An expired, in-progress attempt auto-finalizes on next
touch using whatever was saved — the real Celery task for this
(`expire_stale_attempts`, every 15 min) doesn't exist until Phase 7,
so `expire_attempt_if_stale()` is called inline for now; Phase 7 just
puts it on a schedule instead of writing new logic.

## Certificates (Phase 5)

Issuance is automatic and needs no admin action: the moment
`is_course_complete()` (in `apps/enrollment/services.py`) goes true —
every lesson done, and a passing final-quiz `Attempt` too if the
course requires one — `issue_certificate()` fires from inside the
same completion path, generates the PDF, and saves it. Same "call it
inline now, Phase 7 puts it on a Celery task" pattern as quiz-attempt
expiry: the spec says the trigger is a Celery task, but there's no
task queue until Phase 7. `issue_certificate()` is idempotent and
also callable directly (e.g. from admin, for a manual backfill).

Serial format is `XDA-{audience code}-{year}-{00001}`, e.g.
`XDA-BRD-2026-00001` — generated by `next_serial()` under
`select_for_update()` on a small per-(audience, year) sequence table,
so concurrent issuance can never produce a duplicate (gaps are fine,
duplicates aren't). Verification is public, no auth, at
`/verify/<uuid>/` — shows name/course/date/serial for a valid
certificate, a clear "revoked" state, or a clear "not found" state,
and only ever those three (never a raw 404 or 500). A learner's own
copy (with a download link) lives at `/certificates/<serial>/`,
login-required and owner-only — tested that a different logged-in
user gets a 404, not someone else's certificate.

**PDF generation uses ReportLab, not WeasyPrint** — the spec allowed
either. WeasyPrint needs Pango/Cairo/GDK-Pixbuf system libraries that
are genuinely painful to install on native Windows (this is a Windows
dev machine); ReportLab is pure Python, `pip install` and done.

**The required wording is locked in as a guarded constant**
(`apps/certificates/pdf.py::CERTIFICATE_WORDING`) with a comment
telling a future editor not to touch it without checking the spec
first, and a test (`TestCertificateWording`) asserting the forbidden
words ("accredited", "licensed", "approved", "VCN", "TRCN") never
appear and the required phrase does. A sample PDF was generated
end-to-end (enrolled a test learner, completed all 8 seeded modules,
certificate auto-issued) and sent for review rather than just
described.

## Payments (Phase 6)

**Built per a payments addendum, not build spec §4 directly** — the
addendum supersedes §4's Paystack rules entirely (the Payment/Coupon/
PartnerClinic *models* it specified still stand; the *integration
mechanism* doesn't). Read `ARCHITECTURE.md`'s "Why there is no Paystack
webhook" section before touching anything here.

**The governing constraint**: this Paystack account is shared with
Xpress Vet Marketplace. One webhook URL per account, already claimed
by Xpress Vet's backend — Academy can't use it and must never try.
Instead:

- `/checkout/<course_slug>/` — login required, optional coupon code,
  initializes a Paystack transaction with a **per-transaction
  `callback_url`** (mandatory — omitting it silently sends the learner
  to Xpress Vet's dashboard) and `metadata.product = "xpress_academy"`
  on every single transaction, no exceptions. The local `Payment` row
  is created `PENDING` *before* Paystack is ever called.
- `/checkout/return/` — the learner lands here after paying. The
  query string is **untrusted** — it only says which reference to
  check. `verify_and_grant()` calls Paystack's verify endpoint
  server-side and asserts status/amount/currency/reference/
  `metadata.product` all match before granting anything.
- `grant_access()` (`apps/payments/services.py`) is the **single choke
  point** — atomic, `select_for_update()`-locked, idempotent. Every
  path that can conclude a payment succeeded calls this one function;
  nothing else creates an `Enrollment` from a `Payment`.
- **Reconciliation is the safety net, not optional.** Two management
  commands implement what the addendum specifies as scheduled tasks —
  `reconcile_pending_payments` (meant to run every 10 minutes: verifies
  any `PENDING` payment 5min–7days old, marks anything older
  `ABANDONED`) and `sweep_paystack_transactions` (meant to run daily:
  lists recent Paystack successes, filters to `XDA-`/`xpress_academy`
  transactions only — everything else is Xpress Vet's and is skipped
  entirely, never logged with customer detail — and flags, never
  auto-grants, any Academy success with no local match). **Neither is
  actually scheduled yet** — Celery beat doesn't exist until Phase 7,
  so until then these need running by hand or via Windows Task
  Scheduler/cron if real money is moving. This is a real operational
  gap, not a cosmetic one; flagging it plainly rather than burying it.
- **No webhook view exists**, deliberately — see `ARCHITECTURE.md`.
- **Referral capture**: `ReferralCaptureMiddleware` stores `?ref=CODE`
  in the session for 30 days on any request (not just a checkout page,
  since Phase 8's sales pages don't exist yet but a referral link
  should still work whenever they land). Attribution and coupon
  redemption both happen inside `grant_access()`'s atomic block.
- **Refunds are manual, always** — `refund_payment()` only ever flips
  local `Payment.status = REFUNDED`. It never calls Paystack's refund
  API (addendum §5: that endpoint touches account-wide state shared
  with Xpress Vet). Sam issues the actual refund from the dashboard.

**The concurrency test the addendum specifically calls out** —
"Return handler and reconciliation task racing on the same reference
create exactly one Enrollment... the one people skip" — is
`TestGrantAccessIdempotency::test_concurrent_grant_access_creates_exactly_one_enrollment`,
five real threads hitting `grant_access()` simultaneously. Building it
surfaced two genuine bugs before either could ship (see *Deviations*).

**To click through checkout in a browser** (not just run the test
suite, which mocks Paystack entirely): put real Paystack **test mode**
keys from the shared Xpress Vet dashboard into `.env` —
`PAYSTACK_SECRET_KEY` / `PAYSTACK_PUBLIC_KEY` — nothing else is
needed locally. `SITE_URL` already defaults to
`http://localhost:8000`, which is what gets used to build the
callback URL Paystack redirects back to.

## Engagement (Phase 7)

**Nothing extra to run locally.** `CELERY_TASK_ALWAYS_EAGER=True` in
`dev.py` means every task runs synchronously, in-process, on
`.delay()` — no Redis, no worker, no beat needed for `manage.py
runserver` or the test suite. A real deployment (Phase 9) runs
`celery -A config worker -B` against Redis for real.

**The email gate** (`apps/engagement/services.py::send_email()`) is
the only thing in the codebase allowed to call Resend — same
one-choke-point discipline as the Paystack gateway. It's idempotent
per `dedupe_key` (a retried Celery task, or two tasks racing on the
same event, can't double-send — tested, including that a *failed*
send under a dedupe_key can still be retried, only a *successful* one
blocks a resend), and soft-rate-limits by sleeping briefly if too many
sent in the last 60 seconds rather than hard-rejecting or silently
dropping. With no `RESEND_API_KEY` configured (the local default),
it logs the email and marks it `SENT` anyway rather than erroring —
the whole app works end to end without a Resend account.

**All six §5 tasks are real**, on `config/celery.py`'s beat schedule,
WAT-timezoned:

| Task | Schedule | Notes |
|---|---|---|
| `unlock_dripped_modules` | hourly | "just crossed the threshold" window, not every already-unlocked module |
| `detect_stalled_learners` | daily 09:00 | stops at 3 nudges, counted from past `EmailLog` rows, not a stored counter |
| `warn_expiring_access` | daily | 14-day and 3-day warnings — see the exclusive-bands note below |
| `expire_enrollments` | daily | flips past-expiry `ACTIVE` → `EXPIRED` |
| `remind_live_session` | hourly | 24h and 1h windows |
| `expire_stale_attempts` | every 15 min | new bulk `expire_all_stale_attempts()` — Phase 4 only had the reactive per-attempt version |

Plus what Phase 6 built but couldn't schedule — `reconcile_pending_payments_task`
(every 10 min) and `sweep_paystack_transactions_task` (daily 02:00
WAT), closing the gap flagged at the end of Phase 6. `issue_certificate`
stays a direct inline call, not a task — it's event-triggered, not
scheduled, so there's nothing for a beat schedule to do with it.

**A real bug in `warn_expiring_access`, caught by testing an edge
case that matters in practice** (a task that catches up after being
down, or an enrollment whose window is discovered late): the first
version checked the 14-day and 3-day thresholds independently
(`days_left <= window`), which overlap — a `days_left` of 2 satisfies
*both*. If the 14-day warning hadn't gone out yet, the very next run
sent it **and** the 3-day warning back to back, seconds apart. Fixed
by treating the windows as exclusive bands (14 fires for
`3 < days_left <= 14`, 3 fires for `days_left <= 3`) so at most one
email ever goes out per enrollment per run, while each window still
independently fires exactly once over the enrollment's lifetime.

**Welcome and certificate-issued emails are now real**, not the log
placeholders Phases 5 and 6 left behind — `grant_access()` and
`issue_certificate()` each queue their send via `transaction.on_commit()`,
so a failed send can never roll back the enrollment/certificate it's
about, and the send only fires once the surrounding transaction has
actually committed.

## Database

**Local default: SQLite**, zero setup — good enough for Phase 1–3 model
and admin work. From Phase 4 onward, switch to real Postgres locally
so JSONField/array/constraint behaviour matches production instead of
surprising you later:

```powershell
docker compose up -d db
# then set in .env:
# DATABASE_URL=postgres://postgres:postgres@localhost:5432/xpress_academy
```

**Production: Supabase Postgres.** Per the build spec §3 — if
`DATABASE_URL` points at the transaction-mode pooler (port `6543`),
`prod.py` automatically sets `DISABLE_SERVER_SIDE_CURSORS=True` and
`CONN_MAX_AGE=0` (pgbouncer breaks server-side cursors under
transaction pooling). **Always run `manage.py migrate` against the
direct connection (port `5432`)**, not the pooler — export a
`DATABASE_URL` pointing at 5432 just for that command, e.g.:

```bash
DATABASE_URL=postgres://...:5432/postgres python manage.py migrate
```

then switch the deployed app's `DATABASE_URL` env var back to the
6543 pooler URL for normal running.

## Settings layout

```
config/settings/base.py   shared by every environment
config/settings/dev.py    local dev (manage.py defaults here)
config/settings/prod.py   Render (wsgi.py / asgi.py default here)
```

Select explicitly with `DJANGO_SETTINGS_MODULE` env var; Render will
set this to `config.settings.prod`.

## Project layout

```
config/            settings, urls, wsgi/asgi
apps/
  common/           TimeStampedModel, OrganizationOwnedModel, shared mixins
  organizations/     Organization — the tenant. One row today.
  accounts/          custom User (email login, no username) + Profile
  catalog/           Programme/Course/Module/Lesson — Phase 2
  enrollment/        Enrollment/Cohort/LessonProgress, unlock service,
                      access control, learner dashboard/curriculum/player — Phase 3
  assessment/        QuestionBank/Question/Quiz/Attempt, CSV import,
                      attempt lifecycle + grading, quiz runner views — Phase 4
  certificates/       Certificate + CertificateSequence, PDF generation,
                      public verify + learner's own copy — Phase 5
  payments/          Payment/Coupon/Partner/ReconciliationFlag, Paystack
                      gateway client, checkout + return-handler views,
                      referral middleware — Phase 6
  engagement/         EmailLog/LiveSession, Resend gateway, send-gate
                      service, all six scheduled Celery tasks — Phase 7
templates/, static/, requirements/
```

Business logic belongs in `apps/<app>/services.py`, not in views.
`apps/enrollment/services.py` is the first real one — unlock
computation, progress, completion. `apps/enrollment/access.py` holds
the `@requires_active_enrollment` decorator that gates every `/learn/`
view (build spec §7).

## Multi-tenancy

Every tenant-owned model inherits `apps.common.models.OrganizationOwnedModel`,
which carries a `PROTECT`-guarded FK to `Organization`. One organization
exists today (Xpress Digital Academy). Adding a second tenant later is
meant to be a data operation — create a row, point new content at it —
not a schema rewrite. No tenant-switching UI exists or is planned yet.

**Where the FK actually lives (interpretation, flagged per §0):** the
spec says every tenant-owned model carries the key. Read literally on
`catalog`, that would put `organization` on `Programme`, `Course`,
`Module`, `Lesson`, and `Resource` alike. Instead, only `Programme`
and `Course` — the top-level owned entities — carry it directly;
`Module`/`Lesson`/`Resource` scope through their FK to `Course`/`Module`.
Reasoning: a duplicated FK on every child row is a second place for
tenant identity to live and drift out of sync with its parent (a
Module quietly pointing at a different org than its Course is exactly
the kind of bug a redundant FK invites, not prevents) — the FK chain
is the single source of truth instead. Say if this reading is wrong;
it's a two-migration change to add the field back everywhere.

## Deviations from the build spec (flagging per §0 — "ask before you assume")

- **Python 3.13, not 3.12.** Only 3.13 was available on this machine;
  no 3.12 install exists. Django 5.1 officially supports 3.13. Low
  risk, but noted since the spec was explicit. Install 3.12 and
  recreate the venv if you want to match the spec exactly.
- **Docker was mentioned as available but isn't reachable from this
  shell** (not on PATH, daemon status unconfirmed). `docker-compose.yml`
  is written and ready but unverified — run `docker compose up -d`
  yourself to confirm it works on this machine before relying on it.
- **SQLite is the local default**, not Postgres, so Phase 1 has zero
  setup friction. Documented above how to switch to Postgres via
  Docker once you're ready (recommended by Phase 4).
- **CKEditor 5, not the older `django-ckeditor` (CKEditor 4) package**,
  for the rich-text fields the spec calls for in Phase 2 (lesson
  bodies, course descriptions). Started with the latter, hit a
  built-in warning that it bundles CKEditor 4 with unfixed security
  issues, and swapped before it touched a migration. Admin-only
  surface (only staff ever see the editor), but no reason to ship a
  known-vulnerable dependency when a maintained one drops in cleanly.
- **Tenant FK placement** on the catalog hierarchy — see *Multi-tenancy*
  above.
- **Added a `slug` field to `Lesson`** that isn't in the spec's §4
  model list. §6's URL scheme is `/learn/<course_slug>/<lesson_slug>/`,
  which needs some way to address a lesson in a URL that the spec
  never otherwise specifies — global uniqueness, auto-slugified from
  title with a numeric suffix on collision.
- **Preview-lesson bypass ordering** in `requires_active_enrollment`
  — real enrollment is always looked up first; `is_preview` is only a
  fallback when there's none. Getting this backwards (checking
  `is_preview` before looking for a real enrollment) was a genuine bug
  caught by testing the admin/views authenticated rather than trusting
  `manage.py check`: module 1's seeded lesson is marked preview (so
  the sales page has something to show), which silently broke
  progress-marking for an actually-enrolled learner on that lesson
  specifically. Fixed, and covered by
  `TestAccessControl::test_preview_lesson_does_not_shadow_a_real_enrollment`
  so it can't come back unnoticed.
- **Topic is global, not per-organization** — a deliberate carve-out
  from the tenant-FK non-negotiable, same category as Django's own
  Permission/ContentType being global. Reasoning and Phase 11 tie-in
  (`quiz.item_bad` aggregates question quality, which is more useful
  unfragmented) in `apps/assessment/models.py`.
- **`Question`/`Choice` deletion is `CASCADE`/`PROTECT`-mixed, not
  uniformly protective like Course/Organization** — a Question can be
  deleted freely via its bank (`CASCADE`) because everything a past
  Attempt needs is already frozen into its `question_snapshot`;
  deleting the live row doesn't corrupt historical grading. `Choice`
  cascades from `Question` the same way. `AttemptAnswer.question` is
  the one `PROTECT` in this cluster — deliberately, because that's
  the live FK the Phase 11 `quiz.item_bad` signal aggregates over, and
  answer history is real analytics value, not disposable.
- **Partial-credit formula for MULTI_SELECT** isn't in the spec —
  see *Quizzes* above.
- **ReportLab instead of WeasyPrint** for certificate PDFs — see
  *Certificates* above. Both were spec-acceptable.
- **Certificate issuance triggered inline, not by a Celery task** —
  same "no task queue exists yet" reasoning as quiz-attempt expiry in
  Phase 4.
- **`PartnerClinic` renamed to `Partner`** before it ever touched a
  migration — Sam's call mid-build: the referral mechanism is generic
  and later verticals (JAMB prep, cybersecurity — Phase 10) will have
  referral partners that aren't veterinary clinics. `Enrollment.Source.CLINIC_PARTNER`
  renamed to `PARTNER` to match.
- **`Payment.raw_webhook_payload` (spec §4) doesn't exist — replaced
  by `raw_verify_response`.** There's no webhook (see *Payments*
  above), so what's actually captured is the verify-endpoint response;
  the field is named for what it holds.
- **`ReconciliationFlag` stands in for Phase 11's `operations.Signal`**,
  which doesn't exist yet. The addendum requires
  `sweep_paystack_transactions` to raise a `CRITICAL` signal for a
  human to review — built a minimal model that does the same job now
  (visible in admin, resolvable) rather than blocking Phase 6 on
  Phase 11. Migrate its rows across when Phase 11 ships; don't delete
  the safety net in the meantime — see the model's docstring.
- **Reconciliation isn't actually scheduled** — no Celery beat until
  Phase 7. The two management commands exist and are correct, but
  nothing runs them automatically yet. Flagged plainly in *Payments*
  above since this is a real gap if real money starts moving before
  Phase 7 lands, not a cosmetic one.
- **Two real concurrency-adjacent bugs, caught by actually running the
  required concurrency test rather than skipping it** (the addendum
  predicted people skip it — didn't): (1) `initialize_payment` was
  wrapped in `@transaction.atomic`, so deliberately raising
  `PaymentInitError` after marking a failed `Payment` rolled back the
  Payment's *creation* too — the exact "payment lost track of" failure
  mode the addendum warns against. Fixed by removing the wrapper;
  each write commits on its own. (2) `verify_and_grant` returned the
  caller's stale, pre-update `Payment` object instead of the one
  `grant_access` actually mutated (`grant_access` re-fetches its own
  copy under `select_for_update()` and returns the `Enrollment`, not
  the `Payment`) — fixed with an explicit `refresh_from_db()`. Also:
  SQLite has no real row-level locking (`select_for_update()` degrades
  to file-level contention), which isn't a code bug but did require a
  higher `busy_timeout` in `dev.py` and a bounded retry in the
  concurrency test itself to get a stable result — noted inline in
  both places so it doesn't read as the underlying logic being flaky.

## Tests

```powershell
.\venv\Scripts\pytest
```

91 tests total. `apps/enrollment/tests.py` (23) covers what spec §11
requires before Hard Stop 1: unlock rules and edges, enrollment-active
edge cases, progress/completion, access control. `apps/assessment/tests.py`
(21) covers what §11 requires for assessment: MCQ/multi-select/partial-
credit grading (including a test that proves grading reads the frozen
snapshot, not live Question/Choice data, by editing them mid-attempt
and confirming the grade doesn't change), attempt limits, timer
expiry with answers-given preserved, CSV import (valid + malformed
rows), the module-quiz-gates-next-module and final-quiz-completes-
course wiring, and the full HTTP flow (start → autosave → submit →
results) including confirming `is_correct` never appears in the
attempt page's HTML before submission. `apps/certificates/tests.py`
(15) covers what §11 requires for certificates: completion → issuance
including the explicit negative case (final assessment required but
not passed → no certificate), idempotency, serial sequencing, the
required-wording/forbidden-words check, a real PDF actually
generating (`%PDF` magic bytes), and the verification views (valid /
revoked / not-found states, owner-only access to the learner's own
copy page). `apps/payments/tests.py` (32) covers every case the
payments addendum §6 lists by name: callback_url/metadata.product
always present, tampered/unknown reference grants nothing,
Paystack-reports-failed grants nothing, mismatched amount grants
nothing and marks FAILED, double `grant_access()` call creates
exactly one Enrollment, **the concurrency test** (five real threads
racing `grant_access()` on the same Payment — the one the addendum
explicitly says people skip), sweep ignores non-`XDA-` references
entirely, a stale `PENDING` that actually succeeded gets picked up by
reconciliation, coupon usage increments exactly once. All Paystack
HTTP calls are mocked — no real network calls or keys needed to run
the suite. `apps/engagement/tests.py` (23, not in spec §11's list but
written anyway — dedupe/windowing logic is exactly the kind of thing
that's silently wrong without a test) covers the send-gate's
idempotency and retry behaviour, every task's core windowing/dedup
logic including the exclusive-bands fix above, and the welcome/
certificate email wiring (using `pytest.mark.django_db(transaction=True)`,
required for `transaction.on_commit()` to actually fire in a test —
noted inline so it doesn't look like an arbitrary marker). Catalog/
accounts/organizations still have no tests — same reasoning as
before, revisit before either grows real business logic.

## What's next

No hard stops remain in the build spec after Phase 6, and the owner
has since said to keep building straight through rather than pause
between phases. Order: Phase 11 (operations/signals layer) next —
out of spec order deliberately, since Phase 11's own instruction was
to ship its money-rule §1–5 *before* Phase 6 went live, which already
didn't happen; closing that gap now rather than letting it ride
further. Then Phase 8 (public site) and Phase 9 (deploy). **Phase 10
(instructor platform) is the one exception** — its spec explicitly
says not to build it until Phase 9 is done *and* a first-party course
has actually sold to a real learner. That's a fact-of-reality gate,
not an approval checkpoint, so it's the one place this project stops
and waits regardless of how much momentum there is.
