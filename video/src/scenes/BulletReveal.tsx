import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

import type {SceneComponentProps} from './types';
import {Shell} from './Shell';

/**
 * Reveals one bullet at a time, evenly spread across the scene's
 * measured duration. This is a placeholder cadence — Prompt 1 item 4
 * calls for each bullet firing on the actual WORD that introduces it,
 * via local whisper.cpp word timestamps (@remotion/install-whisper-cpp)
 * feeding this component instead of an even spread. That's a real,
 * separate build (a transcription step ahead of render) not done in
 * this pass — tracked as follow-up, not silently downgraded.
 */
export const BulletReveal: React.FC<SceneComponentProps> = ({scene, theme}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const bullets: string[] = Array.isArray(scene.payload.bullets)
		? (scene.payload.bullets as unknown[]).filter((b): b is string => typeof b === 'string')
		: [];
	const heading = typeof scene.payload.heading === 'string' ? scene.payload.heading : '';

	const perBullet = bullets.length > 0 ? durationInFrames / bullets.length : durationInFrames;

	return (
		<Shell theme={theme}>
			{heading ? <h2 style={{fontSize: 56, color: theme.accent, marginBottom: 32}}>{heading}</h2> : null}
			<ul style={{listStyle: 'none', padding: 0, margin: 0, fontSize: 42, lineHeight: 1.6}}>
				{bullets.map((bullet, i) => {
					const revealFrame = i * perBullet;
					const opacity = interpolate(frame, [revealFrame, revealFrame + 12], [0, 1], {
						extrapolateLeft: 'clamp',
						extrapolateRight: 'clamp',
					});
					const translateY = interpolate(frame, [revealFrame, revealFrame + 12], [16, 0], {
						extrapolateLeft: 'clamp',
						extrapolateRight: 'clamp',
					});
					return (
						<li key={i} style={{opacity, transform: `translateY(${translateY}px)`, marginBottom: 20}}>
							{theme.register === 'clinical' ? `${i + 1}. ` : '• '}
							{bullet}
						</li>
					);
				})}
			</ul>
		</Shell>
	);
};
