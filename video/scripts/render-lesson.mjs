#!/usr/bin/env node
/**
 * The real entry point for turning a lesson's JSON (from
 * `manage.py export_lesson_video_json <lesson_id>` on the Django side)
 * into an MP4. Deliberately plain Node — NOT part of what Remotion's
 * bundle() processes for Root.tsx — because this is the one place
 * allowed to touch the filesystem, spawn Kokoro, and call ElevenLabs;
 * see src/Composition.tsx's top comment for exactly why that split
 * exists. It imports src/tts/*.ts directly (Node 24's built-in
 * TypeScript support strips the type annotations at load time — no
 * separate build step) so the caching/provider logic lives in ONE
 * place, not duplicated between "the interface" and "what actually
 * runs."
 *
 * Usage:
 *   node scripts/render-lesson.mjs --props=samples/what-is-rabies.json [--voice=kokoro|elevenlabs] [--composition=LessonVideo|LessonVideoTeaser] [--out=path.mp4] [--yes]
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
 *   3. Bundle src/Root.tsx and render the requested composition to
 *      out/<track>/<lesson-slug>/<composition>.mp4 (Prompt 1 item 7's
 *      folder convention), via renderMedia() — not a shell loop over
 *      the CLI (Prompt 1 item 8).
 */
import {mkdirSync, readFileSync} from 'fs';
import path from 'path';
import readline from 'readline/promises';

import 'dotenv/config';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';

import {estimateElevenLabsCost, getCachedAudio, resolveProvider, uncachedCharacterCount} from '../src/tts/index.ts';

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

async function main() {
	const args = parseArgs();
	if (!args.props) {
		console.error(
			'Usage: node scripts/render-lesson.mjs --props=<path.json> [--voice=kokoro|elevenlabs] ' +
				'[--composition=LessonVideo|LessonVideoTeaser] [--out=path.mp4] [--yes]'
		);
		process.exitCode = 1;
		return;
	}

	const voiceProviderName = args.voice || 'kokoro'; // DEFAULT is kokoro — Prompt 1 item 2
	const compositionId = args.composition || 'LessonVideo';
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

	console.log(`Preparing audio for ${props.scenes.length} scene(s) via ${voiceProviderName}...`);
	const preparedScenes = [];
	for (const [i, scene] of props.scenes.entries()) {
		const {audioRelPath, fromCache} = await getCachedAudio(provider, scene.narration, voiceId);
		console.log(`  scene ${i + 1}/${props.scenes.length} (${scene.type}): ${fromCache ? 'cached' : 'generated'}`);
		preparedScenes.push({...scene, audioRelPath});
	}
	const preparedProps = {
		...props,
		voiceProvider: voiceProviderName,
		voiceId,
		scenes: preparedScenes,
	};

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
	});

	console.log(`Done: ${outPath}`);
}

main().catch((err) => {
	console.error(err);
	process.exitCode = 1;
});
