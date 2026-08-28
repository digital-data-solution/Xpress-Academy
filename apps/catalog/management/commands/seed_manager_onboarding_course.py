from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# First staff-training course — internal-only (is_staff_training=True,
# never in the public catalog, access is per-Enrollment not is_staff —
# see apps.catalog.views). Real content grounded in this exact
# codebase, not generic manager-onboarding filler: what a Course
# Manager actually does in this admin, day to day.

MODULES = [
    ("Welcome — What This Role Actually Covers",
     """<h2>Your access, in plain terms</h2>
<p>You have a staff account with the "Course Manager" Django group. That gives you real, working access to four areas of the admin: course content (Catalog), instructor review and verification (Instructors), the learner support inbox (Support), and the day-to-day alert queue (Operations → Signals). You do not have access to payments, coupons, other users' accounts, or system configuration — that's deliberate, not a bug, and it's covered in detail in the last module of this course.</p>
<h2>How to log in</h2>
<p>The admin lives at a non-default URL — you were sent it directly. Log in with your own email and the password you set at signup. The same login also works on the public-facing site if you ever want to view a course the way a learner sees it.</p>
<h2>Why this course exists</h2>
<p>Everything in this course is real — the same workflows, the same admin screens, the same rules the system actually enforces (not just suggests). Finishing it and passing the final check is what confirms you're ready to work independently in the admin.</p>"""),
    ("Managing Courses — The Review-and-Publish Workflow",
     """<h2>The content hierarchy</h2>
<p>Everything sits under a Programme (e.g. "Business & Entrepreneurship"), which contains Courses, which contain Modules, which contain Lessons. A Course also has FAQs and Resources attached directly. You can create and edit all of these — Programme, Course, Module, Lesson, Resource, Course FAQ — from the Catalog section of the admin.</p>
<h2>The publication gate — a real rule, not a suggestion</h2>
<p>Every Course has a review_status field (Draft → Submitted → In review → Approved, or Changes requested / Delisted). A course's is_published checkbox can only ever be turned on when review_status is Approved — this is enforced at the database level, so there's no way to accidentally publish something that hasn't been marked Approved first, even by mistake.</p>
<h2>What "publish" actually does</h2>
<p>The moment a course's is_published flips from off to on, the system automatically notifies our CRM that a new course went live — no extra step, no separate email to send. That's also why review_status matters: it's your real checkpoint before that notification fires and the course becomes visible to the public.</p>
<h2>Practical workflow</h2>
<p>Open a course in Catalog → Courses. Check the content is genuinely ready (modules, lessons, FAQs all present and correct). Set review_status to Approved once you're satisfied. Only then tick is_published and save.</p>"""),
    ("Instructor Applications and Verification",
     """<h2>How someone becomes an instructor</h2>
<p>Instructors apply through the public site, not a self-serve builder — an application creates an Instructor record with verification_status set to Unverified, and you get notified. Your job is to actually review what they submitted before doing anything else.</p>
<h2>Reviewing documents before verifying</h2>
<p>Open the Instructor record in Instructors → Instructors. Their submitted documents are attached inline (Instructor documents) — open and actually look at them. Only after that should you use the "Mark selected as VERIFIED" action on the Instructors list. That action does not check the documents for you — it trusts that you already did.</p>
<h2>Course reviews</h2>
<p>When an instructor submits a course for review, a Course review record is created automatically — you don't create these yourself. You record your outcome and notes on the existing record; it's append-only once completed, so there's no editing a review after the fact.</p>
<h2>Moderating ratings</h2>
<p>If a learner review/rating is abusive, open it under Instructors → Course ratings and use "Remove for abuse" — this is logged, not silently deleted.</p>"""),
    ("Learner Support — Replying to Tickets",
     """<h2>Where tickets come from</h2>
<p>Learners reach support through the site. Some questions are answered automatically by a built-in FAQ lookup (payment-pending, certificate download, login issues, and similar); anything it can't answer — or a learner explicitly asking for a human — creates or escalates a real Support ticket that gets emailed to whoever is set as the ops contact.</p>
<h2>How to actually reply</h2>
<p>Open the ticket under Support → Support tickets. You'll see the full conversation. At the bottom is always one blank message row — type your reply into it and save the ticket. That single action does two things: it saves your message as a staff reply, and it automatically emails the learner your reply. There's no separate "send" step.</p>
<h2>Closing out a ticket</h2>
<p>Once the issue is actually resolved, use the "Mark selected as RESOLVED" action on the ticket list. Don't mark something resolved just because you replied — mark it once the learner's actual problem is fixed.</p>"""),
    ("The Ops Queue — Triage in Practice",
     """<h2>What the ops queue is</h2>
<p>Operations → Signals is a running list of automated alerts the system raises on its own — things like a course with unusually low completion, a learner going quiet mid-course, or an instructor needing attention. It is not a to-do list you create yourself; it's generated.</p>
<h2>What you'll see there, and what you won't</h2>
<p>You'll see quality, learner-engagement, instructor, partner, legal, and system-type alerts. You will not see anything in the Money category — payment reconciliation issues, refund spikes, and similar are intentionally kept out of this view for your role. If you ever land directly on a signal link that 403s, that's that restriction working correctly, not an error to report.</p>
<h2>Handling a signal</h2>
<p>Open any signal to see its detail and a recommended action. From there you can Resolve it (the underlying issue is actually handled), Dismiss it (not worth acting on, with a reason), or Snooze it for a set number of days if it needs revisiting later rather than right now.</p>"""),
    ("What's Outside Your Role, and When to Escalate",
     """<h2>What you deliberately don't have</h2>
<p>No access to Payments, Coupons, Partners, or Reconciliation flags. No access to other users' accounts, or your own permission level (you can't grant yourself more access — nor can any account in this group). No access to system/automation configuration (Signal rules, interrupt budgets, digest runs). No access to the revenue dashboard — it's restricted to the account owner specifically.</p>
<h2>Why, in one sentence</h2>
<p>Your access covers everything the role actually needs — content, instructor review, learner support, day-to-day alert triage — and nothing financial or structural, so a mistake in your day-to-day work can't touch money, other people's accounts, or how the system itself is configured.</p>
<h2>When something doesn't fit</h2>
<p>If a support ticket or a signal turns out to be about a payment, refund, or something you can't act on, that's expected — escalate it directly rather than trying to work around the missing access. That boundary is there on purpose, not an oversight to route around.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("A course's review_status is 'Submitted'. Can you publish it?",
     "is_published can only be set to True when review_status is Approved — enforced at the database level.",
     "No — review_status must be Approved first",
     "Yes, publishing and review are independent"),
    ("What happens automatically the moment a course's is_published flips from off to on?",
     "The CRM is notified automatically via webhook — no separate email or manual step is needed.",
     "The CRM is notified automatically",
     "Nothing — you must separately notify the CRM yourself"),
    ("Before using 'Mark selected as VERIFIED' on an instructor, what should you do?",
     "The action itself doesn't check documents — it trusts you already reviewed them first.",
     "Actually open and review their submitted documents",
     "Nothing extra — the action checks the documents for you"),
    ("How do you reply to a learner's support ticket?",
     "Typing into the blank message row and saving both records your reply and emails the learner — one step.",
     "Type into the blank message row at the bottom and save",
     "Reply directly to the notification email you received"),
    ("Which category of signal will you NOT see in the ops queue?",
     "Money-category signals (payment reconciliation, refund spikes) are restricted to the account owner.",
     "Money",
     "Quality"),
]


class Command(BaseCommand):
    help = (
        "Seeds the 'Manager Onboarding' staff-training course (is_staff_training=True) — "
        "6 modules covering the real admin workflows a Course Manager uses, plus a short final "
        "exam. Enrolls the user matching --email if given and found. Safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email", default="", help="Email of a User to enroll in the course once seeded."
        )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="staff-training",
            defaults={
                "title": "Staff Training",
                "audience": Audience.GENERAL,
                "description": "Internal training for Xpress Digital Academy staff — never shown publicly.",
                "is_active": True,
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="manager-onboarding",
                defaults={
                    "title": "Manager Onboarding",
                    "subtitle": "The real admin workflows a Course Manager uses — courses, instructors, support, ops.",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_staff_training": True,
                    "is_compulsory_staff_training": True,
                    "review_status": Course.ReviewStatus.APPROVED,
                    "is_published": True,
                    "meta_description": "Internal onboarding for Xpress Digital Academy Course Managers.",
                },
            )

            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
            else:
                self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))
                for i, (title, body) in enumerate(MODULES, start=1):
                    module = Module.objects.create(
                        course=course, order=i, title=title, unlock_rule=Module.UnlockRule.IMMEDIATE,
                    )
                    Lesson.objects.create(
                        module=module, order=1, title=f"Module {i}: {title}", type=Lesson.Type.TEXT,
                        body=body.strip(), is_preview=False,
                    )
                self.stdout.write(self.style.SUCCESS(f"  {len(MODULES)} modules created with real written content."))

                bank = QuestionBank.objects.create(
                    organization=org, name="Manager Onboarding — Final Check",
                    description="Covers all 6 modules — must be passed to complete onboarding.",
                )
                for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                    q = Question.objects.create(
                        bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                        difficulty=Question.Difficulty.EASY,
                    )
                    Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                    Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
                Quiz.objects.create(
                    scope=Quiz.Scope.FINAL, course=course, title="Manager Onboarding — Final Check",
                    instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course.",
                    bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                    max_attempts=0, time_limit_minutes=0,
                )
                self.stdout.write(self.style.SUCCESS("Created the final check."))

            # Runs regardless of created/already-existed, so re-running
            # this command against a course seeded before the
            # compulsory field existed (as happened once in prod)
            # brings it up to date rather than silently leaving it on
            # the old opt-in shape. Never touches questions/quizzes —
            # only the create branch above does that.
            #
            # Modules are deliberately NOT time-gated (unlock_rule=
            # IMMEDIATE, not DRIP_DAYS) — a brief earlier version of
            # this command drip-locked them a week apart, which was a
            # real misread of the ask: "staff get trained on a regular
            # cadence" meant new courses being ADDED to the compulsory
            # track over time, not existing content inside one course
            # being time-locked from someone motivated to finish it
            # sooner. This block un-drips anyone still on that shape.
            changed = []
            if not course.is_compulsory_staff_training:
                course.is_compulsory_staff_training = True
                changed.append("is_compulsory_staff_training")
            if changed:
                course.save(update_fields=changed)
                self.stdout.write(self.style.SUCCESS(f"  Updated course field(s): {', '.join(changed)}."))
            existing_modules = list(course.modules.order_by("order"))
            unlocked = 0
            for module in existing_modules:
                if module.unlock_rule != Module.UnlockRule.IMMEDIATE or module.drip_days != 0:
                    module.unlock_rule = Module.UnlockRule.IMMEDIATE
                    module.drip_days = 0
                    module.save(update_fields=["unlock_rule", "drip_days"])
                    unlocked += 1
            if unlocked:
                self.stdout.write(self.style.SUCCESS(f"  Unlocked {unlocked} module(s) — no more time-gating."))

        email = options["email"].strip()
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                self.stdout.write(self.style.WARNING(f"No user found for {email} — not enrolled. Run again once they've signed up."))
            else:
                enrollment, enrolled_now = Enrollment.objects.get_or_create(user=user, course=course)
                if enrolled_now:
                    from apps.accounts.signal_receivers import _send_welcome_to_training_email
                    _send_welcome_to_training_email(user, course)
                    self.stdout.write(self.style.SUCCESS(f"Enrolled {email} in {course.title} and sent the welcome email."))
                else:
                    self.stdout.write(self.style.WARNING(f"{email} was already enrolled."))

        self.stdout.write(self.style.SUCCESS("Done — course is published (is_staff_training=True, hidden from the public catalog)."))
