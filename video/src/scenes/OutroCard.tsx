import React from 'react';

import type {SceneComponentProps} from './types';
import {Shell} from './Shell';

export const OutroCard: React.FC<SceneComponentProps> = ({scene, theme}) => {
	const ctaText = typeof scene.payload.ctaText === 'string' ? scene.payload.ctaText : '';

	return (
		<Shell theme={theme}>
			<div style={{textAlign: 'center'}}>
				<h2 style={{fontSize: 60, color: theme.accent}}>Xpress Digital Academy</h2>
				{ctaText ? <p style={{fontSize: 36, marginTop: 20}}>{ctaText}</p> : null}
			</div>
		</Shell>
	);
};
