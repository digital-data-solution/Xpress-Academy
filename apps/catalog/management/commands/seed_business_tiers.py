from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Business Management for Entrepreneurs & SME Owners launched
# Foundation-only. Per explicit instruction, every Foundation-only line
# needs Intermediate and Advanced tiers, gated by prerequisite.

INTERMEDIATE_MODULES = [
    ("Building Real Financial Systems",
     """<h2>From basic bookkeeping to a real financial system</h2>
<p>Foundation covered why bookkeeping matters; this module covers actually building one — a simple chart of accounts, a monthly close routine, and a habit of reviewing real numbers on a set schedule, not just when something feels wrong.</p>
<h2>Budgeting as a forward-looking tool, not just a record</h2>
<p>A budget's real value is in comparing planned versus actual spending regularly, catching drift early — a budget built once and never revisited is closer to a wish list than a management tool.</p>
<h2>Managing cash flow deliberately</h2>
<p>Building a simple cash-flow forecast (expected money in and out over the next 4-8 weeks) turns Foundation's "cash flow matters" lesson into an actual practice — the single highest-leverage habit for avoiding the cash crunches that sink otherwise-healthy businesses.</p>
<h2>Working with an accountant or bookkeeper effectively</h2>
<p>Bringing clean, consistent records to a professional gets far more value from that relationship than arriving with a shoebox of receipts once a year — this module is as much about being a good client to your accountant as it is about the numbers themselves.</p>"""),
    ("Team Building and Hiring Right",
     """<h2>Knowing when you actually need to hire</h2>
<p>Hiring to solve a temporary overload versus hiring for genuine sustained growth are different decisions with different right answers — hiring reactively, under pressure, is a common source of expensive mismatches.</p>
<h2>Writing a role that's actually clear</h2>
<p>A specific description of what the role needs to accomplish (not just a generic title) attracts better-fit candidates and sets a real standard to hire and later evaluate against.</p>
<h2>Interviewing for real fit, not just credentials</h2>
<p>Structured questions about how a candidate actually handled real past situations reveal far more than a general conversation about their resume — a genuinely learnable interviewing skill, not an innate talent some people just have.</p>
<h2>Onboarding that sets someone up to succeed</h2>
<p>A new hire's first weeks — clear expectations, early feedback, real support — substantially shape whether they succeed or struggle; treating onboarding as a real process rather than "figure it out" measurably reduces early turnover.</p>"""),
    ("Sales Systems That Don't Depend on You",
     """<h2>Why "I'm the best salesperson" is a real growth ceiling</h2>
<p>A business where sales only happen because the owner personally closes every deal can't grow past what one person's time allows — building a repeatable sales process that others can execute is what actually removes this ceiling.</p>
<h2>Documenting your own sales process</h2>
<p>Writing down what you actually do — from first contact through closing — turns implicit skill into something a team member can learn and follow, the same documentation principle from Foundation's operations module, applied specifically to sales.</p>
<h2>Setting real sales targets and tracking them</h2>
<p>Specific, tracked targets (not just "sell more") for a sales team or process reveal whether it's actually working, and where — which stage, which channel — is worth the next round of improvement effort.</p>
<h2>Handling the handoff without losing the personal touch</h2>
<p>Customers who valued a personal relationship with the owner can feel a real loss when sales moves to a team — deliberately managing that transition (introductions, maintained involvement in key relationships) preserves what mattered while still removing the ceiling.</p>"""),
    ("Managing Cash Flow Through Growth",
     """<h2>Why growth itself can strain cash flow</h2>
<p>Growing sales often means paying for more inventory, staff, or capacity before the corresponding revenue actually arrives — a genuinely counter-intuitive but common cause of a fast-growing business running into a cash crisis.</p>
<h2>Financing growth responsibly</h2>
<p>A short-term financing gap (a loan, a credit line) to bridge a real growth investment is a reasonable, common tool — provided the actual return and repayment plan are calculated honestly beforehand, not assumed optimistically.</p>
<h2>Negotiating payment terms as a growth lever</h2>
<p>Negotiating faster payment from customers and slightly longer payment terms to suppliers, where reasonably possible, directly eases the cash strain of growth — an underused lever compared to simply trying to sell more.</p>
<h2>Building a cash buffer deliberately</h2>
<p>Maintaining a deliberate cash reserve, even a modest one, gives real flexibility to handle a slow month or an unexpected cost without a crisis — building this in during good periods is far easier than trying to build it during a downturn.</p>"""),
    ("Systems and Processes for a Growing Business",
     """<h2>Why "it worked when we were small" stops working</h2>
<p>Informal, undocumented ways of doing things that worked fine with three people commonly break down at ten or twenty — the business hasn't necessarily gotten worse, it's outgrown its own informal systems, and that's a normal, predictable growth pain.</p>
<h2>Identifying which processes actually need documenting first</h2>
<p>The processes that are repeated most often, or that would cause the most damage if done wrong, are the highest-priority candidates for real documentation — not every single task needs a written process on day one.</p>
<h2>Building systems that scale, not just document</h2>
<p>A genuinely scalable system anticipates growth (can it handle double the volume without falling apart) rather than just describing the current, smaller-scale way of doing things — worth deliberately designing for the size you're growing toward, not just the size you are now.</p>
<h2>Reviewing and updating systems as the business changes</h2>
<p>A system documented once and never revisited becomes outdated and gets quietly ignored — building in a periodic review habit keeps systems actually useful rather than becoming a well-intentioned document nobody follows.</p>"""),
]

INTERMEDIATE_EXAM = [
    ("Why is comparing planned versus actual spending regularly more valuable than simply having a budget document?",
     "A budget's real value is catching drift early through regular comparison — one built once and never revisited functions more like a wish list than a management tool.",
     "Regular comparison catches drift early; an unreviewed budget functions more like a wish list than a real tool",
     "A budget only needs to be created once and referenced occasionally for it to be fully effective"),
    ("Why is hiring reactively, under pressure, described as a common source of expensive mismatches?",
     "Hiring to solve a temporary overload is a genuinely different decision from hiring for sustained growth — treating them the same, under pressure, commonly produces a poor fit.",
     "Temporary-overload hiring and sustained-growth hiring are different decisions, and pressure often blurs that distinction",
     "Reactive hiring produces the same quality outcomes as planned hiring as long as the role is eventually filled"),
    ("Why does a business built entirely around the owner personally closing every sale eventually hit a real growth ceiling?",
     "Sales that only happen through one person's direct involvement can't scale past what that one person's time allows — a documented, repeatable process is what removes the ceiling.",
     "One person's available time inherently caps how much can be sold, regardless of demand",
     "There is no real ceiling as long as the owner is willing to work more hours"),
    ("Why can rapid business growth itself cause a cash flow crisis, even when the business is fundamentally healthy?",
     "Growing sales often require paying for inventory, staff, or capacity before the corresponding revenue actually arrives — a real, counter-intuitive strain distinct from unprofitability.",
     "Growth commonly requires upfront spending on capacity before matching revenue arrives, straining cash even in a healthy business",
     "A growing business can never experience a real cash flow problem since revenue is increasing"),
    ("Why do informal processes that worked fine at a small team size often break down as a business grows?",
     "The business outgrows its own informal systems — a normal, predictable growth pain, not a sign the business itself has gotten worse.",
     "The business has simply outgrown informal systems that depended on a small, closely-coordinated team",
     "Process breakdowns during growth always indicate a fundamental flaw in the original business model"),
]

ADVANCED_MODULES = [
    ("Strategic Planning for Sustainable Growth",
     """<h2>Strategy as deliberate choice, not just ambition</h2>
<p>Real strategy is choosing what NOT to pursue as much as what to pursue — a business trying to be everything to everyone dilutes its resources and its market position; deliberate focus, even at the cost of some opportunities, is what strategic planning actually protects.</p>
<h2>Setting a genuine 1-3 year direction</h2>
<p>A written, specific direction — not just "grow" — gives every subsequent decision (hiring, investment, which opportunities to chase) a real reference point to be evaluated against, rather than each decision being made in isolation.</p>
<h2>Competitive positioning at a strategic level</h2>
<p>Understanding not just who your competitors are but genuinely why customers choose between you and them shapes strategy far more usefully than a generic SWOT exercise — real strategic insight comes from real customer understanding, not a template.</p>
<h2>Revisiting strategy as conditions change</h2>
<p>A strategic plan set once and never revisited becomes a historical document rather than a living tool — building in a genuine periodic strategic review (not just an operational one) keeps direction actually current.</p>"""),
    ("Advanced Financial Management and Investment Decisions",
     """<h2>Reading financial statements as decision tools</h2>
<p>A profit and loss statement, balance sheet, and cash flow statement each answer a genuinely different question — profitability, financial position, and liquidity respectively — and real financial management means using all three together, not relying on just one.</p>
<h2>Evaluating a major investment decision properly</h2>
<p>A structured evaluation (expected return, payback period, what happens if it underperforms) protects against a major investment decision being made on optimism or pressure alone — worth doing deliberately even for a decision that feels obviously right.</p>
<h2>Understanding your real cost of capital</h2>
<p>Whether financing growth through debt, retained profit, or outside investment, each has a real cost — understanding what that cost actually is (interest, dilution, opportunity cost of retained profit) is what makes a financing decision genuinely informed rather than just convenient.</p>
<h2>Building financial resilience deliberately</h2>
<p>Diversified revenue where reasonably possible, a real cash reserve, and honest, regular financial review are what let a business absorb a genuine shock (a bad month, an economic downturn, a lost major customer) without an existential crisis.</p>"""),
    ("Mergers, Partnerships, and Strategic Alliances",
     """<h2>When a partnership genuinely makes sense</h2>
<p>A strategic partnership works when both parties bring something the other genuinely lacks and can't easily replicate alone — partnering just to partner, without that real complementary value, rarely produces a lasting or valuable relationship.</p>
<h2>Structuring a partnership to actually survive disagreement</h2>
<p>A clear written agreement covering decision-making, profit-sharing, and what happens if the partnership needs to end, established while the relationship is still healthy, prevents a genuinely damaging dispute later — this is protective work, not a sign of distrust.</p>
<h2>Evaluating an acquisition opportunity, briefly</h2>
<p>Whether acquiring another business or being acquired, real due diligence — financial, operational, and cultural fit — is what separates a genuinely value-creating deal from an expensive mistake dressed up as opportunity.</p>
<h2>Alternatives to a full merger or acquisition</h2>
<p>A looser strategic alliance, joint venture, or referral partnership can capture much of the value of a full merger with far less risk and complexity — worth genuinely considering before assuming a full merger or acquisition is the only path to a given strategic goal.</p>"""),
    ("Building a Business That Can Run Without You",
     """<h2>The real test of a mature business</h2>
<p>Whether a business can function — genuinely, not just survive — for a month without the owner present is a real, concrete test of how much has actually been built into systems and people versus how much still lives only in the owner's head.</p>
<h2>Succession planning, even if you're not leaving soon</h2>
<p>Identifying who could step into key roles, including the owner's own role, if genuinely needed, isn't pessimism — it's the same risk management discipline Foundation introduced, applied at the highest level of the business.</p>
<h2>Preparing for a future sale, even if you never sell</h2>
<p>The habits that make a business genuinely sellable — clean financials, documented systems, reduced owner-dependency — are the exact same habits that make it a better, more resilient business to actually run, whether or not a sale is ever on the table.</p>
<h2>Closing the loop across every tier of this track</h2>
<p>Every module across Foundation, Intermediate, and this Advanced tier ultimately builds toward the same real outcome: a business that's genuinely well-run, not just busy — profitable, systemized, and resilient enough to outlast any single person's constant presence, including the owner's.</p>"""),
]

ADVANCED_EXAM = [
    ("Why does real strategic planning involve deliberately choosing what NOT to pursue, not just setting ambitious goals?",
     "A business trying to be everything to everyone dilutes its resources and market position — deliberate focus is what strategy actually protects, even at the cost of some opportunities.",
     "Deliberate focus protects resources and market position, even though it means declining some opportunities",
     "Strategic planning should maximize the number of opportunities pursued simultaneously"),
    ("Why does real financial management require using the P&L, balance sheet, and cash flow statement together, not just one?",
     "Each answers a genuinely different question — profitability, financial position, and liquidity respectively — relying on just one gives an incomplete picture.",
     "Each statement answers a different real question, and relying on only one leaves a genuinely incomplete picture",
     "The three statements report the same underlying information in different formats, so any one is sufficient"),
    ("Why does the course recommend structuring a partnership agreement while the relationship is still healthy, rather than waiting?",
     "A clear agreement on decision-making, profit-sharing, and an exit path, set up early, prevents a genuinely damaging dispute later — it's protective, not a sign of distrust.",
     "Setting terms early, while the relationship is healthy, prevents a genuinely damaging dispute later on",
     "Partnership agreements are only legally necessary once a disagreement has already begun"),
    ("What does the course describe as a real, concrete test of how much a business has actually been built into systems versus one person's head?",
     "Whether the business can genuinely function for a month without the owner present.",
     "Whether the business can genuinely keep functioning for a real stretch of time without the owner present",
     "Whether the business has a written mission statement posted in its office"),
    ("Why are the habits that make a business genuinely sellable described as valuable even if the owner never actually sells?",
     "Clean financials, documented systems, and reduced owner-dependency are the same habits that make a business better and more resilient to run day to day, regardless of any eventual sale.",
     "The same habits that improve sellability also make the business more resilient and better-run in general",
     "Building toward sellability only has value in the specific scenario where a sale is actually planned"),
]


class Command(BaseCommand):
    help = (
        "Seeds the Intermediate and Advanced tiers under Business Management "
        "for Entrepreneurs & SME Owners, gated behind the existing Foundation "
        "course. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme = Programme.objects.filter(slug="business-and-entrepreneurship").first()
        foundation = Course.objects.filter(slug="business-management-for-entrepreneurs").first()
        if not programme or not foundation:
            self.stderr.write(self.style.ERROR("Run seed_business_course first."))
            return

        with transaction.atomic():
            intermediate, _ = self._make_course(
                org, programme, slug="business-management-intermediate",
                title="Business Management — Growth Operations",
                subtitle="Real financial systems, hiring right, sales systems that don't depend on you, "
                         "and managing cash flow through growth.",
                description="<p>A 5-module intermediate course building on Business Management for "
                            "Entrepreneurs & SME Owners: building real financial systems, team building and "
                            "hiring right, sales systems that don't depend on you, managing cash flow through "
                            "growth, and systems/processes for a growing business.</p>",
                level=Course.Level.INTERMEDIATE, price_ngn=8000, prerequisite=foundation,
                modules=INTERMEDIATE_MODULES, exam_questions=INTERMEDIATE_EXAM,
                exam_title="Final Exam — Business Management Intermediate",
            )
            self._make_course(
                org, programme, slug="business-management-advanced",
                title="Business Management — Strategic Leadership",
                subtitle="Strategic planning, advanced financial decisions, partnerships and alliances, "
                         "and building a business that can run without you.",
                description="<p>A 4-module advanced course: strategic planning for sustainable growth, "
                            "advanced financial management and investment decisions, mergers/partnerships/"
                            "strategic alliances, and building a business that can run without you.</p>",
                level=Course.Level.ADVANCED, price_ngn=12000, prerequisite=intermediate,
                modules=ADVANCED_MODULES, exam_questions=ADVANCED_EXAM,
                exam_title="Final Exam — Business Management Advanced",
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
