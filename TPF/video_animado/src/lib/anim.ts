import { Easing, interpolate, spring } from "remotion";
import { FPS } from "./tema";

// Lenguaje de movimiento ("Playful", motion-art-direction): entradas con un poco de rebote, salidas que aceleran,
// desplazamientos simétricos. Dos curvas y un resorte, usados en todo el video.
export const ENTRA = Easing.bezier(0.16, 1, 0.3, 1);
export const SALE = Easing.bezier(0.7, 0, 0.84, 0);
export const MUEVE = Easing.bezier(0.65, 0, 0.35, 1);
export const REBOTA = Easing.bezier(0.34, 1.56, 0.64, 1);

/** Progreso 0..1 entre `desde` y `desde + dur` cuadros, con la curva dada. */
export const ap = (f: number, desde: number, dur = 12, curva = ENTRA) =>
  interpolate(f, [desde, desde + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: curva,
  });

/** Resorte con rebote (aparece "con peso"); 0 antes de `desde`. */
export const resorte = (f: number, desde: number, damping = 11, stiffness = 170, mass = 0.8) =>
  f < desde ? 0 : spring({ frame: f - desde, fps: FPS, config: { damping, stiffness, mass } });

export const mezclar = (a: number, b: number, t: number) => a + (b - a) * t;

/** Un valor que oscila suave (movimiento ambiente): nada queda quieto. */
export const respira = (f: number, periodo = 2.4, amp = 1, fase = 0) =>
  Math.sin(((f / FPS) * 2 * Math.PI) / periodo + fase) * amp;

/** Sacudida corta (error, golpe) que se apaga en `dur` cuadros. */
export const sacudir = (f: number, desde: number, dur = 14, amp = 14) => {
  if (f < desde || f > desde + dur) return 0;
  const t = (f - desde) / dur;
  return Math.sin(t * Math.PI * 6) * amp * (1 - t);
};

/** Contador que sube de `a` a `b` con desaceleración. */
export const contar = (f: number, desde: number, dur: number, a: number, b: number) =>
  a + (b - a) * ap(f, desde, dur, Easing.bezier(0.22, 1, 0.36, 1));

export const miles = (n: number) => Math.round(n).toLocaleString("es-AR");
