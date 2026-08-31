from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Eighth and final of the poultry-only ~20-topic batch built so far
# (see seed_mycoplasmosis_poultry_course.py's header for context;
# vetfresh-6c has more coming). A practical husbandry guide, not a
# disease deep-dive — deepens the existing "Nutritional Requirements
# Across Production Stages"/"Feed Formulation and Quality Control"
# modules in the earlier Poultry Advanced Practice course into a
# standalone course, same relationship already established elsewhere
# in this batch.

MODULES = [
    ("Energy, Protein, and Amino Acid Balance",
     """<h2>Why feed is worth understanding as closely as any disease</h2>
<p>Feed is 60-70% of production cost and the most common cause of an underperforming flock — even with zero disease present. A vet or manager who can rule nutrition in or out early saves real time and money before chasing a disease explanation that isn't there.</p>
<h2>Energy drives growth, sometimes counterintuitively</h2>
<p>Energy is what drives growth rate — birds eat to meet an energy target, not a fixed volume of feed. This means low-energy feed can paradoxically increase feed cost per unit of growth, since birds simply eat more of it to reach the same energy intake, without necessarily getting the amino acids they need in that extra volume.</p>
<h2>Amino acid balance over crude protein percentage</h2>
<p>Amino acid balance — particularly lysine and methionine — matters more than raw crude protein percentage on a feed label. Two feeds with identical crude protein numbers can perform very differently depending on their amino acid profile.</p>"""),
    ("Life-Stage Formulation and the Calcium/Phosphorus Ratio",
     """<h2>Getting each stage right</h2>
<p>Starter feed (roughly 0-3 weeks) carries the highest protein and energy density of any stage — this is not the phase to economize on feed quality. Grower/finisher rations step density down from there. Layer ration needs a sharp calcium increase for shell formation; switching to layer feed too late produces thin or broken eggs and forces the hen to draw calcium from her own skeleton instead.</p>
<h2>Calcium and phosphorus — the ratio matters as much as the amounts</h2>
<p>Too little calcium in layers causes thin or soft shells and skeletal problems. Too much calcium in growers interferes with growth and kidney function. The ratio between calcium and phosphorus matters just as much as the absolute amounts of each — a common formulation mistake is getting one number right while ignoring the other.</p>"""),
    ("Vitamins, Minerals, and Water",
     """<h2>Deficiencies with distinct, recognizable signatures</h2>
<p>Vitamin A deficiency causes poor growth, damage to respiratory and digestive linings, and reduced disease resistance — and can even resemble the diphtheritic form of fowlpox on a mucous membrane exam, worth remembering from that course. Vitamin D3 deficiency impairs calcium absorption regardless of how much calcium is actually in the diet, producing rickets and poor shells even when calcium intake looks adequate on paper. Vitamin E and selenium deficiency reduces immune function and causes reproductive problems. B-vitamin deficiencies produce specific syndromes — riboflavin deficiency causes curled-toe paralysis — and are best prevented through a proper commercial premix rather than diagnosed individually after the fact.</p>
<h2>Water — the most commonly overlooked bottleneck</h2>
<p>Birds drink roughly twice their feed intake by weight, more in heat. Restricted or poor-quality water reduces growth just as much as feed shortage does, yet it's the input most likely to be overlooked when investigating a production problem.</p>"""),
    ("Feed Storage and the Aflatoxin Connection",
     """<h2>Storage isn't just a logistics detail</h2>
<p>Heat, humidity, and time degrade vitamin potency in stored feed and allow mold growth — a direct link to aflatoxin risk, already covered as a major issue with Nigerian feed storage conditions on this platform's Poultry series.</p>
<h2>Bringing it together</h2>
<p>Nutrition is worth ruling out early whenever a flock underperforms without obvious disease signs. Amino acid balance and the calcium:phosphorus ratio are where formulations most often go wrong. Water intake deserves the same attention as feed intake. And poor storage doesn't just waste money on degraded vitamins — it actively creates a real toxicological risk through aflatoxin.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's or nutritionist's own formulation work for a specific flock. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why can low-energy feed paradoxically increase feed cost per unit of growth?",
        "Birds eat to meet an energy target, not a fixed feed volume — with low-energy feed, they eat more of it "
        "to reach that target, increasing total feed cost without proportionally improving growth.",
        "Birds eat more low-energy feed to reach their energy target, raising total feed cost for the same growth",
        "Low-energy feed always reduces total feed cost regardless of how much a bird actually eats",
    ),
    (
        "Why does amino acid balance matter more than crude protein percentage alone?",
        "Two feeds with identical crude protein numbers can perform very differently depending on their specific "
        "amino acid profile, particularly lysine and methionine.",
        "Feeds with the same crude protein number can still perform very differently based on amino acid profile",
        "Crude protein percentage alone always reliably predicts a feed's real nutritional performance",
    ),
    (
        "Why can rickets and poor shells appear even when dietary calcium intake looks adequate on paper?",
        "Vitamin D3 deficiency impairs calcium absorption regardless of how much calcium is actually in the diet, "
        "so adequate calcium intake alone doesn't guarantee it's being absorbed and used.",
        "Vitamin D3 deficiency can impair calcium absorption even when dietary calcium intake is adequate",
        "Calcium intake alone always determines shell quality and skeletal health with no other factors involved",
    ),
    (
        "Why is water intake described as a commonly overlooked bottleneck in poultry production?",
        "Restricted or poor-quality water reduces growth just as much as feed shortage does, yet it's the input "
        "most likely to be overlooked when investigating an unexplained production problem.",
        "It reduces growth as much as feed shortage but is often overlooked when troubleshooting production issues",
        "Water intake has only a minor effect on growth compared to feed, so it rarely needs investigation",
    ),
    (
        "How does poor feed storage connect to aflatoxin risk, not just wasted nutrition?",
        "Heat, humidity, and time that degrade vitamin potency in stored feed also allow mold growth — the direct "
        "mechanism linking poor storage to real aflatoxin contamination risk.",
        "The same heat/humidity/time conditions that degrade vitamins also allow the mold growth that causes aflatoxin",
        "Feed storage conditions have no real connection to aflatoxin risk, which comes from the raw ingredients alone",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Nutritional Requirements of Poultry: A Practical Guide' — eighth of the "
        "poultry-only ~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="poultry-nutrition-practical-guide",
                defaults={
                    "title": "Nutritional Requirements of Poultry: A Practical Guide",
                    "subtitle": "Feed is 60-70% of production cost and the most common cause of an "
                                 "underperforming flock — even with zero disease present.",
                    "description": "<p>A 4-module continuing-education course on poultry nutrition — energy, "
                                    "protein, and amino acid balance, life-stage formulation and the calcium/"
                                    "phosphorus ratio, vitamin/mineral deficiency signatures and water intake, "
                                    "and feed storage's direct link to aflatoxin risk.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "Rule out nutrition before you chase a disease that isn't there",
                    "sales_subheadline": "4 modules on poultry nutrition — amino acid balance, the calcium:"
                                          "phosphorus ratio, deficiency signatures, and the aflatoxin storage link.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs advising on flock performance and formulation\n"
                        "Practitioners investigating an unexplained production drop with no obvious disease signs\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for a basic feed-buying guide"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Poultry nutrition CE for vets — amino acid balance, calcium:phosphorus "
                                         "ratio, and the aflatoxin storage connection.",
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
                organization=org, name="Poultry Nutrition Practical Guide — Final Exam",
                description="Covers all 4 modules — must be passed to unlock the certificate.",
            )
            for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.MEDIUM,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
            Quiz.objects.create(
                scope=Quiz.Scope.FINAL, course=course,
                title="Final Exam — Poultry Nutrition Practical Guide",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
