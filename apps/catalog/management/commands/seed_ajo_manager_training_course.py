from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# Role-specific staff-training course for a Xpress Ajo Manager — a
# role on the CRM/HR side (reports to Dr. Omale directly, unrelated to
# the Academy job someone in this role might also hold). Delivered
# here anyway, per the established "course delivery lives in the
# Academy, completions webhook to the CRM/HR side" pattern used for
# every other compulsory staff-training course.
#
# is_staff_training=True (Enrollment-gated, no is_staff/admin login
# needed) + is_compulsory_staff_training=True, scoped via
# required_group to "Ajo Manager" only — see
# apps.catalog.models.Course.required_group.
#
# Content is grounded ONLY in real product facts relayed from the
# xpress-digital-and-data-solutions session that manages Xpress Ajo —
# a real fintech app moving real Naira, not a demo. Deliberately does
# NOT invent contribution schedules, fee structures, or payout
# mechanics beyond what was actually confirmed — same "say what's thin
# honestly rather than fill the gap" discipline as
# seed_general_onboarding_track.py's per-course notes. Module 4 covers
# a live, known bug and is written to be safely updated (not
# re-created) once that session confirms the fix — see
# --unblock-share-feature below.

MODULES = [
    ("What Xpress Ajo Is, and Your Role",
     """<h2>A real product, not a demo</h2>
<p>Xpress Ajo is one of XDDS's own products (as covered in the General Onboarding track's "What We Sell" course) — a group-savings ("ajo"/contribution-circle) fintech app. It is genuinely live and moves real Naira. Treat every account, contribution, and referral you touch in it as real money belonging to a real person, not test data.</p>
<h2>Your role specifically</h2>
<p>As Manager, Xpress Ajo, you report directly to Dr. Omale on this side — this role is separate from any Academy-side reporting line you may also have. Your working knowledge of the actual product (not a generic fintech pitch) is what the rest of this course covers.</p>"""),
    ("Registration and Referral — a Two-Step Flow",
     """<h2>Signing up is its own, plain step</h2>
<p>A new user registers on Xpress Ajo the ordinary way — there's no referral code involved in the signup step itself.</p>
<h2>Applying a referral code is a separate, later step</h2>
<p>A personal referral code is applied <em>after</em> signup, as its own distinct action — not bundled into a single "click this link and you're both signed up and referred" flow. If you're ever explaining this to a user, be precise about that: it's sign up first, then apply a code, as two separate steps, not one.</p>"""),
    ("How Referral Credit Actually Works",
     """<h2>Signing up earns nothing by itself</h2>
<p>Applying someone's referral code after signup does not, on its own, earn that person any credit. Credit only exists once real money has actually moved.</p>
<h2>The real rule: 5% of the first contribution, and only after it happens</h2>
<p>A referral earns a credit equal to 5% of the referred person's <em>first</em> contribution — and only once that contribution has actually been made, not at the point of signup or of applying the code. If someone signs up and applies a code but never actually contributes, no credit is generated. Don't tell a user they've "earned" anything from a referral until their referred person has made a real first contribution.</p>"""),
    ("Known Issue: Don't Recommend \"Just Share Your Code\" Yet",
     """<h2>A real, currently-live bug</h2>
<p>The app's built-in "share my code" feature currently sends a broken download link — a leftover artifact from an unrelated project, not something specific to a particular user's account. This is a known issue on the Xpress Ajo side, already being worked on.</p>
<h2>What that means for you right now</h2>
<p>Until this is fixed, don't tell a user to "just use the share my code button" — it will hand them a broken link. If someone needs to share their referral code today, that has to happen another way (telling someone the code directly, for example) rather than through that in-app feature.</p>
<h2>This will be updated</h2>
<p>This module will be corrected the moment the Xpress Ajo side confirms the fix — check back here rather than assuming it's resolved on your own.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("Is applying a referral code part of the signup step itself?",
     "No — signup is its own plain step; applying a referral code is a separate step that happens after.",
     "No — it's a separate step, applied after signup", "Yes — they happen together in one link"),
    ("When does a referral actually earn credit?",
     "Only once the referred person has made their real first contribution — never just from signing up or applying a code.",
     "Only after the referred person's first real contribution", "As soon as the referred person signs up"),
    ("How much does a referral credit equal?",
     "5% of the referred person's first contribution — not a flat amount, and not a recurring percentage on every contribution.",
     "5% of the referred person's first contribution", "10% of every contribution they ever make"),
    ("Right now, should you tell a user to use the in-app \"share my code\" button?",
     "No — it currently sends a broken download link due to a known, live bug. Share the code another way until it's fixed.",
     "No — it currently sends a broken link", "Yes — it works correctly today"),
]


class Command(BaseCommand):
    help = (
        "Seeds the 'Xpress Ajo Manager Training' staff-training course (is_staff_training=True, "
        "required_group='Ajo Manager') — 4 modules on real product mechanics: the two-step "
        "signup+referral flow, 5%-of-first-contribution referral credit, and the current "
        "'share my code' bug. Enrolls the user matching --email if given and found, and adds "
        "them to the Ajo Manager Group. Safe to re-run."
    )

    def add_arguments(self, parser):
        # Defaults to Dr. Omale's own email — standing policy: as team
        # lead, he's auto-enrolled in every staff-training course by
        # default. Pass --email explicitly to enroll someone else
        # instead (e.g. the actual Ajo Manager hire).
        parser.add_argument(
            "--email", default="omalesamuel4god@gmail.com",
            help="Email of a User to enroll in the course once seeded.",
        )
        parser.add_argument(
            "--unblock-share-feature", action="store_true",
            help="Once the Xpress Ajo side confirms the 'share my code' bug is fixed, pass this "
                 "flag to rewrite Module 4 to say so, rather than leaving the bug-warning text in "
                 "place indefinitely.",
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

        ajo_manager_group, _ = Group.objects.get_or_create(name="Ajo Manager")

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="xpress-ajo-manager-training",
                defaults={
                    "title": "Xpress Ajo Manager Training",
                    "subtitle": "Real product knowledge: registration, referrals, and current known issues.",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 0.75,
                    "is_staff_training": True,
                    "is_compulsory_staff_training": True,
                    "required_group": ajo_manager_group,
                    "review_status": Course.ReviewStatus.APPROVED,
                    "is_published": True,
                    "meta_description": "Internal training for Xpress Ajo Managers.",
                },
            )

            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                if course.required_group_id != ajo_manager_group.id:
                    course.required_group = ajo_manager_group
                    course.save(update_fields=["required_group"])
                    self.stdout.write(self.style.SUCCESS("  Updated required_group to Ajo Manager."))
                if options["unblock_share_feature"]:
                    module4 = course.modules.order_by("order").last()
                    if module4:
                        lesson = module4.lessons.first()
                        if lesson:
                            lesson.body = (
                                "<h2>Fixed</h2>"
                                "<p>The \"share my code\" bug covered in this module has been fixed on the "
                                "Xpress Ajo side. It's now safe to tell users to use the in-app share "
                                "button to share their referral code.</p>"
                            )
                            lesson.save(update_fields=["body"])
                            self.stdout.write(self.style.SUCCESS("  Module 4 updated — bug marked fixed."))
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
                    organization=org, name="Xpress Ajo Manager Training — Final Check",
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
                    scope=Quiz.Scope.FINAL, course=course, title="Xpress Ajo Manager Training — Final Check",
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
                user.groups.add(ajo_manager_group)
                enrollment, enrolled_now = Enrollment.objects.get_or_create(user=user, course=course)
                if enrolled_now:
                    from apps.accounts.signal_receivers import _send_welcome_to_training_email
                    _send_welcome_to_training_email(user, course)
                    self.stdout.write(self.style.SUCCESS(f"Added {email} to Ajo Manager, enrolled in {course.title}, and sent the welcome email."))
                else:
                    self.stdout.write(self.style.WARNING(f"{email} was already enrolled."))

        self.stdout.write(self.style.SUCCESS("Done — course is published (is_staff_training=True, hidden from the public catalog)."))
