"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 6 (Reward and Recognition for Outstanding Work and
Meritorious Service) to the existing "The Public Service Rules —
Complete Guide" course as a new Module, and adds 3 more questions to
the course's existing final exam bank. Requires the course to already
exist; safe to re-run — does nothing if this module has already been
added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULE_TITLE = "Chapter 6: Reward and Recognition for Outstanding Work and Meritorious Service"

MODULE_BODY = """<h2>Reward vs. Recognition — a real distinction</h2>
<p>The PSR treats these as two different things. <strong>Reward</strong> is an MDA or Presidential award of gifts, certificates, or a letter of commendation to a deserving officer, tied to outstanding performance or exemplary conduct. <strong>Recognition</strong> is specifically a certificate of merit and/or gifts given to officers who have served meritoriously for 15, 25, or 35 years — a length-of-service milestone, not a performance judgment. The whole system is called the Reward and Recognition Scheme (R&amp;RS), a deliberate motivational tool meant to lift work ethic and performance across the Service by tying rewards directly to measurable performance, as part of an integrated approach to managing people well.</p>
<h2>Who actually qualifies</h2>
<p>The recipient of any award must genuinely be considered the best on the basis of outstanding performance and exemplary conduct, judged against the approved R&amp;RS criteria attached as an annexure to the PSR itself — this isn't a rotating honor or a consolation prize.</p>
<h2>Four tiers of awards</h2>
<p>Each MDA runs awards across four distinct tiers. <strong>Service-wide awards</strong> include the Presidential Distinguished Public Service Career Award, the Presidential Public Service Merit Award, the Head of the Service of the Federation Commendation Award, the Public Service Excellence Award, a Sports Achievement Award, and Recognition of Retired Permanent Secretaries. <strong>Sectorial MDA awards</strong> mirror these at sector level — a Sector Distinguished Service Award, Sector Merit Award, Honourable Minister Commendation Award, recognition for the best-serving sectoral CEO, and a sector-level Sports Achievement Award. <strong>MDA-level awards</strong> cover Recognition of Top Management, the Honourable Minister Unique Act Award, Bravery Awards, the Permanent Secretary Exemplary Conduct Award, a Long Service Merit Award, and Recognition of Retired Civil Servants. Finally, <strong>Departmental awards</strong> are the most local tier — an Ethic &amp; Professionalism Award and a Mentorship Award.</p>
<h2>How it actually runs</h2>
<p>Each MDA makes these awards within the timeframes the R&amp;RS itself prescribes. The specific criteria qualifying an officer for any given award category are communicated through circulars issued from time to time by the Office of the Head of the Civil Service of the Federation — the criteria aren't fixed in the PSR text itself, but flow from that central guidance. Rewards themselves take many forms: certificates, letters of commendation, engraved plaques or trophies, medals, cash gifts, sponsorship for Masterclasses and local training, admittance into an MDA's Hall of Fame, a tour of a funding agency's international administrative headquarters, or sponsorship for a relevant foreign short course.</p>
<h2>Keeping selection honest</h2>
<p>To keep the selection process transparent and fair, OHCSF provides a selection guidelines handbook laying out the criteria and weightings for each specific award, and dedicated Selection Committees are constituted for each award category in line with the R&amp;RS Guidelines. A Public Service Awards Ceremony is held annually to recognize the various Service-Wide Awardees, and information about the Scheme — including the names of awardees — is published in the monthly Service Welfare Newsletter.</p>"""

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "Under the PSR, what is the real difference between a 'Reward' and a 'Recognition'?",
        "Rule 060101: Reward is an MDA/Presidential award of gifts, certificates, or commendation for "
        "outstanding performance or conduct; Recognition is specifically a certificate of merit/gifts for "
        "15, 25, or 35 years of meritorious service.",
        "Reward is for outstanding performance/conduct; Recognition is for 15/25/35-year service milestones",
        "They are two interchangeable names for exactly the same thing",
    ),
    (
        "Where are the detailed R&RS award criteria formally set out?",
        "Rule 060104: the criteria are outlined in the approved Rewards and Recognition Scheme (R&RS), "
        "attached as an annexure to the PSR.",
        "In the approved R&RS, attached as an annexure to the PSR",
        "In each officer's individual employment contract",
    ),
    (
        "How often is the Public Service Awards Ceremony held to recognize Service-Wide Awardees?",
        "Rule 060110: the Public Service Awards Ceremony shall be held annually.",
        "Annually",
        "Once every five years",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 6 to the PSR course and its final exam. Safe to re-run."

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
