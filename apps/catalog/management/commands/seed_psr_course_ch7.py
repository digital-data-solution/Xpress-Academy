"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 7 (Training and Staff Development Within and Outside
Nigeria) to the existing "The Public Service Rules — Complete Guide"
course as a new Module, and adds 3 more questions to the course's
existing final exam bank. Requires the course to already exist; safe
to re-run — does nothing if this module has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULE_TITLE = "Chapter 7: Training and Staff Development Within and Outside Nigeria"

MODULE_BODY = """<h2>What staff development actually means</h2>
<p>Staff development is the policy of building staff knowledge, skills, attitude, effectiveness, and efficiency — meeting an officer's own career goals while preparing them for changing duties. It's meant to benefit both the individual and the organization together, by improving performance on both sides at once. Government commits to continuous capacity development strategies through the Public Service Training and Capacity Development Policy, with training opportunities meant to be equitably distributed across all staff in every MDA — not concentrated among a favored few.</p>
<h2>Six categories of in-country training</h2>
<p>A course of instruction within Nigeria is one an officer undertakes locally, but outside their own station, at a Federal Training Centre, university, or approved Public Service training institution. Officers can train under six categories: <strong>Category A</strong> is long-term training toward a postgraduate degree that's crucial to both the officer and the MDA's mandate (governed by Rule 120227). <strong>Category B</strong> is also long-term postgraduate training, but in a field that's beneficial without being crucial to the MDA's mandate. <strong>Category C</strong> covers officers pursuing a degree or qualification that may not even relate to their current duties. <strong>Category D</strong> is in-house training — customized, cost-effective, short-term, delivered on or off the premises. <strong>Category E</strong> is short-term online courses, which MDAs must make adequately available across cadres and grade levels for skills development. <strong>Category F</strong> is online courses leading to an actual degree from an accredited institution, again meant to be open across cadres and grade levels.</p>
<h2>Training on-station vs. overseas</h2>
<p>A course of instruction "on station" happens locally within the officer's own station — accredited centers, approved locations, Management Development Institutions, or the MDA's own training hubs. An overseas course is one undertaken outside Nigeria entirely. An officer sent outside Nigeria for duties or training must be given detailed instructions and told in advance, in writing, exactly what allowances and travel facilities they're entitled to at government expense — this comes from their own Permanent Secretary or Head of Extra-Ministerial Office.</p>
<h2>The bond, and what it actually requires</h2>
<p>Attending a course of instruction comes with real strings: the officer must sign a bond to refund all associated government expenses if they fail to (a) obtain a certificate of satisfactory attendance, (b) return to Nigeria afterward, (c) avoid taking any further course without specific government approval, or (d) avoid resigning within three years of completing the course. This is a genuine financial commitment, not a formality.</p>
<h2>Passage, allowances, and outside pay</h2>
<p>A senior officer sent overseas gets free air passage for themselves alone — but if the course runs nine months or longer, their spouse may travel at government expense too. Special allowance rates apply to certain named courses, uniformly for every officer attending. Where a donor agency or country sponsors a course with government's prior approval, the officer is entitled to the difference if the donor's own allowance/facilities package is lower than the standard estacode allowance. An officer who receives a salary from an overseas employer during training loses eligibility for Federal Government emoluments or allowances, unless the Permanent Secretary of the Career Management Office at OHCSF specifically approves otherwise.</p>
<h2>A specific protection tied to pregnancy</h2>
<p>A female officer about to start a training course of six months or less must enter an agreement to refund all or part of its cost only if the course is interrupted specifically on grounds of pregnancy — a targeted, narrow condition, not a general repayment obligation for any interruption.</p>
<h2>Externally assisted and technical-assistance courses</h2>
<p>Where training under a foreign government's technical assistance scheme is needed, nomination applications go through the National Planning Commission for processing. Officers on such technical-assistance courses keep receiving their normal emoluments, while every other condition of service follows the existing arrangement between the donor government and Nigeria. Where an officer requests a course purely for their own reasons, the Head of the Civil Service of the Federation's office can impose special conditions — including leave without pay and withdrawal of some or all of the usual allowances — but the Permanent Secretary must tell the officer, in writing, exactly what those conditions are before they depart.</p>
<h2>Postgraduate study leave — capped, but real</h2>
<p>For a postgraduate course not available at any Nigerian institution, an officer may in exceptional cases be granted study leave with pay, capped at four years. Separately, officers pursuing private studies for a higher degree on their own aren't blocked from doing so, provided it doesn't interfere with their official duties.</p>"""

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "What is the difference between Training Category A and Category B under the PSR?",
        "Rule 070105(a)-(b): both are long-term postgraduate training, but Category A's field of study is "
        "'very crucial' to the MDA's mandate, while Category B's is merely 'beneficial' but not crucial.",
        "Category A's field is crucial to the MDA's mandate; Category B's is merely beneficial",
        "Category A is short-term training; Category B is long-term training",
    ),
    (
        "For a course of nine months or more, who else may accompany a senior officer sent overseas, at government expense?",
        "Rule 070206: where the course duration is not less than nine months, the officer's spouse may "
        "accompany them at Government expense.",
        "Their spouse",
        "Any one of their dependent children",
    ),
    (
        "What is the maximum period of study leave with pay for a postgraduate course not offered by any Nigerian institution?",
        "Rule 070304: officers may be granted study leave with pay subject to a maximum of four years, in "
        "exceptional cases.",
        "Four years",
        "Two years",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 7 to the PSR course and its final exam. Safe to re-run."

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        course = Course.objects.filter(organization=org, slug="public-service-rules-guide").first()
        if not course:
            raise CommandError("Course 'public-service-rules-guide' not found — run seed_psr_course first.")

        if Module.objects.filter(course=course, title=MODULE_TITLE).exists():
            self.stdout.write(self.style.WARNING(f"'{MODULE_TITLE}' already exists on this course — leaving as-is."))
            return

        with transaction.atomic():
            next_order = (Module.objects.filter(course=course).order_by("-order").values_list("order", flat=True).first() or 0) + 1
            module = Module.objects.create(
                course=course, order=next_order, title=MODULE_TITLE, unlock_rule=Module.UnlockRule.SEQUENTIAL,
            )
            Lesson.objects.create(
                module=module, order=1, title=MODULE_TITLE, type=Lesson.Type.TEXT,
                body=MODULE_BODY.strip(), is_preview=False,
            )
            self.stdout.write(self.style.SUCCESS(f"Added module: {MODULE_TITLE}"))

            bank = QuestionBank.objects.filter(
                organization=org, name="Public Service Rules — Complete Guide Final Exam"
            ).first()
            if not bank:
                raise CommandError("Final exam question bank not found — run seed_psr_course first.")

            for stem, explanation, correct, wrong in NEW_FINAL_EXAM_QUESTIONS:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.MEDIUM,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
            self.stdout.write(self.style.SUCCESS(f"  Added {len(NEW_FINAL_EXAM_QUESTIONS)} final-exam questions."))

            quiz = Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=course).first()
            if quiz:
                total = bank.questions.count()
                quiz.question_count = total
                quiz.instructions = f"{total} questions covering the full course. Pass to unlock your certificate."
                quiz.save(update_fields=["question_count", "instructions"])
                self.stdout.write(self.style.SUCCESS(f"  Final exam now draws from {total} questions."))

        self.stdout.write(self.style.SUCCESS("Done."))
