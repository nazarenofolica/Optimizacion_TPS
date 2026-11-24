import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { C, FPS, SOMBRA, TEXTO, TITULO, W } from "../lib/tema";
import { ap, ENTRA, resorte, SALE } from "../lib/anim";
import { LIMITES, T } from "../lib/tiempo";

const esCifra = (s: string) => /[0-9$%]/.test(s);

/** Subtítulos de reel: golpes de 1 a 3 palabras; la palabra que se dice se resalta (amarillo; las cifras, verde). */
export const Subtitulos: React.FC<{ top?: number; alto?: number; tam?: number; ancho?: number }> = ({
  top = 1262,
  alto = 200,
  tam = 76,
  ancho = W,
}) => {
  const f = useCurrentFrame();
  const t = f / FPS;
  const s = T.subtitulos.find((x) => t >= x.t0 && t < x.t1);
  if (!s) return null;
  const entra = resorte(f, Math.round(s.t0 * FPS), 13, 260);
  return (
    <AbsoluteFill style={{ top, height: alto, alignItems: "center", justifyContent: "center", padding: "0 90px" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "6px 20px",
          transform: `scale(${0.82 + 0.18 * entra}) translateY(${(1 - entra) * 18}px)`,
          maxWidth: ancho - 180,
        }}
      >
        {s.palabras.map((p, i) => {
          const sig = s.palabras[i + 1]?.t0 ?? s.t1;
          const activa = t >= p.t0 - 0.04 && t < sig - 0.02;
          const dicha = t >= p.t0 - 0.04;
          const cifra = esCifra(p.texto);
          const golpe = activa ? resorte(f, Math.round((p.t0 - 0.04) * FPS), 10, 300) : 1;
          return (
            <span
              key={i}
              style={{
                fontFamily: TEXTO,
                fontWeight: 900,
                fontSize: tam,
                lineHeight: 1.08,
                textTransform: "uppercase",
                letterSpacing: -1.5,
                color: activa && cifra ? C.blanco : C.tinta,
                padding: "2px 16px 6px",
                borderRadius: 20,
                background: activa ? (cifra ? C.verde : C.amarillo) : "transparent",
                boxShadow: activa ? `0 8px 0 ${C.tinta}` : "none",
                border: activa ? `5px solid ${C.tinta}` : "5px solid transparent",
                opacity: dicha ? 1 : 0.5,
                transform: `scale(${activa ? 0.9 + 0.16 * golpe : 1}) rotate(${activa ? -2 : 0}deg)`,
              }}
            >
              {p.texto}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** Arriba: el capítulo (número y nombre) y el progreso en siete segmentos. */
export const Cabecera: React.FC = () => {
  const f = useCurrentFrame();
  const i = Math.max(0, LIMITES.findIndex((e) => f >= e.desde && f < e.hasta));
  const e = LIMITES[i];
  const entra = resorte(f, e.desde + (i === 0 ? 4 : 8), 12, 200);
  return (
    <div style={{ position: "absolute", top: 238, height: 90, left: 60, right: 60 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "10px 26px 10px 12px",
            background: C.tinta,
            color: C.papel,
            borderRadius: 40,
            fontFamily: TITULO,
            fontWeight: 600,
            fontSize: 36,
            transform: `translateX(${(1 - entra) * -60}px)`,
            opacity: Math.min(1, entra * 1.5),
            boxShadow: SOMBRA,
          }}
        >
          <span
            style={{
              background: C.amarillo,
              color: C.tinta,
              borderRadius: 30,
              width: 52,
              height: 52,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
            }}
          >
            {i + 1}
          </span>
          {e.titulo}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {LIMITES.map((x, k) => {
            const lleno = k < i ? 1 : k > i ? 0 : ap(f, x.desde, x.hasta - x.desde, (v) => v);
            return (
              <div key={k} style={{ width: 40, height: 14, borderRadius: 7, background: "rgba(35,33,58,0.15)", overflow: "hidden" }}>
                <div style={{ width: `${lleno * 100}%`, height: "100%", background: C.tinta, borderRadius: 7 }} />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const COLORES = [C.amarillo, C.verde, C.azul, C.violeta, C.rojo, C.naranja];

/** Entre escenas: dos paneles en diagonal barren el cuadro y se van (el corte queda tapado). */
export const Transiciones: React.FC<{ ancho?: number }> = ({ ancho = W }) => {
  const f = useCurrentFrame();
  return (
    <>
      {LIMITES.slice(1).map((e, k) => {
        const b = e.desde;
        if (f < b - 12 || f > b + 12) return null;
        return [0, 1].map((capa) => {
          const d = capa * 2;
          const entra = ap(f, b - 11 + d, 10, SALE);
          const sale = ap(f, b + 1 + d, 10, ENTRA);
          const viaje = ancho + 620;
          const x = (1 - entra) * viaje - sale * viaje;
          return (
            <AbsoluteFill
              key={`${k}-${capa}`}
              style={{
                left: -400,
                right: -400,
                background: capa === 0 ? COLORES[k % COLORES.length] : C.tinta,
                transform: `translateX(${x}px) skewX(-14deg)`,
                opacity: capa === 1 ? 0.95 : 1,
                zIndex: 10 + capa,
              }}
            />
          );
        });
      })}
    </>
  );
};
