import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

import type {SceneComponentProps} from './types';
import {Shell} from './Shell';

/** Same even-spread placeholder cadence as BulletReveal (see its
 * comment) — steps here are meant to fire on the word that introduces
 * each step once whisper.cpp word timestamps are wired in. */
export const WorkedExample: React.FC<SceneComponentProps> = ({scene, theme}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const steps: string[] = Array.isArray(scene.payload.steps)
		? (scene.payload.steps as unknown[]).filter((s): s is string => typeof s === 'string')
		: [];
	const problem = typeof scene.payload.problem === 'string' ? scene.payload.problem : '';

	const perStep = steps.length > 0 ? durationInFrames / steps.length : durationInFrames;

	return (
		<Shell theme={theme}>
			{problem ? (
				<p style={{fontSize: 44, fontWeight: 600, marginBottom: 32, color: theme.accent}}>{problem}</p>
			) : null}
			<ol style={{fontSize: 38, lineHeight: 1.7, paddingLeft: 32}}>
				{steps.map((step, i) => {
					const revealFrame = i * perStep;
					const opacity = interpolate(frame, [revealFrame, revealFrame + 12], [0, 1], {
						extrapolateLeft: 'clamp',
						extrapolateRight: 'clamp',
					});
					return (
						<li key={i} style={{opacity, marginBottom: 18}}>
							{step}
						</li>
					);
				})}
			</ol>
		</Shell>
	);
};
