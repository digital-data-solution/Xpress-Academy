import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# Flagship course built from Dr. Omale's own 116-page "Post-Mortem
# Diagnosis of Poultry Diseases" atlas (v3, Sept 2026): Part I method +
# 37 disease chapters + appendices, one lesson per chapter. Lesson HTML
# and the 86 figures were converted from the .docx by a one-off script
# into apps/catalog/data/poultry_necropsy_atlas.json and
# static/courses/poultry-necropsy-atlas/ (served by whitenoise, so no
# Supabase storage is used).
#
# Figures are CC BY / CC BY-SA / public domain. Every caption keeps its
# credit line, and the Appendix C credits lesson is a free preview so
# the attribution is public. Treatment lines keep the atlas's
# "follow the label and local regulations" wording. Don't remove either.

DATA = Path(__file__).resolve().parents[2] / "data" / "poultry_necropsy_atlas.json"
QUIZ_DATA = DATA.with_name("poultry_necropsy_atlas_quiz.json")
SLUG = "poultry-post-mortem-diagnosis-atlas"

WELCOME = """<h2>Welcome</h2>
<p>This course is the complete <strong>Post-Mortem Diagnosis of Poultry Diseases</strong> atlas, one lesson per chapter:
the step-by-step necropsy method, sampling for the laboratory, a lesion-based differential key, and 37 disease chapters
(viral, bacterial, fungal, parasitic, nutritional/metabolic/toxic and reproductive), illustrated with 86 labelled photographs.</p>
<h2>How to use it</h2>
<p>Work through Part I first: it is the method every disease chapter relies on. After that, use the disease modules in any order,
and keep the lesion-based differential key (Part I, lesson 7) open at the necropsy table.</p>
<h2>Important limits</h2>
<ul>
<li>This is continuing education, not a substitute for laboratory confirmation or a veterinarian's clinical judgement.</li>
<li>Drug choices, doses and withdrawal periods must follow the product label and the veterinary medicines regulations of your country (in Nigeria, NAFDAC-registered products).</li>
<li>HPAI and Newcastle disease are notifiable: on suspicion, stop and report to the veterinary authorities.</li>
<li>Photographs are open-licence images from Wikimedia Commons and open-access journals; credits are under each figure and in the final lesson.</li>
</ul>"""


class Command(BaseCommand):
    help = "Seeds the Poultry Post-Mortem Diagnosis atlas course (unpublished). Safe to re-run."

    def add_arguments(self, parser):
        parser.add_argument("--price", type=int, default=20000, help="Price in NGN (default 20000; confirm with Sam).")
        parser.add_argument("--publish", action="store_true",
                            help="Also approve and publish (same as publish_psr_courses). Sam's call only.")
        parser.add_argument("--sync-content", action="store_true",
                            help="Course already exists: update each lesson's text in place from the JSON "
                                 "(matched by title). Never deletes anything, so learner progress is kept.")

    def handle(self, *args, **options):
        if options["sync_content"]:
            self._sync_content()
            return
        self._seed(options)
        if options["publish"]:
            course = Course.objects.filter(slug=SLUG).first()
            if course and not course.is_published:
                course.review_status = Course.ReviewStatus.APPROVED
                course.is_published = True
                course.save()
                self.stdout.write(self.style.SUCCESS(f"Published: /courses/{SLUG}/"))

    def _seed(self, options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return
        data = json.loads(DATA.read_text(encoding="utf-8"))

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
                organization=org, programme=programme, slug=SLUG,
                defaults={
                    "title": "Poultry Post-Mortem Diagnosis: The Complete Field Atlas",
                    "subtitle": "Step-by-step necropsy, sampling and lesion-based diagnosis of 37 poultry diseases, "
                                 "with 86 labelled photographs.",
                    "description": "<p>The full field atlas as a course: a fixed necropsy routine, correct laboratory "
                                    "sampling, a lesion-based differential key, and one chapter per disease covering "
                                    "cause, signs, organ-by-organ lesions, pathognomonic findings, differentials, "
                                    "laboratory confirmation and control, written for Nigerian conditions.</p>",
                    "audience": Audience.VET,
                    "level": Course.Level.ADVANCED,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": options["price"],
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 12,
                    "is_published": False,
                    "sales_headline": "Read the carcass, not the guesswork",
                    "sales_subheadline": "A complete, photo-illustrated post-mortem atlas for poultry vets: "
                                          "method, sampling and 37 diseases.",
                    "target_audience": (
                        "Veterinarians and vet students doing poultry necropsies\n"
                        "Animal health technicians and poultry farm vets in Nigeria and West Africa\n"
                        "Lecturers who want a structured, illustrated teaching reference"
                    ),
                    "not_for": "Farmers looking for home treatment instructions — this course teaches diagnosis for professionals",
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    "meta_description": "Poultry post-mortem diagnosis course: necropsy method, sampling and 37 "
                                         "diseases with 86 labelled photographs.",
                },
            )
            if not created:
                if course.quizzes.exists() or Quiz.objects.filter(module__course=course).exists():
                    self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                else:
                    self._seed_quizzes(org, course)
                return

            parts = data["parts"]
            order = 0
            for p_idx, part in enumerate(parts):
                order += 1
                module = Module.objects.create(
                    course=course, order=order, title=part["title"],
                    unlock_rule=Module.UnlockRule.IMMEDIATE,  # a reference atlas: let learners jump to any disease
                )
                lessons = list(part["lessons"])
                l_order = 0
                if p_idx == 0:
                    l_order += 1
                    Lesson.objects.create(module=module, order=l_order, title="Welcome and how to use this course",
                                          type=Lesson.Type.TEXT, body=WELCOME, is_preview=True)
                for les in lessons:
                    l_order += 1
                    num = f"{les['number']}. " if les.get("number") else ""
                    is_credits = les["title"].startswith("Appendix C")
                    Lesson.objects.create(
                        module=module, order=l_order, title=f"{num}{les['title']}"[:255],
                        type=Lesson.Type.TEXT, body=les["html"],
                        # Method chapter 4 + Newcastle (first disease) as free samples; credits always public.
                        is_preview=is_credits or les.get("number") in (4, 8),
                    )
            self.stdout.write(self.style.SUCCESS(
                f"Created {course.title}: {len(parts)} modules, "
                f"{sum(len(p['lessons']) for p in parts) + 1} lessons, {data['figures']} figures."
            ))
            self._seed_quizzes(org, course)
        if not options["publish"]:
            self.stdout.write(self.style.SUCCESS(
                "Course is UNPUBLISHED. Re-run with --publish (or approve + publish in admin) to go live."
            ))

    @transaction.atomic
    def _sync_content(self):
        course = Course.objects.filter(slug=SLUG).first()
        if not course:
            self.stderr.write(self.style.ERROR("Course not found — run without --sync-content first."))
            return
        data = json.loads(DATA.read_text(encoding="utf-8"))
        changed = missing = 0
        for part in data["parts"]:
            for les in part["lessons"]:
                num = f"{les['number']}. " if les.get("number") else ""
                title = f"{num}{les['title']}"[:255]
                lesson = Lesson.objects.filter(module__course=course, title=title).first()
                if lesson is None:
                    missing += 1
                    self.stdout.write(self.style.WARNING(f"  Not found, skipped: {title}"))
                elif lesson.body != les["html"]:
                    lesson.body = les["html"]
                    lesson.save(update_fields=["body"])
                    changed += 1
                    self.stdout.write(f"  Updated: {title}")
        self.stdout.write(self.style.SUCCESS(f"Synced {course.title}: {changed} lesson(s) updated, {missing} not found."))

    def _make_bank(self, org, name, description, items):
        bank = QuestionBank.objects.create(organization=org, name=name, description=description)
        for item in items:
            q = Question.objects.create(
                bank=bank, type=Question.Type.MCQ, stem=item["stem"], explanation=item["explanation"],
                difficulty=Question.Difficulty.MEDIUM, source_note="Poultry Post-Mortem Diagnosis atlas v3",
            )
            for i, text in enumerate(item["options"], start=1):
                Choice.objects.create(question=q, text=text, is_correct=(i == 1), order=i)
        return bank

    @transaction.atomic
    def _seed_quizzes(self, org, course):
        """Case-based module quizzes + a final exam drawn from every module plus integrative cases.
        The first option in the JSON is the correct one; Quiz.randomize_choices shuffles them."""
        quiz = json.loads(QUIZ_DATA.read_text(encoding="utf-8"))
        modules = {m.order: m for m in course.modules.all()}
        all_items = []
        for order, items in quiz["modules"].items():
            module = modules[int(order)]
            bank = self._make_bank(org, f"{course.title} — {module.title}",
                                   "Case-based module quiz.", items)
            Quiz.objects.create(
                scope=Quiz.Scope.MODULE, module=module, title=f"Case quiz — {module.title}",
                instructions=f"{len(items)} case-based questions. 70% to pass; unlimited attempts.",
                bank=bank, question_count=len(items), pass_mark=70, max_attempts=0, time_limit_minutes=0,
            )
            all_items += items
        all_items += quiz["final_only"]
        final_bank = self._make_bank(org, f"{course.title} — Final Exam",
                                     "Every module's cases plus integrative cases; unlocks the certificate.",
                                     all_items)
        Quiz.objects.create(
            scope=Quiz.Scope.FINAL, course=course, title="Final Exam — Poultry Post-Mortem Diagnosis",
            instructions="40 case-based questions drawn from the whole course. Pass 70% to unlock your certificate.",
            bank=final_bank, question_count=min(40, len(all_items)), pass_mark=70,
            max_attempts=0, time_limit_minutes=60,
        )
        course.requires_final_assessment = True
        course.save(update_fields=["requires_final_assessment"])
        self.stdout.write(self.style.SUCCESS(
            f"Created {len(quiz['modules'])} module quizzes and a final exam (bank of {len(all_items)} questions)."
        ))
