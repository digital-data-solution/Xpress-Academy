"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 13 (Medical and Dental Procedures) to the existing
"The Public Service Rules — Complete Guide" course as THREE new
modules (Parts 1-3, given the chapter's real size — 4 sections, ~40
rules), and adds 4 more questions to the course's existing final exam
bank. Requires the course to already exist; safe to re-run — does
nothing if Part 1 has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULES = [
    ("Chapter 13, Part 1: General Medical Requirements",
     """<h2>Who's who in this chapter</h2>
<p>A "Healthcare Provider" is one duly appointed under the National Health Insurance Scheme; a "Hospital" is a facility run by such a provider; a "Medical Officer" is a practitioner authorized to render healthcare services; and a "Private Practitioner" is any other registered medical or dental practitioner outside the NHIS system.</p>
<h2>Medical checks on entry, and periodically after</h2>
<p>Every new appointee must be examined by a recognized Healthcare Provider to confirm fitness for government service before their appointment proceeds — government pays the fee unless the offer says otherwise, and failing the fitness check means the appointment doesn't go ahead. This isn't a one-time thing: every five years in service, an officer must be re-examined to confirm they remain sound and fit to continue, without bias toward government policy on any specific disease. Medical records — certificates, Medical Board reports, dental records, private practitioner reports, confidential health reports — are treated as strictly confidential, with copies given out only as this chapter specifically allows, though a health record can still move with an officer transferred to another government service.</p>
<h2>When government can require a check</h2>
<p>A Permanent Secretary can call an officer in for examination — by an approved Healthcare Provider or a full Medical Board — at any time, to confirm they're physically and mentally capable of their current post or one they might be transferred to. An officer returning from Leave of Absence must similarly be examined before resuming duty, to confirm continued fitness. For either kind of examination, the MDA pays the fee, a specialist can be brought in at public expense if needed, the report goes to government and (if the officer wants) to the officer too, and the officer is told the resulting decision — with the right to contest it, at which point government decides at its own discretion whether more medical evidence is warranted.</p>
<h2>Leave to see a specialist</h2>
<p>An officer can get leave to visit a Medical Specialist or Dentist specifically where a Healthcare Provider certifies they can't handle the case themselves and delaying would genuinely harm the officer's health. This counts as travel on duty for free transport purposes (though not for travel allowance) — and without that certificate, the officer's only route is ordinary casual leave instead.</p>"""),
    ("Chapter 13, Part 2: Facilities for Medical Treatment",
     """<h2>Where treatment happens, and who pays</h2>
<p>In-Nigeria medical facilities and charges for officers and their families are set by the NHIS. An officer who chooses a private practitioner instead of the authorized Healthcare Provider bears the full cost themselves. Where an officer travels abroad on government business as an invalid under a ship or aircraft surgeon's care, government pays that surgeon's fee. Government will also consider refunding medical expenses for serious illness genuinely arising en route on an authorized overseas journey — provided it isn't down to the officer's or family's own negligence — though unrelated on-board claims aren't entertained; frequent-traveling officials like Ministers and Permanent Secretaries get annual International Medical Insurance instead.</p>
<h2>Getting treatment overseas — real, specific conditions</h2>
<p>A refund for overseas medical expenses during leave or duty requires all of: the illness wasn't the officer's own fault, it was genuinely tied to overseas conditions or climate, the officer tried the local NHIS-equivalent service first and couldn't get timely care, they notified the nearest Nigerian government representative promptly, and they showed real diligence and economy throughout. Approval for treatment abroad specifically comes from the Head of the Civil Service of the Federation, based on an approved Healthcare Provider's recommendation and Federal Ministry of Health certification — in genuinely life-threatening cases or where Nigeria lacks the needed diagnostic facilities, the officer is treated as an out-patient and gets the prevailing estacode allowance. Every overseas-treatment application needs a Consultant's report, routed through the Permanent Secretary of the Federal Ministry of Health up to the HCSF; the Nigerian Mission abroad picks the consultant/clinic (unless a prior relationship already exists) and vets every bill before it's settled. Where treatment happens in Nigeria but away from the officer's own duty post, DTA applies at the prevailing rate — extending to an accompanying spouse if a referral to a different town or state becomes necessary. For dependents needing overseas treatment in exceptional cases, government's involvement caps at half the estimated cost.</p>
<h2>A spouse accompanying a genuinely critical case</h2>
<p>A spouse may accompany an officer abroad at government expense only where the officer is in a genuine "life or death" condition requiring immediate treatment or hospitalization — and even then, government's commitment is limited to return air passage for both and estacode for the officer alone (the assumption being the spouse stays in a hotel, or shares the officer's if they're an out-patient). This is never automatic; it needs specific prior Accounting Officer approval before travel.</p>
<h2>Mandatory check-ups by grade level</h2>
<p>Officers on GL.16 and above get a mandatory local check-up once a year; GL.12–15 get one every two years; everyone else, every three years. If a check-up recommends further consultation abroad, approval comes from the President or HCSF depending on grade — and this entitlement can never be monetized (converted to cash instead of used). Approval authority for overseas check-ups specifically is graded further still: Presidential approval for Council of State members, Federal Executive Council members, service chiefs, Permanent Secretaries/DGs, and similarly senior officials; the President merely informed for the Senate President, Chief Justice, Supreme Court Justices, and similar constitutional office holders; and HCSF approval for GL.12-and-above staff generally. Every application needs Federal Ministry of Health countersignature on the local consultant's recommendation.</p>"""),
    ("Chapter 13, Part 3: Sick Leave Procedures and Burial Expenses",
     """<h2>Reporting in sick — the real mechanics</h2>
<p>An ill officer unable to report for duty must notify their Ministry, and any prolonged absence needs an Excuse Duty Certificate, Light Duty Certificate, or Medical Certificate of Treatment from an approved Healthcare Provider. An officer receiving treatment must report back to their employer within 48 hours. Where an officer is too ill to present themselves, their next of kin notifies the Healthcare Provider, who either brings them in or visits directly; if it results in hospital admission, the Ministry is informed. A private practitioner's report gets forwarded to a Healthcare Provider, who — after consulting that practitioner — issues the appropriate certificate: the first certificate covers up to three days (or seven, if the Healthcare Provider has actually examined the patient), each extension caps at seven days, and total sick leave under this route caps at three months before a Medical Board examination becomes mandatory.</p>
<h2>What triggers extra reporting, and the Medical Board's authority</h2>
<p>A Healthcare Provider must specifically report to the Ministry when an officer is admitted to or discharged from hospital, when an officer refuses or neglects prescribed medical advice, or when the Healthcare Provider suspects the officer is feigning illness. Where a Medical Board examination is ordered, the officer must attend and then follow the Board's recommendation — which overrides any prior Healthcare Provider advice — and failing to comply gets the officer treated as absent without leave. Ministries carry their own responsibilities too: keeping up-to-date next-of-kin contact records, investigating any unexplained absence within 24 hours, reporting a seriously ill officer's situation to the nearest Healthcare Provider, and initiating Medical Board proceedings when warranted.</p>
<h2>Sick leave limits, and permanent invalidation</h2>
<p>An officer properly absent on medical grounds (not on Leave of Absence) is treated as being on sick leave; an officer prevented from resuming duty after vacation leave by certified illness can have sick leave granted starting right where the annual leave ended. The real cap: maximum aggregate sick leave in any twelve-month period is three months — beyond that, a Medical Board examination is required to determine whether the officer should be invalidated from Service. An officer incapacitated by an injury sustained specifically in the course of official duty keeps drawing full emolument until discharged from sick leave or permanently invalidated. Where a Medical Board or Healthcare Provider recommends permanent invalidation, the officer immediately begins the two-month pre-retirement vacation leave under Rule 120244. For a hospitalized officer, up to three months of sick leave is allowed in the first instance on a Healthcare Provider's certificate; if still hospitalized after that, a Medical Board must examine them to decide between invalidation and further paid sick leave.</p>
<h2>Burial expenses — what government actually covers</h2>
<p>If a Nigerian officer (or their duly authorized accompanying spouse) dies abroad on official duty or a course of instruction, government repatriates the body at the family's request — covering embalming, a reasonably priced coffin meeting airline regulations, transport to the officer's home town, and up to one full-page obituary notice in a national newspaper. When a pensionable officer dies in service, government covers burial costs (preparation, embalming, mortuary bills, coffin) as a percentage of total annual emolument that scales by grade — from 110% at GL.03–06 down to 70% at GL.15–17 (100% for consolidated-salary officers) — plus reasonable-cost transport of the corpse to the officer's home town.</p>"""),
]

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "How often must an officer present themselves for examination to certify they remain sound in health and fit to continue in Service?",
        "Rule 130103: in every five years, an officer shall present himself for examination to certify fitness "
        "to continue in Service.",
        "Every five years",
        "Every year",
    ),
    (
        "Who bears the expenses when a staff member chooses treatment by a private practitioner instead of an authorized Healthcare Provider?",
        "Rule 130202: a staff who prefers private practitioner treatment must himself bear all expenses incurred.",
        "The staff member themselves, in full",
        "The Government, in full",
    ),
    (
        "What is the maximum aggregate sick leave allowable to an officer during any twelve-month period?",
        "Rule 130317(i): the maximum aggregate sick leave allowed during any period of twelve months shall be "
        "three months.",
        "Three months",
        "One month",
    ),
    (
        "At what percentage of total annual emolument does Government cover burial expenses for a pensionable officer on GL.03-06 who dies in service?",
        "Rule 130402(i)(a): GL.03-06 burial expenses are covered at 110% of total annual emolument.",
        "110%",
        "70%",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 13 (three modules) to the PSR course and its final exam. Safe to re-run."

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
            self.stdout.write(self.style.SUCCESS(f"Added {len(MODULES)} modules for Chapter 13."))

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
