import React from "react";
import { C } from "../lib/tema";
import { ap, MUEVE, REBOTA } from "../lib/anim";

/**
 * Una stickman de trazo grueso, armada por cinemática directa: hombro → codo → mano y cadera → rodilla → pie.
 * Ángulos en grados: 0 = hacia abajo, 90 = hacia adelante (a donde mira), -90 = hacia atrás, 180 = arriba.
 * El brazo y la pierna "cerca" son los del lado de la cámara; `[u, f]` = segmento de arriba (absoluto) y doblez.
 */
export type Pose = {
  inclina: number; // torso, grados (positivo = hacia adelante)
  cabeza: number; // inclinación de la cabeza
  bA: [number, number]; // brazo de adelante
  bB: [number, number]; // brazo de atrás
  pA: [number, number]; // pierna de adelante
  pB: [number, number]; // pierna de atrás
  alto?: number; // salto, px hacia arriba
};

export type Cara =
  | "feliz"
  | "contenta"
  | "asco"
  | "sorpresa"
  | "pensando"
  | "triste"
  | "preocupada"
  | "neutral"
  | "decidida";

export const POSES: Record<string, Pose> = {
  parada: { inclina: 0, cabeza: 0, bA: [26, -18], bB: [-24, 16], pA: [10, 0], pB: [-10, 0] },
  saluda: { inclina: -3, cabeza: -6, bA: [150, 40], bB: [-14, 8], pA: [8, 0], pB: [-8, 0] },
  festeja: { inclina: -4, cabeza: -8, bA: [155, -15], bB: [-155, 15], pA: [14, 0], pB: [-14, 0] },
  señala: { inclina: 3, cabeza: 4, bA: [100, -4], bB: [-10, 10], pA: [10, 0], pB: [-8, 0] },
  piensa: { inclina: 0, cabeza: 8, bA: [30, 130], bB: [-6, 60], pA: [6, 0], pB: [-6, 0] },
  asco: { inclina: -12, cabeza: -14, bA: [70, 70], bB: [55, 85], pA: [10, 0], pB: [-14, 8] },
  encoge: { inclina: 0, cabeza: 10, bA: [55, 100], bB: [-55, -100], pA: [8, 0], pB: [-8, 0] },
  celular: { inclina: 4, cabeza: 14, bA: [35, 95], bB: [20, 105], pA: [8, 0], pB: [-8, 0] },
  tira: { inclina: -20, cabeza: -6, bA: [95, 8], bB: [85, 14], pA: [34, -4], pB: [-30, 30] },
  empuja: { inclina: 14, cabeza: -4, bA: [75, 10], bB: [70, 15], pA: [22, -14], pB: [-26, 10] },
  manosCadera: { inclina: 0, cabeza: 0, bA: [45, -95], bB: [-45, 95], pA: [12, 0], pB: [-12, 0] },
  come: { inclina: 4, cabeza: 6, bA: [40, 120], bB: [30, 70], pA: [8, 0], pB: [-8, 0] },
};

export const mezclarPose = (a: Pose, b: Pose, t: number): Pose => {
  const m = (x: number, y: number) => x + (y - x) * t;
  const par = (x: [number, number], y: [number, number]): [number, number] => [m(x[0], y[0]), m(x[1], y[1])];
  return {
    inclina: m(a.inclina, b.inclina),
    cabeza: m(a.cabeza, b.cabeza),
    bA: par(a.bA, b.bA),
    bB: par(a.bB, b.bB),
    pA: par(a.pA, b.pA),
    pB: par(a.pB, b.pB),
    alto: m(a.alto ?? 0, b.alto ?? 0),
  };
};

/** Pasa de pose en pose: cada clave [cuadro, pose] empieza su transición en ese cuadro (con un poco de rebote). */
export const poseEn = (f: number, claves: [number, Pose | string][], dur = 9): Pose => {
  const P = (p: Pose | string) => (typeof p === "string" ? POSES[p] : p);
  let actual = P(claves[0][1]);
  for (let i = 1; i < claves.length; i++) {
    const [c, p] = claves[i];
    if (f < c) break;
    actual = mezclarPose(actual, P(p), ap(f, c, dur, REBOTA));
  }
  return actual;
};

/** Ciclo de caminata (fase en segundos × pasos por segundo). */
export const caminar = (t: number, ritmo = 1.8, amp = 1): Pose => {
  const s = Math.sin(t * Math.PI * 2 * ritmo * 0.5);
  const c = Math.cos(t * Math.PI * 2 * ritmo * 0.5);
  return {
    inclina: 5,
    cabeza: 0,
    bA: [-28 * s * amp, 20],
    bB: [28 * s * amp, 20],
    pA: [30 * s * amp, Math.max(0, -c) * 40 * amp],
    pB: [-30 * s * amp, Math.max(0, c) * 40 * amp],
    alto: Math.abs(c) * 6 * amp,
  };
};

const L = { torso: 82, cabeza: 31, brazo: 44, ante: 42, muslo: 52, pierna: 52 };
const rad = (g: number) => (g * Math.PI) / 180;
const dir = (g: number) => [Math.sin(rad(g)), Math.cos(rad(g))] as const;

type Props = {
  x: number;
  y: number; // el piso
  escala?: number;
  pose: Pose;
  cara?: Cara;
  mira?: "der" | "izq";
  f: number; // cuadro (para parpadear y respirar)
  semilla?: number;
  color?: string; // color del torso (identidad)
  extras?: ("anteojos" | "sombrero" | "moño" | "cola" | "gorra" | "vincha")[];
  tinte?: string; // color de la cara (asco = verde)
  sudor?: boolean;
  enMano?: React.ReactNode; // algo en la mano de adelante (se dibuja en coordenadas de la mano)
  tinta?: string;
  opacidad?: number;
};

export const Stickman: React.FC<Props> = ({
  x,
  y,
  escala = 1,
  pose,
  cara = "feliz",
  mira = "der",
  f,
  semilla = 0,
  color,
  extras = [],
  tinte,
  sudor,
  enMano,
  tinta = C.tinta,
  opacidad = 1,
}) => {
  const resp = Math.sin((f / 30) * 2 * Math.PI * 0.45 + semilla) * 1.6;
  const inclina = pose.inclina + resp * 0.6;
  // Piernas desde la cadera (0,0)
  const pierna = (p: [number, number]) => {
    const [ux, uy] = dir(p[0]);
    const rod = [ux * L.muslo, uy * L.muslo];
    const [vx, vy] = dir(p[0] - p[1]);
    return { rod, pie: [rod[0] + vx * L.pierna, rod[1] + vy * L.pierna] };
  };
  const pA = pierna(pose.pA);
  const pB = pierna(pose.pB);
  const suelo = Math.max(pA.pie[1], pB.pie[1]);
  const [tx, ty] = dir(180 - inclina);
  const cuello = [tx * L.torso, ty * L.torso];
  const hombro = [tx * (L.torso - 10), ty * (L.torso - 10)];
  const brazo = (b: [number, number]) => {
    const [ux, uy] = dir(b[0]);
    const codo = [hombro[0] + ux * L.brazo, hombro[1] + uy * L.brazo];
    const [vx, vy] = dir(b[0] + b[1]);
    return { codo, mano: [codo[0] + vx * L.ante, codo[1] + vy * L.ante], ang: b[0] + b[1] };
  };
  const bA = brazo(pose.bA);
  const bB = brazo(pose.bB);
  const [hx, hy] = dir(180 - inclina - pose.cabeza * 0.4);
  const cab = [cuello[0] + hx * (L.cabeza + 4), cuello[1] + hy * (L.cabeza + 4)];

  // Parpadeo: cada ~3 s, 3 cuadros.
  const ciclo = Math.floor(84 + ((semilla * 37) % 30));
  const parpadea = (f + Math.floor(semilla * 13)) % ciclo < 3;

  const trazo = { stroke: tinta, strokeWidth: 9, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
  const linea = (pts: number[][], extra?: object) => (
    <polyline points={pts.map((p) => p.join(",")).join(" ")} {...trazo} {...extra} />
  );
  const cuerpoColor = color ?? tinta;

  const ojoY = cab[1] - 3;
  const ojoX = cab[0] + 7;
  const ojos = (() => {
    if (parpadea || cara === "asco")
      return (
        <g stroke={tinta} strokeWidth={4} strokeLinecap="round">
          <line x1={ojoX - 13} y1={ojoY} x2={ojoX - 5} y2={ojoY + (cara === "asco" ? -3 : 0)} />
          <line x1={ojoX + 5} y1={ojoY + (cara === "asco" ? -3 : 0)} x2={ojoX + 13} y2={ojoY} />
        </g>
      );
    const r = cara === "sorpresa" ? 5.5 : 4.5;
    return (
      <g fill={tinta}>
        <circle cx={ojoX - 9} cy={ojoY} r={r} />
        <circle cx={ojoX + 9} cy={ojoY} r={r} />
      </g>
    );
  })();
  const cejas = (() => {
    const e = { stroke: tinta, strokeWidth: 3.5, strokeLinecap: "round" as const };
    const cy = ojoY - 11;
    if (cara === "sorpresa")
      return (
        <g {...e}>
          <line x1={ojoX - 14} y1={cy - 4} x2={ojoX - 5} y2={cy - 6} />
          <line x1={ojoX + 5} y1={cy - 6} x2={ojoX + 14} y2={cy - 4} />
        </g>
      );
    if (cara === "preocupada" || cara === "triste")
      return (
        <g {...e}>
          <line x1={ojoX - 14} y1={cy + 1} x2={ojoX - 5} y2={cy - 3} />
          <line x1={ojoX + 5} y1={cy - 3} x2={ojoX + 14} y2={cy + 1} />
        </g>
      );
    if (cara === "decidida" || cara === "asco")
      return (
        <g {...e}>
          <line x1={ojoX - 14} y1={cy - 3} x2={ojoX - 5} y2={cy + 1} />
          <line x1={ojoX + 5} y1={cy + 1} x2={ojoX + 14} y2={cy - 3} />
        </g>
      );
    if (cara === "pensando")
      return (
        <g {...e}>
          <line x1={ojoX - 14} y1={cy} x2={ojoX - 5} y2={cy} />
          <line x1={ojoX + 5} y1={cy - 5} x2={ojoX + 14} y2={cy - 7} />
        </g>
      );
    return null;
  })();
  const boca = (() => {
    const bx = cab[0] + 7;
    const by = cab[1] + 12;
    const m = { stroke: tinta, strokeWidth: 4, strokeLinecap: "round" as const, fill: "none" };
    switch (cara) {
      case "contenta":
        return <path d={`M${bx - 11},${by - 2} Q${bx},${by + 14} ${bx + 11},${by - 2} Z`} fill={tinta} stroke={tinta} strokeWidth={3} strokeLinejoin="round" />;
      case "sorpresa":
        return <ellipse cx={bx} cy={by + 3} rx={5.5} ry={7} fill={tinta} />;
      case "asco":
        return <path d={`M${bx - 11},${by + 2} q4,-5 7,0 t7,0 t7,0`} {...m} />;
      case "triste":
        return <path d={`M${bx - 9},${by + 6} Q${bx},${by - 3} ${bx + 9},${by + 6}`} {...m} />;
      case "preocupada":
        return <path d={`M${bx - 9},${by + 3} q4.5,-4 9,0 t9,0`} {...m} />;
      case "pensando":
      case "neutral":
      case "decidida":
        return <line x1={bx - 7} y1={by + 3} x2={bx + 7} y2={by + 1} {...m} />;
      default:
        return <path d={`M${bx - 10},${by} Q${bx},${by + 10} ${bx + 10},${by}`} {...m} />;
    }
  })();

  const alto = pose.alto ?? 0;
  return (
    <g
      transform={`translate(${x},${y - alto * escala}) scale(${(mira === "izq" ? -1 : 1) * escala},${escala}) translate(0,${-suelo})`}
      opacity={opacidad}
    >
      {/* sombra */}
      <ellipse cx={0} cy={suelo + 4 + alto} rx={46 - Math.min(20, alto * 0.3)} ry={8} fill="rgba(35,33,58,0.12)" />
      {/* atrás: brazo y pierna lejanos, más claros */}
      <g opacity={0.9}>
        {linea([[0, 0], pB.rod, pB.pie])}
        {linea([hombro, bB.codo, bB.mano])}
      </g>
      {extras.includes("cola") && (
        <path
          d={`M${cab[0] - 26},${cab[1] - 8} q-26,${6 + resp * 2} -22,${34 + resp * 3}`}
          stroke={tinta}
          strokeWidth={11}
          strokeLinecap="round"
          fill="none"
        />
      )}
      {linea([[0, 0], cuello], { stroke: cuerpoColor, strokeWidth: color ? 14 : 9 })}
      {linea([[0, 0], pA.rod, pA.pie])}
      {/* cabeza */}
      <g transform={`rotate(${pose.cabeza * 0.5},${cab[0]},${cab[1]})`}>
        <circle cx={cab[0]} cy={cab[1]} r={L.cabeza} fill={tinte ?? C.papel} stroke={tinta} strokeWidth={8} />
        {extras.includes("vincha") && (
          <path d={`M${cab[0] - 30},${cab[1] - 12} Q${cab[0]},${cab[1] - 24} ${cab[0] + 30},${cab[1] - 12}`} stroke={color ?? C.verde} strokeWidth={8} fill="none" />
        )}
        {ojos}
        {cejas}
        {boca}
        {extras.includes("anteojos") && (
          <g stroke={tinta} strokeWidth={3} fill="rgba(255,255,255,0.35)">
            <circle cx={ojoX - 9} cy={ojoY} r={9} />
            <circle cx={ojoX + 9} cy={ojoY} r={9} />
          </g>
        )}
        {extras.includes("sombrero") && (
          <g fill={tinta}>
            <rect x={cab[0] - 40} y={cab[1] - 34} width={80} height={9} rx={4} />
            <path d={`M${cab[0] - 22},${cab[1] - 30} L${cab[0] - 19},${cab[1] - 60} Q${cab[0]},${cab[1] - 66} ${cab[0] + 19},${cab[1] - 60} L${cab[0] + 22},${cab[1] - 30} Z`} />
          </g>
        )}
        {extras.includes("gorra") && (
          <g fill={color ?? C.rojo}>
            <path d={`M${cab[0] - 30},${cab[1] - 10} A30,30 0 0 1 ${cab[0] + 30},${cab[1] - 10} Z`} />
            <rect x={cab[0] + 14} y={cab[1] - 14} width={30} height={7} rx={3} />
          </g>
        )}
        {cara === "asco" && <circle cx={cab[0] - 14} cy={cab[1] + 10} r={6} fill="rgba(34,176,125,0.55)" />}
        {sudor && (
          <path
            d={`M${cab[0] - 30},${cab[1] - 20} q-6,10 0,14 q6,-4 0,-14`}
            fill={C.azul}
            transform={`translate(0,${(f % 20) * 0.5})`}
          />
        )}
      </g>
      {extras.includes("moño") && (
        <path d={`M${cuello[0] - 12},${cuello[1] + 2} l12,6 l-12,6 z M${cuello[0] + 12},${cuello[1] + 2} l-12,6 l12,6 z`} fill={C.rojo} />
      )}
      {/* adelante */}
      {linea([hombro, bA.codo, bA.mano])}
      {enMano && (
        <g transform={`translate(${bA.mano[0]},${bA.mano[1]}) scale(${mira === "izq" ? -1 : 1},1)`}>{enMano}</g>
      )}
    </g>
  );
};

/** Desplazamiento horizontal con curva (para que entre o cruce caminando). */
export const recorrido = (f: number, desde: number, dur: number, x0: number, x1: number) =>
  x0 + (x1 - x0) * ap(f, desde, dur, MUEVE);
