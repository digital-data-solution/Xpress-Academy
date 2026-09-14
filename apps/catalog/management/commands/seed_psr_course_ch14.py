"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 14 (Allowances) to the existing "The Public Service
Rules — Complete Guide" course as THREE new modules (Parts 1-3, given
the chapter's real size — ~44 rules, one continuous chapter with no
formal Section headers), and adds 4 more questions to the course's
existing final exam bank. Requires the course to already exist; safe
to re-run — does nothing if Part 1 has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULES = [
    ("Chapter 14, Part 1: Travel, Duty, and Estacode Allowances",
     """<h2>What an allowance actually is</h2>
<p>An allowance is a monetary benefit distinct from salary, granted for a specific purpose — and every allowance in this chapter is subject to periodic review by the National Salaries, Incomes and Wages Commission, at OHCSF's instance, through Circulars. There's a genuinely long list of them: Acting, Books, Call Duty, Disengagement, Duty Tour, Estacode, Estacode Supplementation, Hotel Accommodation (first 28 days), Hardship, Hazard, Kilometer, Local Course, Overtime, Project, Resettlement, Responsibility, Spectacle, Transport and Local Running, Teaching, Uniform, Warm Clothing, and Wardrobe. For allowance purposes, officers are graded into bands: GL.03–06, GL.07–10, GL.12–14, GL.15–16, GL.17, Permanent Secretary/part-time Commissioners/Board Chairmen/Chief Executives, and HOS/SGF/Ministers.</p>
<h2>Moving, retiring, and settling in</h2>
<p>Kilometer Allowance covers newly appointed officers reporting for duty, retiring officers, officers using their own car for responsibilities, and officers on transfer or posting, at extant Circular rates. Disengagement Allowance goes to an officer retiring from Service, plus spouse and up to four children, at a uniform 25% of gross annual emolument, plus the Kilometer Allowance. An officer posted, transferred, or newly appointed to a station away from their home city gets transport fare for themselves, spouse, and up to four children, plus either 28 days of hotel accommodation or an equivalent allowance in lieu.</p>
<h2>On tour and traveling locally</h2>
<p>Duty Tour Allowance covers lodging and feeding during approved official tours, at extant Circular rates. All officers on official assignment are entitled to airfare (exigency-dependent, Accounting Officer-approved); where air transport doesn't exist, Kilometer Allowance applies instead. For local running, officers get 30% of their Duty Tour Allowance on top of prevailing airport taxi rates.</p>
<h2>Estacode — the overseas allowance</h2>
<p>Estacode applies when officers undertake special duty abroad, perform official duties during overseas vacation leave, join a short overseas delegation/visit, or undertake overseas instruction/attachment. Overseas Duty Tour and estacode need HCSF approval (on the Permanent Secretary's recommendation) for most public servants, or SGF approval for other categories — at rates set by extant Circulars. Officers wanting to combine overseas leave with an official visit need prior HCSF approval, with a detailed application covering the visit's purpose, dates, address abroad, duration, and total estimated cost. On a duty visit abroad, an officer gets air passage for themselves alone (spouse included only for visits of 9+ months), reimbursement of essential transport costs, estacode, and — where genuinely needed — a special entertainment allocation.</p>
<h2>When a host country already covers some costs</h2>
<p>Estacode Supplementation Allowance kicks in when a donor/host covers accommodation during training or duty: if they provide full board and lodging, the officer gets 10% of appropriate estacode for the whole course (no full estacode for the first 28 days); if lodging alone, 40% to cover boarding and incidentals; if lodging plus cash, the officer claims the difference between that cash and 30% of estacode; and if only cash toward boarding/lodging is given, the officer gets the difference between that cash and the normal Nigerian estacode rate. Approved travel days for overseas journeys are set by Circular from time to time.</p>
<h2>Warm clothing, local courses, and training-related allowances</h2>
<p>An officer sent to a foreign country on duty or study gets a Warm Clothing Allowance — except where the trip coincides with vacation leave in a cold/temperate country, results from the officer's own application combined with vacation leave, or comes less than three years after the officer last drew this allowance. A local course (taken in Nigeria, outside the officer's own station) earns Training Allowance: 30% of Duty Tour Allowance for the first 28 days (plus further Circular-set rates after) if the course exceeds 28 days without provided board/lodging, or 50% of Duty Tour Allowance if it's 28 days or shorter. Training away from station at Federal Training Institutes or Management Development Institutes earns transportation plus 100% of normal Duty Tour Allowance. Books Allowance applies to officers on approved courses at Circular rates, and Project Allowance covers course-duration project work — for postgraduate courses specifically, it's a one-time payment for students actually writing a project.</p>"""),
    ("Chapter 14, Part 2: Responsibility, Overtime, and Acting Allowances",
     """<h2>Responsibility Allowance — for confidential secretarial roles</h2>
<p>Paid annually per extant Circular, in three tiers: Chief Confidential Secretaries attached to the President, Vice President, Senate President, Speaker, Chief Justice, SGF, HCSF, and Ministers; Assistant Chief Confidential Secretaries attached to Permanent Secretaries/Chief Executives and Directors; and ordinary Confidential Secretaries attached to those same functionaries.</p>
<h2>Overtime — the real mechanics</h2>
<p>Overtime is time worked beyond approved working hours, and it's payable specifically to officers on GL.14 and below. The normal approved working week runs 8am–4pm, Monday to Friday, excluding weekends and public holidays — overtime pay covers time genuinely worked beyond that. It requires Accounting Officer/Chief Executive authorization on a Director's recommendation, and applies in specific circumstances: officers attached to Top Management, special assignments like conferences or committees, budget preparation periods, annual accounts closing, or any other Director-approved assignment. Normal-day overtime pays at 0.7% of monthly consolidated salary, capped at 45 hours a month, and still needs Accounting Officer/Chief Executive approval. A "work-free day" is the working day a public holiday falls on; weekend work pays at 1.5× the normal overtime rate, and public-holiday work pays double the normal rate (again, approval required). An officer duly acting in a post that attracts overtime is paid overtime on their full acting emolument, not their substantive one.</p>
<h2>Uniform and Acting Allowances</h2>
<p>Uniform Allowance goes to any officer who wears a uniform in the Service, at Circular rates. Acting Allowance applies to an officer duly authorized to act, running from the gazetted start date to the day before the gazetted end date (inclusive of both), except for any continuous ill-health absence beyond 14 days — and no allowance at all if the acting period doesn't exceed one month. Where an officer acts in a post immediately above their own grade, they're treated as fully performing the higher post's duties and get 100% of the acting-allowance rate. If an officer already draws a personal allowance alongside their normal emoluments, that personal allowance counts as part of their substantive base emolument when calculating acting allowance. For a contract officer or re-engaged pensioner, the substantive emolument used for allowance calculation is their actual emolument minus any contract addition.</p>"""),
    ("Chapter 14, Part 3: Resettlement, Teaching, and Other Allowances",
     """<h2>Resettlement — for a genuinely disrupted living situation</h2>
<p>Resettlement Allowance applies where a posting or transfer confirms an officer's living conditions have genuinely been disturbed, compensating for out-of-pocket transfer expenses not covered elsewhere. "Transfer" here covers both moving station-to-station within a tour of service, and transfer/secondment to another government's service entirely. It's paid at a flat 2% of the officer's annual total emolument — but an officer who requested their own transfer only gets transport allowance, not resettlement allowance at all.</p>
<h2>Teaching-related allowances</h2>
<p>Part-time teaching earns its own allowance at Circular rates. Officers from non-teaching cadres (Professional, Administrative, Executive, Technological, Allied) posted to full-time teaching duties get a separate full-time teaching allowance for the duration of that posting. Specific roles carry their own named allowances: House Master/Mistress, Science/Mathematics Teachers, and Laboratory Attendants who also work evening-class sections — each at its own Circular-set rate.</p>
<h2>Shift work and driver incentives</h2>
<p>Non-health-professional officers who work shift duty get a Shift Duty Allowance of 15% of monthly salary. Drivers who go accident-free for at least six months of continuous vehicle-assigned driving in a year (or whose one accident genuinely isn't their fault) earn a Non-Accident Bonus of ₦50,000 per annum — a real, specific incentive for a specific job category, not a general benefit.</p>"""),
]

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "At what uniform rate of gross annual emolument is Disengagement Allowance paid to a retiring officer?",
        "Rule 140105: Disengagement allowance is paid at a uniform rate of 25% of gross annual emolument, plus "
        "Kilometer Allowance.",
        "25%",
        "10%",
    ),
    (
        "Overtime Allowance is payable to officers on which grade levels, and at what rate for normal working days?",
        "Rule 140121/140125: GL.14 and below, at 0.7% of monthly consolidated salary, capped at 45 hours a "
        "month.",
        "GL.14 and below, at 0.7% of monthly consolidated salary",
        "All grade levels, at 1.5% of monthly consolidated salary",
    ),
    (
        "Is Acting Allowance paid if the period of acting appointment does not extend beyond one month?",
        "Rule 140130: no allowances shall be paid if the period of acting appointment does not extend beyond "
        "one month.",
        "No -- no allowance is paid for acting periods of one month or less",
        "Yes, at half the normal rate",
    ),
    (
        "At what rate of an officer's annual total emolument is Resettlement Allowance paid, and when is it NOT payable?",
        "Rule 140136/140137: paid at 2% of annual total emolument, but not payable (only transport allowance "
        "instead) where the transfer is at the officer's own request.",
        "2%, and not payable where the transfer is at the officer's own request",
        "10%, and payable regardless of who requested the transfer",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 14 (three modules) to the PSR course and its final exam. Safe to re-run."

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
            self.stdout.write(self.style.SUCCESS(f"Added {len(MODULES)} modules for Chapter 14."))

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
