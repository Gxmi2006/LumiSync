import {AbsoluteFill, spring, useCurrentFrame} from 'remotion';
import {colourAt, css, FPS, lighten, sceneStart, TIMING, WHITE_KEYS} from './timeline';

// Group words into short caption chunks: max 3 words, break after punctuation.
type W = (typeof TIMING.words)[number];
const CHUNKS: W[][] = (() => {
  const out: W[][] = [];
  let cur: W[] = [];
  for (const w of TIMING.words) {
    cur.push(w);
    if (cur.length === 3 || /[.,?!]$/.test(w.text)) {
      out.push(cur);
      cur = [];
    }
  }
  if (cur.length) out.push(cur);
  return out;
})();

export const Captions: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  let idx = -1;
  for (let i = 0; i < CHUNKS.length; i++) if (t >= CHUNKS[i][0].start - 0.05) idx = i;
  if (idx < 0) return null;
  const chunk = CHUNKS[idx];
  const last = chunk[chunk.length - 1];
  const next = CHUNKS[idx + 1];
  if (t > last.end + 0.45 && (!next || t < next[0].start - 0.05)) return null;
  const c = t < sceneStart('reveal') ? WHITE_KEYS : colourAt(t);
  const enter = spring({frame: frame - Math.round((chunk[0].start - 0.05) * FPS), fps: FPS, config: {damping: 14, stiffness: 260}});
  return (
    <AbsoluteFill style={{top: 1420, height: 220, alignItems: 'center', justifyContent: 'center'}}>
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '0 22px', maxWidth: 940,
        transform: `scale(${0.85 + 0.15 * enter}) translateY(${(1 - enter) * 20}px)`}}>
        {chunk.map((w, i) => {
          const active = t >= w.start - 0.03;
          const p = spring({frame: frame - Math.round((w.start - 0.03) * FPS), fps: FPS, config: {damping: 10, stiffness: 300}});
          return (
            <span key={i} style={{
              fontFamily: '"Segoe UI", Arial, sans-serif', fontWeight: 900, fontSize: 86, lineHeight: 1.1,
              textTransform: 'uppercase', letterSpacing: -1,
              color: active ? (t >= w.end ? 'white' : css(lighten(c, 0.15))) : 'rgba(255,255,255,0.35)',
              transform: `scale(${active ? 0.9 + 0.1 * p : 0.9})`, display: 'inline-block',
              WebkitTextStroke: '3px rgba(0,0,0,0.85)', paintOrder: 'stroke fill',
              textShadow: active && t < w.end ? `0 0 30px ${css(c, 0.9)}, 0 6px 0 rgba(0,0,0,0.6)` : '0 6px 0 rgba(0,0,0,0.6)',
            }}>
              {w.text}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
