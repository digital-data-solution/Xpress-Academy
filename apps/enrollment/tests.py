"""Coverage required by build spec §11 before Hard Stop 1:
"Module unlock logic — every rule type, every edge" and
"Access control — unenrolled user cannot obtain a video URL by any route."
"""

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Course, Lesson, Module, Programme
from apps.organizations.models import Organization

from .models import Enrollment, LessonProgress
from .services import (
    get_next_lesson,
    get_progress_percent,
    is_enrollment_currently_active,
    is_module_unlocked,
    mark_lesson_complete,
)


@pytest.fixture
def org():
    return Organization.objects.create(name="Test Org", from_email="test@example.com")


@pytest.fixture
def course(org):
    programme = Programme.objects.create(organization=org, title="Test Programme", audience="BREEDER")
    return Course.objects.create(
        organization=org, programme=programme, title="Test Course", audience="BREEDER",
    )


@pytest.fixture
def user():
    return User.objects.create_user(email="learner@example.com", password="testpass123")


def make_module(course, order, unlock_rule=Module.UnlockRule.SEQUENTIAL, drip_days=0):
    module = Module.objects.create(
        course=course, order=order, title=f"Module {order}",
        unlock_rule=unlock_rule, drip_days=drip_days,
    )
    Lesson.objects.create(module=module, order=1, title=f"Lesson {order}.1", type=Lesson.Type.TEXT)
    return module


@pytest.mark.django_db
class TestModuleUnlock:
    def test_immediate_always_unlocked(self, course, user):
        module = make_module(course, 1, unlock_rule=Module.UnlockRule.IMMEDIATE)
        enrollment = Enrollment.objects.create(user=user, course=course)
        assert is_module_unlocked(enrollment, module) is True

    def test_sequential_first_module_always_unlocked(self, course, user):
        module = make_module(course, 1, unlock_rule=Module.UnlockRule.SEQUENTIAL)
        enrollment = Enrollment.objects.create(user=user, course=course)
        assert is_module_unlocked(enrollment, module) is True

    def test_sequential_second_module_locked_until_first_complete(self, course, user):
        m1 = make_module(course, 1)
        m2 = make_module(course, 2)
        enrollment = Enrollment.objects.create(user=user, course=course)

        assert is_module_unlocked(enrollment, m2) is False

        mark_lesson_complete(enrollment, m1.lessons.first())
        assert is_module_unlocked(enrollment, m2) is True

    def test_sequential_requires_ALL_lessons_in_previous_module_complete(self, course, user):
        m1 = make_module(course, 1)
        Lesson.objects.create(module=m1, order=2, title="Second lesson in m1", type=Lesson.Type.TEXT)
        m2 = make_module(course, 2)
        enrollment = Enrollment.objects.create(user=user, course=course)

        mark_lesson_complete(enrollment, m1.lessons.order_by("order").first())
        assert is_module_unlocked(enrollment, m2) is False, "one of two lessons done should still lock module 2"

        mark_lesson_complete(enrollment, m1.lessons.order_by("order").last())
        assert is_module_unlocked(enrollment, m2) is True

    def test_drip_days_locked_before_window(self, course, user):
        module = make_module(course, 1, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        enrollment = Enrollment.objects.create(user=user, course=course)
        assert is_module_unlocked(enrollment, module) is False

    def test_drip_days_unlocked_after_window(self, course, user):
        module = make_module(course, 1, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.started_at = timezone.now() - timezone.timedelta(days=8)
        enrollment.save(update_fields=["started_at"])
        assert is_module_unlocked(enrollment, module) is True

    def test_drip_days_boundary_exact_day(self, course, user):
        module = make_module(course, 1, unlock_rule=Module.UnlockRule.DRIP_DAYS, drip_days=7)
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.started_at = timezone.now() - timezone.timedelta(days=7, seconds=1)
        enrollment.save(update_fields=["started_at"])
        assert is_module_unlocked(enrollment, module) is True


@pytest.mark.django_db
class TestEnrollmentActive:
    def test_active_no_expiry_is_active(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        assert is_enrollment_currently_active(enrollment) is True

    def test_expired_status_is_not_active(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course, status=Enrollment.Status.EXPIRED)
        assert is_enrollment_currently_active(enrollment) is False

    def test_active_status_but_past_expires_at_is_not_active(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course)
        enrollment.expires_at = timezone.now() - timezone.timedelta(days=1)
        enrollment.save(update_fields=["expires_at"])
        assert is_enrollment_currently_active(enrollment) is False, (
            "status field alone lags reality until the Phase 7 expire_enrollments task runs"
        )

    def test_revoked_is_not_active(self, course, user):
        enrollment = Enrollment.objects.create(user=user, course=course, status=Enrollment.Status.REVOKED)
        assert is_enrollment_currently_active(enrollment) is False


@pytest.mark.django_db
class TestProgressAndCompletion:
    def test_progress_percent(self, course, user):
        m1, m2 = make_module(course, 1), make_module(course, 2)
        enrollment = Enrollment.objects.create(user=user, course=course)
        assert get_progress_percent(enrollment) == 0

        mark_lesson_complete(enrollment, m1.lessons.first())
        assert get_progress_percent(enrollment) == 50

    def test_mark_complete_idempotent(self, course, user):
        m1 = make_module(course, 1)
        enrollment = Enrollment.objects.create(user=user, course=course)
        lesson = m1.lessons.first()

        mark_lesson_complete(enrollment, lesson)
        mark_lesson_complete(enrollment, lesson)
        assert LessonProgress.objects.filter(enrollment=enrollment, lesson=lesson).count() == 1

    def test_completing_all_lessons_completes_enrollment_when_no_final_assessment(self, course, user):
        m1 = make_module(course, 1)
        enrollment = Enrollment.objects.create(user=user, course=course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        enrollment.refresh_from_db()
        assert enrollment.status == Enrollment.Status.COMPLETED
        assert enrollment.completed_at is not None

    def test_final_assessment_required_blocks_auto_complete(self, course, user):
        course.requires_final_assessment = True
        course.save(update_fields=["requires_final_assessment"])
        m1 = make_module(course, 1)
        enrollment = Enrollment.objects.create(user=user, course=course)
        mark_lesson_complete(enrollment, m1.lessons.first())
        enrollment.refresh_from_db()
        assert enrollment.status == Enrollment.Status.ACTIVE, (
            "must not auto-complete — Phase 4/5 will extend mark_lesson_complete "
            "to also require a passing final Attempt"
        )

    def test_get_next_lesson_skips_completed_and_stops_at_lock(self, course, user):
        m1, m2 = make_module(course, 1), make_module(course, 2)
        enrollment = Enrollment.objects.create(user=user, course=course)
        assert get_next_lesson(enrollment).id == m1.lessons.first().id

        mark_lesson_complete(enrollment, m1.lessons.first())
        enrollment.refresh_from_db()
        assert get_next_lesson(enrollment).id == m2.lessons.first().id


@pytest.mark.django_db
class TestAccessControl:
    """No path where an unenrolled, non-preview visitor obtains lesson content."""

    def test_anonymous_visitor_redirected_to_login(self, course, user):
        m1 = make_module(course, 1)
        client = Client()
        resp = client.get(f"/learn/{course.slug}/{m1.lessons.first().slug}/")
        assert resp.status_code == 302
        assert "/account/login/" in resp["Location"]

    def test_logged_in_but_unenrolled_gets_403(self, course, user):
        m1 = make_module(course, 1)
        client = Client()
        client.force_login(user)
        resp = client.get(f"/learn/{course.slug}/{m1.lessons.first().slug}/")
        assert resp.status_code == 403

    def test_preview_lesson_viewable_without_enrollment(self, course, user):
        m1 = make_module(course, 1)
        lesson = m1.lessons.first()
        lesson.is_preview = True
        lesson.save(update_fields=["is_preview"])
        client = Client()
        resp = client.get(f"/learn/{course.slug}/{lesson.slug}/")
        assert resp.status_code == 200

    def test_preview_lesson_does_not_shadow_a_real_enrollment(self, course, user):
        """Regression test: an enrolled user's real enrollment/progress
        context must be used even on a lesson flagged is_preview —
        the preview bypass is a fallback for visitors with no
        enrollment, not an override for someone who has one."""
        m1 = make_module(course, 1)
        lesson = m1.lessons.first()
        lesson.is_preview = True
        lesson.save(update_fields=["is_preview"])

        enrollment = Enrollment.objects.create(user=user, course=course)
        client = Client()
        client.force_login(user)

        resp = client.post(f"/learn/{course.slug}/{lesson.slug}/complete/")
        assert resp.status_code == 302
        assert LessonProgress.objects.filter(enrollment=enrollment, lesson=lesson, completed_at__isnull=False).exists()

    def test_locked_module_lesson_redirects_to_curriculum_not_shown(self, course, user):
        m1, m2 = make_module(course, 1), make_module(course, 2)
        Enrollment.objects.create(user=user, course=course)
        client = Client()
        client.force_login(user)
        resp = client.get(f"/learn/{course.slug}/{m2.lessons.first().slug}/")
        assert resp.status_code == 302
        assert resp["Location"].endswith(f"/learn/{course.slug}/")

    def test_revoked_enrollment_loses_access(self, course, user):
        m1 = make_module(course, 1)
        Enrollment.objects.create(user=user, course=course, status=Enrollment.Status.REVOKED)
        client = Client()
        client.force_login(user)
        resp = client.get(f"/learn/{course.slug}/{m1.lessons.first().slug}/")
        assert resp.status_code == 403

    def test_dashboard_requires_login(self):
        client = Client()
        resp = client.get("/dashboard/")
        assert resp.status_code == 302
        assert "/account/login/" in resp["Location"]
