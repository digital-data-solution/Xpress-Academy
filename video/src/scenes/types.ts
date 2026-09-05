import type {ResolvedScene, Track} from '../types';
import type {TrackTheme} from '../theme';

export type SceneComponentProps = {
	scene: ResolvedScene;
	track: Track;
	theme: TrackTheme;
};
