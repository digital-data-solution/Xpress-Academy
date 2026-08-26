from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Programme
from apps.organizations.models import Organization

# Canine Reproduction for Practitioners launched Advanced-only. Per
# explicit instruction, every Advanced-tier line needs a Foundation and
# Intermediate under it, gated by prerequisite. This builds the two
# missing tiers and gates the existing Advanced course behind the new
# Intermediate — same PricingModel.PAID / prerequisite chain pattern as
# Practical Dog Breeding and the poultry series.

FOUNDATION_MODULES = [
    ("Canine Reproductive Anatomy and Physiology",
     """<h2>The bitch's reproductive cycle, structurally</h2>
<p>Anoestrus, proestrus, oestrus, and dioestrus are distinct hormonal and physiological phases, not just behavioral labels — proestrus and oestrus are driven by rising then peaking oestrogen with the LH surge marking ovulation's approach, while dioestrus is a progesterone-dominated phase whether or not pregnancy occurs, a distinction that explains several clinical presentations covered later in this course.</p>
<h2>The dog's reproductive anatomy in practical terms</h2>
<p>Understanding the ovaries, uterine horns, cervix, and vagina's normal appearance and position is the baseline every diagnostic technique in this track — palpation, ultrasound, vaginal cytology — is interpreted against; an abnormal finding only means something once the normal range is genuinely internalized, not just memorized for an exam.</p>
<h2>The stud dog's reproductive anatomy</h2>
<p>Testicular function, epididymal sperm maturation, and prostatic contribution to the ejaculate are the structural basis for everything in semen evaluation (Intermediate tier) — a testicle that looks normal on palpation but has abnormal spermatogenesis is a real, common presentation this anatomy explains.</p>
<h2>Why this foundation matters clinically</h2>
<p>Most reproductive consultations — "is she pregnant," "when should we breed," "why didn't she conceive" — are ultimately anatomy and physiology questions in disguise. A practitioner who can reason from first principles handles the unusual case; one who only knows protocols gets stuck the moment a case doesn't fit the standard pattern.</p>"""),
    ("The Estrous Cycle — Staging and Clinical Relevance",
     """<h2>Vaginal cytology as a staging tool</h2>
<p>The shift from parabasal/intermediate cells toward superficial cornified cells tracks rising oestrogen through proestrus into oestrus, and the sharp drop-off at the onset of dioestrus is one of the most practical, low-cost staging tools available in general practice — genuinely useful before more advanced hormonal timing is warranted.</p>
<h2>Behavioral signs — useful, but not sufficient alone</h2>
<p>Standing to be mounted, tail deviation, and vulvar changes are real signals owners rely on, but behavioral receptivity doesn't perfectly align with the fertile window — treating owner-reported behavior as one data point among several, not the sole basis for a breeding decision, avoids a common source of missed timing.</p>
<h2>Why "she's in season" isn't a diagnosis</h2>
<p>Silent heats, split heats, and prolonged proestrus are all real variations a practitioner needs to recognize rather than assume every bitch presents with the textbook 9-day proestrus/9-day oestrus pattern — atypical cycling is common enough that it shouldn't be treated as exotic.</p>
<h2>Setting up for what's next</h2>
<p>Everything in Intermediate's progesterone-timing module builds directly on accurately staging where in the cycle a bitch currently sits — a practitioner who can't stage a cycle by cytology and history will struggle to interpret a progesterone value in context.</p>"""),
    ("The Breeding Soundness Examination",
     """<h2>What a breeding soundness exam actually screens for</h2>
<p>A systematic BSE — history, general physical, reproductive-specific physical exam, and (for the male) semen evaluation — is meant to catch problems before they cost a breeding season, not just confirm the obviously fertile animal is fertile; the real value is in what it catches early.</p>
<h2>History-taking that actually helps</h2>
<p>Prior litter sizes, cycle regularity, previous breeding outcomes, and any past reproductive treatment are frequently more diagnostically useful than the physical exam alone — a thorough history often narrows the differential before a single test is run.</p>
<h2>The female-specific exam</h2>
<p>Vulvar conformation, vaginal exam findings, and abdominal palpation each screen for different classes of problems (conformational, infectious/inflammatory, structural) — a BSE that skips any one of these leaves a real gap.</p>
<h2>The male-specific exam</h2>
<p>Testicular size, symmetry, consistency, and scrotal circumference correlate with sperm production — an abnormal finding here is the trigger for the semen evaluation covered at Intermediate level, not something to defer indefinitely.</p>
<h2>Documenting a BSE properly</h2>
<p>A written, dated BSE record protects the practitioner and gives the client (and any future vet) a real baseline to compare against — an undocumented exam is, from a liability and continuity-of-care standpoint, close to not having happened at all.</p>"""),
    ("Basic Pregnancy Diagnosis and Monitoring",
     """<h2>Abdominal palpation — useful window, real limits</h2>
<p>Palpation can detect pregnancy in a fairly narrow window (roughly days 21-35 post-ovulation, patient-dependent) and is highly operator-dependent — a negative palpation outside that window, or in an obese or tense patient, is not reliable evidence of a non-pregnant status.</p>
<h2>Ultrasound as the practical gold standard for confirmation</h2>
<p>Ultrasound can confirm pregnancy earlier and more reliably than palpation, and — critically — can assess fetal viability via heartbeat, which palpation cannot do at all; a practice offering breeding services without ultrasound access is offering an incomplete service.</p>
<h2>Radiography's specific, later-stage role</h2>
<p>Radiographs are the practical tool for counting fetuses (via skeletal mineralization, visible from roughly day 45 onward) — useful for whelping preparation and c-section planning, not for early pregnancy confirmation, which is a common point of client confusion worth addressing directly.</p>
<h2>What monitoring through gestation actually looks for</h2>
<p>Serial checks watch for maternal health changes, appropriate fetal growth, and early warning signs of complications — pregnancy monitoring isn't a single confirmation event, it's an ongoing responsibility through to whelping, and framing it that way to clients sets correct expectations.</p>"""),
    ("Normal Parturition and Whelping Basics",
     """<h2>The three stages of normal labor</h2>
<p>Stage 1 (behavioral changes, nesting, no visible straining), Stage 2 (active straining and delivery), and Stage 3 (placental passage) each have a normal expected timeline — knowing these cold is what lets a practitioner recognize a deviation quickly rather than second-guessing whether something is actually wrong.</p>
<h2>What "normal" actually looks like</h2>
<p>Puppies typically arrive at intervals of 30-60 minutes with real variation, though prolonged unproductive straining beyond a reasonable window is the single most important trigger point covered in Intermediate's dystocia-recognition module — this Foundation module sets the baseline that abnormal is measured against.</p>
<h2>The practitioner's role in a normal whelping</h2>
<p>Most normal whelpings need no direct intervention — but being available for phone guidance, knowing when a breeder should actually come in, and having pre-established expectations set with the client beforehand meaningfully reduces both anxiety and the odds of a truly urgent case arriving too late.</p>
<h2>Basic neonatal care right after birth</h2>
<p>Clearing airways, stimulating breathing, umbilical care, and ensuring early nursing are basic, teachable steps every breeding client should already know before whelping day — a practitioner who proactively covers this reduces genuine emergencies, not just answers questions after the fact.</p>"""),
    ("Client Communication in Breeding Practice",
     """<h2>Setting expectations before, not during, a crisis</h2>
<p>A breeder who's been walked through what normal whelping looks like, what warning signs mean "call now," and roughly what a c-section might cost, makes better decisions under real pressure than one improvising for the first time during an actual emergency.</p>
<h2>The economics conversation, done honestly</h2>
<p>Reproductive work carries real cost — ultrasounds, progesterone testing, potential emergency c-sections — and having a straightforward conversation about likely costs before a breeding season starts avoids the much harder conversation mid-emergency, when a client is stressed and a decision needs to be made quickly.</p>
<h2>Building a genuine breeding-service relationship</h2>
<p>Clients who return for every litter, every year, are built through consistent availability and clear communication over a single transaction — treating reproductive work as an ongoing relationship rather than a series of one-off appointments is what makes it a real, sustainable part of a practice.</p>"""),
]

FOUNDATION_EXAM = [
    ("What distinguishes dioestrus from anoestrus hormonally, regardless of whether pregnancy occurred?",
     "Dioestrus is progesterone-dominated whether or not pregnancy occurs, while anoestrus is a period of reproductive quiescence with low sex-steroid activity.",
     "Dioestrus is progesterone-dominated regardless of pregnancy; anoestrus is quiescent with low hormone activity",
     "The two phases are hormonally identical and differ only in a bitch's outward behavior"),
    ("Why is behavioral receptivity alone an insufficient basis for a breeding-timing decision?",
     "Behavioral receptivity doesn't perfectly align with the actual fertile window — it's one data point, not sufficient on its own.",
     "It doesn't reliably align with the fertile window, so it should be one signal among several, not the sole basis",
     "Behavioral receptivity is actually the single most reliable timing indicator available"),
    ("Why does a negative abdominal palpation NOT reliably rule out pregnancy?",
     "Palpation only works in a fairly narrow window and is highly operator- and patient-dependent — a negative outside that window or in a difficult patient isn't reliable evidence.",
     "It's operator- and window-dependent — a negative result outside the reliable window doesn't rule pregnancy out",
     "A negative palpation at any stage of gestation reliably confirms the bitch is not pregnant"),
    ("What is radiography's specific, practical role in a normal canine pregnancy, and when does it apply?",
     "Counting fetuses via skeletal mineralization, useful from roughly day 45 onward for whelping/c-section planning — not for early pregnancy confirmation.",
     "Counting fetuses from about day 45 onward for whelping planning, not for confirming pregnancy early",
     "Radiography is the earliest and most reliable method for confirming pregnancy in the first two weeks"),
    ("Why does the course recommend setting cost and warning-sign expectations with breeding clients before a breeding season, not during a crisis?",
     "A client who already understands normal whelping, warning signs, and likely costs makes better decisions under real pressure than one improvising for the first time mid-emergency.",
     "Pre-set expectations lead to better real-time decisions than a client improvising during an actual emergency",
     "Cost and warning-sign conversations are best avoided until they become directly relevant to a specific case"),
]

INTERMEDIATE_MODULES = [
    ("Semen Collection and Evaluation Fundamentals",
     """<h2>Collection technique, briefly</h2>
<p>Digital manipulation with a teaser bitch present (or a reliable substitute stimulus) is the standard collection method in general practice — a calm, unhurried approach genuinely affects both collection success and semen quality, not just practitioner comfort.</p>
<h2>What a basic semen evaluation actually assesses</h2>
<p>Volume, concentration, motility (both progressive and total), and morphology are the four pillars — each screens for a different category of problem, and a normal result in one doesn't substitute for checking the others.</p>
<h2>Interpreting results in context, not isolation</h2>
<p>A single poor semen evaluation can reflect a genuinely subfertile dog, or simply recent overuse, illness, heat stress, or a rushed/stressed collection — recommending a repeat evaluation under better conditions before declaring a dog subfertile is standard, responsible practice.</p>
<h2>When a finding warrants Advanced-tier referral or workup</h2>
<p>Consistently poor results across repeated, well-conducted evaluations are the trigger for the deeper infertility workup covered in the Advanced tier — this module's job is recognizing that threshold, not performing the full advanced workup itself.</p>"""),
    ("Progesterone Timing and Ovulation Prediction",
     """<h2>Why progesterone timing outperforms day-counting</h2>
<p>Individual bitches show real variation in when ovulation actually occurs relative to the start of proestrus — serial progesterone measurement tracks the bitch's own actual physiology rather than assuming a textbook-average cycle, which is exactly why it's become the practical standard for planned breedings.</p>
<h2>Reading a progesterone trend, not a single number</h2>
<p>A single progesterone value is far less useful than a trend across serial measurements — the rate of rise is what actually identifies the optimal breeding window, not one isolated data point interpreted alone.</p>
<h2>Combining progesterone with cytology</h2>
<p>Vaginal cytology (Foundation tier) and progesterone timing are complementary, not redundant — cytology gives a broad-strokes cycle stage cheaply, while progesterone gives the precision needed for a planned breeding, particularly with frozen or shipped semen where timing tolerance is small.</p>
<h2>Practical scheduling around a progesterone protocol</h2>
<p>Building a realistic testing schedule (typically every 1-2 days as the rise begins) that a client can actually commit to matters as much as the underlying science — a protocol nobody follows accurately produces worse outcomes than a simpler one that's actually executed correctly.</p>"""),
    ("Recognizing Common Infertility Presentations",
     """<h2>The most common reasons a "normal" breeding doesn't produce a litter</h2>
<p>Mistimed breeding (the single most common cause), subclinical infection, luteal insufficiency, and male-factor issues account for the large majority of infertility presentations — working through this list roughly in order of likelihood, before jumping to rare causes, is efficient, responsible diagnostic reasoning.</p>
<h2>When to suspect mistiming vs. a genuine fertility problem</h2>
<p>A single failed breeding in an otherwise normal-cycling bitch, bred without progesterone timing, is far more likely to be a timing miss than true infertility — recommending a properly timed repeat breeding before an extensive workup is both more cost-effective and more likely to actually solve the client's problem.</p>
<h2>Red flags that warrant moving straight to a deeper workup</h2>
<p>Repeated failures despite confirmed correct timing, abnormal vaginal discharge, or a known prior reproductive tract issue are signals that skip straight past "try timing it better" and into genuine workup territory — recognizing these distinctions is what this module is really teaching.</p>
<h2>Setting realistic client expectations around infertility</h2>
<p>Not every infertility case resolves, and being honest about that upfront — while still working through the reasonable diagnostic steps — maintains trust better than implying a guaranteed solution exists for every case.</p>"""),
    ("Basic Dystocia Recognition and Triage",
     """<h2>The core question: is this actually dystocia?</h2>
<p>Prolonged, unproductive strong straining beyond roughly 20-30 minutes without progress, or a prolonged gap between puppies with visible distress, are the practical triggers — distinguishing genuine dystocia from normal variation (Foundation tier's baseline) is the entire point of this module.</p>
<h2>Maternal vs. fetal causes, at triage level</h2>
<p>Uterine inertia (maternal) and obstruction (fetal malposition, oversized puppy, or a birth-canal abnormality) require genuinely different interventions — a triage-level distinction between the two (even before full diagnostics) meaningfully shapes the immediate next step.</p>
<h2>What can be tried before escalating</h2>
<p>Calcium and oxytocin administration have a real but narrow role, appropriate only after obstruction has been reasonably ruled out — using them inappropriately in an obstructive dystocia can make the situation actively worse, which is exactly why triage-level judgment matters here.</p>
<h2>Knowing the threshold for surgical intervention</h2>
<p>A clear, practiced sense of when medical management has had a fair, time-limited trial and when it's time to move to c-section is the single most consequential judgment call in this whole module — hesitating too long is a real, documented cause of preventable puppy and maternal loss.</p>"""),
    ("Neonatal Basics and When to Refer",
     """<h2>The first 24 hours — what's actually normal</h2>
<p>Vigorous nursing, steady weight gain (not loss) from day 2 onward, and a warm, quiet, content puppy define normal — a puppy that's persistently cold, crying, or not gaining is signaling a real problem, not just normal newborn fussiness.</p>
<h2>Common, manageable neonatal problems</h2>
<p>Hypothermia, hypoglycemia, and failure to nurse adequately are frequent, generally manageable in general practice with prompt recognition — the key skill is catching these early, before they cascade into something more serious.</p>
<h2>When a case genuinely needs specialist referral</h2>
<p>Persistent failure to thrive despite correct supportive care, suspected congenital abnormalities, or a litter-wide pattern of problems (suggesting a maternal or infectious cause) are reasonable referral triggers — recognizing the limit of general-practice management, rather than persisting indefinitely, is itself a real clinical skill.</p>
<h2>Closing the loop with the breeding client</h2>
<p>A brief structured follow-up in the days after whelping — checking in on the litter's progress — catches problems early and reinforces the ongoing-relationship model covered at Foundation level, rather than treating whelping as the end of the practitioner's involvement.</p>"""),
]

INTERMEDIATE_EXAM = [
    ("Why should a single poor semen evaluation not immediately be treated as proof of subfertility?",
     "A single poor result can reflect recent overuse, illness, heat stress, or a rushed collection rather than genuine subfertility — a repeat evaluation under better conditions is standard before concluding subfertility.",
     "It can reflect temporary factors rather than true subfertility, so a repeat evaluation under better conditions is standard first",
     "A single semen evaluation is always definitive and needs no confirmation regardless of collection conditions"),
    ("Why does progesterone TREND matter more than a single progesterone value for breeding timing?",
     "The rate of rise across serial measurements is what identifies the optimal breeding window, not one isolated value interpreted alone.",
     "The rate of rise across serial measurements identifies the optimal window, not one isolated number",
     "A single progesterone value at any point in the cycle is sufficient to plan a breeding with precision"),
    ("What's the most common reason a single failed breeding occurs in an otherwise normally-cycling bitch bred without progesterone timing?",
     "Mistimed breeding is the single most common cause — a properly timed repeat breeding is usually more appropriate than an extensive workup after just one failure.",
     "Mistimed breeding — usually more appropriately addressed with a properly timed repeat than an immediate full workup",
     "A single failed breeding almost always indicates a serious, permanent fertility problem"),
    ("Why is distinguishing uterine inertia from obstruction important at the dystocia-triage stage, before full diagnostics?",
     "The two causes require genuinely different interventions, and using calcium/oxytocin inappropriately in an obstructive case can make the situation worse.",
     "They need different interventions, and treating an obstruction as if it were inertia can actively worsen the case",
     "The distinction only matters after full diagnostics are complete and has no bearing on immediate triage"),
    ("What is described as the single most consequential judgment call in managing a dystocia case?",
     "Knowing when medical management has had a fair, time-limited trial and it's time to move to c-section — hesitating too long is a real, documented cause of preventable loss.",
     "Recognizing when medical management's fair trial is over and it's time to escalate to surgical intervention",
     "Whether to administer calcium before or after oxytocin, which is the primary factor in outcome"),
]


class Command(BaseCommand):
    help = (
        "Seeds the Foundation and Intermediate tiers under Canine Reproduction "
        "for Practitioners, and gates the existing Advanced course behind the "
        "new Intermediate (prerequisite chain). Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme = Programme.objects.filter(slug="veterinary-continuing-education").first()
        if not programme:
            self.stderr.write(self.style.ERROR("Run seed_vet_breeding_course first — no Programme found."))
            return

        advanced = Course.objects.filter(slug="canine-reproduction-for-practitioners").first()
        if not advanced:
            self.stderr.write(self.style.ERROR("Run seed_vet_breeding_course first — Advanced course not found."))
            return

        with transaction.atomic():
            foundation, f_created = self._make_course(
                org, programme, slug="canine-reproduction-foundations",
                title="Canine Reproduction — Foundations",
                subtitle="Reproductive anatomy, cycle staging, breeding soundness exams, and pregnancy "
                         "diagnosis — the clinical baseline for reproductive practice.",
                description="<p>A 6-module foundation course covering canine reproductive anatomy and "
                            "physiology, estrous cycle staging, the breeding soundness examination, basic "
                            "pregnancy diagnosis and monitoring, normal parturition, and client communication "
                            "in breeding practice — for licensed veterinarians and vet techs building a real "
                            "reproductive service.</p>",
                level=Course.Level.FOUNDATION, price_ngn=3000, prerequisite=None,
                modules=FOUNDATION_MODULES, exam_questions=FOUNDATION_EXAM,
                exam_title="Final Exam — Canine Reproduction Foundations",
            )
            intermediate, i_created = self._make_course(
                org, programme, slug="canine-reproduction-intermediate",
                title="Canine Reproduction — Intermediate",
                subtitle="Semen evaluation, progesterone timing, infertility recognition, and dystocia "
                         "triage — applied clinical skills building on the Foundations course.",
                description="<p>A 5-module intermediate course covering semen collection and evaluation, "
                            "progesterone timing and ovulation prediction, recognizing common infertility "
                            "presentations, basic dystocia recognition and triage, and neonatal basics — "
                            "bridging Foundations into the clinical depth of the Advanced course.</p>",
                level=Course.Level.INTERMEDIATE, price_ngn=5000, prerequisite=foundation,
                modules=INTERMEDIATE_MODULES, exam_questions=INTERMEDIATE_EXAM,
                exam_title="Final Exam — Canine Reproduction Intermediate",
            )

            if advanced.prerequisite_id != intermediate.id:
                advanced.prerequisite = intermediate
                advanced.save(update_fields=["prerequisite"])
                self.stdout.write(self.style.SUCCESS(
                    f"Gated {advanced.title} behind {intermediate.title}."
                ))
            else:
                self.stdout.write(self.style.WARNING(f"{advanced.title} already gated correctly."))

        self.stdout.write(self.style.SUCCESS(
            "Done. New tiers are unpublished — review, set Vertical + Approved + is_published in admin."
        ))

    def _make_course(self, org, programme, *, slug, title, subtitle, description, level, price_ngn,
                      prerequisite, modules, exam_questions, exam_title):
        from apps.catalog.models import Lesson, Module

        course, created = Course.objects.get_or_create(
            organization=org, programme=programme, slug=slug,
            defaults={
                "title": title, "subtitle": subtitle, "description": description,
                "audience": Audience.VET, "level": level,
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
