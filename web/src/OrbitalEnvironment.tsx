import { useEffect, useLayoutEffect, useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Line, RoundedBox, useTexture } from '@react-three/drei';
import * as THREE from 'three';
import type { Edge, Entity } from './types';

const earthVertex = `
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vWorld;
  void main() {
    vUv = uv;
    vNormal = normalize(mat3(modelMatrix) * normal);
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorld = world.xyz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const earthFragment = `
  uniform sampler2D dayMap;
  uniform sampler2D nightMap;
  uniform vec3 sunDirection;
  varying vec2 vUv;
  varying vec3 vNormal;
  varying vec3 vWorld;
  void main() {
    vec3 normal = normalize(vNormal);
    float daylight = dot(normal, sunDirection);
    float terminator = smoothstep(-0.16, 0.22, daylight);
    vec3 day = texture2D(dayMap, vUv).rgb;
    vec3 night = texture2D(nightMap, vUv).rgb;
    vec3 surface = mix(night * 0.4, day * (0.24 + max(daylight, 0.0) * 0.85), terminator);
    float rim = pow(1.0 - max(dot(normal, normalize(cameraPosition - vWorld)), 0.0), 4.0);
    surface += vec3(0.06, 0.21, 0.40) * rim * (0.25 + 0.75 * terminator);
    gl_FragColor = vec4(surface, 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

const atmosphereFragment = `
  uniform vec3 sunDirection;
  varying vec3 vNormal;
  varying vec3 vWorld;
  void main() {
    vec3 normal = normalize(vNormal);
    vec3 viewDirection = normalize(cameraPosition - vWorld);
    float rim = pow(1.0 - max(dot(normal, viewDirection), 0.0), 3.6);
    float sun = smoothstep(-0.3, 0.8, dot(normal, sunDirection));
    vec3 color = mix(vec3(0.035, 0.12, 0.29), vec3(0.22, 0.53, 0.86), sun);
    gl_FragColor = vec4(color, rim * 0.7);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

/** A textured 3D planet, not a flat sky image. Distances are artistically scaled. */
export function Earth() {
  const [day, clouds, night] = useTexture(['/textures/earth-day.jpg', '/textures/earth-clouds.jpg', '/textures/earth-night.jpg']);
  const globe = useRef<THREE.Group>(null);
  const cloudLayer = useRef<THREE.Mesh>(null);
  const uniforms = useMemo(() => ({
    dayMap: { value: day }, nightMap: { value: night },
    sunDirection: { value: new THREE.Vector3(-0.5, 0.72, 0.38).normalize() },
  }), [day, night]);
  useEffect(() => {
    day.colorSpace = night.colorSpace = THREE.SRGBColorSpace;
    day.anisotropy = night.anisotropy = clouds.anisotropy = 4;
    day.needsUpdate = night.needsUpdate = true;
  }, [day, clouds, night]);
  useFrame((_, dt) => {
    if (globe.current) globe.current.rotation.y += dt * 0.0007;
    if (cloudLayer.current) cloudLayer.current.rotation.y += dt * 0.0012;
  });
  return <group position={[0, -77, -48]} rotation={[0, -0.8, 0.18]}>
    <group ref={globe}>
      <mesh>
        <sphereGeometry args={[76, 96, 64]} />
        <shaderMaterial vertexShader={earthVertex} fragmentShader={earthFragment} uniforms={uniforms} />
      </mesh>
      <mesh ref={cloudLayer} rotation={[0, 0.12, 0]}>
        <sphereGeometry args={[76.3, 80, 48]} />
        <meshStandardMaterial map={clouds} alphaMap={clouds} transparent opacity={0.78} depthWrite={false} roughness={1} />
      </mesh>
    </group>
    <mesh>
      <sphereGeometry args={[77.1, 96, 64]} />
      <shaderMaterial vertexShader={earthVertex} fragmentShader={atmosphereFragment} uniforms={uniforms} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </mesh>
  </group>;
}

export function Sun() {
  const glow = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 128;
    const context = canvas.getContext('2d')!;
    const gradient = context.createRadialGradient(64, 64, 0, 64, 64, 64);
    gradient.addColorStop(0, '#fff9df');
    gradient.addColorStop(0.08, '#fff4d8ee');
    gradient.addColorStop(0.22, '#f7d6a147');
    gradient.addColorStop(0.55, '#e3b67c10');
    gradient.addColorStop(1, '#d49a5b00');
    context.fillStyle = gradient;
    context.fillRect(0, 0, 128, 128);
    return new THREE.CanvasTexture(canvas);
  }, []);
  useEffect(() => () => glow.dispose(), [glow]);
  return <sprite position={[-68, 40, -100]} scale={[25, 25, 1]}>
    <spriteMaterial map={glow} transparent blending={THREE.AdditiveBlending} depthWrite={false} toneMapped={false} />
  </sprite>;
}

export function ModuleHull({ cutaway, color, selected }: { cutaway: boolean; color: string; selected: boolean }) {
  const arc = cutaway ? Math.PI : Math.PI * 2;
  const start = cutaway ? -Math.PI / 2 : 0;
  return <group position={[0, 0.55, 0]}>
    <mesh rotation={[Math.PI / 2, 0, 0]}>
      <cylinderGeometry args={[2.04, 2.04, 4.2, 32, 1, true, start, arc]} />
      <meshStandardMaterial color={selected ? '#d4ede7' : '#b8c4c9'} metalness={0.42} roughness={0.58} side={THREE.DoubleSide} />
    </mesh>
    <mesh rotation={[Math.PI / 2, 0, 0]}>
      <cylinderGeometry args={[1.96, 1.96, 4.15, 32, 1, true, start, arc]} />
      <meshStandardMaterial color="#344551" metalness={0.3} roughness={0.75} side={THREE.DoubleSide} />
    </mesh>
    {[-2.05, -1.45, 1.45, 2.05].map(z => <group key={z} position={[0, 0, z]}>
      <mesh rotation={[0, 0, cutaway ? Math.PI : 0]}>
        <torusGeometry args={[2.055, 0.075, 6, 40, arc]} />
        <meshStandardMaterial color="#e2e4dc" metalness={0.65} roughness={0.4} />
      </mesh>
      <mesh rotation={[0, 0, cutaway ? Math.PI : 0]}>
        <torusGeometry args={[2.08, 0.018, 5, 40, arc]} />
        <meshBasicMaterial color={color} />
      </mesh>
    </group>)}
    {!cutaway && <>
      {[-1, 1].map(side => <group key={`cap-${side}`} position={[0, 0, side * 2.1]}>
        <mesh rotation={[side * Math.PI / 2, 0, 0]} scale={[1, 0.35, 1]}>
          <sphereGeometry args={[2.04, 32, 16, 0, Math.PI * 2, 0, Math.PI / 2]} />
          <meshStandardMaterial color={selected ? '#d4ede7' : '#bbc7cb'} metalness={0.42} roughness={0.58} />
        </mesh>
        <group position={[0, 0, side * 0.72]}>
          <mesh><circleGeometry args={[0.6, 24]} /><meshStandardMaterial color="#334b5a" metalness={0.55} roughness={0.45} side={THREE.DoubleSide} /></mesh>
          <mesh><torusGeometry args={[0.63, 0.075, 6, 24]} /><meshStandardMaterial color="#e0e2da" metalness={0.65} roughness={0.4} /></mesh>
          <mesh><torusGeometry args={[0.48, 0.018, 5, 24]} /><meshBasicMaterial color={color} /></mesh>
        </group>
      </group>)}
      {[-1, 1].map(side => <group key={side} position={[side * 1.92, 0.45, 0]} rotation={[0, 0, -side * 0.25]}>
        {[-1, 0, 1].map(z => <RoundedBox key={z} args={[0.13, 0.52, 0.62]} radius={0.08} position={[0, 0, z]}>
          <meshStandardMaterial color="#173343" metalness={0.75} roughness={0.15} emissive="#275566" emissiveIntensity={0.4} />
        </RoundedBox>)}
      </group>)}
      <mesh position={[0, 2.03, 0]}><boxGeometry args={[0.28, 0.035, 2.25]} /><meshBasicMaterial color={color} /></mesh>
      <mesh position={[0, 2.13, -1.2]}><boxGeometry args={[0.55, 0.17, 0.55]} /><meshStandardMaterial color="#5e737c" metalness={0.7} roughness={0.5} /></mesh>
    </>}
  </group>;
}

export function PressureTunnel({ length, blocked, cutaway }: { length: number; blocked: boolean; cutaway: boolean }) {
  const arc = cutaway ? Math.PI : Math.PI * 2;
  return <group position={[0, 0.24, 0]}>
    <mesh rotation={[Math.PI / 2, 0, 0]}>
      <cylinderGeometry args={[0.62, 0.62, length, 12, 1, true, cutaway ? -Math.PI / 2 : 0, arc]} />
      <meshStandardMaterial color={blocked ? '#8c6258' : '#94a5b1'} metalness={0.48} roughness={0.6} side={THREE.DoubleSide} />
    </mesh>
    {Array.from({ length: Math.max(2, Math.floor(length / 1.8)) }, (_, i) => i).map((_, i, all) => {
      const z = (i / Math.max(1, all.length - 1) - 0.5) * length;
      return <mesh key={i} position={[0, 0, z]} rotation={[0, 0, cutaway ? Math.PI : 0]}>
        <torusGeometry args={[0.64, 0.055, 5, 12, arc]} />
        <meshStandardMaterial color="#d7d9d4" metalness={0.5} roughness={0.6} />
      </mesh>;
    })}
  </group>;
}

function SolarWing({ side, z }: { side: number; z: number }) {
  const cells = useRef<THREE.InstancedMesh>(null);
  useLayoutEffect(() => {
    if (!cells.current) return;
    const dummy = new THREE.Object3D();
    const tint = new THREE.Color();
    for (let x = 0; x < 12; x++) for (let y = 0; y < 8; y++) {
      const index = x * 8 + y;
      dummy.position.set((x - 5.5) * 0.53, 0.065, (y - 3.5) * 0.53);
      dummy.updateMatrix();
      cells.current.setMatrixAt(index, dummy.matrix);
      tint.setHSL(0.61, 0.43, 0.19 + ((x * 7 + y * 3) % 5) * 0.012);
      cells.current.setColorAt(index, tint);
    }
    cells.current.instanceMatrix.needsUpdate = true;
    if (cells.current.instanceColor) cells.current.instanceColor.needsUpdate = true;
  }, []);
  return <group position={[side * 15.5, -0.35, z]} rotation={[0, 0, side * 0.08]}>
    <mesh><boxGeometry args={[6.65, 0.1, 4.6]} /><meshStandardMaterial color="#927b51" metalness={0.85} roughness={0.44} /></mesh>
    <instancedMesh ref={cells} args={[undefined, undefined, 96]}>
      <boxGeometry args={[0.49, 0.025, 0.49]} /><meshStandardMaterial metalness={0.65} roughness={0.38} />
    </instancedMesh>
    {[-2.32, 2.32].map(v => <mesh key={v} position={[0, 0.09, v]}><boxGeometry args={[6.8, 0.06, 0.07]} /><meshStandardMaterial color="#d6d6c7" metalness={0.75} /></mesh>)}
    <mesh position={[-side * 4.65, -0.05, 0]}><boxGeometry args={[3.4, 0.19, 0.2]} /><meshStandardMaterial color="#bbc5c7" metalness={0.6} /></mesh>
    <mesh position={[-side * 3.55, -0.05, 0]} rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.3, 0.3, 0.6, 12]} /><meshStandardMaterial color="#778a94" metalness={0.75} /></mesh>
  </group>;
}

function Truss({ rooms, corridors }: { rooms: Entity[]; corridors: Edge[] }) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const beams = useMemo(() => {
    const result: [THREE.Vector3, THREE.Vector3][] = [];
    for (const edge of corridors) {
      const a = rooms.find(r => r.id === edge.source)!;
      const b = rooms.find(r => r.id === edge.target)!;
      const start = new THREE.Vector3(a.x!, -1.35, a.z!);
      const end = new THREE.Vector3(b.x!, -1.35, b.z!);
      const perpendicular = end.clone().sub(start).normalize().cross(new THREE.Vector3(0, 1, 0)).multiplyScalar(0.5);
      const leftA = start.clone().add(perpendicular), leftB = end.clone().add(perpendicular);
      const rightA = start.clone().sub(perpendicular), rightB = end.clone().sub(perpendicular);
      result.push([leftA, leftB], [rightA, rightB]);
      const count = Math.ceil(start.distanceTo(end) / 1.6);
      for (let i = 0; i < count; i++) {
        const t = i / count, next = (i + 1) / count;
        result.push([leftA.clone().lerp(leftB, t), rightA.clone().lerp(rightB, next)]);
        result.push([rightA.clone().lerp(rightB, t), leftA.clone().lerp(leftB, next)]);
      }
    }
    return result;
  }, [rooms.map(r => `${r.id}:${r.x}:${r.z}`).join('|'), corridors.map(e => `${e.source}:${e.target}`).join('|')]);
  useLayoutEffect(() => {
    if (!mesh.current) return;
    const dummy = new THREE.Object3D(), up = new THREE.Vector3(0, 1, 0);
    beams.forEach(([a, b], i) => {
      dummy.position.copy(a).add(b).multiplyScalar(0.5);
      dummy.quaternion.setFromUnitVectors(up, b.clone().sub(a).normalize());
      dummy.scale.set(1, a.distanceTo(b), 1);
      dummy.updateMatrix();
      mesh.current!.setMatrixAt(i, dummy.matrix);
    });
    mesh.current.instanceMatrix.needsUpdate = true;
  }, [beams]);
  return <instancedMesh ref={mesh} args={[undefined, undefined, beams.length]}>
    <cylinderGeometry args={[0.045, 0.045, 1, 5]} /><meshStandardMaterial color="#738896" metalness={0.8} roughness={0.55} />
  </instancedMesh>;
}

export function StationHardware({ rooms, corridors }: { rooms: Entity[]; corridors: Edge[] }) {
  return <>
    <Truss rooms={rooms} corridors={corridors} />
    {[-1, 1].map(side => [-3.2, 3.2].map(z => <SolarWing key={`${side}-${z}`} side={side} z={z} />))}
    <group position={[0, 0.6, -12.35]}>
      <mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.86, 0.86, 1.5, 20]} /><meshStandardMaterial color="#b6c2c7" metalness={0.55} roughness={0.55} /></mesh>
      <mesh position={[0, 0, -0.8]}><torusGeometry args={[0.86, 0.16, 8, 24]} /><meshStandardMaterial color="#e5e5d9" metalness={0.6} roughness={0.5} /></mesh>
      <mesh position={[0, 0, -0.84]}><torusGeometry args={[0.64, 0.025, 5, 24]} /><meshBasicMaterial color="#83d9d5" /></mesh>
      <mesh position={[0, 0, -0.84]}><circleGeometry args={[0.6, 24]} /><meshStandardMaterial color="#142833" metalness={0.6} roughness={0.4} side={THREE.DoubleSide} /></mesh>
      {[-1, 1].map(side => <mesh key={side} position={[side * 1.7, -0.3, 0.2]} rotation={[0, 0, side * 0.2]}><boxGeometry args={[2, 0.06, 2.5]} /><meshStandardMaterial color="#d2d6d2" metalness={0.3} roughness={0.7} /></mesh>)}
    </group>
    <group position={[8, 2.7, -5]}>
      <mesh position={[0, 0.6, 0]}><cylinderGeometry args={[0.055, 0.055, 1.4, 8]} /><meshStandardMaterial color="#c5cccb" metalness={0.7} /></mesh>
      <group position={[0, 1.4, 0]} rotation={[0.6, 0.5, 0.2]}>
        <mesh rotation={[Math.PI / 2, 0, 0]}><sphereGeometry args={[1.05, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2]} /><meshStandardMaterial color="#d6d9d2" side={THREE.DoubleSide} metalness={0.5} roughness={0.5} /></mesh>
        <Line points={[[-0.8, 0, 0], [0, 0, -0.8], [0.8, 0, 0]]} color="#8ba5ae" lineWidth={1} />
      </group>
    </group>
  </>;
}
