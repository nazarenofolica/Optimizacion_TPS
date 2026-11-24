import React from "react";
import { C } from "../lib/tema";
import { useF } from "./UI";

const COLS = [C.amarillo, C.verde, C.rojo, C.azul, C.violeta, C.naranja];

/** Confeti que estalla en (x, y) en el cuadro `en` y cae con gravedad (determinista: sin Math.random). */
export const Confeti: React.FC<{ en: number; x: number; y: number; n?: number; fuerza?: number }> = ({ en, x, y, n = 46, fuerza = 1 }) => {
  const f = useF();
  const t = (f - en) / 30;
  if (t < 0 || t > 2.4) return null;
  return (
    <g>
      {Array.from({ length: n }, (_, i) => {
        const h = Math.sin(i * 91.7) * 43758.5453;
        const r = h - Math.floor(h);
        const a = -Math.PI / 2 + (r - 0.5) * 2.4;
        const v = (700 + 600 * ((i * 0.618) % 1)) * fuerza;
        const px = x + Math.cos(a) * v * t;
        const py = y + Math.sin(a) * v * t + 900 * t * t;
        const giro = (t * 720 + i * 40) % 360;
        return (
          <rect
            key={i}
            x={px - 8}
            y={py - 5}
            width={16}
            height={10}
            rx={2}
            fill={COLS[i % COLS.length]}
            transform={`rotate(${giro},${px},${py})`}
            opacity={Math.min(1, (2.4 - t) * 2)}
          />
        );
      })}
    </g>
  );
};

/** Un anillo de `total` puntos que se van llenando (metas cumplidas). */
export const AnilloMetas: React.FC<{ x: number; y: number; r: number; total: number; llenos: number; color?: string }> = ({
  x,
  y,
  r,
  total,
  llenos,
  color = C.verde,
}) => (
  <g transform={`translate(${x},${y})`}>
    {Array.from({ length: total }, (_, i) => {
      const a = (i / total) * Math.PI * 2 - Math.PI / 2;
      const lleno = i < llenos;
      return (
        <circle
          key={i}
          cx={Math.cos(a) * r}
          cy={Math.sin(a) * r}
          r={lleno ? 13 : 10}
          fill={lleno ? color : "rgba(35,33,58,0.12)"}
          stroke={lleno ? C.tinta : "none"}
          strokeWidth={3}
        />
      );
    })}
  </g>
);
