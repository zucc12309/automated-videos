import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Character, Expression, Pose} from '../Character';
import {clamp, clip, Props, Scene, SceneAudio, Word} from '../shared';
import {DocCard, HookCard, OutroCard, RepoCard} from './Cards';
import {hue, P, T} from './theme';

const bare = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}$%]/gu, '');

// Real word timings from the TTS when available; otherwise spread words by length across the audio.
const timedWords = (scene: Scene, fps: number): Word[] => {
  if (scene.words?.length) return scene.words;
  const words = scene.narration.trim().split(/\s+/);
  const total = words.reduce((n, w) => n + Math.max(1, bare(w).length), 0);
  const dur = (scene.audioFrames ?? scene.frames) / fps;
  let acc = 0;
  return words.map(w => {
    const s = acc / total * dur;
    acc += Math.max(1, bare(w).length);
    return {w, s, e: acc / total * dur};
  });
};

const phraseOf = (words: Word[], index: number) => {
  let start = 0;
  for (let i = 0; i < words.length; i++) {
    const end = /[.,!?;:—]$/.test(words[i].w) || i - start >= 6 || i === words.length - 1;
    if (end) {
      if (index <= i) return {start, end: i};
      start = i + 1;
    }
  }
  return {start, end: words.length - 1};
};

const useSpeech = (scene: Scene) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const words = timedWords(scene, fps);
  const t = frame / fps + .04;
  let active = 0;
  words.forEach((w, i) => { if (w.s <= t) active = i; });
  const emphasis = (scene.emphasis ?? '').split(/\s+/).map(bare).filter(Boolean);
  const isEmphasis = (w: string) => emphasis.includes(bare(w));
  return {words, active, t, isEmphasis};
};

const Headline: React.FC<{scene: Scene}> = ({scene}) => {
  const {words, active, t, isEmphasis} = useSpeech(scene);
  const {start, end} = phraseOf(words, active);
  return <div style={{position: 'absolute', top: 150, left: 70, right: 70, fontFamily: P.sans, fontWeight: 600, fontSize: 78, lineHeight: 1.12, letterSpacing: -2, color: P.ink}}>
    {words.slice(start, end + 1).map((w, i) => {
      const p = interpolate(t, [w.s - .02, w.s + .12], [0, 1], clamp);
      const accent = isEmphasis(w.w);
      return <span key={start + i} style={{display: 'inline-block', marginRight: 18, opacity: p, transform: `translateY(${(1 - p) * 16}px)`,
        ...(accent ? {fontFamily: P.serif, fontStyle: 'italic', fontWeight: 400, fontSize: 88, color: P.red, letterSpacing: -1} : {})}}>{w.w}</span>;
    })}
  </div>;
};

const PaperScene: React.FC<{scene: Scene; index: number; props: Props; count: number}> = ({scene, index, props, count}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pop = spring({frame: frame - T.card, fps, config: {damping: 15, stiffness: 120}});
  const exit = interpolate(frame, [scene.frames - 10, scene.frames], [0, 1], clamp);
  const item = scene.item ?? 0;
  const series = props.series || 'ITEMS';
  const repo = item > 0 ? props.repos?.[item - 1] : undefined;
  const labels = props.scenes.filter(s => (s.item ?? 0) > 0).map(s => s.label || s.heading);
  const card = scene.visual === 'hook' ? <HookCard title={props.title} series={series} count={count} repos={props.repos ?? []}/>
    : scene.visual === 'outro' ? <OutroCard labels={labels} series={series}/>
    : repo ? <RepoCard repo={repo} scene={scene}/> : <DocCard scene={scene} index={index} series={series}/>;
  const tag = scene.visual === 'hook' ? 'before you scroll' : scene.visual === 'outro' ? 'recap' : (scene.label || scene.heading).toLowerCase();
  return <AbsoluteFill style={{opacity: index === 0 ? 1 : interpolate(frame, [0, 6], [0, 1], clamp)}}>
    <div style={{position: 'absolute', top: 84, left: 70, right: 70, display: 'flex', justifyContent: 'space-between', fontFamily: P.mono, fontSize: 23, color: P.soft, letterSpacing: 1}}>
      <span>// {String(item).padStart(2, '0')} — {clip(tag, 26)}</span>
      {count > 0 && <span>{series} <b style={{color: P.red}}>{scene.visual === 'outro' ? count : item}</b>/{count}</span>}
    </div>
    <Headline scene={scene}/>
    <div style={{position: 'absolute', top: 470, left: 0, right: 0, height: 700, display: 'flex', alignItems: 'center', justifyContent: 'center',
      transform: `translateX(${(1 - pop) * 900 - exit * 1100}px) rotate(${(1 - pop) * 9 - exit * 7}deg) scale(.92)`, opacity: Math.min(1, pop * 2)}}>
      {card}
    </div>
    <SceneAudio scene={scene}/>
  </AbsoluteFill>;
};

const Tracker: React.FC<{props: Props; count: number}> = ({props, count}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const items = props.scenes.filter(s => (s.item ?? 0) > 0);
  const filled = items.filter(s => frame >= s.from + T.plug).length;
  const appear = spring({frame: frame - 8, fps, config: {damping: 16}});
  return <div style={{position: 'absolute', left: 48, top: 1196, display: 'flex', alignItems: 'center', gap: 14, padding: '16px 18px', background: P.card, border: `3px solid ${P.ink}`,
    borderRadius: 24, boxShadow: '0 16px 40px #2a201420', opacity: appear, transform: `translateY(${(1 - appear) * 60}px)`}}>
    <div style={{width: 128, fontFamily: P.mono}}>
      <div style={{fontSize: 17, color: P.soft, letterSpacing: 1}}><span style={{color: filled ? P.red : P.line}}>●</span> {clip(props.series || 'ITEMS', 8)}</div>
      <div style={{fontSize: 34, fontWeight: 800, color: P.ink}}>{filled}/{count}</div>
    </div>
    {items.map((s, i) => {
      const on = frame >= s.from + T.plug;
      const plug = spring({frame: frame - s.from - T.plug, fps, config: {damping: 9, stiffness: 180}});
      const name = s.label || s.heading;
      return <div key={i} style={{position: 'relative', width: 80, height: 80, borderRadius: 16, border: `3px solid ${P.ink}`, background: '#f1ede4', display: 'grid', placeItems: 'center'}}>
        <div style={{display: 'flex', gap: 10}}><span style={{width: 9, height: 26, borderRadius: 4, background: P.ink}}/><span style={{width: 9, height: 26, borderRadius: 4, background: P.ink}}/></div>
        {on && <div style={{position: 'absolute', inset: -3, borderRadius: 16, border: `3px solid ${P.ink}`, background: `hsl(${hue(name)} 55% 52%)`, display: 'grid', placeItems: 'center',
          color: '#fff', fontFamily: P.sans, fontWeight: 800, fontSize: 30, transform: `translateY(${(1 - plug) * -120}px) scale(${.8 + plug * .2})`}}>
          {name.replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase()}
          <span style={{position: 'absolute', top: -14, left: '50%', width: 4, height: 14 + (1 - plug) * 80, background: P.ink, transform: 'translateX(-50%)'}}/>
        </div>}
      </div>;
    })}
  </div>;
};

const Grain = () => <AbsoluteFill style={{pointerEvents: 'none'}}>
  <svg width="1080" height="1920" style={{position: 'absolute', opacity: .32, mixBlendMode: 'multiply'}}>
    <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 .45  0 0 0 0 .4  0 0 0 0 .33  0 0 0 .55 0"/></filter>
    <rect width="1080" height="1920" filter="url(#grain)"/>
  </svg>
  <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 40%, transparent 55%, #7a6a5520 100%)'}}/>
</AbsoluteFill>;

const poseFor = (s?: Scene): Pose => !s ? 'rest' : s.visual === 'hook' ? 'wave' : s.visual === 'outro' ? 'thumbs' : s.visual === 'repo' ? 'point' : (s.item ?? 0) % 2 ? 'present' : 'point';

export const PaperVideo: React.FC<Props> = props => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const scenes = props.scenes;
  let ai = 0;
  scenes.forEach((s, i) => { if (frame >= s.from) ai = i; });
  const scene = scenes[ai];
  const local = frame - scene.from;
  const count = scenes.filter(s => (s.item ?? 0) > 0).length;
  const words = timedWords(scene, fps);
  const t = local / fps;
  const emphasis = (scene.emphasis ?? '').split(/\s+/).map(bare).filter(Boolean);
  const speaking = words.find(w => w.s <= t && t <= w.e + .05);
  const expression: Expression = scene.visual === 'outro' && local > (scene.audioFrames ?? 0) ? 'happy'
    : speaking && /[!?]$/.test(speaking.w) && emphasis.length === 0 ? 'surprised' : 'talk';
  const poseT = ai === 0 ? 1 : spring({frame: local, fps, config: {damping: 14, stiffness: 110}});
  return <AbsoluteFill style={{background: P.paper, overflow: 'hidden'}}>
    <Grain/>
    {scenes.map((s, i) => <Sequence key={i} from={s.from} durationInFrames={s.frames}><PaperScene scene={s} index={i} props={props} count={count}/></Sequence>)}
    {count > 0 && <Tracker props={props} count={count}/>}
    <div style={{position: 'absolute', right: -70, top: 1250}}>
      <Character width={620} mouth={scene.mouth?.[local] ?? 0} pose={poseFor(scene)} prevPose={poseFor(scenes[ai - 1])} poseT={poseT}
        expression={expression} emphasis={!!speaking && emphasis.includes(bare(speaking.w))}
        look={scene.visual === 'repo' || scene.visual === 'doc' ? {x: -1, y: -.8} : {x: 0, y: 0}} accent={P.red} hoodie="#2f3b52"/>
    </div>
    {props.music && <Audio src={staticFile(props.music)}/>}
  </AbsoluteFill>;
};
