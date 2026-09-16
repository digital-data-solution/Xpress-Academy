from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.catalog.management.commands.export_lesson_video_json import Command as ExportCommand
from apps.catalog.models import Course, Lesson

SAMPLES_DIR = Path(settings.BASE_DIR) / "video" / "samples"


class Command(BaseCommand):
    help = (
        "Batch version of export_lesson_video_json: for the given courses, exports one JSON "
        "props file per lesson that has no video yet (no generated_video_url/generated_video) "
        "AND already has authored VideoScene rows (run auto_author_video_scenes first for any "
        "that don't). Writes to video/scripts/samples/<lesson-slug>.json, ready for "
        "render-lesson.mjs. Run against prod the same way as any other prod-touching command "
        "here: DJANGO_SETTINGS_MODULE=config.settings.prod + DATABASE_URL, in your own terminal."
    )

    def add_arguments(self, parser):
        parser.add_argument("--course", action="append", default=[], help="Course slug. Repeatable.")
        parser.add_argument("--all-published", action="store_true", help="Every published course.")

    def handle(self, *args, **options):
        if options["all_published"]:
            courses = Course.objects.filter(is_published=True)
        elif options["course"]:
            courses = Course.objects.filter(slug__in=options["course"])
            found_slugs = set(courses.values_list("slug", flat=True))
            for slug in options["course"]:
                if slug not in found_slugs:
                    self.stdout.write(self.style.WARNING(f"No course with slug={slug!r} — skipping."))
        else:
            self.stdout.write(self.style.ERROR("Pass --course <slug> (repeatable) or --all-published."))
            return

        SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

        lessons = (
            Lesson.objects.filter(module__course__in=courses)
            .exclude(generated_video_url__gt="")
            .exclude(generated_video__gt="")
            .select_related("module__course")
            .order_by("module__course__slug", "module__order", "order")
        )

        exported, no_scenes = 0, []
        exporter = ExportCommand()
        for lesson in lessons:
            if not lesson.video_scenes.exists():
                no_scenes.append(f"{lesson.pk} ({lesson.module.course.slug} / {lesson.slug})")
                continue
            out_path = SAMPLES_DIR / f"{lesson.slug}.json"
            exporter.handle(lesson_id=lesson.pk, out=str(out_path))
            exported += 1

        self.stdout.write(self.style.SUCCESS(f"\nExported {exported} lesson(s) to {SAMPLES_DIR}"))
        if no_scenes:
            self.stdout.write(self.style.WARNING(
                f"\n{len(no_scenes)} lesson(s) skipped — no VideoScene rows yet. Run "
                f"'manage.py auto_author_video_scenes --all-published' first, then re-run this:"
            ))
            for entry in no_scenes:
                self.stdout.write(f"  {entry}")
