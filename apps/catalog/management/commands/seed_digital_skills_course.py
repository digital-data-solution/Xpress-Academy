from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fifth track: the Academy's own core offering — the digital skills
# the parent company (Xpress Digital and Data Solutions Ltd) already
# runs for paying clients, taught directly to small-business-owner
# leads. Self-paced (enroll any time), matching how every other course
# on this platform actually works — no cohort/live-session commitment
# implied. Same idempotent seed pattern as the other 4 tracks.

MODULES = [
    ("Digital Foundations",
     """<h2>Why a deliberate digital presence matters</h2>
<p>Most small businesses in Nigeria are on social media by default, not by design — an account was created at some point, and posting happens whenever there's time. A deliberate digital presence starts from a specific goal (more inquiries, more sales, more trust with new customers) and works backward to what to post and where, rather than posting first and hoping something works.</p>
<h2>Setting a goal you can actually measure</h2>
<p>"Grow our social media" isn't a goal you can act on. "20 qualified inquiries a month through Instagram" is — specific enough that you can tell, honestly, whether what you're doing is working or just keeping you busy.</p>
<h2>Understanding your actual customer's digital habits</h2>
<p>Where your specific customer actually spends time — which platform, at what times, in what mood (scrolling for entertainment vs. actively searching for a solution) — should drive every decision after this module, not general "what's popular" advice that may not fit your specific audience at all.</p>"""),
    ("Building a Professional Social Media Presence",
     """<h2>First impressions happen in seconds</h2>
<p>A profile photo, bio, and first few grid posts are usually what a new visitor sees before deciding whether to trust the account at all — inconsistent branding, an unclear bio, or an inactive-looking feed loses potential customers before they ever see your actual product or service.</p>
<h2>Writing a bio that actually tells people what you do</h2>
<p>A bio should answer, in seconds: what you do, who it's for, and what to do next (visit a link, message you, visit a location) — vague or purely creative bios that don't answer these plainly cost real inquiries.</p>
<h2>Choosing your platforms deliberately</h2>
<p>Being on every platform thinly is weaker than being consistently present on the one or two where your actual customer spends time — a decision made from Module 1's audience research, not from trying to cover every possible channel at once.</p>
<h2>WhatsApp Business as a real storefront</h2>
<p>For much of the Nigerian market, a properly set up WhatsApp Business profile (catalog, business hours, quick replies, away messages) converts better than a formal website — an underused, low-cost setup most small businesses never properly configure.</p>"""),
    ("Content Creation on a Budget",
     """<h2>What actually needs a professional camera (almost nothing)</h2>
<p>A recent smartphone, good natural lighting, and a clean, simple background produce content that performs perfectly well for the vast majority of small-business social media — expensive equipment is rarely the actual bottleneck to better content.</p>
<h2>Free and low-cost tools worth actually learning</h2>
<p>Simple design tools (Canva-style, free-tier), basic phone video editing built into most phones already, and free stock resources for backgrounds/graphics cover almost every real content need without a paid subscription.</p>
<h2>Batching content instead of creating daily</h2>
<p>Setting aside one session to shoot/create a week or two of content at once, rather than scrambling daily, is both more sustainable and produces more consistent quality — daily last-minute content creation is a common reason small-business social media quietly dies out after a few months.</p>
<h2>Repurposing one piece of content multiple ways</h2>
<p>A single photo shoot or video can become a feed post, a story, a WhatsApp status, and a caption-driven text post — multiplying the value of each content creation session rather than needing entirely new content for every format.</p>"""),
    ("Social Media Management Fundamentals",
     """<h2>Consistency beats frequency</h2>
<p>Posting reliably three times a week, every week, builds more trust and algorithmic favor than posting daily for two weeks and then going silent for a month — a consistent, sustainable rhythm is the actual foundation most accounts are missing, not simply "more posts."</p>
<h2>Platform-specific behavior, briefly</h2>
<p>Instagram rewards visual consistency and Stories/Reels engagement; Facebook still performs well for community-driven local businesses and older demographics; TikTok rewards native, unpolished authenticity over produced content — treating every platform identically wastes each one's real strengths.</p>
<h2>Scheduling tools and why they matter</h2>
<p>A scheduling tool (many with usable free tiers) lets a batched content session from Module 3 actually go out consistently without needing to remember to post manually every single day — removing the single most common reason consistency breaks down.</p>
<h2>Responding — the management half of "social media management"</h2>
<p>Timely, genuine responses to comments and messages are as much a part of "management" as posting — an account that posts well but never responds trains its own audience to stop engaging.</p>"""),
    ("Copywriting and Captions That Convert",
     """<h2>Writing for the specific reader, not a general audience</h2>
<p>A caption written for "everyone" persuades no one — writing as if speaking directly to the one specific customer from Module 1's audience research produces language that actually resonates rather than generic marketing-speak.</p>
<h2>The hook — earning the next three seconds</h2>
<p>The first line has to earn attention before anything else in the caption matters — a question, a bold specific claim, or a relatable problem statement consistently outperforms a generic opening line.</p>
<h2>Selling the outcome, not just the feature</h2>
<p>"Handmade leather bags" describes a feature; "a bag that still looks new after three years of daily use" sells an outcome — customers buy outcomes, and captions that only list features leave the actual persuading undone.</p>
<h2>A clear call to action, every time</h2>
<p>Every caption should tell the reader exactly what to do next — "DM to order," "link in bio," "comment YES for details" — leaving it implied rather than explicit measurably reduces how many interested readers actually act.</p>"""),
    ("Digital Marketing Fundamentals",
     """<h2>The customer journey, in plain terms</h2>
<p>Awareness (they discover you exist), consideration (they're deciding whether to trust/choose you), and decision (they actually buy) are the three real stages every customer moves through — knowing which stage a specific piece of content or message is meant to serve prevents the common mistake of only ever creating "buy now" content for people who don't know you yet.</p>
<h2>Organic vs. paid — what each is actually good for</h2>
<p>Organic content builds trust and audience over time at the cost of your own time; paid reach buys speed and precise targeting at the cost of money — a healthy digital marketing approach usually uses both deliberately, not one exclusively.</p>
<h2>Funnels — a simple, practical version</h2>
<p>A funnel is just a deliberate path: content that earns attention, leads to a specific next step (a message, a link, a visit), leads to a sale. Mapping your own actual funnel, even roughly, reveals exactly where interested people are currently falling through the cracks.</p>"""),
    ("Running Your First Paid Ad Campaign",
     """<h2>Why a small test budget beats a large blind one</h2>
<p>Starting with a genuinely small budget (enough to learn, not enough to hurt if it doesn't work) and measuring results before increasing spend is the responsible, realistic way to learn paid advertising — most first-campaign losses come from spending too much before learning what actually works.</p>
<h2>Targeting — reaching the right people, not just more people</h2>
<p>Narrow, specific targeting (based on the real customer profile from Module 1) usually outperforms broad targeting for a small business — a wider audience isn't better if most of it was never going to buy anyway.</p>
<h2>Writing an ad that doesn't feel like an ad</h2>
<p>Ad creative that looks and reads like the organic content already performing well for your account typically outperforms obviously "ad-styled" creative — audiences are increasingly skilled at tuning out anything that visually announces itself as an advertisement.</p>
<h2>What to actually track during a first campaign</h2>
<p>Cost per genuine inquiry/sale (not just clicks or reach) is the number that actually tells you whether a campaign is working — vanity metrics like reach and likes can look impressive while a campaign is quietly losing money.</p>"""),
    ("Analytics and Measuring What Actually Works",
     """<h2>Vanity metrics vs. metrics that matter</h2>
<p>Likes, reach, and follower count feel good but rarely map directly to revenue; inquiries, click-throughs to a specific action, and actual sales attributable to a post or campaign are what should drive real decisions.</p>
<h2>Reading platform analytics without getting lost</h2>
<p>Every major platform provides free built-in analytics — the skill isn't accessing the data, it's knowing which two or three numbers to actually check regularly (engagement rate on recent posts, follower growth trend, top-performing content type) rather than getting overwhelmed by every available metric.</p>
<h2>A simple weekly review habit</h2>
<p>Ten minutes a week reviewing what performed well and what didn't, and adjusting the next week's content accordingly, compounds into real improvement over months — most small businesses never do this at all, posting the same way indefinitely regardless of what's actually working.</p>"""),
    ("Customer Engagement and Community Management",
     """<h2>Comments and DMs are real sales conversations</h2>
<p>A comment or DM asking about price, availability, or details is a genuine sales opportunity, not just social interaction to acknowledge — treating it with the same seriousness as an in-person inquiry, including a timely response, directly affects revenue.</p>
<h2>Handling negative comments and reviews publicly</h2>
<p>A calm, genuine, public response to a complaint — acknowledging the issue and offering a real resolution — builds more trust with everyone else watching than deleting or ignoring it, which usually looks worse than the original complaint.</p>
<h2>Building genuine community, not just an audience</h2>
<p>Asking questions, responding to every comment, and featuring real customers turns passive followers into an engaged community that shares and refers — a meaningfully higher-value outcome than follower count alone.</p>"""),
    ("Building a Content Calendar and Workflow",
     """<h2>Why a calendar beats posting on inspiration</h2>
<p>Relying on inspiration to post consistently fails within weeks for almost everyone — a simple content calendar, planned even a week or two ahead, is what actually sustains the consistency Module 4 covers.</p>
<h2>A realistic content mix</h2>
<p>A sustainable mix — some educational/value content, some behind-the-scenes/relatable content, some direct promotional content — keeps an audience engaged without either boring them with constant selling or never actually asking for the sale.</p>
<h2>A simple weekly workflow that actually gets followed</h2>
<p>One session to plan the week, one batched session to create content (Module 3), scheduling it out in advance (Module 4's tools), and a short weekly review (Module 8) — a repeatable system, not a fresh decision every single day.</p>"""),
    ("Turning Followers Into Customers",
     """<h2>Why followers alone don't pay the bills</h2>
<p>A large following with no clear path to purchase is a common trap — every piece of the system built across this course (presence, content, engagement, ads) should ultimately connect to an actual, specific path to buying.</p>
<h2>Building a simple WhatsApp funnel</h2>
<p>Directing interested followers to WhatsApp, where a warm, direct conversation can happen, consistently converts better than expecting a sale to close entirely within a comments section or DM thread — a deliberate handoff point worth building into every relevant post.</p>
<h2>Following up with people who showed interest but didn't buy</h2>
<p>Most lost sales aren't lost to a competitor — they're lost to no follow-up after initial interest went quiet, the same lesson that applies to any sales process, digital or otherwise.</p>
<h2>Your 90-day digital growth plan</h2>
<p>Bringing every module together into one specific, written plan for your own business — what you'll post, how often, on which platforms, with what budget for ads, and how you'll measure it — turns this course from information into an actual next 90 days of real action.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("Why does the course recommend starting from a specific, measurable goal rather than \"growing social media\" generally?",
     "A vague goal can't tell you whether what you're doing is actually working; a specific, measurable one can.",
     "A specific, measurable goal lets you honestly tell whether your efforts are working, not just busy",
     "Specific goals are only useful for large businesses with dedicated marketing teams"),
    ("Why does the course recommend narrow, specific ad targeting over broad targeting for a small business?",
     "A wider audience isn't better if most of it was never going to buy — narrow targeting based on a real customer profile usually outperforms broad reach.",
     "Narrow targeting based on a real customer profile usually outperforms broad reach for a small business",
     "Broad targeting always produces more total sales than narrow targeting regardless of budget"),
    ("Why does the course say cost per genuine inquiry/sale matters more than reach or likes when running a paid ad campaign?",
     "Vanity metrics like reach and likes can look impressive while a campaign is quietly losing money — cost per real inquiry/sale is what actually tells you if it's working.",
     "Reach and likes can look good while a campaign is still losing money — real inquiry/sale cost is what matters",
     "Reach and likes are the most reliable indicators of a paid campaign's real financial performance"),
    ("Why does responding to a negative comment publicly and calmly usually build more trust than deleting it?",
     "Everyone else watching sees how a real complaint was handled, which usually builds more trust than a deleted comment, which tends to look worse.",
     "Other viewers see the complaint handled well, which builds more trust than deleting it would",
     "Negative comments should always be deleted immediately to protect the business's public image"),
    ("Why is a content calendar recommended over posting whenever inspiration strikes?",
     "Relying on inspiration to post consistently fails within weeks for almost everyone — a calendar sustains the consistency that actually matters.",
     "A calendar sustains consistent posting, which inspiration-based posting almost always fails to do over time",
     "A content calendar mainly exists to make content look more professionally produced"),
    ("Why does the course specifically recommend directing interested followers to WhatsApp rather than trying to close a sale in the comments section?",
     "A warm, direct WhatsApp conversation consistently converts better than expecting a sale to close entirely within a public comments thread.",
     "A direct WhatsApp conversation converts noticeably better than trying to close within a comments thread",
     "WhatsApp is only useful for customer support, not for actually converting a sale"),
    ("According to the course, why are most lost sales actually lost?",
     "Most lost sales aren't lost to a competitor — they're lost to no follow-up after initial interest went quiet.",
     "They're most often lost to a lack of follow-up after interest went quiet, not to a competitor",
     "Most lost sales are lost because the product or service itself wasn't good enough"),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Digital Skills for Business Owners' — the Academy's core "
        "11-module course teaching the digital marketing/social media "
        "skills Xpress Digital and Data Solutions already runs for clients. "
        "Self-paced, real written content, general-audience. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="digital-skills",
            defaults={
                "title": "Digital Skills",
                "audience": Audience.GENERAL,
                "description": "The digital marketing and social media skills Xpress Digital and Data "
                                "Solutions already runs for clients — taught directly to business owners.",
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="digital-skills-for-business-owners",
                defaults={
                    "title": "Digital Skills for Business Owners",
                    "subtitle": "11 modules teaching the exact social media and digital marketing skills our "
                                 "own team runs for paying clients — hands-on, not theory.",
                    "description": "<p>A practical, self-paced digital skills course for small-business owners "
                                    "and aspiring digital marketers. Covers building a professional social media "
                                    "presence, content creation on a budget, social media management fundamentals, "
                                    "copywriting that converts, digital marketing fundamentals, running a first "
                                    "paid ad campaign, analytics, customer engagement, content calendar workflows, "
                                    "and turning followers into paying customers — the same process Xpress Digital "
                                    "and Data Solutions runs for real clients.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 20000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 6.0,
                    "is_published": False,
                    "sales_headline": "Learn what we do for our clients",
                    "sales_subheadline": "We charge clients ₦150,000+/month to run this. Learn to do it yourself — "
                                          "11 modules, real workflows, taught by the team that actually runs them.",
                    "target_audience": (
                        "Small business owners who want to stop guessing at social media and digital marketing\n"
                        "Anyone who wants a real, repeatable process instead of scattered tips\n"
                        "No prior marketing background required"
                    ),
                    "not_for": (
                        "Anyone looking for advanced/enterprise-scale digital marketing strategy — this is built "
                        "for a small business managing its own presence, not a dedicated marketing department"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, Founder, Xpress Digital & Data Solutions Limited "
                                       "— the team behind this course runs the same playbook for real clients.",
                    "meta_description": "Practical digital marketing and social media skills for business "
                                         "owners — taught by the agency that runs it for real clients.",
                },
            )

            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                return

            self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))
            for i, (title, body) in enumerate(MODULES, start=1):
                module = Module.objects.create(
                    course=course, order=i, title=title, unlock_rule=Module.UnlockRule.SEQUENTIAL,
                )
                Lesson.objects.create(
                    module=module, order=1, title=f"Module {i}: {title}", type=Lesson.Type.TEXT,
                    body=body.strip(), is_preview=(i == 1),
                )
            self.stdout.write(self.style.SUCCESS(f"  {len(MODULES)} modules created with real written content."))

            bank = QuestionBank.objects.create(
                organization=org, name="Digital Skills for Business Owners — Final Exam",
                description="Covers all 11 modules — must be passed to unlock the certificate.",
            )
            for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.MEDIUM,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
            Quiz.objects.create(
                scope=Quiz.Scope.FINAL, course=course, title="Final Exam — Digital Skills for Business Owners",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin."
        ))
