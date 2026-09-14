"""Follow-up to seed_psr_course.py / seed_psr_course_ch3.py — appends
Chapter 4 (Emoluments and Increments) to the existing "The Public
Service Rules — Complete Guide" course as a new Module, and adds 3
more questions to the course's existing final exam bank. Requires the
course to already exist; safe to re-run — does nothing if this module
has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULE_TITLE = "Chapter 4: Emoluments and Increments"

MODULE_BODY = """<h2>Getting paid — the basics</h2>
<p>On first appointment, emolument is paid from the date the officer actually assumes duty — not the date of the appointment letter. Every officer must be placed on the IPPIS platform within two months of assuming duty. An officer transferred from another scheduled service becomes eligible for their new office's emolument from the date they assume duty in the new post, not the date of the transfer decision.</p>
<h2>Promotion and pay — the mechanics</h2>
<p>When an officer is promoted within the Federal Public Service to a post on an incremental scale (excluding a move from a non-pensionable to a pensionable office, which follows different rules), where they land on the new salary scale depends on whether the grade levels overlap. If the new grade level doesn't overlap the old one at all, the officer is simply placed at the minimum point of the new grade level. If their old emolument was already higher than that minimum point, they're placed at the next point above their former emolument — after first accounting for the increment they would have earned had they not been promoted. Promotion arrears must be paid within the same year the promotion takes effect.</p>
<h2>What an increment actually is</h2>
<p>An increment is a predetermined amount added to an officer's annual emolument every calendar year. It's normally granted automatically to anyone on an incremental grade level — the exceptions are an officer under interdiction or suspension, one with a pending disciplinary action, or one held back for poor performance. An officer's incremental date is fixed as the 1st of January of the year following at least six months of service (for a new appointment) or six months since a promotion.</p>
<h2>Deferring an increment</h2>
<p>Deferring an increment means postponing the decision on whether to grant it, for a fixed period set at the time of deferment — never less than three months, never more than six. If the initial deferment period is shorter than six months, it can later be extended up to that six-month ceiling. If eventually granted, the increment only takes effect the day after the deferment period ends — but the officer keeps their original incremental date for every increment after that. If a deferred increment still hasn't been granted by the time six months have passed from when it was originally due, it must be withheld instead.</p>
<h2>Withholding an increment — a materially harsher step</h2>
<p>Withholding means the increment isn't granted at all, and the officer becomes ineligible for it until their next incremental date — permanently leaving them one increment behind what they'd otherwise have earned, for the rest of their incremental service, unless the Federal Civil Service Commission later exercises its special-increment authority. A withheld or deferred increment can never be restored retrospectively just because the officer's service later improves — the Permanent Secretary or Head of Extra-Ministerial Office weighs the gravity of the shortcoming and the officer's prior service record when choosing between the two penalties, bearing in mind that withholding is the more serious of the two. If a decision is later made to restore a withheld or deferred increment, the officer must be notified immediately. Separately, the Federal Civil Service Commission may grant one or more special increments at a later incremental date specifically to mitigate the lasting effect of an earlier withholding, raising the officer's salary back towards where it would otherwise have been.</p>
<h2>Paperwork that must happen either way</h2>
<p>Every decision to defer or withhold an increment, or to stop a salary, must be communicated within two weeks — to the Office of the Accountant General of the Federation, the Office of the Auditor-General for the Federation, the Office of the Head of the Civil Service of the Federation, and the officer concerned.</p>"""

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "From what date is an officer's emolument on first appointment generally paid?",
        "Rule 040102: emolument shall, as a general rule, be paid as from the date of assumption of duty.",
        "From the date the officer assumes duty",
        "From the date of the appointment letter",
    ),
    (
        "What is the shortest period for which an increment may initially be deferred, and the longest it can ever reach?",
        "Rule 040205: the deferment period must not be less than three months, and cannot exceed six months even "
        "after extension.",
        "Not less than three months, capped at six months",
        "Not less than one month, capped at three months",
    ),
    (
        "Can a deferred or withheld increment be restored retrospectively because an officer's service later improves?",
        "Rule 040207: an increment deferred or withheld cannot be restored with retrospective effect in "
        "consequence of improved service during a later increment-earning period.",
        "No — it cannot be restored retrospectively for that reason",
        "Yes, automatically, once service improves for six consecutive months",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 4 to the PSR course and its final exam. Safe to re-run."

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
