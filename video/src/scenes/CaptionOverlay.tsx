import React, {useMemo} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {createTikTokStyleCaptions} from '@remotion/captions';
import type {Caption} from '@remotion/captions';

/**
 * Real burnt-in captions — Prompt 1 item 7: "Nigerian students watch on
 * cheap phones with sound off," so every scene needs its narration on
 * screen, not just its audio track. Driven by actual whisper.cpp
 * word-level timestamps (scripts/render-lesson.mjs transcribes each
 * scene's real generated audio before render — see that file), grouped
 * into short pages via @remotion/captions' own TikTok-style grouping
 * rather than showing one word at a time or the whole sentence at once.
 *
 * Renders nothing if `captions` is empty — a scene whose transcription
 * failed or was skipped still plays, just without a caption bar (see
 * ResolvedScene's comment in src/types.ts).
 */
export const CaptionOverlay: React.FC<{captions: Caption[]}> = ({captions}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const currentMs = (frame / fps) * 1000;

	const {pages} = useMemo(
		() => createTikTokStyleCaptions({captions, combineTokensWithinMilliseconds: 1200}),
		[captions]
	);

	if (pages.length === 0) return null;

	const activePage = pages.find((page) => currentMs >= page.startMs && currentMs < page.startMs + page.durationMs);
	if (!activePage) return null;

	return (
		<div
			style={{
				position: 'absolute',
				left: '6%',
				right: '6%',
				bottom: '6%',
				textAlign: 'center',
			}}
		>
			<span
				style={{
					display: 'inline-block',
					padding: '10px 22px',
					borderRadius: 10,
					backgroundColor: 'rgba(0,0,0,0.72)',
					color: '#fff',
					fontSize: 34,
					fontWeight: 600,
					fontFamily: '"Segoe UI", sans-serif',
					lineHeight: 1.3,
				}}
			>
				{activePage.text.trim()}
			</span>
		</div>
	);
};
