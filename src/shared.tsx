import React from 'react';
import {Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export type Style = 'studio' | 'premium' | 'paper' | 'editorial' | 'kinetic' | 'mascot' | 'fieldnotes';
export type Word = {w: string; s: number; e: number};
export type Beat = {s: number; e: number; w: [number, number]; text: string; focus: string; layout: string; anchor: string; transition: string; punch: boolean; layoutReason?: unknown};
export type Motion = {entrance: string; emphasis: string; connect: string; exit: string; camera: string; intensity: number; stagger_frames: number};
export type Repo = {full_name: string; owner: string; name: string; description: string; stars: number; language: string; topics: string[]; readme?: string};
export type Scene = {heading: string; narration: string; caption: string; points: string[]; visual: string; emphasis?: string; stat?: string; item?: number; label?: string; words?: Word[]; mouth?: number[]; visemes?: [number, string][]; beats?: Beat[]; audio: string; uiAudio?: string; frames: number; audioFrames?: number; transitionFrames?: number; from: number;
  // V2 storyboard fields (absent on V1 props)
  id?: string; role?: string; intent?: string; pace?: string; visualData?: Record<string, unknown>; motion?: Motion; media?: string | null; mediaSeconds?: number | null; layoutHint?: string; character?: boolean; claimIds?: string[]};
export type Props = {title: string; style?: Style; brand?: string; series?: string; repos?: Repo[]; music?: string | null; variant?: any; scenes: Scene[]; durationInFrames: number; fps: number; width: number; height: number;
  schemaVersion?: string; theme?: string; characterMode?: 'auto' | 'on' | 'off'};
export type ShotProps = {scene: Scene; index: number; total: number; brand: string};

export const sans = '"Helvetica Neue", Helvetica, Arial, sans-serif';
export const serif = 'Georgia, "Times New Roman", serif';
export const mono = 'Menlo, "SF Mono", Monaco, monospace';

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const clip = (text: string, max: number) => {
  if (text.length <= max) return text;
  const cut = text.slice(0, max + 1).replace(/\s+\S*$/, '');
  return (cut || text.slice(0, max)).replace(/[\s,.;:—-]+$/, '') + '…';
};
export const pad2 = (n: number) => String(n).padStart(2, '0');
const bare = (word: string) => word.toLowerCase().replace(/[^\p{L}\p{N}$%]/gu, '');

// Word timing estimated from word length across the scene's audio (same approach as the original template).
export const useCaption = (scene: Scene, groupSize: number) => {
  const frame = useCurrentFrame();
  const words = scene.narration.trim().split(/\s+/);
  const weights = words.map(word => Math.max(1, bare(word).length));
  const weightTotal = weights.reduce((sum, weight) => sum + weight, 0);
  const audioFrames = Math.max(1, scene.audioFrames ?? scene.frames - 14);
  const progress = Math.min(.999, Math.max(0, frame / audioFrames));
  let passed = 0;
  const starts: number[] = [];
  let found = -1;
  weights.forEach((weight, i) => {
    starts.push(passed / weightTotal * audioFrames);
    if (found < 0 && progress * weightTotal < passed + weight) found = i;
    passed += weight;
  });
  const active = found < 0 ? words.length - 1 : found;
  const groupStart = Math.floor(active / groupSize) * groupSize;
  const emphasis = (scene.emphasis ?? '').split(/\s+/).map(bare).filter(Boolean);
  return {words, active, groupStart, group: words.slice(groupStart, groupStart + groupSize), starts, speaking: frame < audioFrames,
    isEmphasis: (word: string) => emphasis.includes(bare(word))};
};

export const usePop = (delay: number, damping = 14) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: frame - delay, fps, config: {damping, stiffness: 140}});
};

export const splitStat = (stat: string) => {
  const match = stat.match(/^(\D*)([\d,.]+)(.*)$/);
  if (!match) return null;
  const value = Number(match[2].replace(/,/g, ''));
  const decimals = (match[2].split('.')[1] ?? '').length;
  return Number.isFinite(value) ? {prefix: match[1], value, decimals, suffix: match[3]} : null;
};

export const CountUp: React.FC<{stat: string; delay?: number; duration?: number}> = ({stat, delay = 8, duration = 40}) => {
  const frame = useCurrentFrame();
  const parts = splitStat(stat);
  if (!parts) return <>{stat}</>;
  const t = interpolate(frame, [delay, delay + duration], [0, 1], clamp);
  const eased = 1 - Math.pow(1 - t, 3);
  const shown = (parts.value * eased).toLocaleString('en-US', {minimumFractionDigits: parts.decimals, maximumFractionDigits: parts.decimals});
  return <>{parts.prefix}{shown}{parts.suffix}</>;
};

export const SceneAudio: React.FC<{scene: Scene}> = ({scene}) => <>
  {scene.audio && <Audio src={staticFile(scene.audio)}/>}
  {scene.uiAudio && <Audio src={staticFile(scene.uiAudio)} volume={0.2}/>}
</>;

// Entering/leaving progress for the overlap between scenes: -1..0 entering, 0..1 leaving.
export const useTransition = (scene: Scene, index: number, total: number) => {
  const frame = useCurrentFrame();
  const t = Math.max(1, Math.min(scene.transitionFrames ?? 0, Math.floor(scene.frames / 3)));
  const enter = index === 0 ? 1 : interpolate(frame, [0, t], [0, 1], clamp);
  const leave = index === total - 1 ? 0 : interpolate(frame, [scene.frames - t, scene.frames], [0, 1], clamp);
  return {enter, leave};
};
