import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {clamp, CountUp, mono, sans, SceneAudio, serif, ShotProps, usePop, useCaption, useTransition} from '../shared';

const bg = '#1c1b19';
const panel = '#262522';
const line = '#3a3833';
const dim = '#8a8780';
const text = '#f2efe8';
const orange = '#e07a4f';

// Dot sphere (Fibonacci lattice), rotated and projected.
const Orb: React.FC<{label: string}> = ({label}) => {
  const frame = useCurrentFrame();
  const n = 260;
  const appear = usePop(4, 20);
  const dots = Array.from({length: n}, (_, i) => {
    const y = 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    const theta = i * 2.39996 + frame / 40;
    const x = Math.cos(theta) * r;
    const z = Math.sin(theta) * r;
    const pulse = 1 + Math.sin(frame / 10 + i * .3) * .04;
    return {x: x * 230 * pulse, y: y * 230 * pulse, z};
  });
  return <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 50, opacity: appear}}>
    <svg width="560" height="560" viewBox="-280 -280 560 560">
      {dots.map((d, i) => <circle key={i} cx={d.x * appear} cy={d.y * appear} r={2 + (d.z + 1) * 1.8} fill={text} opacity={.15 + (d.z + 1) * .4}/>)}
    </svg>
    <div style={{fontFamily: serif, fontSize: 64, color: text, letterSpacing: -1}}>{label}</div>
  </div>;
};

const Chat: React.FC<ShotProps> = ({scene, brand}) => {
  const frame = useCurrentFrame();
  const steps = scene.points.length ? scene.points : [scene.heading];
  const box = usePop(2, 18);
  return <div style={{width: 900, background: panel, border: `2px solid ${line}`, borderRadius: 30, padding: 38, fontFamily: sans, opacity: box, transform: `translateY(${(1 - box) * 60}px)`}}>
    <div style={{display: 'inline-flex', alignItems: 'center', gap: 12, padding: '10px 20px', borderRadius: 14, background: '#302e2a', color: text, fontSize: 26, fontWeight: 600}}>
      <span style={{color: orange, fontSize: 32, display: 'inline-block', transform: `rotate(${frame * 3}deg)`}}>✳</span>{brand}
    </div>
    <div style={{marginTop: 30, display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: dim, fontSize: 26, padding: '18px 0', borderBottom: `2px solid ${line}`}}>
      <span>◔ Thought for {Math.max(1, Math.round(scene.frames / 60))}s</span>
      <span style={{fontFamily: mono, fontSize: 20, color: orange, background: '#e07a4f1c', padding: '6px 14px', borderRadius: 8}}>{scene.heading.toLowerCase().replace(/[^a-z0-9]+/g, '_').slice(0, 24)}</span>
    </div>
    <div style={{display: 'flex', flexDirection: 'column', gap: 22, paddingTop: 26}}>
      {steps.map((step, i) => {
        const on = interpolate(frame, [16 + i * 14, 24 + i * 14], [0, 1], clamp);
        return <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, opacity: .25 + on * .75, color: text, fontSize: 32}}>
          <span style={{width: 34, height: 34, borderRadius: 8, flexShrink: 0, border: `3px solid ${on > .5 ? orange : dim}`, background: on > .5 ? orange : 'transparent', color: bg, display: 'grid', placeItems: 'center', fontSize: 22, fontWeight: 900}}>{on > .5 ? '✓' : ''}</span>
          <span><span style={{color: dim}}>Step {i + 1} — </span>{step}</span>
        </div>;
      })}
      <div style={{fontSize: 26, marginTop: 8, backgroundImage: `linear-gradient(90deg, ${dim} 0%, ${text} 50%, ${dim} 100%)`, backgroundSize: '200% 100%', backgroundPosition: `${-(frame * 4) % 200}% 0`, WebkitBackgroundClip: 'text', color: 'transparent'} as React.CSSProperties}>Working on it…</div>
    </div>
  </div>;
};

const Code: React.FC<ShotProps> = ({scene}) => {
  const frame = useCurrentFrame();
  const lines = scene.points.length ? scene.points : [scene.heading];
  return <div style={{width: 900, background: '#141412', border: `2px solid ${line}`, borderRadius: 26, padding: '34px 40px', fontFamily: mono, fontSize: 30, color: text}}>
    {lines.map((l, i) => {
      const start = 8 + i * 20;
      const chars = Math.floor(interpolate(frame, [start, start + l.length * .7], [0, l.length], clamp));
      return <div key={i} style={{padding: '10px 0', opacity: frame >= start ? 1 : 0}}><span style={{color: dim}}>{String(i + 1).padStart(2, ' ')}  </span><span style={{color: orange}}>›</span> {l.slice(0, chars)}</div>;
    })}
  </div>;
};

const Big: React.FC<ShotProps> = ({scene}) => {
  const pop = usePop(4, 16);
  return <div style={{textAlign: 'center', opacity: pop, transform: `scale(${.85 + pop * .15})`}}>
    <div style={{fontFamily: serif, fontSize: 210, color: text, letterSpacing: -6, lineHeight: 1}}><CountUp stat={scene.stat!}/></div>
    <div style={{marginTop: 30, fontFamily: mono, fontSize: 26, color: dim, letterSpacing: 6, textTransform: 'uppercase'}}>{scene.heading}</div>
  </div>;
};

const Bars: React.FC<ShotProps> = ({scene}) => {
  const frame = useCurrentFrame();
  const pts = scene.points.length ? scene.points : [scene.heading];
  return <div style={{width: 880, display: 'flex', flexDirection: 'column', gap: 40}}>
    {pts.map((p, i) => <div key={i}>
      <div style={{fontFamily: sans, fontSize: 32, color: text, marginBottom: 14}}>{p}</div>
      <div style={{height: 14, borderRadius: 14, background: line}}>
        <div style={{height: '100%', borderRadius: 14, background: i === 0 ? orange : text, width: `${interpolate(frame, [10 + i * 10, 40 + i * 10], [0, 92 - i * 22], clamp)}%`}}/>
      </div>
    </div>)}
  </div>;
};

export const KineticShot: React.FC<ShotProps> = props => {
  const {scene, index, total} = props;
  const frame = useCurrentFrame();
  const {group, groupStart, starts, isEmphasis} = useCaption(scene, 6);
  const {enter, leave} = useTransition(scene, index, total);
  const visual = scene.stat ? Big : scene.visual === 'terminal' ? Code : scene.visual === 'flow' ? null : scene.visual === 'meter' ? Bars : Chat;
  return <AbsoluteFill style={{background: bg, opacity: enter * (1 - leave), overflow: 'hidden', fontFamily: sans}}>
    <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% ${40 + Math.sin(frame / 50) * 4}%, #2a2925 0%, ${bg} 65%)`}}/>
    <div style={{position: 'absolute', top: 250, left: 80, right: 80, textAlign: 'center', fontSize: 66, lineHeight: 1.2, letterSpacing: -1.5}}>
      {group.map((word, i) => {
        const t = interpolate(frame, [starts[groupStart + i] - 3, starts[groupStart + i] + 5], [0, 1], clamp);
        const accent = isEmphasis(word);
        return <span key={groupStart + i} style={{display: 'inline-block', margin: '0 12px', opacity: t, filter: `blur(${(1 - t) * 8}px)`, transform: `translateY(${(1 - t) * 18}px)`,
          color: accent ? text : dim, fontWeight: accent ? 700 : 400}}>{word}</span>;
      })}
    </div>
    <div style={{position: 'absolute', top: 560, left: 0, right: 0, bottom: 360, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      {visual ? React.createElement(visual, props) : <Orb label={scene.heading}/>}
    </div>
    <div style={{position: 'absolute', bottom: 150, left: 90, right: 90, height: 96, borderRadius: 30, background: panel, border: `2px solid ${line}`, display: 'flex', alignItems: 'center', padding: '0 30px', gap: 22, color: dim, fontSize: 30}}>
      <span style={{fontSize: 40}}>+</span><span style={{flex: 1}}>Ask anything…</span>
      <span style={{width: 54, height: 54, borderRadius: 16, background: '#3a3833', display: 'grid', placeItems: 'center', color: text}}>↑</span>
    </div>
    <div style={{position: 'absolute', bottom: 90, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 12}}>
      {Array.from({length: total}, (_, i) => <span key={i} style={{width: i === index ? 36 : 10, height: 10, borderRadius: 10, background: i === index ? text : line}}/>)}
    </div>
    <SceneAudio scene={scene}/>
  </AbsoluteFill>;
};
