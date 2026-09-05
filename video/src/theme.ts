import type {Track} from './types';

// Prompt 1's whole reason for keeping `track` on the props type: "Video
// tone must differ. Track 1 is plain, warm, practical. Track 2 is
// precise and cites evidence grade." That has to be a lookup keyed by
// track, not a per-scene-component if/else scattered through the
// codebase — a third Programme.audience value (or JAMB later, which has
// its own Manim path, not this) must not require touching every scene
// component to add a branch.
export type TrackTheme = {
	/** Shown on evidenceCard scenes. VET is the only track where a claim
	 * is expected to carry a grade; BREEDER copy stays plain-language and
	 * never claims clinical evidence. */
	showsEvidenceGrade: boolean;
	accent: string;
	background: string;
	text: string;
	fontFamily: string;
	/** Register cue surfaced to scene components' copy (e.g. bulletReveal
	 * uses this to decide plain bullet punctuation vs a more clinical,
	 * numbered-citation style). Not used for narration text itself —
	 * narration always comes verbatim from the author (see VideoScene) —
	 * only for chrome the pipeline itself draws. */
	register: 'plain' | 'clinical';
};

const THEMES: Record<Track, TrackTheme> = {
	BREEDER: {
		showsEvidenceGrade: false,
		accent: '#B45309', // warm amber
		background: '#FFFBF5',
		text: '#2B2118',
		fontFamily: '"Nunito", "Segoe UI", sans-serif',
		register: 'plain',
	},
	VET: {
		showsEvidenceGrade: true,
		accent: '#0F5C4C', // clinical teal
		background: '#F5FAF8',
		text: '#0F1F1B',
		fontFamily: '"IBM Plex Sans", "Segoe UI", sans-serif',
		register: 'clinical',
	},
	GENERAL: {
		showsEvidenceGrade: false,
		accent: '#1D4ED8',
		background: '#F8FAFC',
		text: '#0F172A',
		fontFamily: '"Segoe UI", sans-serif',
		register: 'plain',
	},
};

export const themeForTrack = (track: Track): TrackTheme => THEMES[track];
