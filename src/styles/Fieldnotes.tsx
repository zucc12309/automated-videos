import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {Scene, SceneAudio, ShotProps} from '../shared';

const colors = ['#78e6d0', '#f1bd77', '#86b9ff', '#d29cff', '#f28f8b', '#9ee58d'];
const ink = '#07111c';
const panel = '#101d2b';
const muted = '#91a2b3';

const Reveal: React.FC<{children: React.ReactNode; index: number}> = ({children, index}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const progress = spring({frame: frame - 10 - index * 8, fps, config: {damping: 20, stiffness: 100}});
  return <div style={{opacity: progress, transform: `translateY(${(1-progress)*24}px)`}}>{children}</div>;
};

const Signal: React.FC<{accent: string}> = ({accent}) => {
  const frame = useCurrentFrame();
  return <div style={{position: 'absolute', top: 1130, left: 0, right: 0, height: 270, display: 'grid', placeItems: 'center'}}>
    <div style={{position: 'absolute', width: 380, height: 150, borderRadius: '50%', background: accent, filter: 'blur(95px)', opacity: 0.13}}/>
    <svg width="410" height="245" viewBox="0 0 410 245" fill="none" style={{transform: `translateY(${Math.sin(frame/17)*6}px) rotate(${Math.sin(frame/37)*2}deg)`}}>
      <ellipse cx="205" cy="122" rx="143" ry="58" stroke={accent} strokeOpacity=".22" strokeWidth="1"/>
      <ellipse cx="205" cy="122" rx="105" ry="86" stroke="#e4edf5" strokeOpacity=".14" strokeWidth="1" transform={`rotate(${frame*.35} 205 122)`}/>
      <ellipse cx="205" cy="122" rx="67" ry="67" stroke={accent} strokeOpacity=".5" strokeWidth="2"/>
      <circle cx="205" cy="122" r="46" fill={accent} fillOpacity=".12"/>
      <circle cx="205" cy="122" r="26" fill={accent} fillOpacity=".9"/>
      <circle cx={205 + Math.cos(frame/24)*143} cy={122 + Math.sin(frame/24)*58} r="6" fill={accent}/>
      <circle cx={205 + Math.cos(-frame/32)*105} cy={122 + Math.sin(-frame/32)*86} r="4" fill="#f5f7fa"/>
      {Array.from({length: 21}, (_, i) => {
        const height = 8 + Math.abs(Math.sin(frame/7 + i*.72))*32;
        return <rect key={i} x={82+i*12} y={214-height/2} width="3" height={height} rx="2" fill={i%3===0?accent:'#dce6ee'} fillOpacity={i%3===0?.72:.28}/>;
      })}
    </svg>
  </div>;
};

const VisualCard: React.FC<{scene: Scene; accent: string}> = ({scene, accent}) => {
  const frame = useCurrentFrame();
  const points = scene.points.length ? scene.points : ['The key idea', 'What to try'];
  return <div style={{position: 'absolute', top: 555, left: 68, right: 68, minHeight: 485, padding: 34, boxSizing: 'border-box', border: '1px solid #ffffff1c', borderRadius: 28, background: `linear-gradient(145deg, #152536 0%, ${panel} 55%, #0b1724 100%)`, boxShadow: '0 28px 90px #00000050', transform: `translateY(${Math.sin(frame/29)*4}px)`}}>
    <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 24, borderBottom: '1px solid #ffffff20'}}>
      <div style={{display: 'flex', gap: 9, alignItems: 'center'}}>
        <span style={{width: 9, height: 9, borderRadius: 9, background: accent, boxShadow: `0 0 18px ${accent}`}}/>
        <span style={{fontSize: 18, fontWeight: 800, letterSpacing: 3, color: '#e7eff5'}}>THE SIGNAL</span>
      </div>
      <span style={{fontSize: 16, fontWeight: 700, letterSpacing: 2, color: muted}}>0{points.length} INSIGHTS</span>
    </div>
    <div style={{paddingTop: 25, display: 'flex', flexDirection: 'column', gap: 16}}>
      {points.map((point, index) => <Reveal key={`${point}-${index}`} index={index}>
        <div style={{display: 'flex', alignItems: 'center', gap: 21, minHeight: 82, padding: '15px 20px', border: '1px solid #ffffff14', borderRadius: 16, background: index===0?'#ffffff0b':'#07111c65'}}>
          <span style={{width: 42, height: 42, flexShrink: 0, borderRadius: 13, display: 'grid', placeItems: 'center', background: `${accent}20`, color: accent, fontSize: 18, fontWeight: 900, border: `1px solid ${accent}58`}}>{String(index+1).padStart(2,'0')}</span>
          <span style={{fontSize: 28, lineHeight: 1.2, fontWeight: 700, letterSpacing: -.4, color: '#f4f7fa'}}>{point}</span>
          <span style={{marginLeft: 'auto', width: 8, height: 8, borderRadius: 8, background: accent, opacity: interpolate(frame, [16+index*8, 24+index*8], [0, .9], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}/>
        </div>
      </Reveal>)}
    </div>
    <div style={{position: 'absolute', bottom: 18, left: 36, right: 36, height: 2, background: '#ffffff12'}}>
      <div style={{height: '100%', width: `${interpolate(frame,[0,60],[4,100],{extrapolateLeft:'clamp',extrapolateRight:'clamp'})}%`, background: accent, boxShadow: `0 0 12px ${accent}`}}/>
    </div>
  </div>;
};

export const FieldnotesShot: React.FC<ShotProps> = ({scene,index,total}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const words = scene.narration.trim().split(/\s+/);
  const weights = words.map(word => Math.max(1, word.replace(/[^\p{L}\p{N}]/gu,'').length));
  const weightTotal = weights.reduce((sum, weight) => sum+weight, 0);
  const audioFrames = Math.max(1, scene.audioFrames ?? scene.frames-14);
  const progress = Math.min(.999, Math.max(0, frame/audioFrames));
  let passed = 0;
  const foundIndex = weights.findIndex(weight => {
    passed += weight;
    return progress*weightTotal < passed;
  });
  const activeWord = foundIndex < 0 ? words.length-1 : foundIndex;
  const groupStart = Math.floor(activeWord/4)*4;
  const captionWords = words.slice(groupStart,groupStart+4);
  const accent = colors[index%colors.length];
  const entry = spring({frame, fps, config: {damping: 20}});
  const compact = captionWords.some(word => word.length > 14);
  const transitionFrames = Math.min(scene.transitionFrames ?? 0, Math.floor(scene.frames/3));
  const entering = index===0 ? 0 : interpolate(frame,[0,transitionFrames],[index%2===1?1:-1,0],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const leaving = index===total-1 ? 0 : interpolate(frame,[scene.frames-transitionFrames,scene.frames],[0,(index+1)%2===1?-1:1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const sceneOffset = (entering+leaving)*1080;
  return <AbsoluteFill style={{transform:`translateX(${sceneOffset}px)`,background: ink, color: '#f3f6f8', fontFamily: 'Arial, Helvetica, sans-serif', overflow: 'hidden'}}>
    <AbsoluteFill style={{background: `radial-gradient(ellipse at ${68+Math.sin(frame/45)*5}% ${28+Math.cos(frame/52)*4}%, #17283a 0%, ${ink} 57%)`}}/>
    <AbsoluteFill style={{opacity: .18, backgroundImage: 'linear-gradient(#c9d7e505 1px, transparent 1px), linear-gradient(90deg, #c9d7e505 1px, transparent 1px)', backgroundSize: '72px 72px', transform: `translate(${Math.sin(frame/60)*8}px, ${Math.cos(frame/65)*8}px)`}}/>
    <div style={{position: 'absolute', top: 72, left: 72, right: 72, display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 13}}>
        <span style={{width: 30, height: 30, display: 'grid', placeItems: 'center', borderRadius: 9, color: ink, background: accent, fontSize: 17, fontWeight: 900}}>L</span>
        <span style={{fontSize: 21, fontWeight: 800, letterSpacing: 4}}>FIELDNOTES<span style={{color: muted}}> / STUDIO</span></span>
      </div>
      <span style={{fontSize: 16, fontWeight: 700, color: '#b7c5d0', letterSpacing: 2}}>TECH / {String(index+1).padStart(2,'0')}</span>
    </div>
    <div style={{position: 'absolute', top: 175, left: 76, right: 76, opacity: entry, transform: `translateY(${(1-entry)*28}px)`}}>
      <div style={{fontSize: 18, fontWeight: 800, letterSpacing: 5, color: accent, marginBottom: 22}}>A CLEARER LOOK AT WHAT'S NEXT</div>
      <div style={{maxWidth: 920, fontSize: scene.heading.length>36?58:72, lineHeight: 1.04, fontWeight: 800, letterSpacing: -2.7, color: '#f4f7fa'}}>{scene.heading}</div>
    </div>
    <VisualCard scene={scene} accent={accent}/>
    <Signal accent={accent}/>
    <div style={{position: 'absolute', bottom: 284, left: 0, right: 0, minHeight: 208, display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '26px 56px', boxSizing: 'border-box', background: 'linear-gradient(90deg, #0a1521 0%, #142334 50%, #0a1521 100%)', borderTop: `1px solid ${accent}75`, borderBottom: '1px solid #ffffff17'}}>
      <div style={{maxWidth: 970, display: 'flex', flexWrap: 'wrap', justifyContent: 'center', alignItems: 'center', gap: 10}}>
        {captionWords.map((word, indexInGroup) => {
          const wordIndex = groupStart+indexInGroup;
          const current = wordIndex===activeWord;
          return <span key={wordIndex} style={{padding: compact?'9px 10px':'10px 13px', fontSize: compact?34:40, fontWeight: 800, lineHeight: 1.08, color: current?ink:'#f0f4f7', background: current?accent:'#ffffff12', borderRadius: 8, transform: `translateY(${current?-4:0}px)`, boxShadow: current?`0 8px 24px ${accent}40`:'none'}}>{word}</span>;
        })}
      </div>
    </div>
    <div style={{position: 'absolute', bottom: 154, left: 76, right: 76, display: 'flex', justifyContent: 'space-between', color: muted, fontSize: 15, fontWeight: 800, letterSpacing: 3}}>
      <span>IDEAS, MADE CLEAR.</span><span>{String(index+1).padStart(2,'0')} — {String(total).padStart(2,'0')}</span>
    </div>
    <div style={{position: 'absolute', bottom: 92, left: 76, right: 76, height: 3, background: '#ffffff20'}}>
      <div style={{height: '100%', width: `${(index+frame/scene.frames)/total*100}%`, background: accent, boxShadow: `0 0 16px ${accent}`}}/>
    </div>
    <SceneAudio scene={scene}/>
  </AbsoluteFill>;
};

