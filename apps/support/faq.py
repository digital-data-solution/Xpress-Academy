"""The "pre-answered bot" — plain keyword matching, no external AI
API. That's a deliberate choice, not a shortcut: an LLM call here
would be one more paid dependency and one more thing that can be wrong
about a real learner's money/certificate, for a job a lookup table
already does honestly. Every entry answers from what's actually true
of this codebase (see the linked views/models in each answer) rather
than a generic canned line.

Each entry's `keywords` are matched case-insensitively as substrings
against the learner's message. The entry with the most keyword hits
wins; ties keep the earlier entry (FAQ_ENTRIES is meant to be ordered
roughly most-common-question-first). No hit at all means the bot has
nothing honest to say, and the message escalates to a human instead of
guessing — see services.find_answer / post_learner_message.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FAQEntry:
    key: str
    keywords: tuple
    question: str
    answer: str


FAQ_ENTRIES = [
    FAQEntry(
        key="payment_pending",
        keywords=("payment", "paid", "pay", "debit", "debited", "charged", "pending", "transaction"),
        question="I paid but the site still shows the course/certificate as unpaid",
        answer=(
            "If Paystack already debited you but the course still looks unpaid, this is usually "
            "a payment that didn't get confirmed back to us — it happens if the browser tab closes "
            "right after paying, before the redirect finishes. It's not lost: our system reconciles "
            "pending payments automatically. If it's been more than 30 minutes and still hasn't updated, "
            "reply here with the approximate time you paid and we'll check it directly — do not pay twice."
        ),
    ),
    FAQEntry(
        key="certificate_download",
        keywords=("certificate", "cert", "download", "pdf"),
        question="My certificate won't download / looks wrong",
        answer=(
            "Certificates are issued automatically once a course is fully completed (and paid for, "
            "on courses that require it). If you've finished every module and paid where required but "
            "don't see a certificate yet, or the download link doesn't work, reply here with the course "
            "name and we'll check your enrollment and regenerate it if needed."
        ),
    ),
    FAQEntry(
        key="login_password",
        keywords=("password", "login", "log in", "signin", "sign in", "reset", "locked out", "forgot"),
        question="I can't log in / forgot my password",
        answer=(
            "Use \"Forgot password\" on the login page to reset it by email — the reset link goes to "
            "the address you signed up with. If the email doesn't arrive within a few minutes, check "
            "spam, and reply here if it still doesn't show up so we can check your account directly."
        ),
    ),
    FAQEntry(
        key="final_exam_locked",
        keywords=("final exam", "exam locked", "quiz locked", "can't access exam", "cannot access exam", "final quiz"),
        question="I can't access the final exam",
        answer=(
            "The final exam only unlocks once every module/lesson in the course is marked complete — "
            "this is deliberate, so a certificate always means the whole course was actually covered. "
            "Go back to the course page and check for any lesson without a checkmark."
        ),
    ),
    FAQEntry(
        key="course_access",
        keywords=("access", "enroll", "enrolled", "can't see course", "cannot see course", "start course"),
        question="I enrolled but can't access the course",
        answer=(
            "If you completed checkout, your course should appear on your dashboard immediately. If it "
            "doesn't, it's most likely the same payment-confirmation delay as above — reply here with "
            "the course name and roughly when you paid, and we'll check it."
        ),
    ),
    FAQEntry(
        key="refund",
        keywords=("refund", "money back", "cancel my", "cancel payment"),
        question="Can I get a refund?",
        answer=(
            "Reply here with the course name and reason and we'll review it directly — refunds are "
            "handled case by case by a human, not automatically."
        ),
    ),
    FAQEntry(
        key="become_instructor",
        keywords=("teach", "instructor", "apply to teach", "become a teacher", "become instructor"),
        question="How do I become an instructor?",
        answer=(
            "Apply at /teach/apply/ with your background and area of expertise. Applications are "
            "reviewed by a human — there's no instant approval — and once verified, we work with you "
            "directly to build your course (video, reading, images, quizzes — whatever the subject needs)."
        ),
    ),
    FAQEntry(
        key="talk_to_human",
        keywords=("human", "agent", "real person", "someone", "talk to a person", "representative"),
        question="I want to talk to a real person",
        answer=(
            "Understood — this has been flagged for a human to reply directly. You'll get a reply here "
            "and by email."
        ),
    ),
]

# Checked first, always forces escalation regardless of any keyword
# match above — asking for a human should never get a bot answer
# instead, even if the message also happens to contain FAQ keywords.
FORCE_ESCALATE_KEYWORDS = ("human", "agent", "real person", "representative", "speak to someone", "talk to a person")


def find_answer(text: str) -> FAQEntry | None:
    """Best keyword match, or None if nothing scores at least one hit
    — a zero-hit message is exactly the case that should reach a
    person rather than get a bot's best guess."""
    lowered = text.lower()
    best, best_score = None, 0
    for entry in FAQ_ENTRIES:
        score = sum(1 for kw in entry.keywords if kw in lowered)
        if score > best_score:
            best, best_score = entry, score
    return best


def wants_human(text: str) -> bool:
    lowered = text.lower()
    return any(kw in lowered for kw in FORCE_ESCALATE_KEYWORDS)
