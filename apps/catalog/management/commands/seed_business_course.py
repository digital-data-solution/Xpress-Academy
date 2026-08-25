from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fourth track: a deep, practical business-management course for
# Nigerian entrepreneurs and SME owners — 12 modules spanning planning,
# legal structure, finance, marketing, sales, operations, people, and
# growth. General-audience (not sector-specific), real written content,
# same pattern as the AI Skills / poultry / vet-breeding tracks.

MODULES = [
    ("Business Planning and Model Design",
     """<h2>Why a business plan is a thinking tool, not paperwork</h2>
<p>Most people who avoid writing a business plan imagine it as a formal document for a bank. In practice, its real value is forcing you to answer hard questions before you spend money finding out the answers the expensive way: who exactly is your customer, what are they paying for right now, and why would they switch to you. A plan you actually use is short, specific, and revisited — not a one-time document filed away and forgotten.</p>
<h2>The business model canvas, in plain terms</h2>
<p>A business model is really just an answer to: who you serve, what value you give them, how you reach them, how you make money, and what it costs you to deliver. Mapping these five things on one page — even roughly — exposes gaps most new businesses only discover after losing money: an unclear customer, an unclear reason to buy from you specifically, or costs nobody accounted for.</p>
<h2>Validating an idea before committing real money</h2>
<p>Talking to 10-20 real potential customers before building anything, testing willingness to actually pay (not just "would you use this" — a much weaker signal than "would you pay for this"), and starting with the smallest possible version of the offer are the difference between validated demand and an expensive guess.</p>
<h2>Setting realistic, specific goals</h2>
<p>"Grow the business" isn't a goal you can act on. "50 paying customers by the end of the quarter" is. Specific, time-bound, measurable targets — even rough ones — are what let you tell the difference between a business that's working and one that just feels busy.</p>"""),
    ("Registering and Structuring a Business in Nigeria",
     """<h2>Business name vs. limited liability company</h2>
<p>A registered Business Name (through CAC) is the fastest, cheapest way to formalize a business, but it does not separate your personal assets from business liabilities — if the business owes money or is sued, you're personally exposed. A Limited Liability Company (Ltd) costs more and takes more paperwork to set up, but genuinely separates you from the business legally — a real distinction, not a technicality, once a business takes on real risk (contracts, staff, debt).</p>
<h2>The actual CAC registration steps</h2>
<p>Name availability search and reservation, submission of required documents (means of identification, registered address, for a company: memorandum and articles of association), payment of statutory fees, and issuance of your registration certificate/RC number — increasingly done through the CAC's own online portal rather than exclusively through an agent, though many owners still use one for convenience.</p>
<h2>Tax registration and basic compliance</h2>
<p>Once registered, a business needs a Tax Identification Number (TIN) from FIRS, and depending on structure and turnover, may owe Companies Income Tax, VAT (currently charged on most goods/services above the small-company threshold), and PAYE if you have employees. Ignoring this isn't a savings — it's a deferred, compounding liability that catches many growing businesses off guard exactly when they can least afford the surprise.</p>
<h2>Choosing a structure that fits where you actually are</h2>
<p>A sole proprietor testing an idea with little capital at risk reasonably starts with a Business Name; a business taking on partners, seeking investment, or carrying real contractual/liability risk should seriously consider a Limited Liability Company from the start rather than converting under pressure later, which is more expensive and disruptive than starting right.</p>"""),
    ("Financial Management and Bookkeeping Fundamentals",
     """<h2>Why "I know my numbers in my head" fails as a business grows</h2>
<p>Informal mental bookkeeping works until it doesn't — usually right when the business is busy enough that the failure is expensive: money owed to you that you forgot to collect, expenses that quietly exceed revenue, or simply not knowing if you're actually profitable versus just having cash in hand at any given moment (a genuinely different thing, covered below).</p>
<h2>The three numbers every owner must track</h2>
<p>Revenue (money coming in from sales), expenses (money going out to run the business), and cash flow (the actual timing of money moving, separate from revenue/expense totals) are the non-negotiable minimum. A profitable business on paper can still run out of cash if customers pay slowly while suppliers must be paid quickly — a genuinely common cause of business failure that has nothing to do with whether the business idea itself is sound.</p>
<h2>Separating business and personal finances</h2>
<p>A dedicated business bank account, even for a small sole-proprietor business, is the single highest-leverage bookkeeping habit — it makes every other financial task (knowing real profit, preparing for tax, tracking growth) dramatically easier and more honest, and is close to non-negotiable once a business has any real revenue.</p>
<h2>Basic records worth keeping from day one</h2>
<p>A simple sales log, an expense log (with receipts), and a running bank reconciliation — even in a spreadsheet — are enough to start. The goal isn't sophisticated accounting immediately; it's a consistent, truthful record you can build on, versus starting formal bookkeeping two years late once memory and paper receipts have already been lost.</p>
<h2>When to bring in a professional</h2>
<p>Basic bookkeeping is manageable by most owners early on; annual tax filing, and certainly anything involving a limited company's statutory accounts, is worth a qualified accountant's involvement — the cost is usually small relative to the risk and time cost of getting it wrong.</p>"""),
    ("Pricing, Costing and Profitability",
     """<h2>Cost-based vs. value-based pricing</h2>
<p>Cost-based pricing (cost plus a margin) guarantees you cover expenses but ignores what the customer is actually willing to pay. Value-based pricing starts from what the offer is worth to the customer, which is often considerably more than raw cost — the more differentiated and genuinely valuable your offer, the more room value-based pricing gives you over simply marking up cost.</p>
<h2>Knowing your true cost before you price anything</h2>
<p>True cost includes not just raw materials/direct cost but a fair share of overhead (rent, utilities, your own time) and, for anything with waste, returns, or spoilage, that loss factored in. Pricing off direct cost alone while ignoring overhead is a common, quiet way a seemingly profitable business is actually losing money on every sale.</p>
<h2>Understanding gross margin and why it matters</h2>
<p>Gross margin — revenue minus direct cost of the product/service, as a percentage — tells you how much room you have to cover overhead and still profit. A business with thin gross margins needs very high volume or very low overhead to survive; understanding your actual margin, not just "am I making sales," is what separates a plan for real profitability from hoping it works out.</p>
<h2>The real cost of underpricing</h2>
<p>Underpricing to win customers is one of the most common mistakes new business owners make — it's psychologically easier than asking for what something is worth, but it trains customers to expect low prices, makes raising prices later genuinely harder, and can mean growing a business that's busy but never actually profitable.</p>"""),
    ("Marketing Fundamentals and Brand Building",
     """<h2>What "brand" actually means, beyond a logo</h2>
<p>A brand is the sum of what people think and feel when they encounter your business — built through every touchpoint (product quality, customer service, how you communicate), not just visual identity. A polished logo on an inconsistent, unreliable business builds a weaker brand than a plain logo on a business that consistently delivers.</p>
<h2>Identifying your actual target customer</h2>
<p>"Everyone" is not a target customer — marketing aimed at everyone reaches no one effectively. A specific, well-understood customer profile (who they are, what problem they have, where they spend time, what makes them decide to buy) lets every marketing decision — channel, message, tone — actually be deliberate rather than guessed at.</p>
<h2>Positioning: what makes you the obvious choice</h2>
<p>Positioning is the clear, specific answer to "why you, instead of the alternative" — whether that's price, quality, speed, convenience, trust, or something else genuinely differentiating. A business without a clear position competes on price by default, which is the least defensible position to compete from long-term.</p>
<h2>Consistency over cleverness</h2>
<p>A consistent message and visual identity across every channel, repeated over time, builds recognition and trust far more reliably than one clever campaign — most small-business marketing fails not from a lack of creativity but from a lack of consistency and follow-through over months, not days.</p>"""),
    ("Digital Marketing and Social Media for Business",
     """<h2>Choosing platforms based on where your customer actually is</h2>
<p>Being present on every platform is a common, wasteful mistake — a business should show up where its specific target customer actually spends attention, and be genuinely consistent there, rather than being thinly, inconsistently present everywhere.</p>
<h2>Content that earns attention vs. content that just exists</h2>
<p>Content that solves a real problem, answers a real question, or genuinely entertains earns attention; content that's purely promotional ("buy our product") without giving the audience anything gets scrolled past. A rough rule many businesses find useful: most content should provide value first, with direct promotion a smaller minority of what's posted.</p>
<h2>WhatsApp and Telegram as real Nigerian business channels</h2>
<p>For much of the Nigerian market, WhatsApp Business (catalogs, quick replies, broadcast lists) and Telegram channels are genuinely higher-converting than formal websites for many small businesses — meeting customers on the channel they already use daily, rather than requiring them to go somewhere new.</p>
<h2>Paid advertising — starting small and measuring</h2>
<p>Paid social/search ads can work well, but only with a clear goal, a small test budget, and honest tracking of what that spend actually returned — spending on ads without measurement is close to spending blind, regardless of platform.</p>
<h2>Building an audience you actually own</h2>
<p>A social media following lives on a platform you don't control and can lose access to overnight (an account ban, an algorithm change). An email list, WhatsApp broadcast list, or customer database is an asset you genuinely own — worth deliberately building alongside any social media presence, not instead of it.</p>"""),
    ("Sales and Customer Acquisition",
     """<h2>The real sales process, stripped of jargon</h2>
<p>Every sale, however it happens, moves through the same real stages: someone becomes aware you exist, gets interested enough to consider you, decides to buy, and (ideally) becomes a repeat customer. Knowing which stage a given prospect is actually at determines what should happen next — pushing for a close on someone who's barely aware of you is a common, avoidable mistake.</p>
<h2>Handling objections honestly</h2>
<p>"It's too expensive," "I need to think about it," and "I'm not sure it'll work for me" are almost always really requests for reassurance, not final no's — genuinely understanding the specific concern behind an objection, rather than immediately discounting or over-promising to overcome it, closes more sales and builds more trust than either extreme.</p>
<h2>Referrals — the highest-trust acquisition channel</h2>
<p>A referred customer arrives with borrowed trust from whoever referred them, converts faster, and typically costs nothing to acquire — actively asking satisfied customers for referrals (most businesses simply never ask) is one of the highest-leverage, lowest-cost growth actions available to almost any small business.</p>
<h2>Following up — where most small businesses lose sales</h2>
<p>A large share of lost sales aren't lost to a competitor — they're lost to no follow-up at all after initial interest. A simple, consistent follow-up habit (a message a few days after an inquiry that went quiet) recovers real revenue most businesses are currently leaving on the table.</p>"""),
    ("Customer Service and Retention",
     """<h2>Why retention is usually cheaper than acquisition</h2>
<p>Acquiring a new customer typically costs meaningfully more, in money and effort, than keeping an existing one — yet many small businesses invest heavily in acquisition while treating existing customers as already "won" and needing no further attention. Deliberately investing in retention is often the highest-return marketing decision a growing business can make.</p>
<h2>What actually creates a loyal customer</h2>
<p>Reliability (doing what you said, when you said), how well problems are handled when something goes wrong (not whether problems ever happen — they will), and feeling genuinely valued rather than just transacted with, consistently outweigh price as the real driver of long-term loyalty.</p>
<h2>Handling complaints as an opportunity, not a threat</h2>
<p>A customer who complains directly to you is giving you a chance to fix things before they tell others instead — responding quickly, taking real ownership rather than being defensive, and following through on the fix consistently turns a complaint into one of the strongest loyalty-building moments available.</p>
<h2>Simple systems for staying in touch</h2>
<p>A basic customer record (contact info, what they bought, when), even in a spreadsheet, lets you follow up at the right moments — a restock reminder, a check-in, a relevant new offer — rather than relying on customers to remember to come back on their own.</p>"""),
    ("Operations, Supply Chain and Inventory Management",
     """<h2>Why operations is where profit is quietly won or lost</h2>
<p>Marketing and sales get the most attention, but inefficient operations — wasted materials, poor scheduling, stock that ties up cash sitting unsold — quietly erode profit in ways that don't show up until you actually look. A business can have strong sales and still struggle financially purely from operational inefficiency.</p>
<h2>Managing suppliers as real relationships</h2>
<p>Reliable, well-managed suppliers (clear terms, timely payment, honest communication when something changes) are a genuine competitive advantage — a business that treats suppliers purely transactionally often gets deprioritized exactly when reliability matters most, during shortages or high demand.</p>
<h2>Inventory — the real cost of getting it wrong</h2>
<p>Overstocking ties up cash and risks spoilage/obsolescence; understocking loses sales and frustrates customers who then look elsewhere. Tracking actual sell-through rate (not just "are we out of stock") is what lets ordering decisions be based on real demand patterns rather than guesswork or gut feeling alone.</p>
<h2>Basic process documentation — worth doing earlier than it feels necessary</h2>
<p>Writing down how a repeated task is actually done — even briefly — means it doesn't live only in one person's head, which matters the moment you hire your first employee or take your first day off. Most small businesses only start documenting processes after a costly gap caused by one key person being unavailable.</p>"""),
    ("Leadership, Team Management and Delegation",
     """<h2>The mindset shift from doer to leader</h2>
<p>Many business owners struggle to grow past a certain size because they never make the shift from personally doing most of the work to building a team that can do it without them — a genuinely different skill set, and one of the most common ceilings on small business growth.</p>
<h2>Hiring for a small business, done right</h2>
<p>Clear expectations before hiring (what the role actually needs to accomplish, not just a vague job title), checking references seriously, and a real (even if short) trial or probation period reduce the very real cost of a bad hire, which is expensive both financially and in team morale.</p>
<h2>Delegation that actually works</h2>
<p>Effective delegation hands over both the task and genuine authority to make related decisions, with a clear standard for what "done well" looks like — delegating a task while still controlling every decision within it isn't real delegation, and it burns out both the owner and the employee.</p>
<h2>Building a culture, deliberately</h2>
<p>How you treat mistakes, how directly problems get raised and discussed, and what actually gets recognized and rewarded set the real culture of a business — far more than any stated values poster. Culture is built through consistent daily behavior, not declared once and assumed to hold.</p>"""),
    ("Funding, Investment and Access to Capital",
     """<h2>Bootstrapping — funding growth from your own revenue</h2>
<p>Reinvesting profit rather than seeking outside capital keeps full ownership and control, and forces real financial discipline — the right approach for many small businesses, especially early on, though it can mean slower growth than a well-funded competitor.</p>
<h2>Debt financing — loans and what they actually cost</h2>
<p>A loan (bank, cooperative, or microfinance) must be repaid regardless of whether the business succeeds — understanding the true cost (interest rate, fees, repayment schedule) against what the borrowed capital will actually generate is essential before taking on debt, not an afterthought once funds are already spent.</p>
<h2>Equity investment — what you're really giving up</h2>
<p>Taking on an investor means giving up a real share of ownership and, usually, some control over decisions — worth pursuing when the investor brings genuine value beyond just money (connections, expertise, credibility), and worth being cautious about when it's purely capital with no other real fit.</p>
<h2>Grants and government/development programs</h2>
<p>Grants (government SME schemes, development-agency programs, competitions) provide capital without dilution or repayment, but usually come with real application effort, reporting requirements, and genuine competition — worth pursuing deliberately, not as a first resort to solve every funding gap.</p>
<h2>Being genuinely "investment ready"</h2>
<p>Clean, honest financial records, a clear plan for how capital will be used and what return it will generate, and a track record (even a short one) of executing on stated plans are what actually make a business attractive to any serious source of outside capital — far more than a polished pitch alone.</p>"""),
    ("Growth Strategy, Risk Management and Scaling",
     """<h2>Growth that's deliberate vs. growth that's just busy</h2>
<p>Not all growth is good growth — taking on more customers, more product lines, or more locations without the underlying systems (finance, operations, people) to support it strains a business in ways that can undo real progress. Deliberate growth means scaling capacity alongside demand, not chasing every opportunity that appears.</p>
<h2>Identifying your real growth levers</h2>
<p>More customers, higher average sale value, more frequent repeat purchases, and better margins are the actual levers behind growth — most businesses focus almost entirely on the first (more customers) while leaving real, often easier gains on the table in the other three.</p>
<h2>Risk management — thinking about what could go wrong, deliberately</h2>
<p>Key-person risk (the business depends entirely on one person, often the owner), concentration risk (too much revenue from one customer or one product), and inadequate insurance/legal protection are common, foreseeable risks worth deliberately planning for — not something to discover the hard way when they materialize.</p>
<h2>Building a business that can eventually run without you</h2>
<p>Whether the long-term goal is to sell the business, step back from daily operations, or simply take a real holiday without everything stalling, building systems, documented processes, and a capable team that don't depend entirely on the owner's constant presence is what actually makes a business an asset rather than a job that owns you.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("Why is a Limited Liability Company (Ltd) a genuinely different structure from a registered Business Name, not just more paperwork?",
     "An Ltd legally separates the owner's personal assets from business liabilities, while a Business Name does not — a real legal distinction, not a technicality.",
     "It legally separates personal assets from business liabilities — a real distinction once real risk is involved",
     "It's purely a formality with no real practical difference from a Business Name"),
    ("Why can a profitable business on paper still run out of cash?",
     "Cash flow is about the actual timing of money moving — a business can be profitable overall while customers pay slowly and suppliers must be paid quickly.",
     "Because cash flow timing is separate from overall profitability — slow customer payment against fast supplier payment",
     "A profitable business can never actually run out of cash if its books are accurate"),
    ("What's the real risk of consistently underpricing to win customers?",
     "It trains customers to expect low prices, makes raising prices later harder, and can mean growing a business that's busy but never actually profitable.",
     "It trains customer expectations low and can produce a busy business that's still not actually profitable",
     "There's no real long-term risk as long as sales volume stays high"),
    ("Why does the course recommend a specific target customer over marketing to \"everyone\"?",
     "Marketing aimed at everyone reaches no one effectively — a specific, well-understood customer profile lets channel, message, and tone actually be deliberate.",
     "A specific customer profile lets every marketing decision be deliberate rather than guessed at",
     "Targeting a specific customer unnecessarily limits how many people could ever buy from you"),
    ("Why is retention often a higher-return investment than acquisition for a growing small business?",
     "Acquiring a new customer typically costs meaningfully more than keeping an existing one, yet many businesses under-invest in retention.",
     "New-customer acquisition typically costs more than retaining an existing customer, and retention is often under-invested in",
     "Retention and acquisition cost the same, so the choice makes no real financial difference"),
    ("What makes delegation genuinely effective, rather than just assigning tasks?",
     "Handing over both the task and real authority to make related decisions, with a clear standard for what \"done well\" looks like.",
     "Delegating both the task and real decision-making authority, with a clear standard of success",
     "Assigning a task while the owner still makes every decision within it counts as effective delegation"),
    ("Why is taking on equity investment a fundamentally different decision from taking a loan?",
     "Equity investment means giving up real ownership and usually some control, while a loan must be repaid but doesn't dilute ownership.",
     "Equity gives up real ownership/control, while a loan must be repaid but keeps ownership intact",
     "Equity and debt financing carry essentially the same real trade-offs for a business owner"),
    ("Why does the course caution against chasing every growth opportunity that appears?",
     "Growth without the underlying systems (finance, operations, people) to support it strains a business in ways that can undo real progress.",
     "Growth without matching operational/financial/people capacity can strain and undo real progress",
     "Any growth opportunity is worth pursuing immediately regardless of current capacity"),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Business Management for Entrepreneurs & SME Owners' — a "
        "12-module deep course covering planning, legal structure, finance, "
        "marketing, sales, operations, leadership, funding, and growth. "
        "Real written content, general-audience. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="business-and-entrepreneurship",
            defaults={
                "title": "Business & Entrepreneurship",
                "audience": Audience.GENERAL,
                "description": "Practical, deep business-management courses for Nigerian entrepreneurs and SME owners.",
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="business-management-for-entrepreneurs",
                defaults={
                    "title": "Business Management for Entrepreneurs & SME Owners",
                    "subtitle": "12 modules covering planning, legal structure, finance, marketing, sales, "
                                 "operations, leadership, funding, and growth — built for Nigerian business owners.",
                    "description": "<p>A comprehensive, practical business-management course for entrepreneurs "
                                    "and SME owners. Covers business planning and model design, registering and "
                                    "structuring a business in Nigeria (CAC, tax, compliance), financial management "
                                    "and bookkeeping, pricing and profitability, marketing and brand building, "
                                    "digital marketing and social media, sales and customer acquisition, customer "
                                    "service and retention, operations and inventory management, leadership and "
                                    "team management, funding and access to capital, and growth strategy with real "
                                    "risk management.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 10000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 7.0,
                    "is_published": False,
                    "sales_headline": "Run your business like you mean it",
                    "sales_subheadline": "12 deep modules — planning, legal structure, finance, marketing, sales, "
                                          "operations, leadership, funding, and growth — built for Nigerian "
                                          "entrepreneurs and SME owners, not generic business-school theory.",
                    "target_audience": (
                        "Entrepreneurs starting or formalizing a business in Nigeria\n"
                        "SME owners who've been running on instinct and want real structure\n"
                        "Anyone managing a team, finances, or growth decisions without formal business training"
                    ),
                    "not_for": (
                        "Large-enterprise corporate finance/strategy — this is built for small and growing "
                        "businesses, with Nigeria-specific detail (CAC registration, FIRS/PAYE, local funding routes)"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, Founder, Xpress Digital & Data Solutions Limited.",
                    "meta_description": "A deep, practical business-management course for Nigerian entrepreneurs "
                                         "and SME owners — planning, legal, finance, marketing, sales, operations, "
                                         "leadership, funding, and growth.",
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
                organization=org, name="Business Management for Entrepreneurs — Final Exam",
                description="Covers all 12 modules — must be passed to unlock the certificate.",
            )
            for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.MEDIUM,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
            Quiz.objects.create(
                scope=Quiz.Scope.FINAL, course=course, title="Final Exam — Business Management for Entrepreneurs",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin."
        ))
