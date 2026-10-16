import React from 'react';
import {AbsoluteFill, Composition, registerRoot, Sequence} from 'remotion';
import {Character, Expression, Pose, Viseme} from './Character';
import {Props, ShotProps, Style} from './shared';
import {EditorialShot} from './styles/Editorial';
import {FieldnotesShot} from './styles/Fieldnotes';
import {KineticShot} from './styles/Kinetic';
import {MascotShot} from './styles/MascotScene';
import {PaperVideo} from './paper/PaperVideo';
import {StudioVideo} from './studio/StudioVideo';
import {BlobSheet, PremiumVideo} from './premium/PremiumVideo';
import {DevMimoIntro, DevMimoPoster, MimoSheet} from './devmimo/DevMimoIntro';
import {DevMimoLogo} from './devmimo/Logo';
import {IntroProps} from './devmimo/theme';

const shots: Record<Exclude<Style, 'paper' | 'studio' | 'premium'>, React.FC<ShotProps>> = {editorial: EditorialShot, kinetic: KineticShot, mascot: MascotShot, fieldnotes: FieldnotesShot};

const Video: React.FC<Props> = props => {
  if (props.style === 'paper') return <PaperVideo {...props}/>;
  if (props.style === 'studio') return <StudioVideo {...props}/>;
  if (props.style === 'premium') return <PremiumVideo {...props}/>;
  const Shot = shots[props.style ?? 'fieldnotes'] ?? FieldnotesShot;
  return <AbsoluteFill>{props.scenes.map((scene, index) => <Sequence key={index} from={scene.from} durationInFrames={scene.frames}><Shot scene={scene} index={index} total={props.scenes.length} brand={props.brand ?? 'FIELDNOTES'}/></Sequence>)}</AbsoluteFill>;
};
const defaults: Props = {title: 'Ideas, made clear.', style: 'editorial', brand: 'FIELDNOTES', fps: 30, width: 1080, height: 1920, durationInFrames: 150, scenes: [{heading: 'The signal behind the story', narration: 'The best ideas become clear when you know what to look for.', caption: 'The best ideas become clear when you know what to look for.', points: ['Find the useful detail', 'See what changes'], visual: 'cards', emphasis: 'clear', audio: '', frames: 150, from: 0}]};
const sheet: [Pose, Expression, Viseme, {x: number; y: number}][] = [['wave', 'happy', 'X', {x: 0, y: .2}], ['point', 'talk', 'C', {x: -1, y: -1}], ['present', 'talk', 'D', {x: -.8, y: 0}],
  ['thumbs', 'smug', 'B', {x: .5, y: .3}], ['shrug', 'surprised', 'F', {x: 0, y: -.5}], ['count', 'talk', 'E', {x: .9, y: -.8}]];
const CharacterSheet = () => <AbsoluteFill style={{background: '#ebe8e1', flexDirection: 'row', flexWrap: 'wrap', padding: 30, gap: 10}}>
  {sheet.map(([pose, expression, viseme, look], i) => <div key={i} style={{width: 640, height: 940, display: 'flex', alignItems: 'flex-end', justifyContent: 'center', overflow: 'hidden'}}>
    <Character width={560} mouth={.7} pose={pose} expression={expression} viseme={viseme} look={look} seed={i}/>
  </div>)}
</AbsoluteFill>;
const introDefaults: IntroProps = {fps: 30, durationInFrames: 900, scenes: [], mouth: []};
const DevMimoCompositions = () => <>
  <Composition id="DevMimoIntro" component={DevMimoIntro} defaultProps={introDefaults} durationInFrames={900} fps={30} width={1080} height={1920}
    calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames, fps: props.fps})}/>
  <Composition id="DevMimoLogo" component={DevMimoLogo} durationInFrames={150} fps={30} width={1080} height={1920}/>
  <Composition id="DevMimoPoster" component={DevMimoPoster} durationInFrames={1} fps={30} width={1080} height={1920}/>
  <Composition id="MimoSheet" component={MimoSheet} durationInFrames={1} fps={30} width={1440} height={1240}/>
</>;
const Root = () => <><DevMimoCompositions/><Composition id="BlobSheet" component={BlobSheet} durationInFrames={60} fps={30} width={1440} height={1240}/><Composition id="CharacterSheet" component={CharacterSheet} durationInFrames={120} fps={30} width={2000} height={2000}/><Composition id="Explainer" component={Video} defaultProps={defaults} durationInFrames={150} fps={30} width={1080} height={1920} calculateMetadata={({props}) => ({durationInFrames: props.durationInFrames, fps: props.fps, width: props.width, height: props.height})}/></>;
registerRoot(Root);
