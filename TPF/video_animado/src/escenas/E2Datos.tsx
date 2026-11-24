import React from "react";
import { AbsoluteFill } from "remotion";
import { C, TITULO } from "../lib/tema";
import { ap, contar, ENTRA, miles, MUEVE } from "../lib/anim";
import { cuadro } from "../lib/tiempo";
import { Chip, Fondo, Lienzo, Numero, Pop, PopG, Sfx, Tarjeta, Tics, useF } from "../comp/UI";
import { BaseDatos, Brocoli, Etiqueta, Paquete, Tienda, Tilde } from "../comp/Iconos";
import mapa from "../datos/mapa.json";

const PUNTOS = mapa.puntos as [number, number][];
const COLORES_PAQ = [C.amarillo, C.verde, C.rojo, C.azul, C.violeta, C.naranja];

export const E2Datos: React.FC = () => {
  const f = useF();
  const k = {
    super: cuadro("b05", "súper"),
    informan: cuadro("b05", "informan"),
    dias: cuadro("b05", "días"),
    juntamos: cuadro("b05", "juntamos"),
    millones: cuadro("b05", "8 millones"),
    sucursales: cuadro("b05", "2.600"),
    info: cuadro("b06", "tabla"),
    productos: cuadro("b06", "28.000"),
    aporta: cuadro("b06", "qué"),
    cuesta: cuadro("b06", "cuánto"),
    apto: cuadro("b06", "para"),
  };

  // 1. Las tiendas mandan precios a la base
  const tiendasFuera = k.juntamos;
  const etiquetas = Array.from({ length: 16 }, (_, i) => {
    const s = k.informan + i * 4;
    const t = ap(f, s, 20, MUEVE);
    if (f < s || t >= 1 || f > tiendasFuera + 6) return null;
    const x0 = [230, 540, 850][i % 3];
    const y0 = 930;
    const x = x0 + (540 - x0) * t;
    const y = y0 + (600 - y0) * t - Math.sin(t * Math.PI) * 120;
    return (
      <g key={i} transform={`translate(${x},${y}) scale(${0.5 - 0.25 * t}) rotate(${(1 - t) * 30})`}>
        <Etiqueta texto="$" ancho={90} />
      </g>
    );
  });

  // 2. El mapa
  const MAPA_ALTO = 600;
  const mx = 640;
  const my = 600;
  const progMapa = ap(f, k.sucursales - 4, 34, (v) => v);
  const mapaFuera = ap(f, k.info, 10);
  // Zoom al mapa cuando se nombran las sucursales (con sonido de zoom)
  const zoomMapa = 1 + 0.15 * ap(f, k.sucursales + 12, 16, MUEVE);
  const cxMapa = mx + (0.4009 * MAPA_ALTO) / 2;
  const cyMapa = my + MAPA_ALTO / 2;

  // 3. Productos
  const grillaFuera = ap(f, k.aporta - 10, 8);
  const fichas = [
    { en: k.aporta, texto: "Qué aporta", fondo: C.verdeClaro, icono: <Brocoli /> },
    { en: k.cuesta, texto: "Cuánto cuesta", fondo: C.amarilloClaro, icono: <Etiqueta texto="$" ancho={80} /> },
    { en: k.apto, texto: "Para quién es apto", fondo: C.azulClaro, icono: <Tilde r={50} color={C.azul} /> },
  ];

  return (
    <AbsoluteFill>
      <Fondo />
      <Lienzo>
        {/* Tiendas y base de datos */}
        {[230, 540, 850].map((x, i) => (
          <PopG key={x} en={k.super + i * 3} x={x} y={1010} escala={0.75} sale={tiendasFuera}>
            <Tienda color={[C.rojo, C.azul, C.verde][i]} ancho={260} />
          </PopG>
        ))}
        <PopG en={k.super + 6} x={540} y={600} escala={1.2} sale={tiendasFuera} flota={6}>
          <BaseDatos />
        </PopG>
        {etiquetas}

        {/* Mapa de sucursales reales */}
        {f >= k.sucursales - 4 && mapaFuera < 1 && (
          <g
            transform={`translate(${cxMapa},${cyMapa}) scale(${zoomMapa * (1 - mapaFuera * 0.2)}) translate(${mx - cxMapa},${my - cyMapa})`}
            opacity={1 - mapaFuera}
          >
            {PUNTOS.map(([x, y], i) => {
              const umbral = i / PUNTOS.length;
              if (umbral > progMapa) return null;
              const recien = Math.max(0, 1 - (progMapa - umbral) * 12);
              return (
                <circle
                  key={i}
                  cx={x * MAPA_ALTO}
                  cy={y * MAPA_ALTO}
                  r={4 + recien * 6}
                  fill={recien > 0.2 ? C.amarillo : C.rojo}
                  opacity={0.75}
                />
              );
            })}
          </g>
        )}

        {/* Grilla de productos */}
        {f >= k.info + 4 &&
          grillaFuera < 1 &&
          Array.from({ length: 42 }, (_, i) => {
            const col = i % 7;
            const fila = Math.floor(i / 7);
            const en = k.info + 4 + (col + fila) * 2.2;
            if (f < en) return null;
            const s = ap(f, en, 10, ENTRA);
            return (
              <g
                key={i}
                transform={`translate(${170 + col * 123},${600 + fila * 112}) scale(${0.95 * s * (1 - grillaFuera)})`}
                opacity={1 - grillaFuera}
              >
                <Paquete color={COLORES_PAQ[(i * 5) % COLORES_PAQ.length]} />
              </g>
            );
          })}
      </Lienzo>

      {/* Contadores */}
      <Pop en={k.juntamos + 2} sale={k.info} style={{ top: 360, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <Numero texto={`+${miles(contar(f, k.juntamos + 2, k.millones - k.juntamos + 24, 0, 8000000))}`} tam={132} style={{ position: "relative" }} />
          <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 48, color: C.tintaSuave }}>precios</div>
        </div>
      </Pop>
      <Pop en={k.sucursales} sale={k.info} style={{ top: 760, left: 70 }} desde="abajo">
        <Numero texto={miles(contar(f, k.sucursales, 30, 0, 2600))} tam={120} color={C.rojo} style={{ position: "relative" }} />
        <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 48, color: C.tinta }}>sucursales</div>
        <div style={{ fontFamily: TITULO, fontWeight: 500, fontSize: 34, color: C.tintaSuave, marginTop: 8 }}>
          cada punto, una de verdad
        </div>
      </Pop>
      <Pop en={k.informan + 6} sale={tiendasFuera} style={{ top: 720, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <Chip tam={38} fondo={C.azulClaro}>
          SEPA · Precios Claros
        </Chip>
      </Pop>
      <Pop en={k.info + 4} sale={k.aporta + 40} style={{ top: 370, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ textAlign: "center" }}>
          <Numero texto={miles(contar(f, k.info + 4, k.productos - k.info + 20, 0, 28000))} tam={132} color={C.verde} style={{ position: "relative" }} />
          <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 48, color: C.tintaSuave }}>productos con su tabla nutricional</div>
        </div>
      </Pop>

      {/* La ficha de un producto: tres cosas */}
      <Pop en={k.aporta - 2} style={{ top: 640, left: 110 }}>
        <Tarjeta style={{ position: "relative", width: 860, padding: "34px 40px", display: "flex", flexDirection: "column", gap: 26 }}>
          {fichas.map((x, i) =>
            f >= x.en ? (
              <Pop key={i} en={x.en} desde="abajo" style={{ position: "relative" }}>
                <Chip tam={52} fondo={x.fondo} icono={x.icono}>
                  {x.texto}
                </Chip>
              </Pop>
            ) : (
              <div key={i} style={{ height: 90 }} />
            ),
          )}
        </Tarjeta>
      </Pop>

      <Sfx en={k.informan} s="whoosh" vol={0.3} />
      <Tics desde={k.juntamos + 2} hasta={k.millones + 24} />
      <Tics desde={k.sucursales} hasta={k.sucursales + 30} cada={3} vol={0.15} />
      <Sfx en={k.sucursales} s="brillo" vol={0.4} />
      <Sfx en={k.sucursales + 12} s="zoom" vol={0.4} />
      <Tics desde={k.info + 4} hasta={k.productos + 20} cada={4} vol={0.18} />
      <Sfx en={k.apto + 6} s="ding" vol={0.35} />
    </AbsoluteFill>
  );
};
