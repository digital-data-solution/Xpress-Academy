import {spawn} from 'child_process';
import path from 'path';

import type {TtsProvider} from './types';

const SIDECAR = path.join(process.cwd(), 'scripts', 'kokoro_tts.py');

/**
 * DEFAULT provider (Prompt 1 item 2: "NEVER call ElevenLabs unless
 * explicitly requested"). Local Kokoro-82M via a Python sidecar — no API
 * key, no per-call cost, so there is deliberately no cost guard here;
 * see src/tts/elevenlabs.ts for the one provider that needs one.
 */
export const kokoroProvider: TtsProvider = {
	name: 'kokoro',
	fileExtension: 'wav',
	generate: (text, destPath, opts) =>
		new Promise((resolve, reject) => {
			const pythonBin = process.env.KOKORO_PYTHON || 'python';
			const voice = opts.voiceId || 'af_heart';
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
		}),
};
