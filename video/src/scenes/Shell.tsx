import React from 'react';
import {AbsoluteFill} from 'remotion';

import type {TrackTheme} from '../theme';

/** Common chrome every scene sits inside: background/text color and
 * font come from the track theme (src/theme.ts), so no scene component
 * below repeats "if track === 'VET' use teal" logic itself. */
export const Shell: React.FC<{theme: TrackTheme; children: React.ReactNode}> = ({theme, children}) => (
	<AbsoluteFill
		style={{
			backgroundColor: theme.background,
			color: theme.text,
			fontFamily: theme.fontFamily,
			padding: '6% 8%',
			justifyContent: 'center',
		}}
	>
		{children}
	</AbsoluteFill>
);
