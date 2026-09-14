"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 8 (Free Transport Facilities on Official Assignments)
to the existing "The Public Service Rules — Complete Guide" course as
TWO new modules (Part 1 and Part 2, given the chapter's real size — 4
sections across 7 pages, comparable to Chapter 2/5's multi-part
treatment), and adds 4 more questions to the course's existing final
exam bank. Requires the course to already exist; safe to re-run —
does nothing if Part 1 has already been added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULES = [
    ("Chapter 8, Part 1: Definitions, Authority, and Duty Journeys",
     """<h2>Two definitions worth knowing precisely</h2>
<p>A <strong>"cheaper point"</strong> is a place that can substitute for an officer's Nigerian home place as the start or end of a government-funded journey — but only if the substitution costs government no more, in cash or in transport use, than the standard journey would have. A <strong>"load"</strong> is the unit baggage allowances are measured in: 25 kilograms where freight is charged by weight, or 3/25 of a cubic meter where it's charged by volume.</p>
<h2>Economy first, always</h2>
<p>Before any journey at government expense is authorized, its necessity must be fully established — this isn't a rubber stamp. The transport and route chosen must be determined by cost, the exigency of the duty, and the officer's grade level; all officers are entitled to airfare depending on the assignment's exigencies, but it still requires the Accounting Officer's approval.</p>
<h2>Who authorizes it, and the real limits</h2>
<p>Authority for government-funded transport must be given in writing by the Permanent Secretary/Head of Extra-Ministerial Office or their authorized representative, following the Financial Regulations. Free transport can never exceed what these Rules actually provide for — an officer who wants more must pay the excess themselves, in advance. The Permanent Secretary must specifically verify that authorized transport doesn't exceed both the Rules' maximum and what the journey actually requires; when children are included, each child's age must be ascertained and specified, not assumed.</p>
<h2>Misusing free transport is serious misconduct</h2>
<p>Using free transport for a purpose other than the one it was authorized for, failing to refund an unused cash advance on demand, or claiming payment in arrears for transport never actually used — all three are explicitly treated as serious misconduct, not minor administrative slips. Separately, no staff member may travel at government expense as an orderly or personal attendant to another officer unless the Office of the Head of the Civil Service of the Federation has specifically authorized that role.</p>
<h2>What counts as a "duty journey"</h2>
<p>Free transport facilities cover all journeys within Nigeria, with family passenger fare covering one spouse and up to four children — baggage allowance is included in, not additional to, the standard passenger ticket allowance, and only applies to a spouse, child, or servant who actually travels. A journey counts as "on duty" if it's specifically instructed by the officer's Permanent Secretary or local representative, for dental treatment, to consult a Medical Officer (where the officer's station or leave location lacks medical facilities and a local superior certifies the need), for certified hospital treatment, for a spouse's or child's equivalent medical journeys, or as a health trip recommended by a Medical Board for a change of scene or climate.</p>
<h2>Journeys to a new station</h2>
<p>This category includes the journey made when first assuming duty on appointment (from the place of engagement or Nigerian home place), and the journey made on retirement or to repatriate a deceased officer's family and effects — back to the place of original engagement, a cheaper point, the Nigerian home place, or the final-leave destination, whichever applies. This retirement/repatriation concession must be used within six months of the retirement date or the officer's death — it doesn't stay open indefinitely.</p>"""),
    ("Chapter 8, Part 2: Travel Classes, Vehicles, and Duty Abroad",
     """<h2>Who flies what class</h2>
<p>For duty journeys by air, Permanent Secretaries, Ministers, and above travel Business Class; officers on GL.07–17 travel Economy; a spouse and up to four children traveling with the officer also travel Economy. For journeys by road or river transport, junior officers on GL.06 and below receive either tickets or cash in lieu, at rates set from time to time in Federal Treasury Circulars.</p>
<h2>Moving a vehicle for repair or purchase</h2>
<p>Where an officer's station lacks adequate motor repair facilities and a vehicle is genuinely necessary for their duties, their Permanent Secretary may authorize free transport of the vehicle to and from the nearest place with proper facilities — but this normally excludes ordinary maintenance or servicing, except at the Permanent Secretary's discretion for essential large-scale servicing (for example, a new vehicle's first 1,000-kilometer service). Separately, free transport of a vehicle by train or boat can be granted when an officer is purchasing a new vehicle, or when assuming duty, transferring, or traveling on tour/duty — provided the Permanent Secretary is satisfied the vehicle is genuinely necessary for the duty, and that transporting it is actually the most economical way to keep the officer mobile (cheaper than hiring a vehicle at each stop on their itinerary).</p>
<h2>Duty visits outside Nigeria</h2>
<p>An officer on a duty visit outside Nigeria gets air passage for themselves alone — unless the visit runs nine months or more, in which case their spouse may travel at government expense too. Actual transport expenditure essential to the visit is reimbursed, and where a host government or institution covers the officer's accommodation or hotel costs, the officer becomes entitled to an Estacode Supplementation allowance at the approved rate instead.</p>
<h2>Working during leave, and expense refunds</h2>
<p>An officer who, with prior government approval, performs official duties abroad during their vacation leave and must take accommodation away from their normal residence is treated as being on a duty visit — eligible for the same duty allowance abroad, as long as government isn't already providing accommodation at that destination. Where accommodation is provided, the officer instead gets a refund of the daily travel expenses actually incurred while carrying out those duties, plus a daily subsistence allowance at the appropriate rate.</p>
<h2>The smaller, practical rules</h2>
<p>An officer may bring necessary equipment for their duties — office equipment, survey instruments, tents — at their Permanent Secretary's discretion. Traveling by air on duty, an officer may bring official documents, papers, and office necessities up to 10 kilograms, on top of their ticket's standard baggage allowance, where genuinely necessary for the job. Finally, an officer moving on transfer may get free government transport between their house and the airport, seaport, or motor park at both ends of the move — and where that transport genuinely can't be provided, they're reimbursed instead, at approved rates.</p>"""),
]

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "Which of the following is explicitly treated as serious misconduct under the PSR's transport rules?",
        "Rule 080106: claiming payment in arrears for free transport not actually utilized for the purpose "
        "claimed is explicitly named as serious misconduct, alongside misusing transport for another purpose "
        "or failing to refund an unused cash advance.",
        "Claiming payment in arrears for free transport not actually utilized for the purpose claimed",
        "Declining to use an authorized free transport facility altogether",
    ),
    (
        "Which class of air travel does the PSR provide for officers on Grade Level 07-17 on duty journeys?",
        "Rule 080204(a)(ii): Economy Class is provided for officers on GL.07-17 (Business Class is reserved "
        "for Permanent Secretaries, Ministers, and above).",
        "Economy Class",
        "Business Class",
    ),
    (
        "Within how long of an officer's retirement or death must the retirement/repatriation transport concession be used?",
        "Rule 080203(b): the concession must be utilized within six months of the date of retirement or of "
        "the officer's death.",
        "Six months",
        "Two years",
    ),
    (
        "What is an officer entitled to when a host Government or institution abroad covers their accommodation/hotel expenses?",
        "Rule 080301(c): the officer is entitled to Estacode Supplementation allowance at the approved rates.",
        "Estacode Supplementation allowance, at the approved rates",
        "No allowance at all -- accommodation coverage cancels all further entitlements",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 8 (two modules) to the PSR course and its final exam. Safe to re-run."

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
            self.stdout.write(self.style.SUCCESS(f"Added {len(MODULES)} modules for Chapter 8."))

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
