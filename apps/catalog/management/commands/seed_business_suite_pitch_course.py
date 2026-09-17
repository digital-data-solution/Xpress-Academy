from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# Standalone course for telecallers pitching Business Suite (a Vet
# Marketplace product, NOT part of this codebase) to vet leads on
# their call list. Kept separate from Telecaller Onboarding
# deliberately -- pricing/features here belong to a different team and
# can change independently of the core onboarding flow.
#
# Content is relayed content, not verified against Business Suite's
# own code the way this codebase's own facts are (that code isn't
# accessible from here at all) -- drafted by vetfresh-1d (Vet
# Marketplace's own session, the actual product owner) and passed
# along via xpress-digital-and-data-solutions-3a. Sam directed this be
# built as-is. Flagged honestly in Module 1 that pricing/features
# should be reconfirmed with the Vet Marketplace team if this course
# is still in use much later -- exactly the kind of fact that goes
# stale silently if nobody owns keeping it current.

MODULES = [
    ("What Business Suite Actually Is",
     """<h2>Not the listing — the day-to-day toolkit</h2>
<p>Business Suite is a separate add-on from a vet's Xpress Vet Marketplace listing. The listing is about getting found by new customers; Business Suite is about running the clinic day to day once customers are already coming in — inventory tracking, point-of-sale (recording sales), and staff accounts, all in one place.</p>
<h2>The three real features</h2>
<ul>
<li><strong>Self-updating inventory</strong> — stock drops automatically the moment a sale is recorded, with low-stock warnings. No manual stock-taking.</li>
<li><strong>Full audit trail</strong> — every stock change is logged: who made it, when, and the before/after count. A real theft/shrinkage safeguard, not just a nice-to-have.</li>
<li><strong>Staff accounts</strong> — each staff member gets their own login (or a shared-device PIN), and the owner controls exactly what each person can do: sell, view reports, manage inventory, manage other staff.</li>
</ul>
<h2>An honest note on this module</h2>
<p>This content was drafted by the Vet Marketplace team, not verified against their code directly from this course. If you're reading this much later and something here seems off (pricing especially), check with them before repeating it on a call — pricing is exactly the kind of fact that can quietly go stale.</p>"""),
    ("Pricing and How to Pitch It",
     """<h2>The real pricing</h2>
<p>Free up to <strong>15 products and 2 staff seats</strong> — genuinely no cost to start. Paid only beyond that:</p>
<ul>
<li>₦3,500/month</li>
<li>₦9,000/3 months</li>
<li>₦32,000/year</li>
<li>Extra staff seats beyond the free 2: ₦1,500/seat per 30 days</li>
</ul>
<h2>This is now the primary pitch for vet leads — not a side upsell</h2>
<p>Use this framing on every vet lead call, not as an afterthought:</p>
<p><em>"Since you're already running your own practice, there's a free tool in the app to track your inventory and sales, and give any staff their own login — no cost unless you grow past 15 products or 2 staff. Want me to walk you through turning it on?"</em></p>
<h2>Why this framing works</h2>
<p>It's offered as a free tool to try today, not a sales ask — that's deliberate. Genuinely free at the scale most small practices start at removes the price objection entirely for the first call; the paid tiers only become relevant once someone's actually grown into needing them.</p>"""),
    ("Watch the Demo Before Your First Vet Calls",
     """<h2>Real walkthrough, watch it first</h2>
<p>There's a real demo video — "How to Use Business Suite on Xpress Vet" — <a href="https://youtu.be/9XTJuiXcarY">https://youtu.be/9XTJuiXcarY</a>. Watch it before your first batch of vet-lead calls, not after — you should be able to describe what the screen actually looks like when you offer to "walk them through turning it on," not just repeat the feature list from Module 1.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("What does Business Suite actually cover, as opposed to a vet's marketplace listing?",
     "Day-to-day running of the clinic -- inventory, point-of-sale, staff accounts. The listing is about getting found; Business Suite is about running things once customers already come in.",
     "Day-to-day clinic operations (inventory, sales, staff)", "Getting the clinic found by new customers"),
    ("Up to what scale is Business Suite genuinely free?",
     "15 products and 2 staff seats -- no cost at all up to that point.",
     "15 products and 2 staff seats", "5 products and 1 staff seat"),
    ("How should Business Suite be framed on a vet lead call?",
     "As a free tool to try today, not a sales ask -- that removes the price objection on the first call.",
     "As a free tool to try today, not a sales pitch", "As a paid upgrade the practice needs to compete"),
    ("Before your first batch of vet-lead calls, what should you do?",
     "Watch the real demo video first, so you can describe what the screen actually looks like, not just recite features.",
     "Watch the demo video first", "Just read the feature list -- the video is optional"),
]


class Command(BaseCommand):
    help = (
        "Seeds the standalone 'Pitching Business Suite to Vet Leads' course (is_staff_training=True, "
        "required_group='Telecaller') -- 3 short modules on what Business Suite is, real pricing and "
        "the exact pitch framing, and the demo video to watch before vet-lead calls. Content relayed "
        "from the Vet Marketplace team (vetfresh-1d), not independently verified against their code."
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

        telecaller_group, _ = Group.objects.get_or_create(name="Telecaller")

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="pitching-business-suite-to-vet-leads",
                defaults={
                    "title": "Pitching Business Suite to Vet Leads",
                    "subtitle": "What it is, real pricing, the exact pitch framing, and the demo video to watch first.",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 0.5,
                    "is_staff_training": True,
                    "is_compulsory_staff_training": True,
                    "required_group": telecaller_group,
                    "review_status": Course.ReviewStatus.APPROVED,
                    "is_published": True,
                    "meta_description": "Internal training for telecallers pitching Business Suite to vet leads.",
                },
            )

            if not created and not options["sync_content"]:
                self.stdout.write(self.style.WARNING(
                    f"{course.title} already exists — leaving content as-is (pass --sync-content to rebuild)."
                ))
                if course.required_group_id != telecaller_group.id:
                    course.required_group = telecaller_group
                    course.save(update_fields=["required_group"])
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
                    organization=org, name="Pitching Business Suite to Vet Leads — Final Check",
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
                    scope=Quiz.Scope.FINAL, course=course, title="Pitching Business Suite to Vet Leads — Final Check",
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
                user.groups.add(telecaller_group)
                enrollment, enrolled_now = Enrollment.objects.get_or_create(user=user, course=course)
                if enrolled_now:
                    from apps.accounts.signal_receivers import _send_welcome_to_training_email
                    _send_welcome_to_training_email(user, course)
                    self.stdout.write(self.style.SUCCESS(f"Added {email} to Telecaller, enrolled in {course.title}, and sent the welcome email."))
                else:
                    self.stdout.write(self.style.WARNING(f"{email} was already enrolled."))

        self.stdout.write(self.style.SUCCESS("Done — course is published (is_staff_training=True, hidden from the public catalog)."))
