from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.enrollment.models import Enrollment
from apps.organizations.models import Organization

# The 15-course general/compulsory onboarding track — separate from
# Manager Onboarding (which is role-specific and stays fully open, no
# gating). This track is chained: course N+1 has course N as its
# prerequisite and unlock_delay_days=7, so it only becomes available
# once N is actually completed AND a week has passed — real,
# course-to-course pacing, not module-level locking within one course
# (that's what Manager Onboarding used to do, wrongly — see its own
# seed command's history).
#
# Content is grounded in real source material relayed from the
# xpress-digital-and-data-solutions-58 session (Employee Handbook,
# Operating Blueprint v2, Data Quality Handbook, real SOPs, the live
# site's About page). Where that material was explicitly thin or
# unfinished, this file says so honestly in a code comment rather than
# inventing specifics to fill the gap — see the per-course notes below
# (courses 1, 4, 8, 11, 15).
#
# Each entry: (slug, title, subtitle, body_html, quiz_title, questions)
# questions: list of (stem, explanation, correct_choice, wrong_choice)

COURSES = [
    (
        "welcome-to-xdds",
        "Welcome to XDDS: Our Story & Core Values",
        "Who we are, what we stand for, and how we think about work.",
        """<h2>Who we are</h2>
<p>Xpress Digital and Data Solutions Limited is a CAC-registered Nigerian company — RC 9112280, incorporated under CAMA 2020, registered 23 December 2025 in Lagos. That registration matters: it means everything the company does is done under a real, accountable legal entity, not an informal arrangement.</p>
<p>The company's own words for what it does: "We bridge the gap between innovative technology and measurable business success. We deliver high-quality web solutions, sophisticated data synchronization systems, and comprehensive digital services that help our clients thrive and compete effectively on the global stage. From Lagos to the world, we're committed to excellence, transparency, and building trust through registered, professional service delivery."</p>
<h2>Three core values</h2>
<p><strong>Predictability (Process-First)</strong> — work follows a process, not improvisation. A client or teammate should be able to predict how something will be handled because there's a known way it's done, not because they got lucky with who picked it up.</p>
<p><strong>Integrity (Transparent Communication)</strong> — say what's actually true, especially when it's inconvenient. A missed deadline communicated early is integrity; a missed deadline discovered by the client is not.</p>
<p><strong>Mastery (Expertise & Growth)</strong> — genuine competence, actively maintained. Mastery isn't a one-time credential; it's staying sharp on purpose.</p>
<h2>The founding philosophy</h2>
<p>From the company's own internal strategy document: "We are not building a traditional company. We are building a machine that thinks, automates, and scales... Our edge is not headcount — it is intelligence, speed, and systems." Every hire is expected to ask, daily: <em>Can this be automated? Can AI do this faster or better? What is the highest-value thing only a human can do here?</em></p>
<h2>What's expected of you — the ten commitments</h2>
<p>From the company's internal strategy document, every team member agrees to:</p>
<ol>
<li>I will always look for a way to automate what I am doing manually.</li>
<li>I will use AI tools before asking a human for help.</li>
<li>I will propose at least one system improvement every month.</li>
<li>I will document every process I own so it can one day be handed to automation.</li>
<li>I will respond to clients and colleagues within agreed response time standards.</li>
<li>I will update the CRM immediately — stale data costs the whole company.</li>
<li>I will measure my own performance with real KPIs — not activity, but outcomes.</li>
<li>I will share what I learn about AI tools, better workflows, and new automations.</li>
<li>I will never do something manually a second time without asking if it can be automated.</li>
<li>I will treat every client interaction as if the company's reputation depends on it — because it does.</li>
</ol>
<p>These aren't abstract — several connect directly to things covered later in this track: commitment 5 to the response-time standards in Course 13, commitment 6 to the sales pipeline in Course 9, commitment 7 to the review structure in Course 5.</p>""",
        "Welcome to XDDS — Check",
        [
            ("What is XDDS's CAC registration number?",
             "RC 9112280 — the company's real, registered legal identity.",
             "RC 9112280", "RC 9211280"),
            ("Which of these is one of the three core values?",
             "Predictability, Integrity, and Mastery are the three — 'Speed' isn't one of them, even though speed matters to the company.",
             "Integrity (Transparent Communication)", "Speed (Move Fast)"),
            ("What question is every team member expected to ask daily about their own work?",
             "\"Can this be automated? Can AI do this faster or better?\" is the literal daily standard from the founding philosophy.",
             "Can this be automated, and can AI do it faster or better?",
             "How many hours did I bill today?"),
            ("Which of these is one of the ten team-member commitments?",
             "\"I will update the CRM immediately — stale data costs the whole company\" is commitment 6, verbatim.",
             "I will update the CRM immediately — stale data costs the whole company",
             "I will always agree with my manager, even when I disagree"),
        ],
    ),
    (
        "how-we-work-automation-first",
        "How We Work: Automation-First Philosophy",
        "What automation-first actually looks like in daily work, not just as a slogan.",
        """<h2>The standard: one person, five-person output</h2>
<p>The company's stated goal is that one well-equipped person, using AI and automation properly, should be able to produce what used to take a five-person team. That's not about working five times harder — it's about not doing manually what a tool can already do reliably.</p>
<h2>What's already automated here</h2>
<p>This isn't theoretical — real automation is already running day to day: lead nurture sequences that follow up with prospects automatically, stage-based emails that fire when a deal moves in the CRM, CI/CD pipelines that deploy code without a person manually pushing it live, and invoicing that generates and sends without someone typing it out by hand each time.</p>
<h2>Applying the test to your own role</h2>
<p>Before doing a repetitive task manually, the real habit to build is asking: is this already automated somewhere I haven't found yet? If not, could an AI tool do a first pass I then review, rather than starting from a blank page? And if neither applies — that's exactly the kind of task where a human's judgment is the actual value, not the typing.</p>
<h2>Why this matters beyond "being efficient"</h2>
<p>This isn't about replacing people — it's about making sure the humans on a small team spend their time on the parts that actually need a human: judgment calls, relationship-building, catching what a tool would miss. Time spent on something a tool already does well is time taken away from that.</p>""",
        "Automation-First — Check",
        [
            ("According to the automation-first standard, what should one well-equipped person be able to produce?",
             "The company's explicit standard: one person's output, with AI/automation used properly, should match what a five-person team used to take.",
             "What a five-person team used to produce", "Exactly what one person alone could do unaided"),
            ("Which of these is already a real, running automation at the company (not hypothetical)?",
             "Lead nurture sequences, stage-based emails, CI/CD deploys, and automated invoicing are all real, already-live automations mentioned by name.",
             "CI/CD pipelines that deploy code automatically",
             "A robot that attends client meetings in person"),
            ("Before doing a repetitive task by hand, what should you ask first?",
             "The daily test is whether it's already automated, or whether AI could do a first pass — not whether you personally feel like doing it manually.",
             "Is this already automated, or could AI do a first pass I review?",
             "Is there anyone else who could do this instead of me?"),
        ],
    ),
    (
        "what-we-sell",
        "What We Sell: Our Products & Services",
        "The full picture of what XDDS actually offers — including this Academy.",
        """<h2>Core service pillars</h2>
<p>XDDS's core agency business sells five real pillars of work: <strong>Custom Development & Integration</strong> (bespoke software, systems talking to each other), <strong>Cloud Services & Infrastructure</strong>, <strong>AI & Blockchain</strong> work, <strong>Digital Presence & SEO</strong> (web design/development, discoverability), and <strong>Data Strategy & Synchronization</strong> — the sophisticated data-sync work the company's own mission statement calls out by name.</p>
<h2>The wider family of Xpress-owned products</h2>
<p>Beyond client agency work, XDDS owns and builds its own products directly:</p>
<p><strong>Xpress Ajo</strong> — a group-savings ("ajo"/contribution-circle) fintech app. Still early-stage; described here only at the concept level, since the detailed product spec for it hasn't been finalized yet.</p>
<p><strong>Xpress Vet Marketplace</strong> — a veterinary and agricultural regulatory-compliance product, tied directly to the founder's own background (a DVM veterinarian with NAFDAC regulatory experience). Also early-stage at the detailed-spec level, described here conceptually.</p>
<p><strong>Xpress Digital Academy</strong> — <em>this platform, the one you're taking this course on right now.</em> It's a real, live, operating product: an online learning platform with published courses across multiple subject areas (veterinary continuing education, business, digital skills, AI skills, and more), a full instructor marketplace where verified instructors can build and sell their own courses, quizzes and graded final exams, verifiable PDF certificates issued on completion, and — as of this course existing — the internal staff-training system you're using right now. It is a genuine product line XDDS sells and operates, not a side project.</p>
<h2>Client work — NOT part of what XDDS owns</h2>
<p>It's worth being precise here: some websites/projects in the company's portfolio were built <em>for</em> outside clients (agency work, delivered and owned by that client afterward) rather than being XDDS's own products. Don't describe client-delivered work as if it were something XDDS itself owns or runs — that's a real distinction worth getting right when talking to anyone outside the company.</p>""",
        "What We Sell — Check",
        [
            ("Which of these is a real, live, currently-operating Xpress-owned product (not concept-stage)?",
             "Xpress Digital Academy is live and operating right now — you're using it. Ajo and Vet Marketplace are still concept-stage.",
             "Xpress Digital Academy", "Xpress Ajo"),
            ("What is Xpress Digital Academy, concretely?",
             "It's a real online learning platform: published courses, an instructor marketplace, quizzes/final exams, verifiable certificates, and internal staff training.",
             "An online learning platform with courses, an instructor marketplace, and certificates",
             "A planned future product with no live version yet"),
            ("A website XDDS built for an outside client is best described as:",
             "Client-delivered work belongs to the client afterward — it's not one of XDDS's own owned products.",
             "Client work, not an XDDS-owned product", "Another one of XDDS's own product lines"),
        ],
    ),
    (
        "our-departments",
        "Our Departments & How They Connect",
        "The 9-department structure, and where the company actually is in its growth.",
        """<h2>Nine departments, one reporting line</h2>
<p>The company is organized into nine departments — Marketing, Social Media, Sales, Technical, Delivery & PM, Accounts & Finance, HR, ICT, and Legal & Compliance — each with its own mission and KPIs, all currently reporting to the Founder/CEO. In practical, functional terms: Marketing and Social Media build audience and awareness; Sales moves a prospect from interest to a signed deal; Technical and Delivery & PM actually build and ship the work; Accounts & Finance handles money in and out; HR covers people/hiring/reviews; ICT keeps internal systems and access running; Legal & Compliance covers contracts, IP, and regulatory obligations.</p>
<p>With the team this small right now, department names describe <em>functions and responsibility areas</em>, not necessarily separate people — the same person may cover more than one function today. Ask your manager which department(s) your own role actually touches.</p>
<h2>Where the company is right now</h2>
<p>XDDS describes its own growth in four phases: <strong>Phase 1 — Solo/Founder</strong> (where the company is today), then First Hires, then Growth, then Scale. Knowing this matters: a lot of what will eventually be formal, department-specific process is still being built as the company grows past Phase 1 — some of what you'll be told in future training modules genuinely doesn't exist yet as finished policy, and that's honest, not a gap being hidden from you.</p>
<h2>Who to approach for what</h2>
<p>As a practical rule while the org is this flat: for anything about your own employment, compensation, or a workplace concern, that's HR-shaped territory — currently routed through the Founder/CEO directly. For a client-facing question about scope, budget, or a change to what was agreed, that's Sales/Delivery-shaped. For account access, tools, or something broken on a system, that's ICT-shaped.</p>""",
        "Departments — Check",
        [
            ("How many departments does the company's org structure define?",
             "Nine: Marketing, Social Media, Sales, Technical, Delivery & PM, Accounts & Finance, HR, ICT, Legal & Compliance.",
             "Nine", "Five"),
            ("Which growth phase is the company in right now?",
             "Phase 1 — Solo/Founder, the first of four phases (Solo → First Hires → Growth → Scale).",
             "Phase 1: Solo/Founder", "Phase 3: Growth"),
            ("Who do all nine departments currently report to?",
             "The Founder/CEO — the company is still flat, with no deeper reporting hierarchy modeled yet.",
             "The Founder/CEO", "A separate department head for each function"),
        ],
    ),
    (
        "your-employment-at-xdds",
        "Your Employment at XDDS",
        "Employment status, probation, reviews, and how compensation works.",
        """<h2>FTE vs. Contractor</h2>
<p>XDDS engages people either as Full-Time Employees or as Contractors — a real, meaningful distinction that affects how your engagement is structured. Know which one applies to you; if you're not sure, ask directly rather than assuming.</p>
<h2>Probation</h2>
<p>New hires go through a <strong>6-month probation period</strong>, with <strong>monthly reviews</strong> during that window — not a single pass/fail moment at the end, but regular check-ins along the way.</p>
<h2>Compensation and reviews</h2>
<p>Compensation is reviewed annually. On top of base compensation, Developers and Project Managers are eligible for <strong>quarterly bonuses tied to KPI performance</strong> — real, measurable targets, not discretionary. There's also an annual training budget, reflecting the "Mastery" value: growth is meant to be actively supported, not left entirely up to you to fund yourself.</p>
<p>Beyond probation, performance is reviewed <strong>semi-annually</strong> (twice a year) across three areas: <strong>Technical Competence</strong> (are you good at the actual work), <strong>Process Adherence</strong> (do you follow how things are actually meant to be done — connects directly to the "Predictability" value from Course 1), and <strong>Client-Team Communication</strong> (how you communicate, both with clients and internally).</p>
<h2>Why this structure exists</h2>
<p>Regular, scheduled reviews — monthly during probation, semi-annual afterward — exist so that feedback is a routine, expected part of working here, not a surprise sprung on someone once a year. If you haven't had a review on the expected cadence, that's worth raising directly rather than assuming it was skipped on purpose.</p>""",
        "Your Employment — Check",
        [
            ("How long is the standard probation period, and how often is it reviewed?",
             "Six months, with monthly reviews throughout — not one pass/fail moment at the end.",
             "6 months, reviewed monthly", "3 months, reviewed once at the end"),
            ("How often are performance reviews conducted after probation?",
             "Semi-annually — twice a year, covering Technical Competence, Process Adherence, and Communication.",
             "Semi-annually (twice a year)", "Only once, at the one-year mark"),
            ("Who is eligible for quarterly KPI-tied bonuses?",
             "Developers and Project Managers specifically, per the compensation structure.",
             "Developers and Project Managers", "Every employee regardless of role"),
        ],
    ),
    (
        "code-of-conduct",
        "Code of Conduct & Conflict of Interest",
        "The communication standard, the disciplinary ladder, and how to disclose a conflict.",
        """<h2>The communication standard</h2>
<p>The company's own words: <em>"Respectful, transparent, and direct communication is expected. Harassment and discrimination of any kind are strictly forbidden."</em> That's not a soft aspiration — it's the literal, stated standard everyone is held to, connecting directly to the "Integrity" value from Course 1.</p>
<h2>The disciplinary ladder</h2>
<p>When conduct falls short, the company follows a defined progression rather than jumping straight to the harshest response: <strong>verbal warning → written warning → final warning → termination.</strong> Knowing this matters both ways — it means a first mistake isn't treated as a career-ending event, and it means the progression is real and does escalate if a pattern continues.</p>
<h2>Conflicts of interest</h2>
<p>A conflict of interest is any situation where your personal interests (financial, a relationship, a side business) could reasonably influence — or appear to influence — a decision you make for the company. The rule is simple: <strong>disclose it to the PM Lead</strong> as soon as you're aware of it. Disclosing early and honestly is not itself a problem; failing to disclose one that later comes to light is.</p>
<h2>Why this exists</h2>
<p>None of this is about assuming bad intent — it's about making sure everyone knows exactly what's expected and exactly what happens if it isn't met, so nobody is surprised by either the standard or the consequences.</p>""",
        "Code of Conduct — Check",
        [
            ("What kind of communication does the code of conduct explicitly require?",
             "\"Respectful, transparent, and direct communication is expected\" — the literal standard.",
             "Respectful, transparent, and direct", "Whatever gets the fastest response"),
            ("What is the correct order of the disciplinary ladder?",
             "Verbal warning, then written warning, then final warning, then termination — a defined progression, not an immediate jump to the harshest outcome.",
             "Verbal warning → written warning → final warning → termination",
             "Written warning → verbal warning → termination"),
            ("Who should a conflict of interest be disclosed to?",
             "The PM Lead — as soon as you're aware of it, not after the fact.",
             "The PM Lead", "No one, unless directly asked"),
        ],
    ),
    (
        "security-confidentiality-data",
        "Security, Confidentiality & Client Data Protection",
        "The real rules on PII, breach reporting, and who owns what you deliver.",
        """<h2>A separate NDA, and mandatory security basics</h2>
<p>Beyond your general employment agreement, a separate NDA applies specifically to confidentiality. A VPN is mandatory when accessing company/client systems, and equipment used for work needs to be genuinely secure — not an afterthought.</p>
<h2>The PII rule — no exceptions</h2>
<p>The rule is direct: <strong>never download personally identifiable information (PII) to a local, unsecured device.</strong> Client and company data that includes real people's personal information stays inside secured, approved systems — not a personal laptop's downloads folder, not a personal email, not a personal cloud drive.</p>
<h2>If something goes wrong</h2>
<p>If you ever suspect a data breach — lost equipment, unauthorized access, data sent somewhere it shouldn't have gone — the obligation is <strong>immediate reporting</strong>, not waiting to see if it becomes a real problem, and not trying to quietly fix it yourself first. Early reporting is what limits damage; the delay is usually what makes an incident worse.</p>
<h2>Who owns what you build</h2>
<p>Deliverables you produce for a client automatically become that client's property once delivered, per the governing Client Service Agreement / Statement of Work (CSA/SOW) — this is standard and expected in agency work, and it's why client data and IP need to be handled with real care throughout a project, not just at handoff.</p>""",
        "Security & Data — Check",
        [
            ("Where is it acceptable to download PII (personally identifiable information) for convenience?",
             "Nowhere unsecured, ever — never a local, unsecured device, no exceptions for convenience.",
             "Nowhere — never to a local, unsecured device", "A personal laptop, if you delete it afterward"),
            ("If you suspect a data breach, what should you do?",
             "Report it immediately — don't wait to see if it becomes a real problem, and don't try to quietly resolve it yourself first.",
             "Report it immediately", "Try to fix it quietly first, then report only if needed"),
            ("Who owns a deliverable once it's handed over to a client?",
             "The client — deliverables auto-assign as client property per the governing CSA/SOW.",
             "The client, per the CSA/SOW", "XDDS retains ownership indefinitely"),
        ],
    ),
    (
        "time-tracking-change-orders",
        "Time Tracking, Budget Red-Flags & the Change Order Process",
        "When extra work needs a change order, and why flagging early matters.",
        """<h2>The rule on extra work</h2>
<p>No work beyond what was originally agreed should happen without either a signed change order, or at minimum an explicit WhatsApp confirmation from whoever owns the client relationship. This protects both the client (from scope quietly growing without their knowledge) and you (from doing real, uncompensated extra work that was never actually approved).</p>
<h2>Flag scope changes immediately, in writing</h2>
<p>The moment you notice a project's scope is shifting from what was originally agreed — a client asking for "just one more thing" that's actually a meaningfully different task — flag it in writing right away. Waiting until the project wraps up to mention it removes any real chance of getting it properly approved and compensated.</p>
<h2>On working hours</h2>
<p>The company's own working-hours policy is still being finalized as of this course being written — it isn't something this course can state precisely yet. Until that's settled and communicated, <strong>follow your manager's direction</strong> on hours and availability rather than assuming a specific policy that hasn't actually been confirmed.</p>""",
        "Time & Change Orders — Check",
        [
            ("A client casually asks for extra work beyond the original agreement. What's the correct response?",
             "Get a signed change order or at least explicit WhatsApp confirmation before doing it — never just proceed on a casual ask.",
             "Flag it and get a signed change order or explicit confirmation first",
             "Just do it quickly since it's a small ask"),
            ("When should a scope change be flagged?",
             "Immediately, in writing — not saved up until the project wraps.",
             "Immediately, in writing, as soon as it's noticed",
             "At the end of the project, in the close-out notes"),
            ("What should you follow regarding working hours, given the company policy is still unfinished?",
             "Your manager's direction — the company hasn't finalized a specific working-hours policy yet.",
             "Your manager's direction", "A fixed 9-to-5 policy stated in the handbook"),
        ],
    ),
    (
        "sales-to-project-handoff",
        "Sales-to-Project Handoff: How a Client Becomes a Project",
        "The CRM pipeline stages, and what must happen before work actually starts.",
        """<h2>The pipeline</h2>
<p>Every client moves through the same defined stages in the CRM before becoming an active project: <strong>LEAD → MQL (Marketing Qualified Lead) → SQL (Sales Qualified Lead) → NEGOTIATIONS → WON.</strong> Each stage means something specific — a lead isn't the same as someone actively negotiating terms, and treating them the same wastes everyone's time.</p>
<h2>From quote to deal</h2>
<p>A deal is only real once a quote has actually been agreed and the client has moved to WON — not at "they seemed interested" or "we sent a proposal." This matters because response-time expectations (covered later, in Course 13) actually change depending on which stage a client is at.</p>
<h2>The handoff checklist</h2>
<p>Before a project actually starts, there's a real handoff from Sales to Delivery — the people building the work need what Sales agreed to, not a vague summary. A rushed or incomplete handoff is one of the most common reasons a project starts on the wrong foot.</p>""",
        "Sales-to-Project — Check",
        [
            ("What comes immediately after MQL in the pipeline?",
             "LEAD → MQL → SQL → NEGOTIATIONS → WON — SQL is the stage right after MQL.",
             "SQL (Sales Qualified Lead)", "WON"),
            ("At what point is a deal actually considered real?",
             "Once a quote is agreed and the client has moved to WON — not at earlier, softer signals of interest.",
             "Once the quote is agreed and the client reaches WON",
             "As soon as a proposal is sent"),
            ("Why does a proper Sales-to-Delivery handoff matter?",
             "A rushed or incomplete handoff is one of the most common reasons a project starts on the wrong foot.",
             "It prevents the project starting on the wrong foot",
             "It's only a formality with no real effect on the project"),
        ],
    ),
    (
        "delivering-client-work",
        "Delivering Client Work: Kickoff to Close-out",
        "The real lifecycle of a project once it's WON, start to finish.",
        """<h2>Kickoff</h2>
<p>Once a deal reaches WON, kickoff happens on WhatsApp within <strong>24 hours</strong>. That speed is deliberate — a client who just committed should feel that commitment was met with real momentum, not silence.</p>
<h2>Through the middle of the project</h2>
<p>Regular milestone updates keep a client informed as work progresses. A hard rule: <strong>never go silent on a client for more than 3 days.</strong> Even "still on track, nothing new to report" is a better message than nothing at all — silence is what erodes trust fastest, even when the actual work is going fine.</p>
<h2>Revisions and sign-off</h2>
<p>Client revision requests are capped at <strong>two rounds</strong> as standard — beyond that, further changes are a scope conversation (see Course 8's change-order rule), not an open-ended redo. Nothing gets deployed to a client's live environment without their <strong>written approval</strong> first — a verbal "looks good" on a call isn't sufficient sign-off.</p>
<h2>Close-out</h2>
<p>Every project ends with close-out notes recorded in the CRM — what was delivered, what came up, anything worth knowing for next time. This isn't paperwork for its own sake; it's how the next person (or your future self) actually benefits from what this project taught.</p>""",
        "Delivering Client Work — Check",
        [
            ("How quickly should kickoff happen after a deal reaches WON?",
             "Within 24 hours, on WhatsApp — deliberately fast, to match the client's momentum.",
             "Within 24 hours", "Within one week"),
            ("What's the maximum number of days a client should go without an update?",
             "Never more than 3 days — even a brief \"still on track\" message counts.",
             "3 days", "2 weeks"),
            ("How many rounds of client revisions are standard before it becomes a scope/change-order conversation?",
             "Two rounds — beyond that, further changes go through the change-order process from Course 8.",
             "Two rounds", "Unlimited, as long as the client is a repeat customer"),
        ],
    ),
    (
        "data-quality-standards",
        "Data Quality Standards Everyone Should Know",
        "Why data quality is everyone's job, not just Technical's — and the real cost of getting it wrong.",
        """<h2>Why this applies beyond Technical</h2>
<p>Data quality isn't only a developer's concern — anyone entering, editing, or passing along data (a lead's details in the CRM, a client's requirements in a doc, numbers in a report) can introduce or catch an error. The habits in this course apply company-wide.</p>
<h2>Common categories of data error worth knowing</h2>
<p>Real-world data quality work generally recognizes a handful of recurring error types: <strong>duplicate</strong> records (the same thing entered twice), <strong>missing</strong> data (a required field left empty), <strong>inconsistent</strong> data (the same fact recorded differently in two places), <strong>invalid format</strong> (a phone number typed where an email belongs), <strong>outdated/stale</strong> data (correct once, wrong now), <strong>inaccurate</strong> data (simply wrong), and <strong>incomplete</strong> records (partially filled in). Spotting which category an error falls into is the first step to actually fixing the underlying cause, not just the one instance.</p>
<h2>The 1-10-100 rule</h2>
<p>This is a well-established way of thinking about the real cost of a data error, based on when it's caught: it costs roughly <strong>$1</strong> to prevent an error at the point of entry (a moment's care, a validation check), roughly <strong>$10</strong> to correct it shortly after (someone has to notice and fix it), and roughly <strong>$100</strong> if it's left uncorrected and causes a real failure downstream (a wrong client invoice, a broken report, a decision made on bad data). The lesson isn't the exact numbers — it's that the cost of an error grows dramatically the longer it goes unnoticed, which is exactly why catching things early is worth the small effort it takes.</p>""",
        "Data Quality — Check",
        [
            ("According to the 1-10-100 rule, when is a data error cheapest to deal with?",
             "At the point of entry (~$1) — prevention is dramatically cheaper than fixing it later or living with the consequences.",
             "At the point of entry, before it spreads anywhere", "After it has already caused a downstream failure"),
            ("A phone number typed into an email field is an example of which kind of error?",
             "Invalid format — data entered in a format that doesn't match what the field actually needs.",
             "Invalid format", "Duplicate record"),
            ("Is data quality only Technical's responsibility?",
             "No — anyone entering or passing along data can introduce or catch an error; it's a company-wide habit.",
             "No — it applies company-wide, not just to Technical",
             "Yes — only developers touch data quality"),
        ],
    ),
    (
        "how-we-build-overview",
        "How We Build: Mobile App & Digital Service Delivery (Overview)",
        "A context-setting look at the AI-first delivery model — useful even if you're not technical.",
        """<h2>AI builds scaffolding, humans add intelligence</h2>
<p>The company's delivery approach leans on AI tools to generate the initial scaffolding of a build — the boilerplate, the repetitive structure — so that human time and judgment goes toward the parts that actually require it: real product decisions, catching what doesn't quite fit, and the details a generic AI-generated first pass won't get right on its own.</p>
<h2>The "Nigerian Resilience Test"</h2>
<p>A real, deliberate standard applied to what's built: does it actually hold up under real Nigerian conditions — inconsistent network connectivity, a wide range of device capability, and real cost sensitivity for end users? Something that only works well on a fast connection and a high-end device fails this test, regardless of how polished it looks in a demo.</p>
<h2>Tools in active use</h2>
<p>Claude, GitHub Copilot, Figma's AI features, and Midjourney are all real tools actively used in the build process — not a hypothetical future toolkit.</p>
<h2>Why this matters even if you're not building the product yourself</h2>
<p>Even in a non-technical role, understanding that this is how delivery actually works helps you set realistic expectations with clients and colleagues, and connects directly back to the automation-first philosophy from Course 2.</p>""",
        "How We Build — Check",
        [
            ("What is the \"Nigerian Resilience Test\" checking for?",
             "Whether a build actually holds up under real local conditions — inconsistent network, varied device capability, real cost sensitivity.",
             "Whether it works under real local network/device/cost conditions",
             "Whether it passed automated tests in CI"),
            ("What role does AI play in the build process, per the company's approach?",
             "AI generates the initial scaffolding; humans focus their judgment on the parts that actually need it.",
             "Generates initial scaffolding, freeing humans for the judgment work",
             "Replaces the need for human review entirely"),
            ("Which of these is a real tool actively used in delivery, not a hypothetical?",
             "Claude, GitHub Copilot, Figma AI, and Midjourney are all real, currently-used tools.",
             "GitHub Copilot", "A tool that doesn't exist yet"),
        ],
    ),
    (
        "communication-standards",
        "Communication Standards Across the Company",
        "The actual response-time expectations, by context.",
        """<h2>WhatsApp response times, by lead stage</h2>
<p>Response speed isn't the same for every conversation — it scales with how close a lead is to converting: <strong>MQL — within 4 hours. SQL — within 2 hours. Negotiations — within 1 hour. WON — within 30 minutes.</strong> A prospect actively negotiating gets a faster response than someone who just downloaded a lead magnet, and that's deliberate.</p>
<h2>Social media</h2>
<p>DMs and comments on social channels are expected to get a response within <strong>4 working hours</strong>.</p>
<h2>ICT support</h2>
<p>Internal ICT requests have their own SLA: <strong>critical issues — under 4 hours. Standard requests — under 24 hours.</strong> Know which one your issue actually is before assuming it'll be treated as urgent.</p>
<h2>Client status reporting</h2>
<p>Active client projects get a status report <strong>every Friday</strong> — a standing, weekly cadence, not something sent only when there's a problem to report.</p>""",
        "Communication Standards — Check",
        [
            ("What's the WhatsApp response-time expectation for a lead in the Negotiations stage?",
             "Within 1 hour — response speed scales up as a lead gets closer to WON.",
             "Within 1 hour", "Within 24 hours"),
            ("What's the SLA for a critical ICT support request?",
             "Under 4 hours — standard (non-critical) requests get 24 hours.",
             "Under 4 hours", "Under 1 week"),
            ("How often do active client projects get a status report?",
             "Every Friday — a standing weekly cadence, not only when there's a problem.",
             "Every Friday", "Only when something goes wrong"),
        ],
    ),
    (
        "tools-and-systems",
        "Tools & Systems You'll Use Day to Day",
        "The real tool stack, and the access principle behind who gets what.",
        """<h2>The core stack</h2>
<p>Day to day, the company runs on: <strong>Google Workspace</strong> (email, docs, drive), <strong>WhatsApp Business</strong> (client-facing communication), <strong>Notion and/or Trello</strong> (task/project tracking), <strong>1Password or Bitwarden</strong> (credential management — never share passwords outside these), <strong>Figma and Canva</strong> (design work), and <strong>Claude, ChatGPT, and GitHub Copilot</strong> (the AI tools referenced throughout this whole track, actually in daily use, not aspirational).</p>
<h2>Least-privilege access</h2>
<p>Access to any given system or piece of data is granted based on what a role actually needs to do its job — not given broadly "just in case" it might be useful someday. If you find you have access to something you don't actually need for your role, that's worth flagging, not treating as a convenient bonus.</p>
<h2>Offboarding</h2>
<p>When someone leaves the company, access across these systems is expected to be revoked within <strong>1 hour</strong> of departure — a real, fast security standard, reflecting how seriously access control is treated here.</p>""",
        "Tools & Systems — Check",
        [
            ("Which tool is used specifically for credential/password management?",
             "1Password or Bitwarden — passwords should never be shared outside these.",
             "1Password or Bitwarden", "WhatsApp Business"),
            ("What does \"least-privilege access\" mean in practice?",
             "You get access to what your role actually needs — not broad access granted just in case it's useful someday.",
             "Access is granted based on what your role actually needs",
             "Everyone gets full access to every system by default"),
            ("How quickly is access revoked after someone leaves the company?",
             "Within 1 hour of departure — a fast, deliberate security standard.",
             "Within 1 hour", "Within 30 days"),
        ],
    ),
    (
        "legal-and-regulatory-awareness",
        "Legal & Regulatory Awareness for Every Employee",
        "What every employee should know, even without a legal background.",
        """<h2>A verbal agreement is not a contract</h2>
<p>The company's standard is direct: work does not begin on the strength of a verbal agreement alone. Signed documentation — a contract, a signed SOW, a formal confirmation — is required before real work starts on a client engagement. This protects the company, the client, and you personally from disputes about what was actually agreed.</p>
<h2>IP ownership</h2>
<p>As covered in Course 7: deliverables automatically transfer to the client as their property once delivered, governed by the CSA/SOW that applies to that engagement. This is standard practice, and it's why care with client materials matters throughout a project, not only at the final handoff.</p>
<h2>Regulatory registration — awareness only</h2>
<p>The company holds a SCUML (Special Control Unit Against Money Laundering) registration — part of standard AML (anti-money-laundering) compliance for a Nigerian business of this kind. This course covers it at an awareness level only; it isn't something that changes your day-to-day work, but it's worth knowing the company takes its regulatory obligations seriously.</p>
<h2>An honest note on this course</h2>
<p>This is genuinely the area with the least finished source material of anything in this whole track — there's no complete, dedicated legal/compliance policy document yet. What's here is accurate as far as it goes, but expect this course to expand once the company has written more complete legal and compliance material.</p>""",
        "Legal & Regulatory Awareness — Check",
        [
            ("Can work begin on a client engagement based on a verbal agreement alone?",
             "No — signed documentation is required before real work starts, protecting everyone involved.",
             "No — signed documentation is required first", "Yes, as long as the client sounds committed"),
            ("What does the company's SCUML registration relate to?",
             "AML (anti-money-laundering) compliance — standard regulatory registration for a business of this kind in Nigeria.",
             "Anti-money-laundering (AML) compliance", "Software licensing"),
            ("Who owns a deliverable once it's handed over, per the governing agreement?",
             "The client — per the CSA/SOW, same rule as covered in Course 7.",
             "The client, per the CSA/SOW", "XDDS retains ownership permanently"),
        ],
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds the 15-course General Onboarding track (is_compulsory_staff_training=True, "
        "chained via prerequisite + unlock_delay_days=7) and enrolls every current Group member "
        "in course 1. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="general-onboarding",
            defaults={
                "title": "General Onboarding",
                "audience": Audience.GENERAL,
                "description": "The compulsory sequence every XDDS staff member goes through, regardless of department.",
                "is_active": True,
            },
        )

        previous_course = None
        created_courses = []
        for i, (slug, title, subtitle, body, quiz_title, questions) in enumerate(COURSES, start=1):
            with transaction.atomic():
                course, created = Course.objects.get_or_create(
                    organization=org, programme=programme, slug=slug,
                    defaults={
                        "title": title,
                        "subtitle": subtitle,
                        "audience": Audience.GENERAL,
                        "level": Course.Level.FOUNDATION,
                        "pricing_model": Course.PricingModel.FREE,
                        "access_type": Course.AccessType.LIFETIME,
                        "requires_final_assessment": True,
                        "estimated_hours": 0.5,
                        "is_staff_training": True,
                        "is_compulsory_staff_training": True,
                        "prerequisite": previous_course,
                        "unlock_delay_days": 7 if previous_course else 0,
                        "review_status": Course.ReviewStatus.APPROVED,
                        "is_published": True,
                        "meta_description": f"Course {i} of 15 in XDDS's General Onboarding track."[:160],
                    },
                )
                if not created:
                    self.stdout.write(self.style.WARNING(f"{i}. {course.title} already exists — leaving as-is."))
                else:
                    module = Module.objects.create(
                        course=course, order=1, title=title, unlock_rule=Module.UnlockRule.IMMEDIATE,
                    )
                    Lesson.objects.create(
                        module=module, order=1, title=title, type=Lesson.Type.TEXT,
                        body=body.strip(), is_preview=False,
                    )
                    bank = QuestionBank.objects.create(
                        organization=org, name=f"{quiz_title} — Bank",
                        description=f"Final check for course {i} of the General Onboarding track.",
                    )
                    for stem, explanation, correct, wrong in questions:
                        q = Question.objects.create(
                            bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                            difficulty=Question.Difficulty.EASY,
                        )
                        Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                        Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
                    Quiz.objects.create(
                        scope=Quiz.Scope.FINAL, course=course, title=quiz_title,
                        instructions=f"{len(questions)} questions covering this course.",
                        bank=bank, question_count=len(questions), pass_mark=70,
                        max_attempts=0, time_limit_minutes=0,
                    )
                    self.stdout.write(self.style.SUCCESS(f"{i}. Created: {course.title}"))
                created_courses.append(course)
                previous_course = course

        # Auto-enroll every current Group member (staff) in course 1 —
        # the signal (apps.accounts.signal_receivers) only fires on a
        # NEW group-join going forward; anyone already in a group
        # before this track existed needs a one-time backfill here.
        course1 = created_courses[0]
        staff_user_ids = User.objects.filter(groups__isnull=False).distinct().values_list("id", flat=True)
        enrolled = 0
        for user in User.objects.filter(id__in=staff_user_ids):
            _, was_created = Enrollment.objects.get_or_create(user=user, course=course1)
            if was_created:
                enrolled += 1
                # Same immediate "your training is ready" email the
                # group-join signal sends — a backfilled enrollment
                # deserves the same notice, not silence until Monday.
                from apps.accounts.signal_receivers import _send_welcome_to_training_email
                _send_welcome_to_training_email(user, course1)
        self.stdout.write(self.style.SUCCESS(f"Backfilled {enrolled} existing staff member(s) into course 1."))
        self.stdout.write(self.style.SUCCESS(
            "Done. 15 courses seeded/verified, chained with a 7-day gap after each completion."
        ))
