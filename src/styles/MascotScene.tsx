import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {Character} from '../Character';
import {clamp, clip, CountUp, mono, pad2, sans, SceneAudio, serif, ShotProps, splitStat, usePop, useCaption, useTransition} from '../shared';

const ink = '#1d1b1a';
const yellow = '#ffd84d';
// [backdrop, desk, hoodie]
const palettes = [['#eaa999', '#8a4b3c', '#2f3b52'], ['#86ade6', '#2e4f8f', '#e86f51'], ['#93d6b9', '#2f7a5c', '#2f3b52'], ['#f1ca6c', '#a8642a', '#3d5a99'], ['#c9abe9', '#5b3f8c', '#e8a33d']];
const hard = `10px 10px 0 ${ink}`;

const Readme: React.FC<ShotProps> = ({scene, brand}) => {
  const frame = useCurrentFrame();
  return <div style={{width: 760, background: '#fffdf7', border: `6px solid ${ink}`, borderRadius: 22, boxShadow: hard, padding: '28px 36px 34px'}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 14, fontFamily: sans, fontSize: 26, color: '#555'}}>
      <span style={{width: 36, height: 36, borderRadius: 36, border: `5px solid #3b6fd8`}}/>{brand.toLowerCase()} / <b style={{color: ink}}>{scene.heading.split(' ').slice(0, 2).join('-').toLowerCase().replace(/[^a-z0-9-]/g, '')}</b>
    </div>
    <div style={{display: 'flex', gap: 24, marginTop: 18, fontFamily: sans, fontSize: 20, fontWeight: 800, letterSpacing: 1, borderBottom: '3px solid #e8e2d4', paddingBottom: 10}}>
      <span style={{borderBottom: `4px solid ${ink}`, paddingBottom: 8}}>README</span><span style={{color: '#999'}}>MIT license</span>
    </div>
    <div style={{fontFamily: sans, fontWeight: 900, fontSize: 52, color: ink, marginTop: 20, letterSpacing: -1.5, lineHeight: 1.05}}>{scene.heading}</div>
    {scene.points.map((p, i) => <div key={i} style={{fontFamily: serif, fontStyle: 'italic', fontSize: 34, color: '#444', marginTop: 12, opacity: interpolate(frame, [14 + i * 10, 22 + i * 10], [0, 1], clamp)}}>• {p}</div>)}
  </div>;
};

const Counter: React.FC<ShotProps> = ({scene}) => {
  const parts = splitStat(scene.stat ?? '');
  const digits = parts ? `${parts.value}`.length : 0;
  return <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24}}>
    <div style={{display: 'flex', alignItems: 'center', gap: 22, background: ink, padding: '26px 34px', borderRadius: 24, boxShadow: `10px 10px 0 #00000040`}}>
      <span style={{fontSize: 88, color: yellow, transform: `rotate(${Math.sin(useCurrentFrame() / 8) * 8}deg)`}}>★</span>
      <span style={{fontFamily: mono, fontWeight: 900, fontSize: digits > 7 ? 92 : 120, color: '#fff', letterSpacing: 6, padding: '6px 22px', background: '#2e2b29', borderRadius: 14, border: '4px solid #000'}}>
        {scene.stat ? <CountUp stat={scene.stat} duration={50}/> : '—'}
      </span>
    </div>
    <div style={{fontFamily: mono, fontWeight: 800, fontSize: 30, background: '#fffdf7', border: `5px solid ${ink}`, padding: '10px 26px', borderRadius: 12, boxShadow: `6px 6px 0 ${ink}`}}>{scene.heading.toUpperCase()}</div>
  </div>;
};

const Retro: React.FC<ShotProps> = ({scene}) => {
  const frame = useCurrentFrame();
  return <div style={{width: 760, background: '#2b2a28', border: `6px solid ${ink}`, borderRadius: 22, boxShadow: hard, padding: '26px 34px', fontFamily: mono, fontSize: 30, color: '#e8f5e4'}}>
    <div style={{color: '#8f8', fontSize: 22, marginBottom: 14}}>● ● ●&nbsp;&nbsp;~/{scene.heading.split(' ')[0].toLowerCase()}</div>
    {[scene.heading, ...scene.points].map((l, i) => {
      const start = 6 + i * 16;
      const chars = Math.floor(interpolate(frame, [start, start + l.length * .7], [0, l.length], clamp));
      return <div key={i} style={{padding: '6px 0', color: i === 0 ? yellow : '#e8f5e4'}}>{i === 0 ? '> ' : '  ✓ '}{l.slice(0, chars)}</div>;
    })}
  </div>;
};

const Lights: React.FC<ShotProps> = ({scene}) => {
  const frame = useCurrentFrame();
  const pts = scene.points.length ? scene.points : [scene.heading];
  const colors = ['#ef5b4b', '#f4c13e', '#5fcf6a'];
  return <div style={{display: 'flex', gap: 30, alignItems: 'center'}}>
    <div style={{background: ink, padding: 22, borderRadius: 40, display: 'flex', flexDirection: 'column', gap: 18, boxShadow: `8px 8px 0 #00000040`}}>
      {pts.map((_, i) => {
        const on = frame > 14 + i * 16;
        return <span key={i} style={{width: 92, height: 92, borderRadius: 92, background: on ? colors[i % 3] : '#3a3633', boxShadow: on ? `0 0 40px ${colors[i % 3]}` : 'none'}}/>;
      })}
    </div>
    <div style={{display: 'flex', flexDirection: 'column', gap: 30}}>
      {pts.map((p, i) => <div key={i} style={{fontFamily: sans, fontWeight: 800, fontSize: 36, background: '#fffdf7', border: `5px solid ${ink}`, borderRadius: 14, padding: '14px 22px', boxShadow: `6px 6px 0 ${ink}`, opacity: frame > 14 + i * 16 ? 1 : .35}}>{p}</div>)}
    </div>
  </div>;
};

export const MascotShot: React.FC<ShotProps> = props => {
  const {scene, index, total} = props;
  const frame = useCurrentFrame();
  const [backdrop, desk, hoodie] = palettes[index % palettes.length];
  const {group, groupStart, active, speaking} = useCaption(scene, 3);
  const {enter, leave} = useTransition(scene, index, total);
  const prop = usePop(6, 13);
  const tag = usePop(2, 12);
  const visual = scene.stat ? Counter : scene.visual === 'terminal' ? Retro : scene.visual === 'flow' ? Lights : Readme;
  const shift = ((1 - enter) * (index % 2 ? 1 : -1) + leave * ((index + 1) % 2 ? -1 : 1)) * 1080;
  return <AbsoluteFill style={{background: backdrop, transform: `translateX(${shift}px)`, overflow: 'hidden'}}>
    <AbsoluteFill style={{backgroundImage: 'radial-gradient(#00000026 4px, transparent 4.5px)', backgroundSize: '46px 46px', backgroundPosition: '23px 23px'}}/>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 35%, #ffffff40 0%, transparent 60%)'}}/>
    <div style={{position: 'absolute', top: 96, left: 64, transform: `rotate(-2deg) scale(${tag})`, transformOrigin: 'left', background: ink, color: '#fff', fontFamily: mono, fontWeight: 800, fontSize: 30, letterSpacing: 2, padding: '12px 22px', borderRadius: 10}}>
      {pad2(index + 1)} · {clip(scene.heading.toUpperCase(), 28)}
    </div>
    <div style={{position: 'absolute', top: 210, left: 0, right: 0, height: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: prop, transform: `translateY(${(1 - prop) * -260}px) rotate(${Math.sin(frame / 30) * 1}deg)`}}>
      {React.createElement(visual, props)}
    </div>
    <div style={{position: 'absolute', left: 0, right: 0, top: 860, display: 'flex', justifyContent: 'center'}}>
      <Character width={600} mouth={scene.mouth?.[frame] ?? (speaking ? .5 + Math.sin(frame / 2.6) * .4 : 0)} pose={index % 3 === 0 ? 'wave' : index % 3 === 1 ? 'point' : 'present'} hoodie={hoodie}/>
    </div>
    <div style={{position: 'absolute', left: 0, right: 0, top: 1420, bottom: 0, background: desk, borderTop: `10px solid ${ink}`}}>
      <div style={{height: 26, background: '#ffffff30'}}/>
      <AbsoluteFill style={{backgroundImage: 'repeating-linear-gradient(90deg, #00000012 0 3px, transparent 3px 60px)'}}/>
    </div>
    <div style={{position: 'absolute', top: 1520, left: 60, right: 60, display: 'flex', justifyContent: 'center', gap: 18, flexWrap: 'wrap'}}>
      {group.map((word, i) => {
        const current = groupStart + i === active;
        const shown = groupStart + i <= active;
        return <span key={groupStart + i} style={{fontFamily: sans, fontWeight: 900, fontSize: 70, padding: '6px 22px', borderRadius: 12, border: `6px solid ${ink}`,
          background: current ? yellow : '#fffdf7', color: ink, boxShadow: `6px 6px 0 ${ink}`, opacity: shown ? 1 : 0, transform: `scale(${current ? 1.08 : 1}) rotate(${(i - 1) * 1.5}deg)`}}>{word}</span>;
      })}
    </div>
    <SceneAudio scene={scene}/>
  </AbsoluteFill>;
};
