from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# Role-specific staff-training course for Xpress Digital Academy's
# telecaller role (first hire: Oshunbajo Oluwaseun Blessing), built in
# response to a request relayed by the coordinating session on Sam's
# behalf.
#
# Same pattern as seed_vet_content_manager_course.py: is_staff_training
# =True (Enrollment-gated, no admin login needed), scoped via
# required_group to "Telecaller" only.
#
# Grounded ONLY in what this codebase can actually verify:
#   - "What Xpress Digital sells" is condensed from the existing
#     'What We Sell' staff-training lesson, not invented.
#   - "Where leads come from" is grounded in two real, verified
#     sources: apps.payments.management.commands.report_top_leads's
#     own three signal tiers (abandoned/pending checkout, diagnostic
#     attempts, engagement.Lead site signups), and the real
#     /internal/call-candidates/ endpoint (apps.enrollment.views) that
#     feeds enrolled-learner check-in candidates to the external CRM.
#   - "Escalate vs close it yourself" is grounded in real, documented
#     platform rules: refunds are manual-only through Sam
#     (ARCHITECTURE.md / apps.payments.services.refund_payment never
#     calls Paystack's refund API), and institutional licensing is a
#     separate product surface (apps.licensing) from individual course
#     sales.
#
# Module 7 (Call Assignments / Call Logs / CRM login) was originally
# an honest stub -- that CRM tool isn't part of this codebase. It's
# now real, grounded content, sourced directly from the CRM session
# (xpress-digital-and-data-solutions-3a), which confirmed it has read
# access to that repo and cited real file paths (CallAssignment.js,
# CallLog.js, StaffAccount.js, MyPerformance.jsx) and exact field/
# dropdown values -- relayed secondhand here, same as every other
# fact in this file, not independently verified by this codebase.

MODULES = [
    ("Welcome — What This Role Actually Covers",
     """<h2>Your job, in one sentence</h2>
<p>You call real people who have already shown some interest in Xpress Digital Academy — someone who started paying and stopped, someone who took a free diagnostic test, someone who left an email — and help them either finish enrolling or tell you honestly they're not interested. Both outcomes are useful to the company; only one of them requires you to be persuasive.</p>
<h2>What this course covers</h2>
<p>This course covers: what the company actually sells (so you can answer questions accurately), exactly where the people on your call list come from and why that matters, how to log every call outcome honestly, how to handle the objections you'll actually hear, a clear line for when to close something yourself versus hand it to Sam, and — in Module 7 — the real Call Assignments and Call Logs screens you'll actually use, plus your first CRM login.</p>
<h2>One real company-wide commitment that applies directly to you</h2>
<p>From the company's own onboarding material: <em>"I will update the CRM immediately — stale data costs the whole company."</em> That's not generic advice for you specifically — it's a company-wide commitment every hire agrees to, and your role is one of the places it matters most directly: a call you don't log accurately is worse than a call that never happened, because someone else may act on the stale information.</p>"""),
    ("What Xpress Digital & Data Solutions Actually Sells",
     """<h2>The core agency business</h2>
<p>XDDS's core agency work covers five real pillars: <strong>Custom Development & Integration</strong>, <strong>Cloud Services & Infrastructure</strong>, <strong>AI & Blockchain</strong> work, <strong>Digital Presence & SEO</strong>, and <strong>Data Strategy & Synchronization</strong>. You won't be selling these directly in this role, but a lead may ask "what does this company even do?" — now you can answer accurately instead of guessing.</p>
<h2>The product family — and where you actually work</h2>
<p>Beyond agency work, XDDS owns three products directly: <strong>Xpress Ajo</strong> (an early-stage group-savings fintech app), <strong>Xpress Vet Marketplace</strong> (an early-stage veterinary/agricultural compliance product), and <strong>Xpress Digital Academy</strong> — the real, live, operating platform you're calling leads for. Academy sells published courses (veterinary continuing education, business, digital skills, AI skills, exam prep, and more), each with real quizzes, a final assessment, and a verifiable PDF certificate on completion.</p>
<h2>One distinction worth getting right on a call</h2>
<p>Some projects in the company's portfolio were built <em>for</em> outside clients and are owned by that client, not by XDDS. If a lead ever references something like that, don't describe it as something Xpress itself runs — that's a real distinction, not a technicality, and getting it wrong on a call is an easy way to sound less credible than you are.</p>
<h2>Full detail elsewhere</h2>
<p>This is a condensed version for call purposes. The full "What We Sell" staff-training course covers this in more depth if you want it.</p>"""),
    ("Where Your Leads and Call Candidates Come From",
     """<h2>Two genuinely different kinds of person on your list</h2>
<p>Not every name you're given is the same kind of lead, and treating them the same wastes the call. There are two real sources, and knowing which one you're looking at should change how you open the conversation.</p>
<h2>Pre-purchase interest signals — someone who hasn't enrolled yet</h2>
<p>Ranked by how strong the signal actually is:</p>
<ul>
<li><strong>Abandoned or pending checkout</strong> — the strongest signal there is. This person clicked "Pay" for a specific course and didn't finish. They already decided to buy; something (a payment hiccup, a distraction, cold feet at the price) interrupted them. Open with the specific course they were buying, not a generic pitch.</li>
<li><strong>Diagnostic test takers</strong> — someone took a free practice test (WAEC, JAMB, Civil Service, etc.) and got a real score. A low score is a real, felt gap the paid course closes — lead with their actual result, not a sales script. A high score is still useful: they're engaged enough to finish a 20-question test, which is a real signal even without a knowledge gap to point at.</li>
<li><strong>Site leads</strong> — someone left only an email via a footer or catalog signup. The weakest signal of the three — real interest, but no specific course or felt gap to anchor the call on yet. Expect more of these calls to end in "not right now" than the other two categories, and that's a normal, expected outcome, not a failure on your part.</li>
</ul>
<h2>Enrolled-learner check-in candidates</h2>
<p>Separately, the platform can also surface people who are <em>already enrolled</em> but flagged for a check-in call — someone who stalled partway through a course, for example. These aren't sales calls in the usual sense; they're retention calls. The tone is different: you're checking in on someone who already paid, not persuading someone who hasn't.</p>
<h2>Why this distinction matters for logging (see Module 4)</h2>
<p>Mislabeling an abandoned-checkout lead as a cold site lead (or the reverse) in your notes makes the data actively misleading for whoever looks at it next — log which category a contact actually was, not just the outcome of your call.</p>"""),
    ("Logging Call Outcomes Honestly",
     """<h2>The one rule that matters most</h2>
<p>Log the outcome immediately after the call, not batched at the end of the day from memory. Memory smooths over the awkward parts — the actual objection someone raised, the exact reason they said no — and those specifics are exactly what make a log entry useful to anyone who reads it later.</p>
<h2>A "no" is a real, useful outcome — log it as one</h2>
<p>There's no incentive here to make your numbers look better by marking a clear "not interested" as "follow up later." A dishonest log costs the company a wasted second call and costs you credibility the first time someone checks. A clean, honest "not interested — cited price" is more valuable data than a vague "will call back" that both of you know isn't true.</p>
<h2>Never mark someone "converted" who hasn't actually paid</h2>
<p>Interest is not a sale. Someone saying "okay, I'll enroll" on the phone is a good sign, but the only thing that actually confirms a conversion is the payment itself completing — grant_access() firing, the enrollment existing. Log real interest as real interest, and let the payment status speak for the actual outcome. Overstating a call's result is the kind of small dishonesty that compounds into leadership trusting the data less over time.</p>
<h2>This isn't just advice — it's actually checked</h2>
<p>A "Converted" outcome in Call Logs doesn't count as fully real the moment you log it — it sits as <strong>unverified</strong> until someone other than you confirms it, and can be marked <strong>disputed</strong> if it doesn't hold up. There's no upside to inflating a conversion here; it just gets caught and disputed, which costs you more credibility than an honest "follow-up needed" ever would.</p>
<h2>Record the actual objection, in their words where you can</h2>
<p>"Price" and "price — thought it would include one-on-one tutoring, ₦5,000 felt high just for self-paced videos" are very different notes. The second one is something the business can actually act on (maybe that expectation needs clarifying on the sales page); the first one is nearly useless six months from now.</p>"""),
    ("Handling Objections",
     """<h2>"It's too expensive"</h2>
<p>Most Academy courses are priced between ₦2,000 and ₦20,000 — real money, and a legitimate concern, not something to argue past. Anchor on real value already delivered for free: the diagnostic they took (if that's how they got here) already showed them something real about their own gap, at zero cost. The paid course is the next step past that, not a leap of faith. Don't discount informally on a call — that's not something you're authorized to offer, and it undermines the actual coupon system the business uses deliberately.</p>
<h2>"Is this legit? / I don't want to get scammed"</h2>
<p>A completely reasonable question in Nigeria's online-course market, and worth answering directly rather than brushing off. Real facts you can point to: verifiable certificates (a real serial number, checkable at a public URL, showing name/course/date, or a clear "not found"/"revoked" state — never a vague broken page), payment through Paystack (not a personal bank transfer to an individual), and — if it's true for the course in question — a real refund path that goes through a person (Sam), not a black hole.</p>
<h2>"Let me think about it"</h2>
<p>Don't push past this — pushing here reads as exactly the kind of pressure that makes "is this a scam?" feel more justified, not less. A genuine "let me think" is a fine outcome to log as-is. If you want a soft next step, offering to note their real question or hesitation for a follow-up (with their permission) is fine; a hard-sell close is not.</p>
<h2>"I don't have time to study"</h2>
<p>Real and common for working adults. Point to what's actually true of the platform: self-paced, lifetime or long-term access on most courses (not a ticking clock), progress saved automatically. Don't promise a time commitment you don't actually know — "it typically takes people X hours" is only honest if you actually know that number for the specific course; if you don't, say so rather than invent a figure.</p>"""),
    ("When to Escalate vs Close It Yourself",
     """<h2>You can close it yourself when...</h2>
<p>The person is ready to enroll in a specific individual course at its listed price — send them the checkout link, done. This is the large majority of positive outcomes on your calls, and it's entirely within what you're expected to handle directly.</p>
<h2>Always escalate to Sam: refunds</h2>
<p>Refunds are <strong>manual-only, always</strong>, by real platform design — the system flips a payment's status to REFUNDED, but nothing in the codebase ever calls Paystack's actual refund API automatically. If someone asks about a refund, that's a "let me get you to the right person," not something you resolve or promise on the call.</p>
<h2>Always escalate: bulk or institutional interest</h2>
<p>If a school, company, or organization asks about licensing courses for many people at once rather than one individual enrolling, that's a completely different product surface (institutional licensing) with its own pricing and process — not something to quote a per-course price for. Pass it on rather than improvise an answer.</p>
<h2>Escalate: anything about a technical problem or a payment that already went wrong</h2>
<p>"I paid and didn't get access" or "the site gave me an error" are real operational issues, not sales conversations — get the person's email and what happened, and hand it off rather than trying to diagnose it yourself on the call.</p>
<h2>The judgment call: genuine anger or a serious complaint</h2>
<p>If someone is seriously unhappy — not just objecting to price, but upset about something that already happened — that's worth a human above you knowing about directly, even if you could technically smooth it over yourself on the call. When in doubt, escalate rather than quietly resolve; a complaint that reaches Sam late is worse than one that reaches him a little early.</p>"""),
    ("Using Call Assignments & Call Logs in the CRM",
     """<h2>Your first login is a separate system from Academy</h2>
<p>The CRM you'll work in day to day is a completely different system from the Xpress Digital Academy platform this training runs on — different login, different backend. You'll be given an email and a <strong>temporary password</strong>. The first time you log in, you're prompted right there on the same login page to set a real password before you can go any further — it's not a separate step you do later. Two-factor authentication (an authenticator app, same idea as Google Authenticator) is available afterward from your profile if you want the extra security, but it's optional, not forced.</p>
<h2>"My Assignments" — how a call brief actually works</h2>
<p>When Sam or a manager assigns you a call, it shows up as an assignment with a status badge: <strong>pending → claimed → completed</strong> (or <strong>cancelled</strong>, if it's called off). Each assignment is a real brief, not just a name and number — it includes the contact's name, phone, and company; which channel to use (phone, WhatsApp, Facebook/Instagram DM, email, walk-in, or other); <strong>why this call is happening</strong>; background context on the person; specific talking points; the actual goal of the conversation; any tools or materials you'll need; what a good outcome looks like; and a deadline. Read the whole brief before you dial — it exists so you're never calling someone cold with no context. If the assignment belongs to a portfolio with a manager attached, that manager is automatically copied on the brief and notified once you mark it complete.</p>
<h2>Call Logs — the exact fields</h2>
<p>Every call gets logged, whether it's against an assignment or a call you made on your own initiative. A log records: portfolio, channel, the contact's name/phone/company, the <strong>outcome</strong>, call duration in minutes, and notes. The outcome is a fixed list — pick the one that's actually true, don't approximate:</p>
<ul>
<li>Connected</li>
<li>Left voicemail</li>
<li>No answer</li>
<li>Wrong number</li>
<li>Call-back requested</li>
<li>Not interested</li>
<li>Converted</li>
<li>Follow-up needed</li>
</ul>
<p>If the call needs a follow-up, set a <strong>next-action date and note</strong> right there in the same log entry — that's what actually reminds you (and anyone else who might pick it up) later. A follow-up you plan to "just remember" is exactly the kind of stale data Module 4 already covered.</p>
<h2>One thing worth re-reading from Module 4</h2>
<p>A "Converted" outcome here isn't final the moment you log it — it stays unverified until someone else confirms it, and can be marked disputed. Log it because it's true, not because it looks good on your own numbers.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("Which lead type has the strongest signal that someone was about to buy?",
     "Abandoned or pending checkout — they already clicked Pay on a specific course and didn't finish.",
     "Abandoned or pending checkout", "A generic footer email signup"),
    ("If someone says \"okay I'll enroll\" on the phone but hasn't paid yet, how should you log it?",
     "As real interest, not as a conversion -- only a completed payment actually confirms a conversion.",
     "As interest shown, not yet converted", "As converted, since they verbally agreed"),
    ("A lead asks for a refund on a course they already paid for. What do you do?",
     "Escalate to Sam -- refunds are manual-only by design, never something to promise or resolve on the call.",
     "Tell them you'll escalate it to Sam", "Confirm the refund yourself to close the call quickly"),
    ("Does logging a call as \"Converted\" in Call Logs immediately count it as a real conversion?",
     "No -- it stays unverified until someone other than you confirms it, and can be marked disputed.",
     "No -- it needs verification from someone else first", "Yes -- logging it as Converted is what makes it official"),
    ("On your very first CRM login with a temporary password, what happens?",
     "You're prompted right there on the login page to set a real password before continuing -- not a separate later step.",
     "You're prompted immediately to set a real password", "You log in normally and change your password whenever you feel like it"),
    ("A lead pushes back with \"is this legit?\" What's the strongest honest answer?",
     "Point to real, verifiable facts: certificate verification, Paystack (not personal transfer), and the real refund path.",
     "Point to verifiable certificates and real Paystack payment", "Insist it's definitely not a scam and move on"),
    ("Why does it matter whether you log a call outcome immediately vs. at the end of the day?",
     "Immediate logging preserves the real specifics (the actual objection, the actual course) that memory smooths over later.",
     "Immediate logging keeps the real details accurate", "It doesn't matter, as long as it's logged eventually"),
    ("What should you do if you don't actually know how long a course typically takes someone to finish?",
     "Say so honestly, rather than inventing a time estimate to sound more confident on the call.",
     "Say you don't know rather than guess a number", "Give a confident estimate anyway to keep the call moving"),
]


class Command(BaseCommand):
    help = (
        "Seeds the 'Telecaller Onboarding' staff-training course (is_staff_training=True, "
        "required_group='Telecaller') -- 7 modules covering what the company sells, where "
        "leads/call-candidates come from, honest call logging, objection handling, and "
        "escalation judgment. Module 7 is a deliberate, honestly-labeled stub -- the actual "
        "CRM Call Assignments/Call Logs screens aren't part of this codebase and aren't "
        "guessed at. Enrolls the user matching --email if given and found."
    )

    def add_arguments(self, parser):
        # Defaults to Sam's own email -- same standing policy as
        # seed_vet_content_manager_course.py: as team lead, he's
        # auto-enrolled in every staff-training course by default.
        # Pass --email explicitly once the actual telecaller has an
        # account (e.g. --email her real address).
        parser.add_argument(
            "--email", default="omalesamuel4god@gmail.com",
            help="Email of a User to enroll in the course once seeded.",
        )
        parser.add_argument(
            "--sync-content", action="store_true",
            help="If the course already exists, delete and rebuild its modules/lessons/final quiz to "
                 "match MODULES/FINAL_EXAM_QUESTIONS in this file. Safe as long as no real learner has "
                 "started it yet -- progress/attempts would be lost otherwise.",
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
                organization=org, programme=programme, slug="telecaller-onboarding",
                defaults={
                    "title": "Telecaller Onboarding",
                    "subtitle": "What we sell, where your leads come from, honest logging, objections, and when to escalate.",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.FREE,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_staff_training": True,
                    "is_compulsory_staff_training": True,
                    "required_group": telecaller_group,
                    "review_status": Course.ReviewStatus.APPROVED,
                    "is_published": True,
                    "meta_description": "Internal training for Xpress Digital Academy telecallers.",
                },
            )

            if not created and not options["sync_content"]:
                self.stdout.write(self.style.WARNING(
                    f"{course.title} already exists — leaving content as-is (pass --sync-content to rebuild "
                    "modules/lessons/quiz to match this file, e.g. after editing MODULES)."
                ))
                if course.required_group_id != telecaller_group.id:
                    course.required_group = telecaller_group
                    course.save(update_fields=["required_group"])
                    self.stdout.write(self.style.SUCCESS("  Updated required_group to Telecaller."))
            else:
                if not created:
                    course.modules.all().delete()
                    old_quizzes = list(course.quizzes.filter(scope="FINAL").select_related("bank"))
                    old_banks = [q.bank for q in old_quizzes]
                    for q in old_quizzes:
                        q.delete()
                    for b in old_banks:
                        b.delete()  # cascades to its Questions/Choices too
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
                    organization=org, name="Telecaller Onboarding — Final Check",
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
                    scope=Quiz.Scope.FINAL, course=course, title="Telecaller Onboarding — Final Check",
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
