import {staticFile} from 'remotion';

import type {ResolvedScene} from '../types';

/**
 * Every scene component that shows a picture goes through this instead
 * of reading `scene.image` directly. `image` (set on VideoScene in
 * Django, already an absolute URL — see apps.catalog.models.VideoScene)
 * is a deliberate authored choice and always wins. `imageRelPath` (set
 * by scripts/render-lesson.mjs from a Pexels search — see
 * src/images/pexels.ts) is the automatic fallback, and needs
 * staticFile() to turn it into something Remotion can actually load.
 * Returns null (render nothing) when neither exists — a missing image
 * is never a render error, just a scene with no picture.
 */
export const resolveImageSrc = (scene: Pick<ResolvedScene, 'image' | 'imageRelPath'>): string | null => {
	if (scene.image) return scene.image;
	if (scene.imageRelPath) return staticFile(scene.imageRelPath);
	return null;
};
