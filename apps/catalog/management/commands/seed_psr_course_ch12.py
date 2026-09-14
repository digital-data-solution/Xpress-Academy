"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 12 (Leave) to the existing "The Public Service Rules —
Complete Guide" course as FOUR new modules (Parts 1-4, given the
chapter's real size — 2 sections, 48 rules, one of the largest
chapters), and adds 5 more questions to the course's existing final
exam bank. Requires the course to already exist; safe to re-run —
does nothing if Part 1 has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULES = [
    ("Chapter 12, Part 1: Leave Basics and Annual Leave",
     """<h2>The vocabulary of leave</h2>
<p>Leave is simply an officer's authorized absence from duty for a specific period. A few terms recur constantly through this chapter: a "leave address" is where the officer can be reached while away; "earned leave" is what's actually due for a year's service rendered; "leave-earning service" is the qualifying period of duty before leave can be granted at all; the "date of resumption of duty" is the day right after leave expires; and the "leave year" simply runs 1st January to 31st December. The PSR recognizes a genuinely long list of leave types — annual, proportionate, casual, sick, maternity, paternity, examination, sabbatical, study (with and without pay), compassionate, pre-retirement, leave of absence, urgent private affairs, cultural/sporting activities, and trade union activities. (Deferred leave once existed too, but has since been abolished.)</p>
<h2>Annual leave — the entitlement scale</h2>
<p>Annual leave is authorized by a superior officer, for a period set by grade level: 30 working days for GL.07 and above, 21 for GL.04–06, and 14 for GL.03 and below. An officer only qualifies for their next annual leave at least six months after their previous one, within a leave-earning service year. Each Ministry's HR/Administration department draws up the Annual Leave Roster, which the Permanent Secretary must approve by 31st December for the coming year.</p>
<h2>Taking it, and what happens if you don't</h2>
<p>Leave can be taken at any point in the leave year — normally all at once, though it can be split into at most two installments. Crucially, leave not taken within the calendar year is simply forfeited; officers are never allowed to accumulate leave for later. An officer planning to spend leave abroad must inform their Permanent Secretary in advance with their address details; if called back for duty during vacation leave, that period counts as leave-earning rather than leave-consuming. Every officer must resume duty the day their leave expires, and if recalled early, must take the curtailed portion within 90 days of finishing the assignment that interrupted it. On return, a Resumption of Duty Certificate (Form L.10) must be completed and forwarded up to OHCSF or the relevant pool office.</p>
<h2>Proportionate leave — for partial-year service</h2>
<p>Proportionate (pro-rata) leave applies to new or retiring officers, calculated against the actual days served — any period under 30 days doesn't count at all. It follows a fixed table (for example, six months of service earns 15 working days at GL.07+, 11 at GL.04–06, or 7 at GL.03 and below). This applies specifically to officers who join mid-leave-year, officers on training courses of six months or more, and officers retiring during their leave-earning service period.</p>"""),
    ("Chapter 12, Part 2: Casual, Sick, Maternity, Paternity, and Examination Leave",
     """<h2>Casual and sick leave — the short-term categories</h2>
<p>Casual leave covers short absences up to an aggregate of 7 calendar days in a leave year, and is only granted after an officer has already exhausted their annual leave — anything beyond that 7-day cap needs the Permanent Secretary's own approval. Sick leave is simply authorized absence for ill-health, on a Healthcare Provider's authorization.</p>
<h2>Maternity leave — a real, substantial entitlement</h2>
<p>A pregnant officer is entitled to 112 working days of maternity leave at a stretch, on full pay, starting no less than 28 working days before the Expected Date of Delivery — and a medical certificate confirming that date must be presented at least two months ahead. That year's annual leave counts as part of the maternity leave; if the annual leave was already taken before maternity leave was granted, the equivalent portion of maternity leave goes unpaid instead. An officer adopting a child under four months old gets 84 working days.</p>
<h2>Paternity leave, and time for nursing mothers</h2>
<p>A serving male officer gets 14 working days of paternity leave around the time of his spouse's delivery — capped at once every two years, and only for up to four children in total. Adopting a child under four months gives the same 14 days, with the request backed by either the Expected Date of Delivery report or adoption approval evidence. Separately, a nursing mother gets two hours off duty every day, for up to six months from the date she resumes duty after maternity leave.</p>
<h2>Examination leave — compulsory and non-compulsory</h2>
<p>Special leave for a compulsory examination — one required by the officer's actual conditions of service — is granted as a matter of course. For a non-compulsory examination, full-pay special leave is still possible, but only if the Permanent Secretary certifies that passing it would genuinely enhance the officer's value to the Service, backed by evidence of course admission and an examination timetable.</p>"""),
    ("Chapter 12, Part 3: Sabbatical Leave and Study Leave",
     """<h2>Sabbatical leave — a real career-development tool</h2>
<p>Sabbatical leave is available to officers on GL.15 or equivalent and above, for research or genuine professional development linked to career progression — takeable within or outside Nigeria, for 12 calendar months, once every five years. Only confirmed officers with a genuinely high-performance record, not under a Performance Improvement Plan or disciplinary action, may apply — via written application at least six months ahead, with evidence the receiving organization has actually accepted them. The MDA must certify the officer can be released without disrupting the department's work or a critical national assignment, and the request goes through the Permanent Secretary to OHCSF for final approval. The time itself doesn't count as a break in service, and the officer keeps their emolument throughout — but there's no notional promotion while away, though they remain eligible to sit promotion interviews/exams at the nearest designated center. Officers must return immediately at the end of the leave (absent an approved extension) and submit both a return notification and a formal report on what they accomplished — failing to return is treated as serious misconduct. After returning, the officer must serve at least one more year before exiting the Service.</p>
<h2>Study leave — three real varieties</h2>
<p>Study leave lets a confirmed officer pursue an approved course of study, in one of three forms: in-service training, study leave with pay, or study leave without pay. Any of the three needs Permanent Secretary certification — evidence of admission, the course's duration, that it genuinely enhances the officer's value to the Service, and that it's relevant to their profession. In-service training runs three to four years at normal emoluments, allowances, and fees, granted when the course is genuinely crucial to the MDA. Study leave with pay is capped at two years (extendable by one further year with acceptable justification) and applies when the course fits the MDA's mandate and the officer's own duties; anything that can't fit within three years total (including the extension) should instead go through study leave without pay or part-time study — without prejudice to PRESSSID scholarship recipients' own privileges.</p>
<h2>Study leave without pay — the longer, unfunded route</h2>
<p>This applies where a course isn't in the MDA's approved training proposals but is still relevant to the officer's career or self-development. Officers on it aren't entitled to normal emoluments or allowances; the duration is capped at four years in the first instance, extendable by one further year if genuinely needed — and, like the paid version, this time doesn't count as a break in service. Every form of study leave requires the Head of the Civil Service of the Federation's approval, on the Permanent Secretary's recommendation, before an officer is actually released.</p>"""),
    ("Chapter 12, Part 4: Compassionate Leave, Leave of Absence, and Retirement Transitions",
     """<h2>Compassionate leave, and religious pilgrimage</h2>
<p>An officer may get up to two weeks of full-pay compassionate leave for the burial of a spouse, child, parent, or parent-in-law. Officers going on religious pilgrimage (outside those specifically assigned to cover the event officially) are expected to use part of their own annual leave for it, rather than a separate category.</p>
<h2>Leave of absence — always unpaid, always approved at the top</h2>
<p>Leave of absence is authorized purely on grounds of public policy, always approved by the Head of the Civil Service of the Federation on the Permanent Secretary's recommendation, and always without pay. An officer on it can't accept paid employment without OHCSF's express approval. It covers a specific set of real scenarios: joining a spouse abroad on a course lasting nine months or more (with free passage at government expense for the officer too), joining a spouse on an overseas posting for public-policy reasons (capped at four years, extendable by one more), Technical Aid Corps postings, service as a Special/Personal Assistant to a political office holder, and joining a spouse who is President, Vice President, Governor, or Deputy Governor. It never covers taking up an actual political appointment — Secretary to Government, Minister, Commissioner, or similar — accepting one of those is treated as automatic resignation from the date of acceptance.</p>
<h2>Joining a spouse abroad — the real conditions</h2>
<p>Where a spouse takes up an overseas posting for public-policy reasons, the officer may get leave without pay for up to five years, provided their spouse doesn't take up separate gainful employment there; the time doesn't count as a service break, and genuine self-improvement (additional qualifications) during that period can still count toward advancement under normal rules. The standard period is four years, extendable by up to one further year.</p>
<h2>Winding down toward retirement</h2>
<p>Officers must give three months' notice before their retirement date — the first month of which is a mandatory pre-retirement workshop, with the remaining two months used to put records in order for faster benefits processing. Separately, where a Medical Board finds an officer medically unfit to continue, a two-month vacation leave begins immediately from that finding, with retirement taking effect once it expires.</p>
<h2>The rules that tie it all together</h2>
<p>An officer who fails to resume duty on schedule without acceptable excuse, or extends leave without their Permanent Secretary's consent, is treated as absent without leave and without pay. Dismissed officers forfeit any entitlement to leave entirely. Annual leave is always calculated in working days; every other kind of leave — casual, sick, maternity, and so on — excludes Saturdays, Sundays, and public holidays from the count.</p>"""),
]

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "How many working days of annual leave is an officer on GL.07 and above entitled to?",
        "Rule 120203(a): GL.07 and above are entitled to 30 working days of annual leave.",
        "30 working days",
        "21 working days",
    ),
    (
        "How many working days of maternity leave is a pregnant officer entitled to at a stretch, with full pay?",
        "Rule 120218(i): a pregnant female staff is entitled to 112 working days Maternity leave at a stretch "
        "with full pay.",
        "112 working days",
        "84 working days",
    ),
    (
        "Sabbatical leave is available to officers on which grade level and above, and how often may it be taken?",
        "Rule 120223: sabbatical leave applies to officers on GL.15 or equivalent and above, for twelve months "
        "once every five years.",
        "GL.15 or equivalent and above, once every five years",
        "GL.07 or equivalent and above, once every two years",
    ),
    (
        "How much notice must officers give before their effective retirement date, under the PSR?",
        "Rule 120243: officers are required to give three months' notice to retire from service before the "
        "effective date of retirement.",
        "Three months",
        "One month",
    ),
    (
        "Are officers who are dismissed entitled to any form of leave?",
        "Rule 120246: officers who are dismissed shall not be entitled to any form of leave.",
        "No -- dismissed officers are not entitled to any form of leave",
        "Yes, dismissed officers retain full leave entitlement",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 12 (four modules) to the PSR course and its final exam. Safe to re-run."

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
            self.stdout.write(self.style.SUCCESS(f"Added {len(MODULES)} modules for Chapter 12."))

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
