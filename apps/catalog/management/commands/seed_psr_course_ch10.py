"""Follow-up to seed_psr_course.py and its earlier chapter follow-ups —
appends Chapter 10 (Discipline) to the existing "The Public Service
Rules — Complete Guide" course as FOUR new modules (Parts 1-4, given
the chapter's real size — 7 sections, ~44 rules, pages 68-88, by far
the largest chapter in the document), and adds 5 more questions to
the course's existing final exam bank. Requires the course to already
exist; safe to re-run — does nothing if Part 1 has already been
added."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Course, Lesson, Module
from apps.organizations.models import Organization

MODULES = [
    ("Chapter 10, Part 1: Introduction and General Inefficiency",
     """<h2>Everyone's duty to know the rules</h2>
<p>Every officer is personally responsible for knowing the disciplinary rules and every other regulation in force — this chapter is meant to be read alongside the "Guidelines for Appointments, Promotion and Discipline" issued jointly by the FCSC and OHCSF. Disciplinary authority over Federal Civil Service officers is vested in the Federal Civil Service Commission itself, though the Commission delegates full disciplinary power to Permanent Secretaries and Heads of Extra-Ministerial Offices for officers on GL.13 and below — with one real carve-out: the power of dismissal specifically is delegated only down to GL.06 and below. No Director-General or Chief Executive Officer can remove an officer from service without Board approval, except for GL.06-and-below officers removed on the Junior Staff Committee's recommendation.</p>
<h2>What "general inefficiency" actually means</h2>
<p>General inefficiency isn't one incident — it's a series of omissions or incompetence whose cumulative effect shows the officer genuinely can't discharge their duties efficiently. A superior officer who spots a fault has a real duty to flag it to the subordinate and record having done so, with the goal of improving their usefulness — possibly through redeployment to better-suited work, or training. Before removal proceedings for general inefficiency can even begin, the officer must have been warned in writing on three separate occasions — this is a hard procedural floor, not a suggestion.</p>
<h2>A real protection for pregnant officers</h2>
<p>No female public servant can be required to resign or retire because of pregnancy alone. If the pregnancy genuinely interferes with efficient performance, Management has discretion to assign lighter duties instead — but pregnancy itself is never grounds for forced exit.</p>
<h2>Terminating temporary staff, and increment discipline</h2>
<p>Permanent Secretaries can terminate temporary staff for inefficiency at their discretion (subject to the Labour Act and the officer's letter of appointment terms), but only after informing the officer of the grounds and giving them a genuine opportunity to respond — the same warn-first, explain-first principle that runs through this whole chapter. Where a Permanent Secretary has delegated power to withhold or defer an increment, they must inform the officer in writing immediately, stating the reason and (for deferment) the exact period; where that power isn't delegated, the matter goes to committee first. Either way, the Accountant General and Auditor General must also be informed. If an increment is later restored, the officer must be told immediately. Termination for inefficiency itself requires notice — normally one calendar month, inclusive of any leave owed; if the leave period is longer than the notice period, the officer is simply sent on leave and the notice period absorbed into it.</p>"""),
    ("Chapter 10, Part 2: Misconduct",
     """<h2>What counts as misconduct</h2>
<p>Misconduct is a specific, provable act of wrongdoing or improper behavior that damages the Service's image — real enough to investigate and prove, and serious enough that it can lead to termination or retirement. The Rules list a genuinely long set of examples: scandalous conduct (immoral or unruly behavior, drunkenness, foul language, assault, battery), refusing a transfer or posting, habitual lateness, deliberately delaying official documents, failing to keep records, unauthorized removal of public records, dishonesty, negligence, sleeping on duty, improper or immodest dressing while on duty, hawking merchandise in the office, refusing a lawful instruction, malingering, insubordination, and discourteous behavior toward the public.</p>
<h2>The query process — a real chance to respond</h2>
<p>As soon as a superior officer is dissatisfied with a subordinate's behavior, they must inform the officer in writing with specific details, and call for a written response within a set time. After considering that response, three outcomes are possible: the officer has fully exculpated themselves (no further action, just written confirmation); they haven't exculpated themselves but punishment isn't warranted (a formal letter of advice, acknowledged in writing); or they haven't exculpated themselves and do deserve punishment, which escalates to the full disciplinary procedure. Separately, where a Tribunal of Inquiry recommends disciplinary action against an officer, the FCSC can't act on that recommendation until the officer has been given a genuine chance to respond to the allegations.</p>
<h2>Reporting up the chain</h2>
<p>Every officer has a duty to report misconduct they witness to someone senior to the officer involved. Once misconduct reaches a superior officer's attention, they must report it through their HOD to the Director of Human Resource without delay — including a recommendation on interdiction if warranted. The Permanent Secretary then acts on the report, potentially interdicting the officer, and may suspend them at the appropriate point in the investigation.</p>
<h2>Discipline short of dismissal — and the full dismissal procedure</h2>
<p>Where the FCSC doesn't consider an act of misconduct serious enough to pursue dismissal, it can still investigate and impose lesser penalties — reduction in rank, withholding or deferring an increment, or similar — provided the officer knows the full case against them and has a genuine chance to defend themselves. Disciplinary proceedings against a female officer on maternity leave are postponed until the leave ends, without prejudicing the case either way. Where dismissal genuinely is on the table, a detailed, structured procedure applies: written notification of the precise grounds and likely penalty (with document access in serious cases), a standard query format, and — where necessary — a board of inquiry of at least three people (excluding the officer's own department head) before whom the officer can appear, call witnesses, and cross-examine. The board reports to the Commission, which decides: dismiss, impose a lesser penalty, direct retirement instead, or fully reinstate with back pay if the officer isn't found at fault. The entire process — except genuine criminal cases — must start and finish within 60 days.</p>
<h2>Smaller standing prohibitions</h2>
<p>Officers can't take paid outside professional work during office hours without written Permanent Secretary permission (any resulting fee goes to the Treasury pending a decision on whether the officer keeps any of it). No fine may ever be imposed as a punishment for an on-duty offense — though a genuine loss to public revenue from an officer's neglect can result in a surcharge instead. Officers can't stand surety for interest-bearing loans to others (ordinary bank deposits and co-op society sureties are fine), can't hawk merchandise on the premises, must dress appropriately in any official capacity, and can't issue personal letters of recommendation or character certificates in their official capacity.</p>"""),
    ("Chapter 10, Part 3: Serious Misconduct — Interdiction, Suspension, and Dismissal",
     """<h2>What makes misconduct "serious"</h2>
<p>Serious misconduct is a genuinely severe act of wrongdoing, damaging enough to the Service's image that, if proven, it can lead straight to dismissal. The Rules list an extensive set of examples: falsifying or suppressing records, withholding files, a criminal conviction beyond minor traffic/sanitary offenses, unauthorized absence, false claims against government officials, partisan political activity, bankruptcy, serious financial embarrassment, unauthorized disclosure of official information, bribery, corruption, embezzlement, misappropriation, violating the Oath of Secrecy, action prejudicial to state security, advance fee fraud, holding more than one full-time paid job, nepotism, divided loyalty, sabotage, willful damage to public property, sexual harassment, rape, cyber fraud, cult membership, and — a genuine catch-all — any other act unbecoming of a public officer. The same procedural discipline from ordinary misconduct (Rules 100302–100306) applies here too.</p>
<h2>Interdiction — half pay, not a punishment yet</h2>
<p>Where a serious case that could lead to dismissal has been opened, the Permanent Secretary may interdict the officer on no more than half pay while the case is decided. Interdiction is meant as a last resort — if continued duty performance is against the public interest or prejudices the investigation, alternative duties should be considered first. Once interdicted, the officer stops reporting for duty and receives 50% of their emoluments. If they're ultimately found not guilty, they're reinstated immediately with full back pay for the interdiction period; if found guilty but not dismissed, the Commission has discretion to refund some portion of what was withheld.</p>
<h2>What an interdicted or suspended officer must still do</h2>
<p>An officer under interdiction or suspension must notify their Permanent Secretary before leaving their station, and can't leave the country at all without specific Head of Civil Service approval. They're responsible for keeping their office informed of a reachable address — failing to respond to instructions sent there within seven days gets them treated as absent without leave. Suspension itself is a distinct, harsher status from interdiction: it applies once a serious prima facie case has been established and it's in the public interest to immediately bar the officer from their duties and emoluments altogether, pending investigation.</p>
<h2>Dismissal, and what it actually costs</h2>
<p>Dismissal is the ultimate penalty for serious misconduct. A dismissed officer forfeits all claims to retiring benefits, leave, and transport grants — subject to the Pension Reform Act 2014 — and dismissals from criminal cases are reported to law enforcement. No notice or pay in lieu is given; dismissal takes effect from the date the officer is actually notified, with specific fallback rules (service date, delivery-to-recorded-address date, or postal service date under the Interpretation Act) for an officer who tries to dodge notification.</p>
<h2>Criminal charges and financial embarrassment</h2>
<p>An officer must promptly report both being charged with a criminal offense and the eventual outcome. Where a court convicts an officer, the Commission can dismiss or otherwise punish them based on the court proceedings alone, skipping the full internal procedure entirely. Disciplinary action can proceed regardless of whether criminal proceedings are underway, contemplated, or resolved — though an officer acquitted of a specific charge can't be punished for that exact charge (separate charges from the same conduct are still fair game). A convicted officer (again, beyond minor offenses) is suspended from the date of conviction pending the Commission's own decision. Separately, "serious financial embarrassment" is a defined threshold — unsecured debts exceeding three times monthly emoluments, being an unsettled judgment debtor, or undischarged bankruptcy — treated as automatically impairing efficiency and grounds for discipline. If caused by imprudence, it can mean immediate dismissal, with the burden on the officer to justify otherwise; court registrars must report judgment debtors, and an officer stays disqualified from promotion or acting appointments for as long as the embarrassment continues.</p>"""),
    ("Chapter 10, Part 4: Conduct Restrictions, State Security, and Senior Officer Discipline",
     """<h2>Secrecy, records, and information</h2>
<p>Every officer with access to classified material must sign the Oath of Secrecy before that access is granted, and every officer is bound by the Official Secrets Act — disclosing confidential information without authorization is a real, specific prohibition, not just a general expectation. Officers can't abstract or copy official documents without permission, generally can't access their own secret personnel records, and can't remove public records on leaving the Service without written OHCSF permission. Any historical document of public interest an officer discovers must be reported for preservation, never kept for personal use.</p>
<h2>Public speech and political activity — real, specific limits</h2>
<p>Without express Permanent Secretary permission, an officer can't edit or manage a newspaper (departmental magazines, professional journals, and voluntary-organization publications are exempt), publish or broadcast anything of a political or administrative nature, or give interviews on policy, defense, or administration matters. Permission runs through a two-stage process — provisional approval on an outline, final approval only once the Permanent Secretary has reviewed the complete manuscript. Genuinely non-political general-interest writing is still allowed, provided any government-sourced material carries a clear disclaimer of government responsibility for its accuracy. Political activity itself is similarly restricted: no political-party office, no standing for election, no public support or opposition to a party or candidate, and no campaigning — though voting remains completely unrestricted. An officer seeking elective office must resign three months before the election; failing to do so is treated as automatic resignation, effective three months from election day.</p>
<h2>Money, investments, and gifts</h2>
<p>Officers may hold shares in public or private companies but can't be directors of private ones (only of public companies, and only if government-nominated), and must disclose any investments within three working days if their Permanent Secretary asks — failing to divest a conflict-of-interest holding within six months gets reported to the FCSC. Private practice is generally prohibited, with narrow exemptions for medical practitioners, law lecturers, and ICT/agribusiness professionals whose outside work doesn't conflict with official duties. Officers can't borrow from anyone under their official authority, anyone they have official dealings with, or registered moneylenders — ordinary bank loans, co-op loans, and hire-purchase remain fine, within the same financial-embarrassment thresholds from Part 3. Gifts tied to services rendered or anticipated are prohibited (small personal gifts between colleagues are fine); unavoidable gifts from traditional rulers must be handed over to government. Chieftaincy titles can't be accepted while still serving, except an inherited title with proper clearance through the Secretary to the Government of the Federation. And underlying all of this: no bribery, no corruption, full stop.</p>
<h2>State security, retirement in the public interest, and disciplining a Permanent Secretary</h2>
<p>Where a joint Federal Ministry of Justice/OHCSF committee finds an officer's misconduct genuinely involves or prejudices state security, the normal disciplinary procedure still applies — but the punishment is deliberately aggravated. Separately, the FCSC can retire an officer purely in the public interest even where the ordinary misconduct procedure doesn't cleanly fit — after a full report from the officer's Permanent Secretary and a genuine chance for the officer to respond, with pension handled under the Pension Reform Act. Disciplining a Permanent Secretary themselves follows its own track: their Minister flags the issue to the Head of the Civil Service of the Federation, who notifies the Permanent Secretary in writing and hears their response; an unsatisfactory response escalates to the Federal Service Management Committee, before which the Permanent Secretary can appear and call witnesses. The Committee's recommendation goes to the HCSF, then to the President for the actual decision, which the HCSF then conveys back. The available disciplinary measures span the full range — dismissal, termination, or retirement; reduction in rank or salary; withholding or deferring an increment; loss of pay; surcharge; reprimand; written warning; or verbal warning.</p>"""),
]

NEW_FINAL_EXAM_QUESTIONS = [
    (
        "Before removal proceedings for general inefficiency can begin, how many times must an officer have been warned in writing?",
        "Rule 100203: before removal proceedings for general inefficiency may be commenced, the officer must "
        "have been warned on three occasions in writing.",
        "Three occasions",
        "One occasion, with no further warning required",
    ),
    (
        "Within how many days must all disciplinary procedures (except criminal cases) commence and be completed?",
        "Rule 100307(xiii): all disciplinary procedures must commence and be completed within a period of 60 "
        "days except where it involves criminal cases.",
        "60 days",
        "30 days",
    ),
    (
        "At what proportion of pay may an officer be interdicted pending determination of a serious misconduct case?",
        "Rule 100404(iii): the proportion of emoluments received while on interdiction shall be 50% of the "
        "officer's emoluments.",
        "Not more than half pay (50%)",
        "Full pay, with no reduction",
    ),
    (
        "An officer is deemed to be in 'serious financial embarrassment' if their unsecured debts exceed what threshold?",
        "Rule 100414(1)(a): an officer is deemed in serious financial embarrassment if unsecured debts and "
        "liabilities exceed three times his monthly emoluments.",
        "Three times their monthly emoluments",
        "Their total annual emoluments",
    ),
    (
        "How far before an election must an officer seeking elective office tender their resignation?",
        "Rule 100423(i): any officer seeking elective office is to tender his resignation three months before "
        "the election.",
        "Three months before the election",
        "One month before the election",
    ),
]


class Command(BaseCommand):
    help = "Appends Chapter 10 (four modules) to the PSR course and its final exam. Safe to re-run."

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
            self.stdout.write(self.style.SUCCESS(f"Added {len(MODULES)} modules for Chapter 10."))

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
