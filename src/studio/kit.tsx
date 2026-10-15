import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {Beat, Props, Scene} from '../shared';
import {Palette, Variant} from './tokens';

export const cl = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export type LayoutProps = {beat: Beat; scene: Scene; props: Props; P: Palette; v: Variant; index: number; hit: number | null; dur: number};

export const Panel: React.FC<{P: Palette; style?: React.CSSProperties; children?: React.ReactNode}> = ({P, style, children}) =>
  <div style={{background: P.surface, border: `3px solid ${P.line}`, borderRadius: 28, boxShadow: P.dark ? '0 24px 60px #00000060' : '0 24px 60px #2a201420', ...style}}>{children}</div>;

/** Hand-drawn marker loop that draws itself around content. */
export const Marker: React.FC<{at: number; width: number; height: number; color: string}> = ({at, width, height, color}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [at, at + 14], [0, 1], cl);
  return <svg width={width} height={height} viewBox="0 0 100 60" preserveAspectRatio="none" style={{position: 'absolute', left: -width * .06, top: -height * .14, overflow: 'visible', pointerEvents: 'none'}}>
    <path d="M8 34 C4 12 40 3 64 6 C92 9 100 28 90 44 C80 58 30 60 14 50 C4 44 6 30 22 22" fill="none" stroke={color} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - p}
      vectorEffect="non-scaling-stroke" style={{strokeWidth: 7}} strokeLinecap="round"/>
  </svg>;
};
