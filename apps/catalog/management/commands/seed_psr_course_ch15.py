"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 15 (Innovations and Inventions) to the existing "The
Public Service Rules — Complete Guide" course as a new Module, and
adds 3 more questions to the course's existing final exam bank.
Requires the course to already exist; safe to re-run — does nothing
if this module has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULE_TITLE = "Chapter 15: Innovations and Inventions"

MODULE_BODY = """<h2>The Inventions and Awards Committee</h2>
<p>Each MDA has its own Inventions and Awards Committee, appointed by the Minister or Head of Extra-Ministerial Office — chaired by a Judicial or Legal Officer, plus other appointed members, with the appointment notice published on the MDA's website. The Committee's job is to investigate and recommend on award and commercial-proceeds questions. It can set its own procedural rules, but those only take effect once the Minister approves them; an officer has the right to appear personally before the Committee, or be represented in an approved way. Every conclusion the Committee reaches becomes a formal recommendation, forwarded up to the Minister or Head of Extra-Ministerial Office.</p>
<h2>Reporting an invention — the real first step</h2>
<p>An officer who makes an invention must immediately report it under Secret Cover to government, through their Permanent Secretary. They may then lodge a provisional protection application with the Registrar of Patents and Designs — at their own expense, or government's if required — sending a copy of that application to the Minister at the same time, again through the Permanent Secretary. The Minister decides, as quickly as possible, whether the invention should be treated as secret, and that decision is communicated back to the officer through their Permanent Secretary.</p>
<h2>Who actually controls the patent</h2>
<p>The Head of Government decides whether the officer gets controlling rights in the resulting patent. Where the invention is genuinely unrelated to the officer's actual employment, they're normally granted full rights outright. Until that decision is made, every right in the invention is treated as belonging to, and held in trust for, government. If controlling rights are granted to the officer, they become responsible for all the expense of actually taking out the patent — and government can attach conditions to that grant, including a royalty-free right to use the invention and/or a share of any commercial proceeds. Regardless of whether government reserves either of those rights, the officer can still apply to the Inventions and Awards Committee for an award.</p>
<h2>Awards and sharing commercial proceeds</h2>
<p>Whether an award is made at all, how much it is, and how commercial proceeds get split between government and the officer, are all decided by the Head of Government after the Committee investigates. The officer's own reasonable expenses on the invention are factored in; a royalty-free right of use reserved to government doesn't itself count against the officer — but the moment government actually exercises that right, it's treated as a "material change" in circumstances. If circumstances genuinely change after an award or proceeds-split has already been decided, the Head of Government can revise that original decision after further Committee investigation — but an award already paid can never be reduced by that revision. An officer who finds a Head-of-Government award unacceptable can take the matter to court, to determine whether it counts as fair remuneration under the Patents and Designs Act.</p>
<h2>Secrecy still applies</h2>
<p>Nothing in this chapter changes an officer's existing duties and liabilities under the Official Secrets Act — invention rules and secrecy obligations run in parallel, not as substitutes for each other.</p>"""

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "What must an officer who has made an invention do immediately?",
        "Rule 150104: an Officer who has made an invention must immediately report it under Secret Cover to "
        "Government through his Permanent Secretary/Head of Extra-Ministerial Office.",
        "Report it under Secret Cover to Government through his Permanent Secretary",
        "Publicly announce the invention to secure priority",
    ),
    (
        "Pending the Head of Government's decision on controlling rights in a patent, to whom do all rights in the invention belong?",
        "Rule 150201: pending the decision as to controlling rights, all rights in the invention shall be "
        "deemed to belong to and be held in trust for the Government.",
        "They are deemed to belong to and be held in trust for the Government",
        "They belong entirely and irrevocably to the inventing Officer",
    ),
    (
        "If circumstances materially change after an award has already been paid to an inventor, can the amount already paid be reduced?",
        "Rule 150302: in any modification of the original decision, the amount of an award which has been "
        "paid shall not be reduced.",
        "No -- the amount of an award which has been paid shall not be reduced",
        "Yes, the Head of Government may reduce it at any time without limit",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 15 to the PSR course and its final exam. Safe to re-run."

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
