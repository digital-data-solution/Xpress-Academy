import type React from 'react';

import type {SceneType} from '../types';
import {BulletReveal} from './BulletReveal';
import {EvidenceCard} from './EvidenceCard';
import {FullImage} from './FullImage';
import {OutroCard} from './OutroCard';
import {TitleCard} from './TitleCard';
import type {SceneComponentProps} from './types';
import {WhiteboardDiagram} from './WhiteboardDiagram';
import {WorkedExample} from './WorkedExample';

export const SCENE_COMPONENTS: Record<SceneType, React.FC<SceneComponentProps>> = {
	titleCard: TitleCard,
	bulletReveal: BulletReveal,
	whiteboardDiagram: WhiteboardDiagram,
	fullImage: FullImage,
	workedExample: WorkedExample,
	evidenceCard: EvidenceCard,
	outroCard: OutroCard,
};
