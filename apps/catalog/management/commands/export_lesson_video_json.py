import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Lesson


class Command(BaseCommand):
    help = (
        "Emits one lesson's video script as JSON, in the shape the Remotion "
        "composition's input props expect (see video/src/types.ts): title, "
        "track, instructor, ordered scenes. Reads the video script from "
        "Lesson.video_scenes (apps.catalog.models.VideoScene) — NOT parsed "
        "out of Lesson.body. A lesson with no scenes authored yet has "
        "nothing to export; this refuses rather than emit an empty or "
        "guessed scene list, since a video 'rendered' from a fabricated "
        "script fails in a way that looks like success. Author the script "
        "for a lesson via the Video scenes inline on its Lesson admin page "
        "first."
    )

    def add_arguments(self, parser):
        parser.add_argument("lesson_id", type=int, help="Lesson.pk to export.")
        parser.add_argument(
            "--out", help="Write JSON to this path instead of stdout."
        )

    def handle(self, *args, **options):
        lesson_id = options["lesson_id"]
        try:
            lesson = Lesson.objects.select_related("module__course__programme", "module__course__instructor").get(
                pk=lesson_id
            )
        except Lesson.DoesNotExist:
            raise CommandError(f"No Lesson with pk={lesson_id}.")

        scenes = list(lesson.video_scenes.all())  # already ordered by Meta.ordering
        if not scenes:
            raise CommandError(
                f'Lesson {lesson_id} ("{lesson.title}") has no VideoScene rows — nothing to '
                "export. Write its video script via the Video scenes inline on the Lesson "
                "admin page, then re-run this command."
            )

        course = lesson.module.course
        instructor_name = course.instructor.display_name if course.instructor_id else ""

        data = {
            "title": lesson.title,
            "track": course.programme.audience,
            "instructor": instructor_name,
            "courseSlug": course.slug,
            "lessonSlug": lesson.slug,
            "scenes": [self._scene_dict(scene) for scene in scenes],
        }

        output = json.dumps(data, indent=2, ensure_ascii=False)

        if options.get("out"):
            with open(options["out"], "w", encoding="utf-8") as f:
                f.write(output)
            self.stdout.write(self.style.SUCCESS(f"Wrote {len(scenes)} scene(s) to {options['out']}"))
        else:
            self.stdout.write(output)

    def _scene_dict(self, scene):
        image_url = None
        if scene.image:
            url = scene.image.url
            # Local FileSystemStorage returns a path like /media/...; the S3
            # backend used in prod (see config/settings/prod.py) already
            # returns an absolute URL. Only join what isn't absolute yet —
            # SITE_URL here is whatever this process actually has (the
            # local dev server when run locally, the real domain in prod),
            # unlike the outbound-webhook case in webhooks.py there's no
            # second external system depending on it being reachable from
            # somewhere else: the video/ pipeline runs on this same machine
            # against this same Django instance.
            image_url = url if url.startswith("http") else f"{settings.SITE_URL.rstrip('/')}/{url.lstrip('/')}"

        return {
            "type": scene.scene_type,
            "narration": scene.narration,
            "image": image_url,
            "payload": scene.payload,
        }
