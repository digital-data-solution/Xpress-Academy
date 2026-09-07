import {describe, expect, it} from 'vitest';

import {compositionPropsSchema, sceneTypeSchema} from './types';

const baseScene = {
	type: 'bulletReveal' as const,
	narration: 'Hello.',
	image: null,
	payload: {},
};

describe('compositionPropsSchema', () => {
	it('defaults voiceProvider to kokoro when not specified — "default to kokoro, always"', () => {
		const parsed = compositionPropsSchema.parse({
			title: 'Test',
			track: 'VET',
			instructor: '',
			courseSlug: 'test',
			lessonSlug: 'test-lesson',
			scenes: [baseScene],
		});
		expect(parsed.voiceProvider).toBe('kokoro');
	});

	it('rejects a lesson with zero scenes', () => {
		const result = compositionPropsSchema.safeParse({
			title: 'Test',
			track: 'VET',
			instructor: '',
			courseSlug: 'test',
			lessonSlug: 'test-lesson',
			scenes: [],
		});
		expect(result.success).toBe(false);
	});

	it('rejects an unknown scene type — must match apps.catalog.models.VideoScene.SceneType exactly', () => {
		const result = sceneTypeSchema.safeParse('unknownSceneType');
		expect(result.success).toBe(false);
	});
});
