import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {clamp, clip, CountUp, Repo, Scene, usePop} from '../shared';
import {hue, P, T} from './theme';

const paperCard: React.CSSProperties = {background: P.card, border: `3px solid ${P.ink}`, borderRadius: 18, boxShadow: '0 26px 60px #2a201426, 0 3px 0 #00000010'};

// Hand-drawn marker ellipse that draws itself around content.
export const MarkerCircle: React.FC<{at: number; width: number; height: number}> = ({at, width, height}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [at, at + 14], [0, 1], clamp);
  return <svg width={width} height={height} viewBox="0 0 100 60" preserveAspectRatio="none" style={{position: 'absolute', left: -width * .08, top: -height * .2, overflow: 'visible', pointerEvents: 'none'}}>
    <path d="M8 34 C4 12 40 3 64 6 C92 9 100 28 90 44 C80 58 30 60 14 50 C4 44 6 30 22 22" fill="none" stroke={P.red} strokeWidth="2.6" strokeLinecap="round"
      pathLength={1} strokeDasharray={1} strokeDashoffset={1 - p} vectorEffect="non-scaling-stroke" style={{strokeWidth: 6}}/>
  </svg>;
};

export const Stamp: React.FC<{text: string; at: number; rotate?: number; size?: number}> = ({text, at, rotate = -8, size = 34}) => {
  const pop = usePop(at, 9);
  return <div style={{display: 'inline-block', padding: '8px 22px', border: `5px solid ${P.red}`, borderRadius: 10, color: P.red, fontFamily: P.mono, fontWeight: 900, fontSize: size,
    letterSpacing: 4, background: '#fffdf8e6', opacity: Math.min(1, pop * 1.5), transform: `rotate(${rotate}deg) scale(${2.2 - pop * 1.2})`}}>{text}</div>;
};

const Avatar: React.FC<{name: string; size: number}> = ({name, size}) => {
  const h = hue(name);
  return <div style={{width: size, height: size, borderRadius: size * .24, background: `hsl(${h} 55% 52%)`, border: `3px solid ${P.ink}`, display: 'grid', placeItems: 'center',
    color: '#fff', fontFamily: P.sans, fontWeight: 800, fontSize: size * .42, flexShrink: 0}}>{name.replace(/[^a-z0-9]/gi, '').slice(0, 2).toUpperCase()}</div>;
};

export const RepoCard: React.FC<{repo: Repo; scene: Scene}> = ({repo, scene}) => {
  const frame = useCurrentFrame();
  const cmd = `git clone github.com/${repo.full_name}`;
  const typed = Math.floor(interpolate(frame, [60, 60 + cmd.length * .6], [0, cmd.length], clamp));
  return <div style={{...paperCard, width: 900, overflow: 'hidden'}}>
    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 28px', borderBottom: `2px solid ${P.line}`, fontFamily: P.mono, fontSize: 21, color: P.soft, background: '#f6f3ec'}}>
      <span><span style={{color: P.red}}>●</span> github.com/{repo.owner}</span><span>{repo.language || 'repo'}</span>
    </div>
    <div style={{padding: '28px 34px 30px'}}>
      <div style={{display: 'flex', alignItems: 'center', gap: 22}}>
        <Avatar name={repo.name} size={86}/>
        <div style={{fontFamily: P.sans, fontSize: 30, color: P.soft, lineHeight: 1.1}}>{repo.owner} /<br/><b style={{color: P.ink, fontSize: 50, letterSpacing: -1}}>{clip(repo.name, 24)}</b></div>
      </div>
      <div style={{fontFamily: P.sans, fontSize: 30, lineHeight: 1.32, color: '#4a4540', marginTop: 22}}>{clip(repo.description, 120)}</div>
      <div style={{display: 'flex', flexDirection: 'column', gap: 12, marginTop: 20}}>
        {scene.points.slice(0, 3).map((p, i) => {
          const on = interpolate(frame, [T.card + 14 + i * 8, T.card + 22 + i * 8], [0, 1], clamp);
          return <div key={i} style={{display: 'flex', gap: 16, alignItems: 'center', fontFamily: P.sans, fontWeight: 600, fontSize: 32, color: P.ink, opacity: on, transform: `translateX(${(1 - on) * -20}px)`}}>
            <span style={{width: 34, height: 34, borderRadius: 8, background: P.red, color: '#fff', display: 'grid', placeItems: 'center', fontSize: 22}}>✓</span>{p}
          </div>;
        })}
      </div>
      <div style={{display: 'flex', alignItems: 'center', gap: 30, marginTop: 26}}>
        <div style={{position: 'relative', fontFamily: P.sans, fontWeight: 800, fontSize: 64, color: P.ink, letterSpacing: -1}}>
          <span style={{color: '#e9a92b'}}>★ </span><CountUp stat={repo.stars.toLocaleString('en-US')} delay={T.countFrom} duration={T.countTo - T.countFrom}/>
          <MarkerCircle at={T.circle} width={420} height={120}/>
        </div>
        <span style={{fontFamily: P.mono, fontSize: 22, color: P.soft, letterSpacing: 2}}>STARS</span>
      </div>
      <div style={{marginTop: 22, padding: '14px 18px', borderRadius: 10, background: P.ink, color: '#f2eee6', fontFamily: P.mono, fontSize: 23, whiteSpace: 'nowrap', overflow: 'hidden'}}>
        <span style={{color: P.red}}>$</span> {cmd.slice(0, typed)}<span style={{opacity: frame % 20 < 10 ? 1 : 0}}>▌</span>
      </div>
    </div>
  </div>;
};

export const DocCard: React.FC<{scene: Scene; index: number; series: string}> = ({scene, index, series}) => {
  const frame = useCurrentFrame();
  const big = usePop(T.stamp - 6, 11);
  return <div style={{position: 'relative', width: 880}}>
    <div style={{position: 'absolute', top: -150, left: -20, zIndex: 2, fontFamily: P.serif, fontStyle: 'italic', fontSize: 190, color: P.red, lineHeight: 1,
      opacity: big, transform: `scale(${1.6 - big * .6}) rotate(-4deg)`, transformOrigin: 'left bottom', textShadow: `4px 4px 0 ${P.card}`}}>
      <span style={{fontFamily: P.sans, fontStyle: 'normal', fontWeight: 900, fontSize: 64, color: P.ink, letterSpacing: 2, verticalAlign: 'top'}}>{series.replace(/S$/, '')} </span>No. {scene.item ?? index}
    </div>
    <div style={{...paperCard, padding: '120px 44px 40px', transform: `rotate(${index % 2 ? 1.6 : -1.4}deg)`}}>
      <div style={{fontFamily: P.mono, fontSize: 21, color: P.soft, letterSpacing: 2, borderBottom: `2px dashed ${P.line}`, paddingBottom: 14}}>§ {pad(scene.item ?? index)} — {clip(scene.heading.toLowerCase(), 34)}</div>
      <div style={{fontFamily: P.serif, fontSize: 52, lineHeight: 1.12, color: P.ink, margin: '22px 0 18px'}}>{scene.heading}</div>
      {scene.stat && <div style={{position: 'relative', display: 'inline-block', fontFamily: P.serif, fontStyle: 'italic', fontSize: 110, color: P.red, margin: '0 0 10px'}}>
        <CountUp stat={scene.stat} delay={T.countFrom} duration={T.countTo - T.countFrom}/><MarkerCircle at={T.circle} width={480} height={150}/>
      </div>}
      {scene.points.slice(0, 3).map((p, i) => {
        const sweep = interpolate(frame, [T.card + 18 + i * 10, T.card + 30 + i * 10], [0, 100], clamp);
        return <div key={i} style={{fontFamily: P.sans, fontSize: 32, color: '#3c3833', padding: '10px 0', borderTop: `2px solid ${P.line}`}}>
          <span style={{backgroundImage: `linear-gradient(90deg, ${i === 0 ? '#ffd84d' : P.redSoft} ${sweep}%, transparent ${sweep}%)`, padding: '0 6px'}}>{p}</span>
        </div>;
      })}
    </div>
  </div>;
};

const pad = (n: number) => String(n).padStart(2, '0');

export const HookCard: React.FC<{title: string; series: string; count: number; repos: Repo[]}> = ({title, series, count, repos}) => {
  const frame = useCurrentFrame();
  if (!repos.length) return <div style={{position: 'relative', width: 860}}>
    <div style={{...paperCard, padding: '40px 46px', transform: 'rotate(-2deg)'}}>
      <div style={{fontFamily: P.mono, fontSize: 21, color: P.soft, letterSpacing: 3}}>THE STORY · {count} {series}</div>
      <div style={{fontFamily: P.serif, fontSize: 70, lineHeight: 1.06, color: P.ink, marginTop: 18}}>{clip(title, 80)}</div>
      <div style={{height: 12, width: `${interpolate(frame, [10, 40], [0, 70], clamp)}%`, background: '#ffd84d', marginTop: 18, borderRadius: 6}}/>
    </div>
    <div style={{position: 'absolute', right: -10, bottom: -50}}><Stamp text="MUST READ" at={T.stamp}/></div>
  </div>;
  return <div style={{position: 'relative', width: 900, height: 600}}>
    {repos.map((r, i) => {
      const pop = usePop(T.card + i * 6, 13);
      const spread = (i - (repos.length - 1) / 2);
      return <div key={i} style={{...paperCard, position: 'absolute', left: 230 + spread * 120, top: 60 + Math.abs(spread) * 30, width: 400, height: 470, padding: 28,
        transform: `rotate(${spread * 7 * pop}deg) translateY(${(1 - pop) * 400}px)`, opacity: pop, display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
        <div style={{fontFamily: P.mono, fontSize: 22, color: P.soft}}>#{i + 1} · {series}</div>
        <div style={{fontFamily: P.serif, fontStyle: 'italic', fontSize: 200, color: i === repos.length - 1 ? P.red : P.ink, textAlign: 'center', lineHeight: 1}}>{i + 1}</div>
        <div style={{display: 'flex', gap: 10}}>{[0, 1, 2].map(k => <span key={k} style={{flex: 1, height: 14, borderRadius: 7, background: P.line}}/>)}</div>
      </div>;
    })}
    <div style={{position: 'absolute', right: 10, top: -30}}><Stamp text={`${count} ${series}`} at={T.stamp} rotate={8}/></div>
  </div>;
};

export const OutroCard: React.FC<{labels: string[]; series: string}> = ({labels, series}) => {
  const frame = useCurrentFrame();
  return <div style={{...paperCard, width: 860, padding: '36px 44px', transform: 'rotate(-1deg)'}}>
    <div style={{display: 'flex', justifyContent: 'space-between', fontFamily: P.mono, fontSize: 22, color: P.soft, letterSpacing: 2}}><span>RECAP · {labels.length} {series}</span><span style={{color: P.red}}>SAVED ✓</span></div>
    {labels.map((label, i) => {
      const on = interpolate(frame, [8 + i * 7, 16 + i * 7], [0, 1], clamp);
      return <div key={i} style={{display: 'flex', alignItems: 'center', gap: 20, padding: '16px 0', borderBottom: `2px solid ${P.line}`, fontFamily: P.sans, fontWeight: 700, fontSize: 38, color: P.ink, opacity: on}}>
        <span style={{fontFamily: P.serif, fontStyle: 'italic', color: P.red, width: 50, fontSize: 44}}>{i + 1}</span>{clip(label, 28)}
      </div>;
    })}
    <div style={{display: 'flex', alignItems: 'center', gap: 18, marginTop: 26}}>
      <svg width="54" height="64" viewBox="0 0 24 28"><path d="M3 2 H21 V26 L12 19 L3 26 Z" fill={frame > 30 ? P.red : 'none'} stroke={P.ink} strokeWidth="2.2" strokeLinejoin="round"/></svg>
      <span style={{fontFamily: P.sans, fontWeight: 800, fontSize: 40, color: P.ink}}>Save this for later</span>
    </div>
  </div>;
};
