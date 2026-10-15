import React from 'react';
import {AbsoluteFill, Audio, Easing, interpolate, Sequence, spring, staticFile, useCurrentFrame} from 'remotion';
import {Character, Expression, Pose, Viseme} from '../Character';
import {Beat, Props, Scene} from '../shared';
import {Backdrop, Captions} from './Backdrop';
import {LayoutProps, cl} from './kit';
import {BigNumber, Compare, HeroWord, ListStack, MascotCloseup, Quote, Steps} from './LayoutsText';
import {Chat, Chips, DeviceMock, NodeGraph, RepoCard, StarMeter, Terminal} from './LayoutsData';
import {DocStamp, HookStack, Recap} from './LayoutsStory';
import {DEFAULT_VARIANT, FONT, PALETTES, Palette, STAGE, Variant, punch} from './tokens';

const LAYOUTS: Record<string, React.FC<LayoutProps>> = {heroWord: HeroWord, bigNumber: BigNumber, quote: Quote, mascotCloseup: MascotCloseup, listStack: ListStack,
  steps: Steps, compare: Compare, repoCard: RepoCard, terminal: Terminal, chips: Chips, starMeter: StarMeter, deviceMock: DeviceMock, chat: Chat, nodeGraph: NodeGraph,
  hookStack: HookStack, docStamp: DocStamp, recap: Recap};
const TEXT_FORWARD = new Set(['heroWord', 'quote', 'hookStack', 'loop', 'mascotCloseup']);
const DEICTIC = new Set(['repoCard', 'terminal', 'deviceMock', 'starMeter', 'chips', 'nodeGraph', 'docStamp', 'chat', 'steps', 'listStack', 'bigNumber']);
const T = 9;  // transition length in frames

type GBeat = Beat & {scene: Scene; si: number; bi: number; start: number; end: number; hit: number | null};

const flatten = (scenes: Scene[], fps: number): GBeat[] => {
  const out: GBeat[] = [];
  scenes.forEach((scene, si) => {
    const beats = scene.beats?.length ? scene.beats : [{s: 0, e: scene.frames / fps, w: [0, 0], text: scene.narration, focus: scene.emphasis || scene.heading, layout: 'listStack', anchor: 'right', transition: 'cut', punch: false} as Beat];
    beats.forEach((beat, bi) => {
      const start = scene.from + Math.round(beat.s * fps);
      const end = bi < beats.length - 1 ? scene.from + Math.round(beats[bi + 1].s * fps) : scene.from + scene.frames;
      const key = (scene.emphasis ?? '').toLowerCase().split(/\s+/)[0];
      const word = beat.punch && key ? (scene.words ?? []).slice(beat.w[0], beat.w[1] + 1).find(w => w.w.toLowerCase().includes(key)) : undefined;
      out.push({...beat, scene, si, bi, start, end, hit: word ? Math.round(word.s * fps) - Math.round(beat.s * fps) : null});
    });
  });
  return out;
};

const transitionStyle = (kind: string, p: number, dir: 'in' | 'out'): React.CSSProperties => {
  const e = Easing.inOut(Easing.cubic)(p);
  if (kind === 'whip') return dir === 'in' ? {transform: `translateX(${(1 - e) * 1080}px)`, filter: `blur(${(1 - e) * 22}px)`} : {transform: `translateX(${-e * 1080}px)`, filter: `blur(${e * 22}px)`};
  if (kind === 'zoom') return dir === 'in' ? {transform: `scale(${1.6 - .6 * Easing.out(Easing.exp)(p)})`, opacity: e} : {transform: `scale(${1 - .2 * e})`, opacity: 1 - e};
  if (kind === 'push') return dir === 'in' ? {transform: `translateY(${(1 - e) * 1400}px)`} : {transform: `translateY(${-e * 500}px)`, opacity: 1 - e * .8};
  if (kind === 'mask') return dir === 'in' ? {clipPath: `circle(${e * 150}% at 50% 40%)`} : {};
  return {};
};

const BeatView: React.FC<{b: GBeat; next?: GBeat; props: Props; P: Palette; v: Variant; first: GBeat; pre?: number}> = ({b, next, props, P, v, first, pre = 0}) => {
  const f = useCurrentFrame() - pre;
  const dur = b.end - b.start;
  const tin = b.transition === 'cut' || b.start === 0 ? {} : transitionStyle(b.transition, interpolate(f, [0, T], [0, 1], cl), 'in');
  const tout = next && next.transition !== 'cut' && f > dur ? transitionStyle(next.transition, interpolate(f, [dur, dur + T], [0, 1], cl), 'out') : {};
  if (next && next.transition === 'cut' && f >= dur) return null;
  const cutPunch = b.transition === 'cut' && b.start > 0 ? interpolate(f, [0, 6], [1.06, 1], {...cl, easing: Easing.out(Easing.cubic)}) : 1;
  const push = 1 + .05 * v.camera * Math.min(1, f / Math.max(1, dur));
  const k = punch(f, b.hit ?? -99, .07 * v.camera);
  const isLoop = b.layout === 'loop';
  const L = LAYOUTS[isLoop ? first.layout : b.layout] ?? ListStack;
  const lp: LayoutProps = isLoop ? {beat: first, scene: first.scene, props, P, v, index: 0, hit: null, dur} : {beat: b, scene: b.scene, props, P, v, index: b.si, hit: b.hit, dur};
  return <AbsoluteFill style={{...tin, ...tout}}>
    {b.transition === 'mask' && <Backdrop P={P} kind={v.background} shift={{x: 0, y: 0}}/>}
    <AbsoluteFill style={{transform: `scale(${push * k * cutPunch})`, transformOrigin: '50% 42%'}}>
      <div style={{position: 'absolute', left: STAGE.left, top: STAGE.top, width: STAGE.width, height: STAGE.height}}><L {...lp}/></div>
    </AbsoluteFill>
  </AbsoluteFill>;
};

const ANCHORS: Record<string, {x: number; y: number; w: number}> = {
  right: {x: 560, y: 1265, w: 470}, left: {x: 40, y: 1265, w: 470}, center: {x: 170, y: 560, w: 740}, peek: {x: 640, y: 1400, w: 400},
};

const poseFor = (b: GBeat, beats: GBeat[]): Pose => {
  if (b.layout === 'loop' || b.layout === 'recap') return 'thumbs';
  if (b.start === 0) return 'wave';
  if (/\?$/.test(b.text.trim())) return 'shrug';
  if (DEICTIC.has(b.layout)) return b.anchor === 'left' ? 'pointRight' : 'point';
  if (/\d/.test(b.focus)) return 'count';
  return beats.indexOf(b) % 2 ? 'present' : 'rest';
};

export const StudioVideo: React.FC<Props> = props => {
  const frame = useCurrentFrame();
  const fps = 30;
  const v: Variant = {...DEFAULT_VARIANT, ...(props.variant ?? {})};
  const P = PALETTES[v.palette] ?? PALETTES['paper-red'];
  const beats = flatten(props.scenes, fps);
  let ai = 0;
  beats.forEach((b, i) => { if (frame >= b.start) ai = i; });
  const cur = beats[ai], prev = beats[ai - 1];
  const scene = cur.scene;
  const local = frame - scene.from;
  const since = frame - cur.start;

  // Character direction: anchor travel, gesture strokes led ~5f before the beat, motivated blinks, nods on stresses.
  const travel = spring({frame: since, fps, config: {damping: 16, stiffness: 110}});
  const A = ANCHORS[cur.anchor] ?? ANCHORS.right, B = ANCHORS[prev?.anchor ?? cur.anchor] ?? A;
  const moving = prev && prev.anchor !== cur.anchor;
  const pos = {x: B.x + (A.x - B.x) * travel, y: B.y + (A.y - B.y) * travel - (moving ? Math.sin(Math.PI * Math.min(1, travel)) * 60 : 0), w: B.w + (A.w - B.w) * travel};
  const squash = moving ? 1 - .05 * Math.sin(Math.PI * Math.min(1, travel * 1.2)) : 1;
  const pose = poseFor(cur, beats);
  const relax = !DEICTIC.has(cur.layout) && pose !== 'thumbs' && since > 40;
  const nextB = beats[ai + 1];
  const anticipating = nextB && nextB.start - frame <= 5;
  const target: Pose = anticipating ? poseFor(nextB, beats) : relax ? 'rest' : pose;
  const from: Pose = anticipating ? (relax ? 'rest' : pose) : relax ? pose : prev ? poseFor(prev, beats) : 'rest';
  const strokeStart = anticipating ? nextB.start - 5 : relax ? cur.start + 40 : cur.start - 5;
  const poseT = spring({frame: frame - strokeStart, fps, config: {damping: 15, stiffness: 140}});
  const lookTo = cur.anchor === 'left' ? {x: 1, y: -1} : cur.anchor === 'center' ? {x: 0, y: .4} : {x: -1, y: -1};
  const lookFrom = prev ? (prev.anchor === 'left' ? {x: 1, y: -1} : prev.anchor === 'center' ? {x: 0, y: .4} : {x: -1, y: -1}) : lookTo;
  const dart = spring({frame: since, fps, config: {damping: 30, stiffness: 520}});
  const look = {x: lookFrom.x + (lookTo.x - lookFrom.x) * dart, y: lookFrom.y + (lookTo.y - lookFrom.y) * dart};
  const seedNum = [...v.seed].reduce((n, c) => n + c.charCodeAt(0), 0) % 97;
  const blinks = beats.map(b => b.start).concat(Array.from({length: Math.ceil(props.durationInFrames / 60)}, (_, i) => i * 105 + ((i * 37 + seedNum) % 50)));
  const lastBlink = Math.max(-99, ...blinks.filter(x => x <= frame));
  const hits = beats.flatMap(b => b.hit !== null ? [b.start + b.hit] : []).concat(beats.map(b => b.start + 2));
  const nod = Math.max(0, ...hits.map(h => frame - (h - 2)).filter(t => t >= 0 && t < 10).map(t => Math.sin(t / 10 * Math.PI)));
  const visemes = scene.visemes ?? [];
  let vis: Viseme = 'X';
  for (const [fr, shape] of visemes) { if (fr <= local) vis = shape as Viseme; else break; }
  const audioDone = local > (scene.audioFrames ?? scene.frames);
  const expression: Expression = audioDone || cur.layout === 'loop' ? 'happy' : cur.punch && since < 40 ? 'smug' : 'talk';

  const count = props.scenes.filter(s => (s.item ?? 0) > 0).length;
  const item = scene.item ?? 0;
  const doneItems = props.scenes.filter(s => (s.item ?? 0) > 0 && frame >= s.from + 18).length;
  return <AbsoluteFill style={{background: P.bg, overflow: 'hidden'}}>
    <Backdrop P={P} kind={v.background} shift={{x: -pos.x * .1, y: 0}}/>
    {beats.map((b, i) => {
      // The opening beat starts its animation 44 frames "early" so frame 0 (the cover and the hook) is already fully composed.
      const pre = i === 0 ? 44 : 0;
      return <Sequence key={i} from={b.start - pre} durationInFrames={b.end - b.start + T + pre}>
        <BeatView b={b} next={beats[i + 1]} props={props} P={P} v={v} first={beats[0]} pre={pre}/>
      </Sequence>;
    })}
    {count > 0 && <div style={{position: 'absolute', left: 120, right: 120, top: 292, display: 'flex', alignItems: 'center', gap: 16}}>
      <span style={{fontFamily: FONT.mono, fontSize: 24, color: P.muted, letterSpacing: 2, width: 190}}>{(props.series || 'ITEMS').slice(0, 8)} <b style={{color: P.accent}}>{item || (doneItems === count ? count : 0)}</b>/{count}</span>
      {Array.from({length: count}, (_, i) => <span key={i} style={{flex: 1, height: 12, borderRadius: 6, background: i < doneItems ? P.accent : P.line, transition: 'none'}}/>)}
    </div>}
    {!TEXT_FORWARD.has(cur.layout) && <Captions scene={scene} beat={cur} local={local} P={P} v={v}/>}
    <div style={{position: 'absolute', left: pos.x, top: pos.y, transform: `scale(1, ${squash})`, transformOrigin: 'bottom'}}>
      <Character width={pos.w} mouth={scene.mouth?.[local] ?? 0} viseme={audioDone ? 'X' : vis} pose={target} prevPose={from} poseT={poseT}
        expression={expression} look={look} accent={P.accent} hoodie={v.outfit} hair={v.hair} emphasis={!!cur.hit && since >= cur.hit - 4 && since < cur.hit + 24}
        nod={nod} blink={frame - lastBlink} seed={seedNum}/>
    </div>
    {props.scenes.map((s, i) => <Sequence key={i} from={s.from} durationInFrames={s.frames}>
      {s.audio && <Audio src={staticFile(s.audio)}/>}
      {s.uiAudio && <Audio src={staticFile(s.uiAudio)} volume={.55}/>}
    </Sequence>)}
    {props.music && <Audio src={staticFile(props.music)}/>}
  </AbsoluteFill>;
};
