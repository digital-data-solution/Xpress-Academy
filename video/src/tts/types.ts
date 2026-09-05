import type {VoiceProviderName} from '../types';

export type TtsResult = {
	/** Path to the generated (or cache-hit) audio file, relative to
	 * video/public/ — exactly what Composition.tsx passes to Remotion's
	 * staticFile(). */
	audioRelPath: string;
	/** True when this call was served from cache — i.e. did NOT spend an
	 * ElevenLabs credit. The batch cost guard sums characters only for
	 * results where this is false. */
	fromCache: boolean;
};

export interface TtsProvider {
	name: VoiceProviderName;
	/** Real container format this provider writes — Kokoro writes actual
	 * WAV (via soundfile), ElevenLabs returns MP3. The cache layer names
	 * the file by THIS, not a hardcoded ".wav" for both: saving an MP3
	 * response with a ".wav" name would still "work" often enough in a
	 * quick test (many probes sniff content, not extension) while being
	 * quietly wrong — exactly the kind of thing that fails in a way that
	 * looks like success. */
	fileExtension: 'wav' | 'mp3';
	/** Generate speech for `text` into `destPath` (chosen by the cache
	 * layer — see src/tts/cache.ts — with this provider's fileExtension).
	 * Providers do not decide their own output path or do their own
	 * caching; that's deliberately one shared piece of logic
	 * (hash(text + provider + voiceId)) so both providers cache
	 * identically instead of each reimplementing it. */
	generate(text: string, destPath: string, opts: {voiceId?: string}): Promise<void>;
}
