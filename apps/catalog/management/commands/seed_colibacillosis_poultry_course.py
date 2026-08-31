from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Seventh of the poultry-only ~20-topic batch (see
# seed_mycoplasmosis_poultry_course.py's header for context).

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>Waiting for a door to open, not a primary disease</h2>
<p>Colibacillosis in poultry is caused by avian pathogenic E. coli (APEC) — most E. coli found in a bird are harmless gut flora, and APEC is a genuinely pathogenic subset that acts overwhelmingly as an opportunist rather than a primary invader. This single fact is what shapes the entire diagnostic and treatment approach in this course: colibacillosis is almost never the first thing wrong with a flock.</p>
<h2>What actually opens the door</h2>
<p>Colibacillosis is almost always secondary — to a primary viral respiratory infection (infectious bronchitis, Newcastle disease, mycoplasmosis, all of which damage the respiratory lining), to poor air quality from ammonia damage, to stress, or to immunosuppression. Transmission itself is fecal-oral and environmental, plus a distinct route worth knowing on its own: fecal eggshell contamination penetrating the shell during incubation, seeding yolk sac or navel infection in newly hatched chicks.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>Several distinct presentations, one underlying cause</h2>
<p>The respiratory/airsacculitis form follows primary respiratory damage from another disease. The septicemic form causes sudden death, depression, and greenish diarrhea. Omphalitis in chicks — sometimes called "mushy chick disease" — is a major early mortality cause that traces back to hatchery or egg hygiene, not to anything the chick did wrong after hatching. Less commonly seen: coligranuloma, swollen head syndrome (typically with a concurrent viral infection), and salpingitis or egg peritonitis in layers.</p>
<h2>The same triad seen in mycoplasmosis, for the same reason</h2>
<p>The airsacculitis-pericarditis-perihepatitis triad — already familiar from the mycoplasmosis course — appears here too, since the two conditions frequently co-occur. Chicks with omphalitis show an unhealed, infected navel and a retained, discolored yolk sac at necropsy.</p>"""),
    ("Diagnosis",
     """<h2>Culture is the gold standard, but history is the real clue</h2>
<p>Bacterial culture and isolation from affected tissue is the gold standard, particularly since many different APEC serotypes exist and no single quick test substitutes for it. A history of a preceding or concurrent stressor or primary disease is a strong clue worth actively investigating alongside treatment — not a footnote to it, given how rarely colibacillosis stands alone.</p>
<h2>Key differentials</h2>
<p>Fowl cholera and other systemic bacterial infections need to be considered; culture is what actually differentiates them from colibacillosis rather than clinical picture alone.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treating the infection without treating the trigger invites recurrence</h2>
<p>Culture-guided antibiotics are the standard treatment — antibiotic resistance is a real and growing concern here, which is exactly why culture-guided choice matters rather than reaching for a default. Just as important: addressing the underlying trigger simultaneously, or expect the same problem to recur once treatment stops.</p>
<h2>Control — removing the opportunity, not just treating the infection</h2>
<p>Since this is an opportunistic disease, control means improving ventilation, litter, and ammonia management to remove the opportunity in the first place. For omphalitis specifically, hatchery and egg hygiene are the relevant control point, tracing back to the distinct transmission route covered earlier.</p>
<h2>Prevention</h2>
<p>Good ventilation, vaccination against the primary pathogens that open the door in the first place, egg and hatchery hygiene, and — for high-risk operations — some E. coli vaccines exist as an additional layer.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is colibacillosis described as almost never the first thing wrong with a flock?",
        "Avian pathogenic E. coli acts overwhelmingly as an opportunist — it's almost always secondary to a "
        "primary viral respiratory infection, poor air quality, stress, or immunosuppression opening the door.",
        "APEC is overwhelmingly opportunistic, almost always following a primary infection or stressor",
        "APEC is a primary pathogen that consistently strikes healthy flocks with no prior trigger",
    ),
    (
        "Why does omphalitis ('mushy chick disease') trace back to hatchery or egg hygiene rather than post-hatch conditions?",
        "Fecal eggshell contamination can penetrate the shell during incubation, seeding yolk sac or navel "
        "infection before the chick has even hatched — a distinct transmission route from post-hatch exposure.",
        "Contamination penetrating the eggshell during incubation seeds the infection before the chick even hatches",
        "Omphalitis is caused entirely by conditions in the brooder house after hatching, unrelated to the egg",
    ),
    (
        "Why does treating a colibacillosis outbreak with antibiotics alone risk recurrence?",
        "Colibacillosis is opportunistic — treating the infection without also addressing the underlying trigger "
        "(a primary disease, poor ventilation, stress) leaves the door open for it to happen again.",
        "Without addressing the underlying trigger that let the infection in, the same problem tends to recur",
        "Antibiotic treatment alone reliably prevents any future colibacillosis outbreak in the same flock",
    ),
    (
        "Why does the airsacculitis-pericarditis-perihepatitis triad show up in both colibacillosis and mycoplasmosis?",
        "The two conditions frequently co-occur — E. coli commonly acts as a secondary opportunist on top of an "
        "existing mycoplasmosis infection, producing the same combined lesion pattern.",
        "The two conditions frequently co-occur, with E. coli acting as a secondary opportunist on top of mycoplasmosis",
        "The triad is a coincidental finding with no real connection between the two conditions",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Colibacillosis in Poultry' — seventh of the poultry-only "
        "~20-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="colibacillosis-in-poultry",
                defaults={
                    "title": "Colibacillosis in Poultry",
                    "subtitle": "Almost never the first thing wrong with a flock — E. coli waiting for a primary "
                                 "infection, poor ventilation, or stress to open the door.",
                    "description": "<p>A 4-module continuing-education course on colibacillosis — etiology and "
                                    "why it's an opportunist rather than a primary pathogen, clinical presentations "
                                    "including omphalitis's real transmission route, diagnosis emphasizing history "
                                    "alongside culture, and treatment/control/prevention centered on removing the "
                                    "underlying opportunity, not just treating the infection.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "Treating the infection without treating the trigger just invites it back",
                    "sales_subheadline": "4 modules on colibacillosis — opportunistic pathology, omphalitis's real "
                                          "cause, and why culture-guided treatment matters given resistance risk.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners investigating a suspected secondary infection alongside a primary disease\n"
                        "Anyone working the existing Poultry series who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Colibacillosis CE for vets — opportunistic pathology, omphalitis, and "
                                         "culture-guided treatment given resistance risk.",
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
                organization=org, name="Colibacillosis in Poultry — Final Exam",
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
                title="Final Exam — Colibacillosis in Poultry",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
