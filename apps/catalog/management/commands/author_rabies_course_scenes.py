from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import Lesson, VideoScene

# Content authoring for the lecture-video pipeline (see ../../../../video/),
# covering all four modules of "Canine Rabies: Prevention, Exposure
# Protocol, and the Law" (Course pk=85). Grounded in each lesson's real
# .body text (see apps.catalog.management.commands.seed_canine_rabies_course)
# and the course's real subtitle/description/requires_final_assessment,
# not invented.
#
# Every module follows the same real-instructor shape, not a fact dump:
# welcome + why this module matters -> what you'll be able to do by the
# end -> the content itself -> (evidence, where a real citation backs a
# claim) -> a recap -> what's next. The final module closes the whole
# course instead of pointing to a next module, and mentions the real
# final assessment (course.requires_final_assessment / pass_mark).
#
# Re-running this command REPLACES any existing scenes per lesson
# (delete-then-recreate) — this is content actively being iterated on,
# not a one-time seed.

LESSON_SCENES = {
    301: [  # Module 1: Etiology and Epidemiology
        dict(
            order=1, scene_type=VideoScene.SceneType.TITLE_CARD,
            narration="Welcome to Canine Rabies: Prevention, Exposure Protocol, and the Law. "
                       "I'm glad you're here — this is a four-module continuing education course, "
                       "and this first module covers etiology and epidemiology: what rabies "
                       "actually is, and why it's treated as one of the most serious diseases in "
                       "veterinary practice.",
            payload={"heading": "Module 1: Etiology and Epidemiology", "subheading": "Canine Rabies — Xpress Vet Marketplace"},
        ),
        dict(
            order=2, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="By the end of this module, you'll be able to do four things. Explain what "
                       "causes rabies and how it's classified. Describe how it actually spreads, "
                       "from animal to animal and from animal to human. Explain why dog-mediated "
                       "rabies is treated as a human public health priority, especially here in "
                       "Nigeria. And understand why, for this particular disease, prevention "
                       "matters so much more than treatment.",
            payload={
                "heading": "What you'll learn in this module",
                "bullets": [
                    "What causes rabies, and how it's classified",
                    "How it spreads — animal to animal, and animal to human",
                    "Why dog-mediated rabies is a human public health priority in Nigeria",
                    "Why prevention matters more here than almost anywhere else in practice",
                ],
            },
        ),
        dict(
            order=3, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="Let's start with what causes it. Rabies is caused by rabies virus, a "
                       "lyssavirus, transmitted via bite or saliva contact. It is fatal and "
                       "essentially untreatable once signs appear — and that single fact is "
                       "exactly why prevention and knowing the exposure protocol matter more here "
                       "than almost anything else you'll learn on this platform.",
            payload={
                "heading": "What causes it, and why it matters this much",
                "bullets": [
                    "Caused by rabies virus, a lyssavirus",
                    "Transmitted via bite or saliva contact",
                    "Fatal and essentially untreatable once signs appear",
                    "Prevention and the exposure protocol are what actually save a life",
                ],
            },
        ),
        dict(
            order=4, scene_type=VideoScene.SceneType.EVIDENCE_CARD,
            narration="Now, the epidemiology, and why this is bigger than any one animal. Dogs "
                       "remain a major rabies vector in many parts of the world, including "
                       "Nigeria. The overwhelming majority of human rabies deaths worldwide trace "
                       "back to dog bites — which makes this one of the clearest points in your "
                       "whole career where veterinary practice directly protects human life.",
            payload={
                "claim": "Dog-mediated rabies is a human public health priority — most human "
                         "rabies deaths worldwide trace back to dog bites.",
                "evidenceGrade": "WHO Grade A",
                "citation": "WHO Rabies Fact Sheet",
            },
        ),
        dict(
            order=5, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="Before we move on, let's recap. Rabies is caused by a lyssavirus spread "
                       "through bite or saliva contact. Once signs appear, it's essentially "
                       "untreatable, which is why prevention is everything. And dog-mediated "
                       "spread makes this a human public health issue, not just an animal health "
                       "one — particularly here in Nigeria.",
            payload={
                "heading": "Key takeaways",
                "bullets": [
                    "A lyssavirus, spread by bite or saliva contact",
                    "Essentially untreatable once signs appear — prevention is everything",
                    "Dog-mediated spread makes this a human public health issue too",
                ],
            },
        ),
        dict(
            order=6, scene_type=VideoScene.SceneType.OUTRO_CARD,
            narration="That's etiology and epidemiology covered. In the next module, we'll look "
                       "at clinical findings — including the paralytic form that's easy to miss "
                       "on a first exam. See you there.",
            payload={"ctaText": "Next: Clinical Findings"},
        ),
    ],
    302: [  # Module 2: Clinical Findings
        dict(
            order=1, scene_type=VideoScene.SceneType.TITLE_CARD,
            narration="Welcome back. In Module 1 we covered what rabies is and why it matters. "
                       "In this module, we turn to something every practicing vet needs cold: "
                       "clinical findings — what rabies actually looks like in front of you.",
            payload={"heading": "Module 2: Clinical Findings", "subheading": "Canine Rabies — Xpress Vet Marketplace"},
        ),
        dict(
            order=2, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="By the end of this module, you'll be able to describe why the incubation "
                       "period varies and why bite location changes it. You'll be able to "
                       "distinguish the furious form from the dumb, or paralytic, form. And you'll "
                       "understand why the paralytic form is a real recognition risk in practice — "
                       "one that doesn't match what most people picture when they hear \"rabies.\"",
            payload={
                "heading": "What you'll learn in this module",
                "bullets": [
                    "Why incubation is highly variable, and why bite location matters",
                    "The furious form versus the dumb (paralytic) form",
                    "Why the paralytic form is easy to miss on a first exam",
                ],
            },
        ),
        dict(
            order=3, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="First, incubation. It's highly variable — anywhere from weeks to months — "
                       "and it's shorter with bites to the head or face, simply because the virus "
                       "has a shorter distance to travel to reach the central nervous system.",
            payload={
                "heading": "Incubation — highly variable",
                "bullets": [
                    "Weeks to months — there's no fixed timeline",
                    "Shorter with bites to the head or face",
                    "Because the virus has less distance to travel to the CNS",
                ],
            },
        ),
        dict(
            order=4, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="Rabies presents in two forms, and both are fatal. The furious form is what "
                       "most people picture: aggression, disorientation, hypersalivation, "
                       "difficulty swallowing. The dumb, or paralytic, form looks completely "
                       "different — progressive paralysis and quiet withdrawal. That quiet, "
                       "withdrawn, paralyzed presentation doesn't fit the popular image of rabies "
                       "at all, but it is just as infected, and just as fatal. Take it seriously.",
            payload={
                "heading": "Two forms, both fatal",
                "bullets": [
                    "Furious form: aggression, disorientation, hypersalivation, difficulty swallowing",
                    "Dumb (paralytic) form: progressive paralysis, quiet withdrawal",
                    "The paralytic form is easily mistaken for something else — a real recognition risk",
                ],
            },
        ),
        dict(
            order=5, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="Let's recap. Incubation is variable and shorter with head or face bites. "
                       "There are two forms — furious and dumb — and both are fatal. And the "
                       "paralytic form is the one most likely to be missed, because it doesn't "
                       "look like what people expect rabies to look like.",
            payload={
                "heading": "Key takeaways",
                "bullets": [
                    "Incubation varies — weeks to months, shorter with head/face bites",
                    "Furious and dumb (paralytic) forms — both fatal",
                    "The paralytic form is the easiest one to miss",
                ],
            },
        ),
        dict(
            order=6, scene_type=VideoScene.SceneType.OUTRO_CARD,
            narration="That's clinical findings covered. Next, we'll look at diagnosis — and why "
                       "there's no live-animal test you can run to confirm it. See you there.",
            payload={"ctaText": "Next: Diagnosis"},
        ),
    ],
    303: [  # Module 3: Diagnosis
        dict(
            order=1, scene_type=VideoScene.SceneType.TITLE_CARD,
            narration="Welcome to Module 3. You now know what rabies is and what it looks like "
                       "clinically. This module answers a question every new practitioner asks: "
                       "how do you actually confirm it?",
            payload={"heading": "Module 3: Diagnosis", "subheading": "Canine Rabies — Xpress Vet Marketplace"},
        ),
        dict(
            order=2, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="By the end of this short module, you'll be able to explain why there's no "
                       "reliable live-animal test for rabies, and explain what that limitation "
                       "actually means for how you respond to a bite in real practice.",
            payload={
                "heading": "What you'll learn in this module",
                "bullets": [
                    "Why there's no reliable live-animal test",
                    "What that means for how a bite is actually handled",
                ],
            },
        ),
        dict(
            order=3, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="Here's the core fact of this module: there is no reliable live-animal test "
                       "for rabies. Confirmation is only possible through brain tissue examination, "
                       "after death. That single fact is exactly why the practical response to a "
                       "bite is built on exposure history and a defined observation period — not on "
                       "a diagnostic test you can run in the moment.",
            payload={
                "heading": "Why there's no live-animal test",
                "bullets": [
                    "No reliable test exists on a living animal",
                    "Confirmation only via brain tissue examination, after death",
                    "So real-world response relies on exposure history and observation — not testing",
                ],
            },
        ),
        dict(
            order=4, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="To recap: you cannot test a live animal to confirm rabies. That's not a gap "
                       "in your skills — it's a real limitation of the disease itself. It's exactly "
                       "why the next module, on prevention and the after-a-bite protocol, matters as "
                       "much as it does.",
            payload={
                "heading": "Key takeaway",
                "bullets": [
                    "No live-animal test — confirmation is only possible postmortem",
                    "This is why exposure history and observation carry the real weight",
                ],
            },
        ),
        dict(
            order=5, scene_type=VideoScene.SceneType.OUTRO_CARD,
            narration="That's diagnosis covered. In our final module, we'll cover prevention and "
                       "exactly what happens after a bite — for the dog, and for the person. See you "
                       "there.",
            payload={"ctaText": "Next: Prevention and the After-a-Bite Protocol"},
        ),
    ],
    304: [  # Module 4: Prevention and the After-a-Bite Protocol
        dict(
            order=1, scene_type=VideoScene.SceneType.TITLE_CARD,
            narration="Welcome to the final module. We've covered what rabies is, what it looks "
                       "like, and why it can't be diagnosed in a living animal. Now we cover what "
                       "actually matters most in practice: prevention, and exactly what to do after "
                       "a bite.",
            payload={
                "heading": "Module 4: Prevention and the After-a-Bite Protocol",
                "subheading": "Canine Rabies — Xpress Vet Marketplace",
            },
        ),
        dict(
            order=2, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="By the end of this module, you'll be able to explain why vaccination is "
                       "legally required, not just recommended. You'll be able to walk through what "
                       "actually happens after a bite, for both the dog and the person involved. And "
                       "you'll understand this course's real limits — what it can and can't replace.",
            payload={
                "heading": "What you'll learn in this module",
                "bullets": [
                    "Why vaccination is legally required, not optional",
                    "What actually happens after a bite — for the dog, and for the person",
                    "This course's real limits, and when to defer to a licensed professional",
                ],
            },
        ),
        dict(
            order=3, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="Given everything from the last module — no live test, confirmation only "
                       "after death — prevention isn't just the best strategy. Once exposure risk "
                       "exists, it's essentially the only strategy that matters. Vaccination is "
                       "genuinely effective, and it is legally required in Nigeria and in most "
                       "jurisdictions. It is not discretionary.",
            payload={
                "heading": "Prevention is the entire strategy",
                "bullets": [
                    "Vaccination is genuinely effective",
                    "Legally required in Nigeria and most jurisdictions — not discretionary",
                    "Given diagnosis's limits, prevention is essentially the only strategy that matters",
                ],
            },
        ),
        dict(
            order=4, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="So what actually happens after a bite? A dog bitten by a wild or unknown "
                       "animal needs immediate veterinary assessment. A dog that bites a person is "
                       "typically legally required to be confined and observed for a defined "
                       "period — commonly around ten days in many jurisdictions — rather than "
                       "euthanized immediately for testing. That window exists because a dog "
                       "shedding virus at the time of the bite will reliably show signs within it, "
                       "if it's actually infected. It protects the person, by informing their "
                       "post-exposure treatment decision, and it protects the dog, by avoiding "
                       "unnecessary euthanasia of a genuinely healthy animal.",
            payload={
                "heading": "What actually happens after a bite",
                "bullets": [
                    "Bitten by a wild or unknown animal: immediate veterinary assessment",
                    "Dog that bites a person: confined and observed, commonly around 10 days",
                    "An infected dog will reliably show signs within that window",
                    "Protects the person's treatment decision AND the dog from unnecessary euthanasia",
                ],
            },
        ),
        dict(
            order=5, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="One more thing, and it's important: the person always needs their own "
                       "response too. Anyone bitten by a dog of unknown vaccination status should "
                       "seek medical attention promptly, no matter how healthy the dog looks in that "
                       "moment. Given the variable incubation period we covered earlier, the dog's "
                       "apparent health at the time of the bite tells you nothing reliable about its "
                       "actual infection status.",
            payload={
                "heading": "Human exposure always needs its own response",
                "bullets": [
                    "Seek medical attention promptly — regardless of how healthy the dog looks",
                    "Apparent health at the moment of the bite is not a reliable signal",
                    "This follows directly from the variable incubation period",
                ],
            },
        ),
        dict(
            order=6, scene_type=VideoScene.SceneType.BULLET_REVEAL,
            narration="Before we close, a note on this course's limits. This is continuing "
                       "education content — it is not a substitute for a licensed veterinarian's or "
                       "public health authority's own guidance on a specific exposure incident. Like "
                       "all veterinary continuing-education content on this platform, it has not yet "
                       "been reviewed by a credentialed veterinarian beyond Dr. Omale himself. Treat "
                       "it as a solid starting reference, not the final word.",
            payload={
                "heading": "A note on this course's limits",
                "bullets": [
                    "Continuing education — not a substitute for a licensed professional's guidance",
                    "Not yet reviewed by a credentialed veterinarian beyond Dr. Omale",
                    "A solid starting reference, not the final word on a specific case",
                ],
            },
        ),
        dict(
            order=7, scene_type=VideoScene.SceneType.OUTRO_CARD,
            narration="That completes Canine Rabies: Prevention, Exposure Protocol, and the Law. "
                       "You've covered etiology, clinical findings, diagnosis, and prevention. When "
                       "you're ready, take the final assessment — you'll need seventy percent to "
                       "pass — and your certificate is waiting on the other side. Well done.",
            payload={"ctaText": "Take the final assessment (70% to pass)"},
        ),
    ],
}


class Command(BaseCommand):
    help = "Authors (and re-authors) VideoScene rows for all 4 modules of the Canine Rabies course."

    def handle(self, *args, **options):
        total_created = 0
        for lesson_id, scenes in LESSON_SCENES.items():
            try:
                lesson = Lesson.objects.get(pk=lesson_id)
            except Lesson.DoesNotExist:
                raise CommandError(f"No Lesson with pk={lesson_id} on this database.")

            existing = lesson.video_scenes.count()
            if existing:
                lesson.video_scenes.all().delete()

            for data in scenes:
                VideoScene.objects.create(lesson=lesson, **data)
            total_created += len(scenes)

            self.stdout.write(self.style.SUCCESS(
                f"Lesson {lesson.pk} ({lesson.title}): {len(scenes)} scene(s)"
                + (f" (replaced {existing})" if existing else "")
            ))

        self.stdout.write(self.style.SUCCESS(f"Done — {total_created} scene(s) across {len(LESSON_SCENES)} lesson(s)."))
