import React from 'react';
import {AbsoluteFill} from 'remotion';
import {LogoMark, LogoReveal} from './Logo';
import {Mimo} from './Mimo';
import {DM, DMScene, FONT, io, rand, sp, wf} from './theme';

export type SceneProps = {scene: DMScene; f: number; mouth: number};

const abs = (style: React.CSSProperties): React.CSSProperties => ({position: 'absolute', ...style});
const fmt = (n: number) => Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');

/** Place Mimo by the centre of its feet (x) and the bottom of its shadow (y). */
const MimoAt: React.FC<{x: number; y: number; size: number; children: React.ReactNode; rotate?: number}> = ({x, y, size, children, rotate = 0}) =>
  <div style={abs({left: x - size / 2, top: y - size * 1.2, width: size, transform: `rotate(${rotate}deg)`, transformOrigin: '50% 100%'})}>{children}</div>;

const Terminal: React.FC<{width: number; title: string; children: React.ReactNode; style?: React.CSSProperties; glow?: string}> = ({width, title, children, style, glow}) =>
  <div style={{width, background: DM.panel, borderRadius: 34, border: `2px solid ${DM.line}`, boxShadow: `0 40px 90px rgba(0,0,0,.55)${glow ? `, 0 0 0 3px ${glow}` : ''}`, overflow: 'hidden', ...style}}>
    <div style={{height: 76, display: 'flex', alignItems: 'center', gap: 14, padding: '0 30px', background: DM.panelHi, borderBottom: `2px solid ${DM.line}`}}>
      {[DM.error, DM.ok, DM.ivorySoft].map((c, i) => <div key={i} style={{width: 20, height: 20, borderRadius: 10, background: c, opacity: .85}}/>)}
      <div style={{marginLeft: 18, fontFamily: FONT.mono, fontSize: 32, color: DM.muted}}>{title}</div>
    </div>
    <div style={{padding: '30px 38px'}}>{children}</div>
  </div>;

// ------------------------------------------------------------------------------------------------ 1. hook
const TITLES = ['React in 10 minutes', 'Ultimate Python course', 'Build an AI app, pt 37', 'Docker crash course', 'Git, the right way',
  'Learn Rust fast', 'Next.js full course', 'APIs explained', 'Kubernetes for beginners', 'SQL in one video', 'TypeScript deep dive', 'LLM apps 101'];

export const HookScene: React.FC<SceneProps> = ({scene, f}) => {
  const slow = wf(scene, 3), stuck = wf(scene, 6), still = wf(scene, 5);
  // time warp: the avalanche runs fast, slows on "And", freezes on "stuck?"
  const ft = f < slow ? f : f < stuck ? slow + (f - slow) * .3 : slow + (stuck - slow) * .3;
  const frozen = f >= stuck;
  const count = io(f, 0, Math.max(8, wf(scene, 2)), 9140, 10000, t => 1 - Math.pow(1 - t, 3));
  const hit = sp(f, wf(scene, 2), 9, 220);
  const up = io(f, slow, slow + 12);
  const slam = sp(f, stuck, 10, 260);
  const shake = frozen && f < stuck + 9 ? (rand(f) - .5) * 26 * (1 - (f - stuck) / 9) : 0;
  const glitch = frozen && f < stuck + 6;
  const push = 1 + f * .0009;
  const cards = Array.from({length: 30}, (_, i) => {
    const start = i * 2.4 - 34;
    const speed = 30 + rand(i) * 22;
    const y = -260 + (ft - start) * speed;
    const x = rand(i + 50) * 860 - 80;
    const layer = rand(i + 9);
    return {i, x, y, rot: (rand(i + 3) - .5) * 26 + (ft - start) * (rand(i + 7) - .5) * .8, layer, title: TITLES[i % TITLES.length], prog: rand(i + 2)};
  }).filter(c => c.y > -300 && c.y < 2100);
  return <AbsoluteFill style={{transform: `scale(${push}) translate(${shake}px, ${shake * .4}px)`}}>
    {cards.map(c => <div key={c.i} style={abs({left: c.x, top: c.y, width: 400, padding: '22px 26px', borderRadius: 24, background: DM.panel,
      border: `2px solid ${DM.line}`, transform: `rotate(${c.rot}deg) scale(${.75 + c.layer * .4})`, opacity: (.35 + c.layer * .5) * (frozen ? .55 : 1),
      filter: `blur(${(1 - c.layer) * 3}px)${frozen ? ' grayscale(1)' : ''}`})}>
      <div style={{display: 'flex', alignItems: 'center', gap: 14}}>
        <div style={{width: 40, height: 28, borderRadius: 8, background: DM.orangeDeep, display: 'flex', alignItems: 'center', justifyContent: 'center', color: DM.ivory, fontSize: 18}}>▶</div>
        <div style={{fontFamily: FONT.sans, fontWeight: 700, fontSize: 30, color: DM.ivory, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'}}>{c.title}</div>
      </div>
      <div style={{marginTop: 18, height: 8, borderRadius: 4, background: DM.line}}><div style={{width: `${18 + c.prog * 70}%`, height: '100%', borderRadius: 4, background: DM.orange}}/></div>
    </div>)}
    <AbsoluteFill style={{background: `radial-gradient(ellipse 62% 30% at 50% 36%, rgba(20,20,22,.94), rgba(20,20,22,.55) 70%, transparent)`}}/>
    {/* counter */}
    <div style={abs({left: 0, right: 0, top: 520, textAlign: 'center', transform: `translateY(${-up * 250}px) scale(${(1 + (1 - hit) * .12) * (1 - up * .35)})`})}>
      <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 250, letterSpacing: '-0.04em', color: DM.ivory, fontVariantNumeric: 'tabular-nums', lineHeight: 1}}>{fmt(count)}</div>
      <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 52, letterSpacing: '0.32em', color: DM.orange, marginTop: 18}}>TUTORIALS</div>
    </div>
    {/* still stuck? */}
    <div style={abs({left: 0, right: 0, top: 830, textAlign: 'center', fontFamily: FONT.sans, fontWeight: 900, lineHeight: .92, letterSpacing: '-0.035em'})}>
      <div style={{fontSize: 190, color: DM.ivory, opacity: io(f, still - 2, still + 3), transform: `translateY(${(1 - io(f, still - 2, still + 5)) * 40}px)`}}>STILL</div>
      <div style={{position: 'relative', fontSize: 236, color: DM.orange, opacity: f >= stuck ? 1 : 0, transform: `scale(${1.7 - .7 * slam})`}}>
        {glitch && <span style={abs({left: 0, right: 0, color: '#00e5ff', opacity: .55, transform: 'translate(-14px, 4px)'})}>STUCK?</span>}
        {glitch && <span style={abs({left: 0, right: 0, color: DM.error, opacity: .6, transform: 'translate(12px, -5px)'})}>STUCK?</span>}
        <span style={{position: 'relative'}}>STUCK?</span>
      </div>
    </div>
    {/* error terminal */}
    <div style={abs({left: 120, top: 1330, opacity: io(f, stuck, stuck + 3), transform: `translateY(${(1 - slam) * 60}px) translateX(${glitch ? (rand(f + 3) - .5) * 40 : 0}px)`})}>
      <Terminal width={840} title="~/my-app" glow={DM.error}>
        <div style={{fontFamily: FONT.mono, fontSize: 40, color: DM.ivorySoft}}>$ npm run build</div>
        <div style={{fontFamily: FONT.mono, fontSize: 40, color: DM.error, marginTop: 14, fontWeight: 700}}>✖ build failed (exit 1)</div>
      </Terminal>
    </div>
  </AbsoluteFill>;
};

// ------------------------------------------------------------------------------------------------ 2. reveal
export const RevealScene: React.FC<SceneProps> = ({scene, f, mouth}) => {
  const burst = 14;
  const crack = io(f, 0, burst);
  const blown = io(f, burst, burst + 16, 0, 1, t => t * t);
  const pop = sp(f, burst, 9, 120, .8);
  const land = burst + 16;
  const squash = f >= land && f < land + 10 ? Math.sin((f - land) / 10 * Math.PI) * .9 * (1 - (f - land) / 12) : 0;
  const arc = io(f, burst, land, 0, 1, t => t);
  const mimoY = f < burst ? 1560 : f < land ? 1560 - Math.sin(arc * Math.PI) * 420 - arc * 110 : 1450;
  const meet = wf(scene, 0), name = wf(scene, 1);
  const shake = f < burst ? (rand(f) - .5) * 20 * crack : 0;
  const rays = io(f, burst, burst + 20);
  const wave = io(f, land + 22, land + 30) * (1 - io(f, scene.frames - 12, scene.frames - 2));
  return <AbsoluteFill>
    {/* light rays */}
    <AbsoluteFill style={{opacity: rays * .9, background: `repeating-conic-gradient(from ${f * .6}deg at 50% 62%, rgba(255,122,26,.13) 0deg 7deg, transparent 7deg 20deg)`,
      maskImage: 'radial-gradient(circle at 50% 62%, black 10%, transparent 62%)', WebkitMaskImage: 'radial-gradient(circle at 50% 62%, black 10%, transparent 62%)'}}/>
    <AbsoluteFill style={{background: `radial-gradient(circle at 50% 62%, rgba(255,140,50,${.55 * (1 - io(f, burst, burst + 14))}), transparent ${20 + 50 * io(f, burst, burst + 14)}%)`}}/>
    {/* leftover punch word drifts away */}
    <div style={abs({left: 0, right: 0, top: 830 - f * 6, textAlign: 'center', fontFamily: FONT.sans, fontWeight: 900, fontSize: 236, color: DM.orange, letterSpacing: '-0.035em',
      opacity: 1 - io(f, 2, burst), filter: `blur(${io(f, 2, burst) * 10}px)`})}>STUCK?</div>
    {/* terminal cracks and splits */}
    {[0, 1].map(half => <div key={half} style={abs({left: 120, top: 1330, width: 840, height: 300, overflow: 'hidden',
      clipPath: half === 0 ? 'polygon(0 0, 100% 0, 100% 38%, 62% 52%, 41% 44%, 0 60%)' : 'polygon(0 60%, 41% 44%, 62% 52%, 100% 38%, 100% 100%, 0 100%)',
      transform: `translate(${shake + (half ? 1 : -1) * blown * 520}px, ${(half ? 1 : -1) * blown * 380}px) rotate(${(half ? 1 : -1) * blown * 28}deg)`, opacity: 1 - io(f, burst + 6, burst + 16)})}>
      <Terminal width={840} title="~/my-app" glow={DM.error}>
        <div style={{fontFamily: FONT.mono, fontSize: 40, color: DM.ivorySoft}}>$ npm run build</div>
        <div style={{fontFamily: FONT.mono, fontSize: 40, color: DM.error, marginTop: 14, fontWeight: 700}}>✖ build failed (exit 1)</div>
      </Terminal>
    </div>)}
    {f < burst + 4 && <svg width={1080} height={1920} style={abs({left: 0, top: 0})}>
      <polyline points="150,1530 330,1500 450,1515 560,1470 700,1500 930,1450" fill="none" stroke={DM.orangeHot} strokeWidth={8 + crack * 6}
        strokeDasharray={1000} strokeDashoffset={1000 * (1 - crack)} strokeLinecap="round" style={{filter: `drop-shadow(0 0 ${12 + crack * 20}px ${DM.orange})`}}/>
    </svg>}
    {/* title */}
    <div style={abs({left: 0, right: 0, top: 250, textAlign: 'center'})}>
      <div style={{fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 150, color: DM.ivory, lineHeight: 1, opacity: io(f, meet - 2, meet + 4),
        transform: `translateY(${(1 - io(f, meet - 2, meet + 8)) * 40}px)`}}>Meet</div>
      <div style={{display: 'flex', justifyContent: 'center', fontFamily: FONT.sans, fontWeight: 900, fontSize: 290, color: DM.orange, letterSpacing: '-0.04em', lineHeight: .95}}>
        {[...'Mimo'].map((c, i) => { const k = sp(f, name + i * 2, 11, 200); return <span key={i} style={{display: 'inline-block', opacity: Math.min(1, k * 1.5), transform: `translateY(${(1 - k) * 120}px) rotate(${(1 - k) * (i % 2 ? 12 : -12)}deg)`}}>{c}</span>; })}
      </div>
    </div>
    {f >= burst && <MimoAt x={540} y={mimoY} size={560 * (.3 + .7 * pop)} rotate={f < land ? (1 - arc) * -18 : 0}>
      <Mimo size={560 * (.3 + .7 * pop)} frame={f} mouth={mouth} squash={squash - (f < land ? .35 * (1 - arc) : 0)} expression={f < land + 8 ? 'surprised' : 'happy'}
        blinkAt={[land + 10, land + 17]} wave={wave} glow={1 + .5 * (1 - io(f, burst, burst + 20))} look={{x: 0, y: f < land ? -.6 : 0}}/>
    </MimoAt>}
  </AbsoluteFill>;
};

// ------------------------------------------------------------------------------------------------ 3. build
const TOOLS = ['>_ terminal', '⑂ git', '◎ agents', '{ } API'];
const CODE = ['$ git clone <repo>', '$ npm install', '$ npm run dev', '✓ ready on :3000'];

export const BuildScene: React.FC<SceneProps> = ({scene, f, mouth}) => {
  const real = wf(scene, 2), short = wf(scene, 9), follow = wf(scene, 13);
  const editorIn = sp(f, 34, 13, 150);
  const morph = io(f, short - 2, short + 14);
  const typeStart = 44, typeEnd = Math.max(typeStart + 30, short - 6);
  const chars = io(f, typeStart, typeEnd, 0, CODE.join('').length, t => t);
  const prog = io(f, follow - 10, scene.frames - 16);
  const exit = io(f, scene.frames - 7, scene.frames);
  let left = chars;
  const w = 900 - morph * 340, h = 560 + morph * 160;
  const cx = 540 + morph * 70;
  return <AbsoluteFill style={{transform: `translateX(${-exit * 1080}px)`, filter: exit > 0 ? `blur(${exit * 18}px)` : undefined}}>
    {/* headline */}
    <div style={abs({left: 80, right: 80, top: 190, fontFamily: FONT.sans, fontWeight: 900, color: DM.ivory, letterSpacing: '-0.03em', lineHeight: 1})}>
      <div style={{fontSize: 104, opacity: io(f, real - 2, real + 4), transform: `translateX(${(1 - io(f, real - 2, real + 8)) * -60}px)`}}>
        <span style={{fontFamily: FONT.serif, fontStyle: 'italic', fontWeight: 400, color: DM.orange, fontSize: 124}}>real </span>dev tools
      </div>
      <div style={{fontSize: 104, marginTop: 14, opacity: io(f, short - 2, short + 4), transform: `translateX(${(1 - io(f, short - 2, short + 8)) * -60}px)`}}>
        → <span style={{borderBottom: `12px solid ${DM.orange}`}}>short builds</span>
      </div>
    </div>
    {/* tool chips fly in, then into the editor */}
    {TOOLS.map((t, i) => {
      const k = sp(f, 10 + i * 6, 12, 170);
      const suck = io(f, 36 + i * 2, 48 + i * 2, 0, 1, t2 => t2 * t2);
      const x0 = 90 + (i % 2) * 460, y0 = 560 + Math.floor(i / 2) * 120;
      const x = x0 + (1 - k) * 900 + suck * (540 - 200 - x0), y = y0 + suck * (980 - y0);
      return <div key={t} style={abs({left: x, top: y, width: 420, height: 96, borderRadius: 48, border: `3px solid ${DM.orange}`, background: DM.charcoal2,
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.mono, fontWeight: 700, fontSize: 44, color: DM.ivory,
        opacity: 1 - io(f, 44 + i * 2, 50 + i * 2), transform: `scale(${1 - suck * .6})`})}>{t}</div>;
    })}
    {/* editor → build card */}
    <div style={abs({left: cx - w / 2, top: 760 - morph * 60, width: w, height: h, opacity: Math.min(1, editorIn * 1.4), transform: `scale(${.6 + .4 * editorIn})`,
      transformOrigin: '50% 30%', borderRadius: 34 + morph * 10, background: DM.panel, border: `2px solid ${morph > .5 ? DM.orange : DM.line}`,
      boxShadow: `0 40px 100px rgba(0,0,0,.6), 0 0 ${60 * morph}px ${DM.orangeGlow}`, overflow: 'hidden'})}>
      <div style={{height: 76, display: 'flex', alignItems: 'center', gap: 14, padding: '0 30px', background: DM.panelHi, borderBottom: `2px solid ${DM.line}`}}>
        {[DM.error, DM.ok, DM.ivorySoft].map((c, i) => <div key={i} style={{width: 20, height: 20, borderRadius: 10, background: c, opacity: .85}}/>)}
        <div style={{marginLeft: 18, fontFamily: FONT.mono, fontSize: 32, color: DM.muted}}>{morph < .5 ? 'build_01.sh' : 'BUILD 01'}</div>
      </div>
      <div style={{padding: '36px 40px', opacity: 1 - io(morph, .1, .45, 0, 1, t => t)}}>
        {CODE.map((line, i) => {
          const shown = line.slice(0, Math.max(0, Math.floor(left)));
          left -= line.length;
          return <div key={i} style={{fontFamily: FONT.mono, fontSize: 46, lineHeight: 1.75, color: line.startsWith('✓') ? DM.ok : DM.ivory, whiteSpace: 'nowrap'}}>
            {shown}{shown.length > 0 && shown.length < line.length && <span style={{color: DM.orange}}>▍</span>}
          </div>;
        })}
      </div>
      <div style={abs({left: 0, right: 0, top: 76, bottom: 0, padding: '44px 46px', opacity: io(morph, .5, .9, 0, 1, t => t)})}>
        <div style={{fontFamily: FONT.mono, fontSize: 34, letterSpacing: '0.2em', color: DM.orange}}>BUILD 01</div>
        <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 76, lineHeight: 1.02, color: DM.ivory, marginTop: 14, letterSpacing: '-0.02em'}}>repo<br/>→ running<br/>app</div>
        {['clone', 'install', 'run'].map((s, i) => {
          const on = prog > (i + 1) / 3.4;
          return <div key={s} style={{display: 'flex', alignItems: 'center', gap: 20, marginTop: i ? 16 : 34, fontFamily: FONT.mono, fontSize: 42, color: on ? DM.ivory : DM.muted}}>
            <div style={{width: 46, height: 46, borderRadius: 12, border: `3px solid ${on ? DM.orange : DM.line}`, background: on ? DM.orange : 'transparent',
              color: DM.charcoal, fontSize: 32, fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>{on ? '✓' : ''}</div>{s}</div>;
        })}
        <div style={abs({left: 46, right: 46, bottom: 46, height: 14, borderRadius: 7, background: DM.line})}>
          <div style={{width: `${prog * 100}%`, height: '100%', borderRadius: 7, background: DM.orange}}/>
        </div>
      </div>
    </div>
    <div style={abs({left: 80, right: 80, top: 1500, textAlign: 'right', fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 84, color: DM.ivory,
      opacity: io(f, follow - 14, follow - 6)})}>you can actually <span style={{color: DM.orange}}>follow.</span></div>
    <MimoAt x={210} y={1760} size={330}>
      <Mimo size={330} frame={f + 200} mouth={mouth} typing={io(f, 44, 50) * (1 - io(f, short - 6, short))} look={{x: .8, y: -.6}}
        expression={f > follow ? 'happy' : 'neutral'} blinkAt={[real]}/>
    </MimoAt>
  </AbsoluteFill>;
};

// ------------------------------------------------------------------------------------------------ 4. topics
const PanelTitle: React.FC<{n: number; lead: string; rest: string}> = ({n, lead, rest}) =>
  <div style={abs({left: 80, right: 80, top: 210})}>
    <div style={{fontFamily: FONT.mono, fontSize: 38, letterSpacing: '0.24em', color: DM.muted}}>0{n} / 03</div>
    <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: 128, lineHeight: 1, letterSpacing: '-0.035em', color: DM.ivory, marginTop: 18}}>
      <span style={{color: DM.orange}}>{lead}</span> {rest}</div>
  </div>;

const Pill: React.FC<{x: number; y: number; label: string; on?: boolean; w?: number}> = ({x, y, label, on = true, w = 250}) =>
  <div style={abs({left: x - w / 2, top: y - 46, width: w, height: 92, borderRadius: 46, background: DM.panel, border: `3px solid ${on ? DM.orange : DM.line}`,
    display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.mono, fontWeight: 700, fontSize: 44, color: DM.ivory})}>{label}</div>;

const AgentPanel: React.FC<{f: number}> = ({f}) => {
  const R = 320, cx = 540, cy = 980;
  const nodes = [['plan', -90], ['act', 30], ['check', 150]] as const;
  const draw = io(f, 4, 26);
  const a = (f * 5 - 90) * Math.PI / 180;
  return <>
    <svg width={1080} height={1920} style={abs({left: 0, top: 0})}>
      <circle cx={cx} cy={cy} r={R} fill="none" stroke={DM.orange} strokeWidth={6} strokeDasharray={`${2 * Math.PI * R * draw} 9999`} transform={`rotate(-90 ${cx} ${cy})`} opacity={.8}/>
      <circle cx={cx} cy={cy} r={R} fill="none" stroke={DM.line} strokeWidth={2} strokeDasharray="6 14"/>
      <circle cx={cx + R * Math.cos(a)} cy={cy + R * Math.sin(a)} r={16} fill={DM.orangeHot} opacity={draw} style={{filter: `drop-shadow(0 0 14px ${DM.orange})`}}/>
    </svg>
    <div style={abs({left: cx - 120, top: cy - 120, width: 240, height: 240, borderRadius: 120, background: DM.charcoal2, border: `4px solid ${DM.orange}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${sp(f, 0, 12, 160)})`})}><LogoMark size={150}/></div>
    {nodes.map(([label, deg], i) => { const r = deg * Math.PI / 180; const k = sp(f, 6 + i * 5, 12, 180);
      return <div key={label} style={{transform: `scale(${k})`, transformOrigin: `${cx + R * Math.cos(r)}px ${cy + R * Math.sin(r)}px`, position: 'absolute', inset: 0}}>
        <Pill x={cx + R * Math.cos(r)} y={cy + R * Math.sin(r)} label={label} w={230}/></div>; })}
  </>;
};

const McpPanel: React.FC<{f: number}> = ({f}) => {
  const hub = {x: 600, y: 980};
  const plugs = [['files', 720], ['repo', 980], ['data', 1240]] as const;
  return <>
    <svg width={1080} height={1920} style={abs({left: 0, top: 0})}>
      {plugs.map(([label, y], i) => { const d = io(f, 4 + i * 4, 16 + i * 4); const on = f >= 16 + i * 4;
        return <path key={label} d={`M 330 ${y} C 430 ${y}, 420 ${hub.y}, ${hub.x - 170} ${hub.y}`} fill="none" stroke={on ? DM.orange : DM.line} strokeWidth={7}
          strokeDasharray={600} strokeDashoffset={600 * (1 - d)} style={{filter: on ? `drop-shadow(0 0 10px ${DM.orange})` : undefined}}/>; })}
      <path d={`M ${hub.x + 170} ${hub.y} L 900 ${hub.y}`} stroke={f >= 30 ? DM.orange : DM.line} strokeWidth={7} strokeDasharray={260} strokeDashoffset={260 * (1 - io(f, 24, 32))}/>
    </svg>
    {plugs.map(([label, y], i) => <div key={label} style={{position: 'absolute', inset: 0, transform: `translateX(${(1 - sp(f, i * 4, 13, 180)) * -500}px)`}}>
      <Pill x={200} y={y} label={label} on={f >= 16 + i * 4} w={240}/></div>)}
    <div style={abs({left: hub.x - 170, top: hub.y - 110, width: 340, height: 220, borderRadius: 40, background: DM.charcoal2, border: `5px solid ${DM.orange}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT.mono, fontWeight: 700, fontSize: 92, color: DM.ivory,
      boxShadow: `0 0 ${f >= 16 ? 70 : 0}px ${DM.orangeGlow}`, transform: `scale(${sp(f, 0, 11, 170)})`})}>MCP</div>
    <div style={abs({left: 900 - 20, top: hub.y - 34, width: 68, height: 68, borderRadius: 20, background: DM.orange, opacity: io(f, 28, 32), transform: `scale(${sp(f, 28, 10, 200)})`})}/>
  </>;
};

const TREE = ['repo/', '├── src/', '├── examples/', '├── README.md', '└── LICENSE'];
const RepoPanel: React.FC<{f: number; worth: number}> = ({f, worth}) =>
  <>
    <div style={abs({left: 110, top: 600, width: 860, padding: '40px 50px', borderRadius: 36, background: DM.panel, border: `2px solid ${DM.line}`,
      transform: `translateY(${(1 - sp(f, 0, 13, 160)) * 200}px)`})}>
      {TREE.map((line, i) => <div key={line} style={{fontFamily: FONT.mono, fontSize: 54, lineHeight: 1.6, color: i ? DM.ivory : DM.orange, fontWeight: i ? 500 : 700,
        opacity: io(f, 4 + i * 4, 8 + i * 4), transform: `translateX(${(1 - io(f, 4 + i * 4, 10 + i * 4)) * 40}px)`, whiteSpace: 'nowrap'}}>{line}</div>)}
      <div style={abs({right: 46, top: 40, fontSize: 80, color: DM.orange, transform: `scale(${sp(f, 24, 8, 200)}) rotate(${f * 2}deg)`,
        filter: `drop-shadow(0 0 16px ${DM.orange})`})}>★</div>
    </div>
    <div style={abs({left: 0, right: 0, top: 1300, textAlign: 'center', fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 120, color: DM.ivory,
      opacity: io(f, worth - 3, worth + 3), transform: `translateY(${(1 - io(f, worth - 3, worth + 8)) * 40}px)`})}>worth your <span style={{color: DM.orange}}>time.</span></div>
  </>;

export const TopicsScene: React.FC<SceneProps> = ({scene, f, mouth}) => {
  const starts = [0, wf(scene, 2) - 3, wf(scene, 4) - 3];
  const idx = f >= starts[2] ? 2 : f >= starts[1] ? 1 : 0;
  const local = f - starts[idx];
  const enter = idx === 0 ? io(f, 0, 7) : io(local, 0, 7);
  const titles: [string, string][] = [['AI', 'agents'], ['MCP', 'servers'], ['Open-source', 'repos']];
  const hop = local < 10 ? Math.sin(local / 10 * Math.PI) : 0;
  return <AbsoluteFill>
    <AbsoluteFill style={{transform: `translateX(${(1 - enter) * 1080}px)`, filter: enter < 1 ? `blur(${(1 - enter) * 20}px)` : undefined}}>
      <PanelTitle n={idx + 1} lead={titles[idx][0]} rest={titles[idx][1]}/>
      {idx === 0 && <AgentPanel f={local}/>}
      {idx === 1 && <McpPanel f={local}/>}
      {idx === 2 && <RepoPanel f={local} worth={wf(scene, 6) - starts[2]}/>}
    </AbsoluteFill>
    <MimoAt x={880} y={1800 - hop * 60} size={250}>
      <Mimo size={250} frame={f + 400} mouth={mouth} look={{x: -.7, y: -.7}} squash={-hop * .4} expression={idx === 2 && f > wf(scene, 6) ? 'happy' : 'neutral'}/>
    </MimoAt>
  </AbsoluteFill>;
};

// ------------------------------------------------------------------------------------------------ 5. no fluff
const CHECKS = ['the commands', 'the code', 'why it works'];
export const NoFluffScene: React.FC<SceneProps> = ({scene, f, mouth}) => {
  const fluff = wf(scene, 1);
  const strike = io(f, fluff + 2, fluff + 8);
  const crush = io(f, fluff + 12, fluff + 22, 0, 1, t => t * t);
  const at = [wf(scene, 4), wf(scene, 6), wf(scene, 8)];
  const flash = f < 3 ? 1 - f / 3 : 0;
  return <AbsoluteFill>
    <div style={abs({left: 0, right: 0, top: 220, textAlign: 'center', fontFamily: FONT.sans, fontWeight: 900, letterSpacing: '-0.04em', lineHeight: .95})}>
      <div style={{fontSize: 200, color: DM.ivory, transform: `scale(${1.4 - .4 * sp(f, 0, 10, 240)})`}}>NO</div>
      <div style={{position: 'relative', display: 'inline-block', fontSize: 250, color: 'transparent', WebkitTextStroke: `6px ${DM.orange}`,
        transform: `scaleY(${1 - crush * .85}) translateY(${crush * 120}px)`, opacity: 1 - crush}}>
        FLUFF
        <div style={abs({left: -20, top: '50%', height: 24, width: `${strike * 110}%`, background: DM.ivory, borderRadius: 12, transform: 'rotate(-4deg)'})}/>
      </div>
    </div>
    <div style={abs({left: 0, right: 0, top: 470, textAlign: 'center', fontFamily: FONT.serif, fontStyle: 'italic', fontSize: 150, color: DM.ivory,
      opacity: io(f, fluff + 18, fluff + 26)})}>just</div>
    <div style={abs({left: 90, top: 760, transform: `translateY(${(1 - sp(f, fluff + 14, 13, 150)) * 900}px)`})}>
      <Terminal width={900} title="mimo@dev ~ %">
        {CHECKS.map((c, i) => {
          const k = sp(f, at[i], 10, 220);
          const on = f >= at[i];
          const last = i === CHECKS.length - 1;
          return <div key={c} style={{display: 'flex', alignItems: 'center', gap: 28, padding: '18px 22px', borderRadius: 20, marginTop: i ? 12 : 0,
            background: on && last ? 'rgba(255,122,26,.16)' : 'transparent', opacity: on ? 1 : .32}}>
            <div style={{width: 70, height: 70, borderRadius: 18, border: `4px solid ${on ? DM.orange : DM.line}`, background: on ? DM.orange : 'transparent',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 48, fontWeight: 900, color: DM.charcoal, transform: `scale(${on ? .7 + .3 * k : 1})`}}>{on ? '✓' : ''}</div>
            <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: 60, color: on && last ? DM.orangeHot : DM.ivory}}>{c}</div>
          </div>;
        })}
      </Terminal>
    </div>
    <MimoAt x={220} y={1780} size={300}>
      <Mimo size={300} frame={f + 600} mouth={mouth} look={{x: .6, y: -.6}} expression={f >= at[2] + 6 ? 'happy' : f < fluff + 12 && f > fluff ? 'focused' : 'neutral'}/>
    </MimoAt>
    <AbsoluteFill style={{background: DM.ivory, opacity: flash * .5}}/>
  </AbsoluteFill>;
};

// ------------------------------------------------------------------------------------------------ 6. outro
export const OutroScene: React.FC<SceneProps> = ({scene, f, mouth}) => {
  const follow = wf(scene, 3), real = wf(scene, 9);
  const iris = io(f, 0, 16, 0, 1500);
  const btn = sp(f, follow - 2, 11, 170);
  const press = f >= follow + 16 && f < follow + 22 ? .94 : 1;
  const cursor = io(f, follow + 2, follow + 16);
  const ring = ((f - follow) % 36) / 36;
  return <AbsoluteFill style={{clipPath: `circle(${iris}px at 50% 46%)`}}>
    <AbsoluteFill style={{background: `radial-gradient(ellipse 70% 40% at 50% 40%, rgba(255,122,26,.10), transparent 70%)`}}/>
    <div style={abs({left: 0, top: 130, width: 1080, display: 'flex', justifyContent: 'center'})}><LogoReveal f={f} scale={.86}/></div>
    <div style={abs({left: 0, right: 0, top: 840, display: 'flex', justifyContent: 'center'})}>
      <div style={{position: 'relative', transform: `scale(${btn * press})`}}>
        {f > follow + 4 && <div style={abs({inset: -18 - ring * 40, borderRadius: 90, border: `4px solid ${DM.orange}`, opacity: (1 - ring) * .7})}/>}
        <div style={{padding: '30px 64px', borderRadius: 70, background: DM.orange, fontFamily: FONT.sans, fontWeight: 900, fontSize: 64, color: DM.charcoal, whiteSpace: 'nowrap'}}>
          + Follow along</div>
        <svg width={80} height={96} viewBox="0 0 40 48" style={abs({left: 300 + (1 - cursor) * 320, top: 70 + (1 - cursor) * 260, opacity: f > follow + 2 && f < follow + 50 ? 1 : 0})}>
          <path d="M4 2 L4 38 L13 30 L19 44 L25 41 L19 28 L31 28 Z" fill={DM.ivory} stroke={DM.charcoal} strokeWidth={2.5} strokeLinejoin="round"/>
        </svg>
      </div>
    </div>
    <MimoAt x={540} y={1610} size={400}>
      <Mimo size={400} frame={f + 800} mouth={mouth} wave={io(f, 16, 24) * (1 - io(f, follow, follow + 6)) + io(f, real + 4, real + 12)}
        expression={f >= real + 4 ? 'happy' : f >= follow + 14 && f < follow + 34 ? 'wink' : 'neutral'} look={{x: 0, y: f < follow ? -.8 : f < real ? -.3 : 0}}/>
    </MimoAt>
  </AbsoluteFill>;
};
