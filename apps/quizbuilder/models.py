"""Self-serve quiz builder — MVP scoped from a research pass into the
Google Forms / Microsoft Forms / ProProfs-shaped market (see the
project memory this was proposed from). Positioning: a free,
"Powered by Xpress Digital Academy"-branded pre-test/post-test tool
any signed-in user can build for their own workplace training,
functioning as a lead-gen surface, with a paired pre/post delta
report as the concrete differentiator those tools don't offer.

Deliberately its own app, separate from:
- apps.assessment — the JAMB/WAEC/Civil-Service verified exam-bank
  engine (independently blind-verified, syllabus-tied, staff-authored
  only). Keeping user-generated throwaway quizzes out of that app's
  tables means its integrity guarantees (is_publishable,
  verification_status) are never accidentally diluted.
- apps.licensing.DiagnosticMockTest — free diagnostics, but still
  staff-curated (via Django admin) against a verified QuestionBank.
  This app is the opposite shape: ANY signed-in user authors their
  own quiz, no verification pipeline, no syllabus tie-in, no
  organization FK (works for a solo trainer with a free account, not
  just an Institution with a licence).

MVP scope deliberately narrow (documented here so a future session
doesn't wonder why something "obvious" is missing):
- Single-page take-flow: no resumable/timed attempt state machine
  like DiagnosticAttempt has (time_limit_minutes is stored but not
  yet enforced server-side) -- a short pre/post training quiz doesn't
  need that complexity, unlike a 30-minute mock exam.
  respondent_name/email are both required (unlike DiagnosticAttempt's
  optional email) because pairing pre/post responses for the same
  person is the whole point of TrainingSession.
- No snapshotting: unlike the exam-bank engine (which samples a
  random subset from a large verified bank, so a snapshot is needed
  to keep a past attempt's questions stable even if the bank changes
  later), a Quiz here IS its own fixed, small question set -- there's
  nothing to sample, so the live Question/Choice rows are already the
  permanent record once a Quiz has responses.
- Free tier only: no response/quiz count cap enforced at launch
  (matches how Google Forms itself behaves) -- the free/paid split is
  about the non-removable branding on quiz-taking and export pages,
  not usage limits. A future paid tier removing that branding can
  read/write this same schema with no migration needed.

Ownership philosophy (v2, added after the MVP proved out): since this
content is never verified the way the exam-bank engine's is, the
platform's job is to get out of the creator's way, not gatekeep them.
Concretely: a creator can edit a quiz's questions even after it has
responses (a warning explains the tradeoff -- old responses' recorded
answers may no longer line up with the edited question set -- but the
choice is theirs, not blocked outright), can delete a quiz or any
individual response entirely, and can duplicate a quiz wholesale (the
fast path to turning a pre-test into a post-test). In exchange, a
first-time creator has to explicitly acknowledge they're responsible
for their own quiz's accuracy before their first quiz goes live --
see views.quiz_create's is_first_quiz check -- and every public quiz
page credits "Content by <creator>" alongside the platform's own
"Powered by" branding, so it's never ambiguous whose content it is.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import TimeStampedModel, UUIDModel


class Quiz(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quizbuilder_quizzes"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, help_text="Shown to respondents before they start.")
    slug = models.SlugField(max_length=64, unique=True, blank=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Turn off to stop accepting new responses without deleting the quiz or its existing data.",
    )
    time_limit_minutes = models.PositiveIntegerField(
        default=0, help_text="0 = no time limit. Informational only in this MVP — not yet enforced server-side."
    )
    show_score_immediately = models.BooleanField(
        default=True, help_text="Show each respondent their own score right after they submit."
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:50] or "quiz"
            slug = base
            n = 1
            while Quiz.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def response_count(self):
        return self.responses.filter(submitted_at__isnull=False).count()


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=0)
    stem = models.TextField()
    points = models.PositiveIntegerField(default=1, help_text="How much this question is worth toward the total score.")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.stem[:60]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    order = models.PositiveIntegerField(default=0)
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.text[:60]


class Response(UUIDModel, TimeStampedModel):
    """One respondent's run through a Quiz. Public/unauthenticated by
    design, identified by uuid — same "never leak sequential
    information" reasoning as every other public-attempt model on
    this platform (DiagnosticAttempt, certificate verification)."""

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="responses")
    respondent_name = models.CharField(max_length=255)
    respondent_email = models.EmailField(
        help_text="Required (unlike the free diagnostics) — this is the join key TrainingSession uses to "
                   "match a person's pre-test to their post-test."
    )
    # {"<question_id>": <choice_id>, ...} — see the module docstring's
    # "No snapshotting" note for why this is safe without a
    # question_snapshot the way DiagnosticAttempt needs one.
    answers = models.JSONField(default=dict, blank=True)
    score_percent = models.PositiveIntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.respondent_name} — {self.quiz.title}"


class TrainingSession(TimeStampedModel):
    """Pairs a Pre-Test Quiz and a Post-Test Quiz for one training
    event — the concrete pre/post delta-report feature Google Forms /
    Microsoft Forms / ProProfs don't offer natively, and the real
    reason this app exists rather than just pointing users at one of
    those. Matching between the two quizzes' responses happens by
    respondent_email at report-generation time (services.py) — no
    stored link between individual Response rows, so pairing works
    retroactively even for quizzes that existed before their session
    was created."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quizbuilder_sessions"
    )
    title = models.CharField(max_length=255)
    pre_quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    post_quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, null=True, blank=True, related_name="+")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
