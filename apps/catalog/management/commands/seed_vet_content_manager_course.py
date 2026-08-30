from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# Role-specific staff-training course for the new Xpress Vet
# Marketplace Content Manager (Awhobiwom Betiang) — full editorial
# ownership of the Vet Marketplace blog, a role on a DIFFERENT
# product/codebase from the Academy, delivered here anyway per the
# established "course delivery lives in the Academy" pattern (same as
# the Ajo Manager Training course).
#
# is_staff_training=True (Enrollment-gated, no is_staff/admin login
# needed) + is_compulsory_staff_training=True, scoped via
# required_group to "Vet Content Manager" only — see
# apps.catalog.models.Course.required_group. This role needs no
# Django admin permissions at all (her real access grant lives on the
# Vet Marketplace side, module-scoped to ["blog"]) — the Group here
# exists purely as the training-scope tag, same pattern as "Instructor"
# and "Ajo Manager".
#
# Content is grounded ONLY in real facts relayed by vetfresh-1a (the
# Vet Marketplace session), sourced directly from their code, not
# secondhand — deliberately does NOT invent a brand-voice guide (none
# exists) or describe access she doesn't actually have (the "Promote"
# email-blast feature — explicitly NOT granted to this role, a
# separate trust category confirmed with Sam). Same "say what's thin
# or absent honestly" discipline as every other course this project.

MODULES = [
    ("Welcome — Your Role and What You Own",
     """<h2>Full editorial ownership</h2>
<p>You own the Xpress Vet Marketplace blog end to end — content strategy, writing, and publishing. Unlike some other content roles at XDDS, your own posts do not need anyone else's approval before they go live. That's a real, deliberate trust the company is placing in you, not an oversight — treat "publish" as a real, final action every time, not a draft step.</p>
<h2>What this course covers</h2>
<p>This course covers exactly the real tools you'll use — the actual editor, the actual publish workflow, and (just as importantly) what you deliberately do NOT have access to and why. Nothing here is generic content-marketing advice; it's grounded in the real Vet Marketplace admin as it exists today.</p>"""),
    ("The Real Editorial Workflow",
     """<h2>Starting a new post</h2>
<p>In the Vet Marketplace admin dashboard, open the <strong>Blog</strong> tab and choose <strong>+ New Post</strong>. You'll fill in:</p>
<ul>
<li><strong>Title</strong> — this auto-generates a URL slug as you type. You can edit the slug directly if you want something different from the auto-generated one.</li>
<li><strong>Excerpt</strong> — a short teaser, maximum 300 characters. This does double duty: it's what shows on the post list, AND it's the copy that appears in any promotional email about the post. Write it to actually sell the piece, not just summarize it.</li>
<li><strong>Cover image</strong> — one image per post, plain file upload to Cloudinary, 5MB limit. There's no cropping or resizing tool built in — whatever you upload is used exactly as-is, so get the sizing right before you upload (more on this in the Media module).</li>
<li><strong>Tags</strong> — free-text, comma-separated. There's no fixed category list or hierarchy to follow — you decide what tags make sense.</li>
<li><strong>Author</strong> — defaults to "Xpress Vet Team," but you can edit it per post if that's ever useful.</li>
</ul>
<h2>Writing the body</h2>
<p>The post body is written in <strong>Markdown</strong> in a large text box. There's a live "Preview →" toggle so you can check how it'll actually render before saving — use it before every publish, not just occasionally.</p>"""),
    ("Publishing and Managing Posts",
     """<h2>Draft by default</h2>
<p>A new post saves as a draft by default. If you want it live immediately instead, there's a "Publish immediately" checkbox right on the editor — check it deliberately, not by habit.</p>
<h2>No second approval, once you publish</h2>
<p>The moment a post is published — whether at creation or later — it's immediately live on the app and web. There is no extra step and no second approval gate. That's the real weight of the "full editorial ownership" mentioned in Module 1: once you hit publish, it's live, full stop.</p>
<h2>Managing an existing post</h2>
<p><strong>Edit</strong> reopens the same editor you used to create it. <strong>Publish/Unpublish</strong> is a separate button directly on the post's row in the list — not bundled into the edit screen, so you don't need to open a post just to take it down or bring it back. <strong>Delete</strong> is permanent — there's no recovering a deleted post, so use it deliberately.</p>"""),
    ("What You Don't Have Access To — and Why",
     """<h2>The "Send Email" action exists — you don't have it</h2>
<p>There's a real per-post "Send Email" feature in the Vet Marketplace admin — a branded teaser email (cover image, title, excerpt, a "Read full article" button, not the full post content) that can go out to a person, a segment, or everyone. As currently scoped, <strong>you will not have access to this at all</strong>.</p>
<h2>Why, specifically</h2>
<p>This isn't an oversight or a smaller version of your role — it's a deliberate boundary. Publishing a blog post and sending a real marketing/customer email are treated as two different trust categories: you have full, unsupervised rights over the first, and none over the second, which is gated behind a separate permission module. This was confirmed directly with Sam as the intended design, not a temporary restriction.</p>
<h2>What this means day to day</h2>
<p>Don't build your workflow around eventually using Send Email, and don't go looking for it in the admin — it's not part of your toolkit right now. If that ever changes, you'll be told directly and this module will be updated to match — don't assume it's changed on your own.</p>"""),
    ("Media — What's Actually Supported",
     """<h2>One cover image, uploaded directly</h2>
<p>The only image with a real upload button is the single cover image per post, described in Module 2. There's no cropping or dimension enforcement anywhere in the system — whatever you upload is used exactly as uploaded. A sensible practice (not a system requirement) is to use a landscape image around 1200px wide for covers, so it displays cleanly without you needing to guess.</p>
<h2>Images inside the post body</h2>
<p>There's no inline "upload an image into the article" button. If you want an image inside the body text itself, you use Markdown image syntax — <code>![alt text](image-url)</code> — but the URL has to point to an image that's already hosted somewhere (e.g. already uploaded as a cover image elsewhere, or hosted externally). The editor itself doesn't give you a way to upload a body image directly.</p>"""),
    ("Brand Voice, and Keeping Your Account Secure",
     """<h2>An honest note on brand voice</h2>
<p>There is currently no documented brand-voice or style guide for the Vet Marketplace blog — formal or informal. If a written guide is something you'd find useful, that's genuinely a gap to raise with Sam directly rather than something this course can hand you, since nothing like it exists yet to draw from.</p>
<h2>Two-factor authentication</h2>
<p>Real two-factor authentication (TOTP — the same kind of 6-digit code app used for banking apps, Google Authenticator, Authy) is available on your account here. It's opt-in, not forced, but strongly worth turning on given the level of unsupervised publish access this role carries. Set it up any time from the "Security" link in the site navigation once you're logged in — it walks you through scanning a QR code and saving one-time backup codes.</p>
<h2>Why access is scoped the way it is, generally</h2>
<p>Across every platform in the company, access is granted based on what a role actually needs to do its job — not given broadly "just in case." Your own access here reflects exactly that: full rights over the one thing your role is actually about (publishing content), and nothing beyond it. If you ever notice you have access to something that doesn't seem related to your role, that's worth flagging, not treating as a convenient bonus.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("Does one of your own blog posts need anyone else's approval before it goes live?",
     "No — you have full editorial ownership; publishing is a real, final action, not a draft step awaiting review.",
     "No — you can publish directly", "Yes — every post needs Sam's sign-off first"),
    ("What is the Excerpt field actually used for?",
     "It shows on the post list AND is the exact copy used in any promotional email about the post — it needs to sell the piece.",
     "It shows on the post list and doubles as the promotional-email copy",
     "It's an internal note only visible to you"),
    ("Do you currently have access to the \"Send Email\" (Promote) feature?",
     "No — it's gated behind a separate permission module you don't have; a deliberate different trust category from publishing.",
     "No — that's a deliberate boundary, not an oversight", "Yes — it's part of your normal publishing toolkit"),
    ("How do you add an image inside a post's body text (not the cover)?",
     "There's no body-image upload button — Markdown image syntax against an already-hosted URL is the only way.",
     "Markdown syntax pointing to an already-hosted image URL",
     "The same upload button used for the cover image"),
    ("Is there a documented brand-voice/style guide for the blog today?",
     "No — none exists yet, formal or informal; worth raising with Sam directly if you'd find one useful.",
     "No — none exists yet", "Yes — it's linked in the editor"),
]


class Command(BaseCommand):
    help = (
        "Seeds the 'Vet Marketplace Content Manager Training' staff-training course "
        "(is_staff_training=True, required_group='Vet Content Manager') — 6 modules on the "
        "real blog editor workflow, the explicit Send-Email access boundary, media limits, "
        "and security practice. Enrolls the user matching --email if given and found, and "
        "adds them to the Vet Content Manager Group. Safe to re-run."
    )

    def add_arguments(self, parser):
        # Defaults to Dr. Omale's own email — standing policy: as team
        # lead, he's auto-enrolled in every staff-training course by
        # default. Pass --email explicitly to enroll someone else
        # instead (e.g. the actual Content Manager hire).
        parser.add_argument(
            "--email", default="omalesamuel4god@gmail.com",
            help="Email of a User to enroll in the course once seeded.",
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

        vet_content_group, _ = Group.objects.get_or_create(name="Vet Content Manager")

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="vet-content-manager-training",
                defaults={
                    "title": "Vet Marketplace Content Manager Training",
                    "subtitle": "The real blog editor, what you own, and what you deliberately don't have access to.",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.0,
                    "is_staff_training": True,
                    "is_compulsory_staff_training": True,
                    "required_group": vet_content_group,
                    "review_status": Course.ReviewStatus.APPROVED,
                    "is_published": True,
                    "meta_description": "Internal training for the Xpress Vet Marketplace blog's Content Manager.",
                },
            )

            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                if course.required_group_id != vet_content_group.id:
                    course.required_group = vet_content_group
                    course.save(update_fields=["required_group"])
                    self.stdout.write(self.style.SUCCESS("  Updated required_group to Vet Content Manager."))
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
                    organization=org, name="Vet Content Manager Training — Final Check",
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
                    scope=Quiz.Scope.FINAL, course=course, title="Vet Content Manager Training — Final Check",
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
                user.groups.add(vet_content_group)
                enrollment, enrolled_now = Enrollment.objects.get_or_create(user=user, course=course)
                if enrolled_now:
                    from apps.accounts.signal_receivers import _send_welcome_to_training_email
                    _send_welcome_to_training_email(user, course)
                    self.stdout.write(self.style.SUCCESS(f"Added {email} to Vet Content Manager, enrolled in {course.title}, and sent the welcome email."))
                else:
                    self.stdout.write(self.style.WARNING(f"{email} was already enrolled."))

        self.stdout.write(self.style.SUCCESS("Done — course is published (is_staff_training=True, hidden from the public catalog)."))
