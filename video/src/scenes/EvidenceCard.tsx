import React from 'react';
import {Img} from 'remotion';

import type {SceneComponentProps} from './types';
import {Shell} from './Shell';

/** VET-track scenes only, per Prompt 1: "cites evidence grade." theme
 * .showsEvidenceGrade (src/theme.ts) is what actually gates the grade
 * badge — driven by track, not by whether payload happens to have one,
 * so a BREEDER-track lesson can't accidentally borrow clinical
 * authority it didn't earn. */
export const EvidenceCard: React.FC<SceneComponentProps> = ({scene, theme}) => {
	const claim = typeof scene.payload.claim === 'string' ? scene.payload.claim : '';
	const evidenceGrade = typeof scene.payload.evidenceGrade === 'string' ? scene.payload.evidenceGrade : '';
	const citation = typeof scene.payload.citation === 'string' ? scene.payload.citation : '';

	return (
		<Shell theme={theme}>
			<div style={{display: 'flex', gap: 40, alignItems: 'center'}}>
				{scene.image ? (
					<Img src={scene.image} style={{width: '35%', borderRadius: 12, objectFit: 'cover'}} />
				) : null}
				<div>
					<p style={{fontSize: 46, fontWeight: 600, margin: 0}}>{claim}</p>
					{theme.showsEvidenceGrade && evidenceGrade ? (
						<div
							style={{
								display: 'inline-block',
								marginTop: 20,
								padding: '8px 20px',
								borderRadius: 999,
								backgroundColor: theme.accent,
								color: theme.background,
								fontSize: 28,
								fontWeight: 700,
							}}
						>
							Evidence grade: {evidenceGrade}
						</div>
					) : null}
					{citation ? <p style={{fontSize: 22, opacity: 0.7, marginTop: 16}}>{citation}</p> : null}
				</div>
			</div>
		</Shell>
	);
};
