import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Character} from '../Character';
import {clamp, clip, CountUp, mono, pad2, sans, SceneAudio, serif, ShotProps, usePop, useCaption, useTransition} from '../shared';

const paper = '#f3efe6';
const ink = '#161514';
const red = '#d63a2a';
const soft = '#8b857a';

const slug = (text: string) => clip(text.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim(), 24).replace(/ /g, '-');

const Browser: React.FC<ShotProps> = ({scene, brand}) => {
  const frame = useCurrentFrame();
  const points = scene.points.length ? scene.points : [scene.heading];
  return <div style={{background: '#fff', borderRadius: 26, border: `3px solid ${ink}`, boxShadow: '0 30px 70px #2a201422', overflow: 'hidden'}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '22px 26px', borderBottom: '2px solid #ece7dc', background: '#faf8f3'}}>
      {['#ef6a5b', '#f3bf4f', '#61c454'].map(c => <span key={c} style={{width: 16, height: 16, borderRadius: 16, background: c}}/>)}
      <span style={{marginLeft: 18, flex: 1, padding: '9px 20px', borderRadius: 40, background: '#efebe2', fontFamily: mono, fontSize: 20, color: soft}}>🔒 {brand.toLowerCase()}.app/{slug(scene.heading)}</span>
    </div>
    <div style={{padding: '34px 40px 40px', display: 'flex', flexDirection: 'column', gap: 22}}>
      {points.map((point, i) => {
        const pop = usePop(14 + i * 12);
        const tick = interpolate(frame, [26 + i * 12, 34 + i * 12], [0, 1], clamp);
        return <div key={i} style={{display: 'flex', alignItems: 'center', gap: 22, opacity: pop, transform: `translateX(${(1 - pop) * -30}px)`}}>
          <span style={{width: 40, height: 40, flexShrink: 0, borderRadius: 10, border: `3px solid ${tick > 0 ? red : '#cfc8ba'}`, background: tick > .5 ? red : '#fff', display: 'grid', placeItems: 'center', color: '#fff', fontSize: 26, fontWeight: 900}}>{tick > .5 ? '✓' : ''}</span>
          <span style={{fontFamily: sans, fontSize: 38, fontWeight: 600, color: ink, letterSpacing: -.8}}>{point}</span>
        </div>;
      })}
    </div>
  </div>;
};

const Terminal: React.FC<ShotProps> = ({scene}) => {
  const frame = useCurrentFrame();
  const lines = scene.points.length ? scene.points : [scene.heading];
  return <div style={{background: '#1b1a18', borderRadius: 24, border: `3px solid ${ink}`, padding: '30px 36px 40px', boxShadow: '0 30px 70px #2a201433', fontFamily: mono, fontSize: 30, color: '#e9e4d8'}}>
    <div style={{display: 'flex', gap: 10, marginBottom: 28}}>{['#ef6a5b', '#f3bf4f', '#61c454'].map(c => <span key={c} style={{width: 14, height: 14, borderRadius: 14, background: c}}/>)}</div>
    {lines.map((line, i) => {
      const start = 12 + i * 22;
      const chars = Math.floor(interpolate(frame, [start, start + line.length * .8], [0, line.length], clamp));
      return frame >= start && <div key={i} style={{marginBottom: 18, lineHeight: 1.3}}><span style={{color: red}}>$ </span>{line.slice(0, chars)}{chars < line.length && <span style={{background: '#e9e4d8'}}>&nbsp;</span>}</div>;
    })}
  </div>;
};

const Stat: React.FC<ShotProps> = ({scene}) => {
  const frame = useCurrentFrame();
  const stamp = usePop(52, 10);
  return <div style={{background: '#fff', borderRadius: 22, border: `3px solid ${ink}`, padding: '34px 44px 44px', boxShadow: '0 30px 70px #2a201422', transform: 'rotate(-1.5deg)', position: 'relative'}}>
    <div style={{display: 'flex', justifyContent: 'space-between', fontFamily: mono, fontSize: 22, letterSpacing: 3, color: soft}}><span>THE NUMBER</span><span>{slug(scene.heading).toUpperCase()}</span></div>
    <div style={{fontFamily: serif, fontStyle: 'italic', fontSize: 170, lineHeight: 1.1, color: red, margin: '26px 0 18px', letterSpacing: -4, whiteSpace: 'nowrap'}}>
      {scene.stat ? <CountUp stat={scene.stat}/> : scene.heading}
    </div>
    {scene.points.map((p, i) => <div key={i} style={{fontFamily: mono, fontSize: 24, color: ink, padding: '12px 0', borderTop: '2px dashed #e1dbcf', opacity: interpolate(frame, [30 + i * 8, 38 + i * 8], [0, 1], clamp)}}>— {p}</div>)}
    <div style={{position: 'absolute', top: -26, right: 30, padding: '8px 22px', border: `4px solid ${red}`, color: red, fontFamily: mono, fontWeight: 900, fontSize: 26, letterSpacing: 4, borderRadius: 8, background: '#fff', opacity: stamp, transform: `scale(${2 - stamp}) rotate(8deg)`}}>KEY FACT</div>
  </div>;
};

const Flow: React.FC<ShotProps> = ({scene}) => {
  const frame = useCurrentFrame();
  const points = scene.points.length ? scene.points : [scene.heading];
  return <div style={{display: 'flex', flexDirection: 'column', gap: 0}}>
    {points.map((p, i) => {
      const pop = usePop(12 + i * 16);
      const line = interpolate(frame, [22 + i * 16, 32 + i * 16], [0, 1], clamp);
      return <React.Fragment key={i}>
        <div style={{display: 'flex', alignItems: 'center', gap: 26, padding: '28px 34px', background: '#fff', border: `3px solid ${ink}`, borderRadius: 20, opacity: pop, transform: `scale(${.9 + pop * .1})`, boxShadow: `8px 8px 0 ${i === points.length - 1 ? red : ink}`}}>
          <span style={{width: 58, height: 58, borderRadius: 58, background: i === points.length - 1 ? red : ink, color: '#fff', display: 'grid', placeItems: 'center', fontFamily: mono, fontSize: 26, fontWeight: 800}}>{i + 1}</span>
          <span style={{fontFamily: sans, fontSize: 38, fontWeight: 600, color: ink, letterSpacing: -.8}}>{p}</span>
        </div>
        {i < points.length - 1 && <div style={{height: 52, marginLeft: 62, width: 4, background: ink, transformOrigin: 'top', transform: `scaleY(${line})`}}/>}
      </React.Fragment>;
    })}
  </div>;
};

export const EditorialShot: React.FC<ShotProps> = props => {
  const {scene, index, total, brand} = props;
  const frame = useCurrentFrame();
  const {group, groupStart, active, isEmphasis, speaking} = useCaption(scene, 9);
  const {enter, leave} = useTransition(scene, index, total);
  const card = usePop(4, 16);
  const visual = scene.stat || scene.visual === 'meter' ? Stat : scene.visual === 'terminal' ? Terminal : scene.visual === 'flow' ? Flow : Browser;
  const gestures = ['wave', 'point', 'present', 'thumbs'] as const;
  return <AbsoluteFill style={{background: paper, opacity: Math.min(1, enter * 1.4), transform: `translateY(${leave * -120}px)`, overflow: 'hidden', fontFamily: sans}}>
    <AbsoluteFill style={{backgroundImage: 'radial-gradient(#00000010 1.2px, transparent 1.3px)', backgroundSize: '22px 22px', opacity: .6}}/>
    <div style={{position: 'absolute', top: 96, left: 72, right: 72, display: 'flex', justifyContent: 'space-between', fontFamily: mono, fontSize: 22, color: soft, letterSpacing: 1}}>
      <span>// {pad2(index + 1)} — {clip(scene.heading.toLowerCase().replace(/[.!?]+$/, ''), 30)}</span>
      <span>{scene.stat ? <>AT STAKE <b style={{color: red}}>{scene.stat}</b></> : `${brand} · ${pad2(index + 1)}/${pad2(total)}`}</span>
    </div>
    <div style={{position: 'absolute', top: 190, left: 72, right: 72, fontSize: 82, lineHeight: 1.08, fontWeight: 600, letterSpacing: -2.6, color: ink}}>
      {group.map((word, i) => {
        const shown = groupStart + i <= active;
        const accent = isEmphasis(word);
        return <span key={groupStart + i} style={{display: 'inline-block', marginRight: 20, opacity: shown ? 1 : 0, transform: `translateY(${shown ? 0 : 14}px)`,
          ...(accent ? {fontFamily: serif, fontStyle: 'italic', fontWeight: 400, color: red, letterSpacing: -1} : {})}}>{word}</span>;
      })}
    </div>
    <div style={{position: 'absolute', top: 760, left: 76, right: 76, opacity: card, transform: `translateY(${(1 - card) * 80}px) rotate(${(1 - card) * 3}deg)`}}>
      {React.createElement(visual, props)}
    </div>
    <div style={{position: 'absolute', right: -40, bottom: -70, transform: `translateY(${(1 - usePop(10, 12)) * 300}px)`}}>
      <Character width={440} mouth={scene.mouth?.[frame] ?? (speaking ? .5 + Math.sin(frame / 2.6) * .4 : 0)} pose={gestures[index % gestures.length]} hoodie={ink}/>
    </div>
    <div style={{position: 'absolute', bottom: 90, left: 72, width: 560, height: 4, background: '#00000014'}}>
      <div style={{height: '100%', width: `${(index + frame / scene.frames) / total * 100}%`, background: red}}/>
    </div>
    <SceneAudio scene={scene}/>
  </AbsoluteFill>;
};
