import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';

import {resolveImageSrc} from './resolveImage';
import type {SceneComponentProps} from './types';
import {Shell} from './Shell';

/**
 * PLACEHOLDER. Prompt 1 item 5 asks for real hand-drawn animation: SVG
 * stroke-dashoffset driven by interpolate(useCurrentFrame(), ...) so
 * line art draws itself, with a hand PNG riding the pen tip via
 * getPointAtLength(), and potrace tracing for raster source art (with a
 * path-order warning, since traced paths often draw in a nonsense
 * order). That needs real SVG path data to animate against — none
 * exists yet (no whiteboard art has been supplied to trace), so this
 * scene type currently does a plain image wipe-reveal instead of the
 * real stroke animation. Swap this component's body, not its type
 * signature, once traced SVGs exist — everything upstream (payload
 * shape, calculateMetadata, the dispatcher in scenes/index.tsx) already
 * treats whiteboardDiagram as its own scene type.
 */
export const WhiteboardDiagram: React.FC<SceneComponentProps> = ({scene, theme}) => {
	const frame = useCurrentFrame();
	const reveal = interpolate(frame, [0, 45], [0, 100], {extrapolateRight: 'clamp'});
	const imageSrc = resolveImageSrc(scene);

	return (
		<Shell theme={theme}>
			<div
				style={{
					position: 'relative',
					width: '100%',
					height: '70%',
					overflow: 'hidden',
					borderRadius: 16,
					border: `4px solid ${theme.accent}`,
				}}
			>
				{imageSrc ? (
					<img
						src={imageSrc}
						alt={typeof scene.payload.alt === 'string' ? scene.payload.alt : ''}
						style={{
							width: '100%',
							height: '100%',
							objectFit: 'contain',
							clipPath: `inset(0 ${100 - reveal}% 0 0)`,
						}}
					/>
				) : null}
			</div>
		</Shell>
	);
};
