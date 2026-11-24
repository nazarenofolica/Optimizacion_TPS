import React from "react";
import { AbsoluteFill } from "remotion";
import { C, SOMBRA, TITULO } from "../lib/tema";
import { ap, ENTRA, MUEVE } from "../lib/anim";
import { cuadro, escena } from "../lib/tiempo";
import { Camara, Fondo, Parte, Pop, Sfx, Tarjeta, useF } from "../comp/UI";
import { Brocoli, Cruz, Prohibido, Tilde, Trigo } from "../comp/Iconos";

// Los números del video largo (TPF/video/escenas.py, E6Casos y E7Cierre), que salen del informe.
const CASOS = [
  { palabra: "familia", nombre: "Familia de cuatro", total: "$74.526", metas: "148/148" },
  { palabra: "celíaca", nombre: "Persona celíaca", total: "$29.236", metas: "37/37" },
  { palabra: "vegana", nombre: "Persona vegana", total: "$35.236", metas: "35/35" },
];
const BALAS = [
  { nombre: "Lácteos", valor: 2.0, minimo: 3.0, estado: "67 %" },
  { nombre: "Calcio", valor: 737, minimo: 1000, estado: "74 %" },
  { nombre: "Verduras", valor: 527, minimo: 300, estado: "cumple" },
  { nombre: "Hierro", valor: 31, minimo: 18, estado: "cumple" },
];
const SOMBRAS = [
  { nombre: "Calcio", v: 38.31 },
  { nombre: "Lácteos", v: 22.56 },
  { nombre: "Verduras", v: 21.59 },
  { nombre: "Vitamina B6", v: 15.11 },
  { nombre: "Pescado", v: 9.98 },
  { nombre: "Frutas", v: 9.36 },
];

const Familia: React.FC = () => (
  <g>
    {[
      [-42, -14, 20, C.azul],
      [-8, -18, 22, C.violeta],
      [26, 4, 14, C.amarillo],
      [50, 8, 12, C.verde],
    ].map(([x, y, r, c], i) => (
      <g key={i}>
        <circle cx={x as number} cy={y as number} r={r as number} fill={C.papel} stroke={C.tinta} strokeWidth={5} />
        <line x1={x as number} y1={(y as number) + (r as number)} x2={x as number} y2={50} stroke={c as string} strokeWidth={8} strokeLinecap="round" />
      </g>
    ))}
  </g>
);

export const E6Casos: React.FC = () => {
  const f = useF();
  const k = {
    reales: cuadro("b19"),
    familia: cuadro("b19", "familia"),
    celiaca: cuadro("b19", "celíaca"),
    vegana: cuadro("b19", "vegana"),
    todos: cuadro("b19", "todos"),
    pero: cuadro("b20"),
    cordoba: cuadro("b20", "córdoba"),
    ninguna: cuadro("b20", "ninguna"),
    calcio: cuadro("b20", "calcio"),
    lacteos: cuadro("b20", "lácteos"),
    sombra: cuadro("b21"),
    justo: cuadro("b21", "justo"),
    fin: escena("e6").hasta,
  };
  const enCaso = [k.familia, k.celiaca, k.vegana];
  const iconos = [
    <Familia key="f" />,
    <g key="c" transform="scale(0.8)">
      <Prohibido>
        <Trigo />
      </Prohibido>
    </g>,
    <g key="v" transform="scale(0.85)">
      <Brocoli />
    </g>,
  ];

  return (
    <AbsoluteFill>
      <Fondo />

      {/* ============ A: todos cumplen ============ */}
      <Parte desde={k.reales} hasta={k.pero}>
        <Pop en={k.reales} style={{ top: 375, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 36, color: C.tintaSuave }}>Compra para una semana, en el centro de Buenos Aires</div>
        </Pop>
        {CASOS.map((c, i) => {
          const cumple = ap(f, k.todos + i * 4, 10, ENTRA);
          return (
            <Pop key={c.nombre} en={enCaso[i]} style={{ top: 450 + i * 235, left: 70 }} desde="abajo">
              <Tarjeta style={{ position: "relative", width: 940, height: 200, display: "flex", alignItems: "center", gap: 26, padding: "0 30px", boxSizing: "border-box" }}>
                <svg width={150} height={150} viewBox="-75 -75 150 150">
                  {iconos[i]}
                </svg>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 44, color: C.tinta }}>{c.nombre}</div>
                  <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 52, color: C.tinta, fontVariantNumeric: "tabular-nums" }}>
                    {c.total} <span style={{ fontSize: 30, color: C.tintaSuave, fontWeight: 600 }}>por semana</span>
                  </div>
                </div>
                {/* las metas: primero el número; al "todos cumplen" el número se va y entra el sello (en su lugar) */}
                <div style={{ position: "relative", width: 230, height: 90 }}>
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: TITULO,
                      fontWeight: 600,
                      fontSize: 36,
                      color: C.tintaSuave,
                      opacity: 1 - cumple,
                    }}
                  >
                    {c.metas} metas
                  </div>
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 10,
                      background: C.verdeClaro,
                      border: `5px solid ${C.verde}`,
                      borderRadius: 45,
                      opacity: cumple,
                      transform: `scale(${0.6 + 0.4 * cumple})`,
                    }}
                  >
                    <svg width={44} height={44} viewBox="-45 -45 90 90">
                      <Tilde r={40} />
                    </svg>
                    <span style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 38, color: C.verde }}>{c.metas}</span>
                  </div>
                </div>
              </Tarjeta>
            </Pop>
          );
        })}
      </Parte>

      {/* ============ B: la meta imposible (los gráficos de bala de la página) ============ */}
      <Parte desde={k.pero + 8} hasta={k.sombra}>
        <Camara
          claves={[
            [0, 1, 540, 800],
            [k.calcio, 1.12, 540, 740],
            [k.sombra - 14, 1, 540, 800],
          ]}
        >
          <Pop en={k.pero + 8} style={{ top: 380, left: 70, right: 70 }} desde="abajo">
            <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 46, color: C.tinta, lineHeight: 1.1 }}>
              Celíaca y alérgica a la leche,
              <br />
              en {f >= k.cordoba ? "Córdoba" : "…"}
            </div>
          </Pop>
          <Pop en={k.ninguna} style={{ top: 520, left: 70 }} sonido="error" vol={0.25}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: 12, background: C.rojoClaro, border: `5px solid ${C.rojo}`, borderRadius: 40, padding: "6px 22px" }}>
              <svg width={40} height={40} viewBox="-45 -45 90 90">
                <Cruz r={40} />
              </svg>
              <span style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 36, color: C.rojo }}>35 de 37 metas</span>
            </div>
          </Pop>
          {BALAS.map((b, i) => {
            const ok = b.valor >= b.minimo;
            const tope = Math.max(b.minimo * 1.6, b.valor * 1.15);
            const ancho = 420;
            const crece = ap(f, k.ninguna + 4 + i * 4, 16, MUEVE);
            const realce = (i === 1 && f >= k.calcio) || (i === 0 && f >= k.lacteos) ? 1 : 0;
            return (
              <Pop key={b.nombre} en={k.ninguna + 4 + i * 4} style={{ top: 630 + i * 120, left: 50, right: 50 }} desde="abajo" vol={0.12}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 22,
                    height: 96,
                    padding: "0 20px",
                    borderRadius: 20,
                    background: ok ? "transparent" : C.rojoClaro,
                    border: realce ? `5px solid ${C.rojo}` : "5px solid transparent",
                    boxShadow: realce ? SOMBRA : "none",
                  }}
                >
                  <div style={{ width: 170, textAlign: "right", fontFamily: TITULO, fontWeight: ok ? 600 : 700, fontSize: 38, color: C.tinta }}>{b.nombre}</div>
                  <svg width={ancho} height={60} style={{ overflow: "visible" }}>
                    <rect x={0} y={18} width={ancho} height={24} rx={12} fill="rgba(35,33,58,0.12)" />
                    <rect x={(ancho * b.minimo) / tope} y={18} width={ancho * (1 - b.minimo / tope)} height={24} fill={C.verde} opacity={0.45} />
                    <line x1={(ancho * b.minimo) / tope} y1={8} x2={(ancho * b.minimo) / tope} y2={52} stroke={C.tintaSuave} strokeWidth={5} />
                    <circle
                      cx={((ancho * b.valor) / tope) * crece}
                      cy={30}
                      r={15}
                      fill={ok ? C.tinta : C.papel}
                      stroke={ok ? C.tinta : C.rojo}
                      strokeWidth={ok ? 0 : 7}
                    />
                  </svg>
                  <svg width={40} height={40} viewBox="-45 -45 90 90">
                    {ok ? <Tilde r={40} /> : <Cruz r={40} />}
                  </svg>
                  <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 34, color: ok ? C.verde : C.rojo }}>
                    {ok ? b.estado : `llega al ${b.estado}`}
                  </div>
                </div>
              </Pop>
            );
          })}
          <Pop en={k.ninguna + 24} style={{ top: 1130, left: 0, right: 0, display: "flex", justifyContent: "center" }} sonido={null}>
            <div style={{ fontFamily: TITULO, fontWeight: 500, fontSize: 30, color: C.tintaSuave }}>la franja verde es la meta; el punto, lo que come</div>
          </Pop>
        </Camara>
      </Parte>

      {/* ============ C: precios sombra (sensibilidad) ============ */}
      <Parte desde={k.sombra + 8} hasta={k.fin - 2} mudo>
        <Pop en={k.sombra + 8} style={{ top: 380, left: 70, right: 70 }} desde="abajo">
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 44, color: C.tinta, lineHeight: 1.1 }}>
            Cuánto encarece la semana pedir un 1 % más de cada meta
          </div>
          <div style={{ fontFamily: TITULO, fontWeight: 500, fontSize: 30, color: C.tintaSuave, marginTop: 6 }}>precios sombra, caso base</div>
        </Pop>
        {SOMBRAS.map((s, i) => {
          const en = k.sombra + 12 + i * 3;
          const crece = ap(f, en, 16, MUEVE);
          const top = i < 2;
          const realce = top && f >= k.justo;
          return (
            <Pop key={s.nombre} en={en} style={{ top: 560 + i * 100, left: 60, right: 60 }} desde="abajo" vol={0.1}>
              <div style={{ display: "flex", alignItems: "center", gap: 20, height: 80 }}>
                <div style={{ width: 230, textAlign: "right", fontFamily: TITULO, fontWeight: top ? 700 : 600, fontSize: 36, color: C.tinta }}>{s.nombre}</div>
                <div style={{ width: (s.v / 38.31) * 470 * crece, height: 46, borderRadius: 12, background: top ? C.azul : "rgba(35,33,58,0.22)", boxShadow: realce ? `0 0 0 6px ${C.amarillo}` : "none" }} />
                <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 34, color: top ? C.azul : C.tintaSuave, fontVariantNumeric: "tabular-nums" }}>
                  ${s.v.toFixed(2).replace(".", ",")}
                </div>
              </div>
            </Pop>
          );
        })}
        <Pop en={k.justo} style={{ top: 1160, left: 0, right: 0, display: "flex", justifyContent: "center" }} sonido="brillo" vol={0.3}>
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 38, color: C.tinta, background: C.amarillo, border: `5px solid ${C.tinta}`, borderRadius: 30, padding: "6px 26px" }}>
            calcio y lácteos: justo las que le faltaban
          </div>
        </Pop>
      </Parte>

      <Sfx en={k.todos} s="ding" vol={0.35} />
      <Sfx en={k.todos + 4} s="ding" vol={0.25} />
      <Sfx en={k.todos + 8} s="ding" vol={0.2} />
      <Sfx en={k.lacteos} s="pop" vol={0.3} />
    </AbsoluteFill>
  );
};
