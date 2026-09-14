"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 9 (Virtual Meetings and Engagements) to the existing
"The Public Service Rules — Complete Guide" course as a new Module,
and adds 3 more questions to the course's existing final exam bank.
Requires the course to already exist; safe to re-run — does nothing
if this module has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULE_TITLE = "Chapter 9: Virtual Meetings and Engagements"

MODULE_BODY = """<h2>What counts as a "virtual meeting"</h2>
<p>A virtual meeting or engagement happens when officers — with or without other participants, regardless of where anyone physically is — communicate effectively during a pre-scheduled teleconference, web conference, or video conference, using video, text, or audio features, all occupying the same virtual space for a defined period. The whole point of formalizing this is continuity: it lets employees respond to work demands remotely, so MDAs keep functioning with minimal disruption during a pandemic or other emergency.</p>
<h2>Where this chapter actually applies</h2>
<p>The Rules deliberately spell out ten specific scenarios this chapter covers: high-level intra- and inter-governmental meetings, meetings of statutory commission boards, meetings of Federal Government parastatal/agency boards, the Head of the Civil Service of the Federation's meetings with Permanent Secretaries service-wide, scheduled meetings between the HCSF and Heads of Federal Agencies, ad-hoc government committee meetings, ordinary meetings within Ministries and Extra-Ministerial Offices, bilateral negotiations with other countries, local and international conferences and webinars, and any other MDA engagement with the public.</p>
<h2>Data security comes first for high-level meetings</h2>
<p>Because of how sensitive the information discussed can be, all high-level intra- and inter-governmental meetings must follow guidelines prescribed from time to time by the Federal Ministry of Communications and Digital Economy — and officers are expected to take the specific security measures those guidelines set out to protect government data.</p>
<h2>The actual meeting protocol</h2>
<p>Every virtual meeting needs a predefined agenda, approved by the chairperson and shared with all participants ahead of time via official email. The meeting's Secretary must confirm participant availability in advance, both to track attendance and to clearly establish everyone's identity. Reference materials must be chairperson-approved and circulated to participants at least 24 hours before the meeting — not on the day itself.</p>
<h2>Ground rules while the meeting is running</h2>
<p>No sidebar conversations. No multitasking — running email or handling files while "attending" isn't acceptable. Participants must identify themselves whenever they speak. Non-active speakers mute their phones by group agreement, to cut down feedback noise from other remote locations. Meetings expected to run over an hour must include a 10–15 minute break. And the whole thing is governed by the Ministry of Communications and Digital Economy's broader virtual-engagement policy.</p>
<h2>Joining from home — real expectations, not just etiquette</h2>
<p>Participating from a non-work environment comes with two specific rules: dress formally regardless of the setting, and participate from the most convenient and serene environment available — not wherever happens to be nearby.</p>
<h2>Ad-hoc meetings and personal devices</h2>
<p>For ad-hoc meetings, the Secretary first reaches every attendee by phone to inform them directly, and only afterward circulates the meeting link, agenda, and relevant documents. Where officers connect using their own personal devices, those devices must be used strictly in line with the Federal Ministry of Communications and Digital Economy's guidelines on personal-device use for official engagements.</p>"""

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "What is the main rationale for implementing virtual meetings/engagements in the Public Service?",
        "Rule 090102: implementation is to ensure employees can respond to work demands remotely, so MDAs "
        "continue functioning adequately with minimal disruption during a pandemic/emergency.",
        "To ensure employees can respond to work demands remotely, keeping MDAs functioning during a pandemic/emergency",
        "To replace in-person meetings permanently in all circumstances",
    ),
    (
        "How far in advance of a virtual meeting must approved materials and reference documents be circulated to participants?",
        "Rule 090203: materials shall be approved by the Chairperson and circulated to participants at least "
        "24 hours before the meeting.",
        "At least 24 hours before the meeting",
        "At least one week before the meeting",
    ),
    (
        "For meetings expected to last beyond one hour, what break is required under the PSR's virtual-meeting ground rules?",
        "Rule 090204(v): where meetings are expected to last beyond one hour, a 10-15 minute break shall be "
        "observed.",
        "A 10-15 minute break",
        "No break is required, regardless of duration",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 9 to the PSR course and its final exam. Safe to re-run."

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
