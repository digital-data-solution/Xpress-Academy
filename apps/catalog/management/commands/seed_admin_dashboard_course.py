from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# Standalone role-specific course (is_staff_training=True, NOT
# is_compulsory_staff_training) -- same pattern as Manager Onboarding,
# not part of the universal 15-course chain. Content grounded in a
# real research pass through the actual Xpress CRM admin dashboard
# codebase, relayed from xpress-digital-and-data-solutions-58. All
# modules unlock_rule=IMMEDIATE -- no time-gating, per the earlier,
# hard-learned lesson on this track.

MODULES = [
    ("The Access Model — Four Ways In",
     """<h2>Why this comes first</h2>
<p>Before anything else, understand who can see what. There are four distinct ways into the system, and they are not interchangeable.</p>
<h2>The four access types</h2>
<p><strong>Admin/owner login</strong> — no module gating, full access to everything. This is you.</p>
<p><strong>Staff login</strong> — a StaffAccount with a fixed set of module grants (store, social, blog, leads, email-marketing, hr, financial, reports, portfolio, slots, documents, settings, performance, onboarding). Access is binary per module — a staff member either has a module or doesn't, there's no graduated read/write within a module.</p>
<p><strong>Viewer login</strong> — sees every module but is blocked from any delete/edit/create/send-type action. A read-only tour, useful for someone who needs visibility without operational access.</p>
<p><strong>Candidate onboarding link</strong> — not a login at all. A one-time tokenized URL used for job-candidate intake, covered in its own module later.</p>
<h2>Creating and managing accounts</h2>
<p>Staff & Access (owner-only) is where accounts are created/edited/blocked and module grants assigned. Creating an account or resetting a password auto-emails the login details to that person. Blocking an account takes effect immediately. A module-grant change, however, only takes effect on that person's <strong>next login</strong> — don't expect a live permission change to apply instantly to someone already logged in.</p>
<h2>The "linked HR employee" field — easy to miss</h2>
<p>A staff account has an optional "linked HR employee" field. It is <strong>not auto-matched by email</strong> — you must set it manually. This is what makes My Performance and check-ins actually work for that person. Skipping it is a real, common gap (see the Staff Onboarding module).</p>""",
     [
         ("Which access type has no module gating at all?",
          "Admin/owner login is unrestricted — the only one with full access by default.",
          "Admin/owner login", "Staff login"),
         ("When does a module-grant change actually take effect for a staff account?",
          "Not immediately — only on that person's next login.",
          "On their next login", "Instantly, the moment you save it"),
         ("Is the \"linked HR employee\" field on a staff account auto-matched by email?",
          "No — it must be set manually, and it's what makes My Performance work for that person.",
          "No, it must be set manually", "Yes, it matches automatically by email"),
     ]),
    ("Dashboard — What It Actually Shows",
     """<h2>How it works</h2>
<p>The Dashboard live-polls roughly 9 endpoints every 60 seconds and computes its stats client-side. Worth knowing: it does <strong>not</strong> use the dedicated <code>/api/admin/stats</code> endpoint that exists for exactly this purpose — that endpoint is a hardcoded, unused stub. Don't assume changing that endpoint affects what you see here.</p>
<h2>What's real on it</h2>
<p>Overdue-invoice, unread-quote, and pending-slot alert banners; the CRM funnel; revenue trends; and a recent activity feed. All of it reflects live data pulled every minute, not a cached snapshot.</p>""",
     [
         ("Does the Dashboard use the dedicated /api/admin/stats endpoint?",
          "No — that endpoint is an unused stub. The dashboard computes its stats client-side from ~9 other live-polled endpoints.",
          "No, that endpoint is an unused stub", "Yes, that's its primary data source"),
         ("How often does the Dashboard poll for fresh data?",
          "Roughly every 60 seconds.",
          "About every 60 seconds", "Once a day"),
     ]),
    ("Financial Accounting — Real Bookkeeping",
     """<h2>Real double-entry, not a spreadsheet</h2>
<p>This module is genuine double-entry bookkeeping, with its own separate login layer. Recording a transaction requires debits and credits to actually balance before it can be posted — it will not let you post an unbalanced entry.</p>
<h2>Reports</h2>
<p>Income Statement, Balance Sheet, Cash Flow, and Trial Balance are all available as real CSV exports.</p>
<h2>What's not fully wired up yet</h2>
<p>Tax & Compliance: only a sample VAT calculator button is actually functional — don't expect a full tax-filing workflow here yet. The Settings tab is display-only in the UI right now, despite there being a working backend edit endpoint behind it — a real gap between what's built and what's exposed.</p>""",
     [
         ("Can you post an unbalanced (debits ≠ credits) transaction?",
          "No — the system requires debits and credits to balance before a transaction can be posted.",
          "No, it must balance first", "Yes, it posts and flags it for later correction"),
         ("What's the actual state of the Tax & Compliance area?",
          "Only a sample VAT calculator button is functional — not a full tax workflow yet.",
          "Only a sample VAT calculator is functional", "A complete automated tax-filing workflow"),
     ]),
    ("Blog, Social & WhatsApp Status",
     """<h2>Blog Management</h2>
<p>Draft/published/scheduled states, comment moderation, and a "Promote" action that cross-posts a blog entry to Facebook/Instagram with auto-built, platform-appropriate captions.</p>
<h2>Announcements</h2>
<p>Deliberately thin — plain CRUD, no workflow, no cron behind it. Feeds the public "What's New" banner directly.</p>
<h2>Facebook/Instagram Posting</h2>
<p>Posts can be scheduled or posted immediately — image for Facebook, image or video for Instagram. A cron job publishes due posts every minute and emails a pass/fail result. It also fires a one-time "calendar empty" alert when the scheduled queue drains completely. A separate monthly job reseeds a "fill" calendar from your own content library — this <strong>wipes any manual edits</strong> to upcoming fill posts every time it runs. That's by design, not a bug, but it's easy to lose manual tweaks if you don't know it's coming.</p>
<h2>WhatsApp Status — not automated</h2>
<p>This is genuinely important to understand correctly: there is <strong>no WhatsApp Business API integration</strong> here. It is a daily human hand-off, not automated posting. At 07:00, the system auto-derives today's content and emails a one-tap share link. A human then taps "Share to WhatsApp Status," then "Mark as posted." One reminder fires at noon if it's still unposted by then. Nothing happens automatically beyond that — if no one taps through, nothing gets posted.</p>""",
     [
         ("Does WhatsApp Status post automatically via an API integration?",
          "No — there's no WhatsApp Business API integration. It's a daily human hand-off with a one-tap share link.",
          "No — it's a human hand-off, not automated posting", "Yes, fully automated via the WhatsApp Business API"),
         ("What happens to manual edits on upcoming \"fill\" social posts when the monthly reseed job runs?",
          "They're wiped — the monthly job overwrites the fill calendar from the content library, by design.",
          "They're wiped, by design", "They're preserved and merged with new content"),
         ("How often does the FB/IG scheduled-post cron actually publish due posts?",
          "Every minute — a real, frequent cron, not a daily batch.",
          "Every minute", "Once a day"),
     ]),
    ("Digital Store",
     """<h2>What's live</h2>
<p>A real product catalog with Flutterwave payment processing, including a race-guarded single-fulfillment path (so a payment can't accidentally fulfill an order twice under concurrent requests). Publishing a new product automatically emails subscribers.</p>
<h2>What exists but has no button yet</h2>
<p>Refunds and Settlements both exist as real backend endpoints — but there's no UI button for either yet. If a refund or settlement is needed right now, it has to be actioned directly, not through the dashboard interface.</p>""",
     [
         ("What happens automatically when a new product is published?",
          "Subscribers are automatically emailed about it.",
          "Subscribers are automatically emailed", "Nothing — publishing is silent until manually announced"),
         ("Can Refunds and Settlements be triggered from the UI right now?",
          "No — both exist as backend endpoints only, with no UI button built yet.",
          "No, no UI button exists yet for either", "Yes, both have full UI buttons"),
     ]),
    ("Documents — Vault, QMS & Invoices",
     """<h2>Document Vault vs. Document Control</h2>
<p>These are the same underlying file store, distinguished by a "docLevel" setting. Document Vault is general file storage. Document Control (the QMS side) is the same store with docLevel set — documents there are auto-numbered (e.g. SOP-HR-001), versioned, require explicit approval per version, and generate review-date alerts as they age.</p>
<h2>Invoices & Receipts — the real revenue link</h2>
<p>Invoices and receipts live here too. Marking an invoice as paid does something important: it automatically creates or updates a Contact, Lead, and Deal in the CRM. This is the <strong>main path by which billed work actually becomes CRM revenue</strong> — not a side effect, the central mechanism.</p>""",
     [
         ("What distinguishes Document Control (QMS) from the general Document Vault?",
          "They're the same store — Document Control is distinguished by a docLevel setting, with auto-numbering, versioning, and approval requirements.",
          "A docLevel setting on the same underlying store", "A completely separate storage system"),
         ("What happens automatically when an invoice is marked paid?",
          "A Contact, Lead, and Deal are automatically created or updated in the CRM — the main path billed work becomes CRM revenue.",
          "A Contact, Lead, and Deal are auto-created/updated in the CRM",
          "Nothing — invoices are disconnected from the CRM"),
     ]),
    ("CRM — Leads, Deals & Quotes",
     """<h2>The pipeline</h2>
<p>XpressCRM tracks the lead pipeline through LEAD → MQL → SQL → NEGOTIATIONS → PROPOSAL → WON/LOST, alongside a Deals kanban board and Quotes.</p>
<h2>A real bug worth knowing about directly</h2>
<p>The Quotes tab's workflow buttons assume statuses that don't actually match the real backend enum — so the button meant to finalize a quote fails silently in normal use. The reliable workaround right now: a <strong>direct status update to "converted"</strong> is what actually triggers the Quote → Deal automation, not the button that's supposed to do it.</p>
<h2>Two other known gaps</h2>
<p>The Contacts page has a dead category filter — it writes to a schema field that doesn't actually exist, so filtering by category silently does nothing. Slot Booking, unlike every other conversion path in the system, has <strong>zero CRM sync</strong> — a booked slot doesn't create or update anything in the CRM on its own.</p>""",
     [
         ("What's the actual reliable way to trigger the Quote → Deal automation right now?",
          "A direct status update to \"converted\" — the intended finalize button doesn't match the real backend enum and fails.",
          "A direct status update to \"converted\"", "Clicking the quote's \"Finalize\" button"),
         ("Does Slot Booking sync with the CRM like other conversion paths do?",
          "No — Slot Booking has zero CRM sync, unlike every other conversion path in the system.",
          "No, it has zero CRM sync", "Yes, exactly like invoices and other conversions"),
         ("What's wrong with the Contacts page's category filter?",
          "It's a dead filter — it writes to a schema field that doesn't actually exist, so it silently does nothing.",
          "It writes to a nonexistent schema field, so it does nothing", "It works correctly and is fully reliable"),
     ]),
    ("Email — Marketing, Logs & Templates",
     """<h2>Email Marketing</h2>
<p>Segmented campaigns, plus a direct-send endpoint that bypasses the subscriber system entirely. Draft campaigns require a manual "Send Now" — this is exactly the mechanism by which the Academy's course-published webhook draft campaigns actually go out; nothing sends itself without that manual step.</p>
<h2>Email Logs</h2>
<p>Dual-provider Resend/Brevo failover — if one provider has an issue, sends fail over to the other rather than simply failing.</p>
<h2>Email Templates — a real disconnect</h2>
<p>Email Templates is stored in browser local storage only. It is <strong>disconnected from what automated jobs actually send</strong> — editing a template here does not change what an automated email actually contains. Don't assume a template edit here propagates anywhere.</p>""",
     [
         ("What triggers a draft email campaign (e.g. from the course-published webhook) to actually go out?",
          "A manual \"Send Now\" — draft campaigns never send themselves automatically.",
          "A manual \"Send Now\" action", "They send automatically once created"),
         ("Does editing an Email Template here change what automated jobs actually send?",
          "No — Email Templates is browser-local-storage only, disconnected from what automated sends actually use.",
          "No — it's disconnected from automated sends", "Yes, all automated emails read from these templates"),
         ("What happens if the primary email provider (Resend) has an issue?",
          "Sends fail over to the second provider (Brevo) — a real dual-provider failover, not a single point of failure.",
          "Sends automatically fail over to Brevo", "All sending stops until manually fixed"),
     ]),
    ("HR Management",
     """<h2>Employees</h2>
<p>A soft-delete archive (nothing is hard-deleted), auto-generated employee IDs, and auto-logged career history with promotion detection built in.</p>
<h2>Analytics, Org Chart, Leave, Payroll</h2>
<p>Org Chart exports directly to Document Control. Approving or rejecting a leave request now emails the employee automatically — they're not left to check manually.</p>
<h2>Performance — where training completions show up</h2>
<p>The Performance tab within HR includes a read-only Training Completions panel, fed directly by the Academy's own completion webhook — this is literally where a staff member's Academy course completions become visible on the HR side.</p>
<h2>Contract-expiry alerts</h2>
<p>These run daily and only re-arm if the exit date on that employee's record is actually edited — a stale/unedited exit date won't keep re-alerting indefinitely.</p>""",
     [
         ("Are employee records hard-deleted when someone leaves?",
          "No — Employees uses a soft-delete archive, not hard deletion.",
          "No, it's a soft-delete archive", "Yes, records are permanently removed"),
         ("Where do a staff member's Academy training completions become visible on the HR side?",
          "The Training Completions panel in HR's Performance tab — fed directly by the Academy's own completion webhook.",
          "The Training Completions panel in Performance", "They don't appear on the HR side at all"),
         ("What triggers a contract-expiry alert to re-arm?",
          "Editing the exit date on that employee's record — an unedited date won't keep re-alerting.",
          "Editing the employee's exit date", "It re-arms automatically every day regardless"),
     ]),
    ("Staff Onboarding — From Candidate to Employee",
     """<h2>The flow</h2>
<p>A tokenized, no-login candidate flow — a one-time URL, not a real account — that ends in a real Employee record once completed.</p>
<h2>Review the Job Description before finalizing</h2>
<p>The admin must review and edit the auto-generated Job Description before finalizing a new hire. Skip this, and the raw template ships with unfilled placeholders still in it — a real, avoidable mistake if rushed.</p>
<h2>The gap that matters most</h2>
<p>Finalizing a candidate does <strong>not</strong> create a StaffAccount login. That is a separate, manual step, done in Staff & Access (see the first module). Skipping it means that person has no login — and, connected to the earlier point about the "linked HR employee" field, it also breaks My Performance for them until both steps are actually done.</p>""",
     [
         ("Does finalizing a candidate in Staff Onboarding automatically create their StaffAccount login?",
          "No — that's a separate, manual step in Staff & Access. Skipping it leaves the new hire with no login.",
          "No, that's a separate manual step in Staff & Access", "Yes, it's created automatically"),
         ("What happens if the auto-generated Job Description isn't reviewed before finalizing?",
          "It ships with unfilled placeholders still in the raw template.",
          "It ships with unfilled placeholders", "It's automatically completed with reasonable defaults"),
     ]),
    ("Signature Atlas, Authorization & Promotion Readiness",
     """<h2>Signature Atlas</h2>
<p>Canonical signatures used across the system — a single source of truth rather than each module handling signatures its own way.</p>
<h2>Authorization matrix</h2>
<p>Defines who can approve what, up to what limit — a real, structured approval-authority system, not an informal understanding.</p>
<h2>Promotion Readiness scoring</h2>
<p>A weighted composite of tenure, performance, targets-met, and manager-recommendation. Missing data is <strong>excluded from the calculation, not treated as zero</strong> — an employee with no recorded manager-recommendation yet isn't penalized as if they scored zero on it.</p>""",
     [
         ("How does Promotion Readiness scoring handle a missing input (e.g. no manager recommendation on record)?",
          "It's excluded from the calculation entirely — not treated as a zero score, which would unfairly penalize the employee.",
          "It's excluded from the calculation, not scored as zero", "It's automatically scored as zero"),
         ("What does the authorization matrix define?",
          "Who can approve what, up to what limit — a structured approval-authority system.",
          "Who can approve what, up to what limit", "Only who can log into the system"),
     ]),
    ("Performance Targets & My Performance",
     """<h2>How it works</h2>
<p>Target-setting combined with self-service check-ins, and one-tap supervisor approval — only actual disputes reach the admin directly; routine approvals don't need to.</p>
<h2>Closing a target</h2>
<p>Closing a target now requires a reason: achieved, not achieved, superseded, or cancelled. A target can't just be silently closed with no record of why.</p>
<h2>The weekly reminder — unconditional</h2>
<p>The weekly reminder cron is genuinely unconditional: everyone with an active target gets emailed regardless of any recent activity on it. It doesn't check whether they've already checked in recently — worth knowing so you're not surprised by a reminder landing right after someone just updated their target.</p>""",
     [
         ("What's required to close a Performance Target?",
          "A reason — achieved, not achieved, superseded, or cancelled. It can't be closed with no reason on record.",
          "A stated reason (achieved/not achieved/superseded/cancelled)", "Nothing — it can simply be marked closed"),
         ("Does the weekly Performance Target reminder check for recent activity before sending?",
          "No — it's unconditional. Everyone with an active target gets emailed regardless of recent check-ins.",
          "No, it's sent unconditionally to everyone with an active target",
          "Yes, it only sends if there's been no activity that week"),
     ]),
    ("Reports, Activity Log & Staff/Access",
     """<h2>Reports</h2>
<p>Revenue, Invoices, Clients, Quotes, and Contacts reports — all cached for 5 minutes, so a very recent change may not appear instantly in a report view.</p>
<h2>Activity Log</h2>
<p>Fully viewer-accessible and read-only. If unauthenticated, it honestly falls back to demo data rather than silently failing or showing nothing.</p>
<h2>Staff & Access — the recap</h2>
<p>This is where everything from Module 1 actually happens: creating/editing/blocking accounts, assigning module grants, and setting the linked HR employee field. Worth revisiting Module 1 if any of that feels unfamiliar — this is the module you'll use most often as the account admin.</p>""",
     [
         ("How long are Reports cached for?",
          "5 minutes — a very recent change may not show up instantly.",
          "5 minutes", "24 hours"),
         ("What does the Activity Log show if accessed while unauthenticated?",
          "An honest demo-data fallback, rather than failing silently or showing nothing.",
          "An honest demo-data fallback", "A blank error page"),
     ]),
    ("Background Systems — What Runs Silently",
     """<h2>Why this matters</h2>
<p>A meaningful amount of real work happens with no dashboard screen behind it at all. Knowing this list exists prevents the mistake of assuming something isn't happening just because there's no UI showing it.</p>
<h2>What's actually running</h2>
<p>Contract-expiry alerts, QMS document review alerts, weekly performance reminders, the WhatsApp Status hand-off and its noon reminder, the monthly content-calendar refresh, per-minute FB/IG scheduled publishing, 10-minute auto-receipt generation, an invoice reminder ladder, a weekly admin digest, lead score decay, 14-day and 90-day nurture sequences, and the two real outbound webhooks: <code>course.published</code> (creates a draft email campaign) and <code>staff_training.completed</code> (feeds the Training Completions panel covered in the HR module).</p>
<h2>The practical takeaway</h2>
<p>If something seems to be "just happening" — a reminder email, a status change, a draft campaign appearing — it's very likely one of these background jobs, not manual action from anyone. When something surprising happens, check this list before assuming it's a bug.</p>""",
     [
         ("How often does the FB/IG scheduled-post publishing job actually run?",
          "Every minute — the same cadence covered in the Blog/Social module.",
          "Every minute", "Once every 10 minutes"),
         ("Which two real outbound webhooks were mentioned as part of these background systems?",
          "course.published (creates a draft email campaign) and staff_training.completed (feeds Training Completions).",
          "course.published and staff_training.completed",
          "invoice.paid and lead.converted"),
     ]),
]


class Command(BaseCommand):
    help = (
        "Seeds the standalone 'Admin: Xpress CRM Dashboard' course (is_staff_training=True, NOT "
        "compulsory) and enrolls --email (default omalesamuel4god@gmail.com) if the user exists. "
        "Safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", default="omalesamuel4god@gmail.com")

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="admin-training",
            defaults={
                "title": "Admin Training",
                "audience": Audience.GENERAL,
                "description": "Role-specific training for Xpress CRM dashboard admins.",
                "is_active": True,
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="admin-xpress-crm-dashboard",
                defaults={
                    "title": "Admin: Xpress CRM Dashboard",
                    "subtitle": "Every module in the CRM admin dashboard — the access model, real gotchas, and what runs silently in the background.",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_staff_training": True,
                    "is_compulsory_staff_training": False,
                    "review_status": Course.ReviewStatus.APPROVED,
                    "is_published": True,
                    "meta_description": "Role-specific admin training for the Xpress CRM dashboard.",
                },
            )
            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
            else:
                all_questions = []
                for i, (title, body, questions) in enumerate(MODULES, start=1):
                    module = Module.objects.create(
                        course=course, order=i, title=title, unlock_rule=Module.UnlockRule.IMMEDIATE,
                    )
                    Lesson.objects.create(
                        module=module, order=1, title=title, type=Lesson.Type.TEXT,
                        body=body.strip(), is_preview=False,
                    )
                    all_questions.extend(questions)
                self.stdout.write(self.style.SUCCESS(f"Created course with {len(MODULES)} modules."))

                bank = QuestionBank.objects.create(
                    organization=org, name="Admin: Xpress CRM Dashboard — Final Check",
                    description="Covers all modules — must be passed to complete the course.",
                )
                for stem, explanation, correct, wrong in all_questions:
                    q = Question.objects.create(
                        bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                        difficulty=Question.Difficulty.MEDIUM,
                    )
                    Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                    Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
                Quiz.objects.create(
                    scope=Quiz.Scope.FINAL, course=course, title="Admin: Xpress CRM Dashboard — Final Check",
                    instructions=f"{len(all_questions)} questions covering every module.",
                    bank=bank, question_count=len(all_questions), pass_mark=70,
                    max_attempts=0, time_limit_minutes=0,
                )
                self.stdout.write(self.style.SUCCESS(f"Created final check with {len(all_questions)} questions."))

        email = options["email"].strip()
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                self.stdout.write(self.style.WARNING(f"No user found for {email} — not enrolled."))
            else:
                _, enrolled_now = Enrollment.objects.get_or_create(user=user, course=course)
                if enrolled_now:
                    self.stdout.write(self.style.SUCCESS(f"Enrolled {email}."))
                else:
                    self.stdout.write(self.style.WARNING(f"{email} was already enrolled."))

        self.stdout.write(self.style.SUCCESS("Done."))
