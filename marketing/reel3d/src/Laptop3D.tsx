import {useThree} from '@react-three/fiber';
import {useLayoutEffect, useMemo, useRef} from 'react';
import {Easing, interpolate, useCurrentFrame} from 'remotion';
import * as THREE from 'three';
import {colourAt, FPS, keyColour, Rgb, sceneStart, screenAt, smooth, WHITE_KEYS} from './timeline';

// ------------------------------------------------------------- keyboard layout
const ROWS = [
  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2],
  [1.5, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1.5],
  [1.8, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2.2],
  [2.3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2.7],
  [1.2, 1, 1.2, 6.4, 1.2, 1, 1, 1],
];
const KW = 2.86, KD = 1.04, KZ0 = -1.0, GAP = 0.03;

type Key = {x: number; z: number; w: number; d: number; xn: number; row: number};
const KEYS: Key[] = (() => {
  const out: Key[] = [];
  const kd = (KD - GAP * (ROWS.length - 1)) / ROWS.length;
  ROWS.forEach((lay, r) => {
    const units = lay.reduce((a, b) => a + b, 0);
    const u = (KW - GAP * (lay.length - 1)) / units;
    let x = -KW / 2;
    for (const w of lay) {
      const kw = w * u;
      out.push({x: x + kw / 2, z: KZ0 + r * (kd + GAP) + kd / 2, w: kw, d: kd, xn: (x + kw / 2 + KW / 2) / KW, row: r});
      x += kw + GAP;
    }
  });
  return out;
})();

const glowTexture = (() => {
  if (typeof document === 'undefined') return null;
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d')!;
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(0.35, 'rgba(255,255,255,0.55)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
})();

const toCol = (c: Rgb, k = 1) => new THREE.Color(c[0] / 255 * k, c[1] / 255 * k, c[2] / 255 * k);

// ------------------------------------------------------------- camera choreography
type V3 = [number, number, number];
type CamKey = {t: number; pos: V3; look: V3; ease?: (x: number) => number};

const camKeys = (): CamKey[] => {
  const r = sceneStart('reveal'), d = sceneStart('demo'), f = sceneStart('focal');
  const o = sceneStart('optimise'), fe = sceneStart('features'), c = sceneStart('cta');
  return [
    {t: 0, pos: [2.0, 0.42, 1.25], look: [0.35, 0.14, -0.4]},
    {t: r - 0.02, pos: [1.25, 0.5, 1.0], look: [0.1, 0.14, -0.45]},
    {t: r + 0.55, pos: [0.0, 2.6, 6.6], look: [0, 1.35, -0.45], ease: Easing.out(Easing.exp)},
    {t: f - 0.2, pos: [-1.9, 2.2, 6.1], look: [0, 1.3, -0.45]},
    {t: f + 0.8, pos: [0, 1.25, 3.4], look: [0, 1.0, -1.05]},
    {t: o, pos: [0.25, 1.3, 3.2], look: [0, 1.0, -1.05]},
    {t: o + 0.9, pos: [0, 7.6, 0.9], look: [0, 0, -0.35]},
    {t: fe, pos: [0.3, 7.4, 1.2], look: [0, 0, -0.35]},
    {t: fe + 0.9, pos: [3.6, 1.05, 4.6], look: [0, 1.15, -0.4]},
    {t: c, pos: [-3.2, 1.3, 5.0], look: [0, 1.0, -0.4]},
    {t: c + 1.1, pos: [0, 3.6, 8.2], look: [0, 1.4, -0.4]},
  ];
};

const lerpV = (a: V3, b: V3, m: number): V3 => [a[0] + (b[0] - a[0]) * m, a[1] + (b[1] - a[1]) * m, a[2] + (b[2] - a[2]) * m];

const CameraRig: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const {camera} = useThree();
  const keys = useMemo(camKeys, []);
  useLayoutEffect(() => {
    let i = 0;
    while (i < keys.length - 1 && t >= keys[i + 1].t) i++;
    const a = keys[i], b = keys[Math.min(i + 1, keys.length - 1)];
    const span = Math.max(0.001, b.t - a.t);
    const ease = b.ease ?? Easing.inOut(Easing.cubic);
    const m = a === b ? 1 : ease(Math.max(0, Math.min(1, (t - a.t) / span)));
    const pos = lerpV(a.pos, b.pos, m);
    const look = lerpV(a.look, b.look, m);
    // impact shake when the keyboard lights up
    const since = t - sceneStart('reveal');
    if (since > 0 && since < 0.6) {
      const amp = 0.05 * (1 - since / 0.6);
      pos[0] += Math.sin(since * 90) * amp;
      pos[1] += Math.cos(since * 70) * amp;
    }
    camera.position.set(...pos);
    camera.lookAt(...look);
    camera.updateProjectionMatrix();
  }, [t, camera, keys]);
  return null;
};

// ------------------------------------------------------------- laptop
export const Laptop3D: React.FC<{textures: Record<string, THREE.Texture>}> = ({textures}) => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const reveal = sceneStart('reveal');
  const col = t < reveal ? WHITE_KEYS : colourAt(t);
  const inten = t < reveal ? 0.35 : 1;

  const caps = useRef<THREE.InstancedMesh>(null);
  const glows = useRef<THREE.InstancedMesh>(null);
  const halos = useRef<THREE.InstancedMesh>(null);

  useLayoutEffect(() => {
    const m = new THREE.Matrix4();
    const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0));
    KEYS.forEach((k, i) => {
      m.compose(new THREE.Vector3(k.x, 0.135, k.z), new THREE.Quaternion(), new THREE.Vector3(k.w * 0.92, 0.045, k.d * 0.9));
      caps.current!.setMatrixAt(i, m);
      m.compose(new THREE.Vector3(k.x, 0.112, k.z), q, new THREE.Vector3(k.w * 1.9, k.d * 2.1, 1));
      glows.current!.setMatrixAt(i, m);
      m.compose(new THREE.Vector3(k.x, 0.175, k.z), q, new THREE.Vector3(k.w * 1.5, k.d * 1.7, 1));
      halos.current!.setMatrixAt(i, m);
    });
    caps.current!.instanceMatrix.needsUpdate = true;
    glows.current!.instanceMatrix.needsUpdate = true;
    halos.current!.instanceMatrix.needsUpdate = true;
  }, []);

  useLayoutEffect(() => {
    KEYS.forEach((k, i) => {
      const {c, i: ki} = keyColour(t, k.xn, k.row);
      glows.current!.setColorAt(i, toCol(c, ki * 2.0));
      halos.current!.setColorAt(i, toCol(c, ki * 0.28));
      caps.current!.setColorAt(i, toCol(c, 0.16 + 0.26 * ki).add(new THREE.Color(0.03, 0.033, 0.04)));
    });
    glows.current!.instanceColor!.needsUpdate = true;
    halos.current!.instanceColor!.needsUpdate = true;
    caps.current!.instanceColor!.needsUpdate = true;
  }, [t]);

  const s = screenAt(t);
  const fade = smooth(s.since / 0.12);
  const screenGlow = toCol(colourAt(t), 0.8);

  // the lid opens a touch during the reveal for drama
  const lidOpen = interpolate(t, [reveal - 0.1, reveal + 0.5], [0.42, 0.26], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.back(1.6)),
  });

  return (
    <>
      <CameraRig />
      <color attach="background" args={['#040507']} />
      <fog attach="fog" args={['#040507', 9, 18]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[-3, 5, 4]} intensity={1.1} color="#cfd8ff" />
      <directionalLight position={[4, 2, -3]} intensity={0.8} color="#8090ff" />
      <pointLight position={[0, 0.7, -0.6]} intensity={2.4 * inten} distance={4.5} decay={1.4} color={toCol(col)} />
      <pointLight position={[0, 1.2, 0.6]} intensity={2.2} distance={3} decay={1.5} color={screenGlow} />

      {/* glossy floor + coloured ambient pool of light */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]}>
        <planeGeometry args={[30, 30]} />
        <meshStandardMaterial color="#08090c" roughness={0.45} metalness={0.5} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.003, -0.2]}>
        <planeGeometry args={[9, 7]} />
        <meshBasicMaterial map={glowTexture} color={toCol(col, 0.42 * inten)} transparent blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false} />
      </mesh>

      {/* base */}
      <mesh position={[0, 0.05, -0.35]}>
        <boxGeometry args={[3.3, 0.1, 2.25]} />
        <meshStandardMaterial color="#1a1c22" roughness={0.42} metalness={0.7} />
      </mesh>
      <mesh position={[0, 0.101, 0.42]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[1.05, 0.55]} />
        <meshStandardMaterial color="#202329" roughness={0.75} metalness={0.3} />
      </mesh>
      {/* keyboard well */}
      <mesh position={[0, 0.1005, KZ0 + KD / 2]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[KW + 0.08, KD + 0.08]} />
        <meshStandardMaterial color="#0b0c0f" roughness={0.8} />
      </mesh>
      <instancedMesh ref={glows} args={[undefined, undefined, KEYS.length]}>
        <planeGeometry args={[1, 1]} />
        <meshBasicMaterial map={glowTexture} transparent blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false} />
      </instancedMesh>
      <instancedMesh ref={caps} args={[undefined, undefined, KEYS.length]}>
        <boxGeometry args={[1, 1, 1]} />
        <meshStandardMaterial roughness={0.55} metalness={0.2} />
      </instancedMesh>
      <instancedMesh ref={halos} args={[undefined, undefined, KEYS.length]}>
        <planeGeometry args={[1, 1]} />
        <meshBasicMaterial map={glowTexture} transparent blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false} />
      </instancedMesh>

      {/* lid, hinged at the back edge */}
      <group position={[0, 0.1, -1.47]} rotation={[-lidOpen, 0, 0]}>
        <mesh position={[0, 1.07, -0.03]}>
          <boxGeometry args={[3.3, 2.14, 0.06]} />
          <meshStandardMaterial color="#17191e" roughness={0.4} metalness={0.75} />
        </mesh>
        <mesh position={[0, 1.08, 0.002]}>
          <planeGeometry args={[3.12, 1.95]} />
          <meshBasicMaterial color="#000000" />
        </mesh>
        <mesh position={[0, 1.1, 0.004]}>
          <planeGeometry args={[3.04, 1.78]} />
          <meshBasicMaterial map={textures[s.prev]} toneMapped={false} />
        </mesh>
        <mesh position={[0, 1.1, 0.006]}>
          <planeGeometry args={[3.04, 1.78]} />
          <meshBasicMaterial map={textures[s.cur]} transparent opacity={fade} toneMapped={false} />
        </mesh>
      </group>
    </>
  );
};
