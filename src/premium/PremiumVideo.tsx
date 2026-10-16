import React from 'react';
import {AbsoluteFill, Audio, Sequence, spring, staticFile, useCurrentFrame} from 'remotion';
import {Beat, Props, Scene} from '../shared';
import {Blob, BlobState} from './Blob';
import {Ground, Headline, Masthead} from './Frame';
import {BeforeAfter, BrowserWindow, CodeEditor, EmphasisTile, Footage, ObjProps, PhoneNotice, PointsPanel, PremiumHook, PullQuote, ReadmePanel,
  RepositoryReveal, SignatureCTA, StatFigure, TerminalRun, ToggleList, WarningNote, Workflow} from './Objects';
import {C, DUR, EASE, ID, SPRING, STAGE, T, clamp01, ensureFonts} from './tokens';

/* fieldnotes-premium renderer. Same props contract as the studio renderer (scenes → beats with semantic layouts);
   the visual director (Python) adds per-beat `transition` and `character` staging; sensible defaults apply otherwise. */

type Staging = {state: BlobState; scale: 'companion' | 'medium' | 'closeup' | 'hidden'; anchor: 'home' | 'right' | 'centre'; point?: 'left' | 'right' | 'up'; dim?: number; wink?: boolean};
type PBeat = Beat & {transition: string; character?: Staging; direction?: unknown};
type GBeat = PBeat & {scene: Scene; si: number; start: number; end: number};

const LAYOUT: Record<string, React.FC<ObjProps>> = {
  hookBold: PremiumHook, hookStack: PremiumHook, repoCard: RepositoryReveal, starMeter: StatFigure, readmeScroll: ReadmePanel,
  repoConnect: p => <Workflow {...p} hub/>, nodeGraph: p => <Workflow {...p} hub/>, flowDiagram: Workflow, codeBlock: CodeEditor, terminal: TerminalRun,
  splitCompare: BeforeAfter, compare: BeforeAfter, deviceMock: PhoneNotice, chat: PhoneNotice, browserMock: BrowserWindow, warningCard: WarningNote,
  steps: ToggleList, timeline: ToggleList, listStack: ToggleList, recap: ToggleList, chips: PointsPanel, docStamp: PullQuote, quote: PullQuote,
  heroWord: EmphasisTile, mascotCloseup: EmphasisTile, bigNumber: StatFigure, chartBars: StatFigure, statRing: StatFigure, outroCTA: SignatureCTA,
  cinematic: Footage, motionClip: Footage,
};
const SIZES = ID.scales;
const ANCHOR_X = {home: 64, right: 1080 - 64, centre: 540};
const FEET_Y = T.character.home.y + 40;
const TRANS = DUR.transition;

const flatten = (scenes: Scene[], fps: number): GBeat[] => {
  const out: GBeat[] = [];
  scenes.forEach((scene, si) => {
    const beats = (scene.beats?.length ? scene.beats : [{s: 0, e: scene.frames / fps, w: [0, 0], text: scene.narration, focus: scene.emphasis || scene.heading,
      layout: 'quote', anchor: 'right', transition: 'blurDissolve', punch: false}]) as PBeat[];
    beats.forEach((beat, bi) => {
      const start = scene.from + Math.round(beat.s * fps);
      const end = bi < beats.length - 1 ? scene.from + Math.round(beats[bi + 1].s * fps) : scene.from + scene.frames;
      out.push({...beat, scene, si, start, end});
    });
  });
  return out;
};

const exitStyle = (kind: string, p: number): React.CSSProperties => {
  if (p <= 0) return {};
  const e = EASE.exit(p);
  if (kind === 'cut') return {opacity: p >= 1 ? 0 : 1};
  if (kind === 'expand') return {opacity: 1 - e, transform: `scale(${1 + .08 * e})`, filter: `blur(${e * 8}px)`};
  if (kind === 'focus') return {opacity: 1 - e, transform: `scale(${1 + .14 * e})`, filter: `blur(${e * 12}px)`};
  if (kind === 'push') return {opacity: 1 - e, transform: `translateX(${-140 * e}px)`, filter: `blur(${e * 6}px)`};
  return {opacity: 1 - e, transform: `scale(${1 - .02 * e})`, filter: `blur(${e * T.motion.blur.exit}px)`};
};

const BeatView: React.FC<{b: GBeat; next?: GBeat; props: Props; first: GBeat; count: number}> = ({b, next, props, first, count}) => {
  const f = useCurrentFrame();
  const dur = b.end - b.start;
  const loop = b.layout === 'loop';
  const src = loop ? first : b;
  const Obj = LAYOUT[src.layout] ?? PullQuote;
  const out = next ? clamp01((f - dur) / TRANS) : 0;
  const style = exitStyle(next?.transition ?? 'blurDissolve', out);
  const push = 1 + T.motion.camera.push * Math.min(1, f / Math.max(1, dur));
  const enterPush = b.transition === 'push' && b.start > 0 ? {transform: `translateX(${(1 - clamp01(f / TRANS)) * 140}px)`} : {};
  return <AbsoluteFill style={style}>
    <AbsoluteFill style={{transform: `scale(${push})`, transformOrigin: '50% 45%', ...enterPush}}>
      <div style={{position: 'absolute', left: STAGE.left, top: STAGE.top, width: STAGE.width, height: STAGE.height}}>
        <Obj beat={src} scene={src.scene} props={props} f={loop ? f + 60 : f} dur={dur} count={count}/>
      </div>
    </AbsoluteFill>
  </AbsoluteFill>;
};

const defaultStaging = (b: GBeat, isFirst: boolean, isLast: boolean): Staging => {
  if (isFirst) return {state: 'speaking', scale: 'closeup', anchor: 'centre'};
  if (b.layout === 'outroCTA') return {state: 'pointing', scale: 'medium', anchor: 'right', point: 'left', wink: true};
  if (['codeBlock', 'terminal', 'flowDiagram', 'nodeGraph', 'repoConnect', 'readmeScroll', 'splitCompare'].includes(b.layout)) return {state: 'speaking', scale: 'companion', anchor: 'home', dim: .2};
  if (b.layout === 'repoCard') return {state: 'presenting', scale: 'medium', anchor: 'home', point: 'right'};
  if (b.layout === 'cinematic' || b.layout === 'motionClip') return {state: 'idle', scale: 'hidden', anchor: 'home'};
  return {state: 'speaking', scale: 'companion', anchor: 'home'};
};

export const PremiumVideo: React.FC<Props> = props => {
  ensureFonts();
  const frame = useCurrentFrame();
  const fps = props.fps;
  const beats = flatten(props.scenes, fps);
  const count = props.scenes.filter(s => (s.item ?? 0) > 0).length;
  let ai = 0;
  beats.forEach((b, i) => { if (frame >= b.start) ai = i; });
  const cur = beats[ai], prev = beats[ai - 1];
  const scene = cur.scene;
  const local = frame - scene.from;
  const since = frame - cur.start;
  const t = local / fps;
  const hideHeadline = ['hookBold', 'hookStack', 'outroCTA', 'loop'].includes(cur.layout);

  // ---- character staging (director-provided, else defaults), sizes/positions eased between beats
  const stage = (b: GBeat | undefined, i: number) => b ? (b.character ?? defaultStaging(b, i === 0, i === beats.length - 1)) : undefined;
  const now = stage(cur, ai)!, before = stage(prev, ai - 1) ?? now;
  const k = spring({frame: since, fps, config: SPRING});
  const size = SIZES[before.scale] + (SIZES[now.scale] - SIZES[before.scale]) * k;
  const xOf = (s: Staging, w: number) => s.anchor === 'centre' ? ANCHOR_X.centre - w / 2 : s.anchor === 'right' ? ANCHOR_X.right - w : ANCHOR_X.home;
  const x = xOf(before, SIZES[before.scale]) + (xOf(now, SIZES[now.scale]) - xOf(before, SIZES[before.scale])) * k;
  const entrance = spring({frame: frame + 2, fps, config: {damping: 14, stiffness: 120}});       // signature pop-up, mostly up on frame 0
  const last = beats[beats.length - 1];
  const exiting = frame > last.end - 8;
  const words = scene.words ?? [];
  const speaking = local < (scene.audioFrames ?? scene.frames);
  const mouth = speaking ? scene.mouth?.[local] ?? 0 : 0;
  const seed = [...(props.variant?.seed ?? 'x')].reduce((n: number, c: string) => n + c.charCodeAt(0), 0) % 97;
  const blinks = beats.map(b => b.start + 2).concat(Array.from({length: Math.ceil(props.durationInFrames / 84)}, (_, i) => i * 104 + ((i * 41 + seed) % 36)));
  const lastBlink = Math.max(-99, ...blinks.filter(v => v <= frame));
  const lookX = now.anchor === 'right' ? -1 : now.anchor === 'centre' ? 0 : 1;
  const state: BlobState = exiting ? 'exiting' : now.state === 'speaking' && !speaking ? 'idle' : now.state;
  const visible = now.scale !== 'hidden' || (before.scale !== 'hidden' && k < 1);

  return <AbsoluteFill style={{background: C.ground, overflow: 'hidden'}}>
    <Ground frame={frame}/>
    {beats.map((b, i) => <Sequence key={i} from={b.start} durationInFrames={b.end - b.start + (beats[i + 1] ? TRANS : 0)}>
      <BeatView b={b} next={beats[i + 1]} props={props} first={beats[0]} count={count}/>
    </Sequence>)}
    <Headline words={words} t={t} emphasis={scene.emphasis ?? ''} hidden={hideHeadline}/>
    <Masthead brand={props.brand ?? 'FIELDNOTES'} series={props.series ?? ''} index={cur.si + 1} total={props.scenes.length}
      progress={frame / Math.max(1, props.durationInFrames - 1)}/>
    {visible && <div style={{position: 'absolute', left: x, top: FEET_Y - size * .79, transform: `translateY(${(1 - entrance) * 220}px)`, opacity: entrance}}>
      <Blob size={size} frame={frame} state={state} stateFrame={exiting ? frame - (last.end - 8) : since} mouth={mouth} look={{x: lookX, y: -.6}}
        blink={frame - lastBlink} point={now.point} wink={now.wink && since > 20} dim={now.dim ?? 0}/>
    </div>}
    {props.scenes.map((s, i) => <Sequence key={i} from={s.from} durationInFrames={s.frames}>
      {s.audio && <Audio src={staticFile(s.audio)}/>}
      {s.uiAudio && <Audio src={staticFile(s.uiAudio)} volume={.45}/>}
    </Sequence>)}
    {props.music && <Audio src={staticFile(props.music)}/>}
  </AbsoluteFill>;
};

export const BlobSheet: React.FC = () => {
  ensureFonts();
  const f = useCurrentFrame();
  const states: BlobState[] = ['idle', 'speaking', 'thinking', 'pointing', 'typing', 'explaining', 'surprised', 'celebrating', 'warning', 'confused', 'presenting', 'exiting'];
  return <AbsoluteFill style={{background: C.ground, display: 'flex', flexWrap: 'wrap', padding: 60, gap: 40, alignContent: 'flex-start'}}>
    {states.map((s, i) => <div key={s} style={{width: 300, height: 330, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end'}}>
      <Blob size={220} frame={f} state={s} stateFrame={Math.min(f, s === 'exiting' ? 6 : 18)} mouth={s === 'speaking' ? .7 : 0} point={i % 2 ? 'left' : 'right'}
        look={{x: 0, y: 0}} blink={s === 'idle' ? 1 : 99} wink={s === 'presenting'}/>
      <div style={{fontFamily: T.font.mono, color: C.muted, fontSize: 30, marginTop: 30}}>{s}</div>
    </div>)}
  </AbsoluteFill>;
};

