from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module

# Intermediate and Advanced tiers for the Practical Dog Breeding
# track — same subject, deeper each level, real written content (not
# placeholders). Same discipline as the foundation content: general
# animal-husbandry/business knowledge, never clinical instruction —
# health-adjacent topics always route the actual decision to a vet;
# the legal/business module routes actual legal decisions to a
# professional, same idea applied to that domain.

INTERMEDIATE_MODULES = [
    ("Genetics and hereditary disease, made usable",
     """<h2>Simple inheritance, without the jargon overload</h2>
<p>You don't need a genetics degree to breed responsibly, but a few concepts change how you read a pairing. Many hereditary conditions follow a <strong>recessive</strong> pattern — a dog can carry one copy of a problem gene, show no symptoms at all, and still pass it on. Two "silent carriers" bred together can produce affected puppies neither parent ever showed signs of. This is exactly why "he's never had a problem" isn't the same as "he can't pass one on."</p>
<h2>Hip and elbow scoring, read correctly</h2>
<p>Hip/elbow scoring schemes (OFA-style grading, or similar systems used regionally) give you a number or grade, not a guarantee. A dog with an excellent score can still throw dysplastic puppies if the pairing is unlucky or the other parent's score is poor — scoring reduces risk across a breeding program, it doesn't eliminate it in any single litter.</p>
<h2>Reading a DNA panel</h2>
<p>A genetic panel typically reports a dog as <strong>clear</strong>, <strong>carrier</strong>, or <strong>affected</strong> for specific tested conditions. The safest pairing rule most breeders use: never breed carrier × carrier for the same condition, since that risks affected puppies. Carrier × clear is generally considered acceptable, since it can't produce an affected puppy for that specific gene (though it can produce more carriers).</p>
<h2>Using coefficient of inbreeding (COI) practically</h2>
<p>COI is a number estimating how related a pairing's ancestors are — a rough proxy for how much both good and bad traits will be concentrated. There's no single "safe" number that applies to every breed, but a noticeably higher COI than your breed's typical average is worth pausing on, not ignoring.</p>"""),
    ("Whelping complications, in more depth",
     """<h2>Building on the Foundation whelping module</h2>
<p>You already know the red flags that mean "call the vet now." This module goes one level deeper into what happens once that call is made, and what you can do while you wait or assist.</p>
<h2>Uterine inertia</h2>
<p>This is when the uterus stops contracting effectively — either from the start (primary inertia) or after delivering some puppies but stalling with more still inside (secondary inertia, often from exhaustion). It's a common, real cause of dystocia and usually needs veterinary intervention — medical or surgical, depending on the situation.</p>
<h2>What "assisting" safely looks like</h2>
<p>If a puppy is visibly presenting (partially out) and the dam is straining without progress, very gentle traction timed with her contractions — pulling down and slightly out, never straight out, never without her also pushing — can sometimes help. If this doesn't work within a couple of contractions, stop and call your vet; forcing it risks real harm to both puppy and dam.</p>
<h2>Neonatal resuscitation basics</h2>
<p>A puppy born not breathing: clear its airway (a bulb syringe, gently), briskly rub it with a clean towel to stimulate breathing, and hold it head-slightly-down to help clear fluid. If it doesn't respond within a minute or two of real effort, this is an emergency — get it to a vet immediately if at all possible.</p>
<h2>Working with your vet during an emergency decision</h2>
<p>A caesarean decision under time pressure is stressful. Having your vet's emergency contact saved, knowing the fastest route to a clinic that can do emergency surgery, and not hesitating out of cost concern when the dam's life may be at risk — these are decisions worth thinking through calmly, before an emergency, not during one.</p>"""),
    ("Pedigree, registration, and honest marketing",
     """<h2>Why registration matters beyond paperwork</h2>
<p>Registering litters (with a recognised kennel club or breed registry where available) creates a verifiable pedigree record — proof of parentage across generations. This matters for buyers who care about lineage, and it builds the kind of track record serious breeders rely on to prove a breeding program's results over time.</p>
<h2>Building your own pedigree records</h2>
<p>Even where formal registry access is limited, keep your own multi-generation records: parents, grandparents, notable health results, and outcomes of each litter. This becomes an asset — buyers increasingly ask for it, and it's exactly the data that makes Module 1's genetics guidance usable in practice.</p>
<h2>Microchipping</h2>
<p>A microchip gives each puppy a permanent, unique ID — useful for registration, and valuable to buyers as proof the dog they own is the one you actually bred. It's a small, one-time cost per puppy worth building into your pricing.</p>
<h2>Marketing honestly</h2>
<p>Word of mouth and referrals from previous happy buyers remain the strongest marketing a small breeder has — stronger than any advert. If you do build any online presence, the same rule from the Foundation course applies: honest photos, honest health disclosures, and no claims you can't back up. A reputation, once damaged by an exaggerated claim, is very hard to rebuild.</p>"""),
    ("From one litter to a real kennel operation",
     """<h2>Space and facility planning</h2>
<p>Scaling past one or two litters a year changes your real needs: separate whelping/recovery space per dam, enough room that litters aren't mixing, and a layout that makes daily cleaning realistic rather than a constant losing battle.</p>
<h2>Getting help</h2>
<p>At real scale, one person can't safely do everything — feeding, cleaning, health monitoring, socialisation, and buyer communication all compete for time. Even part-time help, properly trained on your protocols (especially hygiene and quarantine practices from the Foundation course), is often what actually prevents corners being cut.</p>
<h2>Outbreak contingency planning</h2>
<p>At scale, a single disease outbreak can affect far more dogs and far more money than it would for a hobby breeder. Have a written plan before you need it: where a sick dog gets isolated, who you call, and how you'll communicate with buyers who already have deposits down if a litter is affected.</p>
<h2>Record-keeping that scales</h2>
<p>A notebook works for one litter a year. At real scale, a simple spreadsheet or dedicated software tracking matings, whelping dates, individual puppy weights and health events, and buyer information becomes necessary — not for bureaucracy's sake, but because you genuinely cannot hold it all in memory once you're running several litters at once.</p>"""),
    ("Turning health test results into pairing decisions",
     """<h2>Bringing Module 1 back into practice</h2>
<p>Knowing what a hip score or a DNA panel says is only useful once you actually use it to decide who gets paired with whom. This module is about that decision.</p>
<h2>Weighing multiple results together</h2>
<p>Real pairings rarely have a single deciding factor — you're usually weighing hip/elbow scores, DNA carrier status for several conditions, temperament, and structure all at once. A dog that's excellent in every category except one specific carrier status might still be a good match, paired carefully against a clear-tested partner for that specific gene.</p>
<h2>When to walk away from a pairing</h2>
<p>If two dogs are both carriers for the same serious condition, or the combined health picture raises more concerns than it resolves, the responsible call — echoing the Foundation course's closing message — is not to breed that specific pairing, even if everything else about the dogs looks good.</p>
<h2>Keeping your own results honest</h2>
<p>Record every health test result for every breeding dog you own, good or bad, and refer back to them for every pairing decision — not just the results that support the mating you already wanted to do.</p>"""),
]

ADVANCED_MODULES = [
    ("Advanced reproductive technology, honestly assessed",
     """<h2>Beyond basic AI</h2>
<p>Building on the Foundation course's introduction to artificial insemination, this module looks at when more advanced reproductive technology actually makes sense for a serious breeding program.</p>
<h2>Chilled vs frozen semen</h2>
<p><strong>Chilled semen</strong> (collected and shipped, used within a couple of days) has good success rates and is far simpler logistically. <strong>Frozen semen</strong> can be stored indefinitely — useful for accessing a stud that's no longer alive, or genuinely far away — but generally needs surgical or trans-cervical insemination and precise timing for reasonable success rates. It's a bigger investment, justified mainly when the genetics are genuinely worth it.</p>
<h2>Progesterone-timed protocols</h2>
<p>For any AI, and especially frozen semen, precise timing via progesterone testing (introduced in the Foundation course) stops being optional and becomes close to essential — the margin for timing error with frozen semen especially is much smaller than with natural mating.</p>
<h2>When the investment makes commercial sense</h2>
<p>Advanced reproductive technology costs real money — collection, shipping, storage, veterinary procedure fees. It makes sense when the genetic value of a specific pairing (correcting a real fault, introducing genuine diversity, accessing bloodlines otherwise unavailable) clearly outweighs that cost. It rarely makes sense just because it's available.</p>"""),
    ("Managing genetic diversity across a program",
     """<h2>Beyond one pairing at a time</h2>
<p>Module-level pairing decisions (Intermediate Module 5) are about one mating. This module is about your breeding program as a whole, across years and generations.</p>
<h2>Effective population size</h2>
<p>A breed or a kennel line can look numerically large while actually being genetically narrow — if most dogs trace back to a small number of heavily-used ancestors, genetic diversity is much lower than the raw dog count suggests. This is the popular-sire problem (Foundation course, Module 3) scaled up to a whole program.</p>
<h2>Avoiding concentration at the program level</h2>
<p>Deliberately varying which dogs you use as sires and dams across generations, tracking cumulative COI (Intermediate Module 1) at the program level rather than just per-litter, and periodically bringing in genuinely outside bloodlines are all real tools for keeping a program's genetic base broader over time.</p>
<h2>Planning tools</h2>
<p>Serious breeding programs increasingly use pedigree-analysis software or services to calculate program-wide diversity metrics, not just single-pairing COI. Even a well-maintained spreadsheet tracking ancestor frequency across your last several generations of breeding stock is a meaningful start.</p>"""),
    ("Building a multi-generation breeding program",
     """<h2>Setting goals across years, not just litters</h2>
<p>A real breeding program has a direction: specific traits being improved, specific faults being bred out, over multiple generations — not just "a nice litter this year."</p>
<h2>Culling and retention decisions</h2>
<p>Deciding which puppies from your own litters to keep back for future breeding (retention) and which lines to stop breeding from (culling from the program, not the dog's life — these dogs make fine pets) is one of the highest-leverage decisions a breeder makes. It should be driven by your program's actual goals and honest health/temperament results, not sentiment.</p>
<h2>When to bring in outside bloodlines</h2>
<p>Even a well-planned program benefits from periodically introducing genuinely unrelated, carefully-vetted outside dogs — both for genetic diversity (Module 2) and to bring in traits your existing line lacks. This should be planned, not reactive.</p>
<h2>Reviewing your own results honestly</h2>
<p>Look back at your program every few years: are the health results actually improving? Is temperament consistent? Are you proud of where your last three generations of puppies ended up? A program that isn't reviewed honestly tends to drift rather than improve.</p>"""),
    ("The legal and business side of commercial breeding",
     """<h2>This module is general guidance, not legal advice</h2>
<p>Business and legal requirements vary by state and change over time. Treat everything here as a starting checklist for a conversation with an actual lawyer or accountant, not as the final word.</p>
<h2>Business registration considerations</h2>
<p>Operating as a real commercial breeder rather than an occasional hobbyist may have registration, tax, and record-keeping implications worth discussing with a professional — this protects you as much as it satisfies any requirement.</p>
<h2>Contracts at scale</h2>
<p>The simple buyer agreement introduced in the Foundation course (Module 8) becomes more important, not less, at commercial volume — consider having a properly drafted template reviewed by a lawyer once, rather than relying on an informal agreement across dozens of sales a year.</p>
<h2>Liability and insurance</h2>
<p>At real scale, consider what happens if a buyer claims a puppy caused property damage, a bite incident, or if a dog escapes and causes an accident. Insurance and clear contract language around liability are worth understanding before you need them, not after.</p>
<h2>Importing new bloodlines</h2>
<p>Bringing in dogs or genetic material from outside the country involves import regulations, quarantine requirements, and health certification that take real time to arrange — start this process early and involve your vet in the required paperwork.</p>"""),
    ("Mentorship, ethics, and advancing the breed",
     """<h2>Giving back to the breeder community</h2>
<p>Every experienced breeder in this course's audience learned from someone else. Mentoring newer breeders — sharing honest experience, including your mistakes — is part of what keeps standards rising across a breed community rather than each breeder relearning the same hard lessons alone.</p>
<h2>Working with breed clubs</h2>
<p>Breed clubs and associations, where they exist for your breed, are a real resource for shared health data, breed-standard discussion, and connecting with other serious breeders — worth engaging with rather than working in isolation.</p>
<h2>Exhibition and judging</h2>
<p>Showing your dogs, and eventually learning to evaluate structure and temperament against the breed standard yourself, sharpens your own eye for what you're actually breeding for — a skill that feeds directly back into every pairing decision in this whole course.</p>
<h2>A closing reflection</h2>
<p>This course started with Foundation Module 1's question: why are you breeding? At this level, with real investment, real scale, and real responsibility to buyers and to the dogs themselves, that question is worth asking again — and answering honestly, every single year you continue.</p>"""),
]

FINAL_EXAMS = {
    "practical-dog-breeding-intermediate": [
        ("Two dogs are both carriers for the same recessive hereditary condition. What does breeding them together risk?",
         "Two carriers bred together can produce affected puppies, even though neither parent shows any symptoms themselves — this is exactly why carrier status matters more than visible health.",
         "Producing affected puppies, even though both parents appear healthy themselves",
         "Nothing extra — carriers are functionally identical to clear dogs"),
        ("What does a higher-than-typical COI (coefficient of inbreeding) on a pairing suggest?",
         "COI estimates how related a pairing's ancestors are — a high COI means both good and hidden bad traits are more likely to be concentrated, worth pausing on rather than ignoring.",
         "Both good and hidden problem traits are more likely to be concentrated in the resulting puppies",
         "It has no practical meaning for a single pairing"),
        ("What is uterine inertia?",
         "It's when the uterus stops contracting effectively, either from the start or after delivering some puppies — a real, common cause of dystocia usually needing veterinary help.",
         "The uterus failing to contract effectively during labour, a real cause of dystocia",
         "A normal brief pause between puppies that never needs attention"),
        ("Why does the course recommend registering litters and keeping multi-generation pedigree records?",
         "Registration and honest records create verifiable proof of parentage and health results over time — increasingly what serious buyers look for, and what makes genetic pairing decisions usable in practice.",
         "It creates a verifiable, buyer-trusted record of parentage and results over generations",
         "It's mainly a formality with little effect on buyer trust or breeding decisions"),
        ("At real kennel scale, why does the course recommend written outbreak contingency planning?",
         "A disease outbreak at scale can affect far more dogs and money than for a hobby breeder — having a plan before it's needed prevents costly delay and confusion during a real crisis.",
         "Because an outbreak at scale can affect far more dogs, and a plan avoids costly delay during a real crisis",
         "Outbreaks are rare enough at scale that planning isn't worth the time"),
    ],
    "practical-dog-breeding-advanced": [
        ("Why does frozen semen generally need more precise timing than natural mating or chilled semen?",
         "The fertility window for frozen semen is narrower, and success rates depend heavily on precise progesterone-timed insemination — the margin for timing error is much smaller.",
         "Its usable fertility window is narrower, so timing precision matters much more",
         "There's no real timing difference between frozen and chilled semen"),
        ("What is the \"popular-sire problem\" scaled up to a whole breeding program?",
         "If most dogs in a program or breed trace back to a small number of heavily-used ancestors, genetic diversity is much lower than the raw dog count suggests — effective population size shrinks.",
         "Effective genetic diversity can be much lower than raw dog numbers suggest, if too many trace to the same few ancestors",
         "It only matters for a single litter, not for a whole program"),
        ("What does \"retention and culling\" mean in the context of a multi-generation program?",
         "Deciding which of your own puppies to keep back for future breeding (retention) and which lines to stop breeding from (culling from the program, not from life) based on honest results and program goals.",
         "Deciding which puppies to keep for future breeding and which lines to stop breeding from, based on honest results",
         "A process that only applies to buying outside dogs, never your own litters"),
        ("Why does the course frame the legal/business module as general guidance rather than legal advice?",
         "Business and legal requirements vary by state and change over time — the honest, responsible approach is treating this as a starting checklist for a real lawyer/accountant conversation.",
         "Because requirements vary by location and change over time, so a real professional should be consulted",
         "Because legal requirements never apply to dog breeding specifically"),
        ("What's the course's closing framing on why mentorship and breed-club involvement matter at this level?",
         "It's part of what keeps standards rising across a whole breed community, rather than each breeder separately relearning the same hard lessons alone.",
         "It helps raise standards across the whole community instead of everyone relearning the same lessons alone",
         "It's optional networking with no real effect on breeding outcomes"),
    ],
}


def _create_tier(self, *, org, programme, slug, title, level, pricing_model, price_ngn,
                  prerequisite, modules_data, sales_headline):
    course, created = Course.objects.get_or_create(
        organization=org, programme=programme, slug=slug,
        defaults={
            "title": title,
            "subtitle": "Continuing the Practical Dog Breeding track for Nigerian breeders.",
            "description": f"<p>{sales_headline}</p>",
            "audience": Audience.BREEDER,
            "level": level,
            "pricing_model": pricing_model,
            "price_ngn": price_ngn,
            "access_type": Course.AccessType.LIFETIME,
            "requires_final_assessment": True,
            "estimated_hours": 3.0,
            "is_published": False,
            "prerequisite": prerequisite,
            "sales_headline": sales_headline,
            "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
        },
    )
    if not created:
        self.stdout.write(self.style.WARNING(f"{title} already exists — leaving modules/lessons as-is."))
        return course

    self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))
    for i, (mtitle, body) in enumerate(modules_data, start=1):
        module = Module.objects.create(
            course=course, order=i, title=mtitle, unlock_rule=Module.UnlockRule.SEQUENTIAL,
        )
        Lesson.objects.create(
            module=module, order=1, title=f"Module {i}: {mtitle}", type=Lesson.Type.TEXT,
            body=body.strip(), is_preview=(i == 1),
        )
    self.stdout.write(self.style.SUCCESS(f"  {len(modules_data)} modules created with real written content."))
    return course


class Command(BaseCommand):
    help = (
        "Creates the Intermediate (₦2000 certificate, requires Foundation "
        "completed) and Advanced (₦5000 for course+certificate) tiers of the "
        "Practical Dog Breeding track, each with real written content and a "
        "final exam. Safe to re-run — skips any course that already exists."
    )

    def handle(self, *args, **options):
        try:
            foundation = Course.objects.get(slug="practical-dog-breeding")
        except Course.DoesNotExist:
            raise CommandError("Run `seed_demo_course` first — Intermediate needs Foundation to exist as its prerequisite.")

        org = foundation.organization
        programme = foundation.programme

        with transaction.atomic():
            intermediate = _create_tier(
                self, org=org, programme=programme,
                slug="practical-dog-breeding-intermediate",
                title="Practical Dog Breeding — Intermediate",
                level=Course.Level.INTERMEDIATE,
                pricing_model=Course.PricingModel.CERTIFICATE_PAID,
                price_ngn=2000,
                prerequisite=foundation,
                modules_data=INTERMEDIATE_MODULES,
                sales_headline="Genetics, complications, and running a real kennel — for breeders who've finished Foundation.",
            )
            advanced = _create_tier(
                self, org=org, programme=programme,
                slug="practical-dog-breeding-advanced",
                title="Practical Dog Breeding — Advanced",
                level=Course.Level.ADVANCED,
                pricing_model=Course.PricingModel.PAID,
                price_ngn=5000,
                prerequisite=None,  # see command docstring / session notes on this choice
                modules_data=ADVANCED_MODULES,
                sales_headline="Advanced reproductive technology, program-level genetics, and the business of breeding at scale.",
            )

            for course in (intermediate, advanced):
                if Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=course).exists():
                    continue
                questions = FINAL_EXAMS[course.slug]
                bank = QuestionBank.objects.create(
                    organization=org, name=f"{course.title} — Final Exam",
                    description=f"Covers all modules of {course.title} — must be passed to unlock the certificate.",
                )
                for stem, explanation, correct, wrong in questions:
                    q = Question.objects.create(
                        bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                        difficulty=Question.Difficulty.MEDIUM,
                    )
                    Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                    Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
                Quiz.objects.create(
                    scope=Quiz.Scope.FINAL, course=course,
                    title=f"Final Exam — {course.title}",
                    instructions=f"{len(questions)} questions covering everything in this course. Pass to unlock your certificate.",
                    bank=bank, question_count=len(questions), pass_mark=70,
                    max_attempts=0, time_limit_minutes=0,
                )
                self.stdout.write(self.style.SUCCESS(f"Created final exam for {course.title}."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Both tiers are unpublished — review, set Vertical + Approved + is_published in admin, same as Foundation."
        ))
