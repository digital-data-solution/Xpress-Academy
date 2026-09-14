"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 16 (Compensation and Insurance) to the existing "The
Public Service Rules — Complete Guide" course as a new Module, and
adds 3 more questions to the course's existing final exam bank.
Requires the course to already exist; safe to re-run — does nothing
if this module has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULE_TITLE = "Chapter 16: Compensation and Insurance"

MODULE_BODY = """<h2>Private property — largely the officer's own responsibility</h2>
<p>Officers generally aren't entitled to compensation from public funds for property lost in circumstances outside their service — which is exactly why the Rules explicitly suggest officers consider insuring their own property against loss or damage. This isn't government being indifferent; it's a deliberate boundary on what public funds cover.</p>
<h2>Death in active service</h2>
<p>Where an officer dies while still in active service, their legal representative — or whoever they designated as Next of Kin during their lifetime — receives their entitlements under the life insurance policy maintained under Section 8 of the Pension Reform Act 2014. This is a real, structured benefit, not a discretionary payout.</p>
<h2>Vehicle damage on official duty</h2>
<p>If an officer's own private vehicle is damaged as a direct result of civil disturbance while being used for official duties, government accepts responsibility — and "official duties" here deliberately includes the ordinary commute between house and office, not just formal assignments. Separately, if that same vehicle is damaged beyond repair in an accident during official duty, government covers the gap between what the insurance indemnity pays out and the actual cost of replacing the vehicle.</p>
<h2>When an officer goes missing</h2>
<p>If an officer is reported missing and still not found a full year after being declared missing, a Board of Enquiry is convened to determine, based on the available information and circumstances, whether it's reasonable to presume the officer is dead. Where that presumption is made, the Next of Kin becomes entitled to the death benefit under the Group Life Assurance Scheme, plus the full accrued balance of the officer's Retirement Savings Account.</p>
<h2>Health insurance while working abroad</h2>
<p>An officer on official assignment outside Nigeria gets free health insurance cover for the whole duration of that assignment, with government paying the premium. Where the officer makes a stop-over en route to their actual approved destination, though, they're responsible for arranging their own insurance for that stop-over leg — government's cover only applies once they've reached the assignment itself.</p>
<h2>Compensation for injury or death — a real, timed obligation</h2>
<p>Compensation for fatal cases or injuries — whether they happen at the workplace or outside it — is handled under the Employees' Compensation Act 2010, and payment is required within three months of the incident. This is a hard deadline, not an aspirational target.</p>"""

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "Where an officer dies in active service, what is paid to their legal representative or designated Next of Kin?",
        "Rule 160201: entitlements under the life insurance policy maintained under Section 8 of the Pension "
        "Reform Act, 2014.",
        "Their entitlements under the life insurance policy maintained under Section 8 of the Pension Reform Act, 2014",
        "A one-time discretionary gift determined by the Permanent Secretary",
    ),
    (
        "How long after an officer is declared missing must they remain not found before a Board of Enquiry is set up?",
        "Rule 160203(a): a Board of Enquiry shall be set up if the officer is not found within one year from "
        "the date declared missing.",
        "One year",
        "Six months",
    ),
    (
        "Under which Act is compensation for fatal cases or injury in a workplace (or outside it) treated, and within how long must payment be made?",
        "Rule 160206: treated under the Employees' Compensation Act 2010, with payment required within three "
        "months of the incident.",
        "The Employees' Compensation Act 2010, within three months",
        "The Pension Reform Act 2014, within one year",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 16 to the PSR course and its final exam. Safe to re-run."

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
