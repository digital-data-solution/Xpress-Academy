from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.catalog.models import Lesson

VIDEO_OUT_DIR = Path(settings.BASE_DIR) / "video" / "out"


class Command(BaseCommand):
    help = "One-off: lists free/paid courses with at least one rendered lesson, by real course URL."

    def handle(self, *args, **options):
        slugs = [p.parent.name for p in VIDEO_OUT_DIR.glob("*/*/LessonVideo.mp4")]

        by_course = {}
        for slug in slugs:
            lesson = Lesson.objects.filter(slug=slug).select_related("module__course").first()
            if not lesson:
                continue
            c = lesson.module.course
            by_course.setdefault(c, []).append(lesson)

        free, paid = [], []
        for c, lessons in by_course.items():
            total = c.modules.count()
            entry = (c.title, c.slug, c.price_ngn, len(set(lessons)), total)
            (free if c.pricing_model == "FREE" else paid).append(entry)

        self.stdout.write("=== FREE ===")
        for title, slug, price, done, total in sorted(free):
            self.stdout.write(f"{title} | /courses/{slug}/ | {done}/{total} rendered")

        self.stdout.write("")
        self.stdout.write("=== PAID ===")
        for title, slug, price, done, total in sorted(paid):
            self.stdout.write(f"{title} (N{price}) | /courses/{slug}/ | {done}/{total} rendered")
