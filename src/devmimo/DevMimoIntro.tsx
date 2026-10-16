import React from 'react';
import {AbsoluteFill, interpolate, Sequence, useCurrentFrame} from 'remotion';
import {ensureFonts} from '../premium/tokens';
import {Backdrop} from './Backdrop';
import {LogoMark} from './Logo';
import {Mimo, MimoExpr} from './Mimo';
import {BuildScene, HookScene, NoFluffScene, OutroScene, RevealScene, SceneProps, TopicsScene} from './Scenes';
import {DM, FONT, IntroProps, rand} from './theme';

/* DevMimo intro: six scenes timed by examples/devmimo/build_intro.py from the real Kokoro narration (props.scenes[].from/frames/words),
   Mimo's mouth driven by the narration loudness (props.mouth, one value per frame). Audio is mixed and mastered outside Remotion
   against the same frame numbers. */

const SCENES: Record<string, React.FC<SceneProps>> = {hook: HookScene, reveal: RevealScene, build: BuildScene, topics: TopicsScene, nofluff: NoFluffScene, outro: OutroScene};
const KEY: Record<string, [number, number]> = {hook: [50, 36], reveal: [50, 62], build: [60, 48], topics: [50, 50], nofluff: [50, 40], outro: [50, 42]};

const SlabWipe: React.FC<{g: number; at: number}> = ({g, at}) => {
  if (g < at - 9 || g > at + 9) return null;
  const x = interpolate(g, [at - 9, at + 9], [-2600, 2600]);
  return <AbsoluteFill style={{pointerEvents: 'none'}}>
    <div style={{position: 'absolute', left: -500, top: -600, width: 2080, height: 3120, transform: `translateX(${x}px) rotate(14deg)`, display: 'flex'}}>
      <div style={{width: 260, background: DM.orangeHot}}/><div style={{flex: 1, background: DM.orange}}/><div style={{width: 200, background: DM.charcoal2}}/>
    </div>
  </AbsoluteFill>;
};

export const DevMimoIntro: React.FC<IntroProps> = props => {
  ensureFonts();
  const g = useCurrentFrame();
  const scenes = props.scenes;
  const current = scenes.find(s => g >= s.from && g < s.from + s.frames) ?? scenes[scenes.length - 1];
  const [kx, ky] = current ? KEY[current.kind] ?? [50, 45] : [50, 45];
  const mouth = props.mouth[g] ?? 0;
  const build = scenes.find(s => s.kind === 'build');
  return <AbsoluteFill style={{background: DM.charcoal}}>
    <Backdrop f={g} keyX={kx} keyY={ky} intensity={current?.kind === 'reveal' ? 1.2 : .7}/>
    <Ambient g={g}/>
    {scenes.map((s, i) => {
      const Comp = SCENES[s.kind];
      const next = scenes[i + 1];
      const overhang = next?.kind === 'outro' ? 16 : 0;      // the outro's iris opens over this scene
      return Comp ? <Sequence key={s.id} from={s.from} durationInFrames={s.frames + overhang} layout="none">
        <SceneFrame scene={s} Comp={Comp} mouth={mouth}/>
      </Sequence> : null;
    })}
    {build && <SlabWipe g={g} at={build.from}/>}
  </AbsoluteFill>;
};

const DRIFT = new Set(['build', 'topics', 'nofluff', 'outro']);
const SceneFrame: React.FC<{scene: IntroProps['scenes'][number]; Comp: React.FC<SceneProps>; mouth: number}> = ({scene, Comp, mouth}) => {
  const f = useCurrentFrame();
  // slow camera push so no beat sits dead still once its graphic has landed
  const z = DRIFT.has(scene.kind) ? 1 + .045 * Math.min(1, f / scene.frames) : 1;
  return <AbsoluteFill style={{transform: `scale(${z})`, transformOrigin: '50% 45%'}}><Comp scene={scene} f={f} mouth={mouth}/></AbsoluteFill>;
};

const GLYPHS = ['</>', '{ }', '>_', ';', '=>', '//', '()', '#'];
/** Ambient code glyphs drifting up behind everything: depth and constant, quiet motion. */
const Ambient: React.FC<{g: number}> = ({g}) => <AbsoluteFill style={{pointerEvents: 'none'}}>
  {Array.from({length: 16}, (_, i) => {
    const speed = .8 + rand(i) * 1.6, size = 34 + rand(i + 4) * 40;
    const y = 2050 - ((g * speed + rand(i + 8) * 2200) % 2300);
    const x = rand(i + 12) * 1000 + Math.sin(g / 40 + i) * 30;
    return <div key={i} style={{position: 'absolute', left: x, top: y, fontFamily: FONT.mono, fontWeight: 700, fontSize: size,
      color: i % 3 === 0 ? DM.orange : DM.ivory, opacity: .07 + rand(i + 20) * .1, transform: `rotate(${Math.sin(g / 50 + i) * 12}deg)`}}>{GLYPHS[i % GLYPHS.length]}</div>;
  })}
</AbsoluteFill>;

/** Reel cover (1080x1920). Key content sits inside the centred 4:5 grid crop (y 285–1635). */
export const DevMimoPoster: React.FC = () => {
  ensureFonts();
  return <AbsoluteFill style={{background: DM.charcoal}}>
    <Backdrop f={0} keyX={50} keyY={66} intensity={1.3}/>
    <AbsoluteFill style={{opacity: .8, background: 'repeating-conic-gradient(from 0deg at 50% 70%, rgba(255,122,26,.10) 0deg 7deg, transparent 7deg 20deg)',
      maskImage: 'radial-gradient(circle at 50% 70%, black 10%, transparent 55%)', WebkitMaskImage: 'radial-gradient(circle at 50% 70%, black 10%, transparent 55%)'}}/>
    <div style={{position: 'absolute', top: 330, left: 0, right: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 22}}>
      <LogoMark size={86}/>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 64, letterSpacing: '-0.03em'}}><span style={{color: DM.ivory}}>Dev</span><span style={{color: DM.orange}}>Mimo</span></div>
    </div>
    <div style={{position: 'absolute', top: 470, left: 0, right: 0, textAlign: 'center'}}>
      <div style={{fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 160, color: DM.ivory, lineHeight: 1}}>Meet</div>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 300, color: DM.orange, letterSpacing: '-0.045em', lineHeight: .92}}>Mimo.</div>
      <div style={{fontFamily: FONT.mono, fontWeight: 500, fontSize: 40, letterSpacing: '0.16em', color: DM.ivorySoft, marginTop: 26}}>REAL DEV BUILDS, EXPLAINED</div>
    </div>
    <div style={{position: 'absolute', left: 540 - 270, top: 1620 - 540 * 1.2, width: 540}}>
      <Mimo size={540} frame={14} wave={1} expression="happy" autoBlink={false}/>
    </div>
  </AbsoluteFill>;
};

/** Inspection sheet for the mascot (npx remotion still src/index.tsx MimoSheet). */
export const MimoSheet: React.FC = () => {
  ensureFonts();
  const poses: [MimoExpr, number, number, number][] = [['neutral', 0, 0, 10], ['happy', 1, 0, 14], ['surprised', 0, 0, 10], ['wink', .6, .5, 22], ['focused', 0, 0, 10], ['neutral', 0, .9, 3]];
  return <AbsoluteFill style={{background: DM.charcoal, flexDirection: 'row', flexWrap: 'wrap', padding: 40, gap: 20}}>
    {poses.map(([e, wave, mouth, frame], i) => <div key={i} style={{width: 440, height: 560, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end'}}>
      <Mimo size={360} frame={frame} wave={wave} mouth={mouth} expression={e} autoBlink={false}/>
      <div style={{fontFamily: FONT.mono, color: DM.muted, fontSize: 26, marginTop: 6}}>{e}{wave ? ' · wave' : ''}{mouth ? ' · talk' : ''}</div>
    </div>)}
  </AbsoluteFill>;
};
