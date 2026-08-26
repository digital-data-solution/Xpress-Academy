from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# AI Skills for Professionals launched Foundation-only. Per explicit
# instruction, every Foundation-only line needs Intermediate and
# Advanced tiers under it, gated by prerequisite.

INTERMEDIATE_MODULES = [
    ("Building Reusable Prompt Systems",
     """<h2>From one-off prompts to reusable templates</h2>
<p>A prompt written once and reused, with clearly marked variables for the parts that change (audience, topic, format), turns a one-time trick into a repeatable asset — the practical difference between someone who "uses AI sometimes" and someone who's actually built a system around it.</p>
<h2>Prompt libraries — worth building deliberately</h2>
<p>Keeping a working set of proven prompt templates for recurring tasks (drafting a report, summarizing a document, generating options) saves real time and avoids re-solving the same prompting problem every time — a genuinely underused practice.</p>
<h2>Version-controlling your prompts</h2>
<p>Treating a prompt template like any other reusable asset — noting what changed and why when you improve it — means improvements compound instead of being lost the next time you're in a hurry and just wing it.</p>
<h2>Sharing prompt systems across a team</h2>
<p>A documented, shared prompt library means a whole team benefits from one person's refinement, rather than everyone separately rediscovering the same techniques — a real, practical way AI literacy compounds at an organizational level, not just individually.</p>"""),
    ("Working With Documents and Long Context",
     """<h2>Getting long documents into a model usefully</h2>
<p>Pasting an entire long document rarely produces the best result — providing a clear instruction about what to extract or do with the content, and being aware of context-window limits (Course 1's foundational concept), shapes a genuinely more useful response.</p>
<h2>Summarization strategies that actually work</h2>
<p>Asking for a structured summary (key points, decisions, open questions) rather than a generic paragraph produces something actually usable in a professional context — the specificity principle from prompt engineering, applied to a very common real task.</p>
<h2>Extracting structured information from unstructured text</h2>
<p>Asking a model to pull specific fields (dates, names, action items) out of messy text into a clean list or table is one of the most immediately useful, underused applications for anyone dealing with reports, emails, or notes regularly.</p>
<h2>Cross-referencing multiple documents</h2>
<p>Providing several documents and asking for a comparison, contradiction check, or synthesis is a genuinely advanced but achievable technique — most valuable exactly where doing it manually would take real time.</p>"""),
    ("AI-Assisted Research and Fact-Finding",
     """<h2>Using AI as a research starting point, not an endpoint</h2>
<p>A model can rapidly generate an overview, suggest angles, or surface terminology you didn't know to search for — genuinely valuable as a starting point, provided every specific factual claim is still independently verified before being relied upon (Course 1's hallucination risk, applied practically here).</p>
<h2>Asking for sources and how to treat them</h2>
<p>Requesting sources or reasoning behind a claim is useful, but a model can also generate plausible-sounding but fabricated citations — treating any AI-provided source as a lead to verify, not a citation to trust outright, is non-negotiable due diligence.</p>
<h2>Comparative and multi-perspective research</h2>
<p>Asking a model to lay out multiple genuine perspectives on a genuinely contested question, rather than one confident answer, often produces more useful research output than seeking a single "correct" answer to something that doesn't have one.</p>
<h2>Building a research workflow around AI</h2>
<p>Using AI for the broad initial pass, then human verification and deep-diving on the parts that actually matter, is a realistic, efficient division of labor — not "AI does the research" or "AI is useless for research," but a genuine partnership with clear boundaries.</p>"""),
    ("AI for Presentations and Communication",
     """<h2>Structuring a presentation with AI assistance</h2>
<p>Asking for an outline first, then iterating slide by slide, produces a far better result than asking for "a full presentation" in one shot — the same decomposition principle from Course 1's advanced prompting, applied to a specific, common professional task.</p>
<h2>Adapting one message for different audiences</h2>
<p>The same underlying content — a project update, a proposal — often needs different framing for executives, technical peers, or clients; asking a model to adapt tone and emphasis for each specific audience is a fast, genuinely useful technique.</p>
<h2>Practicing difficult conversations</h2>
<p>Using AI to roleplay a difficult conversation (a negotiation, delivering hard feedback) before having it for real is an underused but genuinely effective way to prepare — not a replacement for the real conversation, a rehearsal for it.</p>
<h2>Knowing when NOT to let AI write the final version</h2>
<p>High-stakes, deeply personal, or relationship-sensitive communication (a genuine apology, a resignation, a sensitive HR matter) should be written or at minimum heavily rewritten in your own authentic voice — this is a judgment call worth making deliberately, not by default.</p>"""),
    ("Measuring Your Own AI-Assisted Productivity",
     """<h2>Why "I use AI a lot" isn't a useful measure</h2>
<p>Usage frequency doesn't tell you whether AI use is actually saving time or just feeling productive — tracking real outcomes (time saved on a specific recurring task, quality of output before heavy editing) is what turns a vague impression into something you can actually improve.</p>
<h2>A simple way to track real time savings</h2>
<p>Comparing how long a specific recurring task took before and after building an AI-assisted workflow for it (Course 1's closing module) gives a concrete, honest number — often surprising in either direction, and worth actually measuring rather than assuming.</p>
<h2>Recognizing when AI assistance isn't actually helping</h2>
<p>If a task consistently needs so much editing/correction that it would have been faster to just do it yourself, that's a genuine signal to change the approach (a different prompt, a different tool, or simply doing it manually) — not a reason to feel like you're using AI wrong.</p>
<h2>Building toward genuine fluency, not just familiarity</h2>
<p>The gap between someone who occasionally uses AI tools and someone genuinely fluent with them is exactly the systems, workflows, and measurement habits this Intermediate tier covers — the foundation for the strategic and technical depth in the Advanced tier.</p>"""),
]

INTERMEDIATE_EXAM = [
    ("What's the practical benefit of a reusable prompt template over writing a fresh prompt every time?",
     "A template with marked variables turns a one-time trick into a repeatable, improvable asset rather than re-solving the same prompting problem repeatedly.",
     "It turns a one-off prompt into a repeatable, improvable asset instead of starting from scratch each time",
     "Reusable templates only matter for developers writing code, not for general professional use"),
    ("Why should extracted \"sources\" or citations from an AI response always be independently verified?",
     "A model can generate plausible-sounding but fabricated citations — an AI-provided source is a lead to verify, not a citation to trust outright.",
     "Because a model can generate plausible but fabricated citations, so any source needs independent verification",
     "AI-generated citations are cryptographically verified and therefore inherently trustworthy"),
    ("Why does asking for an outline first, before generating a full presentation in one shot, usually produce a better result?",
     "It applies the decomposition principle — breaking a complex task into steps produces better results than one large, sprawling request.",
     "It applies task decomposition — breaking the work into steps produces a better result than one large request",
     "Outlines are only useful for very long presentations, not for shorter ones"),
    ("Why does the course recommend heavily rewriting or personally writing high-stakes, relationship-sensitive communication rather than using raw AI output?",
     "That category of communication (a genuine apology, sensitive HR matters) calls for an authentic voice — a deliberate judgment call, not an automatic default.",
     "High-stakes, relationship-sensitive messages call for an authentic voice — a deliberate choice, not automatic AI use",
     "AI-generated communication is always inappropriate for any professional context regardless of stakes"),
    ("Why is tracking real time saved on a specific recurring task a better measure than \"how often you use AI\"?",
     "Usage frequency doesn't reveal whether AI use is actually saving time versus just feeling productive — concrete before/after comparison gives an honest answer.",
     "Frequency doesn't show real impact — a concrete before/after time comparison gives an honest, actionable answer",
     "There is no meaningful way to measure whether AI assistance is actually improving productivity"),
]

ADVANCED_MODULES = [
    ("Designing AI Strategy for a Team or Organization",
     """<h2>Moving from individual use to organizational capability</h2>
<p>An organization where a few people use AI well but most don't has a fraction of the potential value of one with a deliberate rollout — genuine organizational AI strategy is about capability-building, not just tool procurement.</p>
<h2>Identifying high-value use cases, not just easy ones</h2>
<p>The most impactful AI adoption targets recurring, high-volume, or high-cost tasks — not necessarily the flashiest demo use case; a structured audit of where time and money actually go is worth doing before picking pilot projects.</p>
<h2>Change management — the real bottleneck</h2>
<p>Technical capability is rarely the limiting factor in organizational AI adoption; genuine behavior change, trust-building, and overcoming skepticism or fear (including reasonable job-security concerns) usually is — treating this as a real project, not an afterthought, determines whether adoption actually sticks.</p>
<h2>Governance — policy before problems, not after</h2>
<p>A clear, written policy on acceptable use (what data can go into which tools, disclosure expectations, review requirements for client-facing output) prevents real problems rather than reacting after an incident — the earlier this exists, the less painful it is to establish.</p>"""),
    ("Advanced Prompt Systems and Tool Integration",
     """<h2>Chaining prompts into multi-step pipelines</h2>
<p>Connecting the output of one prompt as the input to the next — research, then draft, then review, then format — builds genuinely more capable systems than any single prompt could produce alone, applying Intermediate's reusable-template thinking at a systems level.</p>
<h2>Connecting AI to real data and tools</h2>
<p>Tools and integrations that let a model query a real database, call an API, or read a live document move well beyond static prompting into genuinely dynamic, current-data-aware systems — the practical foundation for the agent concepts introduced at Foundation level.</p>
<h2>Designing for reliability, not just capability</h2>
<p>A system that works in demos but fails unpredictably in production is a common trap — building in validation steps, fallback behavior, and human checkpoints at the right points is what separates a genuinely reliable system from an impressive but fragile one.</p>
<h2>Evaluating whether a system is actually worth building</h2>
<p>Not every repetitive task justifies a multi-step AI system — honestly weighing build/maintenance cost against the actual value delivered avoids the common failure mode of over-engineering a solution to a problem that a simple prompt template would have solved.</p>"""),
    ("Data Privacy, Security, and Compliance at Scale",
     """<h2>Where organizational AI use creates real exposure</h2>
<p>Client data, proprietary business information, and personal data entered into third-party AI tools carry real privacy and confidentiality risk depending on that tool's actual data-handling terms — this is a materially bigger concern at organizational scale than for individual casual use.</p>
<h2>Vendor evaluation from a compliance standpoint</h2>
<p>Understanding a vendor's data retention policy, whether inputs are used for further model training, and where data is actually processed and stored are the real questions to ask before an organization adopts a tool at scale — not just capability and price.</p>
<h2>NDPR and Nigerian-specific compliance considerations</h2>
<p>Processing Nigerian users' personal data through AI tools carries the same NDPR obligations as any other data processing — an organization's AI adoption plan needs to account for this explicitly, not assume general AI enthusiasm exempts it from existing data-protection law.</p>
<h2>Building a practical, enforceable compliance approach</h2>
<p>A short, clear, actually-followed policy beats an exhaustive one nobody reads — practical enforceability is the real design goal, not comprehensive theoretical coverage that has no real effect on daily behavior.</p>"""),
    ("Leading AI Adoption and Training Others",
     """<h2>Why "just start using it" doesn't scale as a training approach</h2>
<p>Structured onboarding — worked examples, common early mistakes, a clear internal resource for questions — produces meaningfully better organizational adoption than expecting people to independently discover effective use, particularly for less naturally tech-forward team members.</p>
<h2>Meeting people at their actual starting point</h2>
<p>A skeptical or anxious colleague needs a genuinely different introduction than an enthusiastic early adopter — tailoring the training approach to where someone actually is, rather than a one-size-fits-all rollout, meaningfully improves real adoption rates.</p>
<h2>Creating internal champions</h2>
<p>Identifying and supporting a few genuinely engaged early adopters who can informally help colleagues often does more for real organizational adoption than formal training sessions alone — peer influence is a real, underused lever.</p>
<h2>Sustaining adoption past the initial rollout</h2>
<p>Interest and usage often dip after an initial push unless there's ongoing reinforcement — periodic check-ins, sharing new use cases, and visibly updating tools/policy as the field moves keep adoption genuinely alive rather than fading into occasional, inconsistent use.</p>"""),
]

ADVANCED_EXAM = [
    ("Why is organizational AI strategy described as being about capability-building rather than just tool procurement?",
     "An organization where only a few people use AI well captures a fraction of the potential value compared to a deliberate, structured rollout — genuine strategy builds broad capability, not just access.",
     "Broad capability-building captures far more value than simply giving people access to tools",
     "Organizational AI strategy is primarily about selecting which vendor to purchase licenses from"),
    ("According to the course, what's usually the real bottleneck in organizational AI adoption — technical capability, or something else?",
     "Genuine behavior change, trust-building, and overcoming skepticism or reasonable job-security concerns are usually the real bottleneck, not technical capability.",
     "Change management — behavior change and trust-building — is usually the real limiting factor, not the technology itself",
     "Technical capability and tool availability are always the primary bottleneck in adoption"),
    ("Why should AI-use policy exist before an incident happens, not after?",
     "A clear, written policy on acceptable use prevents real problems rather than reacting after something has already gone wrong — earlier is meaningfully less painful to establish.",
     "Establishing policy proactively prevents real problems, which is far less painful than reacting after an incident",
     "Policy only becomes necessary once an actual data or compliance incident has already occurred"),
    ("Why does processing Nigerian users' data through third-party AI tools still require NDPR compliance?",
     "The same NDPR obligations apply to any processing of personal data — general enthusiasm about AI doesn't exempt an organization from existing data-protection law.",
     "NDPR obligations apply regardless of the tool used — AI adoption doesn't create an exemption from existing law",
     "NDPR only applies to traditional databases and does not cover data processed through AI tools"),
    ("Why does the course recommend tailoring AI training/onboarding to where each person actually starts, rather than one-size-fits-all?",
     "A skeptical or anxious colleague needs a genuinely different introduction than an enthusiastic early adopter — matching the approach meaningfully improves real adoption.",
     "Different starting points (skeptical vs. enthusiastic) need different approaches to meaningfully improve real adoption",
     "Training should always be identical for everyone to ensure fairness across the organization"),
]


class Command(BaseCommand):
    help = (
        "Seeds the Intermediate and Advanced tiers under AI Skills for "
        "Professionals, gated behind the existing Foundation course. "
        "Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme = Programme.objects.filter(slug="ai-skills").first()
        foundation = Course.objects.filter(slug="ai-skills-for-professionals").first()
        if not programme or not foundation:
            self.stderr.write(self.style.ERROR("Run seed_ai_skills_course first."))
            return

        with transaction.atomic():
            intermediate, _ = self._make_course(
                org, programme, slug="ai-skills-intermediate",
                title="AI Skills — Applied Practice",
                subtitle="Reusable prompt systems, working with long documents, AI-assisted research, and "
                         "measuring your own productivity gains — building fluency beyond the basics.",
                description="<p>A 5-module intermediate course building on AI Skills for Professionals: "
                            "reusable prompt systems, working with documents and long context, AI-assisted "
                            "research and fact-finding, AI for presentations and communication, and measuring "
                            "your own AI-assisted productivity.</p>",
                level=Course.Level.INTERMEDIATE, price_ngn=7000, prerequisite=foundation,
                modules=INTERMEDIATE_MODULES, exam_questions=INTERMEDIATE_EXAM,
                exam_title="Final Exam — AI Skills Intermediate",
            )
            self._make_course(
                org, programme, slug="ai-skills-advanced",
                title="AI Skills — Strategy and Leadership",
                subtitle="Designing AI strategy for a team, advanced prompt systems, compliance at scale, "
                         "and leading adoption — for anyone driving AI use beyond their own desk.",
                description="<p>A 4-module advanced course: designing AI strategy for a team or organization, "
                            "advanced prompt systems and tool integration, data privacy/security/compliance "
                            "at scale (including NDPR), and leading AI adoption and training others.</p>",
                level=Course.Level.ADVANCED, price_ngn=10000, prerequisite=intermediate,
                modules=ADVANCED_MODULES, exam_questions=ADVANCED_EXAM,
                exam_title="Final Exam — AI Skills Advanced",
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
