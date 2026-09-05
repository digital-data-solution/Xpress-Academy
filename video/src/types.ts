import {z} from 'zod';

// Mirrors apps.catalog.models.VideoScene.SceneType and the JSON emitted by
// `manage.py export_lesson_video_json <lesson_id>` (see that command's
// docstring on the Django side). Keep these two lists in sync by hand —
// there are only seven values, a shared codegen step would be more
// machinery than the problem needs.
export const sceneTypeSchema = z.enum([
	'titleCard',
	'bulletReveal',
	'whiteboardDiagram',
	'fullImage',
	'workedExample',
	'evidenceCard',
	'outroCard',
]);
export type SceneType = z.infer<typeof sceneTypeSchema>;

// `payload` is intentionally untyped JSON on the Django side (see
// VideoScene.payload's help_text) so scene shape can evolve here without
// a migration there. Each scene component below narrows it with
// `.parse()`/`.safeParse()` against its OWN schema, not this file — the
// cost of a wrong lesson author's payload is a clear render-time error
// naming the lesson and scene, not a silent blank frame.
export const sceneSchema = z.object({
	type: sceneTypeSchema,
	narration: z.string(),
	image: z.string().nullable(),
	payload: z.record(z.string(), z.unknown()),
	// NOT part of what Django exports — stamped on by
	// scripts/render-lesson.mjs once it has generated/cached this
	// scene's narration audio into video/public/audio/, as a path
	// relative to public/ (what Remotion's staticFile() expects). Optional
	// here because a freshly-exported lesson JSON legitimately doesn't
	// have it yet; Composition.tsx's calculateMetadata is what actually
	// requires it to be present, with a clear error naming the scene if
	// it isn't (see that file's comment on why this can't be generated
	// in-line during rendering).
	audioRelPath: z.string().optional(),
});
export type Scene = z.infer<typeof sceneSchema>;

// "Track" is Programme.audience on the Django side (Audience.BREEDER /
// Audience.VET / Audience.GENERAL) — it's what drives tone: Prompt 1 is
// explicit that track 1 (dog breeding) is plain/warm/practical and
// track 2 (veterinary) is precise/evidence-graded. That difference is
// looked up from this field at render time (see src/theme.ts), never
// hardcoded per-scene-component, so a new BREEDER or VET lesson gets the
// right register automatically.
export const trackSchema = z.enum(['BREEDER', 'VET', 'GENERAL']);
export type Track = z.infer<typeof trackSchema>;

export const lessonVideoPropsSchema = z.object({
	title: z.string(),
	track: trackSchema,
	instructor: z.string(),
	courseSlug: z.string(),
	lessonSlug: z.string(),
	scenes: z.array(sceneSchema).min(1),
});
export type LessonVideoProps = z.infer<typeof lessonVideoPropsSchema>;

// Academy only ever needs these two (Prompt 1 item 2) — AjoApp's separate
// pipeline is the one with a third `manual` provider for hand-recorded
// Pidgin audio; that doesn't apply here, so it isn't in this union.
export const voiceProviderSchema = z.enum(['kokoro', 'elevenlabs']);
export type VoiceProviderName = z.infer<typeof voiceProviderSchema>;

// What the COMPOSITION actually takes as inputProps: the lesson content
// (verbatim from export_lesson_video_json) plus which voice to render
// with. Kept separate from lessonVideoPropsSchema on purpose — voice
// choice is a render-time decision, not part of what Django exported,
// and defaulting it here (not scattered across call sites) is what
// makes "kokoro is the default provider" true by construction.
export const compositionPropsSchema = lessonVideoPropsSchema.extend({
	voiceProvider: voiceProviderSchema.default('kokoro'),
	voiceId: z.string().default(''),
});
export type CompositionProps = z.infer<typeof compositionPropsSchema>;

// What calculateMetadata hands each scene component after resolving
// audio (see Composition.tsx) — the authored Scene plus what only
// exists once the narration has actually been synthesized: the audio
// file to play and how many frames it fills. No scene ever hardcodes a
// duration; this is the one place a duration exists, and it always
// comes from measuring real audio (Prompt 1 item 3).
export type ResolvedScene = Scene & {
	audioRelPath: string;
	durationInFrames: number;
};
