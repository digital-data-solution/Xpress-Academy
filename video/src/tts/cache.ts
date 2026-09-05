import {createHash} from 'crypto';
import {existsSync, mkdirSync} from 'fs';
import path from 'path';

import type {TtsProvider, TtsResult} from './types';

// Files live under public/audio/ — NOT .cache/ — because Remotion's
// staticFile() (what Composition.tsx uses to actually play/measure
// this audio) only serves paths under the project's public/ folder.
// Same folder doubles as the durable cache: re-running a render for a
// scene whose narration hasn't changed finds its file already here and
// never regenerates it.
const PUBLIC_AUDIO_DIR = path.join(process.cwd(), 'public', 'audio');

const cacheKey = (text: string, providerName: string, voiceId: string) =>
	createHash('sha256').update(`${providerName}:${voiceId}:${text}`).digest('hex');

const relPathFor = (provider: TtsProvider, text: string, voiceId: string) =>
	path.join('audio', `${cacheKey(text, provider.name, voiceId)}.${provider.fileExtension}`);

/**
 * The one place "an unchanged scene must never re-bill me" (Prompt 1
 * item 2 / Prompt 4's cost guard) is actually enforced. Every provider —
 * Kokoro or ElevenLabs — goes through this; neither is called at all
 * when the hash already has a cached file on disk. Keying on
 * hash(text + provider + voiceId) means switching providers, or
 * re-cloning a voice under a new voiceId, correctly produces a fresh
 * cache entry instead of silently reusing stale audio from a different
 * voice.
 *
 * Only ever called from scripts/render-lesson.mjs (a real Node
 * process, run BEFORE Remotion bundles/renders anything) — never from
 * Composition.tsx. See that file's top comment for why: this module
 * uses fs/crypto/child_process, none of which exist in the
 * headless-Chromium context calculateMetadata actually runs in.
 */
export const getCachedAudio = async (provider: TtsProvider, text: string, voiceId: string): Promise<TtsResult> => {
	mkdirSync(PUBLIC_AUDIO_DIR, {recursive: true});
	const audioRelPath = relPathFor(provider, text, voiceId);
	const absPath = path.join(process.cwd(), 'public', audioRelPath);

	const fromCache = existsSync(absPath);
	if (!fromCache) {
		await provider.generate(text, absPath, {voiceId});
	}

	return {audioRelPath, fromCache};
};

/** Characters that WOULD be billed right now for `text` under `voiceId` —
 * i.e. skips anything already cached. Used by the ElevenLabs cost guard
 * so the estimate reflects what a batch is actually about to spend, not
 * the whole lesson's narration (most of which is usually already
 * cached from earlier Kokoro iteration). */
export const uncachedCharacterCount = (texts: string[], provider: TtsProvider, voiceId: string): number =>
	texts
		.filter((text) => !existsSync(path.join(process.cwd(), 'public', relPathFor(provider, text, voiceId))))
		.reduce((sum, text) => sum + text.length, 0);
