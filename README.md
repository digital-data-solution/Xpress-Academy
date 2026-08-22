# Xpress Digital Academy

Self-paced online course platform. Django 5 LMS. See `xpress-academy-build-spec.md`
(kept alongside this repo, not committed) for the full spec and phase plan.

**Status: Phase 5 — Certificates complete. At Hard Stop 2.** Custom
User, Organization, full catalog hierarchy, Enrollment/progress/
unlocking, the full quiz engine, and now automatic certificate
issuance with PDF generation and public verification. Manually
enrolled via admin, no payments wired. **Per the build spec, no
Paystack work starts until this phase is reviewed and explicitly
approved.**

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
  payments/          Paystack — Phase 6
  engagement/         email gate, Celery tasks — Phase 7
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

## Tests

```powershell
.\venv\Scripts\pytest
```

59 tests total. `apps/enrollment/tests.py` (23) covers what spec §11
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
copy page). Catalog/accounts/organizations still have no tests — same
reasoning as before, revisit before either grows real business logic.

## What's NOT built yet

Payments, email/Celery, the public site — all later phases.
**Currently at Hard Stop 2** (end of Phase 5, per build spec §8): no
Paystack work starts until this is reviewed and explicitly approved.
Phase 6 (payments) is next after that — see the payments addendum
(kept alongside this repo, not committed, same as the main build
spec) for the required architecture: the Paystack account is shared
with Xpress Vet Marketplace, so no webhooks — verify-on-return +
reconciliation instead.
