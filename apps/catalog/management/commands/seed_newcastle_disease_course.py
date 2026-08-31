from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# First of the ~30 single-topic CE courses cross-promoting the Vet
# Marketplace blog's new MSD-Veterinary-Manual-grounded article series
# (topic list + full article text relayed by the Vet session, sourced
# from MSD's real category structure — approved by Sam to build in
# batches, matched to the pace the blog side is actually writing at,
# not all 30 at once). This is deliberately a narrower, single-disease
# "micro-course" shape rather than the broader multi-topic CE courses
# built earlier (Canine Reproduction, the 3-course Poultry series) —
# matches one blog post 1:1, same cross-promotion pattern as the
# course-publish webhook already wired between the two platforms.
#
# Same honesty discipline as every other vet CE course on this
# platform: this content has NOT been reviewed by a credentialed
# veterinarian beyond Sam himself — flagged explicitly in the closing
# module, not just in this comment.

MODULES = [
    ("Etiology and Epidemiology",
     """<h2>What causes Newcastle disease</h2>
<p>Newcastle disease (ND) is caused by avian orthoavulavirus 1 (formerly Newcastle disease virus, NDV), a single-stranded, negative-sense RNA virus in the family Paramyxoviridae. Strains are classified into three pathotypes by pathogenicity: <strong>velogenic</strong> (highly virulent, high mortality, systemic or neurological disease), <strong>mesogenic</strong> (moderate virulence, respiratory/nervous signs, lower mortality mainly in young birds), and <strong>lentogenic</strong> (low virulence, often subclinical — several lentogenic strains, LaSota and Hitchner B1, are used as live vaccines).</p>
<p>The virus is enveloped and relatively fragile outside the host, but it survives well in cool, moist conditions — contaminated litter, water, and equipment — and can persist for weeks in a shaded poultry house.</p>
<h2>Why it matters in Nigeria specifically</h2>
<p>ND is endemic across much of sub-Saharan Africa, including Nigeria, where it is the leading cause of mortality in village and backyard poultry and a constant biosecurity threat to commercial layer and broiler operations. Depending on strain and flock immune status, mortality can reach 100% within days of onset in an unvaccinated flock.</p>
<h2>Host range and transmission</h2>
<p>Chickens are most susceptible, but the virus infects a very wide host range — turkeys, guinea fowl, pigeons, ducks, geese, and numerous wild and captive bird species, many of which shed virus with few or no clinical signs and act as a reservoir. Transmission is primarily respiratory and oral: inhalation of aerosolized virus, or ingestion of virus-contaminated feed, water, droppings, or fomites (crates, footwear, vehicles, staff clothing).</p>
<p>The three most consistently identified risk factors for outbreaks in Nigerian production systems: live bird markets, movement of scavenging village poultry between compounds, and introduction of untested new stock.</p>"""),
    ("Clinical Findings and Lesions",
     """<h2>Signs by system</h2>
<p>Signs vary with pathotype, age, immune status, and secondary infections, appearing 2 to 15 days after exposure:</p>
<ul>
<li><strong>Respiratory</strong> — gasping, coughing, nasal discharge, rales</li>
<li><strong>Digestive</strong> — greenish, watery diarrhea</li>
<li><strong>Nervous</strong> — tremors, torticollis (twisted neck), circling, wing droop, complete paralysis of legs and wings, typically appearing several days after the respiratory/digestive phase in velogenic infections, or dominant in mesogenic strains</li>
<li><strong>Production effects</strong> — sudden, sharp drop in egg production, and soft-shelled, misshapen, or depigmented eggs in layers that survive</li>
</ul>
<p>In peracute velogenic outbreaks, sudden death with few premonitory signs is common — this is often the first thing a farmer or field vet actually sees.</p>
<h2>What necropsy shows</h2>
<p>Gross lesions are most consistent in the digestive tract: hemorrhagic and necrotic lesions of the proventriculus (particularly at the junction with the gizzard), petechiae on the tips of intestinal lymphoid tissue (Peyer's patches, cecal tonsils), and tracheal hemorrhage and mucus. Splenic and pancreatic necrotic foci may appear with some velogenic strains.</p>
<h2>The critical diagnostic caveat</h2>
<p>These gross lesions overlap substantially with highly pathogenic avian influenza (HPAI) — necropsy findings alone cannot distinguish the two. This is not a minor technicality: it's the reason lab confirmation is required before any control decision, not an optional extra step.</p>"""),
    ("Diagnosis and Differentials",
     """<h2>Building the diagnosis</h2>
<p>Clinical suspicion comes from history and signs — a sudden drop in egg production, nervous signs, high mortality — supported by gross necropsy findings consistent with ND. Neither is confirmatory on its own.</p>
<h2>Confirmatory testing</h2>
<ul>
<li>Virus isolation in embryonated chicken eggs, followed by hemagglutination (HA) and hemagglutination-inhibition (HI) testing</li>
<li>RT-PCR for rapid detection and pathotyping (sequencing the F protein cleavage site)</li>
<li>Paired serology (HI titers) on recovering flocks where virus isolation isn't feasible</li>
</ul>
<h2>Key differentials to rule out</h2>
<p>Highly pathogenic avian influenza (the most critical to distinguish, given the lesion overlap), infectious bronchitis, infectious laryngotracheitis, fowl cholera, and infectious bursal disease.</p>
<h2>Reporting obligation</h2>
<p>Newcastle disease is notifiable in Nigeria and most jurisdictions — a suspected outbreak isn't just a clinical matter, it triggers a reporting obligation to the relevant veterinary authority.</p>"""),
    ("Treatment, Control, Prevention, and Zoonotic Risk",
     """<h2>Treatment — supportive only</h2>
<p>There is no specific antiviral treatment for Newcastle disease. Management is supportive — warmth, fluids, reduced stress — aimed at limiting secondary bacterial infection while the bird's own immune response runs its course (or doesn't).</p>
<h2>Control once disease is present</h2>
<p>Isolate or cull affected and in-contact birds where regulation requires it; restrict movement of birds, eggs, equipment, and personnel; disinfect with a product effective against enveloped viruses after removing organic matter; notify the relevant veterinary authority.</p>
<h2>Prevention — where the real leverage is</h2>
<p>Live vaccines (LaSota, Hitchner B1) via eye drop, drinking water, or spray, starting in the first week of life with boosters through lay; inactivated (killed) vaccines by injection to layers and breeders for longer-lasting, higher-titer immunity. Vaccination schedules should be set with a licensed veterinarian based on local disease pressure, maternal antibody levels, and production type — this course does not substitute for that individualized decision.</p>
<p>Biosecurity fundamentals that meaningfully reduce risk: controlled entry, footbaths, quarantine of new stock, avoiding live bird markets for breeding stock, and rodent/wild bird control.</p>
<h2>Zoonotic risk</h2>
<p>ND can cause a mild, self-limiting conjunctivitis in people with heavy occupational exposure (lab workers, vaccination teams) — no systemic illness in humans. Standard precautions are sufficient; this is not a disease that should drive panic in farm staff, but it's worth knowing honestly rather than either overstating or ignoring.</p>
<h2>A note on this course's limits</h2>
<p>This is continuing-education content, not a substitute for a licensed veterinarian's own clinical judgment, a specific vaccination protocol, or your local veterinary authority's current guidance. As with all veterinary CE content on this platform, it has not yet been reviewed by a credentialed veterinarian beyond Dr. Omale himself — treat it as a solid starting reference, not a final word.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "Why can't gross necropsy findings alone confirm a diagnosis of Newcastle disease?",
        "ND's gross lesions — particularly the proventricular and intestinal lymphoid findings — overlap substantially "
        "with highly pathogenic avian influenza, so lab confirmation (virus isolation, RT-PCR, or serology) is required "
        "before any control decision is made.",
        "Its lesions overlap substantially with highly pathogenic avian influenza, so lab testing is required to tell them apart",
        "Necropsy lesions are fully specific to Newcastle disease and no further testing is ever needed",
    ),
    (
        "What are the three most consistently identified risk factors for ND outbreaks in Nigerian production systems?",
        "Live bird markets, movement of scavenging village poultry between compounds, and introduction of untested new "
        "stock are the three factors most consistently linked to outbreaks in this setting.",
        "Live bird markets, movement of village poultry between compounds, and introducing untested new stock",
        "Cold weather, vaccine storage temperature, and feed brand are the leading identified risk factors",
    ),
    (
        "Why are lentogenic NDV strains like LaSota and Hitchner B1 significant beyond being a mild pathotype?",
        "Their low virulence is exactly what makes them usable as live vaccines — the same strains that cause mild or "
        "subclinical disease naturally are deliberately administered to build immunity.",
        "They're low-virulence strains that are deliberately used as live vaccines",
        "They are the primary cause of the high-mortality outbreaks seen in unvaccinated flocks",
    ),
    (
        "Is there a specific antiviral treatment for Newcastle disease in an affected bird?",
        "No — management is supportive only (warmth, fluids, reduced stress, limiting secondary bacterial infection); "
        "prevention through vaccination and biosecurity is where the real intervention happens.",
        "No — treatment is supportive only; prevention via vaccination and biosecurity is the real control point",
        "Yes — a specific antiviral is standard first-line treatment once ND is confirmed",
    ),
    (
        "What is the real zoonotic risk of Newcastle disease to farm or lab staff?",
        "It can cause a mild, self-limiting conjunctivitis in people with heavy occupational exposure — no systemic "
        "illness in humans, and standard precautions are sufficient.",
        "A mild, self-limiting conjunctivitis in heavily exposed workers, with no systemic illness in humans",
        "ND causes severe systemic illness in humans and requires the same containment as a major zoonosis",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'Newcastle Disease in Poultry: Recognition, Response, and Prevention' — "
        "a single-topic CE micro-course matching a Vet Marketplace blog post, first of "
        "the ~30-topic cross-promotion batch. Safe to re-run."
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
                organization=org, programme=programme, slug="newcastle-disease-in-poultry",
                defaults={
                    "title": "Newcastle Disease in Poultry: Recognition, Response, and Prevention",
                    "subtitle": "Etiology, clinical signs, diagnosis, and control for the leading cause of poultry "
                                 "mortality in unvaccinated Nigerian flocks.",
                    "description": "<p>A 4-module continuing-education course on Newcastle disease — etiology and "
                                    "epidemiology, clinical findings and necropsy lesions, diagnosis and key "
                                    "differentials (including why HPAI can't be ruled out on lesions alone), and "
                                    "treatment/control/prevention including real biosecurity guidance for Nigerian "
                                    "production systems.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.INTERMEDIATE,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 3000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 1.5,
                    "is_published": False,
                    "sales_headline": "The disease costing village and backyard flocks the most — in clinical depth",
                    "sales_subheadline": "4 modules on Newcastle disease: recognition, diagnosis, and real prevention "
                                          "guidance for Nigerian production conditions.",
                    "target_audience": (
                        "Licensed veterinarians and vet techs serving poultry clients\n"
                        "Practitioners wanting a focused refresher on one specific, high-impact disease\n"
                        "Anyone working the existing Poultry Health & Biosecurity course who wants deeper single-topic detail"
                    ),
                    "not_for": (
                        "Farmers or breeders without veterinary training looking for basic flock-management guidance — "
                        "see the Poultry Health & Biosecurity course instead"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Newcastle disease CE for vets — etiology, diagnosis, and prevention for "
                                         "Nigeria's leading cause of poultry mortality.",
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
                organization=org, name="Newcastle Disease in Poultry — Final Exam",
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
                title="Final Exam — Newcastle Disease in Poultry",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin. "
            "Link from the matching Vet Marketplace blog post once both are live."
        ))
