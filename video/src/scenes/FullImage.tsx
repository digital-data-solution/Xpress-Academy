import React from 'react';
import {AbsoluteFill, Img} from 'remotion';

import type {SceneComponentProps} from './types';

export const FullImage: React.FC<SceneComponentProps> = ({scene, theme}) => {
	const caption = typeof scene.payload.caption === 'string' ? scene.payload.caption : '';

	return (
		<AbsoluteFill style={{backgroundColor: theme.background}}>
			{scene.image ? (
				<Img
					src={scene.image}
					style={{width: '100%', height: '100%', objectFit: 'cover'}}
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
