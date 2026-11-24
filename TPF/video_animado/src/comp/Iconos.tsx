import React from "react";
import { C, TITULO } from "../lib/tema";

// Íconos dibujados en SVG, centrados en (0,0) y de unos 120 px. Mismo trazo que las stickmans.
const T = { stroke: C.tinta, strokeWidth: 6, strokeLinejoin: "round" as const, strokeLinecap: "round" as const };

export const Bolsa: React.FC<{ color: string; letra?: string; tinta?: string }> = ({ color, letra, tinta = C.tinta }) => (
  <g>
    <path d="M-42,-50 L42,-50 L50,58 L-50,58 Z" fill={color} {...T} stroke={tinta} />
    <path d="M-42,-50 L-30,-66 L30,-66 L42,-50" fill={color} {...T} stroke={tinta} />
    <rect x={-30} y={-14} width={60} height={42} rx={8} fill="rgba(255,255,255,0.85)" stroke={tinta} strokeWidth={4} />
    {letra && (
      <text x={0} y={16} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={26} fill={tinta}>
        {letra}
      </text>
    )}
  </g>
);

export const Harina: React.FC<{ tinta?: string }> = ({ tinta }) => <Bolsa color="#F4EAD5" letra="HARINA" tinta={tinta} />;

export const Repollo: React.FC<{ tinta?: string }> = ({ tinta = C.tinta }) => (
  <g>
    <circle cx={0} cy={4} r={54} fill="#9BD47A" stroke={tinta} strokeWidth={6} />
    <path d="M-30,-30 Q0,10 -8,52 M30,-30 Q0,10 8,52 M0,-48 L0,50" stroke={tinta} strokeWidth={4} fill="none" strokeLinecap="round" />
    <path d="M-54,4 Q-20,-18 0,-48 Q20,-18 54,4" stroke={tinta} strokeWidth={4} fill="none" />
  </g>
);

export const Espinaca: React.FC<{ tinta?: string }> = ({ tinta = C.tinta }) => (
  <g>
    {[-34, 0, 34].map((dx, i) => (
      <g key={i} transform={`rotate(${dx * 0.6}) translate(${dx * 0.4},0)`}>
        <path d="M0,58 L0,10" stroke={tinta} strokeWidth={5} />
        <path d="M0,10 C-34,-10 -26,-58 0,-62 C26,-58 34,-10 0,10 Z" fill={i === 1 ? "#2F9E5B" : "#3DB86C"} stroke={tinta} strokeWidth={5} />
        <path d="M0,4 L0,-48" stroke={tinta} strokeWidth={3} />
      </g>
    ))}
  </g>
);

export const Fideos: React.FC<{ medio?: boolean }> = () => (
  <g>
    <rect x={-34} y={-62} width={68} height={124} rx={10} fill={C.amarillo} {...T} />
    <rect x={-22} y={-30} width={44} height={56} rx={6} fill={C.papel} stroke={C.tinta} strokeWidth={4} />
    {[-12, -2, 8].map((x) => (
      <path key={x} d={`M${x},-22 q6,8 0,16 q-6,8 0,16 q6,8 0,16`} stroke="#E0A526" strokeWidth={4} fill="none" />
    ))}
  </g>
);

export const Lentejas: React.FC = () => (
  <g>
    <path d="M-40,-40 L40,-40 L46,58 L-46,58 Z" fill="#B5754A" {...T} />
    <rect x={-40} y={-58} width={80} height={20} rx={6} fill="#8A5634" {...T} />
    {[[-18, 0], [6, -8], [20, 16], [-8, 22], [-24, 34], [14, 40], [0, 6]].map(([x, y], i) => (
      <ellipse key={i} cx={x} cy={y} rx={8} ry={6} fill="#E2A36F" stroke={C.tinta} strokeWidth={2.5} />
    ))}
  </g>
);

export const Arroz: React.FC = () => <Bolsa color={C.azulClaro} letra="ARROZ" />;

export const Leche: React.FC = () => (
  <g>
    <path d="M-34,-36 L0,-64 L34,-36 L34,62 L-34,62 Z" fill={C.blanco} {...T} />
    <path d="M-34,-36 L34,-36" {...T} />
    <path d="M-34,0 Q0,-14 34,0 L34,62 L-34,62 Z" fill={C.azul} opacity={0.85} />
    <path d="M-34,-36 L0,-64 L34,-36 L34,62 L-34,62 Z" fill="none" {...T} />
  </g>
);

export const Trigo: React.FC = () => (
  <g>
    <path d="M0,62 L0,-56" {...T} fill="none" />
    {[-40, -18, 4].map((y) => (
      <g key={y}>
        <ellipse cx={-14} cy={y} rx={10} ry={16} transform={`rotate(-30,-14,${y})`} fill={C.amarillo} {...T} strokeWidth={4} />
        <ellipse cx={14} cy={y} rx={10} ry={16} transform={`rotate(30,14,${y})`} fill={C.amarillo} {...T} strokeWidth={4} />
      </g>
    ))}
  </g>
);

export const Prohibido: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <g>
    <circle r={78} fill={C.papel} stroke={C.rojo} strokeWidth={10} />
    <g transform="scale(0.8)">{children}</g>
    <line x1={-55} y1={-55} x2={55} y2={55} stroke={C.rojo} strokeWidth={12} strokeLinecap="round" />
  </g>
);

export const Changuito: React.FC<{ lleno?: number; color?: string }> = ({ lleno = 1, color = C.rojo }) => (
  <g>
    {lleno > 0 && (
      <g opacity={Math.min(1, lleno)}>
        <circle cx={-26} cy={-42} r={18} fill={C.verde} stroke={C.tinta} strokeWidth={4} />
        <rect x={-6} y={-70} width={26} height={44} rx={5} fill={C.amarillo} stroke={C.tinta} strokeWidth={4} />
        <circle cx={34} cy={-40} r={16} fill={C.rojo} stroke={C.tinta} strokeWidth={4} />
      </g>
    )}
    <path d="M-80,-60 L-62,-60 L-46,10 L52,10 L64,-40 L-54,-40" fill="none" {...T} />
    <path d="M-54,-40 L64,-40 L52,10 L-46,10 Z" fill={color} opacity={0.25} />
    <circle cx={-34} cy={32} r={11} fill={C.tinta} />
    <circle cx={40} cy={32} r={11} fill={C.tinta} />
    <path d="M-46,10 L-40,22 L46,22" fill="none" {...T} />
  </g>
);

export const Tienda: React.FC<{ color: string; ancho?: number }> = ({ color, ancho = 200 }) => {
  const a = ancho / 2;
  const franjas = 6;
  return (
    <g>
      <rect x={-a + 8} y={-40} width={ancho - 16} height={130} fill={C.papel} {...T} />
      <rect x={-22} y={20} width={44} height={70} fill={C.azulClaro} {...T} strokeWidth={5} />
      <rect x={-a + 24} y={10} width={46} height={40} fill={C.azulClaro} {...T} strokeWidth={5} />
      <rect x={a - 70} y={10} width={46} height={40} fill={C.azulClaro} {...T} strokeWidth={5} />
      {Array.from({ length: franjas }).map((_, i) => (
        <path
          key={i}
          d={`M${-a + (ancho / franjas) * i},-70 h${ancho / franjas} v34 a${ancho / franjas / 2},14 0 0 1 ${-ancho / franjas},0 Z`}
          fill={i % 2 ? C.papel : color}
          stroke={C.tinta}
          strokeWidth={5}
        />
      ))}
      <rect x={-a} y={-96} width={ancho} height={28} rx={8} fill={color} {...T} strokeWidth={5} />
    </g>
  );
};

export const Celular: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <g>
    <rect x={-34} y={-60} width={68} height={120} rx={12} fill={C.tinta} />
    <rect x={-28} y={-50} width={56} height={98} rx={6} fill={C.papel} />
    {children}
  </g>
);

export const Calendario: React.FC<{ texto: string; sub?: string; color?: string }> = ({ texto, sub, color = C.rojo }) => (
  <g>
    <rect x={-70} y={-62} width={140} height={132} rx={16} fill={C.papel} {...T} />
    <path d="M-70,-30 L-70,-46 Q-70,-62 -54,-62 L54,-62 Q70,-62 70,-46 L70,-30 Z" fill={color} {...T} />
    <line x1={-36} y1={-76} x2={-36} y2={-50} {...T} />
    <line x1={36} y1={-76} x2={36} y2={-50} {...T} />
    <text x={0} y={30} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={56} fill={C.tinta}>
      {texto}
    </text>
    {sub && (
      <text x={0} y={58} textAnchor="middle" fontFamily={TITULO} fontWeight={600} fontSize={20} fill={C.tintaSuave}>
        {sub}
      </text>
    )}
  </g>
);

export const Pin: React.FC<{ color?: string }> = ({ color = C.rojo }) => (
  <g>
    <path d="M0,60 C-10,30 -44,8 -44,-20 A44,44 0 0 1 44,-20 C44,8 10,30 0,60 Z" fill={color} {...T} />
    <circle cx={0} cy={-20} r={16} fill={C.papel} stroke={C.tinta} strokeWidth={5} />
  </g>
);

export const Tilde: React.FC<{ r?: number; color?: string }> = ({ r = 40, color = C.verde }) => (
  <g>
    <circle r={r} fill={color} stroke={C.tinta} strokeWidth={r / 8} />
    <path
      d={`M${-r * 0.42},${r * 0.02} L${-r * 0.1},${r * 0.34} L${r * 0.45},${-r * 0.3}`}
      stroke={C.blanco}
      strokeWidth={r / 4.5}
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </g>
);

export const Cruz: React.FC<{ r?: number }> = ({ r = 40 }) => (
  <g>
    <circle r={r} fill={C.rojo} stroke={C.tinta} strokeWidth={r / 8} />
    <path d={`M${-r * 0.32},${-r * 0.32} L${r * 0.32},${r * 0.32} M${r * 0.32},${-r * 0.32} L${-r * 0.32},${r * 0.32}`} stroke={C.blanco} strokeWidth={r / 4.5} strokeLinecap="round" />
  </g>
);

export const Etiqueta: React.FC<{ texto: string; color?: string; ancho?: number }> = ({ texto, color = C.amarillo, ancho = 150 }) => (
  <g>
    <path d={`M${-ancho / 2},-34 L${ancho / 2 - 20},-34 L${ancho / 2 + 10},0 L${ancho / 2 - 20},34 L${-ancho / 2},34 Z`} fill={color} {...T} />
    <circle cx={ancho / 2 - 18} cy={0} r={6} fill={C.papel} stroke={C.tinta} strokeWidth={3} />
    <text x={-10} y={13} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={36} fill={C.tinta}>
      {texto}
    </text>
  </g>
);

export const Reloj: React.FC<{ minutos: number }> = ({ minutos }) => {
  const a = (minutos / 60) * 360;
  return (
    <g>
      <circle r={56} fill={C.papel} {...T} />
      <path d={describirArco(0, 0, 44, 0, Math.min(359.9, a))} fill={C.amarilloClaro} />
      <line x1={0} y1={0} x2={Math.sin((a * Math.PI) / 180) * 38} y2={-Math.cos((a * Math.PI) / 180) * 38} {...T} />
      <circle r={6} fill={C.tinta} />
    </g>
  );
};

export function describirArco(cx: number, cy: number, r: number, a0: number, a1: number) {
  const p = (a: number) => [cx + r * Math.sin((a * Math.PI) / 180), cy - r * Math.cos((a * Math.PI) / 180)];
  const [x0, y0] = p(a0);
  const [x1, y1] = p(a1);
  const grande = a1 - a0 > 180 ? 1 : 0;
  return `M${cx},${cy} L${x0},${y0} A${r},${r} 0 ${grande} 1 ${x1},${y1} Z`;
}

export const BaseDatos: React.FC<{ color?: string }> = ({ color = C.azul }) => (
  <g>
    {[30, 0, -30].map((y) => (
      <g key={y}>
        <path d={`M-60,${y - 20} L-60,${y + 14} A60,18 0 0 0 60,${y + 14} L60,${y - 20}`} fill={color} {...T} />
        <ellipse cx={0} cy={y - 20} rx={60} ry={18} fill={y === -30 ? C.azulClaro : color} {...T} />
      </g>
    ))}
  </g>
);

export const Corazon: React.FC<{ color?: string }> = ({ color = C.rojo }) => (
  <path d="M0,50 C-60,10 -66,-30 -38,-48 C-18,-60 0,-44 0,-30 C0,-44 18,-60 38,-48 C66,-30 60,10 0,50 Z" fill={color} {...T} />
);

export const Plato: React.FC<{ children?: React.ReactNode; tinta?: string }> = ({ children, tinta = C.tinta }) => (
  <g>
    <ellipse cx={0} cy={0} rx={130} ry={34} fill={C.papel} stroke={tinta} strokeWidth={6} />
    <ellipse cx={0} cy={-4} rx={92} ry={20} fill="none" stroke={tinta} strokeWidth={3} opacity={0.4} />
    {children}
  </g>
);

export const Avion: React.FC = () => (
  <g>
    <path d="M-60,0 L60,-50 L28,52 L4,20 Z" fill={C.azul} {...T} />
    <path d="M4,20 L60,-50 L-14,12" fill="none" {...T} />
    <path d="M4,20 L2,44 L18,32" fill={C.azulClaro} {...T} strokeWidth={4} />
  </g>
);

export const Estrella: React.FC<{ r?: number; color?: string }> = ({ r = 40, color = C.amarillo }) => {
  const pts = Array.from({ length: 10 }, (_, i) => {
    const a = (i * Math.PI) / 5 - Math.PI / 2;
    const rr = i % 2 ? r * 0.45 : r;
    return `${Math.cos(a) * rr},${Math.sin(a) * rr}`;
  }).join(" ");
  return <polygon points={pts} fill={color} stroke={C.tinta} strokeWidth={r / 10} strokeLinejoin="round" />;
};

export const Alerta: React.FC<{ r?: number }> = ({ r = 46 }) => (
  <g>
    <path d={`M0,${-r} L${r * 1.05},${r * 0.8} L${-r * 1.05},${r * 0.8} Z`} fill={C.amarillo} {...T} />
    <line x1={0} y1={-r * 0.35} x2={0} y2={r * 0.25} {...T} strokeWidth={8} />
    <circle cx={0} cy={r * 0.52} r={5} fill={C.tinta} />
  </g>
);

export const Brocoli: React.FC = () => (
  <g>
    <path d="M-10,60 L-6,4 L6,4 L10,60 Z" fill="#7CC36B" {...T} />
    {[[-26, -10], [0, -24], [26, -10], [-12, -40], [14, -42]].map(([x, y], i) => (
      <circle key={i} cx={x} cy={y} r={24} fill="#2F9E5B" {...T} strokeWidth={5} />
    ))}
  </g>
);

export const Paquete: React.FC<{ color: string }> = ({ color }) => (
  <g>
    <rect x={-30} y={-40} width={60} height={80} rx={8} fill={color} {...T} strokeWidth={5} />
    <rect x={-18} y={-14} width={36} height={26} rx={4} fill="rgba(255,255,255,0.8)" />
  </g>
);
