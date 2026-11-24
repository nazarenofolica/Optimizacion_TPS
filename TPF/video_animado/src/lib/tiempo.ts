import tiempos from "../datos/tiempos.json";
import { FPS } from "./tema";

export type Palabra = { texto: string; beat: string; t0: number; t1: number };
export type Subtitulo = {
  t0: number;
  t1: number;
  beat: string;
  palabras: { texto: string; t0: number; t1: number }[];
};
export type EscenaT = { id: string; titulo: string; t0: number; t1: number };

export const T = tiempos as unknown as {
  voz: string;
  duracion: number;
  url: string;
  nombre: string;
  escenas: EscenaT[];
  beats: Record<string, { escena: string; t0: number; t1: number }>;
  palabras: Palabra[];
  subtitulos: Subtitulo[];
};

export const COLA = 2.2; // segundos de cierre después de la última palabra
export const TOTAL = Math.ceil((T.duracion + COLA) * FPS);

export const fr = (s: number) => Math.round(s * FPS);

const normal = (s: string) =>
  s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9ñ$% ]/g, "");

/** Cuadro (absoluto) en que empieza el beat, o la palabra del beat que empieza con `palabra`. */
export const cuadro = (beat: string, palabra?: string, n = 1): number => {
  const b = T.beats[beat];
  if (!b) throw new Error(`No existe el beat ${beat}`);
  if (!palabra) return fr(b.t0);
  const q = normal(palabra);
  let vistas = 0;
  for (const p of T.palabras) {
    if (p.beat === beat && normal(p.texto).startsWith(q)) {
      vistas++;
      if (vistas === n) return fr(p.t0);
    }
  }
  throw new Error(`No encuentro "${palabra}" en ${beat}`);
};

export const finBeat = (beat: string): number => fr(T.beats[beat].t1);

/** Límites de cada escena en cuadros: cada una empieza en la mitad del silencio que la separa de la anterior. */
export const LIMITES = T.escenas.map((e, i) => {
  const ini = i === 0 ? 0 : fr((T.escenas[i - 1].t1 + e.t0) / 2);
  const fin = i === T.escenas.length - 1 ? TOTAL : fr((e.t1 + T.escenas[i + 1].t0) / 2);
  return { ...e, desde: ini, hasta: fin };
});

export const escena = (id: string) => {
  const e = LIMITES.find((x) => x.id === id);
  if (!e) throw new Error(id);
  return e;
};
