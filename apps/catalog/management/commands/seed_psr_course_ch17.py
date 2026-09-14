"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 17 (Application of the Public Service Rules to
Federal Government Parastatals) to the existing "The Public Service
Rules — Complete Guide" course as TWO new modules (Parts 1-2), and
adds 4 more questions to the course's existing final exam bank. This
is the FINAL chapter — completes the course's coverage of all 17
chapters of the PSR. Requires the course to already exist; safe to
re-run — does nothing if Part 1 has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULES = [
    ("Chapter 17, Part 1: What a Parastatal Is, and Board/Council Authority",
     """<h2>What counts as a Parastatal</h2>
<p>A Parastatal is a government-owned organization established by statute to render specified services to the public — structured and operating according to its own establishing instrument, but still under government's overall policy direction. The Rules classify Parastatals into five real categories: Regulatory Agencies, General Services, Infrastructure/Utility Agencies, Paramilitary Agencies, and Research and Development Agencies. Each Parastatal's Conditions of Service, Scheme of Service, and Organizational Structure need OHCSF approval, on the recommendation of the relevant Board or Council.</p>
<h2>How Parastatal rules relate to the PSR</h2>
<p>Parastatals are expected to retain and improve their own existing rules, procedures, and practices — provided none of it deviates from the PSR's general principles. Variations in things like probationary periods or promotion maturity periods are treated as reflecting genuine organizational peculiarities, not inconsistency with the PSR. Where a Parastatal has no internal rule on a given matter at all, the relevant PSR provision simply applies directly.</p>
<h2>What a Board or Council actually does</h2>
<p>A Statutory Board or Council sets operational and administrative policy in line with government's own policy direction, and supervises how that policy gets implemented — including policies on staff appointment, promotion, and discipline. Critically, a Board is never meant to be directly involved in a Parastatal's day-to-day management; a Minister's control over a Parastatal runs only at the policy level, exercised through the Board. Part-time Board or Council members don't get permanent accommodation, and can't retain an official vehicle for permanent personal use — their privileges are deliberately bounded.</p>"""),
    ("Chapter 17, Part 2: Appointments, Discipline, and Leaving the Service",
     """<h2>Who handles appointments, promotion, and discipline</h2>
<p>Every Federal Government Parastatal has its own Junior Staff Committee and Senior Staff Committee to handle appointment, promotion, and discipline matters. All appointments and promotions — senior and junior alike — happen on the Board or Council's authority, exercised through these Staff Management Committees, within approved manning levels. Appointments themselves must be genuinely need-based, Board/Council-approved, and run through a fair, open, merit-based process that respects the Federal Character Principle — eligibility follows the same standard set in PSR Rule 020206(f).</p>
<h2>Promotion authority — split by seniority</h2>
<p>Senior staff promotions go to the Board or Council itself, on the Senior Staff Committee's recommendation; junior staff promotions are delegated down to the Parastatal's own Chief Executive Officer, on the Junior Staff Committee's recommendation. The same promotion-eligibility rules from PSR 020802(b), (c), and (d) apply across every Parastatal, without overriding each one's own specific Conditions of Service.</p>
<h2>Discipline — largely mirroring Chapter 10, with substituted authorities</h2>
<p>Disciplinary control in Parastatals sits with the appropriate Staff Committees, subject to Board/Council approval for officers on SGL.07 and above — where no Board or Council exists, the supervisory Ministry's own Minister exercises that power instead. For SGL.06 and below, the Chief Executive Officer approves the Committee's recommendations directly. Every JSC and SSC in a Parastatal must include a Human Resource Management representative from the supervising Ministry, plus an OHCSF observer. In practice, PSR Chapter 10's Sections 2 through 6 guide all Parastatal disciplinary matters — wherever those Rules reference the Federal Civil Service Commission or the Head of the Civil Service of the Federation, the Board/Council performs that role instead, and the Parastatal's CEO stands in for the Permanent Secretary. Paramilitary Services are a real exception — they keep using their own service-specific disciplinary procedures instead. OHCSF and Supervising Ministry observers sit on every relevant Staff Committee across all Parastatals, specifically to monitor compliance with the extant rules.</p>
<h2>Leaving the service, and petitions</h2>
<p>PSR Chapter 2 Section 9 — the rules on leaving the Federal Civil Service — applies to Parastatals exactly as it does elsewhere. Similarly, an officer in a Parastatal who wants to petition the Head of Government follows the same routing principle from PSR Chapter 11 Section 2, but through Parastatal-specific channels: their own superior officer, then the Chief Executive Officer, then the Board or Council, then finally the Supervising Ministry.</p>"""),
]

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "How is a 'Parastatal' defined under the Public Service Rules?",
        "Rule 170101: a Parastatal is a government-owned organization established by statute to render "
        "specified service(s) to the public.",
        "A government-owned organization established by statute to render specified services to the public",
        "A private company that has received a one-time government grant",
    ),
    (
        "Is a Board directly involved in the day-to-day management of a Parastatal?",
        "Rule 170201(a): a Board shall not be involved directly in the day-to-day management of a Parastatal.",
        "No -- a Board is not directly involved in day-to-day management",
        "Yes, the Board manages all day-to-day operations personally",
    ),
    (
        "Who approves promotion for Senior Staff in a Parastatal, and who approves it for Junior Staff?",
        "Rule 170303: the Board/Council approves Senior Staff promotion on the Senior Staff Committee's "
        "recommendation; Junior Staff promotion is delegated to the Chief Executive Officer on the Junior "
        "Staff Committee's recommendation.",
        "The Board/Council for Senior Staff; the Chief Executive Officer for Junior Staff",
        "The Chief Executive Officer approves all promotions, senior and junior alike",
    ),
    (
        "When PSR Chapter 10's disciplinary rules reference the Federal Civil Service Commission or the Head of the Civil Service of the Federation, who performs those roles in a Parastatal?",
        "Rule 170307: the Board/Councils perform those functions, while the Chief Executive Officer performs "
        "the functions of Permanent Secretary.",
        "The Board/Council performs those functions, and the CEO performs the Permanent Secretary's role",
        "Those references simply do not apply to Parastatals at all",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 17 (final chapter, two modules) to the PSR course and its final exam. Safe to re-run."

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        course = Course.objects.filter(organization=org, slug="public-service-rules-guide").first()
        if not course:
            raise CommandError("Course 'public-service-rules-guide' not found — run seed_psr_course first.")

        first_title = MODULES[0][0]
        if Module.objects.filter(course=course, title=first_title).exists():
            self.stdout.write(self.style.WARNING(f"'{first_title}' already exists on this course — leaving as-is."))
            return

        with transaction.atomic():
            next_order = (Module.objects.filter(course=course).order_by("-order").values_list("order", flat=True).first() or 0) + 1
            for i, (title, body) in enumerate(MODULES):
                module = Module.objects.create(
                    course=course, order=next_order + i, title=title, unlock_rule=Module.UnlockRule.SEQUENTIAL,
                )
                Lesson.objects.create(
                    module=module, order=1, title=title, type=Lesson.Type.TEXT,
                    body=body.strip(), is_preview=False,
                )
            self.stdout.write(self.style.SUCCESS(f"Added {len(MODULES)} modules for Chapter 17."))

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

        self.stdout.write(self.style.SUCCESS("Done. All 17 chapters of the PSR are now covered by this course."))
