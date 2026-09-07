import {createHash} from 'crypto';
import {existsSync, mkdirSync, writeFileSync} from 'fs';
import path from 'path';

// Node-only, same discipline as src/tts/* and src/captions/transcribe.ts
// — only ever called from scripts/render-lesson.mjs, before Remotion
// bundles anything (see Composition.tsx's top comment for why).
//
// "Images help in remembering things" — a real, contextual photo per
// content scene, not a placeholder. Pexels because: free, no card, ~20k
// requests/month, and it's what the original build doc already named
// for this exact purpose (Xpress Digital's ad pipeline). Never blocks a
// render: if PEXELS_API_KEY isn't set, or a search comes up empty, the
// scene just renders without an image — same fail-open discipline as
// captions.
const PUBLIC_IMAGES_DIR = path.join(process.cwd(), 'public', 'images');

const cacheKeyFor = (query: string) => createHash('sha256').update(query).digest('hex');

export type CachedImage = {imageRelPath: string; fromCache: boolean};

/**
 * Cached by hash(query) under public/images/ — the same search term
 * (e.g. a scene's heading) never re-fetches or re-spends a Pexels
 * request once it's been resolved once.
 */
export const getCachedImage = async (query: string): Promise<CachedImage | null> => {
	const apiKey = process.env.PEXELS_API_KEY;
	if (!apiKey) return null;

	mkdirSync(PUBLIC_IMAGES_DIR, {recursive: true});
	const key = cacheKeyFor(query);
	const imageRelPath = path.join('images', `${key}.jpg`);
	const absPath = path.join(process.cwd(), 'public', imageRelPath);

	if (existsSync(absPath)) {
		return {imageRelPath, fromCache: true};
	}

	try {
		const searchRes = await fetch(
			`https://api.pexels.com/v1/search?query=${encodeURIComponent(query)}&per_page=1&orientation=landscape`,
			{headers: {Authorization: apiKey}}
		);
		if (!searchRes.ok) {
			console.warn(`  (image: Pexels search failed for "${query}": ${searchRes.status})`);
			return null;
		}
		const data = (await searchRes.json()) as {photos?: Array<{src: {large: string}}>};
		const photo = data.photos?.[0];
		if (!photo) {
			console.warn(`  (image: no Pexels result for "${query}")`);
			return null;
		}

		const imgRes = await fetch(photo.src.large);
		if (!imgRes.ok) {
			console.warn(`  (image: failed to download Pexels photo for "${query}": ${imgRes.status})`);
			return null;
		}
		const buffer = Buffer.from(await imgRes.arrayBuffer());
		writeFileSync(absPath, buffer);
		return {imageRelPath, fromCache: false};
	} catch (err) {
		console.warn(`  (image: Pexels lookup errored for "${query}": ${err instanceof Error ? err.message : err})`);
		return null;
	}
};
