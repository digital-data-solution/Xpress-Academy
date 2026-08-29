from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field

from apps.common.models import OrganizationOwnedModel, TimeStampedModel


class Audience(models.TextChoices):
    BREEDER = "BREEDER", "Breeder"
    VET = "VET", "Veterinarian"
    GENERAL = "GENERAL", "General"


class Programme(OrganizationOwnedModel):
    """Top of the content hierarchy — e.g. "Dog Breeding Courses"."""

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    audience = models.CharField(max_length=20, choices=Audience.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class WebhookLine(models.TextChoices):
        """Which external system (if any) apps.catalog.webhooks notifies
        when a course in this Programme publishes. An explicit,
        admin-editable choice per Programme rather than a hardcoded
        list of slugs in Python — new destinations are added by adding
        a choice + a settings URL/secret pair, not a redeploy-required
        rule change. Defaults NONE (opt-in): with more than one real
        destination now, assuming a new Programme belongs to any
        particular line is no longer a safe guess."""
        NONE = "NONE", "None — publishing doesn't notify any external system"
        DIGITAL = "DIGITAL", "Digital line (Xpress Digital Academy campaign system)"
        VET = "VET", "Veterinary line (Xpress Vet Marketplace)"

    webhook_line = models.CharField(
        max_length=20, choices=WebhookLine.choices, default=WebhookLine.NONE,
        help_text="Fires the matching course-publish webhook (if that destination is configured) when a course here publishes.",
    )

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class Course(OrganizationOwnedModel):
    """A sellable course. Tenant ownership lives here and on Programme —
    Module/Lesson/Resource below scope through their FK to Course and
    deliberately do NOT carry a duplicate organization FK. Two owned
    entities disagreeing on tenant (a Module pointing at a different
    org than its Course) is a data-integrity risk a redundant FK would
    invite, not prevent; the chain of FKs is the single source of
    truth. See ARCHITECTURE.md.
    """

    class Level(models.TextChoices):
        FOUNDATION = "FOUNDATION", "Foundation"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        ADVANCED = "ADVANCED", "Advanced"

    class AccessType(models.TextChoices):
        LIFETIME = "LIFETIME", "Lifetime"
        TIMED = "TIMED", "Timed"

    class PricingModel(models.TextChoices):
        PAID = "PAID", "Paid — pay to access the course"
        FREE = "FREE", "Free — course and certificate both free"
        CERTIFICATE_PAID = "CERTIFICATE_PAID", "Free course, paid certificate"
        PAY_WHAT_YOU_WANT = "PAY_WHAT_YOU_WANT", "Pay what you want — buyer names the price"

    # PROTECT: losing a Programme must never cascade-delete the paid
    # courses under it. Same discipline as Organization → everything.
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="courses")

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    subtitle = models.CharField(max_length=255, blank=True)
    description = CKEditor5Field(blank=True, config_name="default")

    cover_image = models.ImageField(upload_to="courses/covers/", blank=True, null=True)
    promo_video_id = models.CharField(max_length=255, blank=True)

    audience = models.CharField(max_length=20, choices=Audience.choices)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.FOUNDATION)

    pricing_model = models.CharField(
        max_length=20, choices=PricingModel.choices, default=PricingModel.PAID,
        help_text="PAID: pay to access. FREE: course and certificate both free. "
                   "CERTIFICATE_PAID: access is free, price_ngn is charged for the certificate instead.",
    )
    price_ngn = models.PositiveIntegerField(
        default=0,
        help_text="Whole naira. Ignored (treated as 0) when pricing_model is FREE. Used as "
                   "the suggested price when pricing_model is PAY_WHAT_YOU_WANT.",
    )
    minimum_price_ngn = models.PositiveIntegerField(
        default=0,
        help_text="Only used when pricing_model is PAY_WHAT_YOU_WANT — the floor the buyer "
                   "can't go under. 0 means a buyer can genuinely pay nothing.",
    )
    compare_at_price_ngn = models.PositiveIntegerField(
        null=True, blank=True, help_text="Strike-through 'was' price. Leave blank if none."
    )

    access_type = models.CharField(
        max_length=20, choices=AccessType.choices, default=AccessType.LIFETIME
    )
    access_months = models.PositiveIntegerField(
        null=True, blank=True, help_text="Required when access_type is TIMED."
    )

    content_version = models.PositiveIntegerField(
        default=1, help_text="Bump when material is materially updated."
    )
    free_update_months = models.PositiveIntegerField(default=12)

    requires_final_assessment = models.BooleanField(default=False)
    pass_mark = models.PositiveIntegerField(default=70)

    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    is_staff_training = models.BooleanField(
        default=False,
        help_text="Internal training course. Hidden from the public catalog entirely; the "
                   "course-detail page 404s for anyone not enrolled (or not a superuser) — enroll "
                   "someone via the Enrollment admin to grant access, same as any other course. Not "
                   "is_staff-based: a trainee needs no Django-admin login rights at all.",
    )
    is_compulsory_staff_training = models.BooleanField(
        default=False,
        help_text="Only meaningful when is_staff_training is also set. Every user is auto-enrolled "
                   "in this course the moment they're added to any Django Group (see "
                   "apps.accounts.signal_receivers) — the personal, sequential 'everyone goes through "
                   "this as they join' track. Pace modules with unlock_rule=DRIP_DAYS so each person's "
                   "journey runs from their own enrollment date, not a shared calendar date. Leave "
                   "unchecked for one-off department/personal/emergency training that's assigned "
                   "manually instead.",
    )
    required_group = models.ForeignKey(
        "auth.Group", on_delete=models.SET_NULL, null=True, blank=True, related_name="scoped_compulsory_courses",
        help_text="Only meaningful when is_compulsory_staff_training is also set. Leave blank for a "
                   "track every staff member goes through regardless of role (e.g. General "
                   "Onboarding). Set this to scope a role-specific compulsory course (e.g. Manager "
                   "Onboarding, Instructor Onboarding) so only members of that one Group are "
                   "auto-enrolled — without this, a second role-specific compulsory course would "
                   "force every staff member through every role's training, not just their own.",
    )

    # Sales-page copy (Phase 8) — not in the spec's original §4 model
    # list, added because the public sales page it asks for needs
    # somewhere to hold this content, and Django admin is the only
    # authoring tool. All blank-safe: the template falls back to
    # subtitle/description when these are empty, so an un-marketed
    # course still renders sensibly.
    sales_headline = models.CharField(max_length=255, blank=True)
    sales_subheadline = models.CharField(max_length=255, blank=True)
    target_audience = models.TextField(blank=True, help_text="Who this course is for — one point per line.")
    not_for = models.TextField(blank=True, help_text="Who this course is NOT for — one point per line.")
    instructor_bio = models.TextField(blank=True)
    meta_description = models.CharField(
        max_length=160, blank=True, help_text="SEO meta description. Falls back to subtitle if blank."
    )

    # --- Phase 10: instructor marketplace ---------------------------
    class ReviewStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        IN_REVIEW = "IN_REVIEW", "In review"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes requested"
        APPROVED = "APPROVED", "Approved"
        DELISTED = "DELISTED", "Delisted"

    # null = a first-party Xpress Digital course, per spec.
    instructor = models.ForeignKey(
        "instructors.Instructor", on_delete=models.PROTECT, null=True, blank=True, related_name="courses"
    )
    # Self-referential — e.g. "Advanced" requiring "Intermediate"
    # completed first. PROTECT: a course other courses depend on
    # shouldn't be deletable out from under them without deliberately
    # clearing the dependency first. Enforced at checkout() (blocks
    # enrollment/payment) and surfaced on the course detail page —
    # not a DB constraint, since "has this user COMPLETED that
    # course" is an Enrollment-table question, not expressible as a
    # CheckConstraint on Course alone.
    prerequisite = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="unlocks",
        help_text="Learner must have COMPLETED this course before they can enroll in this one. Leave blank for no prerequisite.",
    )
    unlock_delay_days = models.PositiveIntegerField(
        default=0,
        help_text="Only relevant when prerequisite is set AND is_compulsory_staff_training is True: how many "
                   "days after completing the prerequisite before this course auto-enrolls (see "
                   "apps.engagement.tasks.advance_compulsory_training_chains_task). Course-to-course pacing "
                   "for a compulsory training sequence — separate from Module.drip_days, which paces content "
                   "within a single course.",
    )
    vertical = models.ForeignKey(
        "instructors.Vertical", on_delete=models.PROTECT, null=True, blank=True, related_name="courses"
    )
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    domain_reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Snapshot of who actually reviewed this course — may differ from the Vertical's current reviewer over time.",
    )
    review_notes = models.TextField(blank=True, help_text="Internal — never shown on the public sales page.")
    delisted_reason = models.CharField(max_length=255, blank=True)
    last_content_review_at = models.DateTimeField(null=True, blank=True)
    next_content_review_due = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["programme", "title"]
        constraints = [
            # The spec's literal "hard constraint" — enforced at the
            # DATABASE level, not just in clean(), so it holds even
            # against a raw .update() or a future API route that
            # forgets to call full_clean(). See
            # apps.catalog.tests.TestPublicationGate for the bypass
            # attempt this is proven against.
            models.CheckConstraint(
                check=models.Q(is_published=False) | models.Q(review_status="APPROVED"),
                name="course_publish_requires_approved_review_status",
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.access_type == self.AccessType.TIMED and not self.access_months:
            raise ValidationError(
                {"access_months": "Required when access type is TIMED."}
            )

        if self.instructor_id and not self.instructor.is_eligible_for_courses:
            raise ValidationError({
                "instructor": "This instructor isn't VERIFIED with a signed agreement yet — "
                               "cannot attach them to a course.",
            })

        if self.review_status == self.ReviewStatus.APPROVED:
            # §4.1: "review_status cannot move to APPROVED if the
            # Vertical has no domain_reviewer." Enforced here via
            # clean() (admin/forms always call this); a raw .update()
            # bypassing clean() is a narrower gap than the
            # is_published one above, which the DB constraint closes
            # unconditionally — documented as a known scoping decision
            # in README rather than retrofitting a save()-override
            # onto a model that's been stable since Phase 2.
            if not self.vertical_id:
                raise ValidationError({"review_status": "Cannot approve a course with no Vertical set."})
            if not self.vertical.domain_reviewer_id:
                raise ValidationError({
                    "review_status": f'The Vertical "{self.vertical}" has no domain reviewer — cannot approve.',
                })

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        # Detect draft→published on THIS save, before super().save()
        # overwrites what's in the DB — a raw .update() bypasses this
        # (same narrower gap as clean(), documented above), but every
        # real publish path (admin, management commands) goes through
        # a normal .save().
        just_published = False
        if self.is_published and self.pk:
            was_published = Course.objects.filter(pk=self.pk).values_list("is_published", flat=True).first()
            just_published = was_published is False
        elif self.is_published and not self.pk:
            just_published = True  # created directly as published — rare, but a real publish event too

        if just_published and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

        if just_published:
            from .webhooks import notify_course_published
            notify_course_published(self)


class Module(TimeStampedModel):
    class UnlockRule(models.TextChoices):
        IMMEDIATE = "IMMEDIATE", "Immediate"
        SEQUENTIAL = "SEQUENTIAL", "Sequential (previous module completed)"
        DRIP_DAYS = "DRIP_DAYS", "Drip — days after enrollment"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)

    unlock_rule = models.CharField(
        max_length=20, choices=UnlockRule.choices, default=UnlockRule.SEQUENTIAL
    )
    drip_days = models.PositiveIntegerField(
        default=0, help_text="Days after enrollment. Used only when unlock_rule is DRIP_DAYS."
    )
    requires_quiz_pass_to_advance = models.BooleanField(default=False)

    class Meta:
        ordering = ["course", "order"]

    def __str__(self):
        return f"{self.course.title} — Module {self.order}: {self.title}"


class Lesson(TimeStampedModel):
    class Type(models.TextChoices):
        VIDEO = "VIDEO", "Video"
        TEXT = "TEXT", "Text"
        PDF = "PDF", "PDF"
        DOWNLOAD = "DOWNLOAD", "Download"
        LIVE = "LIVE", "Live session"

    class VideoProvider(models.TextChoices):
        BUNNY = "BUNNY", "Bunny Stream"
        CLOUDINARY = "CLOUDINARY", "Cloudinary"

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    order = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    # Not in the original §4 model list — added because §6's learner
    # URL scheme (/learn/<course_slug>/<lesson_slug>/) needs one and
    # the spec doesn't otherwise say how a lesson is addressed in a
    # URL. Global uniqueness (not per-module) because it's simplest
    # and the only author today is Sam; save() disambiguates a title
    # collision by suffixing rather than erroring.
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.VIDEO)

    video_provider = models.CharField(
        max_length=20, choices=VideoProvider.choices, blank=True
    )
    video_id = models.CharField(max_length=255, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    body = CKEditor5Field(
        blank=True,
        config_name="default",
        help_text="Used as the lesson content for TEXT lessons, and as notes otherwise.",
    )
    attachment = models.FileField(upload_to="lessons/attachments/", blank=True, null=True)

    is_preview = models.BooleanField(
        default=False, help_text="Viewable without enrollment, for the sales page."
    )
    transcript = models.TextField(blank=True)

    class Meta:
        ordering = ["module", "order"]

    def __str__(self):
        return f"{self.module.title} — {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 2
            while Lesson.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Resource(TimeStampedModel):
    """A downloadable one-pager attached to a Course or a Module —
    exactly one of the two must be set."""

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="resources", null=True, blank=True
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, related_name="resources", null=True, blank=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to="resources/")
    download_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def clean(self):
        if bool(self.course_id) == bool(self.module_id):
            raise ValidationError("Set exactly one of course or module, not both or neither.")


class CourseFAQ(models.Model):
    """Sales-page FAQ — Phase 8. Admin-managed, ordered per course."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="faqs")
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["course", "order"]

    def __str__(self):
        return self.question
