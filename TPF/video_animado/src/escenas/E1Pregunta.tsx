import React from "react";
import { AbsoluteFill } from "remotion";
import { C, TITULO } from "../lib/tema";
import { ap, contar, ENTRA, MUEVE, SALE, sacudir } from "../lib/anim";
import { cuadro } from "../lib/tiempo";
import { Fondo, Lienzo, MudoCtx, Pop, PopG, Sello, Sfx, TituloAnimado, useF, Chip } from "../comp/UI";
import { caminar, poseEn, recorrido, Stickman, POSES, mezclarPose } from "../comp/Stickman";
import { Calendario, Changuito, Espinaca, Etiqueta, Harina, Plato, Repollo, Tienda } from "../comp/Iconos";

/** 1945: Stigler, la dieta de harina, repollo y espinaca, y el salto al súper de hoy. */
const Mundo: React.FC<{ color: boolean }> = ({ color }) => {
  const f = useF();
  const k = {
    pizarra: cuadro("b01", "calculó"),
    nombre: cuadro("b01", "economista"),
    resultado: cuadro("b02", "resultado"),
    harina: cuadro("b02", "harina"),
    repollo: cuadro("b02", "repollo"),
    espinaca: cuadro("b02", "espinaca"),
    anio: cuadro("b02", "todo"),
    barata: cuadro("b03", "barata"),
    nadie: cuadro("b03", "nadie"),
    comer: cuadro("b03", "comer"),
    nacio: cuadro("b04", "así"),
    problema: cuadro("b04", "problema"),
    nosotros: cuadro("b04", "nosotros"),
    super: cuadro("b04", "súper"),
    hoy: cuadro("b04", "hoy"),
  };
  const asco = f >= k.nadie;
  const poseStigler = poseEn(f, [
    [0, "parada"],
    [k.pizarra - 6, "señala"],
    [k.nombre + 10, "parada"],
    [k.resultado, "señala"],
    [k.harina + 4, "parada"],
    [k.barata, "manosCadera"],
    [k.nadie - 2, "come"],
    [k.comer, "asco"],
    [k.nosotros + 6, "parada"],
    [k.hoy, "saluda"],
  ]);
  const caraStigler = f >= k.nosotros + 6 ? "sorpresa" : asco ? "asco" : f >= k.barata ? "contenta" : "feliz";

  // Pizarrón con la "fórmula" que se escribe sola
  const escribe = ap(f, k.pizarra, 26, MUEVE);
  const pizarraFuera = ap(f, k.resultado, 10);
  // Sofi entra con el changuito
  const entraSofi = k.nosotros + 6;
  const xSofi = recorrido(f, entraSofi, 34, 1260, 690);
  const caminando = f >= entraSofi && f < entraSofi + 34;
  const poseSofi = caminando
    ? mezclarPose(caminar((f - entraSofi) / 30, 2.2), POSES.empuja, 0.5)
    : poseEn(f, [[0, "empuja"], [entraSofi + 34, "parada"], [k.hoy + 2, "saluda"]]);

  const dias = Math.round(contar(f, k.anio, 30, 1, 365));
  const aparta = ap(f, k.comer + 6, 14, SALE);
  const tiembla = sacudir(f, k.comer, 16, 10);

  return (
    <AbsoluteFill>
      <Fondo color={color ? C.fondo : C.sepia} puntos={color ? undefined : "rgba(91,70,48,0.12)"} />
      {/* Titular del gancho: desde el primer cuadro */}
      <TituloAnimado
        texto="La dieta más barata del mundo"
        en={1}
        paso={2}
        tam={104}
        resaltar={["barata"]}
        style={{ top: 360, left: 70, right: 70 }}
        sale={k.nacio}
      />
      <Sello en={cuadro("b01", "1945")} rota={-10} style={{ top: 560, left: 690 }} sale={k.nacio}>
        <div
          style={{
            fontFamily: TITULO,
            fontWeight: 700,
            fontSize: 64,
            color: C.rojo,
            border: `7px solid ${C.rojo}`,
            borderRadius: 18,
            padding: "2px 22px",
            background: "rgba(255,251,244,0.6)",
          }}
        >
          1945
        </div>
      </Sello>
      <Pop en={k.hoy} style={{ top: 640, left: 0, right: 0, display: "flex", justifyContent: "center" }} sonido="brillo" vol={0.4}>
        <Chip tam={46} fondo={C.verde} color={C.papel}>
          de 1945 a hoy
        </Chip>
      </Pop>
      <Pop en={k.nombre} sale={k.resultado} style={{ top: 640, left: 70 }}>
        <Chip tam={38}>George Stigler, economista</Chip>
      </Pop>
      <Sello en={k.problema} rota={-4} style={{ top: 400, left: 90, right: 90, display: "flex", justifyContent: "center" }}>
        <div
          style={{
            fontFamily: TITULO,
            fontWeight: 700,
            fontSize: 84,
            lineHeight: 1,
            textAlign: "center",
            color: C.tinta,
            background: C.amarillo,
            border: `8px solid ${C.tinta}`,
            borderRadius: 26,
            padding: "18px 30px",
          }}
        >
          El problema
          <br />
          de la dieta
        </div>
      </Sello>

      <Lienzo>
        {/* Pizarrón */}
        {pizarraFuera < 1 && f >= k.pizarra - 8 && (
          <g transform={`translate(${780 + pizarraFuera * 500},900) scale(${ap(f, k.pizarra - 8, 10, ENTRA)})`}>
            <rect x={-200} y={-150} width={400} height={260} rx={18} fill="#2F4A3A" stroke={C.tinta} strokeWidth={8} />
            <clipPath id={`tiza1${color ? "c" : "s"}`}>
              <rect x={-170} y={-110} width={340 * escribe} height={80} />
            </clipPath>
            <clipPath id={`tiza2${color ? "c" : "s"}`}>
              <rect x={-170} y={-20} width={340 * ap(f, k.pizarra + 16, 20)} height={70} />
            </clipPath>
            <text x={-160} y={-50} fontFamily={TITULO} fontWeight={600} fontSize={54} fill="#F4F1E6" clipPath={`url(#tiza1${color ? "c" : "s"})`}>
              mín Σ c·x
            </text>
            <text x={-160} y={30} fontFamily={TITULO} fontWeight={500} fontSize={40} fill="#F4F1E6" clipPath={`url(#tiza2${color ? "c" : "s"})`}>
              cubre todo ✓
            </text>
            <line x1={-120} y1={110} x2={-120} y2={170} stroke={C.tinta} strokeWidth={8} />
            <line x1={120} y1={110} x2={120} y2={170} stroke={C.tinta} strokeWidth={8} />
          </g>
        )}

        {/* La tienda (solo en el mundo de hoy) */}
        <PopG en={k.nosotros + 2} x={905} y={1010} escala={1.2}>
          <Tienda color={C.verde} ancho={300} />
          <text x={0} y={-75} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={26} fill={C.papel}>
            SÚPER
          </text>
        </PopG>

        {/* Plato con la dieta: Stigler lo prueba y lo aparta (se va de cuadro, no queda nada encima) */}
        {aparta < 1 && (
          <PopG en={k.resultado + 4} x={700 + aparta * 520} y={1150}>
            <g transform={`translate(${tiembla},0) rotate(${aparta * 25})`} opacity={1 - aparta}>
              <Plato />
              <PopG en={k.harina} x={-78} y={-60} escala={0.85} rota={-20} sonido="golpe" vol={0.4}>
                <Harina />
              </PopG>
              <PopG en={k.repollo} x={16} y={-48} escala={0.8} rota={20} sonido="golpe" vol={0.4}>
                <Repollo />
              </PopG>
              <PopG en={k.espinaca} x={100} y={-50} escala={0.7} rota={-20} sonido="golpe" vol={0.4}>
                <Espinaca />
              </PopG>
            </g>
          </PopG>
        )}
        <PopG en={k.anio} x={880} y={760} sale={k.nacio} flota={6}>
          <Calendario texto={`${dias}`} sub="días" />
        </PopG>
        <PopG en={k.barata} x={700} y={930} rota={-20} sale={k.nadie} sonido="ding" vol={0.3}>
          <Etiqueta texto="$ barata" color={C.verdeClaro} ancho={210} />
        </PopG>
        {/* Globito de asco, al costado de la cabeza (no encima de nada) */}
        <PopG en={k.comer} x={500} y={700} sale={k.nacio} sonido={null}>
          <path d="M-100,0 a100,62 0 1,1 200,0 a100,62 0 1,1 -200,0 Z" fill={C.papel} stroke={C.tinta} strokeWidth={6} />
          <path d="M-70,50 L-120,110 L-30,58" fill={C.papel} stroke={C.tinta} strokeWidth={6} strokeLinejoin="round" />
          <path d="M-80,56 L-30,52" stroke={C.papel} strokeWidth={10} />
          <text x={0} y={18} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={56} fill={C.verde}>
            ¡puaj!
          </text>
        </PopG>

        <Stickman
          x={290}
          y={1190}
          escala={1.45}
          f={f}
          pose={poseStigler}
          cara={caraStigler}
          extras={["anteojos", "sombrero", "moño"]}
          tinte={asco && f < k.nosotros + 6 ? "#CFEBC8" : undefined}
          sudor={asco && f < k.nosotros + 6}
          semilla={1}
        />
        {f >= entraSofi && (
          <g>
            <Stickman x={xSofi} y={1190} escala={1.4} f={f} pose={poseSofi} cara="feliz" mira="izq" color={C.violeta} extras={["cola"]} semilla={3} />
            <g transform={`translate(${xSofi - 150},1150) scale(-1.2,1.2)`}>
              <Changuito color={C.violeta} lleno={1} />
            </g>
          </g>
        )}
      </Lienzo>
    </AbsoluteFill>
  );
};

export const E1Pregunta: React.FC = () => {
  const f = useF();
  const wipe = cuadro("b04", "nosotros");
  const r = ap(f, wipe, 18, MUEVE) * 2400;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ filter: "sepia(0.75) saturate(0.65) contrast(0.95)" }}>
        <Mundo color={false} />
      </AbsoluteFill>
      {f >= wipe && (
        <AbsoluteFill style={{ clipPath: `circle(${r}px at 1000px 1050px)` }}>
          <MudoCtx.Provider value>
            <Mundo color />
          </MudoCtx.Provider>
        </AbsoluteFill>
      )}
      <Sfx en={cuadro("b01", "calculó")} s="tiza" vol={0.5} />
      <Sfx en={cuadro("b02", "todo")} s="tic" vol={0.4} />
      <Sfx en={cuadro("b02", "todo") + 8} s="tic" vol={0.4} />
      <Sfx en={cuadro("b02", "todo") + 16} s="tic" vol={0.4} />
      <Sfx en={cuadro("b03", "comer")} s="boing" vol={0.4} />
      <Sfx en={cuadro("b03", "comer") + 6} s="whoosh" vol={0.35} />
      <Sfx en={wipe} s="whoosh" vol={0.5} />
      <Sfx en={wipe + 8} s="pasos" vol={0.4} />
    </AbsoluteFill>
  );
};
