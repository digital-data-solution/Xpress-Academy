"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 11 (Petitions and Appeals) to the existing "The
Public Service Rules — Complete Guide" course as a new Module, and
adds 3 more questions to the course's existing final exam bank.
Requires the course to already exist; safe to re-run — does nothing
if this module has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULE_TITLE = "Chapter 11: Petitions and Appeals"

MODULE_BODY = """<h2>Appeal vs. petition — a real distinction</h2>
<p>An appeal is a formal request from an aggrieved officer for reconsideration of a decision by the appropriate authority. A petition is broader — a formal complaint made to an appropriate authority about a matter affecting the officer personally, or touching on general or public interest. They're related but not identical tools.</p>
<h2>Where representations actually go</h2>
<p>Every officer's representation to government has a specific correct channel: the Chairman of the Federal Civil Service Commission for appointment, promotion, transfer, and discipline matters; the Head of the Civil Service of the Federation for other conditions of service like leave, passages, allowances, pensions, and gratuities; or the Head of the MDA or Head of Government for issues bordering mostly on general or public interest. An officer addressing the Head of Government directly must still transmit the communication unsealed, in triplicate, through one of these proper channels — anything received outside that channel gets returned to the writer. This isn't bureaucratic gatekeeping for its own sake; it exists so every communication is properly verified and reported on before it reaches the top.</p>
<h2>Timing, and exhausting internal remedies first</h2>
<p>An appeal from an aggrieved officer must be handled and concluded within six months. Officers are expected to exhaust the avenues the PSR and Circulars already provide before turning to the courts — and separately, must obtain the Head of the Civil Service of the Federation's permission before proceeding to court at all, without this overriding their actual constitutional rights.</p>
<h2>No shortcuts through influence</h2>
<p>Consistent with the general prohibition on seeking outside influence, an officer dissatisfied with a decision must first raise it with their immediate superior officer or Permanent Secretary. Only if that doesn't resolve things does a formal appeal or petition to the appropriate authority become the proper next step.</p>
<h2>Routing, copies, and identity — the mechanics that matter</h2>
<p>An appeal or petition must go through the proper departmental channel — the petitioner's immediate superior and their Permanent Secretary — who forwards it with their own comments and recommendations to the Chairman of the FCSC or the Head of the Civil Service of the Federation. It must be submitted in duplicate (an advance copy may go directly to the final authority, with evidence the proper channel was also used), and must carry the petitioner's full name, staff number, signature, and address. Where someone else writes it on the petitioner's behalf, that writer's own signature and address go on it too — and if it's written on behalf of an illiterate person, the petition must say so explicitly.</p>
<h2>What gets a petition rejected outright</h2>
<p>An appeal or petition won't be entertained if it fails to follow the proper channel, concerns a matter already before a court of law, is illegible or meaningless, uses abusive or improper language, or simply repeats an earlier petition without adding anything new. It also won't be entertained if submitted more than six months after the decision being complained of — unless the delay comes with a genuinely valid reason. Finally, every petition must close with a concise statement of the actual redress being sought, and if it runs longer than two foolscap pages, it needs its own summary of the supporting reasons.</p>"""

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "Under the PSR, what is the difference between an 'appeal' and a 'petition'?",
        "Rule 110101: an appeal is a formal request for reconsideration of a specific decision; a petition is "
        "a broader formal complaint about a matter affecting the officer personally or the general/public "
        "interest.",
        "An appeal seeks reconsideration of a specific decision; a petition is a broader formal complaint",
        "They are fully interchangeable terms with no meaningful distinction",
    ),
    (
        "Within how long must an appeal from an aggrieved officer be handled and concluded?",
        "Rule 110201(i): appeal from an aggrieved Officer shall be handled and concluded within six months.",
        "Six months",
        "One month",
    ),
    (
        "Will an appeal/petition be entertained if it merely repeats the substance of a previous petition?",
        "Rule 110208(a)(v): a petition which merely repeats the substance of a previous petition without "
        "introducing new relevant matter will not be entertained.",
        "No, unless it introduces new relevant matter",
        "Yes, repetition alone is never grounds for rejection",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 11 to the PSR course and its final exam. Safe to re-run."

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
