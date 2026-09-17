from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# Standalone staff-wide course (not part of the paced general-onboarding
# sequence -- existing staff like the telecaller need this available
# immediately, not gated behind weeks of unlock_delay_days). Open to
# any staff account, not required_group-gated to one role.
#
# Grounded in real, corrected facts confirmed by the CRM session
# (xpress-digital-and-data-solutions-3a), which has read access to
# that repo. Important correction this course exists specifically to
# get right: the existing "Admin: Xpress CRM Dashboard" staff course
# describes Performance Targets from PerformanceAdminPanel.jsx -- the
# OWNER's management view (target-setting, closing a target with a
# reason). That is explicitly NOT what an ordinary staff member sees
# or does. The real staff-facing page is /my-performance
# (MyPerformance.jsx), confirmed reachable by any logged-in staff
# account regardless of module grants -- a check-in-only view. This
# course deliberately does not describe closing/creating targets,
# because staff don't do that.

MODULES = [
    ("Finding Your Performance Page",
     """<h2>Where it is</h2>
<p><code>/my-performance</code> is reachable by any logged-in staff account — it doesn't depend on which module grants you have. If you have a staff login at all, you have this page.</p>
<h2>What's on it</h2>
<p>A card per target assigned to you. Targets are set <em>for</em> you (by your manager or Sam) — this page is not where you create or define your own targets, it's where you check in on ones you've already been given.</p>"""),
    ("Checking In on a Target",
     """<h2>The basic check-in</h2>
<p>Each target card has an inline check-in: enter a value and a short note, then submit. What "value" means depends on how that specific target was set up — a number, a percentage, or a simple yes/done, depending on the target.</p>
<h2>Auto-metric targets — you may not type a number at all</h2>
<p>Some targets are linked directly to real activity data — for a telecaller, a target like "conversions this month" is very likely one of these. For a target set up this way, the number isn't something you type in: it's computed automatically from your actual Call Logs the moment you submit. If your target looks like this, your job in the check-in is just the <strong>note</strong> — the number fills itself, honestly, from what you've actually logged. This is exactly why accurate Call Logs (see the Telecaller Onboarding course) matter beyond just the call itself — they're what your own numbers here are built from.</p>
<h2>Write a real note, not a placeholder</h2>
<p>Even when the number is automatic, the note is the one part that's actually yours — real context on where things stand, not "ok" or "good progress" as a placeholder to get past the field.</p>"""),
    ("The Weekly Reminder — and What You Don't Do Here",
     """<h2>A reminder email every week, unconditionally</h2>
<p>If you have an active target, you'll get a reminder email about it every week — this fires regardless of whether you already checked in recently. Don't read a reminder as a sign you forgot or fell behind; it goes out on a fixed schedule to everyone with an active target, full stop.</p>
<h2>What you don't do on this page</h2>
<p>Creating a new target, or formally closing one out (marked achieved, not achieved, superseded, or cancelled) is your manager's or Sam's action, done from a different, owner-level view — not something available to you here. If a target of yours needs to be closed or changed, that's a conversation with them, not a button you're looking for on your own page.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("Who sets the targets that show up on your /my-performance page?",
     "Your manager or Sam sets them for you -- you check in on them, you don't create your own.",
     "Your manager or Sam", "You create your own targets on this page"),
    ("For an auto-metric target (e.g. linked to Call Logs), what do you actually type in at check-in?",
     "Just a note -- the number is computed automatically from your real activity data, not typed in.",
     "Just a note -- the number fills itself in", "The exact number, calculated by hand"),
    ("You get a weekly reminder email about a target you already checked in on yesterday. What does that mean?",
     "Nothing is wrong -- the weekly reminder is unconditional and fires on a fixed schedule regardless of recent activity.",
     "It's just the normal, unconditional weekly reminder", "You must have missed logging your last check-in"),
    ("Can you close out your own target as \"achieved\" from your Performance page?",
     "No -- closing a target is your manager's/Sam's action from a different, owner-level view, not something staff do themselves.",
     "No -- that's your manager's or Sam's action", "Yes -- pick a reason and close it yourself"),
]


class Command(BaseCommand):
    help = (
        "Seeds the standalone 'Using Your Performance Page' staff-wide course (is_staff_training=True, "
        "is_compulsory_staff_training=True, no required_group -- open to any staff account). 3 short "
        "modules on the real /my-performance check-in flow, grounded in facts confirmed by the CRM "
        "session, deliberately NOT describing target creation/closing since that's an owner-only action "
        "staff don't have. Enrolls the user matching --email if given and found."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--email", default="omalesamuel4god@gmail.com",
            help="Email of a User to enroll in the course once seeded.",
        )
        parser.add_argument(
            "--sync-content", action="store_true",
            help="If the course already exists, delete and rebuild its modules/lessons/final quiz to "
                 "match MODULES/FINAL_EXAM_QUESTIONS in this file.",
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
                organization=org, programme=programme, slug="using-your-performance-page",
                defaults={
                    "title": "Using Your Performance Page",
                    "subtitle": "Checking in on your targets — and what's actually the owner's job, not yours.",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 0.5,
                    "is_staff_training": True,
                    "is_compulsory_staff_training": True,
                    "review_status": Course.ReviewStatus.APPROVED,
                    "is_published": True,
                    "meta_description": "Internal training on the staff-facing Performance check-in page.",
                },
            )

            if not created and not options["sync_content"]:
                self.stdout.write(self.style.WARNING(
                    f"{course.title} already exists — leaving content as-is (pass --sync-content to rebuild)."
                ))
            else:
                if not created:
                    course.modules.all().delete()
                    old_quizzes = list(course.quizzes.filter(scope="FINAL").select_related("bank"))
                    old_banks = [q.bank for q in old_quizzes]
                    for q in old_quizzes:
                        q.delete()
                    for b in old_banks:
                        b.delete()
                    self.stdout.write(self.style.WARNING(f"Rebuilding content for existing course: {course}"))
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
                    organization=org, name="Using Your Performance Page — Final Check",
                    description="Covers all modules — must be passed to complete onboarding.",
                )
                for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                    q = Question.objects.create(
                        bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                        difficulty=Question.Difficulty.EASY,
                    )
                    Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                    Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
                Quiz.objects.create(
                    scope=Quiz.Scope.FINAL, course=course, title="Using Your Performance Page — Final Check",
                    instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course.",
                    bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                    max_attempts=0, time_limit_minutes=0,
                )
                self.stdout.write(self.style.SUCCESS("Created the final check."))

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
