import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame} from 'remotion';
import {cl} from './kit';
import {FONT, Palette} from './tokens';

/* Motion grammar: every animation is a named behaviour with explicit parameters, built only on frame-based Remotion
   utilities (deterministic: no Date, no Math.random, no CSS transitions).

   ENTER      fade | slide | scale | mask | reveal
   EMPHASIZE  pulse | zoom | highlight | underline | counter
   CONNECT    line_draw | node_link | flow | morph
   EXIT       fade | push | mask | collapse | cut                                                                  */

export const EASE = {
  standard: Easing.bezier(.2, 0, 0, 1),          // Material 3 "emphasized" — editorial default
  enter: Easing.bezier(0, 0, .3, 1),             // IBM Carbon expressive entrance
  exit: Easing.bezier(.4, 0, 1, 1),
  inOut: Easing.inOut(Easing.cubic),
};
export const DURATION = {micro: 6, short: 10, medium: 16, long: 24, draw: 20};    // frames at 30 fps
export const SPRING = {
  gentle: {damping: 22, stiffness: 120, mass: 1},
  snappy: {damping: 14, stiffness: 170, mass: .9},
  overshoot: {damping: 10, stiffness: 160, mass: .8},
};

export type EnterKind = 'fade' | 'slide' | 'scale' | 'mask' | 'reveal';
export type EmphasisKind = 'pulse' | 'zoom' | 'highlight' | 'underline' | 'counter' | 'none';
export type ExitKind = 'fade' | 'push' | 'mask' | 'collapse' | 'cut';
export type Direction = 'up' | 'down' | 'left' | 'right';
export type MotionParams = {delay?: number; duration?: number; amplitude?: number; direction?: Direction; easing?: (t: number) => number};

/** 0..1 progress of a timed behaviour starting at `delay`. */
export const progress = (frame: number, {delay = 0, duration = DURATION.medium, easing = EASE.standard}: MotionParams = {}) =>
  interpolate(frame - delay, [0, duration], [0, 1], {...cl, easing});

const offset = (d: Direction, amount: number) => d === 'up' ? `0, ${amount}px` : d === 'down' ? `0, ${-amount}px` : d === 'left' ? `${amount}px, 0` : `${-amount}px, 0`;

/** Style for an ENTER behaviour. */
export const enterStyle = (kind: EnterKind, frame: number, params: MotionParams = {}): React.CSSProperties => {
  const p = progress(frame, params);
  const a = params.amplitude ?? 1;
  const dir = params.direction ?? 'up';
  if (kind === 'fade') return {opacity: p};
  if (kind === 'slide') return {opacity: Math.min(1, p * 1.4), transform: `translate(${offset(dir, (1 - p) * 90 * a)})`};
  if (kind === 'scale') return {opacity: Math.min(1, p * 1.6), transform: `scale(${1 - (1 - p) * .12 * a})`};
  if (kind === 'mask') return {clipPath: dir === 'left' || dir === 'right' ? `inset(0 ${(1 - p) * 100}% 0 0)` : `inset(${(1 - p) * 100}% 0 0 0)`};
  return {opacity: Math.min(1, p * 2), transform: `translate(${offset(dir, (1 - p) * 40 * a)})`, filter: `blur(${(1 - p) * 8}px)`};
};

/** Style for an EXIT behaviour that ends at `end` frames (relative to the element's local frame). */
export const exitStyle = (kind: ExitKind, frame: number, end: number, params: MotionParams = {}): React.CSSProperties => {
  const duration = params.duration ?? DURATION.short;
  const p = interpolate(frame, [end - duration, end], [0, 1], {...cl, easing: EASE.exit});
  if (kind === 'cut' || p <= 0) return {};
  if (kind === 'fade') return {opacity: 1 - p};
  if (kind === 'push') return {transform: `translateY(${-p * 120}px)`, opacity: 1 - p};
  if (kind === 'mask') return {clipPath: `inset(0 0 ${p * 100}% 0)`};
  return {transform: `scaleY(${1 - p})`, transformOrigin: 'top', opacity: 1 - p * .5};
};

/** EMPHASIZE value (scale multiplier) around a hit frame. */
export const emphasisScale = (kind: EmphasisKind, frame: number, hit: number, amplitude = 1) => {
  const t = frame - hit;
  if (kind === 'pulse') return t < 0 || t > 14 ? 1 : 1 + .06 * amplitude * Math.sin(t / 14 * Math.PI);
  if (kind === 'zoom') return 1 + .08 * amplitude * interpolate(t, [-4, 4, 18], [0, 1, .6], cl);
  return 1;
};

// ---------- primitives ----------

/** Masked line reveal: text rises from behind a clip edge. */
export const MaskedText: React.FC<{text: string; delay?: number; style?: React.CSSProperties; duration?: number}> = ({text, delay = 0, style, duration = DURATION.medium}) => {
  const f = useCurrentFrame();
  const p = progress(f, {delay, duration});
  return <span style={{display: 'inline-block', overflow: 'hidden', verticalAlign: 'bottom', paddingBottom: '.08em'}}>
    <span style={{display: 'inline-block', transform: `translateY(${(1 - p) * 105}%)`, ...style}}>{text}</span>
  </span>;
};

/** Character-by-character reveal with a fixed stagger. */
export const CharReveal: React.FC<{text: string; delay?: number; stagger?: number; style?: React.CSSProperties}> = ({text, delay = 0, stagger = 1.2, style}) => {
  const f = useCurrentFrame();
  return <span style={{whiteSpace: 'pre-wrap', ...style}}>{text.split('').map((c, i) => {
    const p = progress(f, {delay: delay + i * stagger, duration: DURATION.short});
    return <span key={i} style={{opacity: p, display: 'inline-block', transform: `translateY(${(1 - p) * 18}px)`}}>{c === ' ' ? ' ' : c}</span>;
  })}</span>;
};

/** Word-by-word reveal with one emphasised word (highlight sweep or underline draw). */
export const WordEmphasis: React.FC<{text: string; emphasis?: string; P: Palette; kind?: EmphasisKind; delay?: number; size: number; serif?: boolean}> =
  ({text, emphasis = '', P, kind = 'highlight', delay = 0, size, serif}) => {
    const f = useCurrentFrame();
    const key = emphasis.toLowerCase().split(/\s+/)[0];
    return <div style={{display: 'flex', flexWrap: 'wrap', columnGap: size * .26, rowGap: size * .08}}>
      {text.split(/\s+/).map((w, i) => {
        const p = progress(f, {delay: delay + i * 2.5, duration: DURATION.short});
        const hot = !!key && w.toLowerCase().replace(/[^\w$%]/g, '').startsWith(key.replace(/[^\w$%]/g, ''));
        const sweep = progress(f, {delay: delay + i * 2.5 + 8, duration: DURATION.medium}) * 100;
        return <span key={i} style={{position: 'relative', display: 'inline-block', fontFamily: serif ? FONT.serif : FONT.sans, fontSize: size, lineHeight: 1.08,
          fontWeight: serif ? 500 : 780, letterSpacing: -size * .02, color: hot && kind !== 'highlight' ? P.accent : P.ink, opacity: p, transform: `translateY(${(1 - p) * 24}px)`,
          backgroundImage: hot && kind === 'highlight' ? `linear-gradient(90deg, ${P.hl}${P.dark ? '66' : '55'} ${sweep}%, transparent ${sweep}%)` : undefined,
          padding: hot && kind === 'highlight' ? '0 .08em' : undefined}}>
          {w}
          {hot && kind === 'underline' && <span style={{position: 'absolute', left: 0, bottom: -size * .06, height: Math.max(4, size * .06), width: `${sweep}%`, background: P.accent, borderRadius: 4}}/>}
        </span>;
      })}
    </div>;
  };

/** Number counter that keeps the source formatting (commas, decimals, prefix/suffix). */
export const Counter: React.FC<{value: string; delay?: number; duration?: number}> = ({value, delay = 4, duration = DURATION.long + 8}) => {
  const f = useCurrentFrame();
  const m = value.match(/^(\D*)([\d,.]+)(.*)$/);
  if (!m) return <>{value}</>;
  const target = Number(m[2].replace(/,/g, ''));
  const decimals = (m[2].split('.')[1] ?? '').length;
  const t = progress(f, {delay, duration, easing: Easing.out(Easing.cubic)});
  return <>{m[1]}{(target * t).toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}{m[3]}</>;
};

/** SVG path that draws itself (CONNECT line_draw / node_link). */
export const DrawPath: React.FC<{d: string; color: string; width?: number; delay?: number; duration?: number; dashed?: boolean}> = ({d, color, width = 6, delay = 0, duration = DURATION.draw, dashed}) => {
  const f = useCurrentFrame();
  const p = progress(f, {delay, duration, easing: EASE.inOut});
  return <path d={d} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" pathLength={1} strokeDasharray={dashed ? '0.02 0.02' : 1}
    strokeDashoffset={dashed ? 0 : 1 - p} opacity={dashed ? p : 1}/>;
};

/** A packet travelling along a straight segment (CONNECT flow). Loops every `period` frames after `delay`. */
export const FlowDot: React.FC<{x1: number; y1: number; x2: number; y2: number; color: string; delay?: number; period?: number}> = ({x1, y1, x2, y2, color, delay = 0, period = 36}) => {
  const f = useCurrentFrame() - delay;
  if (f < 0) return null;
  const t = EASE.inOut((f % period) / period);
  return <circle cx={x1 + (x2 - x1) * t} cy={y1 + (y2 - y1) * t} r={10} fill={color}/>;
};

/** Camera: slow push-in and optional pan, applied to a whole layer. */
export const cameraStyle = (kind: string, frame: number, dur: number, intensity = 1): React.CSSProperties => {
  const t = Math.min(1, frame / Math.max(1, dur));
  if (kind === 'static') return {};
  if (kind === 'pan_left') return {transform: `translateX(${-t * 30 * intensity}px) scale(${1 + .02 * intensity})`};
  if (kind === 'pan_right') return {transform: `translateX(${t * 30 * intensity}px) scale(${1 + .02 * intensity})`};
  if (kind === 'dolly') return {transform: `scale(${1 + .08 * intensity * EASE.inOut(t)})`};
  return {transform: `scale(${1 + .04 * intensity * t})`};
};

/** Parallax layers: children offset by depth against a shared drift. */
export const Parallax: React.FC<{depth: number; drift: number; children: React.ReactNode}> = ({depth, drift, children}) =>
  <div style={{position: 'absolute', inset: 0, transform: `translate3d(${drift * depth}px, ${drift * depth * .3}px, 0)`}}>{children}</div>;

/** Perspective card stack: cards fan in with depth. */
export const CardStack: React.FC<{count: number; delay?: number; render: (i: number) => React.ReactNode; gap?: number}> = ({count, delay = 0, render, gap = 26}) => {
  const f = useCurrentFrame();
  return <div style={{position: 'relative', perspective: 1400}}>
    {Array.from({length: count}, (_, i) => {
      const s = spring({frame: f - delay - i * 4, fps: 30, config: SPRING.gentle});
      return <div key={i} style={{transform: `translateY(${(1 - s) * 120}px) rotateX(${(1 - s) * 18}deg)`, opacity: Math.min(1, s * 1.5), marginTop: i ? gap : 0}}>{render(i)}</div>;
    })}
  </div>;
};

/** Typing effect for code: characters per frame, a blinking caret on the active line. */
export const typed = (frame: number, lines: string[], {delay = 4, cps = 1.6, lineGap = 6} = {}) => {
  let t = frame - delay;
  return lines.map(line => {
    const shown = Math.max(0, Math.min(line.length, Math.floor(t * cps)));
    const active = t >= 0 && shown < line.length;
    t -= line.length / cps + lineGap;
    return {text: line.slice(0, shown), active, done: shown === line.length};
  });
};
