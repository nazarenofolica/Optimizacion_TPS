import React from "react";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Video } from "@remotion/media";
import { C, TITULO } from "../lib/tema";
import { ap, contar, ENTRA, miles, MUEVE, SALE } from "../lib/anim";
import { cuadro, finBeat, T } from "../lib/tiempo";
import { Chip, EscenaCtx, Fondo, Lienzo, Numero, Pop, Sfx, Tarjeta, Tics, useF } from "../comp/UI";
import PAGINA from "../datos/pagina.json";
import { AnilloMetas, Confeti } from "../comp/Extra";
import { caminar, mezclarPose, poseEn, POSES, recorrido, Stickman } from "../comp/Stickman";
import { Calendario, Celular, Pin, Reloj, Tienda, Tilde } from "../comp/Iconos";

const ANCHO_V = 948;
const ALTO_V = 520;

/** La ventana del navegador con la grabación real de la página (TPF/video/grabar.py), recortada y acercada. */
const Navegador: React.FC<{ k: Record<string, number> }> = ({ k }) => {
  const f = useF();
  const { desde } = React.useContext(EscenaCtx);
  const entra = ap(f, k.pagina - 4, 14, ENTRA);
  const sale = ap(f, k.sofi, 12, SALE);
  if (f < k.pagina - 4 || sale >= 1) return null;
  const durForm = k.ticket - k.pagina;
  const durRes = k.sofi + 12 - k.ticket;
  // Acercamiento lento al total del ticket mientras se lo nombra
  const zoom = 1 + 0.35 * ap(f, k.ticket + 10, 70, MUEVE);
  return (
    <Tarjeta
      style={{
        left: 60,
        top: 340,
        width: ANCHO_V + 12,
        transform: `translateY(${(1 - entra) * 300 - sale * 900}px) scale(${0.85 + 0.15 * entra}) rotate(${(1 - entra) * -4}deg)`,
        opacity: entra,
      }}
    >
      <div style={{ height: 58, background: C.tinta, display: "flex", alignItems: "center", gap: 12, padding: "0 22px" }}>
        {[C.rojo, C.amarillo, C.verde].map((c) => (
          <div key={c} style={{ width: 20, height: 20, borderRadius: 10, background: c }} />
        ))}
        <div
          style={{
            marginLeft: 14,
            flex: 1,
            background: "rgba(255,255,255,0.14)",
            color: C.papel,
            borderRadius: 18,
            padding: "6px 18px",
            fontFamily: TITULO,
            fontSize: 26,
          }}
        >
          {T.url}
        </div>
      </div>
      <div style={{ position: "relative", width: ANCHO_V, height: ALTO_V, overflow: "hidden", background: "#F7F7F5" }}>
        <Sequence from={k.pagina - desde} durationInFrames={durForm} layout="none">
          <Video
            src={staticFile("pagina_form.mp4")}
            muted
            playbackRate={Math.max(1, 22 / (durForm / 30))}
            style={{ position: "absolute", width: 1280 * 0.98, left: -150 * 0.98, top: 0 }}
          />
        </Sequence>
        <Sequence from={k.ticket - desde} durationInFrames={durRes} layout="none">
          <Video
            src={staticFile("pagina_res.mp4")}
            muted
            playbackRate={Math.max(1, Math.min(2.4, 14 / (durRes / 30)))}
            style={{
              position: "absolute",
              width: 1280 * 1.115,
              left: -150 * 1.115,
              top: -60 * 1.115,
              transformOrigin: "560px 170px",
              transform: `scale(${zoom})`,
            }}
          />
        </Sequence>
      </div>
    </Tarjeta>
  );
};

export const E3Pagina: React.FC = () => {
  const f = useF();
  const k = {
    pagina: cuadro("b07", "página"),
    quienes: cuadro("b07", "quiénes"),
    donde: cuadro("b07", "dónde"),
    tiempo: cuadro("b07", "cuánto"),
    ticket: cuadro("b08", "ticket"),
    comprar: cuadro("b08", "qué"),
    super: cuadro("b08", "en"),
    minutos: cuadro("b08", "cuántos"),
    sofi: cuadro("b09", "Sofi"),
    centro: cuadro("b09", "centro"),
    precio: cuadro("b09", "$24.000"),
    semana: cuadro("b09", "semana"),
    metas: cuadro("b09", "37"),
    fin: finBeat("b09"),
  };

  const chips1 = [
    { en: k.quienes, texto: "Quiénes comen", icono: <g transform="scale(0.8)"><circle cx={-26} cy={-10} r={22} fill={C.violeta} stroke={C.tinta} strokeWidth={6} /><circle cx={26} cy={-10} r={22} fill={C.amarillo} stroke={C.tinta} strokeWidth={6} /><path d="M-60,50 Q-26,10 8,50 M-8,50 Q26,10 60,50" stroke={C.tinta} strokeWidth={8} fill="none" /></g> },
    { en: k.donde, texto: "Dónde comprás", icono: <Pin /> },
    { en: k.tiempo, texto: "Para cuánto tiempo", icono: <g transform="scale(0.8)"><Calendario texto="7" /></g> },
  ];
  const chips2 = [
    { en: k.comprar, texto: "Qué comprar", icono: <Tilde r={52} /> },
    { en: k.super, texto: "En qué súper", icono: <g transform="scale(0.45)"><Tienda color={C.rojo} ancho={240} /></g> },
    { en: k.minutos, texto: "≈ 9 min a pie (estimado)", icono: <Reloj minutos={9} /> },
  ];

  // Sofi: abajo a la izquierda con el celular; después camina al centro de la escena
  const xSofi = f < k.sofi ? 165 : recorrido(f, k.sofi, 22, 165, 270);
  const camina = f >= k.sofi && f < k.sofi + 22;
  const pose = camina
    ? caminar((f - k.sofi) / 30, 2.2)
    : poseEn(f, [
        [0, "celular"],
        [k.sofi + 22, "parada"],
        [k.precio, "señala"],
        [k.metas + 26, "festeja"],
      ]);
  const escSofi = f < k.sofi ? 1.05 : 1.05 + 0.45 * ap(f, k.sofi, 22, MUEVE);
  const llenas = Math.round(contar(f, k.metas, 26, 0, 37));
  const velForm = Math.max(1, 22 / ((k.ticket - k.pagina) / 30));

  return (
    <AbsoluteFill>
      <Fondo />
      <Navegador k={k} />

      {chips1.map((c, i) => (
        <Pop key={i} en={c.en} sale={k.ticket} desde="abajo" style={{ top: 930 + i * 104, left: 320 }}>
          <Chip tam={46} icono={c.icono}>
            {c.texto}
          </Chip>
        </Pop>
      ))}
      {chips2.map((c, i) => (
        <Pop key={i} en={c.en} sale={k.sofi} desde="abajo" style={{ top: 930 + i * 104, left: 320 }}>
          <Chip tam={46} icono={c.icono} fondo={i === 2 ? C.amarilloClaro : C.papel}>
            {c.texto}
          </Chip>
        </Pop>
      ))}

      {/* Sofi */}
      <Pop en={k.sofi + 14} style={{ top: 380, left: 80 }} desde="abajo">
        <Chip tam={40} fondo={C.violetaClaro}>
          Sofi · 34 años · oficinista
        </Chip>
      </Pop>
      <Pop en={Math.max(k.centro, k.sofi + 18)} style={{ top: 470, left: 80 }} desde="abajo">
        <Chip tam={34} icono={<Pin color={C.violeta} />}>
          Centro de Buenos Aires
        </Chip>
      </Pop>
      <Pop en={k.precio - 2} style={{ top: 600, left: 470, width: 560, textAlign: "center" }}>
        <Numero texto={`$${miles(contar(f, k.precio - 2, 22, 0, 24000))}`} tam={136} color={C.tinta} style={{ position: "relative" }} />
        <Pop en={k.semana} style={{ position: "relative" }}>
          <Chip tam={40} fondo={C.amarillo}>
            por semana
          </Chip>
        </Pop>
      </Pop>
      {f >= k.metas - 2 && (
        <Pop en={k.metas - 2} style={{ top: 900, left: 560 }}>
          <svg width={400} height={330} viewBox="-200 -165 400 330" style={{ overflow: "visible" }}>
            <AnilloMetas x={0} y={0} r={140} total={37} llenos={llenas} />
            <text x={0} y={22} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={76} fill={llenas === 37 ? C.verde : C.tinta}>
              {llenas}/37
            </text>
            <text x={0} y={66} textAnchor="middle" fontFamily={TITULO} fontWeight={600} fontSize={30} fill={C.tintaSuave}>
              metas
            </text>
          </svg>
        </Pop>
      )}

      <Lienzo>
        <Stickman
          x={xSofi}
          y={1235}
          escala={escSofi}
          f={f}
          pose={f >= k.precio && f < k.metas + 26 ? mezclarPose(pose, POSES.señala, 0) : pose}
          cara={f >= k.metas + 20 ? "contenta" : "feliz"}
          color={C.violeta}
          extras={["cola"]}
          semilla={3}
          enMano={f < k.sofi ? <g transform="rotate(-10) scale(0.55) translate(10,-40)"><Celular /></g> : undefined}
        />
        <Confeti en={k.metas + 26} x={760} y={1000} />
      </Lienzo>

      <Sfx en={k.pagina} s="whoosh" vol={0.35} />
      {/* Los clics y el tipeo de la grabación, al ritmo acelerado con que se ve */}
      {PAGINA.clics.map((c) => {
        const en = k.pagina + Math.round((c / velForm) * 30);
        return en < k.ticket ? <Sfx key={c} en={en} s="click" vol={0.55} /> : null;
      })}
      {PAGINA.tipeo.map(([a]) => {
        const en = k.pagina + Math.round((a / velForm) * 30);
        return en < k.ticket ? <Sfx key={a} en={en} s="teclado" vol={0.35} /> : null;
      })}
      <Sfx en={k.ticket} s="caja" vol={0.4} />
      <Sfx en={k.ticket + 10} s="zoom" vol={0.4} />
      <Sfx en={k.sofi} s="whoosh" vol={0.3} />
      <Tics desde={k.precio - 2} hasta={k.precio + 20} cada={3} vol={0.15} />
      <Sfx en={k.precio + 20} s="caja" vol={0.45} />
      <Tics desde={k.metas - 2} hasta={k.metas + 24} cada={2} vol={0.12} />
      <Sfx en={k.metas + 26} s="ding" vol={0.45} />
      <Sfx en={k.metas + 26} s="brillo" vol={0.35} />
    </AbsoluteFill>
  );
};
