import React, { createContext, useContext } from "react";
import { AbsoluteFill, Sequence, staticFile, useCurrentFrame } from "remotion";
import { Audio } from "@remotion/media";
import { C, H, SOMBRA, TITULO, W } from "../lib/tema";
import { ap, ENTRA, MUEVE, resorte, respira, SALE } from "../lib/anim";

/** Cada escena vive en una <Sequence>: el contexto guarda dónde empieza, para trabajar en cuadros absolutos. */
export const EscenaCtx = createContext({ desde: 0, hasta: 0 });

/** Cuadro absoluto del video (los cuadros de `cuadro("b06", ...)` son absolutos). */
export const useF = () => {
  const f = useCurrentFrame();
  const { desde } = useContext(EscenaCtx);
  return f + desde;
};

export type NombreSfx =
  | "pop"
  | "whoosh"
  | "ding"
  | "caja"
  | "error"
  | "tic"
  | "boing"
  | "brillo"
  | "golpe"
  | "zoom"
  | "swish"
  | "click"
  | "teclado"
  | "tiza"
  | "pasos";

/** Silencia los efectos de lo que envuelve (una capa dibujada dos veces suena una sola). */
export const MudoCtx = createContext(false);

/** Un efecto de sonido en el cuadro absoluto `en` (debajo de la voz: nunca más fuerte que ella). */
export const Sfx: React.FC<{ en: number; s: NombreSfx; vol?: number }> = ({ en, s, vol = 0.5 }) => {
  const { desde } = useContext(EscenaCtx);
  const mudo = useContext(MudoCtx);
  if (mudo) return null;
  return (
    <Sequence from={en - desde} durationInFrames={45} layout="none" name={`sfx ${s}`}>
      <Audio src={staticFile(`audio/sfx/${s}.wav`)} volume={vol} />
    </Sequence>
  );
};

/** Tics mientras un contador sube: uno cada `cada` cuadros entre `desde` y `hasta`. */
export const Tics: React.FC<{ desde: number; hasta: number; cada?: number; vol?: number }> = ({ desde, hasta, cada = 4, vol = 0.22 }) => (
  <>
    {Array.from({ length: Math.max(0, Math.floor((hasta - desde) / cada)) }, (_, i) => (
      <Sfx key={i} en={desde + i * cada} s="tic" vol={vol * (1 - (0.5 * i * cada) / Math.max(1, hasta - desde))} />
    ))}
  </>
);

/** Fondo crema con una grilla de puntos que se desplaza despacio (movimiento ambiente). */
export const Fondo: React.FC<{ color?: string; puntos?: string }> = ({ color = C.fondo, puntos = "rgba(35,33,58,0.07)" }) => {
  const f = useCurrentFrame();
  const d = (f * 0.4) % 48;
  return (
    <AbsoluteFill style={{ backgroundColor: color }}>
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(${puntos} 3px, transparent 3.5px)`,
          backgroundSize: "48px 48px",
          backgroundPosition: `${d}px ${d * 0.5}px`,
        }}
      />
    </AbsoluteFill>
  );
};

/** Lienzo SVG del tamaño del cuadro: las escenas dibujan en coordenadas de 1080x1920. */
export const Lienzo: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <AbsoluteFill style={style}>
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ overflow: "visible" }}>
      {children}
    </svg>
  </AbsoluteFill>
);

/** Sonido de entrada (y de salida, si hay `sale`) de un elemento: nada aparece ni se va en silencio. */
const SonidoES: React.FC<{ en: number; sale?: number; sonido?: NombreSfx | null; vol?: number }> = ({
  en,
  sale,
  sonido = "pop",
  vol = 0.16,
}) => (
  <>
    {sonido && <Sfx en={en} s={sonido} vol={vol} />}
    {sale !== undefined && sonido && <Sfx en={sale} s="swish" vol={vol * 0.8} />}
  </>
);

/** Un grupo SVG que aparece con resorte en `en` (escala desde 0 con rebote) y, si se pide, se va en `sale`. */
export const PopG: React.FC<{
  en: number;
  x?: number;
  y?: number;
  escala?: number;
  sale?: number;
  rota?: number;
  flota?: number;
  sonido?: NombreSfx | null;
  vol?: number;
  children: React.ReactNode;
}> = ({ en, x = 0, y = 0, escala = 1, sale, rota = 0, flota = 0, sonido, vol, children }) => {
  const f = useF();
  const audio = <SonidoES en={en} sale={sale} sonido={sonido} vol={vol} />;
  if (f < en) return audio;
  const s = resorte(f, en);
  const fuera = sale !== undefined ? ap(f, sale, 8) : 0;
  if (fuera >= 1) return audio;
  const dy = flota ? respira(f, 2.6, flota, x * 0.01) : 0;
  return (
    <>
      {audio}
      <g
        transform={`translate(${x},${y + dy - fuera * 30}) rotate(${rota * (1 - s)}) scale(${escala * s * (1 - fuera * 0.3)})`}
        opacity={Math.min(1, s * 2) * (1 - fuera)}
      >
        {children}
      </g>
    </>
  );
};

/** Para personajes: aparecen con un fundido y subiendo un poco, sin escalar (no "crecen" desde una esquina). */
export const AparecG: React.FC<{ en: number; sale?: number; children: React.ReactNode }> = ({ en, sale, children }) => {
  const f = useF();
  if (f < en) return null;
  const t = ap(f, en, 12, ENTRA);
  const fuera = sale !== undefined ? ap(f, sale, 8) : 0;
  if (fuera >= 1) return null;
  return (
    <g transform={`translate(0,${(1 - t) * 40 - fuera * 30})`} opacity={t * (1 - fuera)}>
      {children}
    </g>
  );
};

/** Lo mismo para HTML: entra subiendo y creciendo con rebote. */
export const Pop: React.FC<{
  en: number;
  sale?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
  desde?: "abajo" | "escala";
  sonido?: NombreSfx | null;
  vol?: number;
}> = ({ en, sale, style, children, desde = "escala", sonido, vol }) => {
  const f = useF();
  const audio = <SonidoES en={en} sale={sale} sonido={sonido} vol={vol} />;
  if (f < en) return audio;
  const s = resorte(f, en);
  const fuera = sale !== undefined ? ap(f, sale, 8) : 0;
  if (fuera >= 1) return audio;
  const t =
    desde === "abajo"
      ? `translateY(${(1 - s) * 60 - fuera * 40}px)`
      : `scale(${(0.4 + 0.6 * s) * (1 - fuera * 0.2)})`;
  return (
    <>
      {audio}
      <div style={{ position: "absolute", ...style, transform: `${style?.transform ?? ""} ${t}`, opacity: Math.min(1, s * 1.6) * (1 - fuera) }}>
        {children}
      </div>
    </>
  );
};

/**
 * Una parte de la escena: se ve entre `desde` y `hasta`, y en `hasta` todo el grupo sube y se va (8 cuadros).
 * Regla del video: la parte siguiente entra recién cuando esta terminó de irse, nunca encima.
 */
export const Parte: React.FC<{ desde: number; hasta?: number; children: React.ReactNode; mudo?: boolean }> = ({
  desde,
  hasta,
  children,
  mudo,
}) => {
  const f = useF();
  const fuera = hasta !== undefined ? ap(f, hasta, 8, SALE) : 0;
  const audio = hasta !== undefined && !mudo ? <Sfx en={hasta} s="swish" vol={0.22} /> : null;
  if (f < desde || fuera >= 1) return audio;
  return (
    <>
      {audio}
      <AbsoluteFill style={{ transform: `translateY(${-fuera * 70}px)`, opacity: 1 - fuera }}>{children}</AbsoluteFill>
    </>
  );
};

/**
 * Cámara: acerca o aleja todo lo que envuelve. Cada clave [cuadro, escala, x, y] lleva la cámara a mirar (x, y) con esa
 * escala, en 16 cuadros; acercarse suena a "zoom" y alejarse a "swish".
 */
export const Camara: React.FC<{ claves: [number, number, number, number][]; children: React.ReactNode }> = ({ claves, children }) => {
  const f = useF();
  let [s, x, y] = [claves[0][1], claves[0][2], claves[0][3]];
  for (let i = 1; i < claves.length; i++) {
    const [c, s2, x2, y2] = claves[i];
    if (f < c) break;
    const t = ap(f, c, 16, MUEVE);
    s = s + (s2 - s) * t;
    x = x + (x2 - x) * t;
    y = y + (y2 - y) * t;
  }
  // Se acerca al punto (x, y) llevándolo hacia el centro del escenario a medida que crece.
  const k = (s - 1) / Math.max(1e-6, s);
  const dx = (540 - x) * k;
  const dy = (800 - y) * k;
  return (
    <>
      {claves.slice(1).map(([c, s2], i) => (
        <Sfx key={c} en={c} s={s2 > claves[i][1] ? "zoom" : "swish"} vol={0.38} />
      ))}
      <AbsoluteFill style={{ transformOrigin: `${x}px ${y}px`, transform: `translate(${dx}px,${dy}px) scale(${s})` }}>
        {children}
      </AbsoluteFill>
    </>
  );
};

/** Una píldora de texto (etiqueta, dato) con ícono opcional a la izquierda. */
export const Chip: React.FC<{
  children: React.ReactNode;
  color?: string;
  fondo?: string;
  tam?: number;
  icono?: React.ReactNode;
  borde?: boolean;
}> = ({ children, color = C.tinta, fondo = C.papel, tam = 44, icono, borde = true }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: tam * 0.35,
      padding: `${tam * 0.28}px ${tam * 0.6}px`,
      borderRadius: tam,
      background: fondo,
      color,
      border: borde ? `5px solid ${C.tinta}` : "none",
      boxShadow: SOMBRA,
      fontFamily: TITULO,
      fontWeight: 600,
      fontSize: tam,
      lineHeight: 1.05,
      whiteSpace: "nowrap",
    }}
  >
    {icono && (
      <svg width={tam * 1.2} height={tam * 1.2} viewBox="-70 -70 140 140" style={{ overflow: "visible" }}>
        {icono}
      </svg>
    )}
    {children}
  </div>
);

/** Título que entra palabra por palabra (cada una sube con rebote, separadas `paso` cuadros). */
export const TituloAnimado: React.FC<{
  texto: string;
  en: number;
  tam?: number;
  color?: string;
  paso?: number;
  resaltar?: string[];
  colorResalte?: string;
  style?: React.CSSProperties;
  sale?: number;
}> = ({ texto, en, tam = 96, color = C.tinta, paso = 3, resaltar = [], colorResalte = C.amarillo, style, sale }) => {
  const f = useF();
  const fuera = sale !== undefined ? ap(f, sale, 8) : 0;
  const audio = (
    <>
      <Sfx en={en} s="pop" vol={0.2} />
      {sale !== undefined && <Sfx en={sale} s="swish" vol={0.15} />}
    </>
  );
  if (f < en || fuera >= 1) return audio;
  const palabras = texto.split(" ");
  return (
    <>
    {audio}
    <div
      style={{
        position: "absolute",
        fontFamily: TITULO,
        fontWeight: 700,
        fontSize: tam,
        lineHeight: 1.02,
        color,
        textAlign: "center",
        letterSpacing: -1,
        opacity: 1 - fuera,
        ...style,
      }}
    >
      {palabras.map((p, i) => {
        const s = resorte(f, en + i * paso, 12, 180);
        const r = resaltar.some((x) => p.toLowerCase().startsWith(x.toLowerCase()));
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translateY(${(1 - s) * 50}px) scale(${0.6 + 0.4 * s})`,
              opacity: Math.min(1, s * 2),
              margin: `0 ${tam * 0.12}px`,
              padding: r ? `0 ${tam * 0.12}px` : 0,
              background: r ? colorResalte : "transparent",
              borderRadius: tam * 0.18,
            }}
          >
            {p}
          </span>
        );
      })}
    </div>
    </>
  );
};

/** Un número grande que cuenta (el texto lo arma quien llama). */
export const Numero: React.FC<{ texto: string; tam?: number; color?: string; style?: React.CSSProperties }> = ({
  texto,
  tam = 150,
  color = C.tinta,
  style,
}) => (
  <div
    style={{
      position: "absolute",
      fontFamily: TITULO,
      fontWeight: 700,
      fontSize: tam,
      lineHeight: 1,
      color,
      letterSpacing: -2,
      fontVariantNumeric: "tabular-nums",
      ...style,
    }}
  >
    {texto}
  </div>
);

/** Sello que cae desde grande (con golpe). */
export const Sello: React.FC<{ en: number; children: React.ReactNode; style?: React.CSSProperties; rota?: number; sale?: number }> = ({
  en,
  children,
  style,
  rota = -8,
  sale,
}) => {
  const f = useF();
  const audio = (
    <>
      <Sfx en={en + 5} s="golpe" vol={0.4} />
      {sale !== undefined && <Sfx en={sale} s="swish" vol={0.15} />}
    </>
  );
  if (f < en) return audio;
  const t = ap(f, en, 7, ENTRA);
  const fuera = sale !== undefined ? ap(f, sale, 8) : 0;
  if (fuera >= 1) return audio;
  const s = (2.2 - 1.2 * t) * (1 - 0.3 * fuera);
  return (
    <>
    {audio}
    <div style={{ position: "absolute", ...style, transform: `${style?.transform ?? ""} rotate(${rota}deg) scale(${s})`, opacity: Math.min(1, t * 2) * (1 - fuera) }}>
      {children}
    </div>
    </>
  );
};

/** Una tarjeta blanca con borde de tinta (para ventanas, tickets, paneles). */
export const Tarjeta: React.FC<{ style?: React.CSSProperties; children?: React.ReactNode }> = ({ style, children }) => (
  <div
    style={{
      position: "absolute",
      background: C.papel,
      border: `6px solid ${C.tinta}`,
      borderRadius: 32,
      boxShadow: SOMBRA,
      overflow: "hidden",
      ...style,
    }}
  >
    {children}
  </div>
);
