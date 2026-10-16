import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ensureFonts} from '../premium/tokens';
import {MimoMascot, MimoState, ProjectVisual} from './Visuals';
import {accentA, CoverProps, EpisodeInfo, FONT, fitSize, inkA, S, SAFE, SeriesInfo} from './theme';

/* Dedicated Reels-grid cover (1080×1920 master; the 4:5 and 1:1 previews are centre crops of it). Everything essential sits inside the
   square safe region (series.json safe_zone.cover_square), so every crop keeps the header, episode number, headline, illustration,
   mascot and footer. `mask` renders essential elements as solid white on black for the overflow/crop QA. */

const Q = SAFE.cover_square;
const Essential: React.FC<{mask?: boolean; children: React.ReactNode; style?: React.CSSProperties}> = ({mask, children, style}) =>
  <div style={{...style, filter: mask ? 'brightness(0) invert(1)' : undefined}}>{children}</div>;

export const SeriesHeader: React.FC<{text: string; size?: number; color?: string}> = ({text, size = 32, color = S.accent}) =>
  <div style={{fontFamily: FONT.mono, fontWeight: 700, fontSize: size, letterSpacing: size * .2, color, whiteSpace: 'nowrap'}}>{text}</div>;

export const EpisodeNumber: React.FC<{label: string; size?: number; solid?: boolean}> = ({label, size = 72, solid = true}) =>
  <div style={{display: 'inline-flex', alignItems: 'center', fontFamily: FONT.mono, fontWeight: 700, fontSize: size, lineHeight: 1,
    letterSpacing: size * .04, color: solid ? S.ground : S.accent, background: solid ? S.accent : 'transparent',
    border: solid ? 'none' : `3px solid ${S.accent}`, padding: `${size * .2}px ${size * .32}px`, borderRadius: size * .22, whiteSpace: 'nowrap'}}>{label}</div>;

export const HEADLINE_MAX = 150;
export const CoverHeadline: React.FC<{lines: string[]; width: number; max?: number}> = ({lines, width, max = HEADLINE_MAX}) => {
  const size = fitSize(lines, width, max);
  return <div style={{fontFamily: FONT.sans, fontWeight: 900, fontSize: size, lineHeight: .95, letterSpacing: -size * .02, textAlign: 'center'}}>
    {lines.map((l, i) => <div key={i} style={{color: i === lines.length - 1 && lines.length > 1 ? S.accent : S.ink, whiteSpace: 'nowrap'}}>{l}</div>)}
  </div>;
};

export const BrandFooter: React.FC<{text: string; size?: number}> = ({text, size = 30}) => {
  const [brand, ...rest] = text.split(' · ');
  return <div style={{fontFamily: FONT.sans, fontSize: size, color: S.muted, whiteSpace: 'nowrap', letterSpacing: .5}}>
    <span style={{color: S.ink, fontWeight: 800}}>{brand}</span>{rest.length ? <> <span style={{color: S.accent}}>·</span> {rest.join(' · ')}</> : null}
  </div>;
};

/** QA overlay: square and 4:5 crop outlines. Never part of an export. */
export const CoverSafeZone: React.FC = () =>
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    <div style={{position: 'absolute', left: 0, right: 0, top: 285, height: 1350, border: '3px dashed #39f'}}/>
    <div style={{position: 'absolute', left: 0, right: 0, top: 420, height: 1080, border: '3px dashed #f3c'}}/>
    <div style={{position: 'absolute', left: Q.left, top: Q.top, width: Q.right - Q.left, height: Q.bottom - Q.top, border: '3px solid #3f6'}}/>
  </AbsoluteFill>;

const Ground: React.FC<{episode: EpisodeInfo}> = ({episode}) => episode.coverMinimal ? <AbsoluteFill>
    <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
      <defs><radialGradient id="ckey" cx="50%" cy="46%" r="55%"><stop offset="0" stopColor={accentA(.10)}/><stop offset="1" stopColor={accentA(0)}/></radialGradient></defs>
      <rect width={1080} height={1920} fill="url(#ckey)"/>
    </svg></AbsoluteFill> :
  <AbsoluteFill>
    <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
      <defs>
        <pattern id="cdots" width="36" height="36" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.6" fill={inkA(.07)}/></pattern>
        <radialGradient id="ckey" cx="50%" cy="46%" r="55%"><stop offset="0" stopColor={accentA(.10)}/><stop offset="1" stopColor={accentA(0)}/></radialGradient>
      </defs>
      <rect width={1080} height={1920} fill="url(#cdots)"/>
      <rect width={1080} height={1920} fill="url(#ckey)"/>
    </svg>
    {/* outside the square: decorative only (the full 9:16 view shows it; crops drop it) */}
    <div style={{position: 'absolute', top: 120, left: 0, right: 0, textAlign: 'center', fontFamily: FONT.mono, fontWeight: 700, fontSize: 210,
      color: 'transparent', WebkitTextStroke: `2px ${inkA(.09)}`, letterSpacing: 20}}>{String(episode.n).padStart(3, '0')}</div>
    <div style={{position: 'absolute', top: 1560, left: 0, right: 0, textAlign: 'center', fontFamily: FONT.mono, fontSize: 26, color: S.dim, letterSpacing: 3, lineHeight: 1.6}}>
      <div>{episode.category.toUpperCase()}</div><div>github.com/{episode.repo}</div></div>
  </AbsoluteFill>;

export const SeriesCover: React.FC<CoverProps> = ({series, episode, mask = false}) => {
  ensureFonts();
  // the illustration starts below the measured headline, so a short headline set large never collides with it
  const head = fitSize(episode.headline, Q.right - Q.left - 40, HEADLINE_MAX);
  const visTop = Math.max(Q.top + 500, Q.top + 250 + episode.headline.length * head * .95 + 28);
  const visH = Math.min(420, Q.bottom - 96 - visTop);
  return <AbsoluteFill style={{background: mask ? '#000' : S.ground}}>
    {!mask && <Ground episode={episode}/>}
    <Essential mask={mask} style={{position: 'absolute', top: Q.top + 34, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
      <SeriesHeader text={series.header}/></Essential>
    <Essential mask={mask} style={{position: 'absolute', top: Q.top + 100, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
      <EpisodeNumber label={episode.label}/></Essential>
    <Essential mask={mask} style={{position: 'absolute', top: Q.top + 250, left: Q.left + 10, right: 1080 - Q.right + 10, display: 'flex', justifyContent: 'center'}}>
      <CoverHeadline lines={episode.headline} width={Q.right - Q.left - 40}/></Essential>
    <Essential mask={mask} style={{position: 'absolute', top: visTop, left: 90, width: 700, height: visH}}>
      <ProjectVisual visual={episode.visual} w={700} h={visH} assets={episode.visualAssets}/></Essential>
    <Essential mask={mask} style={{position: 'absolute', top: visTop + visH - 230, left: 790, width: 190}}>
      <MimoMascot state={(episode.expression as MimoState) || 'surprised'} size={190} frame={40} amount={1} look={{x: -1, y: -.6}}/></Essential>
    <Essential mask={mask} style={{position: 'absolute', top: Q.bottom - 74, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
      <BrandFooter text={series.footer} size={episode.coverMinimal ? 36 : 30}/></Essential>
  </AbsoluteFill>;
};

export const SeriesCoverGuides: React.FC<CoverProps> = props => <AbsoluteFill><SeriesCover {...props}/><CoverSafeZone/></AbsoluteFill>;
export type {SeriesInfo};
