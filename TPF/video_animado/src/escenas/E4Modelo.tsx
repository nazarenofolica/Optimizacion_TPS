import React from "react";
import { AbsoluteFill } from "remotion";
import { C, FORMULA, SOMBRA, TITULO } from "../lib/tema";
import { ap, ENTRA, MUEVE, REBOTA, respira, sacudir } from "../lib/anim";
import { cuadro, escena } from "../lib/tiempo";
import { Chip, Fondo, Lienzo, Parte, Pop, PopG, Sfx, TituloAnimado, useF, AparecG } from "../comp/UI";
import { poseEn, Stickman } from "../comp/Stickman";
import { Fideos } from "../comp/Iconos";

/** Una fórmula en una tarjeta: el texto va como nodos, para poder pintar cada pieza. */
export const Formula: React.FC<{ children: React.ReactNode; tam?: number; fondo?: string; style?: React.CSSProperties }> = ({
  children,
  tam = 58,
  fondo = C.papel,
  style,
}) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: tam * 0.25,
      padding: `${tam * 0.3}px ${tam * 0.55}px`,
      background: fondo,
      border: `6px solid ${C.tinta}`,
      borderRadius: 26,
      boxShadow: SOMBRA,
      fontFamily: FORMULA,
      fontWeight: 700,
      fontSize: tam,
      color: C.tinta,
      whiteSpace: "nowrap",
      ...style,
    }}
  >
    {children}
  </div>
);

const Etapa: React.FC<{ n: number; nombre: string; como: string; color: string; activa: number }> = ({ n, nombre, como, color, activa }) => (
  <div
    style={{
      width: 440,
      padding: "20px 26px",
      background: C.papel,
      border: `6px solid ${activa > 0.5 ? color : C.tinta}`,
      borderRadius: 26,
      boxShadow: SOMBRA,
      opacity: 0.35 + 0.65 * activa,
      transform: `scale(${0.94 + 0.06 * activa})`,
    }}
  >
    <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 28, color, letterSpacing: 2 }}>ETAPA {n}</div>
    <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 44, color: C.tinta, lineHeight: 1.05 }}>{nombre}</div>
    <div style={{ fontFamily: TITULO, fontWeight: 500, fontSize: 30, color: C.tintaSuave }}>{como}</div>
  </div>
);

export const E4Modelo: React.FC = () => {
  const f = useF();
  const k = {
    decide: cuadro("b10"),
    objetivos: cuadro("b10", "objetivos"),
    pelean: cuadro("b10", "pelean"),
    comerBien: cuadro("b10", "comer"),
    gastar: cuadro("b10", "gastar"),
    podriamos: cuadro("b11", "podríamos"),
    pero: cuadro("b11", "pero"),
    primero: cuadro("b11", "primero"),
    despues: cuadro("b11", "después"),
    bolsillo: cuadro("b11", "bolsillo"),
    etapa1: cuadro("b12"),
    lineal: cuadro("b12", "lineal"),
    rango: cuadro("b12", "rango"),
    corto: cuadro("b12", "quedarse"),
    pasarse: cuadro("b12", "pasarse"),
    desvio: cuadro("b12", "desvío"),
    minimiza: cuadro("b12", "minimiza"),
    etapa2: cuadro("b13"),
    barato: cuadro("b13", "barato"),
    mismo: cuadro("b13", "mismo"),
    paquetes: cuadro("b13", "paquetes"),
    nadie: cuadro("b13", "nadie"),
    medio: cuadro("b13", "medio"),
    fideos: cuadro("b13", "fideos"),
    fin: escena("e4").hasta,
  };

  // --- A: la cinchada, el precio de la salud (tachado) y el podio
  const tironeo = f < k.primero ? respira(f, 0.9, 26) + respira(f, 0.37, 10) : 0;
  const subeVerde = ap(f, k.primero + 4, 16, MUEVE);
  const subeRojo = ap(f, k.despues + 4, 16, MUEVE);
  const xV = 250 + tironeo + subeVerde * 180;
  const xR = 830 + tironeo + subeRojo * -180;
  const yV = 1235 - subeVerde * 220 - Math.sin(subeVerde * Math.PI) * 80;
  const yR = 1235 - subeRojo * 140 - Math.sin(subeRojo * Math.PI) * 70;
  const podio = ap(f, k.primero - 2, 12, REBOTA);
  const tacha = ap(f, k.pero, 10, MUEVE);

  // --- B: la pista de una meta
  const X0 = 110;
  const X1 = 970;
  const Y = 820;
  const xp = (t: number) => X0 + (X1 - X0) * t;
  const pista = ap(f, k.lineal, 14, MUEVE);
  const rango = ap(f, k.rango, 12, REBOTA);
  const corto = ap(f, k.corto, 12, ENTRA);
  const pasa = ap(f, k.pasarse, 12, ENTRA);
  const realza = f >= k.desvio && f < k.desvio + 12 ? 1 + 0.12 * Math.sin(((f - k.desvio) / 12) * Math.PI) : 1;

  const activa1 = f < k.etapa2 ? 1 : 1 - ap(f, k.etapa2, 10);
  const activa2 = ap(f, k.etapa2, 10);

  // --- C: medio paquete
  const corte = ap(f, k.medio, 12, MUEVE);

  return (
    <AbsoluteFill>
      <Fondo />

      {/* ============ A ============ */}
      <Parte desde={k.decide} hasta={k.etapa1}>
        <TituloAnimado texto="¿Cómo decide?" en={k.decide} tam={104} style={{ top: 400, left: 60, right: 60 }} sale={k.objetivos} />
        <Pop en={k.comerBien} sale={k.podriamos} style={{ top: 700, left: 90 }} desde="abajo">
          <Chip tam={50} fondo={C.verdeClaro}>
            comer bien
          </Chip>
        </Pop>
        <Pop en={k.gastar} sale={k.podriamos} style={{ top: 712, left: 505 }}>
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 44, color: C.tintaSuave }}>vs.</div>
        </Pop>
        <Pop en={k.gastar} sale={k.podriamos} style={{ top: 700, left: 640 }} desde="abajo">
          <Chip tam={50} fondo={C.rojoClaro}>
            gastar poco
          </Chip>
        </Pop>
        {/* "Podríamos ponerle precio a la salud": la fórmula con λ, que se tacha */}
        <Pop en={k.podriamos} sale={k.primero} style={{ top: 420, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <div style={{ position: "relative" }}>
            <Formula tam={54}>
              <span>mín</span>
              <span>costo</span>
              <span>+</span>
              <span style={{ color: C.rojo }}>λ</span>
              <span>·</span>
              <span style={{ color: C.verde }}>(lo que falta)</span>
            </Formula>
            <div
              style={{
                position: "absolute",
                left: -10,
                top: "50%",
                height: 10,
                width: `calc((100% + 20px) * ${tacha})`,
                background: C.rojo,
                borderRadius: 5,
                transform: "rotate(-4deg)",
              }}
            />
          </div>
          <div
            style={{
              position: "absolute",
              top: 120,
              left: 0,
              right: 0,
              textAlign: "center",
              fontFamily: FORMULA,
              fontWeight: 600,
              fontSize: 32,
              color: C.tintaSuave,
              opacity: ap(f, k.podriamos + 10, 10),
            }}
          >
            λ = cuántos pesos vale la salud
          </div>
        </Pop>
        {/* Metas lexicográficas */}
        <Pop en={k.bolsillo + 6} style={{ top: 410, left: 0, right: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <Formula tam={60}>
            <span>lex mín (</span>
            <span style={{ color: C.verde }}>Φ</span>
            <span>,</span>
            <span style={{ color: C.naranja }}>costo</span>
            <span>)</span>
          </Formula>
          <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 34, color: C.tintaSuave }}>
            metas lexicográficas: primero una, después la otra
          </div>
        </Pop>
        <Lienzo>
          {f < k.primero && (
            <g>
              <path
                d={`M${xV + 70},1105 Q540,${1125 + respira(f, 0.5, 6)} ${xR - 70},1105`}
                stroke="#B07A4A"
                strokeWidth={10}
                fill="none"
                strokeLinecap="round"
              />
              <g transform={`translate(${540 + tironeo},1120)`}>
                <path d="M0,0 L0,-60 L40,-46 L0,-32" fill={C.amarillo} stroke={C.tinta} strokeWidth={5} strokeLinejoin="round" />
              </g>
            </g>
          )}
          {podio > 0 && (
            <g transform={`translate(0,${(1 - podio) * 300})`} opacity={Math.min(1, podio * 2)}>
              <rect x={330} y={1015} width={200} height={222} rx={10} fill={C.verde} stroke={C.tinta} strokeWidth={7} />
              <rect x={550} y={1095} width={200} height={142} rx={10} fill={C.naranja} stroke={C.tinta} strokeWidth={7} />
              <text x={430} y={1120} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={72} fill={C.papel}>
                1°
              </text>
              <text x={430} y={1180} textAnchor="middle" fontFamily={TITULO} fontWeight={600} fontSize={34} fill={C.papel}>
                salud
              </text>
              <text x={650} y={1170} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={56} fill={C.papel}>
                2°
              </text>
              <text x={650} y={1218} textAnchor="middle" fontFamily={TITULO} fontWeight={600} fontSize={30} fill={C.papel}>
                bolsillo
              </text>
            </g>
          )}
          <Stickman
            x={xV}
            y={yV}
            escala={1.15}
            f={f}
            pose={poseEn(f, [[0, "tira"], [k.primero + 4, "festeja"]])}
            cara={f >= k.primero ? "contenta" : "decidida"}
            color={C.verde}
            extras={["vincha"]}
            semilla={2}
          />
          <Stickman
            x={xR}
            y={yR}
            escala={1.15}
            f={f}
            pose={poseEn(f, [[0, "tira"], [k.despues + 14, "manosCadera"]])}
            mira="izq"
            cara={f >= k.despues ? "feliz" : "decidida"}
            color={C.naranja}
            extras={["gorra"]}
            semilla={5}
          />
        </Lienzo>
      </Parte>

      {/* ============ Las dos etapas (arriba, toda la parte B y C) ============ */}
      <Parte desde={k.etapa1 + 8} hasta={k.fin - 2} mudo>
        <Pop en={k.etapa1 + 8} style={{ top: 370, left: 60 }} desde="abajo">
          <Etapa n={1} nombre="Cumplir las metas" como="programa lineal" color={C.verde} activa={activa1} />
        </Pop>
        <Pop en={k.etapa1 + 12} style={{ top: 440, left: 517 }}>
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 52, color: C.tinta }}>→</div>
        </Pop>
        <Pop en={k.etapa1 + 14} style={{ top: 370, left: 580 }} desde="abajo">
          <Etapa n={2} nombre="Lo más barato" como="programa entero" color={C.naranja} activa={activa2} />
        </Pop>
      </Parte>

      {/* ============ B: rango y desvíos ============ */}
      <Parte desde={k.lineal} hasta={k.etapa2}>
        <Lienzo>
          {/* pista */}
          <line x1={X0} y1={Y} x2={X0 + (X1 - X0) * pista} y2={Y} stroke="rgba(35,33,58,0.14)" strokeWidth={30} strokeLinecap="round" />
          {rango > 0 && (
            <g>
              <line x1={xp(0.5 - 0.16 * rango)} y1={Y} x2={xp(0.5 + 0.16 * rango)} y2={Y} stroke={C.verde} strokeWidth={30} opacity={0.55} />
              {[0.34, 0.66].map((t, i) => (
                <g key={t} opacity={Math.min(1, rango)}>
                  <line x1={xp(t)} y1={Y - 34} x2={xp(t)} y2={Y + 34} stroke={C.tinta} strokeWidth={6} strokeLinecap="round" />
                  <text x={xp(t)} y={Y - 50} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={48} fill={C.tinta}>
                    {i === 0 ? "L" : "U"}
                  </text>
                </g>
              ))}
              <text x={xp(0.5)} y={Y - 110} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={40} fill={C.verde} opacity={Math.min(1, rango)}>
                rango de la meta
              </text>
            </g>
          )}
          {/* quedarse corto: Δ déficit */}
          {corto > 0 && (
            <g opacity={Math.min(1, corto * 2)}>
              <circle cx={xp(0.1)} cy={Y} r={24 * Math.min(1.3, 0.4 + corto)} fill={C.rojo} stroke={C.tinta} strokeWidth={6} />
              <line x1={xp(0.1)} y1={Y + 70} x2={xp(0.1 + (0.34 - 0.1) * corto)} y2={Y + 70} stroke={C.rojo} strokeWidth={8} strokeLinecap="round" />
              {corto > 0.95 && (
                <path d={`M${xp(0.34) - 18},${Y + 58} L${xp(0.34)},${Y + 70} L${xp(0.34) - 18},${Y + 82}`} stroke={C.rojo} strokeWidth={8} fill="none" strokeLinecap="round" />
              )}
              <g transform={`translate(${xp(0.22)},${Y + 140}) scale(${realza})`}>
                <text textAnchor="middle" fontFamily={FORMULA} fontWeight={700} fontSize={48} fill={C.rojo}>
                  Δ déficit
                </text>
              </g>
            </g>
          )}
          {/* pasarse: Δ exceso */}
          {pasa > 0 && (
            <g opacity={Math.min(1, pasa * 2)}>
              <circle cx={xp(0.88)} cy={Y} r={24 * Math.min(1.3, 0.4 + pasa)} fill={C.naranja} stroke={C.tinta} strokeWidth={6} />
              <line x1={xp(0.66)} y1={Y + 70} x2={xp(0.66 + (0.88 - 0.66) * pasa)} y2={Y + 70} stroke={C.naranja} strokeWidth={8} strokeLinecap="round" />
              {pasa > 0.95 && (
                <path d={`M${xp(0.88) - 18},${Y + 58} L${xp(0.88)},${Y + 70} L${xp(0.88) - 18},${Y + 82}`} stroke={C.naranja} strokeWidth={8} fill="none" strokeLinecap="round" />
              )}
              <g transform={`translate(${xp(0.77)},${Y + 140}) scale(${realza})`}>
                <text textAnchor="middle" fontFamily={FORMULA} fontWeight={700} fontSize={48} fill={C.naranja}>
                  Δ exceso
                </text>
              </g>
            </g>
          )}
        </Lienzo>
        <Pop en={k.minimiza} style={{ top: 1060, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <Formula tam={50}>
            <span>mín Φ = Σ w (</span>
            <span style={{ color: C.rojo }}>Δ déf</span>
            <span>+</span>
            <span style={{ color: C.naranja }}>Δ exc</span>
            <span>)</span>
          </Formula>
        </Pop>
      </Parte>

      {/* ============ C: lo más barato, con paquetes enteros ============ */}
      <Parte desde={k.etapa2 + 8} hasta={k.fin - 2} mudo>
        {[
          { en: k.barato, f: "mín Σ π·x", dice: "la compra más barata" },
          { en: k.mismo, f: "Δ ≤ Δ* etapa 1", dice: "ninguna meta queda peor" },
          { en: k.paquetes, f: "x ∈ {0, 1, 2, …}", dice: "paquetes enteros" },
        ].map((r, i) => (
          <Pop key={i} en={r.en} style={{ top: 640 + i * 120, left: 70, right: 70 }} desde="abajo">
            <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
              <div style={{ width: 430, fontFamily: FORMULA, fontWeight: 700, fontSize: 48, color: C.tinta, whiteSpace: "nowrap" }}>{r.f}</div>
              <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 38, color: C.tintaSuave }}>{r.dice}</div>
            </div>
          </Pop>
        ))}
        <Lienzo>
          {f >= k.nadie - 2 && (
            <PopG en={k.nadie - 2} x={330} y={1130} escala={1.15}>
              <g transform={`translate(${sacudir(f, k.fideos, 14, 6)},0)`}>
                <g transform={`translate(${-corte * 40},${corte * 6}) rotate(${-corte * 14})`}>
                  <clipPath id="mitadIzq">
                    <rect x={-80} y={-90} width={80} height={180} />
                  </clipPath>
                  <g clipPath="url(#mitadIzq)">
                    <Fideos />
                  </g>
                </g>
                <g transform={`translate(${corte * 40},${corte * 6}) rotate(${corte * 14})`} opacity={1 - 0.6 * ap(f, k.fideos, 10)}>
                  <clipPath id="mitadDer">
                    <rect x={0} y={-90} width={80} height={180} />
                  </clipPath>
                  <g clipPath="url(#mitadDer)">
                    <Fideos />
                  </g>
                </g>
                {corte < 0.3 && <line x1={0} y1={-80} x2={0} y2={80} stroke={C.rojo} strokeWidth={5} strokeDasharray="12 10" />}
              </g>
            </PopG>
          )}
          <AparecG en={k.nadie}>
            <Stickman
              x={950}
              y={1235}
              escala={0.85}
              f={f}
              pose={poseEn(f, [[0, "señala"], [k.fideos + 4, "encoge"]])}
              mira="izq"
              cara={f >= k.fideos + 4 ? "contenta" : "sorpresa"}
              color={C.azul}
              semilla={7}
            />
          </AparecG>
        </Lienzo>
        <Pop en={k.fideos} style={{ top: 1080, left: 450 }} sonido="error" vol={0.3}>
          <Chip tam={36} fondo={C.rojoClaro}>
            ½ paquete: no existe
          </Chip>
        </Pop>
      </Parte>

      <Sfx en={k.decide} s="boing" vol={0.3} />
      <Sfx en={k.pelean} s="whoosh" vol={0.3} />
      <Sfx en={k.pero} s="error" vol={0.3} />
      <Sfx en={k.primero + 4} s="boing" vol={0.35} />
      <Sfx en={k.despues + 4} s="boing" vol={0.3} />
      <Sfx en={k.minimiza} s="brillo" vol={0.3} />
      <Sfx en={k.etapa2} s="whoosh" vol={0.3} />
      <Sfx en={k.medio} s="whoosh" vol={0.3} />
    </AbsoluteFill>
  );
};
