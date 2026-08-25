from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Third track requested: a comprehensive AI skills course — 11
# modules covering practical AI literacy for a general professional
# audience, from foundational understanding through prompt
# engineering, generative AI, RAG, agents, and responsible use.
# General-audience, not developer-only: concepts are explained in
# plain language with concrete examples, not assuming a programming
# background, while still going deep enough to be genuinely useful to
# someone who DOES code.

MODULES = [
    ("Understanding AI and Large Language Models",
     """<h2>What a large language model actually is</h2>
<p>At its core, a large language model (LLM) is a system trained on enormous amounts of text to predict what word (technically, "token") is most likely to come next, given everything before it. That simple mechanism, at sufficient scale, produces something that can write, reason through problems, summarize, translate, and hold a conversation — not because it "understands" the way a person does, but because predicting language well at scale requires capturing an enormous amount of the structure and knowledge embedded in that language.</p>
<h2>Why this matters practically</h2>
<p>Understanding the prediction mechanism explains both AI's strengths (fluent, contextually appropriate output across almost any topic) and its real limitations: it can produce confident, fluent, and completely wrong statements ("hallucination") because fluency and factual accuracy are not the same thing to a system built to predict plausible next words.</p>
<h2>Training vs. using a model</h2>
<p>"Training" (the enormously expensive process of building the model from data) is distinct from "inference" (using an already-trained model to generate a response to your input) — as a user, you're almost always doing the latter, and understanding this distinction clarifies why a model's knowledge has a cutoff date and doesn't update in real time just from you using it.</p>
<h2>The context window</h2>
<p>A model can only "see" a limited amount of text at once — its context window. Everything relevant to your request needs to fit within that window, which is a foundational constraint that shapes almost every practical technique covered later in this course, especially prompt engineering and RAG.</p>
<h2>Different models, different strengths</h2>
<p>Models vary in size, training data, and specialization — some are optimized for speed and cost, others for reasoning depth, others specifically for code, images, or other modalities. Choosing the right tool for a given task, rather than defaulting to whatever's most familiar, is itself a real skill covered in Module 9.</p>"""),
    ("Prompt Engineering Fundamentals",
     """<h2>Why prompting is a real, learnable skill</h2>
<p>The same underlying model can produce dramatically different quality output depending on how a request is phrased — this isn't a trick or a workaround, it's a direct consequence of how these models generate responses: more context and clarity genuinely produces better predictions.</p>
<h2>Being specific about the task</h2>
<p>Vague requests ("write about marketing") produce vague, generic output. Specific requests (audience, format, length, tone, purpose) produce output that's actually usable without heavy editing. The gap between a mediocre prompt and a good one is almost always specificity, not cleverness.</p>
<h2>Providing context the model doesn't otherwise have</h2>
<p>A model has no knowledge of your specific business, audience, or prior conversation unless you provide it. Including relevant background — even a few sentences — dramatically improves output relevance, and is the single most under-used technique among casual users.</p>
<h2>Assigning a role or persona</h2>
<p>Framing a request as "as an experienced [role], do X" shapes the model's tone, vocabulary, and the kind of considerations it surfaces — a lightweight but genuinely effective technique, especially for professional or technical writing tasks.</p>
<h2>Iterating rather than expecting perfection on the first try</h2>
<p>Treating the first response as a draft, then refining ("make this shorter," "focus more on X," "use simpler language") is how experienced users actually work — prompting is a conversation and a craft, not a single perfect incantation you're expected to get right immediately.</p>"""),
    ("Advanced Prompt Engineering",
     """<h2>Chain-of-thought prompting</h2>
<p>Explicitly asking a model to "think step by step" or show its reasoning before giving a final answer measurably improves accuracy on complex or multi-step problems — the act of generating intermediate reasoning steps genuinely helps the model arrive at better answers, not just explain a fixed answer more clearly.</p>
<h2>Few-shot prompting</h2>
<p>Providing one or more examples of the exact input/output pattern you want, before your actual request, is often far more effective than describing the desired format in the abstract — showing, not just telling, especially for anything with a specific structure (a report format, a tone, a classification scheme).</p>
<h2>Structured output requests</h2>
<p>Explicitly requesting a specific format — a table, numbered list, JSON structure, or specific headings — makes output dramatically easier to actually use downstream, whether that's pasting into a document or feeding into another system.</p>
<h2>Breaking complex tasks into steps</h2>
<p>A single sprawling request often produces a worse result than the same task broken into a sequence of smaller, focused prompts, each building on the last — genuinely complex work (a full report, a multi-part analysis) usually benefits from this decomposition rather than one giant ask.</p>
<h2>Setting explicit constraints</h2>
<p>Telling a model what NOT to do ("don't use jargon," "don't exceed 200 words," "don't include a conclusion section") is just as useful as saying what you want — negative constraints are an underused but genuinely powerful part of the toolkit.</p>"""),
    ("Generative AI for Text and Content Creation",
     """<h2>Where generative AI genuinely helps with writing</h2>
<p>First drafts, restructuring existing content, adapting tone for a different audience, summarizing long material, and overcoming blank-page paralysis are all areas where AI-assisted writing provides real, measurable time savings — used as a collaborator, not a replacement for your own judgment on what's actually worth saying.</p>
<h2>Editing and refining AI output</h2>
<p>Raw AI-generated text usually needs editing for accuracy, voice, and genuine originality — treating the first output as a strong starting draft rather than a finished product is the difference between AI-assisted work that reads well and AI-generated work that reads generic.</p>
<h2>Maintaining a consistent voice</h2>
<p>Providing examples of your own past writing, or a clear style description, helps a model match your actual voice rather than defaulting to a generic "AI-sounding" style that readers increasingly recognize and discount.</p>
<h2>Fact-checking is still your responsibility</h2>
<p>Because of the hallucination risk covered in Module 1, any factual claim, statistic, or citation in AI-generated content needs independent verification before publication — this isn't optional due diligence, it's a hard requirement for responsible use.</p>
<h2>Content workflows worth building</h2>
<p>Using AI for outlining before writing, generating multiple headline/angle options before committing to one, and repurposing one piece of content into multiple formats (a report into a summary, a summary into social posts) are all genuinely efficient, realistic workflows worth adopting deliberately rather than ad hoc.</p>"""),
    ("Generative AI for Images and Multimedia",
     """<h2>How image generation models differ from text models</h2>
<p>Text-to-image models are trained on image/caption pairs rather than pure text, and generate by a different underlying process (commonly diffusion-based) — the practical implication is that prompting for images rewards different techniques than prompting for text, even though some principles (specificity, iteration) carry over.</p>
<h2>Writing effective image prompts</h2>
<p>Describing subject, style, composition, lighting, and mood explicitly produces far more predictable results than a vague description — "a professional photo of a veterinarian examining a dog, natural lighting, shallow depth of field" will consistently outperform "a vet with a dog."</p>
<h2>Iterating on image output</h2>
<p>Most tools let you refine a generated image (adjusting specific elements, regenerating variations, upscaling) rather than starting over — building a workflow of generate, review, refine is far more efficient than trying to nail the perfect prompt on the first attempt.</p>
<h2>Real limitations to know</h2>
<p>Text rendering within images, hands and other fine anatomical detail, and precise factual/technical accuracy (a specific real device, a specific real location) remain genuinely weak points across most current image models — worth planning around rather than being surprised by.</p>
<h2>Licensing and usage rights — a real, not academic, concern</h2>
<p>Different platforms have different terms regarding commercial use, ownership, and whether generated images might resemble copyrighted training material too closely — checking the specific terms of whatever tool you're using before commercial deployment is a genuinely necessary step, not optional caution.</p>"""),
    ("Retrieval-Augmented Generation (RAG) Explained",
     """<h2>The problem RAG solves</h2>
<p>A model's built-in knowledge has a training cutoff and no awareness of your private/internal documents. RAG solves this by retrieving relevant information from an external source (a document set, a database) at the moment of the request, and including it in the model's context — combining the model's language ability with information it was never trained on.</p>
<h2>How RAG actually works, conceptually</h2>
<p>Your documents are broken into chunks and converted into numerical representations (embeddings) that capture meaning, stored in a searchable index (a vector database). When a query comes in, the system finds the most relevant chunks by similarity, and feeds them into the model's context alongside your actual question — the model then answers using that retrieved information, not just its trained-in knowledge.</p>
<h2>Why RAG reduces hallucination</h2>
<p>By grounding the model's answer in retrieved, verifiable source material rather than relying purely on trained-in (and potentially outdated or absent) knowledge, RAG significantly reduces — though doesn't eliminate — the hallucination risk covered in Module 1, especially for domain-specific or private-document questions.</p>
<h2>Where RAG genuinely adds value</h2>
<p>Internal company knowledge bases, customer support over product documentation, research over a specific document set, and any application needing up-to-date or private information a general model was never trained on are the clearest, highest-value RAG use cases.</p>
<h2>RAG's real limitations</h2>
<p>Retrieval quality directly caps answer quality — if the relevant chunk isn't retrieved, the model can't use it, no matter how good the model itself is. Chunking strategy, embedding quality, and retrieval tuning are genuine engineering work, not a solved problem you can ignore once the basic pipeline is running.</p>"""),
    ("AI Agents and Automation",
     """<h2>What makes something an "agent" rather than a chatbot</h2>
<p>A basic chatbot responds to a prompt with text. An agent can take actions — calling tools, running code, browsing the web, updating a database — and often operates in a loop: plan, act, observe the result, and decide the next step, continuing until the task is genuinely complete rather than stopping after one response.</p>
<h2>Tool use as the core agent capability</h2>
<p>Modern agent systems let a model call external "tools" (a calculator, a search function, an API, a database query) when it determines that's needed to complete the task — this is what allows an agent to do things a pure text-generation model fundamentally cannot, like check a real-time price or actually send an email.</p>
<h2>Multi-step task automation</h2>
<p>Agents genuinely shine at tasks with multiple dependent steps — research a topic, then draft a summary, then format it a specific way, then save it — where each step's output feeds the next, without a human manually relaying information between steps.</p>
<h2>Real risks of autonomous agents</h2>
<p>An agent taking real-world actions (sending an email, making a purchase, modifying data) without adequate human oversight is a genuinely different risk category than a chatbot that only produces text — errors compound across steps, and the consequences of a wrong action are real, not just a wrong sentence to be ignored.</p>
<h2>Building trust incrementally</h2>
<p>Starting with agents that draft/recommend actions for human approval, rather than fully autonomous execution, and expanding autonomy only as reliability is genuinely proven, is the responsible, realistic path — not deploying full autonomy on day one because the technology theoretically allows it.</p>"""),
    ("AI for Data Analysis and Decision-Making",
     """<h2>What AI genuinely adds to data work</h2>
<p>Modern AI tools can interpret natural-language questions about data ("what were our top three products by revenue last quarter"), generate the underlying analysis code, explain statistical results in plain language, and spot patterns a manual review might miss — lowering the skill barrier to real data analysis significantly.</p>
<h2>Where human judgment remains essential</h2>
<p>AI can execute an analysis correctly on flawed or misunderstood data and produce a confident, wrong conclusion — understanding your own data's real limitations, biases, and context remains a human responsibility no tool removes, however capable it is.</p>
<h2>Using AI to explore, not just to conclude</h2>
<p>Asking a model to generate multiple possible interpretations of a data pattern, or to suggest what additional data might strengthen or challenge a finding, is often more valuable than asking it for one definitive-sounding conclusion.</p>
<h2>Validating AI-generated analysis</h2>
<p>Spot-checking AI-generated calculations against known values, and understanding at least the general logic of any analysis method used, is a necessary discipline — treating AI-generated numbers with the same unquestioning trust you wouldn't extend to an unverified spreadsheet formula from an unknown source.</p>
<h2>Communicating AI-assisted findings</h2>
<p>Being transparent that AI was used in an analysis, and being able to explain the reasoning in your own words rather than just relaying the tool's output verbatim, maintains the kind of credibility that matters in real business/professional decision-making.</p>"""),
    ("Choosing and Using AI Tools",
     """<h2>The current AI tool landscape, broadly</h2>
<p>General-purpose conversational assistants, specialized writing/image/code tools, and platforms letting you build custom workflows (connecting a model to your own data or tools) each serve different needs — knowing which category actually fits your task avoids both under- and over-tooling a problem.</p>
<h2>Evaluating a tool for your actual use case</h2>
<p>Cost structure (free tier limits, usage-based pricing, subscription), data privacy terms (does your input get used for further training, is it appropriate for sensitive business information), and actual task fit (a tool excellent at code may be mediocre at long-form writing) are the real evaluation criteria — not just which tool is currently most talked about.</p>
<h2>Free vs. paid tiers — what actually changes</h2>
<p>Paid tiers commonly offer more capable underlying models, higher usage limits, and additional features (larger context windows, tool integrations) — worth a genuine cost/benefit evaluation against your actual usage pattern rather than defaulting to free indefinitely or paying for capability you don't use.</p>
<h2>Building a personal or team toolkit</h2>
<p>Most people and teams end up with two or three tools covering different needs (a general assistant, a specialized writing or coding tool, perhaps an image tool) rather than one tool for everything — deliberately building this toolkit, rather than accumulating it randomly, saves real time.</p>
<h2>Staying current without chasing every new release</h2>
<p>This field moves genuinely fast — a practical approach is periodically reassessing your toolkit against your actual needs (quarterly, for most people) rather than either ignoring developments entirely or chasing every new release, which is its own time cost.</p>"""),
    ("AI Ethics, Bias, and Responsible Use",
     """<h2>Where bias in AI actually comes from</h2>
<p>Models learn patterns from their training data — if that data reflects historical human biases (in hiring language, in representation, in whose perspectives are over- or under-represented), the model can reproduce or amplify those biases in its output, often in ways that aren't immediately obvious without deliberate scrutiny.</p>
<h2>Practical steps to reduce biased output</h2>
<p>Reviewing AI-generated content specifically for biased assumptions (not just general quality), testing prompts across varied scenarios to check for inconsistent treatment, and being especially careful in high-stakes uses (hiring, lending, healthcare-adjacent decisions) are concrete, actionable practices, not abstract ideals.</p>
<h2>Privacy considerations</h2>
<p>Entering sensitive personal or business information into a general AI tool may mean that data is stored, logged, or in some cases used for further model training depending on the platform's terms — understanding a tool's actual data policy before entering sensitive information is basic due diligence.</p>
<h2>Transparency and disclosure</h2>
<p>Being honest with clients, employers, or audiences about where AI was used in a piece of work — especially for anything presented as entirely human-created — is both an emerging professional/ethical norm and, in a growing number of contexts, an actual disclosure requirement.</p>
<h2>Environmental and labor considerations</h2>
<p>Training large models has a real computational and environmental cost, and the data used to train them, along with the human labor involved in review/moderation, raises real questions worth being aware of as an informed user — not something a user needs to solve personally, but genuinely worth understanding as part of using this technology responsibly.</p>"""),
    ("Building an AI-Powered Workflow",
     """<h2>From individual tricks to an actual workflow</h2>
<p>The real value of everything in this course compounds when specific techniques are combined into a repeatable workflow for a real, recurring task — not scattered one-off uses of AI, which capture only a fraction of the possible value.</p>
<h2>Mapping your own repetitive tasks</h2>
<p>Identifying tasks you do repeatedly — a weekly report, recurring customer responses, content creation with a consistent format — is the starting point for building genuine AI-assisted workflows, rather than trying to "use AI more" without a specific target.</p>
<h2>Designing a workflow, step by step</h2>
<p>A real workflow typically combines several techniques from this course: a well-crafted prompt template (Modules 2-3) with consistent structure, retrieval of relevant background information where needed (Module 6's RAG concepts), and a clear human-review step before anything goes out the door.</p>
<h2>Measuring whether it's actually working</h2>
<p>Tracking real time saved, quality of output (are you editing heavily or lightly), and whether the workflow is actually being used consistently (versus abandoned after the novelty wears off) turns "we use AI for this" from a vague claim into something you can genuinely evaluate and improve.</p>
<h2>A closing framework for using AI well</h2>
<p>Across every module in this course, one theme repeats: AI is a genuinely powerful collaborator that dramatically accelerates specific kinds of work, but human judgment, verification, and accountability remain non-negotiable — the goal isn't replacing your judgment, it's freeing more of your time and attention for the judgment calls that actually need you.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    ("Why can a large language model produce a fluent, confident, but factually wrong statement (a \"hallucination\")?",
     "The model is fundamentally built to predict plausible next words based on patterns, not to verify facts — fluency and factual accuracy are not the same thing to a system built this way.",
     "Because it's built to predict plausible language, not to verify facts — fluency isn't the same as accuracy",
     "Hallucination only happens due to a technical malfunction and is otherwise entirely preventable"),
    ("What's usually the biggest single factor separating a mediocre prompt from a genuinely good one?",
     "Specificity — vague requests produce vague output, while specific detail about task, audience, format, and tone produces usable results.",
     "Specificity about the task, audience, format, and tone, rather than cleverness or trickery",
     "Using unusual or clever wording that most users wouldn't think to try"),
    ("Why does chain-of-thought prompting (\"think step by step\") measurably improve accuracy on complex problems?",
     "Generating intermediate reasoning steps genuinely helps the model arrive at a better answer, not just explain a fixed answer more clearly.",
     "The act of generating intermediate reasoning steps genuinely improves how the model arrives at its answer",
     "It has no real effect on accuracy and only makes responses longer"),
    ("Why does RAG (retrieval-augmented generation) reduce hallucination risk compared to relying on a model's trained-in knowledge alone?",
     "It grounds the model's answer in retrieved, verifiable source material rather than purely trained-in (and potentially outdated or absent) knowledge.",
     "It grounds answers in retrieved, verifiable source material instead of only trained-in knowledge",
     "RAG completely eliminates hallucination risk with no remaining limitations"),
    ("What fundamentally distinguishes an AI \"agent\" from a basic chatbot?",
     "An agent can take real actions via tools (calling APIs, running code, browsing) in a plan-act-observe loop, not just respond with text to a single prompt.",
     "An agent can take real actions using tools, operating in a loop, not just generate a single text response",
     "There's no real technical difference — the terms are interchangeable"),
    ("Why should AI-generated data analysis still be spot-checked against known values?",
     "AI can execute an analysis correctly on flawed or misunderstood data and produce a confident, wrong conclusion — validation remains a human responsibility.",
     "AI can confidently produce a wrong conclusion from flawed or misunderstood data — validation is still necessary",
     "AI-generated analysis is inherently self-verifying and never requires independent checking"),
    ("Where does bias in AI model output typically originate from?",
     "Models learn patterns from their training data — if that data reflects historical human biases, the model can reproduce or amplify them in its output.",
     "It's learned from patterns in training data, which can reflect and reproduce historical human biases",
     "AI models are inherently neutral and bias only comes from how a user phrases a prompt"),
    ("Why does the course frame effective AI use as building repeatable workflows rather than scattered one-off uses?",
     "Combining specific techniques into a repeatable workflow for a real recurring task captures far more compounding value than isolated, ad hoc uses.",
     "A repeatable workflow for a recurring task captures much more value than scattered individual uses",
     "There's no real difference in value between a structured workflow and occasional one-off use"),
]


class Command(BaseCommand):
    help = (
        "Seeds 'AI Skills for Professionals' — an 11-module comprehensive AI "
        "literacy course covering LLMs, prompt engineering, generative AI, RAG, "
        "agents, data analysis, tool selection, ethics, and workflow-building. "
        "Real written content, general-audience. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="ai-skills",
            defaults={
                "title": "AI Skills",
                "audience": Audience.GENERAL,
                "description": "Practical AI literacy courses for professionals — no programming background assumed.",
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="ai-skills-for-professionals",
                defaults={
                    "title": "AI Skills for Professionals",
                    "subtitle": "11 modules covering everything from how LLMs actually work to prompt engineering, "
                                 "generative AI, RAG, agents, and building real AI-powered workflows.",
                    "description": "<p>A comprehensive, general-audience AI literacy course — no programming "
                                    "background assumed. Covers how large language models actually work, prompt "
                                    "engineering (fundamentals through advanced techniques), generative AI for text "
                                    "and images, retrieval-augmented generation, AI agents and automation, AI-assisted "
                                    "data analysis, choosing the right tools, responsible/ethical use, and building "
                                    "real repeatable AI-powered workflows.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 9000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 6.0,
                    "is_published": False,
                    "sales_headline": "11 real AI skills, not 11 ways to say \"just use ChatGPT\"",
                    "sales_subheadline": "From how large language models actually work through prompt engineering, "
                                          "generative AI, RAG, agents, and building workflows that actually stick.",
                    "target_audience": (
                        "Professionals and business owners who want to use AI well, not just occasionally\n"
                        "Anyone who's used AI tools casually but wants to actually understand what they're doing\n"
                        "No programming background required — concepts are explained in plain language throughout"
                    ),
                    "not_for": (
                        "Anyone looking for a deep technical/coding course on building AI models from scratch — "
                        "this is a practical-use and literacy course, not a machine-learning engineering course"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, Founder, Xpress Digital & Data Solutions Limited.",
                    "meta_description": "A comprehensive, no-code-required AI skills course — prompt engineering, "
                                         "generative AI, RAG, agents, and real workflows.",
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
                organization=org, name="AI Skills for Professionals — Final Exam",
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
                scope=Quiz.Scope.FINAL, course=course, title="Final Exam — AI Skills for Professionals",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin."
        ))
