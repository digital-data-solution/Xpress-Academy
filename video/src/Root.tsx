import React from 'react';
import {Composition, registerRoot} from 'remotion';

import {calculateMetadata, calculateTeaserMetadata, LessonVideo} from './Composition';
import {compositionPropsSchema, type CompositionProps} from './types';
import sampleLesson from '../samples/rabies-module-301.json';

// Real defaultProps, not placeholders — this is exactly what
// `manage.py export_lesson_video_json 301` emitted for the real
// authored "Etiology and Epidemiology" lesson (see
// video/samples/rabies-module-301.json), so Remotion Studio opens
// showing real content per Prompt 1's deliverables, not an empty frame.
//
// Cast, not assert-free: compositionPropsSchema.parse()'s own inferred
// return type has `captions?: unknown[]` (zod can't know we want that
// narrowed to @remotion/captions' Caption[] — see the comment on Scene
// in src/types.ts for why that narrowing lives outside the zod schema).
// The cast is safe here because defaultProps never carries real
// captions anyway (Studio's sample has none until render-lesson.mjs's
// prepare step runs against it).
const defaultProps = compositionPropsSchema.parse({
	...sampleLesson,
	voiceProvider: 'kokoro',
	voiceId: '',
}) as CompositionProps;

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
