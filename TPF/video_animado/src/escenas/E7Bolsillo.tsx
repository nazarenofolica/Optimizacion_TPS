import React from "react";
import { AbsoluteFill } from "remotion";
import { C, SOMBRA, TITULO } from "../lib/tema";
import { ap, contar, miles, REBOTA } from "../lib/anim";
import { cuadro, escena } from "../lib/tiempo";
import { Fondo, Lienzo, Parte, Pop, PopG, Sello, Sfx, Tics, useF, AparecG } from "../comp/UI";
import { caminar, poseEn, Stickman } from "../comp/Stickman";
import { Calendario, Tienda, Tilde } from "../comp/Iconos";

/*
 * El hilo del capítulo: un marcador con las tres formas de pagar menos, que se va completando, y abajo siempre el mismo
 * gráfico (antes / después) con los números del video largo. Cada palanca es un caso distinto del informe: se dice
 * cuál, para no sumar ahorros que no se suman.
 */
const PALANCAS = [
  {
    nombre: "comprar por mes",
    caso: "la misma dieta · costo por día",
    antes: { etq: "por semana", v: 3433 },
    despues: { etq: "por mes", v: 2540 },
    sello: "−26 %",
  },
  {
    nombre: "caminar más",
    caso: "hogar de dos, en Córdoba · una semana",
    antes: { etq: "15 min", v: 56256 },
    despues: { etq: "60 min", v: 42140 },
    sello: "−25 %",
  },
  {
    nombre: "dos súper",
    caso: "celíaca con alergias y nena escolar · una semana",
    antes: { etq: "1 súper", v: 288518 },
    despues: { etq: "2 súper", v: 109028 },
    sello: "−62 %",
  },
];

const Billetera: React.FC = () => (
  <g>
    <rect x={-60} y={-40} width={120} height={84} rx={16} fill="#B5754A" stroke={C.tinta} strokeWidth={6} />
    <path d="M-60,-14 L60,-14" stroke={C.tinta} strokeWidth={5} />
    <rect x={20} y={-4} width={44} height={30} rx={10} fill="#8A5634" stroke={C.tinta} strokeWidth={5} />
    <circle cx={36} cy={11} r={6} fill={C.amarillo} />
    <rect x={-44} y={-58} width={70} height={30} rx={5} fill={C.verde} stroke={C.tinta} strokeWidth={4} transform="rotate(-8)" />
  </g>
);

type Claves = { slots: number; inicio: number[]; sello: number[] };

const Marcador: React.FC<{ k: Claves; f: number }> = ({ k, f }) => {
  const iconos = [
    <g key="m" transform="scale(0.45)">
      <Calendario texto="30" color={C.verde} />
    </g>,
    <g key="c" transform="scale(0.42) translate(0,40)">
      <Stickman x={0} y={60} f={f} pose={caminar(f / 30, 2)} cara="feliz" color={C.violeta} extras={["cola"]} semilla={3} escala={0.75} />
    </g>,
    <g key="d" transform="scale(0.3)">
      <g transform="translate(-70,0)">
        <Tienda color={C.rojo} ancho={160} />
      </g>
      <g transform="translate(80,10)">
        <Tienda color={C.azul} ancho={160} />
      </g>
    </g>,
  ];
  return (
    <div style={{ position: "absolute", top: 370, left: 50, right: 50, display: "flex", justifyContent: "space-between" }}>
      {PALANCAS.map((p, i) => {
        const activa = f >= k.inicio[i] && f < k.inicio[i + 1];
        const hecha = f >= k.sello[i] + 8;
        return (
          <Pop key={p.nombre} en={k.slots + i * 4} style={{ position: "relative" }} vol={0.18}>
            <div
              style={{
                width: 300,
                height: 200,
                borderRadius: 30,
                background: hecha ? C.verdeClaro : C.papel,
                border: `6px solid ${activa ? C.amarillo : hecha ? C.verde : C.tinta}`,
                boxShadow: activa ? `0 0 0 6px ${C.tinta}, ${SOMBRA}` : SOMBRA,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                transform: `scale(${activa ? 1.04 : 1})`,
                opacity: !activa && !hecha && f >= k.inicio[0] ? 0.55 : 1,
              }}
            >
              <svg width={120} height={90} viewBox="-60 -50 120 100" style={{ overflow: "visible" }}>
                {iconos[i]}
              </svg>
              <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 32, color: C.tinta }}>
                {i + 1}. {p.nombre}
              </div>
              <div style={{ height: 44, fontFamily: TITULO, fontWeight: 700, fontSize: 38, color: C.verde, display: "flex", alignItems: "center", gap: 8 }}>
                {hecha && (
                  <>
                    <svg width={34} height={34} viewBox="-45 -45 90 90">
                      <Tilde r={40} />
                    </svg>
                    {p.sello}
                  </>
                )}
              </div>
            </div>
          </Pop>
        );
      })}
    </div>
  );
};

/** El gráfico de cada palanca: dos barras (antes en tinta, después en verde), el caso y el sello del ahorro. */
const Comparacion: React.FC<{ p: (typeof PALANCAS)[number]; en: number; sello: number; extra?: React.ReactNode }> = ({ p, en, sello, extra }) => {
  const f = useF();
  const ALTO = 380;
  const BASE = 1150;
  const barras = [
    { ...p.antes, x: 150, color: C.tinta, en: en + 6 },
    { ...p.despues, x: 420, color: C.verde, en: en + 18 },
  ];
  return (
    <>
      <Pop en={en} style={{ top: 610, left: 70, right: 70 }} desde="abajo">
        <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 32, color: C.tintaSuave }}>{p.caso}</div>
      </Pop>
      <Lienzo>
        {barras.map((b) => {
          const s = ap(f, b.en, 16, REBOTA);
          const h = (b.v / p.antes.v) * ALTO * s;
          if (f < b.en) return null;
          return (
            <g key={b.etq}>
              <rect x={b.x} y={BASE - h} width={190} height={h} rx={16} fill={b.color} stroke={C.tinta} strokeWidth={6} />
              <text x={b.x + 95} y={BASE - h - 18} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={44} fill={b.color === C.verde ? C.verde : C.tinta} opacity={Math.min(1, s)}>
                ${miles(contar(f, b.en, 16, 0, b.v))}
              </text>
              <text x={b.x + 95} y={BASE + 50} textAnchor="middle" fontFamily={TITULO} fontWeight={600} fontSize={36} fill={C.tinta}>
                {b.etq}
              </text>
            </g>
          );
        })}
        <line x1={110} y1={BASE} x2={660} y2={BASE} stroke={C.tinta} strokeWidth={6} strokeLinecap="round" />
      </Lienzo>
      <Sello en={sello} rota={-8} style={{ top: 780, left: 700 }}>
        <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 96, color: C.papel, background: C.verde, border: `8px solid ${C.tinta}`, borderRadius: 30, padding: "0 26px" }}>
          {p.sello}
        </div>
      </Sello>
      {extra}
      <Tics desde={en + 6} hasta={en + 34} cada={3} vol={0.12} />
    </>
  );
};

export const E7Bolsillo: React.FC = () => {
  const f = useF();
  const fin = escena("e7").hasta;
  const k = {
    bolsillo: cuadro("b22"),
    slots: cuadro("b22", "tres"),
    inicio: [cuadro("b23"), cuadro("b24"), cuadro("b25"), fin + 100],
    sello: [cuadro("b23", "26"), cuadro("b24", "25"), cuadro("b25", "mitad")],
    envases: cuadro("b23", "envases"),
    caminar: cuadro("b24", "caminar"),
    caso: cuadro("b25", "caso"),
  };

  return (
    <AbsoluteFill>
      <Fondo />
      <Parte desde={k.bolsillo} hasta={fin - 2} mudo>
        <Marcador k={k} f={f} />
      </Parte>

      {/* Antes de la primera: Sofi con la billetera */}
      <Parte desde={k.bolsillo} hasta={k.inicio[0]}>
        <Pop en={k.bolsillo} style={{ top: 640, left: 0, right: 0, display: "flex", justifyContent: "center" }} desde="abajo">
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 60, color: C.tinta, textAlign: "center", lineHeight: 1.05 }}>
            la misma canasta,
            <br />
            <span style={{ background: C.amarillo, borderRadius: 18, padding: "0 14px" }}>pagando menos</span>
          </div>
        </Pop>
        <Lienzo>
          <AparecG en={k.bolsillo + 4}>
            <Stickman
              x={460}
              y={1235}
              escala={1.15}
              f={f}
              pose={poseEn(f, [[0, "parada"], [k.slots, "señala"]])}
              cara="contenta"
              color={C.violeta}
              extras={["cola"]}
              semilla={3}
            />
          </AparecG>
          <PopG en={k.bolsillo + 10} x={680} y={1020} escala={1.2} flota={8} sonido="caja" vol={0.3}>
            <Billetera />
          </PopG>
        </Lienzo>
      </Parte>

      {/* Las tres palancas, una por vez */}
      {PALANCAS.map((p, i) => (
        <Parte key={p.nombre} desde={k.inicio[i] + 8} hasta={i < 2 ? k.inicio[i + 1] : fin - 2} mudo={i === 2}>
          <Comparacion
            p={p}
            en={k.inicio[i] + 8}
            sello={k.sello[i]}
            extra={
              i === 0 ? (
                <Pop en={k.envases} style={{ top: 960, left: 700, width: 320 }} sonido={null}>
                  <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 32, color: C.tinta, lineHeight: 1.15 }}>
                    se aprovechan mejor los envases
                  </div>
                </Pop>
              ) : i === 2 ? (
                <Pop en={k.caso} style={{ top: 960, left: 700, width: 320 }} sonido={null}>
                  <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 32, color: C.tinta, lineHeight: 1.15 }}>
                    en un caso: más de la mitad
                  </div>
                </Pop>
              ) : null
            }
          />
        </Parte>
      ))}

      <Sfx en={k.caminar} s="pasos" vol={0.4} />
      {k.sello.map((s) => (
        <Sfx key={s} en={s + 8} s="caja" vol={0.35} />
      ))}
    </AbsoluteFill>
  );
};
