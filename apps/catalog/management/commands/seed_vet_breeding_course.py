from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# "Canine Reproduction for Practitioners" — the vet-audience
# counterpart to the breeder-facing Practical Dog Breeding track
# (referenced as a placeholder in that course's own "not_for" copy
# since it was first seeded). Audience=VET, so the content bar is
# different from the breeder track: this assumes clinical training
# and licensure, and goes into diagnostic reasoning, physiology, and
# practice-level detail the breeder course deliberately stays out of.
#
# Still deliberately stops short of prescriptive protocols (specific
# drug names/doses/surgical technique steps) — this is CE-level
# conceptual and diagnostic-reasoning content, not a substitute for a
# vet's own clinical judgment, training, or product literature. Every
# module that touches pharmacology speaks in terms of drug CLASSES and
# mechanisms, not a "give X mg of Y" instruction.

MODULES = [
    ("Reproductive Physiology and the Estrous Cycle, in Depth",
     """<h2>Beyond the breeder-level overview</h2>
<p>This course assumes you already know the four-stage cycle (proestrus, estrus, diestrus, anestrus). This module is about the underlying endocrinology that actually drives clinical decision-making.</p>
<h2>The hormonal cascade</h2>
<p>Rising estrogen through proestrus drives the physical signs breeders see — vulvar swelling, sanguineous discharge — while follicles mature. The LH surge triggers ovulation, typically 24-72 hours later depending on the individual bitch, which is precisely why "day of standing heat" is such an unreliable proxy for "day of ovulation" at the clinical level, not just the breeder level. Post-ovulation, oocytes require an additional 48-72 hours of maturation before they're actually fertilizable — a detail that matters when counseling an owner on optimal breeding timing.</p>
<h2>Progesterone as the clinical anchor</h2>
<p>Serial progesterone assays remain the most practical, widely available tool for pinpointing ovulation in general practice. A rise above roughly 5 ng/mL is generally used as the marker of the LH surge/impending ovulation, with levels continuing to climb through diestrus. Interpretation matters more than the number alone: a single value is a snapshot, not a trend, and serial sampling (every 24-48h through late proestrus) is what actually lets you predict the fertile window with confidence rather than react to it after the fact.</p>
<h2>Vaginal cytology as a complementary tool</h2>
<p>Cornification patterns track the same estrogen rise cytologically — superficial cell percentage climbing through proestrus, peaking around ovulation. Cytology alone is a reasonable low-cost screening tool but is less precise than progesterone timing for a client investing in AI or an out-of-area stud; the two used together give more confidence than either alone.</p>
<h2>Anestrus length and its clinical relevance</h2>
<p>Interestrous interval varies meaningfully by breed (commonly cited as roughly 5-11 months, with real breed variation at both extremes) — worth documenting per patient rather than assuming a population average, since it directly informs when to expect the next cycle and whether an apparently "delayed" cycle actually warrants workup.</p>"""),
    ("Diagnostic Approach to the Infertile Bitch or Dog",
     """<h2>Framing the infertility workup</h2>
<p>"Infertile" covers a wide differential — timing failure (still the most common real-world cause, and the first thing to rule out before further workup), true anovulation, luteal insufficiency, anatomic abnormality, infectious causes, and male-factor infertility. A structured workup, not a single test, is what actually resolves most cases.</p>
<h2>History as the first diagnostic tool</h2>
<p>Before any test: exact timing of prior breeding attempts relative to cytology/progesterone (if any was done), prior litter history, any medication history (including some anti-inflammatories and hormonal products that can suppress cyclicity), and body condition — both under- and over-conditioned bitches show measurably reduced fertility.</p>
<h2>The female workup</h2>
<p>Serial progesterone through a monitored cycle (does she actually ovulate, and when, relative to when breeding was attempted), vaginal cytology, and — where history suggests it — vaginal culture and cytology for infectious causes, abdominal ultrasound for uterine/ovarian structural findings, and Brucella canis screening, especially for a bitch with any history from an unknown-status source or prior reproductive loss.</p>
<h2>The male side of the workup</h2>
<p>Infertility workups that skip the stud are a common gap. A complete semen evaluation (volume, concentration, motility, morphology) plus a general physical/reproductive exam (testicular size and symmetry, prostate) should be standard before extensive female workup in a pairing that's failed more than once, not an afterthought.</p>
<h2>When timing genuinely was the problem</h2>
<p>A large share of "infertility" referrals resolve once proper progesterone-timed breeding is done — worth explicitly ruling out first, both for the client's sake and because it reframes the whole workup if timing was never actually controlled for in prior attempts.</p>"""),
    ("Assisted Reproduction: AI, Semen Evaluation, and Cryopreservation",
     """<h2>Choosing among AI methods</h2>
<p><strong>Vaginal AI</strong> is least invasive but generally needs the freshest, highest-quality semen and good timing precision. <strong>Trans-cervical insemination (TCI)</strong> — using endoscopic guidance to deposit semen directly into the uterus — meaningfully improves success rates with chilled or frozen semen and is now standard practice at most reproduction-focused practices. <strong>Surgical AI</strong> remains an option, particularly historically for frozen semen, though TCI has reduced how often it's truly necessary.</p>
<h2>Semen evaluation, properly done</h2>
<p>A complete evaluation is volume, concentration (via hemocytometer or computer-assisted analysis), progressive motility, and morphology (ideally via a stained smear, assessing head/midpiece/tail defects separately) — not concentration or motility alone. Morphology in particular is often under-assessed in general practice despite being a strong predictor of fertility.</p>
<h2>Chilled semen logistics</h2>
<p>Extenders exist specifically to preserve motility over 24-72 hours at refrigerated temperature; shipping logistics (same-day courier, proper packaging, arrival-time coordination with the bitch's monitored cycle) are as much a practice-management skill as a clinical one — a perfectly viable sample can still fail from poor shipping coordination.</p>
<h2>Frozen semen realities</h2>
<p>Post-thaw motility is inherently lower than fresh/chilled — TCI or surgical AI, with tight progesterone-guided timing (often narrower than for fresh semen), is what makes frozen semen viable at all. Set client expectations accordingly: frozen-semen success rates are genuinely lower per cycle than fresh, which matters for counseling on cost and likely number of attempts needed.</p>
<h2>When AI is the right recommendation to make</h2>
<p>Geographic separation, a size/temperament mismatch making natural mating unsafe, accessing genetics unavailable any other way, or a stud with no natural-mating experience are all legitimate indications — framing this clearly for clients helps them understand it as a clinical tool, not just an expensive convenience.</p>"""),
    ("Pregnancy Diagnosis and Management",
     """<h2>Confirming pregnancy — modality and timing</h2>
<p>Abdominal ultrasound remains the most useful early tool, reliably detecting gestational sacs from around day 21-25 post-ovulation and allowing a rough viability assessment via fetal heart rate from around day 25 onward. Relaxin assays (specific to pregnancy, unlike general progesterone) are useful from around day 25-30 where ultrasound access is limited. Radiography becomes useful later — from around day 45 onward, once fetal skeletal mineralization allows a reliable count, which ultrasound alone often underestimates in a multi-fetus litter.</p>
<h2>Monitoring through gestation</h2>
<p>A single early confirmation isn't a management plan. Periodic reassessment — particularly a pre-whelping radiograph for fetal count and positioning — gives you and the owner a real baseline for what "normal" looks like at whelping, which matters enormously for recognizing dystocia early rather than late.</p>
<h2>Nutritional and management counseling</h2>
<p>Beyond the breeder-level "increase calories in the final third" guidance: body condition scoring through gestation, awareness of eclampsia risk factors (particularly in smaller-breed bitches with larger litters), and a clear whelping-date estimate communicated to the owner with an honest range, not false precision.</p>
<h2>Medication safety in the pregnant patient</h2>
<p>Relatively few medications have solid safety data in pregnant bitches. When a pregnant patient needs treatment for an unrelated condition, the practical approach is: treat the condition that genuinely needs treating, favor agents with the best available safety data for the species and life stage, and have an honest risk conversation with the owner rather than assuming "nothing is safe" or "everything is fine."</p>
<h2>Recognizing pregnancy loss</h2>
<p>Resorption (typically early, sometimes undetected without serial monitoring) and abortion (later, usually with visible signs) have different differentials worth distinguishing — infectious causes (including Brucella canis), hormonal insufficiency, and structural/uterine causes among them — and different implications for the bitch's future breeding soundness.</p>"""),
    ("Dystocia: Clinical Decision-Making and Intervention",
     """<h2>Building the clinical decision framework</h2>
<p>The breeder-facing course teaches "call the vet" red flags. This module is about what happens once that call reaches you — the actual differential and decision tree for maternal vs. fetal dystocia, and when medical management is appropriate versus when it's time to move to surgery.</p>
<h2>Maternal causes</h2>
<p>Primary uterine inertia (labor never establishes effectively — often linked to overstretching in a large litter, hypocalcemia, or an aged/obese dam), secondary inertia (normal labor that stalls from exhaustion after delivering some puppies), and true obstruction (pelvic narrowing, uterine torsion, or a mass) each point toward a different intervention.</p>
<h2>Fetal causes</h2>
<p>Oversized fetus relative to maternal pelvis, malposition/malpresentation, and fetal death with secondary obstruction are the main categories — abdominal ultrasound and radiography both have a role in distinguishing these before deciding on intervention.</p>
<h2>Medical management — when it's appropriate</h2>
<p>For confirmed primary inertia with a normally positioned, appropriately sized fetus and no obstruction, medical management (calcium and/or oxytocin, used judiciously and only after confirming there's no obstruction — oxytocin against an obstructed birth canal is actively dangerous) can be appropriate. This is a decision that depends on a full assessment, not a default first step.</p>
<h2>When to move to caesarean without delay</h2>
<p>Any confirmed obstruction, failure to progress after appropriate medical management, fetal or maternal distress, or a breed/individual history predicting a high likelihood of dystocia (notably brachycephalic breeds) are all indications to proceed to surgery promptly rather than continuing to "wait and see" — the clinical cost of delay here is real and well documented.</p>
<h2>Counseling the client through the decision</h2>
<p>Owners in the middle of a whelping emergency are stressed and often emotionally invested in "letting her do it naturally." Clear, direct communication about why a caesarean is the safer path in a specific situation — grounded in the actual clinical findings, not general anxiety — is as much a skill here as the surgery itself.</p>"""),
    ("Neonatal Critical Care",
     """<h2>Beyond the breeder-level basics</h2>
<p>Owners are taught warmth, weighing, and colostrum timing. This module covers what a practice actually does when a neonate presents in real trouble.</p>
<h2>Assessing the critical neonate</h2>
<p>A rapid triage covers: rectal temperature (neonates are poikilothermic for the first couple of weeks — a temperature reading means something different here than in an adult patient), respiratory effort and rate, mucous membrane color, hydration (skin tent is unreliable in neonates; consider urine output and mucous membrane moisture instead), and blood glucose (a bedside glucometer reading is fast, cheap, and often the single most useful triage data point in a collapsed neonate).</p>
<h2>Hypothermia and hypoglycemia — the vicious cycle, clinically managed</h2>
<p>Warm gradually (rapid rewarming risks its own complications) using an incubator or controlled external heat source, monitoring rectal temperature through the process rather than guessing. Glucose support — oral if the neonate can suckle/swallow safely, or via a diluted dextrose solution applied to oral mucosa or given parenterally if not — should generally follow, not precede, adequate warming, matching the physiology: a cold gut doesn't absorb or utilize glucose effectively.</p>
<h2>Fluid therapy in neonates</h2>
<p>Neonates have a proportionally higher body water content and higher fluid turnover than adults, and both dehydration and overhydration happen faster and are tolerated worse. Subcutaneous fluids are often adequate for mild cases; more critical presentations may need intraosseous or intravenous access, which in a neonate is a real technical skill worth deliberately practicing before you need it in an emergency.</p>
<h2>Common neonatal presentations and their differentials</h2>
<p>"Fading puppy syndrome" is a description, not a diagnosis — the real differential includes sepsis (often from inadequate colostrum transfer or environmental contamination), congenital anomalies, hypoxic injury from a difficult birth, and herpesvirus (which behaves very differently, and far more dangerously, in neonates than adults).</p>
<h2>When to counsel euthanasia is the humane option</h2>
<p>Not every neonatal crisis has a good outcome available. A clear-eyed, honest conversation with the owner about prognosis — informed by exam findings, not just the family's hopes — is part of responsible neonatal care, not a failure of it.</p>"""),
    ("Reproductive Pathology and Common Presenting Complaints",
     """<h2>Pyometra</h2>
<p>The classic diestrual, progesterone-primed presentation — typically an intact bitch some weeks post-estrus, with variable systemic signs depending on whether the cervix is open (discharge visible) or closed (systemic signs often more severe, no external discharge). Ultrasound is the key diagnostic tool; ovariohysterectomy remains the definitive treatment, though medical management (prostaglandins, in an open-cervix, stable, breeding-value patient) is a real option worth understanding, not just surgery by default.</p>
<h2>Brucella canis</h2>
<p>Beyond the breeder-level mention: this is a reportable disease in many jurisdictions, causes late-term abortion/infertility/epididymitis, and is genuinely zoonotic (rare but real transmission risk) — a positive result has implications for the whole breeding operation and the people around it, not just the individual dog. Testing protocol and confirmatory testing (given a meaningful false-positive rate on rapid screening tests) is worth knowing cold if you serve a breeding-dog population.</p>
<h2>Prostatic disease in the intact male</h2>
<p>Benign prostatic hyperplasia is near-universal in intact older males and is often incidental; prostatitis, prostatic cysts, and (less commonly) neoplasia need to be actively differentiated via history, palpation, ultrasound, and where indicated, culture or cytology — "it's probably just BPH" is a reasonable first thought, not a diagnosis you stop investigating at.</p>
<h2>Testicular and scrotal pathology</h2>
<p>Cryptorchidism (with its associated elevated neoplasia risk in the retained testicle), testicular neoplasia, and orchitis/epididymitis each have distinct presentations and management implications worth being able to distinguish confidently on exam.</p>
<h2>Vaginal and uterine structural findings</h2>
<p>Vaginal hyperplasia/prolapse (estrogen-driven, typically resolving post-estrus but occasionally needing intervention), and structural uterine findings on ultrasound (from cystic endometrial hyperplasia through to neoplasia) round out the differential list worth carrying into any reproductive-complaint exam.</p>"""),
    ("Building a Reproduction Service in Practice",
     """<h2>Why this is worth building deliberately</h2>
<p>Reproduction work — progesterone-timed breedings, AI, C-sections, neonatal care — is high-value, relationship-building work that keeps breeder clients loyal to a practice for years, not a one-off transaction. Practices that build real capability here tend to become the default referral for their local breeding community.</p>
<h2>Equipment and capability, realistically staged</h2>
<p>Start with what pays for itself fastest: in-house progesterone testing (or fast-turnaround send-out), a good ultrasound with a curvilinear probe suited to abdominal reproductive work, and a clear internal protocol for pregnancy diagnosis and dystocia triage. TCI equipment and semen-freezing capability are reasonable next investments once demand is proven, not day-one requirements.</p>
<h2>Building relationships with the breeding community</h2>
<p>Responsible breeders (the exact audience of the companion breeder-track course) are looking for a vet who understands their world, not one who treats every breeding-related visit as an inconvenience. Being visibly knowledgeable — including, practically, engaging with local breed clubs — compounds into real referral volume over time.</p>
<h2>Pricing reproduction services</h2>
<p>Progesterone-timed breeding programs, AI procedures, and elective/emergency C-sections are commonly underpriced relative to the skill, equipment cost, and after-hours availability they actually require — worth costing honestly against your practice's real overhead rather than defaulting to whatever a nearby practice happens to charge.</p>
<h2>After-hours and emergency capacity</h2>
<p>Whelping emergencies don't respect business hours. Having a clear, communicated after-hours protocol (whether in-house or via a trusted referral/emergency partner) is part of what makes a practice a genuine reproduction destination rather than one that only handles the parts that happen to occur at 2pm on a Tuesday.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is progesterone timing considered more clinically reliable than relying on the day of standing heat alone?",
        "The LH surge and resulting ovulation can occur well after standing heat begins, and oocytes need an additional "
        "48-72h to mature post-ovulation — a single visible sign doesn't capture this timeline the way serial "
        "progesterone sampling does.",
        "It tracks the actual hormonal trigger for ovulation, not just a visible external sign that can lag it",
        "Standing heat and ovulation always occur on exactly the same day, so timing method doesn't matter",
    ),
    (
        "In a structured infertility workup, why should the stud's semen evaluation not be treated as an afterthought?",
        "Male-factor infertility is a real and often-overlooked contributor — a complete workup evaluates both partners, "
        "not just the female, especially after more than one failed breeding attempt.",
        "Because male-factor infertility is common enough that skipping it leaves a major differential unexamined",
        "Because the stud is never a meaningful factor in a failed breeding",
    ),
    (
        "Why does frozen semen generally require tighter progesterone-guided timing than fresh or chilled semen?",
        "Post-thaw motility and longevity are inherently reduced compared to fresh/chilled semen, so the fertile window "
        "that frozen semen can actually be used within is narrower.",
        "Its viable post-thaw window is shorter, so timing precision matters proportionally more",
        "Frozen semen has no real timing sensitivity compared to fresh semen",
    ),
    (
        "Why is a pre-whelping radiograph valuable even after an earlier ultrasound already confirmed pregnancy?",
        "Ultrasound alone often underestimates fetal count in a multi-fetus litter, while radiography (once skeletal "
        "mineralization allows it) gives a more reliable count and positioning — both useful for recognizing dystocia early.",
        "It gives a more reliable fetal count and positioning than ultrasound alone typically provides",
        "It's purely a formality with no real diagnostic value beyond the ultrasound already done",
    ),
    (
        "Why is oxytocin potentially dangerous to administer before ruling out obstruction in a dystocia case?",
        "Stimulating contractions against a genuine obstruction (rather than primary inertia) can cause real harm — "
        "confirming there's no obstruction is a prerequisite for appropriate medical management, not an optional step.",
        "Because it can cause real harm if used against an undiagnosed obstruction rather than true inertia",
        "Oxytocin has no real risk regardless of the underlying cause of dystocia",
    ),
    (
        "Why does a cold neonate typically need warming before glucose support, not the other way around?",
        "Neonatal physiology means a cold gut doesn't absorb or utilize glucose effectively — warming first is what "
        "actually lets subsequent glucose support work as intended.",
        "A cold neonate can't effectively absorb or use glucose until adequately warmed first",
        "The order of warming versus glucose support makes no real physiological difference",
    ),
    (
        "What distinguishes an open-cervix from a closed-cervix pyometra presentation, and why does it matter clinically?",
        "Open-cervix cases show visible discharge and are often less systemically severe; closed-cervix cases can be "
        "more severe with no external discharge — this distinction also affects whether medical management is a "
        "reasonable option.",
        "It affects both the visible signs and whether medical management is a realistic treatment option",
        "The distinction has no real effect on clinical presentation or treatment options",
    ),
    (
        "Why is a positive Brucella canis result significant beyond the individual dog's own health?",
        "It's a reportable disease in many jurisdictions with real zoonotic risk and implications for an entire "
        "breeding operation, not just the one affected dog.",
        "It has reportable-disease and zoonotic implications reaching beyond the individual patient",
        "It only ever affects the single dog tested and has no wider relevance",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Canine Reproduction for Practitioners' — the vet-audience "
        "counterpart to the breeder-facing Practical Dog Breeding track — "
        "with real written content and a final exam. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="veterinary-continuing-education",
            defaults={
                "title": "Veterinary Continuing Education",
                "audience": Audience.VET,
                "description": "Clinical continuing-education courses for licensed veterinarians and vet techs.",
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="canine-reproduction-for-practitioners",
                defaults={
                    "title": "Canine Reproduction for Practitioners",
                    "subtitle": "Diagnostic reasoning and clinical decision-making in canine reproduction, for licensed veterinarians.",
                    "description": "<p>An 8-module continuing-education course covering canine reproductive "
                                    "physiology, infertility workups, assisted reproduction, dystocia management, "
                                    "neonatal critical care, and reproductive pathology — at clinical depth, for "
                                    "practicing veterinarians and vet techs.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.ADVANCED,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 7500,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 5.0,
                    "is_published": False,
                    "sales_headline": "The clinical depth your breeder clients assume you already have on tap",
                    "sales_subheadline": "8 modules on canine reproduction — physiology, infertility workups, "
                                          "assisted reproduction, dystocia, and neonatal critical care.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs in general or reproduction-focused practice\n"
                        "Practitioners wanting to build a real reproduction service, not just handle emergencies as they come\n"
                        "Anyone who wants the clinical depth behind what the breeder-facing course teaches at a lay level"
                    ),
                    "not_for": (
                        "Breeders without veterinary training — see the Practical Dog Breeding track instead, "
                        "it's built for exactly that audience"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Clinical-depth canine reproduction CE for practicing veterinarians — "
                                         "physiology, infertility, assisted reproduction, dystocia, neonatal care.",
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
                organization=org, name="Canine Reproduction for Practitioners — Final Exam",
                description="Covers all 8 modules — must be passed to unlock the certificate.",
            )
            for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.HARD,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
            Quiz.objects.create(
                scope=Quiz.Scope.FINAL, course=course,
                title="Final Exam — Canine Reproduction for Practitioners",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin."
        ))
