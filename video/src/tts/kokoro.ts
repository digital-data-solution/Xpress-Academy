import {spawn} from 'child_process';
import {writeFile} from 'fs/promises';
import path from 'path';

import type {TtsProvider} from './types';

const SIDECAR = path.join(process.cwd(), 'scripts', 'kokoro_tts.py');
const SERVER_URL = process.env.KOKORO_SERVER_URL || 'http://127.0.0.1:8765';

// Persistent server path (scripts/kokoro_server.py) — one torch/model
// load for an entire batch instead of one per scene. Diagnosed during a
// real overnight render batch: the per-scene subprocess spawn's cold
// reload was the actual driver behind repeated OOM kills, stacking on
// top of Remotion's own Chrome memory ~150 times in a row. Returns
// false (never throws) on anything from "server not running" to a
// mid-request failure — the caller falls back to the subprocess either
// way, so this is purely an optimization, never a new failure mode.
const generateViaServer = async (text: string, destPath: string, voice: string): Promise<boolean> => {
	try {
		const res = await fetch(`${SERVER_URL}/synthesize`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({text, voice}),
			signal: AbortSignal.timeout(60000),
		});
		if (!res.ok) return false;
		await writeFile(destPath, Buffer.from(await res.arrayBuffer()));
		return true;
	} catch {
		return false;
	}
};

const generateViaSubprocess = (text: string, destPath: string, voice: string) =>
	new Promise<void>((resolve, reject) => {
		const pythonBin = process.env.KOKORO_PYTHON || 'python';
		const child = spawn(pythonBin, [SIDECAR, destPath, `--voice=${voice}`]);

		let stderr = '';
		child.stderr.on('data', (chunk) => {
			stderr += chunk.toString();
		});
		child.on('error', (err) => {
			reject(
				new Error(
					`Failed to start Kokoro sidecar (${pythonBin} ${SIDECAR}). Is Kokoro installed? ` +
						`See video/README.md. Original error: ${err.message}`
				)
			);
		});
		child.on('close', (code) => {
			if (code !== 0) {
				reject(new Error(`Kokoro sidecar exited with code ${code}.\n${stderr}`));
				return;
			}
			resolve();
		});

		child.stdin.write(text, 'utf-8');
		child.stdin.end();
	});

/**
 * DEFAULT provider (Prompt 1 item 2: "NEVER call ElevenLabs unless
 * explicitly requested"). Local Kokoro-82M — no API key, no per-call
 * cost, so there is deliberately no cost guard here; see
 * src/tts/elevenlabs.ts for the one provider that needs one. Prefers
 * the persistent server (scripts/kokoro_server.py) when one is running,
 * falling back to the one-shot subprocess (scripts/kokoro_tts.py)
 * otherwise — both produce identical WAV output, just at very different
 * cold-start cost.
 */
export const kokoroProvider: TtsProvider = {
	name: 'kokoro',
	fileExtension: 'wav',
	generate: async (text, destPath, opts) => {
		const voice = opts.voiceId || 'af_heart';
		if (await generateViaServer(text, destPath, voice)) return;
		await generateViaSubprocess(text, destPath, voice);
	},
};
