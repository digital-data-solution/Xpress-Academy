from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from apps.catalog.models import Course, Module
from apps.common.models import TimeStampedModel, OrganizationOwnedModel


class Topic(models.Model):
    """A shared taxonomy tag across the whole platform, not per-org —
    unlike Programme/Course/QuestionBank. "Ovulation Timing" means the
    same thing whether it tags a breeder-track or a vet-track question,
    and item-quality reporting (which questions perform badly — see
    Phase 11 ops signal quiz.item_bad) is more useful aggregated across
    everything than fragmented per tenant. Deliberate carve-out from
    non-negotiable #2, same category as Django's own Permission/
    ContentType models being global rather than per-tenant.
    """

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class SourceExam(models.Model):
    """Which real, external exam a question was written for — JAMB, WAEC,
    TRCN PQE, a civil service exam, etc. Global, not per-tenant, same
    reasoning as Topic: "JAMB" means the same thing platform-wide.

    First-class per the question-bank-engine spec's explicit instruction
    ("Make SourceExam a first-class dimension... Do not fork") — this
    model, plus SyllabusTopic and Question.source_exam below, is the
    whole of what that requires. Adding a new exam type later (WAEC,
    TRCN, civil service) is one new row here plus new SyllabusTopic rows
    under it — the generation, verification, and delivery code (Quiz/
    Attempt, already built) doesn't change at all."""

    code = models.SlugField(max_length=30, unique=True, help_text="Short code, e.g. 'jamb', 'waec', 'trcn-pqe'.")
    name = models.CharField(max_length=255, help_text="Full name, e.g. 'JAMB UTME'.")
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class SyllabusTopic(models.Model):
    """A real, hierarchical syllabus position — Subject > Section > Topic
    — for one SourceExam, distinct from the existing Topic model above.

    Deliberately NOT reusing Topic directly: Topic is a flat, single-level
    tag shared across the whole platform's existing course quizzes (see
    its own docstring — the point is aggregated cross-tenant item-quality
    reporting, e.g. "Ovulation Timing" meaning the same thing everywhere).
    Retrofitting a real exam syllabus's actual hierarchy (JAMB Biology's
    5 sections, each with several named sub-topics) onto that flat,
    general-purpose tag would either break Topic's existing semantics or
    force a hierarchy onto every other course's quiz tagging that never
    needed one. A Question can (and should) still carry both: SyllabusTopic
    for exam-specific reporting/syllabus-coverage, and the existing Topic
    M2M for the platform-wide item-quality signal to keep working
    unchanged.

    subject is a plain string, not its own model, deliberately — JAMB's
    "Biology" and a future WAEC "Biology" are the same subject name but
    different syllabuses (different SourceExam), so subject only needs
    to be unique within one SourceExam, not globally; a full Subject
    model would be one more join for no real benefit at this scale."""

    source_exam = models.ForeignKey(SourceExam, on_delete=models.CASCADE, related_name="syllabus_topics")
    subject = models.CharField(max_length=100, help_text="e.g. 'Biology', 'Chemistry', 'Mathematics'.")
    section = models.CharField(max_length=255, blank=True, help_text="e.g. 'A. Variety of Organisms' — the syllabus's own top-level grouping, if it has one.")
    name = models.CharField(max_length=255, help_text="The specific topic, e.g. 'Nutrition' or 'Heredity — Sex-linked Characters'.")
    order = models.PositiveIntegerField(default=0, help_text="Display order within the syllabus, roughly matching the official document's own sequence.")

    class Meta:
        ordering = ["source_exam", "order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["source_exam", "subject", "name"], name="unique_syllabus_topic_per_exam_subject"),
        ]

    def __str__(self):
        return f"{self.source_exam.code}/{self.subject}: {self.name}"


class QuestionBank(OrganizationOwnedModel):
    """Top-level owned entity — carries the tenant FK directly, same
    as Programme/Course (see catalog's Multi-tenancy note)."""

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Question(TimeStampedModel):
    class Type(models.TextChoices):
        MCQ = "MCQ", "Multiple choice (single answer)"
        MULTI_SELECT = "MULTI_SELECT", "Multiple choice (select all that apply)"
        TRUE_FALSE = "TRUE_FALSE", "True / False"

    class Difficulty(models.TextChoices):
        EASY = "EASY", "Easy"
        MEDIUM = "MEDIUM", "Medium"
        HARD = "HARD", "Hard"

    # CASCADE, not PROTECT: once a question has been served in an
    # Attempt, the full stem/choices/correct-answer are snapshotted
    # onto that Attempt's question_snapshot JSON — deleting the live
    # Question or its whole bank later does not corrupt historical
    # grading or the results page. This is different from
    # Course/Organization, which have no analogous snapshot
    # protecting Enrollment.
    bank = models.ForeignKey(QuestionBank, on_delete=models.CASCADE, related_name="questions")
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.MCQ)
    stem = models.TextField()
    explanation = models.TextField(blank=True, help_text="Shown to the learner after grading.")
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    topics = models.ManyToManyField(Topic, blank=True, related_name="questions")
    is_active = models.BooleanField(default=True)
    source_note = models.CharField(max_length=255, blank=True)

    # --- Question bank engine: SourceExam as a first-class dimension ---
    # Both null/blank so every existing Question (ordinary course quizzes,
    # not tied to any external exam) is unaffected — this is purely
    # additive. A Question with source_exam set is exam-bank content
    # (JAMB, WAEC, ...); one without it is regular course-quiz content,
    # same model, same Quiz/Attempt delivery either way.
    source_exam = models.ForeignKey(
        SourceExam, on_delete=models.PROTECT, related_name="questions", null=True, blank=True,
        help_text="Which real exam this question targets, if any (JAMB, WAEC, ...). Blank for ordinary course-quiz questions.",
    )
    syllabus_topics = models.ManyToManyField(
        SyllabusTopic, blank=True, related_name="questions",
        help_text="Real syllabus position(s) within source_exam — only meaningful when source_exam is set.",
    )
    # Mandatory-verification-pass tracking (spec: "every generated
    # question is independently re-solved in a separate pass that does
    # not see the stored answer key... never published" if it disagrees).
    # Only relevant to AI-generated exam-bank questions; True by default
    # so hand-authored course-quiz questions (the overwhelming existing
    # majority) aren't retroactively treated as unverified.
    is_ai_generated = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=[("N_A", "Not applicable"), ("VERIFIED", "Verified — independent pass agreed"),
                  ("DISPUTED", "Disputed — independent pass disagreed, needs human review")],
        default="N_A",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.stem[:80]

    @property
    def is_well_formed(self):
        """Defensive check used when drawing questions for an attempt
        (see services.start_attempt) — malformed questions are skipped
        from the pool rather than hard-blocked at save time, since
        Django admin saves a Question before its Choice inlines exist
        and strict clean() validation would fight that save order."""
        choices = list(self.choices.all())
        correct_count = sum(1 for c in choices if c.is_correct)
        if self.type in (self.Type.MCQ, self.Type.TRUE_FALSE):
            return len(choices) >= 2 and correct_count == 1
        if self.type == self.Type.MULTI_SELECT:
            return len(choices) >= 2 and correct_count >= 1
        return False

    @property
    def is_publishable(self):
        """The real gate services._build_question_snapshot filters on —
        is_well_formed alone isn't enough for AI-generated exam-bank
        content: the spec is explicit that a DISPUTED question (the
        independent verification pass disagreed with the stored answer)
        must "never [be] published," not just flagged. Hand-authored
        course-quiz questions are unaffected (verification_status
        defaults to N_A, not DISPUTED)."""
        return self.is_well_formed and self.verification_status != "DISPUTED"


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text[:60]


class Quiz(models.Model):
    class Scope(models.TextChoices):
        MODULE = "MODULE", "Module quiz"
        FINAL = "FINAL", "Final assessment"

    scope = models.CharField(max_length=10, choices=Scope.choices)
    # Exactly one of module/course must be set, matching scope —
    # same pattern as catalog.Resource. CASCADE: a module-scoped quiz
    # is meaningless without its module, same reasoning as Lesson.
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="quizzes", null=True, blank=True
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="quizzes", null=True, blank=True
    )

    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)

    # PROTECT: a live Quiz depends on its bank to generate new
    # attempts. Emptying that source out from under it is a content
    # bug, not a delete an admin should be able to do by accident.
    bank = models.ForeignKey(QuestionBank, on_delete=models.PROTECT, related_name="quizzes")
    question_count = models.PositiveIntegerField(default=10)
    topic_filter = models.ManyToManyField(Topic, blank=True, related_name="quizzes")
    # Separate from topic_filter deliberately: topic_filter scopes an
    # ordinary course/module quiz against the platform-wide flat Topic
    # taxonomy; this scopes a question-bank-engine mock exam (JAMB/WAEC/
    # etc.) against the exam-specific, hierarchical SyllabusTopic tree
    # instead — e.g. "JAMB Biology, Ecology section only". Additive, not
    # a replacement of topic_filter, so existing course/module quizzes
    # are untouched. Both filters apply (AND) when both are set on the
    # same quiz, though in practice a quiz uses one or the other.
    syllabus_topic_filter = models.ManyToManyField(
        SyllabusTopic, blank=True, related_name="quizzes",
        help_text="Scope this quiz to specific syllabus topics (question-bank-engine mock exams only).",
    )

    pass_mark = models.PositiveIntegerField(default=70)
    max_attempts = models.PositiveIntegerField(default=0, help_text="0 = unlimited.")
    time_limit_minutes = models.PositiveIntegerField(default=0, help_text="0 = no time limit.")
    randomize_choices = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "quizzes"

    def __str__(self):
        return self.title

    def clean(self):
        if self.scope == self.Scope.MODULE and not self.module_id:
            raise ValidationError({"module": "Required when scope is MODULE."})
        if self.scope == self.Scope.FINAL and not self.course_id:
            raise ValidationError({"course": "Required when scope is FINAL."})
        if self.module_id and self.course_id:
            raise ValidationError("Set exactly one of module or course, not both.")

    @property
    def course_ref(self) -> Course:
        """The course this quiz belongs to either way — used by
        access-control and unlock code that doesn't care about scope."""
        return self.course or self.module.course


class Attempt(TimeStampedModel):
    # CASCADE: meaningless without its enrollment, and Enrollment
    # itself is PROTECTed elsewhere — same reasoning as LessonProgress.
    enrollment = models.ForeignKey("enrollment.Enrollment", on_delete=models.CASCADE, related_name="attempts")
    # PROTECT: a Quiz that has graded history behind it shouldn't be
    # casually deletable — matches the "don't lose graded work"
    # discipline applied to Enrollment.
    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="attempts")
    attempt_number = models.PositiveIntegerField()

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Null = no time limit on this attempt.")

    score_percent = models.PositiveIntegerField(null=True, blank=True)
    passed = models.BooleanField(null=True)

    # The exact questions and choice order served, snapshotted at
    # attempt-start — see build spec §4: "Never re-query the bank at
    # grading time; questions get edited and old attempts must remain
    # gradeable and auditable." is_correct lives in here but must
    # never be sent to the browser before submission — see
    # services.serialize_snapshot_for_display, the one function
    # allowed to strip it for rendering.
    question_snapshot = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["enrollment", "quiz", "attempt_number"], name="unique_attempt_number"),
        ]
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.enrollment.user.email} — {self.quiz.title} (#{self.attempt_number})"

    @property
    def is_in_progress(self):
        return self.submitted_at is None

    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at is not None and self.expires_at <= timezone.now() and self.is_in_progress


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    # PROTECT: historical per-question answer records are exactly what
    # the Phase 11 ops signal quiz.item_bad aggregates over
    # ("a question <20%% or >95%% correct across >=30 attempts") — a
    # Question with real answer history behind it shouldn't be
    # deletable; retire it via is_active=False instead.
    question = models.ForeignKey(Question, on_delete=models.PROTECT, related_name="attempt_answers")
    selected_choices = models.ManyToManyField(Choice, blank=True, related_name="selected_in_answers")
    is_correct = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_attempt_question_answer"),
        ]

    def __str__(self):
        return f"{self.attempt} — {self.question_id}"
