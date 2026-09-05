import type {VoiceProviderName} from '../types';
import {elevenLabsProvider} from './elevenlabs.ts';
import {kokoroProvider} from './kokoro.ts';
import type {TtsProvider} from './types';

export {getCachedAudio, uncachedCharacterCount} from './cache.ts';
export {estimateElevenLabsCost} from './elevenlabs.ts';
export type {TtsProvider, TtsResult} from './types';

const PROVIDERS: Record<VoiceProviderName, TtsProvider> = {
	kokoro: kokoroProvider,
	elevenlabs: elevenLabsProvider,
};

// DEFAULT = kokoro, everywhere, always — the one line every caller
// (render script, Studio preview, a scheduled digest job in other
// prompts) should route `--voice` through, so "default to kokoro" is
// true by construction rather than by every call site remembering to
// pass 'kokoro' itself.
export const resolveProvider = (name: VoiceProviderName = 'kokoro'): TtsProvider => PROVIDERS[name];
