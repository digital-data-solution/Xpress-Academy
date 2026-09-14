"""One-off command to publish the two PSR Chapters 1-2 courses created by
seed_psr_course.py and create_exam_prep_course. Replicates exactly what
CourseAdmin.publish_selected_courses does (approve + is_published=True,
saved individually so the publish webhook still fires) for just these two
slugs, as a workaround for a PowerShell pipe/BOM issue when trying to run
the equivalent as a one-off `manage.py shell` script."""
from django.core.management.base import BaseCommand

from apps.catalog.models import Course

SLUGS = ["public-service-rules-guide", "civil-service-psr-exam-prep"]


class Command(BaseCommand):
    help = "Publishes the PSR Chapters 1-2 course and exam-prep course."

    def handle(self, *args, **options):
        for slug in SLUGS:
            course = Course.objects.get(slug=slug)
            if course.is_published:
                self.stdout.write(f"{slug}: already published")
                continue
            course.review_status = Course.ReviewStatus.APPROVED
            course.is_published = True
            course.save()
            self.stdout.write(self.style.SUCCESS(f"{slug}: published"))
