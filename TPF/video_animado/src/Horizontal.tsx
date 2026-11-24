import React from "react";
import { AbsoluteFill, staticFile, useCurrentFrame } from "remotion";
import { Audio } from "@remotion/media";
import { C, SOMBRA, TITULO } from "./lib/tema";
import { ap, ENTRA, resorte } from "./lib/anim";
import { LIMITES, T } from "./lib/tiempo";
import { Fondo } from "./comp/UI";
import { Subtitulos, Transiciones } from "./comp/Capas";
import { Changuito, Tilde } from "./comp/Iconos";
import { Escenas } from "./Reel";

/*
 * Versión horizontal (1920x1080, para LinkedIn o una presentación): no es el reel con franjas a los costados. Las
 * mismas escenas se recortan a su zona de animación (y 330 a 1250 del cuadro vertical) y van en un escenario a la
 * derecha; a la izquierda, un panel con la marca, el capítulo actual y el índice; abajo, los subtítulos a lo ancho.
 */
const ANCHO = 1920;
const ALTO = 1080;
const Y0 = 330; // zona de animación del cuadro vertical
const Y1 = 1285;
const ESC_ALTO = 870;
const S = ESC_ALTO / (Y1 - Y0);
const ESC_ANCHO = Math.round(1080 * S);
const ESC_X = ANCHO - ESC_ANCHO - 56;
const ESC_Y = 40;

const Panel: React.FC = () => {
  const f = useCurrentFrame();
  const i = Math.max(0, LIMITES.findIndex((e) => f >= e.desde && f < e.hasta));
  const e = LIMITES[i];
  const entra = resorte(f, e.desde + (i === 0 ? 2 : 8), 12, 200);
  return (
    <div style={{ position: "absolute", left: 70, top: 56, width: ESC_X - 130, height: ESC_ALTO }}>
      {/* marca */}
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <svg width={86} height={70} viewBox="-90 -80 180 130">
          <Changuito color={C.verde} />
        </svg>
        <div>
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 46, color: C.tinta, lineHeight: 1 }}>{T.nombre}</div>
          <div style={{ fontFamily: TITULO, fontWeight: 500, fontSize: 26, color: C.tintaSuave }}>{T.url}</div>
        </div>
      </div>
      {/* capítulo actual */}
      <div
        style={{
          marginTop: 70,
          display: "flex",
          alignItems: "center",
          gap: 24,
          transform: `translateX(${(1 - entra) * -50}px)`,
          opacity: Math.min(1, entra * 1.4),
        }}
      >
        <div
          style={{
            width: 104,
            height: 104,
            borderRadius: 52,
            background: C.amarillo,
            border: `6px solid ${C.tinta}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: TITULO,
            fontWeight: 700,
            fontSize: 60,
            color: C.tinta,
            flexShrink: 0,
          }}
        >
          {i + 1}
        </div>
        <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 76, color: C.tinta, lineHeight: 1 }}>{e.titulo}</div>
      </div>
      {/* índice */}
      <div style={{ marginTop: 54, display: "flex", flexDirection: "column", gap: 10 }}>
        {LIMITES.map((x, k) => {
          const hecho = k < i;
          const actual = k === i;
          const lleno = actual ? ap(f, x.desde, x.hasta - x.desde, (v) => v) : hecho ? 1 : 0;
          return (
            <div key={x.id} style={{ display: "flex", alignItems: "center", gap: 16, opacity: actual ? 1 : hecho ? 0.85 : 0.4 }}>
              <div style={{ width: 34, height: 34, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {hecho ? (
                  <svg width={34} height={34} viewBox="-45 -45 90 90">
                    <Tilde r={40} />
                  </svg>
                ) : (
                  <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 28, color: C.tinta }}>{k + 1}</div>
                )}
              </div>
              <div
                style={{
                  position: "relative",
                  fontFamily: TITULO,
                  fontWeight: actual ? 700 : 600,
                  fontSize: 34,
                  color: C.tinta,
                  padding: "2px 16px",
                  borderRadius: 14,
                  background: actual ? C.amarilloClaro : "transparent",
                  overflow: "hidden",
                }}
              >
                {actual && (
                  <div style={{ position: "absolute", left: 0, bottom: 0, height: 5, width: `${lleno * 100}%`, background: C.tinta }} />
                )}
                {x.titulo}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** El escenario: las escenas verticales, recortadas a su zona de animación. */
const Escenario: React.FC = () => {
  const f = useCurrentFrame();
  const entra = ap(f, 0, 14, ENTRA);
  return (
    <div
      style={{
        position: "absolute",
        left: ESC_X,
        top: ESC_Y,
        width: ESC_ANCHO,
        height: ESC_ALTO,
        overflow: "hidden",
        borderRadius: 36,
        border: `5px solid ${C.tinta}`,
        boxShadow: SOMBRA,
        background: C.fondo,
        opacity: Math.max(0.999, entra),
      }}
    >
      <div style={{ position: "absolute", left: 0, top: -Y0 * S, width: 1080, height: 1920, transform: `scale(${S})`, transformOrigin: "0 0" }}>
        <Escenas />
      </div>
    </div>
  );
};

export const ReelHorizontal: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: C.fondo }}>
    <Fondo />
    <Panel />
    <Escenario />
    <Transiciones ancho={ANCHO} />
    <Subtitulos top={ESC_Y + ESC_ALTO + 8} alto={ALTO - ESC_Y - ESC_ALTO - 8} tam={58} ancho={ANCHO} />
    <Audio src={staticFile("audio/voz.wav")} name="Voz" />
    <Audio src={staticFile("audio/musica.wav")} name="Música" volume={0.55} />
  </AbsoluteFill>
);

export const HORIZONTAL = { ancho: ANCHO, alto: ALTO };
