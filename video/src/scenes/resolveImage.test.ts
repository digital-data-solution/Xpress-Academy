import {describe, expect, it, vi} from 'vitest';

vi.mock('remotion', () => ({
	staticFile: (p: string) => `/static-file/${p}`,
}));

// Import after the mock so resolveImage.ts's `import {staticFile} from
// 'remotion'` resolves to the stub above, not the real implementation
// (which needs a `window` global this plain Node test environment
// doesn't have — see the .mjs render script's own comment on where
// browser-only Remotion APIs are and aren't safe to call).
const {resolveImageSrc} = await import('./resolveImage');

describe('resolveImageSrc', () => {
	it('prefers a real Django-authored image over an auto-fetched one', () => {
		const src = resolveImageSrc({image: 'https://cdn.example.com/real.jpg', imageRelPath: 'images/auto.jpg'});
		expect(src).toBe('https://cdn.example.com/real.jpg');
	});

	it('falls back to the auto-fetched Pexels image, resolved via staticFile', () => {
		const src = resolveImageSrc({image: null, imageRelPath: 'images/auto.jpg'});
		expect(src).toBe('/static-file/images/auto.jpg');
	});

	it('returns null when neither exists — no image, not an error', () => {
		expect(resolveImageSrc({image: null, imageRelPath: undefined})).toBeNull();
	});
});
