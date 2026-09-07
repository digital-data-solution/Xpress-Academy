"""Generates VideoScene rows for the lecture-video pipeline (../../../../video/)
automatically from a Lesson's real .body HTML and its Course/Module
context — no hand-written narration, unlike
apps.catalog.management.commands.author_rabies_course_scenes. Built to
run across the whole catalog (231 published lessons), where hand-writing
each script the way the rabies course was written isn't a realistic
amount of authoring time.

Grounded, not fabricated: every content scene's narration comes directly
from the lesson's own <h2>/<p>/<li> body text (parsed below), not
invented facts. The one thing the hand-written rabies script had that
this deliberately omits: evidenceCard scenes, which need a REAL external
citation (e.g. a WHO fact sheet) — auto-detecting "this sentence needs a
citation" isn't reliable, so this generator never fabricates one. Every
content scene here is bulletReveal instead.

Same instructional shape as the hand-written course: welcome/framing ->
what you'll learn -> one scene per body section -> recap -> next steps
(or course completion + real final-assessment mention, on a course's
last module).
"""
import re
from html import unescape

from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Course, Lesson, VideoScene

TAG_RE = re.compile(r"<[^>]+>")
H2_SPLIT_RE = re.compile(r"<h2>(.*?)</h2>", re.DOTALL)
P_RE = re.compile(r"<p>(.*?)</p>", re.DOTALL)
LI_RE = re.compile(r"<li>(.*?)</li>", re.DOTALL)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
MODULE_PREFIX_RE = re.compile(r"^Module\s+\d+:\s*", re.IGNORECASE)


def spoken_title(lesson_title):
    """'Module 2: Clinical Findings' -> 'Clinical Findings' for narration
    that already says 'this module' / 'the next module' — the full
    'Module N: ...' form reads fine as an on-screen heading but doubles
    up awkwardly when spoken inside a sentence that already establishes
    it's a module. Full lesson.title is still used verbatim in payload
    headings, just not repeated inline in narration."""
    return MODULE_PREFIX_RE.sub("", lesson_title).strip() or lesson_title


def strip_tags(fragment):
    return unescape(TAG_RE.sub("", fragment)).strip()


def extract_sections(body):
    """[{heading, paragraphs: [str], bullets: [str]}, ...] from Lesson.body.
    Falls back to one untitled section (the whole stripped body) if there
    are no <h2> headings at all — rare, but real (a couple of lessons
    are a single paragraph)."""
    if not body or not body.strip():
        return []

    parts = H2_SPLIT_RE.split(body)
    if len(parts) == 1:
        text = strip_tags(body)
        return [{"heading": "", "paragraphs": [text], "bullets": []}] if text else []

    sections = []
    # parts alternates: [pre-text, heading, content, heading, content, ...]
    for i in range(1, len(parts), 2):
        heading = strip_tags(parts[i])
        content_html = parts[i + 1] if i + 1 < len(parts) else ""
        paragraphs = [strip_tags(p) for p in P_RE.findall(content_html)]
        paragraphs = [p for p in paragraphs if p]
        bullets = [strip_tags(li) for li in LI_RE.findall(content_html)]
        bullets = [b for b in bullets if b]
        sections.append({"heading": heading, "paragraphs": paragraphs, "bullets": bullets})
    return sections


def sentences(text):
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


# Phrasing rotation — without this, every non-first module in all 154
# lessons opens with the byte-identical "Welcome back. This module
# covers X." (same for the recap/outro lines). Picked deterministically
# by module position (not random) so re-running this command on the
# same lesson produces the same script — idempotent, not idempotent-
# except-for-wording.
WELCOME_BACK_VARIANTS = [
    "Welcome back. This module covers {title}.",
    "Let's continue. This module is about {title}.",
    "Picking up where we left off — this module covers {title}.",
    "Next up is {title}.",
]
LEARN_INTRO_VARIANTS = [
    "In this module, we'll cover: {list}.",
    "Here's what this module walks through: {list}.",
    "This module covers: {list}.",
]
RECAP_INTRO_VARIANTS = [
    "Before we move on, let's recap what this module covered: {list}.",
    "Quick recap before we continue: {list}.",
    "To sum up this module: {list}.",
]
NEXT_MODULE_VARIANTS = [
    "That covers {title}. In the next module, we'll look at {next_title}. See you there.",
    "That's {title} covered. Next up: {next_title}.",
    "With {title} covered, let's move on to {next_title}.",
]


def build_scenes(lesson):
    course = lesson.module.course
    module = lesson.module
    modules = list(course.modules.order_by("order"))
    position = next((i for i, m in enumerate(modules) if m.pk == module.pk), 0)
    is_first = position == 0
    is_last = position == len(modules) - 1

    sections = extract_sections(lesson.body)
    if not sections:
        raise ValueError(f"Lesson {lesson.pk} has no usable body content to build a script from.")

    scenes = []
    order = 1

    # --- Welcome / framing ------------------------------------------------
    if is_first:
        subtitle = course.subtitle or strip_tags(course.description)[:200]
        welcome = f"Welcome to {course.title}."
        if subtitle:
            welcome += f" {subtitle}"
        welcome += f" This is module {position + 1} of {len(modules)}: {spoken_title(lesson.title)}."
    else:
        variant = WELCOME_BACK_VARIANTS[position % len(WELCOME_BACK_VARIANTS)]
        welcome = variant.format(title=spoken_title(lesson.title))
    scenes.append(dict(
        order=order, scene_type=VideoScene.SceneType.TITLE_CARD,
        narration=welcome,
        payload={"heading": lesson.title, "subheading": course.title},
    ))
    order += 1

    # --- What you'll learn -------------------------------------------------
    headings = [s["heading"] for s in sections if s["heading"]] or [lesson.title]
    learn_variant = LEARN_INTRO_VARIANTS[position % len(LEARN_INTRO_VARIANTS)]
    scenes.append(dict(
        order=order, scene_type=VideoScene.SceneType.BULLET_REVEAL,
        narration=learn_variant.format(list="; ".join(headings)),
        payload={"heading": "What you'll learn in this module", "bullets": headings},
    ))
    order += 1

    # --- One scene per body section -----------------------------------------
    for section in sections:
        narration = " ".join(section["paragraphs"]).strip()
        if not narration and section["bullets"]:
            narration = " ".join(section["bullets"])
        if not narration:
            continue
        bullets = section["bullets"] or [s for p in section["paragraphs"] for s in sentences(p)][:5]
        scenes.append(dict(
            order=order, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration=narration,
            payload={"heading": section["heading"], "bullets": bullets},
        ))
        order += 1

    # --- Recap ---------------------------------------------------------------
    recap_variant = RECAP_INTRO_VARIANTS[position % len(RECAP_INTRO_VARIANTS)]
    scenes.append(dict(
        order=order, scene_type=VideoScene.SceneType.BULLET_REVEAL,
        narration=recap_variant.format(list="; ".join(headings)),
        payload={"heading": "Key takeaways", "bullets": headings},
    ))
    order += 1

    # --- Outro -----------------------------------------------------------------
    if is_last:
        if course.requires_final_assessment:
            cta = f"Take the final assessment ({course.pass_mark}% to pass)"
            narration = (
                f"That completes {course.title}. When you're ready, take the final "
                f"assessment — you'll need {course.pass_mark} percent to pass — and your "
                f"certificate is waiting on the other side. Well done."
            )
        else:
            cta = "Course complete"
            narration = f"That completes {course.title}. Well done."
    else:
        next_module = modules[position + 1]
        next_lesson = next_module.lessons.order_by("order").first()
        next_title = next_lesson.title if next_lesson else next_module.title
        cta = f"Next: {next_title}"
        next_variant = NEXT_MODULE_VARIANTS[position % len(NEXT_MODULE_VARIANTS)]
        narration = next_variant.format(title=spoken_title(lesson.title), next_title=spoken_title(next_title))
    scenes.append(dict(
        order=order, scene_type=VideoScene.SceneType.OUTRO_CARD,
        narration=narration,
        payload={"ctaText": cta},
    ))

    return scenes


class Command(BaseCommand):
    help = (
        "Auto-generates VideoScene rows from each targeted Lesson's real .body content. "
        "Scope with --course=<pk> (repeatable) or --all-published. Replaces existing scenes "
        "for a lesson (delete-then-recreate), same as author_rabies_course_scenes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--course", type=int, action="append", default=[], help="Course pk to author. Repeatable.")
        parser.add_argument("--all-published", action="store_true", help="Author every published course's lessons.")
        parser.add_argument("--dry-run", action="store_true", help="Print what would be created, write nothing.")

    def handle(self, *args, **options):
        if options["all_published"]:
            courses = Course.objects.filter(is_published=True)
        elif options["course"]:
            courses = Course.objects.filter(pk__in=options["course"])
            missing = set(options["course"]) - set(courses.values_list("pk", flat=True))
            if missing:
                raise CommandError(f"No Course with pk in {sorted(missing)}.")
        else:
            raise CommandError("Pass --course=<pk> (repeatable) or --all-published.")

        lessons = Lesson.objects.filter(module__course__in=courses).select_related("module__course").order_by(
            "module__course__pk", "module__order"
        )
        if not lessons.exists():
            self.stdout.write(self.style.WARNING("No lessons matched."))
            return

        total_scenes = 0
        skipped = []
        for lesson in lessons:
            try:
                scenes = build_scenes(lesson)
            except ValueError as e:
                skipped.append((lesson, str(e)))
                continue

            if options["dry_run"]:
                self.stdout.write(f"\n--- Lesson {lesson.pk}: {lesson.title} ({len(scenes)} scenes) ---")
                for s in scenes:
                    heading = s["payload"].get("heading", "")
                    self.stdout.write(f"  [{s['scene_type']}] {heading!r} — {s['narration'][:80]}...")
                continue

            existing = lesson.video_scenes.count()
            if existing:
                lesson.video_scenes.all().delete()
            for data in scenes:
                VideoScene.objects.create(lesson=lesson, **data)
            total_scenes += len(scenes)
            self.stdout.write(f"Lesson {lesson.pk} ({lesson.title}): {len(scenes)} scenes" + (f" (replaced {existing})" if existing else ""))

        if skipped:
            self.stdout.write(self.style.WARNING(f"\nSkipped {len(skipped)} lesson(s) with no usable body content:"))
            for lesson, reason in skipped:
                self.stdout.write(f"  {lesson.pk} ({lesson.title}): {reason}")

        if not options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(
                f"\nDone — {total_scenes} scene(s) across {lessons.count() - len(skipped)} lesson(s)."
            ))
