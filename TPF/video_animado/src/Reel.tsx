import React from "react";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Audio } from "@remotion/media";
import { C } from "./lib/tema";
import { LIMITES } from "./lib/tiempo";
import { EscenaCtx } from "./comp/UI";
import { Cabecera, Subtitulos, Transiciones } from "./comp/Capas";
import { E1Pregunta } from "./escenas/E1Pregunta";
import { E2Datos } from "./escenas/E2Datos";
import { E3Pagina } from "./escenas/E3Pagina";
import { E4Modelo } from "./escenas/E4Modelo";
import { E5Ejemplo } from "./escenas/E5Ejemplo";
import { E6Casos } from "./escenas/E6Casos";
import { E7Bolsillo } from "./escenas/E7Bolsillo";
import { E8Cierre } from "./escenas/E8Cierre";

const ESCENAS: Record<string, React.FC> = {
  e1: E1Pregunta,
  e2: E2Datos,
  e3: E3Pagina,
  e4: E4Modelo,
  e5: E5Ejemplo,
  e6: E6Casos,
  e7: E7Bolsillo,
  e8: E8Cierre,
};

/** Las ocho escenas seguidas, sincronizadas con la voz (las usan las dos versiones). */
export const Escenas: React.FC = () => (
  <>
    {LIMITES.map((e) => {
      const Escena = ESCENAS[e.id];
      return (
        <Sequence key={e.id} name={`${e.id} · ${e.titulo}`} from={e.desde} durationInFrames={e.hasta - e.desde} premountFor={30}>
          <EscenaCtx.Provider value={{ desde: e.desde, hasta: e.hasta }}>
            <Escena />
          </EscenaCtx.Provider>
        </Sequence>
      );
    })}
  </>
);

/** El reel vertical: las escenas, arriba la cabecera, abajo los subtítulos. */
export const Reel: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: C.fondo }}>
    <Escenas />
    <Cabecera />
    <Transiciones />
    <Subtitulos />
    <Audio src={staticFile("audio/voz.wav")} name="Voz" />
    <Audio src={staticFile("audio/musica.wav")} name="Música" volume={0.55} />
  </AbsoluteFill>
);
