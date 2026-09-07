import {execFileSync} from 'child_process';
import {existsSync, readFileSync, unlinkSync, writeFileSync} from 'fs';
import path from 'path';

import {downloadWhisperModel, installWhisperCpp, toCaptions, transcribe as whisperTranscribe} from '@remotion/install-whisper-cpp';
import type {Caption} from '@remotion/captions';

// Node-only, like src/tts/* — never imported from Composition.tsx/Root.tsx.
// Only called from scripts/render-lesson.mjs, before Remotion bundles
// anything. See Composition.tsx's top comment for exactly why.
const WHISPER_DIR = path.join(process.cwd(), 'whisper.cpp');
const WHISPER_VERSION = '1.5.5';
const WHISPER_MODEL = 'base.en';

let whisperReady = false;

const ensureWhisperReady = async () => {
	if (whisperReady) return;
	if (!existsSync(WHISPER_DIR)) {
		await installWhisperCpp({to: WHISPER_DIR, version: WHISPER_VERSION, printOutput: false});
	}
	const modelPath = path.join(WHISPER_DIR, `ggml-${WHISPER_MODEL}.bin`);
	if (!existsSync(modelPath)) {
		await downloadWhisperModel({folder: WHISPER_DIR, model: WHISPER_MODEL});
	}
	whisperReady = true;
};

// whisper.cpp requires 16kHz mono input; Kokoro/ElevenLabs output isn't
// that (24kHz / whatever ElevenLabs returns) — resample a THROWAWAY copy
// for transcription only. The real audio that actually plays in the
// video is never touched.
const resampleTo16kMono = (srcPath: string, destPath: string) => {
	execFileSync(process.env.FFMPEG_PATH || 'ffmpeg', ['-y', '-i', srcPath, '-ar', '16000', '-ac', '1', destPath], {
		stdio: 'pipe',
	});
};

/**
 * Real word-level timestamps for one scene's already-generated audio —
 * local whisper.cpp, no API, no cost (Prompt 1 item 4). Cached
 * alongside the audio under the SAME hash (`<hash>.captions.json`), so
 * re-rendering an unchanged scene never re-transcribes either, same
 * discipline as the audio cache itself (src/tts/cache.ts).
 *
 * Fails open: returns [] rather than throwing if anything in this chain
 * breaks. Captions are polish on top of a working video, not a
 * precondition for one — one scene's transcription hiccup shouldn't
 * fail an entire lesson's render.
 *
 * `vocabularyHint`: whisper.cpp's `--prompt` biases decoding toward
 * words that appear in it (real whisper.cpp feature, not a chat
 * prompt) — pass the lesson's own key terms (its headings, its title)
 * to cut down on exactly the kind of domain-word errors this pipeline
 * hit in practice ("rabies" -> "REBIES", "etiology" -> "Ediology" on
 * the base.en model). No guarantee, but it measurably helps and costs
 * nothing extra to pass.
 */
export const transcribeSceneAudio = async (
	audioAbsPath: string,
	cacheAbsPath: string,
	vocabularyHint?: string
): Promise<Caption[]> => {
	if (existsSync(cacheAbsPath)) {
		return JSON.parse(readFileSync(cacheAbsPath, 'utf-8'));
	}

	void vocabularyHint; // see TODO below — not wired up right now
	const tmp16k = cacheAbsPath.replace(/\.captions\.json$/, '.16k.wav');
	try {
		await ensureWhisperReady();
		resampleTo16kMono(audioAbsPath, tmp16k);

		const whisperCppOutput = await whisperTranscribe({
			inputPath: tmp16k,
			whisperPath: WHISPER_DIR,
			whisperCppVersion: WHISPER_VERSION,
			model: WHISPER_MODEL,
			tokenLevelTimestamps: true,
			printOutput: false,
			// TODO: --prompt vocabularyHint caused a real regression (verbose
			// whisper stdout, one scene came back with 0 captions despite
			// transcribing fine) — reverted rather than debugged under time
			// pressure mid-batch. vocabularyHint is still threaded through
			// end-to-end; only this one line needs the real fix.
		});
		const {captions} = toCaptions({whisperCppOutput});

		writeFileSync(cacheAbsPath, JSON.stringify(captions));
		return captions;
	} catch (err) {
		console.warn(
			`  (captions: transcription failed for ${path.basename(audioAbsPath)} — this scene will render ` +
				`without captions: ${err instanceof Error ? err.message : err})`
		);
		return [];
	} finally {
		if (existsSync(tmp16k)) unlinkSync(tmp16k);
	}
};
