#!/usr/bin/env node
/**
 * The real entry point for turning a lesson's JSON (from
 * `manage.py export_lesson_video_json <lesson_id>` on the Django side)
 * into an MP4. Deliberately plain Node — NOT part of what Remotion's
 * bundle() processes for Root.tsx — because this is the one place
 * allowed to touch the filesystem, spawn Kokoro, and call ElevenLabs;
 * see src/Composition.tsx's top comment for exactly why that split
 * exists. It imports src/tts/*.ts and src/captions/*.ts directly
 * (Node 24's built-in TypeScript support strips the type annotations at
 * load time — no separate build step) so the caching/provider/
 * transcription logic lives in ONE place, not duplicated between "the
 * interface" and "what actually runs."
 *
 * Usage:
 *   node scripts/render-lesson.mjs --props=samples/rabies-module-1.json [--voice=kokoro|elevenlabs] [--composition=LessonVideo|LessonVideoTeaser] [--out=path.mp4] [--yes] [--no-captions]
 *
 * What it does, in order:
 *   1. For every scene, ensure its narration audio exists under
 *      public/audio/ (generating it via the selected provider only on a
 *      cache miss) and stamp `audioRelPath` onto the scene.
 *   2. If --voice=elevenlabs, print the character count / estimated
 *      cost for whatever is NOT already cached and require typed
 *      confirmation before spending anything (Prompt 1 item 2 /
 *      Prompt 4's hard cost guard) — skippable with --yes for
 *      non-interactive use, but never silently.
 *   3. Transcribe each scene's real audio with local whisper.cpp for
 *      word-level timestamps (Prompt 1 item 4), cached the same way as
 *      audio. Skippable with --no-captions for a quick layout/timing
 *      iteration that doesn't need captions yet.
 *   4. Bundle src/Root.tsx and render the requested composition to
 *      out/<track>/<lesson-slug>/<composition>.mp4 (Prompt 1 item 7's
 *      folder convention), via renderMedia() — not a shell loop over
 *      the CLI (Prompt 1 item 8). Writes a matching .srt sidecar next
 *      to it, built from the same captions burnt into the video.
 */
import {execFileSync} from 'child_process';
import {mkdirSync, readFileSync, writeFileSync} from 'fs';
import os from 'os';
import path from 'path';
import readline from 'readline/promises';

import 'dotenv/config';
import {bundle} from '@remotion/bundler';
import {createTikTokStyleCaptions, serializeSrt} from '@remotion/captions';
import {renderMedia, selectComposition} from '@remotion/renderer';

import {transcribeSceneAudio} from '../src/captions/transcribe.ts';
import {getCachedImage} from '../src/images/pexels.ts';
import {estimateElevenLabsCost, getCachedAudio, resolveProvider, uncachedCharacterCount} from '../src/tts/index.ts';

// Learned the hard way (a real OOM killed a 154-lesson batch partway
// through): Remotion's render Chrome needs real headroom to even
// launch. Rather than start a render that's likely to just die, wait
// here — cheap, and turns "the whole batch crashes at 2am" into "this
// one lesson pauses for a bit."
const MIN_FREE_MEMORY_BYTES = 500 * 1024 * 1024;
const MEMORY_POLL_MS = 15000;

async function waitForMemory() {
	let warned = false;
	while (os.freemem() < MIN_FREE_MEMORY_BYTES) {
		if (!warned) {
			console.warn(
				`  (memory: only ${Math.round(os.freemem() / 1024 / 1024)}MB free, want ${Math.round(
					MIN_FREE_MEMORY_BYTES / 1024 / 1024
				)}MB before starting Chrome — waiting rather than risk an OOM crash)`
			);
			warned = true;
		}
		await new Promise((resolve) => setTimeout(resolve, MEMORY_POLL_MS));
	}
}

function parseArgs() {
	const out = {};
	for (const arg of process.argv.slice(2)) {
		const [key, ...rest] = arg.replace(/^--/, '').split('=');
		out[key] = rest.length ? rest.join('=') : true;
	}
	return out;
}

async function confirmSpend(characters, estimatedUsd) {
	const rl = readline.createInterface({input: process.stdin, output: process.stdout});
	try {
		const answer = await rl.question(
			`About to spend ElevenLabs credits: ${characters} characters, ~$${estimatedUsd} estimated ` +
				'(rough — check elevenlabs.io/app/usage for the real rate). Type "yes" to continue: '
		);
		return answer.trim().toLowerCase() === 'yes';
	} finally {
		rl.close();
	}
}

// Real duration of the audio that will actually play, used only to
// place captions at the right offset in the combined .srt sidecar —
// Remotion's own calculateMetadata (Composition.tsx) is the source of
// truth for the video's actual per-scene frame timing; this is a
// second, independent measurement of the same real file for the
// sidecar, not a value fed back into the render itself.
function ffprobeDurationMs(absPath) {
	const out = execFileSync(
		process.env.FFPROBE_PATH || 'ffprobe',
		['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', absPath],
		{encoding: 'utf-8'}
	);
	return Math.round(parseFloat(out.trim()) * 1000);
}

async function main() {
	const args = parseArgs();
	if (!args.props) {
		console.error(
			'Usage: node scripts/render-lesson.mjs --props=<path.json> [--voice=kokoro|elevenlabs] ' +
				'[--composition=LessonVideo|LessonVideoTeaser] [--out=path.mp4] [--yes] [--no-captions]'
		);
		process.exitCode = 1;
		return;
	}

	const voiceProviderName = args.voice || 'kokoro'; // DEFAULT is kokoro — Prompt 1 item 2
	const compositionId = args.composition || 'LessonVideo';
	const wantCaptions = !args['no-captions'];
	const provider = resolveProvider(voiceProviderName);
	const props = JSON.parse(readFileSync(path.resolve(args.props), 'utf-8'));
	const voiceId =
		args.voiceId || (voiceProviderName === 'elevenlabs' ? process.env.ELEVENLABS_VOICE_ID || '' : 'af_heart');

	if (voiceProviderName === 'elevenlabs') {
		const characters = uncachedCharacterCount(
			props.scenes.map((s) => s.narration),
			provider,
			voiceId
		);
		const {estimatedUsd} = estimateElevenLabsCost(characters);
		if (characters === 0) {
			console.log('ElevenLabs: everything is already cached — this render will not spend anything.');
		} else {
			console.log(`ElevenLabs: ${characters} uncached characters, ~$${estimatedUsd} estimated.`);
			if (!args.yes && !(await confirmSpend(characters, estimatedUsd))) {
				console.log('Aborted — nothing rendered, nothing spent.');
				process.exitCode = 1;
				return;
			}
		}
	}

	// whisper.cpp --prompt vocabulary hint (see transcribeSceneAudio's
	// comment) — built once per lesson from the lesson title and every
	// scene heading, so domain terms ("etiology", "lyssavirus", the
	// disease name itself) are primed before transcribing any scene.
	const vocabularyHint = [props.title, ...props.scenes.map((s) => s.payload?.heading).filter(Boolean)]
		.join(', ')
		.slice(0, 800);

	console.log(`Preparing audio for ${props.scenes.length} scene(s) via ${voiceProviderName}...`);
	const preparedScenes = [];
	let cumulativeMs = 0;
	const srtLines = [];
	for (const [i, scene] of props.scenes.entries()) {
		const {audioRelPath, fromCache} = await getCachedAudio(provider, scene.narration, voiceId);
		const audioAbsPath = path.resolve('public', audioRelPath);
		const durationMs = ffprobeDurationMs(audioAbsPath);

		let captions = [];
		if (wantCaptions) {
			const captionsCachePath = path.resolve(
				'public',
				audioRelPath.replace(/\.(wav|mp3)$/, '.captions.json')
			);
			captions = await transcribeSceneAudio(audioAbsPath, captionsCachePath, vocabularyHint);
		}

		// "Images help in remembering things" — a real, contextual photo
		// per content scene (titleCard/outroCard stay text-only; they're
		// branding beats, not content). Never overrides a real
		// Django-authored image; silently skipped if PEXELS_API_KEY isn't
		// set (see src/images/pexels.ts) — a render never fails or even
		// warns loudly just because photos aren't configured yet.
		let imageRelPath;
		const wantsImage = !scene.image && ['bulletReveal', 'evidenceCard', 'workedExample', 'whiteboardDiagram', 'fullImage'].includes(scene.type);
		if (wantsImage) {
			const query = scene.payload?.heading || props.title;
			const image = await getCachedImage(query);
			if (image) imageRelPath = image.imageRelPath;
		}

		console.log(
			`  scene ${i + 1}/${props.scenes.length} (${scene.type}): audio ${fromCache ? 'cached' : 'generated'}` +
				(wantCaptions ? `, ${captions.length} caption token(s)` : '') +
				(imageRelPath ? ', image' : '')
		);

		preparedScenes.push({...scene, audioRelPath, captions, ...(imageRelPath ? {imageRelPath} : {})});

		// Offset this scene's captions into the whole lesson's timeline for
		// the .srt sidecar, grouped into the SAME short pages the burnt-in
		// caption bar shows on screen (CaptionOverlay.tsx uses the identical
		// createTikTokStyleCaptions call) — one SRT cue per page, not one
		// giant cue per scene.
		if (captions.length > 0) {
			const {pages} = createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds: 1200});
			for (const page of pages) {
				srtLines.push(
					page.tokens.map((token, idx) => ({
						text: token.text,
						startMs: cumulativeMs + token.fromMs,
						endMs: cumulativeMs + token.toMs,
						timestampMs: null,
						confidence: null,
						pageBreakAfter: idx === page.tokens.length - 1,
					}))
				);
			}
		}
		cumulativeMs += durationMs;
	}
	const preparedProps = {
		...props,
		voiceProvider: voiceProviderName,
		voiceId,
		scenes: preparedScenes,
	};

	await waitForMemory();

	console.log('Bundling src/Root.tsx...');
	const serveUrl = await bundle({entryPoint: path.resolve('src/Root.tsx')});

	const composition = await selectComposition({serveUrl, id: compositionId, inputProps: preparedProps});

	const trackDir = (props.track || 'general').toLowerCase();
	const outPath = args.out
		? path.resolve(args.out)
		: path.resolve('out', trackDir, props.lessonSlug || 'lesson', `${compositionId}.mp4`);
	mkdirSync(path.dirname(outPath), {recursive: true});

	console.log(
		`Rendering ${compositionId} (${composition.durationInFrames} frames @ ${composition.fps}fps, ` +
			`${composition.width}x${composition.height}) -> ${outPath}`
	);
	await renderMedia({
		composition,
		serveUrl,
		codec: 'h264',
		outputLocation: outPath,
		inputProps: preparedProps,
		// Remotion's default concurrency opens several parallel Chrome
		// tabs to render frames faster — on a machine with a couple GB of
		// RAM to spare that's fine; on this one it's very likely what
		// actually pushed the earlier batch into OOM. Slower, but it
		// finishes instead of taking the whole batch down with it.
		concurrency: 1,
	});

	if (srtLines.length > 0) {
		const srtPath = outPath.replace(/\.mp4$/, '.srt');
		writeFileSync(srtPath, serializeSrt({lines: srtLines}));
		console.log(`Captions: ${srtPath}`);
	}

	console.log(`Done: ${outPath}`);
}

main().catch((err) => {
	console.error(err);
	process.exitCode = 1;
});
