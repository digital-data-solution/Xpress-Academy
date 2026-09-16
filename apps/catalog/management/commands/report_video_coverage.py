from django.core.management.base import BaseCommand

from apps.catalog.models import Course


class Command(BaseCommand):
    help = (
        "One-off: reports, per course, how many lessons actually have a playable "
        "video attached (generated_video_url or generated_video) vs total lessons. "
        "Run this against production (Render Shell) to see real coverage, not just "
        "what's been rendered locally."
    )

    def handle(self, *args, **options):
        rows = []
        for c in Course.objects.all().order_by("title"):
            lessons = list(c.modules.values_list(
                "lessons__id", "lessons__generated_video_url", "lessons__generated_video"
            ))
            lessons = [l for l in lessons if l[0] is not None]
            total = len(lessons)
            if total == 0:
                continue
            has_video = sum(1 for _, url, f in lessons if url or f)
            rows.append((c.is_published, has_video, total, c.title, c.slug))

        rows.sort(key=lambda r: (r[1] / r[2], r[3]))

        self.stdout.write(f"{'PUB':<5}{'COVERAGE':<12}{'TITLE':<70}SLUG")
        for is_pub, has_video, total, title, slug in rows:
            pub = "yes" if is_pub else "no"
            coverage = f"{has_video}/{total}"
            self.stdout.write(f"{pub:<5}{coverage:<12}{title[:68]:<70}{slug}")

        zero = [r for r in rows if r[1] == 0]
        partial = [r for r in rows if 0 < r[1] < r[2]]
        full = [r for r in rows if r[1] == r[2]]
        self.stdout.write("")
        self.stdout.write(
            f"Summary: {len(full)} fully covered, {len(partial)} partial, "
            f"{len(zero)} with zero video, out of {len(rows)} courses with lessons."
        )
        pub_zero = [r for r in zero if r[0]]
        if pub_zero:
            self.stdout.write(
                f"Published courses with ZERO video ({len(pub_zero)}): "
                + ", ".join(r[4] for r in pub_zero)
            )
