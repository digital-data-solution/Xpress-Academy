import {describe, expect, it} from 'vitest';

import {themeForTrack} from './theme';

describe('themeForTrack', () => {
	it('gives VET the clinical register with an evidence grade badge', () => {
		const theme = themeForTrack('VET');
		expect(theme.register).toBe('clinical');
		expect(theme.showsEvidenceGrade).toBe(true);
	});

	it('gives BREEDER the plain register WITHOUT an evidence grade badge', () => {
		// The real reason this matters: EvidenceCard.tsx gates the grade
		// badge on theme.showsEvidenceGrade specifically so a BREEDER-track
		// lesson can never accidentally borrow clinical authority it
		// didn't earn, even if its payload happens to carry an
		// evidenceGrade field.
		const theme = themeForTrack('BREEDER');
		expect(theme.register).toBe('plain');
		expect(theme.showsEvidenceGrade).toBe(false);
	});

	it('gives every track a distinct accent color', () => {
		const accents = new Set((['BREEDER', 'VET', 'GENERAL'] as const).map((t) => themeForTrack(t).accent));
		expect(accents.size).toBe(3);
	});
});
