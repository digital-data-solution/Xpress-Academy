import {writeFile} from 'fs/promises';

import type {TtsProvider} from './types';

const API_BASE = 'https://api.elevenlabs.io/v1';

// Rough, deliberately conservative estimate for the pre-batch cost
// print (Prompt 1 item 2 / Prompt 4 item "Voice strategy"): ElevenLabs'
// published per-character rate moves between plans and over time, so
// treat this as "in the right ballpark," not a quote — the API key's
// own dashboard (elevenlabs.io/app/usage) is the source of truth.
// Verify against the current pricing page before trusting this for a
// real budget decision; last checked when this file was written
// (2026-09), Creator-tier cost per 1k characters was in the ~$0.09-0.11
// range.
const ESTIMATED_USD_PER_1K_CHARACTERS = 0.1;

export const estimateElevenLabsCost = (characters: number) => ({
	characters,
	estimatedUsd: Math.round((characters / 1000) * ESTIMATED_USD_PER_1K_CHARACTERS * 100) / 100,
});

// STOCK_FALLBACK_VOICE_ID: "Rachel", one of ElevenLabs' own premade
// voices — always resolvable with just an API key, so a render never
// hard-fails only because ELEVENLABS_VOICE_ID isn't set yet (Prompt 1:
// "fall back to a stock voice if unset").
const STOCK_FALLBACK_VOICE_ID = '21m00Tcm4TlvDq8ikWAM';

/**
 * OPT-IN provider (Prompt 1 item 2). Never called by anything in this
 * project except a render explicitly started with --voice=elevenlabs —
 * see scripts/render-lesson.mjs, which is also where the cost guard
 * (estimateElevenLabsCost + a confirmation prompt) lives, run ONCE
 * before any scene in the batch reaches this file.
 */
export const elevenLabsProvider: TtsProvider = {
	name: 'elevenlabs',
	fileExtension: 'mp3',
	generate: async (text, destPath, opts) => {
		const apiKey = process.env.ELEVENLABS_API_KEY;
		if (!apiKey) {
			throw new Error(
				'ELEVENLABS_API_KEY is not set. This provider is opt-in and should only run when you ' +
					'meant to spend a credit — set the env var to actually use it.'
			);
		}
		const voiceId = opts.voiceId || process.env.ELEVENLABS_VOICE_ID || STOCK_FALLBACK_VOICE_ID;

		const res = await fetch(`${API_BASE}/text-to-speech/${voiceId}`, {
			method: 'POST',
			headers: {
				'xi-api-key': apiKey,
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				text,
				model_id: 'eleven_multilingual_v2',
			}),
		});

		if (!res.ok) {
			const body = await res.text();
			throw new Error(`ElevenLabs request failed (${res.status}): ${body}`);
		}

		const buffer = Buffer.from(await res.arrayBuffer());
		await writeFile(destPath, buffer);
	},
};
