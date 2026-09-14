"""Follow-up to seed_psr_course.py / seed_psr_course_ch3.py /
seed_psr_course_ch4.py — appends Chapter 5 (Performance Management
System) to the existing "The Public Service Rules — Complete Guide"
course as TWO new modules (Part 1 and Part 2, given the chapter's real
size — 7 sections across 9 pages, comparable to Chapter 2), and adds 4
more questions to the course's existing final exam bank. Requires the
course to already exist; safe to re-run — does nothing if Part 1 has
already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULES = [
    ("Chapter 5, Part 1: Probation Reports and the Performance Management System",
     """<h2>Progress reports during probation</h2>
<p>For officers on probation or initial contract, Progress Reports exist to build a full record of work, conduct, and capability — the evidence base for deciding on confirmation or re-engagement. Just as importantly, they exist to give an officer whose suitability is in doubt a timely warning and a fair chance to correct course, rather than a surprise termination. Permanent Secretaries/Heads of Extra-Ministerial Offices must render these reports every six months from the date of first appointment, with the final report due no later than two months before the probationary period (or second tour of contract) expires.</p>
<h2>When leave complicates the timeline</h2>
<p>If a probationary period is due to expire while the officer is on leave, the final Progress Report must instead be rendered at least two months before the officer actually proceeds on that leave — so a decision on confirmation, deferment, or termination can be made and communicated before they leave. For contract officers, if an adverse opinion has already formed by that point, it must be communicated before departure too, so the officer can weigh, with full information, whether returning is in their own interest.</p>
<h2>The 21-month report</h2>
<p>Progress reports go, under personal and confidential cover, to the Permanent Secretary of the FCSC or the Permanent Secretary of the Career Management Office. Specifically, the final Progress Report rendered after 21 months of service must include a definite recommendation — confirm, terminate, or renew the contract. This isn't optional commentary; it's a required decision point.</p>
<h2>PMS replaces the old APER system</h2>
<p>The Performance Management System (PMS) is the current tool for setting goals, and tracking, assessing, and reporting on individual performance across the Federal Public Service — it formally replaced the old Annual Performance Evaluation Report (APER), and every MDA is expected to comply. PMS focuses on two things together: measurable output (objectives and targets) and the underlying competencies — knowledge, skills, and personal attributes — needed to actually deliver on them. Both performance management and training are meant to be result-oriented.</p>
<h2>Who can report on whom</h2>
<p>Annual reports are expected to be detailed and candid — the Rules note directly that a Reporting Officer's own capability shows through in the quality of the reports they write on subordinates. A Reporting Officer must be at least one substantive grade above the officer being reported on, and must be their direct immediate superior. If an officer served under multiple superiors before the report is due, the Reporting Officer is whoever supervised them for the substantial part of the reporting period. Every report must also be judiciously assessed by a countersigning officer before it's finalized.</p>
<h2>Handling adverse comments fairly</h2>
<p>Any adverse comment on an officer's work or conduct must be conveyed to them in writing, in sympathetic terms, aimed at helping them overcome the shortcoming — not just recorded against them. The report itself must state that this was done, and a copy of both the letter and the officer's acknowledgment must be attached. When an officer is seconded elsewhere, the host Ministry or Extra-Ministerial Office becomes responsible for their reports; the same principle extends to secondments at Corporations, States, or State-owned companies, which are asked to furnish reports as though they were government departments, requested at least two months ahead of the due date by the seconding office.</p>"""),
    ("Chapter 5, Part 2: The Performance Management Cycle, Underperformance, and Oversight",
     """<h2>The annual cycle</h2>
<p>The Performance Management Cycle runs January to December each year, beginning once each MDA's leadership has finalized its institutional and departmental goals. Annual goals for each post are set by HRM in collaboration with the relevant department or unit. Key Performance Indicators are agreed by January and finally appraised by December of the same year — and an employee's actual performance results become the primary basis for their development options, rewards, sanctions, and other related decisions.</p>
<h2>Who's accountable for making it happen</h2>
<p>The Accounting Officer of every Federal Public Service institution is responsible for the PMS working properly at every level — executing the annual cycle and ensuring proper complaints-handling processes exist. The Director of HRM prepares the Annual Performance Management Report for the Accounting Officer at the end of each cycle, and coordinates the follow-through on reward, recognition, incentives, and development recommendations based on rated performance.</p>
<h2>Four real stages: planning, monitoring, appraisal, rewards</h2>
<p><strong>Planning</strong> happens at the start of the cycle: Job Descriptions define scope and responsibilities, performance expectations flow from the Accounting Officer down through each head of department until every employee has agreed Annual Performance Goals, documented and signed in a Performance Planning Form. <strong>Monitoring</strong> is continuous throughout the year — regular appraiser/appraisee discussions, captured in a Monthly Performance Dialogue Form and a Quarterly Performance Review Form, led by the immediate supervisor with a second opinion required from the next supervisor up. <strong>Appraisal</strong> combines ongoing self-appraisal with a formal end-of-year review meeting, covering the past year's performance, training needs, career aspirations, and further support — documented in an End of Year Performance Appraisal Form, with training provided to staff in both the appraiser and appraisee roles. <strong>Rewards</strong> are explicitly linked to these results (feeding into Chapter 6's reward and recognition system) but performance incentives or bonuses are only paid once the Accounting Officer and the Head of the Civil Service of the Federation have both fully signed off on the year's appraisal results. Promotion decisions also draw on demonstrated performance from these results, on top of the FCSC's usual promotion requirements.</p>
<h2>Underperformance — a supportive process before a punitive one</h2>
<p>Underperformance means an appraisal outcome below average or not meeting the expectations of the role, and it's handled case by case. Appraisers are expected to act promptly once performance becomes a concern — understanding root causes through the regular monitoring conversations, and offering help. Where the issue is serious, a formal Performance Improvement Plan (PIP) is used: the employee is notified in writing through a confidential process, gap-closure actions are jointly agreed between appraiser and appraisee and documented in the PIP, and the Director HRM coordinates implementation with the appraisers. At the end of a PIP period, the employee gets formal feedback on whether they've improved enough to be retained in their current role — with the actual decision made by the Performance Appraisal Committee and then shared with the individual.</p>
<h2>Appraisals for staff who were away</h2>
<p>An employee who was on approved absence for part of the performance period has a review session with their supervisor on return, to set or revise their targets for the remainder of the year — the rest of the normal process then continues as usual.</p>
<h2>Committee oversight and central coordination</h2>
<p>Beyond their existing role in appointment, promotion, and discipline, each MDA's Senior Staff Committee and Junior Staff Committee also review and manage annual appraisal outcomes for their staff, escalating disputed cases to the OHCSF/FCSC Appraisal Committee. These committees are expected to keep appraisals fair and objective, meeting the specific criteria and weighting set out in the Performance Management Policy guidelines, conducted in strict confidence and in line with the Employee Personal Data Privacy Protection Rules. Overall compliance across the Federal Public Service is monitored by a Central Coordinating Body domiciled in the OHCSF. Every record generated during the performance management cycle remains, at all times, the property of the Federal Government of Nigeria, and must be administered under proper document and data management practice.</p>"""),
]

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "What system did the Performance Management System (PMS) replace for the Federal Public Service?",
        "Rule 050201: the PMS shall replace the Annual Performance Evaluation Report (APER) for the Federal "
        "Public Service.",
        "The Annual Performance Evaluation Report (APER)",
        "The Certificate of Service",
    ),
    (
        "By when must Key Performance Indicators (KPIs) be drawn and agreed upon each year, under the Performance Management Cycle?",
        "Rule 050301(ii): KPIs shall be drawn and agreed upon by January of each year, with final appraisal by "
        "December of the same year.",
        "By January",
        "By June",
    ),
    (
        "When may performance incentives or bonuses actually be paid, per Rule 050405?",
        "Rule 050405(iii): incentives or bonuses shall be paid after the annual performance appraisal results "
        "have been fully signed off by the Accounting Officers and the Head of the Civil Service of the "
        "Federation.",
        "After the annual appraisal results are fully signed off by the Accounting Officer and the Head of the Civil Service of the Federation",
        "Immediately at the start of each Performance Management Cycle",
    ),
    (
        "What formal process is adopted for serious cases of underperformance under the PSR?",
        "Rule 050406(iv): in cases where performance issues are of a very serious nature, the Performance "
        "Improvement Plan (PIP) process shall be adopted.",
        "The Performance Improvement Plan (PIP)",
        "Immediate interdiction pending investigation",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 5 (two modules) to the PSR course and its final exam. Safe to re-run."

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
            self.stdout.write(self.style.SUCCESS(f"Added {len(MODULES)} modules for Chapter 5."))

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
