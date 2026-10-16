import React from 'react';
import {AbsoluteFill} from 'remotion';
import {DM, accentA} from './theme';

/* Ground stage: a slow-drifting dot grid, a cool accent key light and a vignette. Cheap enough to sit under every scene. */
export const Backdrop: React.FC<{f: number; intensity?: number; keyX?: number; keyY?: number; grid?: number}> = ({f, intensity = .6, keyX = 50, keyY = 42, grid = 1}) =>
  <AbsoluteFill style={{background: DM.charcoal, overflow: 'hidden'}}>
    <AbsoluteFill style={{
      backgroundImage: `radial-gradient(${DM.line} 2.2px, transparent 2.6px)`, backgroundSize: '54px 54px',
      backgroundPosition: `${(f * .35) % 54}px ${(f * .6) % 54}px`, opacity: .55 * grid,
      maskImage: 'radial-gradient(ellipse 70% 60% at 50% 45%, black 30%, transparent 85%)',
      WebkitMaskImage: 'radial-gradient(ellipse 70% 60% at 50% 45%, black 30%, transparent 85%)'}}/>
    <AbsoluteFill style={{background: `radial-gradient(ellipse 60% 38% at ${keyX}% ${keyY}%, ${accentA(.16 * intensity)}, transparent 70%)`}}/>
    <AbsoluteFill style={{background: 'radial-gradient(ellipse 85% 70% at 50% 50%, transparent 55%, rgba(0,0,0,.55) 100%)'}}/>
  </AbsoluteFill>;
