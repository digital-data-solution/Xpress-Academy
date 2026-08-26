from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Digital Skills for Business Owners launched Foundation-only. Per
# explicit instruction, every Foundation-only line needs Intermediate
# and Advanced tiers, gated by prerequisite.

INTERMEDIATE_MODULES = [
    ("Building a Real Content System",
     """<h2>From posting to a real system</h2>
<p>Foundation covered batching and calendars; this module covers building an actual repeatable content system — content pillars (2-3 recurring themes you always return to), a real production rhythm, and a way of recycling proven content rather than always creating from zero.</p>
<h2>Content pillars that actually reflect your business</h2>
<p>Pillars built around what your specific customer actually cares about (not generic "tips" content) keep a content system focused and genuinely useful rather than becoming a scattered mix of unrelated posts.</p>
<h2>Repurposing systematically, not occasionally</h2>
<p>A deliberate system — every piece of pillar content becomes a post, a story, a caption variant, a WhatsApp status — multiplies output from the same creation effort, turning Foundation's repurposing idea into an actual habit.</p>
<h2>Reviewing and evolving your content system</h2>
<p>A content system built once and never revisited goes stale — a monthly review of what's actually performing, and adjusting pillars accordingly, keeps the system genuinely alive rather than running on autopilot indefinitely.</p>"""),
    ("Paid Advertising at a Working Level",
     """<h2>Moving past your first test campaign</h2>
<p>Foundation covered running a first small test; this module covers what comes after — genuinely reading the results, deciding what to scale, and what to kill, rather than running the same test campaign indefinitely without acting on what it taught you.</p>
<h2>Audience targeting, refined</h2>
<p>Layering interests, behaviors, and lookalike audiences (people who resemble your existing customers) onto the basic targeting from Foundation meaningfully improves efficiency — a genuinely learnable skill with real, measurable impact on cost per result.</p>
<h2>Creative testing — the real lever most people skip</h2>
<p>Testing multiple ad variations (different images, different opening lines) against each other, rather than running one version indefinitely, is consistently one of the highest-impact things a small advertiser can do — more impactful for most small budgets than aggressive targeting refinement.</p>
<h2>Budget allocation across campaigns</h2>
<p>Once running more than one campaign, deliberately shifting budget toward what's actually working (rather than splitting evenly by default) compounds the value of the testing habit above.</p>"""),
    ("Email and WhatsApp Marketing Systems",
     """<h2>Why owning a contact channel matters more as you grow</h2>
<p>Foundation flagged that a social following is a rented audience; this module is about actually building the owned channel — a real WhatsApp broadcast list or email list, deliberately grown, not left as an afterthought.</p>
<h2>Growing a list ethically and effectively</h2>
<p>Offering something genuinely useful in exchange for a contact (a discount, a helpful resource) converts meaningfully better than a bare "join my list" ask, and respects the person choosing to opt in — a real transaction, not a trick.</p>
<h2>What to actually send, and how often</h2>
<p>A consistent but not overwhelming cadence, mixing genuine value with occasional direct offers (the same content-mix principle from Foundation, applied to a more personal channel), keeps a list engaged rather than driving people to unsubscribe.</p>
<h2>Segmenting a list for better results</h2>
<p>Even simple segmentation (new vs. returning customers, different interest areas) lets messages be more relevant to each recipient — a meaningfully higher-converting approach than one identical message to an entire list regardless of relevance.</p>"""),
    ("Reading Analytics Like a Marketer",
     """<h2>Moving beyond the weekly check-in</h2>
<p>Foundation introduced a simple weekly review habit; this module goes deeper — understanding what's actually driving a metric's change, not just noting that it changed, and connecting marketing metrics to real business outcomes.</p>
<h2>Connecting engagement to actual revenue</h2>
<p>High engagement that never translates into inquiries or sales is a real warning sign, not a success — deliberately tracking the full path from a post to an actual sale (even roughly) is what makes analytics genuinely useful rather than just interesting.</p>
<h2>Identifying your actual best-performing content type</h2>
<p>A genuine pattern analysis across weeks or months — not just "that one post did well" — reveals what content type consistently works for your specific audience, which is far more actionable than reacting to individual post performance.</p>
<h2>Using data to make real content decisions</h2>
<p>Letting what the data actually shows shape next month's content plan — doing more of what works, deliberately less of what doesn't — is the entire point of tracking analytics in the first place; data that's collected but never acted on has no real value.</p>"""),
    ("Scaling Your Digital Presence",
     """<h2>When it's time to bring in help</h2>
<p>A genuine signal — consistently not having time to execute the system you've built, or growth stalling because you're the bottleneck — is when bringing in a team member or freelancer for content/ads execution starts to make real sense.</p>
<h2>Documenting your system so someone else can run it</h2>
<p>Everything built across this course — content pillars, posting cadence, ad approach, list-building — should already be documented well enough to hand off; if it only lives in your head, that's the real work still needed before scaling.</p>
<h2>Managing someone else executing your digital presence</h2>
<p>Clear expectations, regular review of output against your established system, and staying involved in strategy even after handing off execution keeps quality consistent as the work moves beyond just you.</p>
<h2>Where this leads — into genuine digital marketing strategy</h2>
<p>Everything in this Intermediate tier is the applied, hands-on layer; the Advanced tier moves into the strategic layer — planning campaigns, managing a real marketing budget, and building a digital presence that scales with the business itself.</p>"""),
]

INTERMEDIATE_EXAM = [
    ("Why should content pillars be built around what your specific customer actually cares about, rather than generic \"tips\" content?",
     "Pillars reflecting the actual audience keep a content system focused and genuinely useful, rather than becoming a scattered mix of unrelated posts.",
     "Audience-specific pillars keep the content system focused rather than a scattered mix of unrelated posts",
     "Generic tips content always performs better than content tailored to a specific business's actual audience"),
    ("Why is testing multiple ad creative variations against each other described as one of the highest-impact actions for a small advertiser?",
     "Creative testing is consistently one of the highest-impact levers, often more impactful for small budgets than aggressive audience-targeting refinement alone.",
     "It's consistently high-impact, often more so than targeting refinement alone, especially for small budgets",
     "Creative testing only matters for advertisers with very large budgets and many campaigns running simultaneously"),
    ("Why does offering something genuinely useful in exchange for a contact convert better than a bare \"join my list\" ask?",
     "It's a real transaction that respects the person's choice to opt in, rather than a trick — genuinely useful value in exchange for their contact converts meaningfully better.",
     "It's a real, respectful transaction — useful value in exchange for a contact converts meaningfully better",
     "A bare join request always converts equally well regardless of what's offered in return"),
    ("Why is high engagement with no resulting inquiries or sales described as a real warning sign, not a success?",
     "Engagement that never translates into actual business outcomes signals a disconnect between attention and real value — tracking the full path to a sale is what makes analytics genuinely useful.",
     "It signals a disconnect between attention and real business outcomes, which analytics should be tracking end to end",
     "High engagement is always a positive sign regardless of whether it leads to any measurable business outcome"),
    ("What's described as the real signal that it's time to bring in help for digital execution?",
     "Consistently not having time to execute your own system, or growth stalling because you personally are the bottleneck.",
     "Consistently lacking the time to execute your system, or being the personal bottleneck on further growth",
     "Reaching a specific, universal follower-count threshold that applies to every business the same way"),
]

ADVANCED_MODULES = [
    ("Digital Marketing Strategy and Planning",
     """<h2>Moving from tactics to genuine strategy</h2>
<p>Intermediate built real tactical systems — content, ads, lists, analytics; this module is about tying them together into one coherent strategy driven by actual business goals, not a collection of separately-run tactics that happen to coexist.</p>
<h2>Setting a real digital marketing budget</h2>
<p>Deliberately allocating a marketing budget across channels based on what the data (from Intermediate's analytics work) actually shows is working, rather than splitting spend evenly or by habit, is what separates strategic budgeting from just spending.</p>
<h2>Planning a genuine campaign, not just ongoing posting</h2>
<p>A time-bound campaign with a specific goal (a launch, a seasonal push) needs deliberate planning — content, ads, and list outreach coordinated around one goal — distinct from the steady, ongoing presence built in Foundation and Intermediate.</p>
<h2>Building a strategy that adapts</h2>
<p>A strategic plan reviewed and adjusted quarterly against real results stays genuinely useful; one set once and followed rigidly regardless of what's actually happening in the market becomes a liability rather than a guide.</p>"""),
    ("Building a Digital Brand That Scales",
     """<h2>Brand consistency at a genuinely larger scale</h2>
<p>Maintaining the same brand consistency principles from Foundation becomes genuinely harder once multiple people are creating content — clear, written brand guidelines (voice, visual identity, what's off-limits) are what keep it coherent as the team grows.</p>
<h2>Managing brand reputation proactively</h2>
<p>Actively monitoring what's being said about the brand across platforms, and having a real plan for responding to both praise and criticism, is a genuinely different discipline from the individual comment-response habits covered earlier — reputation management at scale needs its own deliberate process.</p>
<h2>Expanding into new platforms strategically</h2>
<p>Adding a new platform should be a deliberate strategic decision — genuine audience presence there, clear purpose — not simply following trend pressure; the "choose deliberately, not everywhere" principle from Foundation still applies, just at a larger scale.</p>
<h2>Building genuine brand equity over time</h2>
<p>A digital brand that consistently delivers value and reliability over years builds real equity — customer trust, word-of-mouth, resilience to a single bad period — that a purely tactical, campaign-by-campaign approach never accumulates.</p>"""),
    ("Advanced Analytics and Marketing ROI",
     """<h2>Calculating real marketing ROI, not just engagement</h2>
<p>True return on marketing investment requires connecting spend to actual revenue generated, not just cost per click or engagement rate — the deepest, most decision-useful level of the analytics progression that started in Foundation.</p>
<h2>Customer acquisition cost and lifetime value together</h2>
<p>Knowing what it actually costs to acquire a customer, and what that customer is genuinely worth over their relationship with the business, together determine whether a given marketing channel is actually profitable — either number alone is incomplete.</p>
<h2>Attribution — a genuinely hard but important problem</h2>
<p>A customer's path to purchase often touches multiple channels before converting; understanding roughly which channels genuinely deserve credit (rather than only crediting the last touchpoint) leads to smarter, more accurate budget allocation.</p>
<h2>Building a genuine data-driven culture around marketing</h2>
<p>Making real business decisions based on what the data actually shows — even when it contradicts intuition or a favorite channel — is the final, most mature stage of the analytics thread that ran through every tier of this course.</p>"""),
    ("Leading Digital Transformation in Your Business",
     """<h2>Digital as a whole-business capability, not just marketing</h2>
<p>The most successful digitally-driven businesses treat digital capability as something spanning operations, customer service, and sales, not just a marketing department's concern — the strategic ceiling on this whole course's value if digital thinking stays siloed to marketing alone.</p>
<h2>Building a genuinely digital-capable team</h2>
<p>Beyond one person handling marketing, a business benefits from broader digital literacy across the team — informed by everything covered across this three-tier track, not concentrated in a single role.</p>
<h2>Staying current without chasing every trend</h2>
<p>A deliberate practice of periodically reassessing tools and platforms against actual business needs (echoing the same discipline from the original AI Skills course) keeps a digital strategy current without wasting resources chasing every new platform or feature.</p>
<h2>Closing the loop across the whole Digital Skills track</h2>
<p>Foundation built the fundamentals, Intermediate built real working systems, and this Advanced tier builds the strategic and organizational capability to make digital work a genuine, lasting competitive advantage — not a task, a real part of how the business runs.</p>"""),
]

ADVANCED_EXAM = [
    ("Why does the course distinguish \"genuine strategy\" from the tactical systems built in the Intermediate tier?",
     "Strategy ties tactics together around actual business goals, rather than leaving them as separately-run activities that happen to coexist.",
     "Strategy connects tactics to real business goals, rather than letting them run as separate, uncoordinated activities",
     "Strategy and tactics are the same thing at a larger scale, with no real distinction between them"),
    ("Why do written brand guidelines become genuinely necessary once multiple people are creating content for a business?",
     "Maintaining brand consistency gets meaningfully harder with more contributors — clear guidelines are what keep it coherent as the team grows.",
     "Consistency gets harder with more contributors, and clear written guidelines keep the brand coherent as it scales",
     "Brand guidelines are only useful for large corporations, not for a growing small business"),
    ("Why is knowing both customer acquisition cost AND lifetime value together necessary to judge a channel's profitability?",
     "Either number alone is incomplete — a channel's actual profitability depends on both what a customer costs to acquire and what they're genuinely worth over time.",
     "Acquisition cost and lifetime value together determine real profitability — neither number alone tells the full story",
     "Acquisition cost alone is sufficient to determine whether any given marketing channel is profitable"),
    ("Why does the course caution against only crediting the last touchpoint in a customer's path to purchase?",
     "A purchase path often touches multiple channels before converting — accurate attribution requires understanding which channels genuinely deserve credit, not just the final one.",
     "Purchase paths often involve multiple channels, and accurate attribution needs to account for more than just the last touch",
     "Last-touch attribution is always the most accurate method regardless of how many channels were involved"),
    ("Why does the course argue digital capability should span the whole business, not stay concentrated in a marketing role?",
     "The most successful digitally-driven businesses treat digital as a whole-business capability — confining it to marketing alone is described as a real ceiling on this course's value.",
     "Confining digital capability to marketing alone is a real ceiling — the most successful businesses spread it more broadly",
     "Digital capability is inherently a marketing-only concern and has no real relevance to other parts of a business"),
]


class Command(BaseCommand):
    help = (
        "Seeds the Intermediate and Advanced tiers under Digital Skills for "
        "Business Owners, gated behind the existing Foundation course. "
        "Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme = Programme.objects.filter(slug="digital-skills").first()
        foundation = Course.objects.filter(slug="digital-skills-for-business-owners").first()
        if not programme or not foundation:
            self.stderr.write(self.style.ERROR("Run seed_digital_skills_course first."))
            return

        with transaction.atomic():
            intermediate, _ = self._make_course(
                org, programme, slug="digital-skills-intermediate",
                title="Digital Skills — Applied Systems",
                subtitle="Real content systems, paid advertising at a working level, email/WhatsApp "
                         "marketing, analytics, and scaling your digital presence.",
                description="<p>A 5-module intermediate course building on Digital Skills for Business "
                            "Owners: building a real content system, paid advertising at a working level, "
                            "email and WhatsApp marketing systems, reading analytics like a marketer, and "
                            "scaling your digital presence.</p>",
                level=Course.Level.INTERMEDIATE, price_ngn=15000, prerequisite=foundation,
                modules=INTERMEDIATE_MODULES, exam_questions=INTERMEDIATE_EXAM,
                exam_title="Final Exam — Digital Skills Intermediate",
            )
            self._make_course(
                org, programme, slug="digital-skills-advanced",
                title="Digital Skills — Strategy and Transformation",
                subtitle="Digital marketing strategy, building a brand that scales, marketing ROI, and "
                         "leading digital transformation across your whole business.",
                description="<p>A 4-module advanced course: digital marketing strategy and planning, "
                            "building a digital brand that scales, advanced analytics and marketing ROI, "
                            "and leading digital transformation in your business.</p>",
                level=Course.Level.ADVANCED, price_ngn=18000, prerequisite=intermediate,
                modules=ADVANCED_MODULES, exam_questions=ADVANCED_EXAM,
                exam_title="Final Exam — Digital Skills Advanced",
            )

        self.stdout.write(self.style.SUCCESS(
            "Done. New tiers are unpublished — review, set Vertical + Approved + is_published in admin."
        ))

    def _make_course(self, org, programme, *, slug, title, subtitle, description, level, price_ngn,
                      prerequisite, modules, exam_questions, exam_title):
        course, created = Course.objects.get_or_create(
            organization=org, programme=programme, slug=slug,
            defaults={
                "title": title, "subtitle": subtitle, "description": description,
                "audience": Audience.GENERAL, "level": level,
                "pricing_model": Course.PricingModel.PAID, "price_ngn": price_ngn,
                "access_type": Course.AccessType.LIFETIME, "requires_final_assessment": True,
                "estimated_hours": 4.0, "is_published": False, "prerequisite": prerequisite,
                "instructor_bio": "Dr. Omale Ojonimi Samuel, Founder, Xpress Digital & Data Solutions Limited.",
            },
        )
        if not created:
            self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
            return course, False

        self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))
        for i, (mtitle, body) in enumerate(modules, start=1):
            module = Module.objects.create(
                course=course, order=i, title=mtitle, unlock_rule=Module.UnlockRule.SEQUENTIAL,
            )
            Lesson.objects.create(
                module=module, order=1, title=f"Module {i}: {mtitle}", type=Lesson.Type.TEXT,
                body=body.strip(), is_preview=(i == 1),
            )
        self.stdout.write(self.style.SUCCESS(f"  {len(modules)} modules created with real written content."))

        bank = QuestionBank.objects.create(
            organization=org, name=f"{title} — Final Exam",
            description=f"Covers all {len(modules)} modules — must be passed to unlock the certificate.",
        )
        for stem, explanation, correct, wrong in exam_questions:
            q = Question.objects.create(
                bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                difficulty=Question.Difficulty.MEDIUM,
            )
            Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
            Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
        Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=course, title=exam_title,
            instructions=f"{len(exam_questions)} questions covering the full course. Pass to unlock your certificate.",
            bank=bank, question_count=len(exam_questions), pass_mark=70,
            max_attempts=0, time_limit_minutes=0,
        )
        return course, True
