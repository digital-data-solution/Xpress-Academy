from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Fifth of the ~30-topic Vet-blog cross-promotion batch (see
# seed_newcastle_disease_course.py's header for full context). No
# dedicated livestock Programme exists yet — following the same
# precedent already set by the Poultry series (also non-canine/feline
# livestock content placed under Veterinary Continuing Education), PPR
# goes in the same programme rather than creating a new one for a
# single course. Worth revisiting once enough livestock-audience
# courses exist to justify a dedicated Programme.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>What causes PPR</h2>
<p>Peste des petits ruminants (PPR), sometimes called "goat plague," is caused by small ruminant morbillivirus, an enveloped, single-stranded RNA virus in the family Paramyxoviridae, genus Morbillivirus — the same genus as rinderpest virus (now eradicated) and measles virus. Being enveloped, the virus is far less environmentally durable than a virus like parvovirus, which meaningfully shapes the control approach covered later in this course.</p>
<h2>Why this disease matters in Nigeria specifically</h2>
<p>PPR is one of the most economically important livestock diseases in Nigeria and the wider Sahel region. Global and regional programs have targeted PPR for eradication by 2030, following the model that succeeded against rinderpest — but the disease remains endemic across much of Nigeria today.</p>
<h2>Who's affected and how it spreads</h2>
<p>Goats and sheep are the primary hosts, with goats generally showing more severe disease. Cattle and pigs can be infected subclinically and aren't significant in maintaining transmission. Transmission is primarily via direct contact and inhalation of aerosolized virus from secretions, particularly during the acute febrile stage. Morbidity can reach 100% in a fully susceptible herd, with case fatality commonly 20-90% depending on strain, host, age, and concurrent disease.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>The early signs, often missed</h2>
<p>High fever, often 40-41°C, is the earliest sign — and frequently the one that gets missed until other signs follow. Oculonasal discharge progresses from serous to mucopurulent as the disease advances.</p>
<h2>The signs that usually prompt a call to the vet</h2>
<p>Erosive stomatitis — necrotic lesions on gums, inner lips, tongue, and hard palate — along with profuse, often foul-smelling diarrhea, rapid dehydration and weight loss. Respiratory signs from secondary bronchopneumonia are common contributors to mortality. Pregnant animals may abort.</p>
<h2>What necropsy shows</h2>
<p>Erosive/necrotic lesions throughout the oral cavity and forestomachs, hemorrhagic enteritis with a characteristic "zebra stripe" pattern in the large intestine, and pneumonia. Lymphoid tissue depletion reflects the virus's tropism for the immune system — the same underlying mechanism seen in measles and rinderpest.</p>"""),
    ("Diagnosis",
     """<h2>Building clinical suspicion</h2>
<p>The combination of fever, oculonasal discharge, oral erosions, and diarrhea — especially with high herd morbidity — should raise immediate suspicion for PPR, particularly in an endemic region.</p>
<h2>Confirmatory testing</h2>
<p>RT-PCR is the standard confirmatory test, run on ocular/nasal swabs, whole blood, or lymphoid tissue at necropsy. Antigen capture ELISA and virus neutralization/competitive ELISA serology are particularly useful for surveillance and for monitoring the success of a vaccination program, not just diagnosing an individual sick animal.</p>
<h2>Key differentials</h2>
<p>Contagious caprine pleuropneumonia, bluetongue, foot-and-mouth disease, contagious ecthyma (orf), heartwater, and pasteurellosis all need to be considered — several of these overlap significantly in presentation, which is exactly why lab confirmation matters here as much as it does with Newcastle disease in poultry.</p>"""),
    ("Treatment, Control, and Prevention",
     """<h2>Treatment — supportive only, and herd spread isn't stopped by it</h2>
<p>There is no specific antiviral treatment. Supportive care — fluids, antibiotics for secondary bacterial infection — can reduce mortality in individual animals, but it does nothing to stop spread through the rest of the herd. This distinction matters for how you counsel a farmer: treating the sick animal is not the same as controlling the outbreak.</p>
<h2>Control during an outbreak</h2>
<p>Quarantine and movement restriction — PPR is notifiable in Nigeria given its role in regional eradication efforts. Ring vaccination around confirmed outbreaks, and safe carcass disposal and disinfection (the virus is relatively fragile, so routine disinfectants work if applied properly — a real contrast with parvovirus's environmental durability).</p>
<h2>Prevention — the single most cost-effective tool</h2>
<p>A live attenuated PPR vaccine gives strong, often lifelong immunity after a single dose — the cornerstone of national and regional control programs, including Nigeria's participation in continental eradication efforts. Avoid introducing untested new animals without quarantine, and coordinate herd vaccination timing with local veterinary/livestock authorities — regional, not just individual-herd, vaccination is what actually interrupts transmission at scale.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment or your local veterinary/livestock authority's current eradication-program guidance. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why is PPR virus's enveloped structure clinically relevant to how outbreaks are controlled?",
        "Being enveloped makes the virus far less environmentally durable than a non-enveloped virus like parvovirus, "
        "so routine disinfectants work effectively if applied properly during an outbreak.",
        "It makes the virus relatively fragile in the environment, so routine disinfectants work if applied properly",
        "The envelope makes the virus more durable in the environment, requiring specialized disinfectants",
    ),
    (
        "Why can cattle and pigs largely be set aside when investigating a PPR outbreak in a mixed-livestock area?",
        "They can be infected subclinically but aren't significant in maintaining transmission — goats and sheep are "
        "the primary hosts and the actual drivers of herd spread.",
        "They can be infected subclinically but don't play a significant role in maintaining transmission",
        "Cattle and pigs are fully immune to small ruminant morbillivirus and cannot be infected at all",
    ),
    (
        "Why is the high fever that opens a PPR case often missed by farmers?",
        "It's typically the earliest sign, appearing before the more visible signs (oculonasal discharge, oral "
        "erosions, diarrhea) that actually prompt someone to call for help.",
        "It's the earliest sign, usually appearing well before the more visibly alarming signs that follow",
        "PPR does not typically cause a detectable fever in the early stages of infection",
    ),
    (
        "Why does treating a single sick animal with supportive care not solve a PPR outbreak at the herd level?",
        "Supportive care can reduce mortality in that individual animal, but it does nothing to stop spread through "
        "the rest of the herd — outbreak control requires quarantine, movement restriction, and ring vaccination.",
        "It only helps the individual animal and does nothing to stop the disease spreading through the herd",
        "Treating one animal with supportive care reliably halts further spread through the whole herd",
    ),
    (
        "Why is coordinated regional vaccination, not just individual-herd vaccination, emphasized for PPR control?",
        "Regional, coordinated vaccination timing is what actually interrupts transmission at scale — an isolated "
        "individual herd's vaccination alone leaves surrounding susceptible herds as a continuing source of spread.",
        "Only regional, coordinated vaccination timing actually interrupts transmission at a meaningful scale",
        "Individual-herd vaccination alone is fully sufficient to interrupt regional transmission",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Peste des Petits Ruminants: The Disease Threatening Nigeria's Goats and Sheep' — "
        "fifth of the ~30-topic Vet-blog cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="peste-des-petits-ruminants",
                defaults={
                    "title": "Peste des Petits Ruminants: The Disease Threatening Nigeria's Goats and Sheep",
                    "subtitle": "A morbillivirus disease that's economically devastating for smallholder herds — "
                                 "and, unusually, on a real global eradication timeline.",
                    "description": "<p>A 4-module continuing-education course on peste des petits ruminants (PPR) — "
                                    "etiology and why the virus's fragility matters, clinical findings and necropsy "
                                    "lesions, diagnosis and key differentials, and treatment/control/prevention "
                                    "centered on ring vaccination and regional eradication strategy.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "Goat plague is targeted for global eradication by 2030 — here's the real playbook",
                    "sales_subheadline": "4 modules on PPR — clinical recognition, diagnosis, and the vaccination "
                                          "strategy behind Nigeria's role in a real eradication effort.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving goat and sheep clients\n"
                        "Practitioners advising on herd vaccination programs and regional eradication efforts\n"
                        "Anyone wanting the underserved livestock-disease coverage this platform's course catalog has lacked"
                    ),
                    "not_for": (
                        "Smallholder farmers without veterinary training looking for basic herd-management guidance"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "PPR (goat plague) CE for vets — clinical recognition, diagnosis, and "
                                         "vaccination strategy for Nigeria's goats and sheep.",
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
                organization=org, name="Peste des Petits Ruminants — Final Exam",
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
                title="Final Exam — Peste des Petits Ruminants",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
