import React from 'react';
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';

import {resolveImageSrc} from './resolveImage';
import type {SceneComponentProps} from './types';

export const FullImage: React.FC<SceneComponentProps> = ({scene, theme}) => {
	const frame = useCurrentFrame();
	const {durationInFrames} = useVideoConfig();
	const caption = typeof scene.payload.caption === 'string' ? scene.payload.caption : '';
	const imageSrc = resolveImageSrc(scene);

	// Slow Ken Burns drift rather than a static photo — the same idea
	// Prompt 3's per-listing ffmpeg pipeline uses for a reason: a
	// perfectly still full-bleed image reads as a frozen slide, a slow
	// drift reads as produced.
	const scale = interpolate(frame, [0, durationInFrames], [1, 1.08], {extrapolateRight: 'clamp'});

	return (
		<AbsoluteFill style={{backgroundColor: theme.background}}>
			{imageSrc ? (
				<Img
					src={imageSrc}
					style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${scale})`}}
					alt={typeof scene.payload.alt === 'string' ? scene.payload.alt : ''}
				/>
			) : null}
			{caption ? (
				<div
					style={{
						position: 'absolute',
						bottom: '6%',
						left: '8%',
						right: '8%',
						fontSize: 34,
						color: '#fff',
						textShadow: '0 2px 8px rgba(0,0,0,0.6)',
						fontFamily: theme.fontFamily,
					}}
				>
					{caption}
				</div>
			) : null}
		</AbsoluteFill>
	);
};
