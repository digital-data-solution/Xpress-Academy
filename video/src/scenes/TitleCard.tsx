import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

import type {SceneComponentProps} from './types';
import {Shell} from './Shell';

export const TitleCard: React.FC<SceneComponentProps> = ({scene, theme}) => {
	const frame = useCurrentFrame();
	const heading = typeof scene.payload.heading === 'string' ? scene.payload.heading : '';
	const subheading = typeof scene.payload.subheading === 'string' ? scene.payload.subheading : '';
	const opacity = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'});

	return (
		<Shell theme={theme}>
			<div style={{opacity, textAlign: 'center'}}>
				<h1 style={{fontSize: 88, fontWeight: 800, margin: 0, color: theme.accent}}>{heading}</h1>
				{subheading ? <p style={{fontSize: 40, marginTop: 24}}>{subheading}</p> : null}
			</div>
		</Shell>
	);
};
