"""Seeds 'The Public Service Rules — Complete Guide', a real instructional
course teaching the Federal Government Public Service Rules (PSR) 2021
edition, chapter by chapter. Sourced directly from the user's own hard
copy (verified against the official soft copy at oagf.gov.ng) — every
module's content is drawn from the actual transcribed rule text, not
invented. See project memory for the sourcing/verification process.

Built incrementally, chapter by chapter, given the document's real size
(17 chapters, ~500 rules). This command currently seeds Chapters 1-2;
later chapters are added via seed_psr_course_ch<N>.py-style follow-ups
or by extending MODULES here directly — same "one command, re-run
safely" pattern as every other seed command on this platform.

Same VET/business-CE course shape as every other instructor-authored
course here: real prose per module (not raw rule dumps), a short
quiz-style final exam, unpublished until reviewed. Audience is GENERAL
(any civil servant or aspiring civil servant), not VET-specific.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

MODULES = [
    ("Chapter 1: Introduction",
     """<h2>What the PSR actually is</h2>
<p>The Public Service Rules (PSR) are the Federal Government's own policies and guidelines defining the employment relationship between public servants and government — conditions of service, and the human resources management procedures that govern a civil servant's entire career. They are enforced strictly across every Ministry, Extra-Ministerial Office, and Agency.</p>
<h2>Who they apply to — and who's exempt</h2>
<p>The PSR apply to all officers in the Public Service, with one real exception: the holders of a specific list of high constitutional and statutory offices (the President, Vice President, National Assembly members, judiciary at the highest levels, the Auditor-General for the Federation, the Federal Civil Service Commission, and a handful of other named statutory bodies) are only bound by the PSR where it doesn't conflict with their own specific constitutional/appointment terms.</p>
<h2>The PSR bows to the Constitution</h2>
<p>The Rules only apply to the extent that they're consistent with the Constitution of the Federal Republic of Nigeria. Where a conflict exists on conditions of service, the Constitution and other applicable law win.</p>
<h2>Every officer's personal duty</h2>
<p>It's each officer's own individual duty to acquaint themselves with the PSR and other extant regulations and circulars — not something HR is solely responsible for keeping them informed of. A physical copy of the PSR must also form part of the inventory of every Public Service office.</p>
<h2>Key definitions worth knowing precisely</h2>
<p>A handful of Chapter 1's defined terms come up constantly through the rest of the Rules and are worth knowing exactly: <strong>Interdiction</strong> is the temporary removal of an officer from duty while dismissal proceedings are pending, on half salary. <strong>Suspension</strong> is removal from duty once a serious prima facie case is established, with no salary at all — a materially harsher status than interdiction. A <strong>Junior Officer</strong> is a pensionable officer on Grade Level 06 and below; <strong>Senior Posts</strong> start at GL.07. The <strong>Pass Mark</strong> for a promotion examination is currently 60%, below which a candidate is considered to have failed. Finally, wherever the PSR uses "Officer" or "Staff" in the masculine, the Rules explicitly apply equally to both genders — this isn't an oversight in the drafting, it's addressed directly in Rule 010107.</p>"""),
    ("Chapter 2, Part 1: Appointments, Recruitment and Probation",
     """<h2>Who actually has the authority to appoint you</h2>
<p>Appointments in the Federal Civil Service happen on the authority of the Federal Civil Service Commission (FCSC) — either by a letter under the Commission's direction, or by formal agreement between the officer and government. The FCSC itself handles appointments to posts graded GL.07–17; each individual Ministry or Extra-Ministerial Office handles GL.06 and below through its own Junior Staff Committee.</p>
<h2>The entry examination</h2>
<p>For GL.07–10 entry, there's an annual competitive Public/Civil Service Entry Examination, run jointly by the FCSC, the Office of the Head of the Civil Service of the Federation (OHCSF), the Administrative Staff College of Nigeria (ASCON), and the Public Service Institute of Nigeria (PSIN). Advertisements run in three national newspapers plus the Commission's website, with a six-week application window.</p>
<h2>Recruitment categories</h2>
<p>"Recruitment" specifically means filling vacancies from outside the Public Service entirely — it excludes transferring an officer already in Federal service. New entrants can come in as trainees/pupils, on probation in a pensionable post, on non-pensionable contract, in an acting capacity, or via special appointment routes (NYSC Presidential Merit Award winners are automatically absorbed regardless of vacancy; 5% of all recruitment is reserved for persons with disability).</p>
<h2>Eligibility, and the things that can block an appointment</h2>
<p>To be eligible at all, an applicant must be 18–50 years old, meet the qualification and computer-literacy requirements in the relevant Scheme of Service, be certified medically fit, and hold a testimonial of good conduct. No appointment can happen without an authorized establishment/recruitment waiver from OHCSF — and separately, no candidate can be appointed at all without the FCSC's (or the relevant Board's) prior specific approval if they've ever been convicted of a criminal offence, or previously dismissed or forced to resign/retire from public service. Every applicant must declare this history themselves.</p>
<h2>Probation and confirmation</h2>
<p>Nearly every first appointment to a pensionable post is on probation, normally for two years — reducible to as little as six months if the officer already has relevant prior public service. During probation, the officer must pass whichever examination applies to their appointment (a specific senior-post exam under Chapter 7, the general Promotion/Confirmation Examination for clerical grades, or a technical Scheme-of-Service exam) and complete their probationary period satisfactorily before confirmation follows automatically. A newly recruited officer becomes eligible to sit the compulsory confirmation exam (COMPRO) once they've served six months.</p>"""),
    ("Chapter 2, Part 2: Short-Term Appointments",
     """<h2>Why this category exists</h2>
<p>Where the Public Service needs specialized or emerging skills not yet in the standard Schemes of Service, it can fill the gap through several short-term routes rather than a normal pensionable appointment: Contract Appointments, Sabbatical Appointments, Career Exchange, Talent Sourcing, Internships, and Volunteerism.</p>
<h2>Contract appointments</h2>
<p>A Contract Appointment is a temporary, non-pensionable appointment recorded in a formal agreement — offered when the Service genuinely lacks the specific skill, or the post is tied to a funded project with a defined lifespan, or (for expatriates specifically) when no suitable Nigerian is available. A Nigerian can also be offered contract terms if they're already a pensioner, 50+ years old, or specifically request it. Contract duration runs 1–2 years at a time, renewable but capped at 4 years total, and the post must not be below Senior Grade Level 12. Crucially, a contract officer's actual conditions of service come from their contract itself, not the general PSR privileges — unless the contract explicitly says otherwise.</p>
<h2>Sabbatical, internship, and volunteerism</h2>
<p>Sabbatical Appointment is specifically for officers on GL.15 and above, for research/professional development, running 12 calendar months — the host organization covers travel and lodging while the parent MDA keeps paying salary. Internship gives students/graduates structured, discipline-relevant workplace experience (3–6 months part-time during a school session, or up to 12 months full-time). Volunteerism is broader — offering time or talent for charitable/educational work — and runs up to 12 months at a time, with stipends set by the National Volunteering Policy.</p>
<h2>Ending and renewing a contract</h2>
<p>A contract can be terminated by government at any time per its own terms. An officer wanting re-engagement must notify government in writing at least four months before their leave is due — silence is taken as not wanting re-engagement. If re-engagement genuinely happens before the old contract's leave period ends, service counts as continuous, not a break in service.</p>"""),
    ("Chapter 2, Part 3: Transfer, Secondment, Posting and Acting Appointments",
     """<h2>Transfer vs. secondment — a real distinction</h2>
<p>Transfer is the <em>permanent</em> release of an officer from one scheduled service (or class) to another. Secondment is <em>temporary</em> release to another government-approved body or recognized international organization for a fixed period. They are not interchangeable terms in the PSR, and the rules governing each are genuinely different.</p>
<h2>Secondment's real time limits</h2>
<p>An ordinary secondment runs a maximum of two years in the first instance, extendable, but capped at four years total. Where secondment is specifically in the public interest, that cap rises to six years. During secondment, the officer keeps their substantive post, keeps earning increments and remaining eligible for promotion, and is treated as though posted on special duty — secondment is not a career interruption.</p>
<h2>Posting — not a punishment tool</h2>
<p>Posting is the initial or reassigned placement of an officer to a position within or outside their current MDA, meant to build "whole-service" experience. The Rules are explicit that posting must never be used as a tool for coercion, punishment, or cronyism — fairness is the underlying principle. Posting outside an officer's professional cadre is prohibited outright, and pool officers must be posted at least every four years. Refusing a legitimate posting is itself treated as misconduct.</p>
<h2>A real protection for union executives</h2>
<p>Labour Union Executives cannot be posted out of their MDA until their tenure in office expires — a specific protection against using posting to remove an inconvenient union leader. Trade Unions/Staff Associations are themselves required to cap tenure at two terms of no more than two years each.</p>
<h2>Acting appointments — deliberately limited</h2>
<p>Acting appointment fills a duty post (SGL 14 and above) when no substantive-rank officer is available, and requires FCSC/Board approval and a gazette notice. Critically, the Rules state plainly that acting appointment is <strong>not</strong> a way to trial someone for promotion — it exists purely to keep a post filled temporarily. It's capped at one year, extendable once for another year, and a brief absence like casual leave doesn't count as relinquishing it, provided that leave is spent in Nigeria and no one else needs to be appointed to cover it.</p>"""),
    ("Chapter 2, Part 4: Promotion",
     """<h2>Who actually promotes you</h2>
<p>Promotion authority is layered by grade: GL.06 and below is handled at MDA level; GL.07 to Senior Grade Level 14 is handled by the Ministry/Extra-Ministerial Office with OHCSF approval, subject to FCSC confirmation; GL.15–17 goes through the FCSC itself on recommendation routed through OHCSF.</p>
<h2>The minimum time-in-post rule</h2>
<p>You cannot be promoted no matter how strong your performance until you've spent the minimum required time in your current post: 2 years minimum for GL.06 and below, 3 years for GL.07–14, and 4 years for GL.15–17. This is a hard floor, not a guideline.</p>
<h2>Merit, not just seniority</h2>
<p>Promotion is meant to be strictly competitive-merit-based. The Rules explicitly separate an officer's record of performance in their current (lower) grade from their assessed <em>potential</em> to perform the higher post's duties — these are treated as genuinely different questions. Seniority and past performance only become tiebreakers between candidates who are otherwise equally strong on potential; a generally satisfactory conduct record is required in every case regardless.</p>
<h2>Becoming a Permanent Secretary — a real, distinct track</h2>
<p>Permanent Secretary appointment has its own eligibility gate, separate from ordinary promotion: the candidate must already be a GL.17 Director in the mainstream Federal Civil Service, verified on the IPPIS platform, with at least two years on the Director post, not retiring within the following year, with proof of state indigeneship (which — the Rules specifically state — cannot be established through marriage for a female civil servant), and with no pending disciplinary action. Selection then runs through a genuinely competitive process: written examination, ICT proficiency testing, and oral interview, sometimes involving outside resource persons from both public and private institutions.</p>
<h2>Two real, separate tenure caps</h2>
<p>A Director (GL.17 or equivalent) must compulsorily retire after eight years in that specific post. A Permanent Secretary's own term is four years, renewable once for a further four years subject to satisfactory performance — eight years total, and no further renewal beyond that regardless of performance.</p>"""),
    ("Chapter 2, Part 5: Leaving the Service, Pension and Certificate of Service",
     """<h2>The different doors out</h2>
<p>An officer can leave the Federal Civil Service through several distinct routes, each with different consequences: termination during probation (for unsatisfactory conduct — generally with a month's notice and, if conduct was good, a free transport grant home), resignation (which forfeits vacation-leave claims and can require refunding any money owed to government), abolition of office or redundancy, repeatedly failing a promotion examination, or reaching mandatory retirement.</p>
<h2>The three-strikes rule on promotion exams</h2>
<p>An officer who fails a promotion examination three consecutive times — or who is absent without an acceptable reason (only a medical report from a recognized healthcare provider counts automatically as acceptable) — is deemed to have exited the service after that third failed or missed attempt. This is a real, hard consequence, not just a delay to the next promotion cycle.</p>
<h2>Mandatory retirement</h2>
<p>The mandatory retirement age is 60 years, or 35 years of pensionable service — whichever comes <em>first</em>. No officer may remain in service past whichever threshold is reached earlier, though this doesn't override separate, different retirement rules that already exist for judicial officers and university academic staff.</p>
<h2>Pension is compulsory, not optional</h2>
<p>Every pensionable officer must participate in the Contributory Pension Scheme under the Pension Reform Act 2014. To keep retirement benefits moving promptly, Departmental Pension Officers must forward a substantial, specific document set to PENCOM — gazetted first-appointment letter, birth certificate, last four promotion letters, IPPIS registration evidence, NIN, BVN, and more. Once that's done, retirement benefits are meant to be paid within one month of retirement, and National Housing Fund contributions accessed within that same one-month window.</p>
<h2>Certificate of Service</h2>
<p>Every departing officer — pensionable or not — receives a Certificate of Service, meant to serve as a reference for future employment. It requires specific countersignatures depending on grade (the Permanent Secretary, FCSC for GL.07+; the Permanent Secretary, Career Management Office for GL.06 and below), and the Rules are explicit that adverse comments have no place on it — if there's a real disciplinary issue, it has to be handled through proper disciplinary process before the officer leaves, not noted as a parting remark on their exit paperwork.</p>"""),
]

FINAL_EXAM_QUESTIONS = [
    (
        "What is the mandatory retirement age under the PSR?",
        "Rule 020908: 60 years or 35 years of pensionable service, whichever is earlier — a dual threshold, "
        "not a single fixed age.",
        "60 years or 35 years of pensionable service, whichever is earlier",
        "65 years of age only, regardless of years of service",
    ),
    (
        "How long is the standard probationary period before confirmation, and what's the shortest it can be reduced to?",
        "Rule 020301: normally two years, reducible to not less than six months where the officer already has "
        "relevant prior public service rendered satisfactorily.",
        "Two years, reducible to not less than six months for relevant prior service",
        "Six months in every case, with no possibility of extension",
    ),
    (
        "Is acting appointment meant to be used as a trial period to test someone's suitability for promotion?",
        "Rule 020703 states this explicitly: acting appointment is not intended as a means of testing suitability "
        "for promotion — it exists to fill temporarily vacant posts, nothing more.",
        "No — the Rules explicitly say it is not intended as a trial for promotion",
        "Yes — it is the Public Service's standard formal method for trialling promotion candidates",
    ),
    (
        "What happens to an officer who fails a promotion examination three consecutive times?",
        "Rule 020906(i): they are deemed to have exited the service after the third failed attempt (or third "
        "unexcused absence from the exam) — a real, hard consequence, not just a delay.",
        "They are deemed to have exited the service after the third failed attempt",
        "They are automatically enrolled in remedial training with no effect on their employment",
    ),
    (
        "What is the maximum total duration of an ordinary secondment (not specifically in the public interest)?",
        "Rule 020503(f): a maximum of two years in the first instance, extendable, but capped at four years "
        "total for an ordinary secondment.",
        "A maximum of four years in total",
        "A maximum of ten years in total",
    ),
    (
        "Under the PSR, can posting be used to punish or coerce an officer?",
        "Rule 020603: fairness is the explicit underlying principle for posting decisions, specifically so the "
        "system is never used as a tool for coercion, punishment, or cronyism.",
        "No — fairness is the explicit underlying principle, precisely to prevent that misuse",
        "Yes, provided the officer's Permanent Secretary personally approves the posting",
    ),
    (
        "What is the minimum time an officer must spend in a GL.07-14 post before becoming eligible for promotion?",
        "Rule 020802(c): a minimum of 3 years for Grade Levels 07-14 (2 years for GL.06 and below, 4 years "
        "for GL.15-17).",
        "A minimum of 3 years",
        "A minimum of 1 year",
    ),
    (
        "How many total years can a Permanent Secretary serve, including any renewal?",
        "Rule 020909: a four-year term, renewable once for a further four years subject to satisfactory "
        "performance — eight years total, with no further renewal after that.",
        "Eight years total (a four-year term, renewable once)",
        "An unlimited number of four-year terms, provided performance stays satisfactory",
    ),
    (
        "Can indigeneship for the Permanent Secretary eligibility criteria be established through marriage, for a female civil servant?",
        "Rule 020811(f) states this explicitly: indigeneship of a state must not be established by marriage in "
        "the case of a female civil servant.",
        "No — the Rules explicitly exclude marriage as a basis for indigeneship in this context",
        "Yes, marriage to an indigene of the state is an accepted route to establishing indigeneship",
    ),
    (
        "What is the main stated purpose of issuing a Certificate of Service?",
        "Rule 021103: to serve as a reference covering the holder's public service when seeking other "
        "employment — and Rule 021105 specifically bars adverse comments from appearing on it.",
        "To serve as a reference for the officer's public service when seeking future employment",
        "To formally record any unresolved disciplinary allegations against the officer",
    ),
]


class Command(BaseCommand):
    help = (
        "Seeds 'The Public Service Rules — Complete Guide' (Chapters 1-2 so far). "
        "Safe to re-run; later chapters extend MODULES in a follow-up."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="civil-service-training",
            defaults={
                "title": "Civil Service Training",
                "audience": Audience.GENERAL,
                "description": "Real instructional courses for Nigerian civil servants and aspiring civil "
                                "servants — starting with a complete, chapter-by-chapter guide to the Public "
                                "Service Rules.",
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="public-service-rules-guide",
                defaults={
                    "title": "The Public Service Rules — Complete Guide",
                    "subtitle": "A chapter-by-chapter guide to the Federal Government Public Service Rules "
                                 "(2021) — what every civil servant actually needs to know, in plain language.",
                    "description": "<p>The Public Service Rules govern the entire career of a Nigerian federal "
                                    "civil servant — appointment, promotion, discipline, leave, and everything "
                                    "in between. This course goes through the real Rules chapter by chapter, in "
                                    "plain language, with the exact rule numbers cited so you can always check "
                                    "back against the source document.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 5000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 2.0,
                    "is_published": False,
                    "sales_headline": "Know the actual rules that govern your civil service career",
                    "sales_subheadline": "A plain-language, chapter-by-chapter guide to the real Public "
                                          "Service Rules — appointments, promotion, discipline, leave, and more.",
                    "target_audience": (
                        "Federal civil servants at any grade level\n"
                        "Anyone preparing for civil service recruitment or promotion examinations\n"
                        "HR/personnel officers in Ministries, Extra-Ministerial Offices, and Agencies"
                    ),
                    "not_for": "Officers in state or local government service — this covers the Federal PSR specifically.",
                    "instructor_bio": "Xpress Digital Academy, sourced directly from the official 2021 Public Service Rules.",
                    "meta_description": "A plain-language, chapter-by-chapter guide to Nigeria's Federal "
                                         "Government Public Service Rules — real rule citations throughout.",
                },
            )

            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                return

            self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))
            for i, (title, body) in enumerate(MODULES, start=1):
                module = Module.objects.create(
                    course=course, order=i, title=title, unlock_rule=Module.UnlockRule.SEQUENTIAL,
                )
                Lesson.objects.create(
                    module=module, order=1, title=title, type=Lesson.Type.TEXT,
                    body=body.strip(), is_preview=(i == 1),
                )
            self.stdout.write(self.style.SUCCESS(f"  {len(MODULES)} modules created with real written content."))

            bank = QuestionBank.objects.create(
                organization=org, name="Public Service Rules — Complete Guide Final Exam",
                description="Covers Chapters 1-2 so far — must be passed to unlock the certificate.",
            )
            for stem, explanation, correct, wrong in FINAL_EXAM_QUESTIONS:
                q = Question.objects.create(
                    bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                    difficulty=Question.Difficulty.MEDIUM,
                )
                Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
            Quiz.objects.create(
                scope=Quiz.Scope.FINAL, course=course,
                title="Final Exam — The Public Service Rules",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin, "
            "or use the same 'Publish selected courses' bulk action as the exam-prep courses."
        ))
