import React from "react";
import { AbsoluteFill } from "remotion";
import { C, SOMBRA, TITULO } from "../lib/tema";
import { ap, MUEVE, respira } from "../lib/anim";
import { cuadro, T } from "../lib/tiempo";
import { AparecG, Fondo, Lienzo, Pop, Sfx, TituloAnimado, useF } from "../comp/UI";
import { poseEn, Stickman } from "../comp/Stickman";
import { Avion, Changuito } from "../comp/Iconos";

/** La moraleja y la placa final, con Stigler y Sofi juntos (la rima con la primera escena). */
export const E8Cierre: React.FC = () => {
  const f = useF();
  const k = {
    moraleja: cuadro("b26"),
    donde: cuadro("b26", "dónde"),
    importa: cuadro("b26", "importa"),
    que: cuadro("b26", "qué"),
    pagina: cuadro("b27", "llama"),
    gratis: cuadro("b27", "gratis"),
    probala: cuadro("b27", "probala"),
    pasasela: cuadro("b27", "pasásela"),
    caro: cuadro("b27", "caro"),
  };
  const finMoraleja = k.pagina - 4;
  const placa = finMoraleja + 10; // la placa entra recién cuando la moraleja terminó de irse
  const avion = ap(f, k.pasasela, 30, MUEVE);

  return (
    <AbsoluteFill>
      <Fondo />
      {/* La moraleja */}
      <TituloAnimado texto="Dónde comprás" en={k.donde} tam={118} resaltar={["dónde", "comprás"]} style={{ top: 390, left: 40, right: 40 }} sale={finMoraleja} paso={4} />
      <TituloAnimado texto="importa tanto como" en={k.importa} tam={64} color={C.tintaSuave} style={{ top: 545, left: 40, right: 40 }} sale={finMoraleja} paso={3} />
      <TituloAnimado
        texto="qué comprás"
        en={k.que}
        tam={118}
        resaltar={["qué", "comprás"]}
        colorResalte={C.verdeClaro}
        style={{ top: 630, left: 40, right: 40 }}
        sale={finMoraleja}
        paso={4}
      />
      {/* La placa final */}
      <Pop en={placa} style={{ top: 360, left: 60, right: 60, display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }} sonido="brillo" vol={0.35}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <svg width={120} height={100} viewBox="-90 -80 180 130">
            <Changuito color={C.verde} />
          </svg>
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 92, color: C.tinta, lineHeight: 1 }}>{T.nombre}</div>
        </div>
        <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 52, color: C.tinta, opacity: ap(f, k.gratis, 8) }}>
          probala <span style={{ background: C.amarillo, borderRadius: 16, padding: "0 12px" }}>gratis</span>
        </div>
        <div
          style={{
            fontFamily: TITULO,
            fontWeight: 600,
            fontSize: 40,
            color: C.papel,
            background: C.tinta,
            borderRadius: 40,
            padding: "16px 34px",
            boxShadow: SOMBRA,
            transform: `scale(${1 + (f >= k.probala ? respira(f - k.probala, 0.8, 0.03) : 0)})`,
          }}
        >
          {T.url}
        </div>
      </Pop>
      <Pop en={k.pasasela + 4} style={{ top: 690, left: 80, right: 80, display: "flex", justifyContent: "center" }} desde="abajo">
        <div
          style={{
            fontFamily: TITULO,
            fontWeight: 600,
            fontSize: 46,
            textAlign: "center",
            color: C.tinta,
            background: C.papel,
            border: `5px solid ${C.tinta}`,
            borderRadius: 30,
            padding: "18px 30px",
            boxShadow: SOMBRA,
            lineHeight: 1.15,
          }}
        >
          Pasásela a quien dice que
          <br />
          <b style={{ color: C.rojo }}>comer sano es caro</b>
        </div>
      </Pop>

      <Lienzo>
        <AparecG en={k.moraleja}>
          <Stickman
            x={250}
            y={1235}
            escala={1.25}
            f={f}
            pose={poseEn(f, [[0, "parada"], [k.donde, "señala"], [k.pagina, "parada"], [k.probala, "saluda"]])}
            cara="feliz"
            extras={["anteojos", "sombrero", "moño"]}
            semilla={1}
          />
          <Stickman
            x={830}
            y={1235}
            escala={1.25}
            f={f}
            mira="izq"
            pose={poseEn(f, [[0, "parada"], [k.que, "señala"], [k.pagina, "parada"], [k.probala + 4, "saluda"], [k.caro, "festeja"]])}
            cara={f >= k.caro ? "contenta" : "feliz"}
            color={C.violeta}
            extras={["cola"]}
            semilla={3}
          />
        </AparecG>
        {f >= k.pasasela && avion < 1 && (
          <g transform={`translate(${-120 + avion * 1340},${1020 - Math.sin(avion * Math.PI) * 260}) rotate(${-15 + avion * 20}) scale(0.9)`}>
            <Avion />
          </g>
        )}
      </Lienzo>

      <Sfx en={k.donde} s="golpe" vol={0.35} />
      <Sfx en={k.que} s="golpe" vol={0.35} />
      <Sfx en={k.pasasela} s="whoosh" vol={0.4} />
      <Sfx en={k.caro} s="ding" vol={0.4} />
    </AbsoluteFill>
  );
};
