"""Follow-up to seed_psr_course.py — appends Chapter 3 (Prescribed
Examination for Confirmation) to the existing "The Public Service
Rules — Complete Guide" course as a new Module, and adds 3 more
questions to the course's existing final exam bank, exactly matching
the pattern documented in seed_psr_course.py's own docstring
("seed_psr_course_ch<N>.py-style follow-ups"). Requires the course to
already exist (run seed_psr_course.py first); safe to re-run — does
nothing if this module has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULE_TITLE = "Chapter 3: Prescribed Examination for Confirmation"

MODULE_BODY = """<h2>Two exams, not one</h2>
<p>On joining the Service, every officer must complete an induction training course and then pass a prescribed confirmation examination — the Compulsory Confirmation Examination for Senior Officers, or the Compulsory Confirmation/Promotion Examination for Junior Officers, depending on grade. Passing this exam is a real precondition for being confirmed in post, not a formality.</p>
<h2>Who runs it</h2>
<p>The Career Management Office (CMO), in the Office of the Head of the Civil Service of the Federation, is responsible for conducting and supervising the examinations, through a dedicated Examination Board chaired by the Permanent Secretary, CMO (OHCSF), with the Director, Learning and Development Department (OHCSF) serving as Secretary — plus representatives from the Federal Civil Service Commission and several key Ministries. The exam is held once a year.</p>
<h2>The real deadlines — and the real consequences</h2>
<p>Every officer must take the confirmation examination within two years of taking up their appointment. An officer who fails to take the exam at all within three years of their first appointment is required to resign. Separately, an officer who fails the examination itself after three consecutive attempts must also resign or withdraw from the service. These are two distinct failure modes — never sitting the exam, and never passing it — and both carry the same hard consequence.</p>
<h2>What's tested, and how</h2>
<p>Senior Officers (COMPRO I &amp; III) sit three groups of papers: Group A is Law (the Nigerian Legal System and key legislation such as the Constitution, the Official Secrets Act, and the Interpretation Act); Group B covers Official Publications and other subject areas — the Public Service Rules, Financial Regulations, Computer Appreciation, a General Paper, and role-specific papers for Police, Customs, Immigration, Correctional, Civil Defence, Road Safety, and Fire Service officers; Group C tests Computer Appreciation and Literacy on its own. An Administrative Officer/Professional with a Nigerian law qualification, or who has been called to the Nigerian Bar, is exempt from Group A. During the exam, reference books such as the PSR, Financial Regulations, and the Civil Service Handbook are generally allowed — except for the General Paper, Office Procedure/Routine, and Special Paper components, which are closed-book.</p>
<h2>Junior Officers (COMPRO II)</h2>
<p>Junior Officers sit a different set of papers: the Public Service Rules, Financial Regulations, Computer Appreciation and Literacy, a General Paper, English Language, and Office Routine/Special Paper — plus Elementary Mathematics specifically for Clerical Assistants on GL.03. A Clerical Officer on GL.04 whose result is exceptional passes at "accelerated level" — they're automatically advanced to GL.06 after one year of Certificate in Supervisory General Management (CSGM) training, and converted to the Executive Officer cadre.</p>
<h2>Eligibility and edge cases</h2>
<p>Officers directly appointed to the Federal Public Service become eligible to sit the exam once they've served six months, and must pass within two years of appointment. The same requirement extends to officers promoted from unconfirmed junior posts, and to officers transferred from another scheduled Service who are under 40 at the date of transfer and haven't yet satisfied confirmation conditions. For further advancement beyond GL.10, officers must additionally attend an approved institution — ASCON, PSIN, CMD, or similar — and pass its prescribed examination. Where the Gazette of First Appointment and Confirmation of Appointment isn't available within two years, the COMPRO result itself is used in its place. Unconfirmed Senior Police Officers and unconfirmed Para-Military Officers (Senior and Junior) face the same compulsory confirmation requirement in their own services. Examiner and invigilator fees are set from time to time by the Office of the Head of the Civil Service of the Federation.</p>"""

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "How often is the PSR confirmation examination held?",
        "Rule 030106: confirmation examination shall be held once a year.",
        "Once a year",
        "Twice a year",
    ),
    (
        "What happens to an officer who fails to take the confirmation examination at all within three years of their first appointment?",
        "Rule 030105: an officer who fails to take the confirmation examination after 3 years of first "
        "appointment shall be required to resign from the service.",
        "They are required to resign from the service",
        "They face no consequence, provided they eventually sit it",
    ),
    (
        "Which officers are exempt from Group A (the Law Examination) of the confirmation exam?",
        "Rule 030109: an Administrative Officer/Professional with a Nigerian law qualification, or who has "
        "been called to the Nigerian Bar, is exempted from taking Group A.",
        "Administrative Officers/Professionals with a Nigerian law qualification, or called to the Nigerian Bar",
        "Officers who have served more than ten years, regardless of qualification",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 3 to the PSR course and its final exam. Safe to re-run."

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
