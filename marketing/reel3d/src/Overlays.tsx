import {AbsoluteFill, Easing, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {colourAt, css, END, FPS, hex, lighten, Rgb, sceneEnd, sceneStart, SceneId, screenAt, SCREENS, wordAt} from './timeline';

const FONT = '"Segoe UI", "Segoe UI Variable", Arial, sans-serif';
const MONO = 'Consolas, "Cascadia Mono", monospace';

const useT = () => useCurrentFrame() / FPS;

/** 0..1 fade for a block shown from a to b */
const win = (t: number, a: number, b: number, fi = 0.25, fo = 0.25) =>
  Math.min(
    interpolate(t, [a, a + fi], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
    interpolate(t, [b - fo, b], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
  );

const usePop = (at: number, damping = 11) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: frame - Math.round(at * fps), fps, config: {damping, stiffness: 170, mass: 0.7}});
};

const Glow: React.FC<{c: Rgb; children: React.ReactNode; size: number; style?: React.CSSProperties}> = ({c, children, size, style}) => (
  <div
    style={{
      fontFamily: FONT, fontWeight: 900, fontSize: size, letterSpacing: -2, lineHeight: 1.1,
      color: css(lighten(c, 0.45)),
      textShadow: `0 0 6px ${css(lighten(c, 0.2), 0.9)}, 0 0 30px ${css(c, 0.85)}, 0 0 80px ${css(c, 0.55)}`,
      ...style,
    }}
  >
    {children}
  </div>
);

const Card: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
  <div
    style={{
      background: 'linear-gradient(160deg, rgba(28,30,38,0.92), rgba(12,13,18,0.94))',
      border: '2px solid rgba(255,255,255,0.09)', borderRadius: 44, padding: 40,
      boxShadow: '0 40px 120px rgba(0,0,0,0.7)', ...style,
    }}
  >
    {children}
  </div>
);

// ------------------------------------------------------------- hook: 16.7M colour counter
const Hook: React.FC = () => {
  const t = useT();
  const end = sceneStart('reveal');
  const a = win(t, 0.05, end, 0.15, 0.08);
  const whiteAt = wordAt('hook', 'white');
  const p = usePop(whiteAt - 0.05, 9);
  if (a <= 0) return null;
  const n = Math.round(16777216 * Easing.out(Easing.cubic)(Math.min(1, t / 1.6)));
  const shake = t > whiteAt && t < whiteAt + 0.35 ? Math.sin(t * 120) * 8 * (1 - (t - whiteAt) / 0.35) : 0;
  return (
    <AbsoluteFill style={{opacity: a, alignItems: 'center', top: 300}}>
      <div style={{fontFamily: MONO, fontWeight: 700, fontSize: 104, color: 'white', letterSpacing: -3,
        textShadow: '0 0 40px rgba(255,255,255,0.35)'}}>
        {n.toLocaleString('en-GB')}
      </div>
      <div style={{fontFamily: FONT, fontWeight: 700, fontSize: 46, color: '#9aa1b2', marginTop: 4}}>colours available</div>
      <div
        style={{
          marginTop: 34, transform: `scale(${p}) translateX(${shake}px) rotate(-3deg)`, opacity: Math.min(1, p * 2),
          fontFamily: FONT, fontWeight: 900, fontSize: 60, color: '#111', background: '#f2f3f7',
          padding: '10px 30px', borderRadius: 16,
        }}
      >
        colours used: 1
      </div>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------- reveal flash
const Flash: React.FC = () => {
  const t = useT();
  const r = sceneStart('reveal');
  const a = interpolate(t, [r - 0.02, r + 0.03, r + 0.35], [0, 0.95, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (a <= 0) return null;
  return <AbsoluteFill style={{background: 'white', opacity: a, mixBlendMode: 'screen'}} />;
};

// ------------------------------------------------------------- demo: logo + category chips
const Demo: React.FC = () => {
  const t = useT();
  const s0 = wordAt('demo', 'lumisync') - 0.15;
  const a = win(t, s0, sceneStart('focal'), 0.2, 0.3);
  const p = usePop(s0, 10);
  if (a <= 0) return null;
  const c = colourAt(t);
  const sc = screenAt(t);
  const showChip = t >= wordAt('demo', 'games') - 0.05;
  const chipPop = spring({frame: Math.round(sc.since * FPS), fps: FPS, config: {damping: 12, stiffness: 220}});
  return (
    <AbsoluteFill style={{opacity: a, alignItems: 'center', top: 270}}>
      <Glow c={c} size={176} style={{transform: `scale(${0.6 + 0.4 * p})`}}>LumiSync</Glow>
      {showChip && (
        <div style={{marginTop: 30, transform: `scale(${0.5 + 0.5 * chipPop})`, display: 'flex', gap: 18, alignItems: 'center',
          background: 'rgba(10,11,15,0.85)', border: `3px solid ${css(c, 0.9)}`, borderRadius: 60, padding: '14px 34px',
          boxShadow: `0 0 40px ${css(c, 0.5)}`}}>
          <div style={{width: 30, height: 30, borderRadius: 15, background: css(c), boxShadow: `0 0 18px ${css(c)}`}} />
          <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 52, color: 'white', letterSpacing: 2}}>{SCREENS[sc.cur].label}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------- focal vs average
const MUD: Rgb = [74, 70, 92];
const Focal: React.FC = () => {
  const t = useT();
  const s = sceneStart('focal');
  const a = win(t, s + 0.15, sceneEnd('focal'), 0.3, 0.25);
  const p = usePop(s + 0.15, 13);
  const boxP = usePop(wordAt('focal', 'glowing') - 0.1, 12);
  const mudP = usePop(wordAt('focal', 'averaging') - 0.05, 12);
  const crossP = usePop(wordAt('focal', 'mud') - 0.05, 9);
  if (a <= 0) return null;
  const g: Rgb = [60, 255, 150];
  return (
    <AbsoluteFill style={{opacity: a, alignItems: 'center', top: 300}}>
      <Card style={{width: 900, transform: `translateY(${(1 - p) * 120}px) scale(${0.9 + 0.1 * p})`}}>
        <div style={{position: 'relative', width: 820, height: 480, borderRadius: 24, overflow: 'hidden'}}>
          <Img src={staticFile('scenes/ring.png')} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
          <div style={{position: 'absolute', left: 205, top: 35, width: 410, height: 410, border: `5px solid ${css(g)}`,
            borderRadius: 12, opacity: boxP, transform: `scale(${1.3 - 0.3 * boxP})`, boxShadow: `0 0 30px ${css(g, 0.7)}`}} />
          <div style={{position: 'absolute', left: 205, top: 35, transform: 'translateY(-100%)', opacity: boxP,
            fontFamily: MONO, fontWeight: 700, fontSize: 30, color: '#04140a', background: css(g), padding: '4px 14px'}}>
            focal: ring 0.91
          </div>
        </div>
        <div style={{display: 'flex', gap: 30, marginTop: 34}}>
          {[
            {label: 'Screen average', c: MUD, pop: mudP, bad: true},
            {label: 'LumiSync', c: g, pop: boxP, bad: false},
          ].map((x) => (
            <div key={x.label} style={{flex: 1, opacity: x.pop, transform: `translateY(${(1 - x.pop) * 40}px)`}}>
              <div style={{position: 'relative', height: 150, borderRadius: 24, background: css(x.c),
                boxShadow: x.bad ? 'none' : `0 0 50px ${css(x.c, 0.6)}`}}>
                {x.bad && (
                  <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontFamily: FONT, fontWeight: 900, fontSize: 130, color: '#ff4a4a', transform: `scale(${crossP})`,
                    textShadow: '0 4px 20px rgba(0,0,0,0.6)'}}>✕</div>
                )}
              </div>
              <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 40, color: x.bad ? '#8b90a0' : 'white', marginTop: 14, textAlign: 'center'}}>
                {x.label}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------- optimisation
const Optimise: React.FC = () => {
  const t = useT();
  const s = sceneStart('optimise');
  const e = sceneEnd('optimise');
  const a = win(t, s + 0.1, e, 0.3, 0.25);
  const p = usePop(s + 0.1, 13);
  const shrinkAt = wordAt('optimise', 'shrinks');
  const wipe = interpolate(t, [shrinkAt, shrinkAt + 0.9], [0, 100], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic)});
  const sizeP = usePop(wordAt('optimise', 'hundred') - 0.1, 12);
  const skipAt = wordAt('optimise', 'skips');
  const skipP = usePop(skipAt - 0.1, 14);
  if (a <= 0) return null;
  const c = colourAt(t);
  const tiles = 12;
  const lit = interpolate(t, [skipAt, skipAt + 1.4], [0, tiles], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const send = new Set([0, 5, 9]);
  return (
    <AbsoluteFill style={{opacity: a, alignItems: 'center', top: 250}}>
      <Glow c={c} size={96} style={{transform: `scale(${0.7 + 0.3 * p})`, marginBottom: 30}}>Seriously light</Glow>
      <Card style={{width: 900, padding: 36, transform: `translateY(${(1 - p) * 120}px)`}}>
        <div style={{position: 'relative', width: 828, height: 466, borderRadius: 22, overflow: 'hidden'}}>
          <Img src={staticFile('scenes/city_full.png')} style={{position: 'absolute', width: '100%', height: '100%'}} />
          <Img src={staticFile('scenes/city_160.png')} style={{position: 'absolute', width: '100%', height: '100%',
            clipPath: `inset(0 ${100 - wipe}% 0 0)`, imageRendering: 'pixelated'}} />
          {wipe > 0 && wipe < 100 && (
            <div style={{position: 'absolute', top: 0, bottom: 0, left: `${wipe}%`, width: 6, background: css(c),
              boxShadow: `0 0 30px 8px ${css(c, 0.8)}`}} />
          )}
          <div style={{position: 'absolute', right: 20, bottom: 20, opacity: sizeP, transform: `scale(${sizeP})`, transformOrigin: 'right bottom',
            fontFamily: MONO, fontWeight: 700, fontSize: 72, color: 'white', background: 'rgba(0,0,0,0.75)', padding: '6px 24px', borderRadius: 18}}>
            160 × 90
          </div>
        </div>
        <div style={{display: 'flex', gap: 24, marginTop: 28}}>
          {[['144×', 'fewer pixels than 1080p'], ['10–30', 'FPS, tuned per use']].map(([big, small], i) => {
            const q = i === 0 ? sizeP : skipP;
            return (
              <div key={big} style={{flex: 1, opacity: q, transform: `translateY(${(1 - q) * 30}px)`,
                background: 'rgba(255,255,255,0.04)', borderRadius: 24, padding: '20px 24px'}}>
                <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 64, color: css(lighten(c, 0.3))}}>{big}</div>
                <div style={{fontFamily: FONT, fontWeight: 600, fontSize: 30, color: '#9aa1b2'}}>{small}</div>
              </div>
            );
          })}
        </div>
        <div style={{marginTop: 28, opacity: skipP}}>
          <div style={{display: 'flex', gap: 10}}>
            {Array.from({length: tiles}, (_, i) => {
              const on = i < lit;
              const isSend = send.has(i);
              return (
                <div key={i} style={{flex: 1, height: 64, borderRadius: 12,
                  background: on ? (isSend ? css(c) : 'rgba(255,255,255,0.08)') : 'rgba(255,255,255,0.03)',
                  boxShadow: on && isSend ? `0 0 24px ${css(c, 0.8)}` : 'none',
                  border: '2px solid rgba(255,255,255,0.06)'}} />
              );
            })}
          </div>
          <div style={{fontFamily: FONT, fontWeight: 700, fontSize: 32, color: '#c9cdd8', marginTop: 14, textAlign: 'center'}}>
            Tiny colour changes are skipped, so it barely writes to your RGB
          </div>
        </div>
      </Card>
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------- features
const Features: React.FC = () => {
  const t = useT();
  const s = sceneStart('features');
  const a = win(t, s, sceneEnd('features'), 0.2, 0.25);
  const items: [string, string][] = [
    ['openrgb', 'Works with OpenRGB'],
    ['free', '100% free'],
    ['open', 'Open source · MIT'],
  ];
  const pops = items.map(([w]) => usePop(wordAt('features', w) - 0.08, 10));
  if (a <= 0) return null;
  const c = colourAt(t);
  return (
    <AbsoluteFill style={{opacity: a, alignItems: 'center', top: 330, gap: 34}}>
      {items.map(([w, label], i) => (
        <div key={w} style={{transform: `translateX(${(1 - pops[i]) * (i % 2 ? 400 : -400)}px) rotate(${(i - 1) * -2}deg)`,
          opacity: Math.min(1, pops[i] * 1.5), display: 'flex', alignItems: 'center', gap: 22,
          background: 'rgba(10,11,15,0.88)', border: `3px solid ${css(c, 0.85)}`, borderRadius: 30,
          padding: '22px 44px', boxShadow: `0 0 50px ${css(c, 0.4)}`}}>
          <div style={{width: 46, height: 46, borderRadius: 23, background: css(c), display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontFamily: FONT, fontWeight: 900, fontSize: 32, color: '#0a0a0a'}}>✓</div>
          <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 64, color: 'white'}}>{label}</div>
        </div>
      ))}
    </AbsoluteFill>
  );
};

// ------------------------------------------------------------- call to action
const Star: React.FC<{size: number; c: string}> = ({size, c}) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path fill={c} d="M12 2l2.9 6.6 7.1.6-5.4 4.7 1.6 7L12 17.3 5.8 20.9l1.6-7L2 9.2l7.1-.6z" />
  </svg>
);

const Cta: React.FC = () => {
  const t = useT();
  const s = sceneStart('cta');
  const a = win(t, s - 0.1, END + 1, 0.3, 0.1);
  const p = usePop(s - 0.1, 11);
  const urlP = usePop(s + 0.35, 12);
  const starP = usePop(wordAt('cta', 'star') - 0.1, 7);
  if (a <= 0) return null;
  const c = colourAt(t);
  const spin = interpolate(t, [wordAt('cta', 'star') - 0.1, wordAt('cta', 'star') + 0.6], [-180, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.back(2))});
  return (
    <AbsoluteFill style={{opacity: a, alignItems: 'center', top: 520}}>
      <Glow c={c} size={200} style={{transform: `scale(${0.5 + 0.5 * p})`}}>LumiSync</Glow>
      <div style={{fontFamily: FONT, fontWeight: 700, fontSize: 50, color: 'white', marginTop: 18, opacity: p}}>
        Ambient RGB sync, without the bloat.
      </div>
      <div style={{marginTop: 56, transform: `scale(${urlP})`, background: 'white', borderRadius: 70, padding: '26px 52px',
        display: 'flex', alignItems: 'center', gap: 22, boxShadow: `0 0 70px ${css(c, 0.55)}`}}>
        <svg width={56} height={56} viewBox="0 0 16 16"><path fill="#0d1117" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>
        <div style={{fontFamily: MONO, fontWeight: 700, fontSize: 46, color: '#0d1117'}}>Gxmi2006/LumiSync</div>
      </div>
      <div style={{marginTop: 44, display: 'flex', alignItems: 'center', gap: 20, opacity: Math.min(1, starP * 1.4)}}>
        <div style={{transform: `scale(${starP}) rotate(${spin}deg)`, filter: 'drop-shadow(0 0 22px rgba(255,200,60,0.9))'}}>
          <Star size={92} c="#ffc83c" />
        </div>
        <div style={{fontFamily: FONT, fontWeight: 900, fontSize: 62, color: 'white'}}>Star it · Link in bio</div>
      </div>
    </AbsoluteFill>
  );
};

export const Overlays: React.FC = () => (
  <>
    <Hook />
    <Demo />
    <Focal />
    <Optimise />
    <Features />
    <Cta />
    <Flash />
  </>
);

export const blurFor = (t: number) => {
  const cardScenes: SceneId[] = ['focal', 'optimise', 'cta'];
  let b = 0;
  for (const id of cardScenes) {
    const s = sceneStart(id) + 0.1, e = id === 'cta' ? END + 1 : sceneEnd(id);
    b = Math.max(b, win(t, s, e, 0.35, 0.3));
  }
  return b;
};
