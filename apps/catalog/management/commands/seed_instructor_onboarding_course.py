from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# Second role-specific staff-training course, after Manager Onboarding
# — is_staff_training=True (Enrollment-gated, no is_staff/admin login
# needed), is_compulsory_staff_training=True, scoped via
# required_group to the "Instructor" Group only (see
# apps.catalog.models.Course.required_group — this is exactly the gap
# that field was added to close: without it, adding this course would
# have force-enrolled every existing staff member, Course Managers
# included, into instructor-specific training).
#
# Content is grounded in the real /teach/ portal code
# (apps.instructors.views/services/models) — the actual workflow an
# internal Instructor uses, same discipline as Manager Onboarding's
# content being the real admin, not generic filler.

MODULES = [
    ("Welcome — Becoming a Real Instructor Here",
     """<h2>You're a staff Instructor, not a public applicant</h2>
<p>You report to the Course Manager for Xpress Digital Academy. But the platform itself doesn't have a separate "staff instructor" login — you use the exact same instructor account and /teach/ portal that any verified marketplace instructor uses. There's no special admin access to learn here, and none is needed for this role.</p>
<h2>How your instructor account gets set up</h2>
<p>An Instructor record is created the moment someone applies at /teach/apply/ while logged in — it starts with verification_status=Unverified. You cannot publish anything, and your courses won't earn, until <em>both</em> of two things are true: your verification_status is set to Verified by staff review, and your agreement_signed_at is recorded. Both, not either — that's enforced directly on the Instructor record, not a soft rule.</p>
<h2>Why this course exists</h2>
<p>Everything below is the real /teach/ workflow, not a simplified version — the same dashboard, the same submit-for-review gate, the same rules that apply to any instructor selling on this platform. Finishing it and passing the final check is what confirms you're ready to build and publish real courses here.</p>"""),
    ("Your Dashboard and Building a Course",
     """<h2>Where your work lives</h2>
<p>Everything instructor-facing sits under /teach/ — Dashboard (balance, course count, this month's enrollments, completion rate, any pending payout), Courses (your own course list), Earnings, and Marketing. All of it requires being logged in with a verified Instructor profile; there's no separate staff shortcut into it.</p>
<h2>Editing a course</h2>
<p>Open a course from /teach/courses/ to edit its metadata. One real rule to know before you're surprised by it: once a course's review_status is Submitted or In review, editing is locked — the form won't save changes until a reviewer has actually acted on it. Get your content right before you submit, not after.</p>
<h2>Submitting for review</h2>
<p>A course can only be submitted for review while its review_status is Draft or Changes requested — not from any other state. Submitting creates a new, permanent CourseReview round (rounds are append-only — a second round never overwrites the first) and flips review_status to Submitted. From there, a reviewer decides Approved, Changes requested (unlocks editing again, with their notes), or Rejected (back to Draft, not deleted).</p>"""),
    ("Working With Learners — What You Can and Can't Do",
     """<h2>Learner names and progress — never contact details</h2>
<p>Your Course learners page (/teach/courses/&lt;slug&gt;/learners/) shows you each enrolled learner's name, status, and progress percentage. It deliberately never shows their email or phone number — that's not an oversight, it's a firm anti-poaching rule: an instructor should never be able to pull a learner's contact details straight out of the platform and reach them directly.</p>
<h2>How you actually talk to a learner</h2>
<p>All learner-instructor communication goes through the platform's own messaging, logged on both sides — never a private channel like WhatsApp or personal email, even if a learner asks for it. That's not about mistrust; it's a real, enforced policy, and it protects you as much as the learner (a documented conversation instead of a private one you can't point back to).</p>
<h2>Course ratings</h2>
<p>Learners who are enrolled and past 50% progress can rate and review your course. You may respond publicly to a review once — you can't edit or delete a learner's review yourself. If a review is genuinely abusive rather than just critical, that's escalated to a Course Manager to remove, not something you action directly.</p>"""),
    ("Earnings, Attribution, and Marketing Links",
     """<h2>How a sale becomes your earning</h2>
<p>When someone buys one of your courses, the system automatically writes the accounting for it — the full sale amount, the platform's fee, and your actual earning — onto your ledger. Your balance shown on the dashboard is always computed live from that ledger, never a stored number that can drift out of sync.</p>
<h2>Two earning rates — which one applies depends on attribution</h2>
<p>You have two different rates: one for a sale that came through your own referral link (own_traffic_rate), and a lower one for a sale that happened to land on your course without your link (platform_traffic_rate). Attribution is last-touch: if someone used your ?ref=&lt;your code&gt; link within the last 30 days before buying, it's yours at the higher rate.</p>
<h2>Your marketing link</h2>
<p>Your Marketing page (/teach/marketing/) lists a ready-made link for each of your published courses, already carrying your referral code. That's the actual link to share — sharing a course's plain URL instead of your ?ref= link means a real sale still happens, just at the lower platform-traffic rate instead of your own.</p>
<h2>Getting paid</h2>
<p>Payouts are manual, not automatic: a statement is generated from your ledger for a period, a Course Manager or the account owner reviews it, pays by bank transfer, and marks it sent with a reference. There's no self-serve "withdraw" button — that's a deliberate control, not a missing feature.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("What two things must both be true before you can publish and earn on a course?",
     "verification_status must be Verified AND agreement_signed_at must be set — both, not either.",
     "Verified status AND a signed agreement", "Just being logged in with an Instructor record"),
    ("When is a course locked for editing?",
     "While review_status is Submitted or In review — editing reopens once a reviewer acts.",
     "While it's Submitted or In review", "Only after it's been Approved"),
    ("What does the learners page on your course show you?",
     "Name, status, and progress only — never email or phone, by deliberate anti-poaching rule.",
     "Name, status, and progress percentage only", "Name, email, and phone number"),
    ("How should you communicate with a learner who messages you about your course?",
     "Through the platform's own messaging — logged, never a private channel like WhatsApp.",
     "Through the platform's own messaging, logged", "Wherever is most convenient, including WhatsApp"),
    ("Which rate applies when someone buys your course through your own ?ref= link within 30 days?",
     "That's own_traffic_rate — the higher of your two rates, per the last-touch attribution rule.",
     "Your own_traffic_rate (the higher rate)", "Your platform_traffic_rate (the lower rate)"),
]


class Command(BaseCommand):
    help = (
        "Seeds the 'Instructor Onboarding' staff-training course (is_staff_training=True, "
        "required_group='Instructor') — 4 modules covering the real /teach/ instructor "
        "workflow, plus a short final exam. Enrolls the user matching --email if given and "
        "found, and adds them to the Instructor Group. Safe to re-run."
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

        # See seed_manager_onboarding_course.py's own comment on the
        # same pattern — required_group is what stops this course from
        # force-enrolling every staff member, not just instructors.
        instructor_group, _ = Group.objects.get_or_create(name="Instructor")

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="instructor-onboarding",
                defaults={
                    "title": "Instructor Onboarding",
                    "subtitle": "The real /teach/ workflow — building, submitting, and selling courses here.",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_staff_training": True,
                    "is_compulsory_staff_training": True,
                    "required_group": instructor_group,
                    "review_status": Course.ReviewStatus.APPROVED,
                    "is_published": True,
                    "meta_description": "Internal onboarding for Xpress Digital Academy instructors.",
                },
            )

            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                if course.required_group_id != instructor_group.id:
                    course.required_group = instructor_group
                    course.save(update_fields=["required_group"])
                    self.stdout.write(self.style.SUCCESS("  Updated required_group to Instructor."))
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
                    organization=org, name="Instructor Onboarding — Final Check",
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
                    scope=Quiz.Scope.FINAL, course=course, title="Instructor Onboarding — Final Check",
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
                user.groups.add(instructor_group)
                enrollment, enrolled_now = Enrollment.objects.get_or_create(user=user, course=course)
                if enrolled_now:
                    from apps.accounts.signal_receivers import _send_welcome_to_training_email
                    _send_welcome_to_training_email(user, course)
                    self.stdout.write(self.style.SUCCESS(f"Added {email} to Instructor, enrolled in {course.title}, and sent the welcome email."))
                else:
                    self.stdout.write(self.style.WARNING(f"{email} was already enrolled."))

        self.stdout.write(self.style.SUCCESS("Done — course is published (is_staff_training=True, hidden from the public catalog)."))
