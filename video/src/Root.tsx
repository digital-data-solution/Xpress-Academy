import React from 'react';
import {Composition, registerRoot} from 'remotion';

import {calculateMetadata, calculateTeaserMetadata, LessonVideo} from './Composition';
import {compositionPropsSchema} from './types';
import sampleLesson from '../samples/what-is-rabies.json';

// Real defaultProps, not placeholders — this is what
// `manage.py export_lesson_video_json <lesson_id>` actually emits for a
// real lesson (see video/samples/what-is-rabies.json and its own
// comment), so Remotion Studio opens showing real content per Prompt
// 1's deliverables, not an empty frame.
const defaultProps = compositionPropsSchema.parse({...sampleLesson, voiceProvider: 'kokoro', voiceId: ''});

const Root: React.FC = () => (
	<>
		<Composition
			id="LessonVideo"
			component={LessonVideo}
			schema={compositionPropsSchema}
			defaultProps={defaultProps}
			calculateMetadata={calculateMetadata}
			width={1920}
			height={1080}
			// fps/durationInFrames come from calculateMetadata (measured
			// audio) — these are just Composition's required placeholders
			// before that resolves.
			fps={30}
			durationInFrames={900}
		/>
		<Composition
			id="LessonVideoTeaser"
			component={LessonVideo}
			schema={compositionPropsSchema}
			defaultProps={defaultProps}
			calculateMetadata={calculateTeaserMetadata}
			width={1080}
			height={1920}
			fps={30}
			durationInFrames={900}
		/>
	</>
);

registerRoot(Root);
