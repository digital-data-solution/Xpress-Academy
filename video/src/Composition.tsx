import React from 'react';
import {AbsoluteFill, Audio, Series, staticFile} from 'remotion';
import type {CalculateMetadataFunction} from 'remotion';
import {getAudioDurationInSeconds} from '@remotion/media-utils';

import {CaptionOverlay} from './scenes/CaptionOverlay';
import {SCENE_COMPONENTS} from './scenes';
import {themeForTrack} from './theme';
import type {CompositionProps, ResolvedScene} from './types';

const FPS = 30;

/**
 * IMPORTANT — why this file never imports src/tts/*:
 * calculateMetadata (and every component below) is bundled by Remotion
 * into the SAME webpack bundle that runs inside its headless-Chromium
 * render/preview process — confirmed the hard way while building this:
 * `remotion compositions` fails at the bundling step the instant
 * anything reachable from Root.tsx imports 'fs', 'crypto' or
 * 'child_process' (Webpack 5 does zero Node polyfilling, and Remotion
 * doesn't add any), and getAudioDurationInSeconds itself throws
 * "only available in the browser" if you try to call it from a plain
 * Node script directly. So Kokoro/ElevenLabs generation and disk
 * caching (src/tts/*, which DOES use fs/crypto/child_process) can only
 * ever run as a real Node process BEFORE bundling — that's
 * scripts/render-lesson.mjs. Its job is to make sure every scene's
 * audio already exists under public/audio/ and to stamp each scene
 * with `audioRelPath` pointing at it before inputProps ever reach this
 * file. What's left for calculateMetadata to do is exactly what it's
 * allowed to do: turn a relative path into a URL via staticFile() (pure
 * data, no Node APIs) and MEASURE the real file with
 * getAudioDurationInSeconds, which does work here because this code
 * really does run inside a browser context at render/Studio time.
 *
 * Net effect, Prompt 1 item 3 still holds exactly as asked: no scene
 * duration is ever hardcoded — every one is measured from real audio.
 * It's just measured here, and generated one step earlier.
 */
const durationOf = (scene: CompositionProps['scenes'][number]) => {
	const audioRelPath = scene.audioRelPath;
	if (!audioRelPath) {
		throw new Error(
			`Scene "${scene.type}" (narration: "${scene.narration.slice(0, 40)}...") has no audioRelPath. ` +
				'Render through npm run render:lesson / render:sample (scripts/render-lesson.mjs) — it ' +
				"prepares each scene's audio and stamps this field before Remotion ever sees the props. " +
				'Opening Root.tsx some other way with props that skip that step is the only way to land here.'
		);
	}
	return getAudioDurationInSeconds(staticFile(audioRelPath));
};

export const calculateMetadata: CalculateMetadataFunction<CompositionProps> = async ({props}) => {
	const resolvedScenes: ResolvedScene[] = [];
	for (const scene of props.scenes) {
		const durationInSeconds = await durationOf(scene);
		resolvedScenes.push({
			...scene,
			audioRelPath: scene.audioRelPath as string,
			durationInFrames: Math.max(1, Math.round(durationInSeconds * FPS)),
			captions: scene.captions ?? [],
		});
	}

	const durationInFrames = resolvedScenes.reduce((sum, scene) => sum + scene.durationInFrames, 0);

	return {
		props: {...props, scenes: resolvedScenes},
		durationInFrames,
		fps: FPS,
	};
};

const TEASER_MAX_SECONDS = 30;

/**
 * Prompt 1 item 7's "1080x1920 30-second teaser per lesson." Same
 * measurement as calculateMetadata above, just stops adding scenes once
 * the next one would push the teaser past 30s — always keeps at least
 * the first scene, even if that one alone runs long. Width/height for
 * the teaser are set on the <Composition> registration in Root.tsx, not
 * here; this only decides which scenes fit and how long the result is.
 */
export const calculateTeaserMetadata: CalculateMetadataFunction<CompositionProps> = async ({props}) => {
	const capFrames = TEASER_MAX_SECONDS * FPS;

	const resolvedScenes: ResolvedScene[] = [];
	let total = 0;
	for (const scene of props.scenes) {
		const durationInSeconds = await durationOf(scene);
		const durationInFrames = Math.max(1, Math.round(durationInSeconds * FPS));
		if (resolvedScenes.length > 0 && total + durationInFrames > capFrames) break;
		resolvedScenes.push({
			...scene,
			audioRelPath: scene.audioRelPath as string,
			durationInFrames,
			captions: scene.captions ?? [],
		});
		total += durationInFrames;
	}

	return {
		props: {...props, scenes: resolvedScenes},
		durationInFrames: total,
		fps: FPS,
	};
};

export const LessonVideo: React.FC<CompositionProps> = ({scenes, track}) => {
	const theme = themeForTrack(track);
	const resolved = scenes as ResolvedScene[]; // populated by calculateMetadata above by render time

	return (
		<AbsoluteFill>
			<Series>
				{resolved.map((scene, i) => {
					const SceneComponent = SCENE_COMPONENTS[scene.type];
					return (
						<Series.Sequence key={`${scene.type}-${i}`} durationInFrames={scene.durationInFrames}>
							<SceneComponent scene={scene} track={track} theme={theme} />
							<CaptionOverlay captions={scene.captions} />
							<Audio src={staticFile(scene.audioRelPath)} />
						</Series.Sequence>
					);
				})}
			</Series>
		</AbsoluteFill>
	);
};
