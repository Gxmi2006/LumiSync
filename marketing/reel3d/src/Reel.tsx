import {ThreeCanvas} from '@remotion/three';
import {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, continueRender, delayRender, Sequence, staticFile, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {Captions} from './Captions';
import {Laptop3D} from './Laptop3D';
import {blurFor, Overlays} from './Overlays';
import {END, FPS, SCHEDULE, sceneStart, SCREENS, TIMING, wordAt} from './timeline';

const useTextures = () => {
  const [tex, setTex] = useState<Record<string, THREE.Texture> | null>(null);
  const [handle] = useState(() => delayRender('scene textures'));
  useEffect(() => {
    const loader = new THREE.TextureLoader();
    Promise.all(
      Object.entries(SCREENS).map(async ([k, v]) => {
        const t = await loader.loadAsync(staticFile(v.img));
        t.colorSpace = THREE.SRGBColorSpace;
        t.anisotropy = 8;
        return [k, t] as const;
      }),
    ).then((list) => {
      setTex(Object.fromEntries(list));
      continueRender(handle);
    });
  }, [handle]);
  return tex;
};

// ElevenLabs-generated effects (tools/sfx.mjs), peak-normalised
const Sfx: React.FC<{at: number; src: string; volume?: number}> = ({at, src, volume = 1}) => (
  <Sequence from={Math.max(0, Math.round(at * FPS))} layout="none">
    <Audio src={staticFile(`sfx/el_${src}.mp3`)} volume={volume} />
  </Sequence>
);

const ramp = (t: number, pts: [number, number][]) => {
  if (t <= pts[0][0]) return pts[0][1];
  for (let i = 1; i < pts.length; i++) {
    const [t1, v1] = pts[i], [t0, v0] = pts[i - 1];
    if (t <= t1) return v0 + ((v1 - v0) * (t - t0)) / Math.max(0.001, t1 - t0);
  }
  return pts[pts.length - 1][1];
};

export const Reel: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const textures = useTextures();
  const blur = blurFor(t);
  const reveal = sceneStart('reveal');

  return (
    <AbsoluteFill style={{background: '#040507'}}>
      <AbsoluteFill style={{filter: blur > 0.01 ? `blur(${blur * 14}px) brightness(${1 - blur * 0.45})` : undefined}}>
        {textures && (
          <ThreeCanvas width={1080} height={1920} camera={{fov: 42, near: 0.05, far: 60}} gl={{antialias: true}}>
            <Laptop3D textures={textures} />
          </ThreeCanvas>
        )}
      </AbsoluteFill>
      {/* vignette */}
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 50% 55%, transparent 45%, rgba(0,0,0,0.75) 100%)'}} />
      <Overlays />
      <Captions />

      {!TIMING.scratch && <Audio src={staticFile('voice.mp3')} />}
      {/* music: tense pad under the hook, beat loop drops on the reveal and lifts after the last line */}
      <Audio src={staticFile('sfx/el_pad.mp3')} volume={(f) => ramp(f / FPS, [[0, 0], [0.6, 0.17], [reveal - 0.3, 0.22], [reveal + 0.2, 0]])} />
      <Sequence from={Math.round(reveal * FPS)} layout="none">
        <Audio
          src={staticFile('sfx/el_beat.mp3')}
          loop
          volume={(f) => {
            const t = reveal + f / FPS;
            return ramp(t, [[reveal, 0.22], [reveal + 1.2, 0.13], [TIMING.duration - 0.2, 0.11], [TIMING.duration + 0.3, 0.4], [END - 0.9, 0.4], [END, 0]]);
          }}
        />
      </Sequence>

      {/* hook */}
      <Sfx at={0.05} src="counter" volume={0.45} />
      <Sfx at={wordAt('hook', 'white') - 0.05} src="scratch" volume={0.55} />
      {/* reveal */}
      <Sfx at={reveal - 1.6} src="riser" volume={0.35} />
      <Sfx at={reveal - 0.02} src="impact" volume={0.38} />
      {/* screen changes get a soft click, big card transitions a whoosh */}
      {SCHEDULE.slice(1)
        .filter(([at]) => !(['focal', 'optimise', 'cta'] as const).some((id) => Math.abs(at - sceneStart(id)) < 0.05))
        .map(([at], i) => <Sfx key={i} at={at - 0.03} src="click" volume={0.5} />)}
      {(['focal', 'optimise', 'features', 'cta'] as const).map((id) => (
        <Sfx key={id} at={sceneStart(id) - 0.18} src="whoosh" volume={0.4} />
      ))}
      <Sfx at={wordAt('demo', 'lumisync') - 0.15} src="pop" volume={0.4} />
      <Sfx at={wordAt('optimise', 'shrinks')} src="glitch" volume={0.35} />
      {(['openrgb', 'free', 'open'] as const).map((w) => (
        <Sfx key={w} at={wordAt('features', w) - 0.08} src="pop" volume={0.45} />
      ))}
      <Sfx at={wordAt('cta', 'star') - 0.1} src="sparkle" volume={0.5} />
    </AbsoluteFill>
  );
};
