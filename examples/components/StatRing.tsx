import React from 'react';
import {useCurrentFrame} from 'remotion';
import {LayoutProps} from '../../kit';
import {Counter, progress} from '../../motion';
import {FONT, clampText} from '../../tokens';

/** A ring fills to the scene's percentage stat while the number counts up. Example of a forge-submitted component. */
export const StatRing: React.FC<LayoutProps> = ({scene, P}) => {
  const f = useCurrentFrame();
  const stat = scene.stat || '';
  const pct = Math.max(0, Math.min(100, Number((stat.match(/[\d.]+/) ?? ['0'])[0])));
  const t = progress(f, {delay: 4, duration: 30});
  const r = 230, c = 2 * Math.PI * r;
  return <div style={{position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 30}}>
    <svg width={560} height={560} viewBox="0 0 560 560">
      <circle cx={280} cy={280} r={r} fill="none" stroke={P.line} strokeWidth={34}/>
      <circle cx={280} cy={280} r={r} fill="none" stroke={P.accent} strokeWidth={34} strokeLinecap="round" strokeDasharray={c}
        strokeDashoffset={c * (1 - (pct / 100) * t)} transform="rotate(-90 280 280)"/>
      <text x={280} y={300} textAnchor="middle" fontFamily={FONT.sans} fontWeight={850} fontSize={120} fill={P.ink}><Counter value={stat || '0'}/></text>
    </svg>
    <div style={{fontFamily: FONT.sans, fontWeight: 700, fontSize: 44, color: P.ink}}>{clampText(scene.heading, 30)}</div>
  </div>;
};
