import React from "react";
import { AbsoluteFill } from "remotion";
import { C, FORMULA, SOMBRA, TITULO } from "../lib/tema";
import { ap, ENTRA, miles, MUEVE, SALE } from "../lib/anim";
import { cuadro, escena } from "../lib/tiempo";
import { AparecG, Fondo, Lienzo, Parte, Pop, PopG, Sfx, Tarjeta, Tics, useF } from "../comp/UI";
import { poseEn, Stickman } from "../comp/Stickman";
import { Alerta, Arroz, Estrella, Fideos, Lentejas, Tilde } from "../comp/Iconos";

/*
 * El ejemplo del video largo (TPF/video/escenas.py, E5Ejemplo), con sus números: x = lentejas, y = arroz, en gramos
 * por día. Los tres productos dan 350 kcal cada 100 g. Energía: 3,5x + 3,5y entre 1.900 y 2.100. Proteína:
 * 0,25x + 0,07y >= 60 (después 300). Costo por semana: 5,6x + 1,75y.
 *
 * El hilo (como en "Tu bolsillo"): arriba, un marcador con los cinco pasos que se van tildando; al costado, "Tu compra",
 * que muestra en vivo la compra del punto que se mueve por el plano. Las tarjetas de lentejas y arroz vuelan a los ejes:
 * de los productos sale el plano. Las rectas y la región se calculan; con 300 g el eje se agranda para que la recta se
 * siga viendo.
 */
const YMAX = 900;
const OX = 170;
const OY = 1150;
const AN = 800;
const AL = 400;
type P = [number, number];

const S_MIN = 1900 / 3.5; // gramos totales en el borde de 1.900 kcal
/** El vértice óptimo (borde de 1.900 kcal y recta de proteína) para una meta de proteína p. */
const vertice = (p: number): P => {
  const x = (p - 0.07 * S_MIN) / 0.18;
  return [x, S_MIN - x];
};
const costo = (x: number, y: number) => 5.6 * x + 1.75 * y;
const proteina = (x: number, y: number) => 0.25 * x + 0.07 * y;

const recortar = (poli: P[], a: number, b: number, c: number, mayor = true): P[] => {
  const v = (p: P) => (mayor ? a * p[0] + b * p[1] - c : c - a * p[0] - b * p[1]);
  const out: P[] = [];
  for (let i = 0; i < poli.length; i++) {
    const p = poli[i];
    const q = poli[(i + 1) % poli.length];
    const vp = v(p);
    const vq = v(q);
    if (vp >= 0) out.push(p);
    if (vp * vq < 0) {
      const t = vp / (vp - vq);
      out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
    }
  }
  return out;
};

/** Los dos puntos donde la recta a·x + b·y = c corta el cuadro [0, xm] × [0, YMAX]. */
const segmento = (a: number, b: number, c: number, xm: number): [P, P] | null => {
  const pts: P[] = [];
  for (const x of [0, xm]) {
    const y = (c - a * x) / b;
    if (y >= -1e-6 && y <= YMAX + 1e-6) pts.push([x, y]);
  }
  for (const y of [0, YMAX]) {
    const x = (c - b * y) / a;
    if (x >= -1e-6 && x <= xm + 1e-6) pts.push([x, y]);
  }
  if (pts.length < 2) return null;
  pts.sort((p, q) => p[0] - q[0] || p[1] - q[1]);
  return [pts[0], pts[pts.length - 1]];
};

/** Interpola por claves [cuadro, x, y] con curva suave (para el punto que recorre el plano). */
const porClaves = (f: number, claves: [number, number, number][], dur = 18): P => {
  let [x, y] = [claves[0][1], claves[0][2]];
  for (let i = 1; i < claves.length; i++) {
    const [c, x2, y2] = claves[i];
    if (f < c) break;
    const t = ap(f, c, dur, MUEVE);
    x = x + (x2 - x) * t;
    y = y + (y2 - y) * t;
  }
  return [x, y];
};

const Producto: React.FC<{ icono: React.ReactNode; nombre: string; prot: string; precio: string; apagado?: number; resalta?: number }> = ({
  icono,
  nombre,
  prot,
  precio,
  apagado = 0,
  resalta = 0,
}) => (
  <Tarjeta
    style={{
      position: "relative",
      width: 300,
      padding: "18px 22px",
      opacity: 1 - 0.55 * apagado,
      borderColor: resalta > 0.5 ? C.amarillo : C.tinta,
      borderWidth: 6 + 4 * resalta,
    }}
  >
    <svg width={110} height={110} viewBox="-70 -70 140 140" style={{ display: "block", margin: "0 auto" }}>
      {icono}
    </svg>
    <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 44, color: C.tinta, textAlign: "center" }}>{nombre}</div>
    <div
      style={{
        fontFamily: TITULO,
        fontWeight: 600,
        fontSize: 30,
        color: apagado > 0.5 ? C.rojo : C.tintaSuave,
        textAlign: "center",
        textDecoration: apagado > 0.5 ? "line-through" : "none",
      }}
    >
      {prot} de proteína
    </div>
    <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 32, color: C.tinta, textAlign: "center" }}>{precio} / 100 g</div>
  </Tarjeta>
);

const PASOS = [
  { nombre: "la oferta", hecho: "lentejas + arroz" },
  { nombre: "las metas", hecho: "región factible" },
  { nombre: "el óptimo", hecho: "$1.420 / sem" },
  { nombre: "precio sombra", hecho: "+$21 por g" },
  { nombre: "si no alcanza", hecho: "llega a 150 g" },
];

const Marcador: React.FC<{ f: number; en: number; inicio: number[]; hecho: number[] }> = ({ f, en, inicio, hecho }) => {
  const iconos = [
    <g key="o" transform="scale(0.32)">
      <g transform="translate(-50,0)">
        <Lentejas />
      </g>
      <g transform="translate(50,0)">
        <Arroz />
      </g>
    </g>,
    <g key="m">
      <path d="M-34,26 L26,-30 L40,-14 L-20,40 Z" fill={C.amarillo} stroke={C.tinta} strokeWidth={4} strokeLinejoin="round" />
      <line x1={-40} y1={-36} x2={40} y2={36} stroke={C.azul} strokeWidth={6} strokeLinecap="round" />
    </g>,
    <g key="e" transform="scale(0.75)">
      <Estrella r={40} />
    </g>,
    <text key="s" y={14} textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={42} fill={C.azul}>
      +$
    </text>,
    <g key="a" transform="scale(0.7)">
      <Alerta />
    </g>,
  ];
  return (
    <div style={{ position: "absolute", top: 362, left: 40, right: 40, display: "flex", justifyContent: "space-between" }}>
      {PASOS.map((p, i) => {
        const activo = f >= inicio[i] && f < inicio[i + 1];
        const listo = f >= hecho[i];
        return (
          <Pop key={p.nombre} en={en + i * 3} style={{ position: "relative" }} vol={0.12}>
            <div
              style={{
                width: 188,
                height: 146,
                borderRadius: 24,
                background: listo ? C.verdeClaro : C.papel,
                border: `5px solid ${activo ? C.amarillo : listo ? C.verde : C.tinta}`,
                boxShadow: activo ? `0 0 0 5px ${C.tinta}, ${SOMBRA}` : SOMBRA,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                transform: `scale(${activo ? 1.05 : 1})`,
                opacity: !activo && !listo ? 0.5 : 1,
              }}
            >
              <svg width={80} height={56} viewBox="-50 -42 100 84" style={{ overflow: "visible" }}>
                {iconos[i]}
              </svg>
              <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 25, color: C.tinta, whiteSpace: "nowrap" }}>
                {i + 1}. {p.nombre}
              </div>
              <div style={{ height: 30, fontFamily: TITULO, fontWeight: 700, fontSize: 23, color: C.verde, whiteSpace: "nowrap", display: "flex", alignItems: "center", gap: 5 }}>
                {listo && (
                  <>
                    <svg width={22} height={22} viewBox="-45 -45 90 90">
                      <Tilde r={40} />
                    </svg>
                    {p.hecho}
                  </>
                )}
              </div>
            </div>
          </Pop>
        );
      })}
    </div>
  );
};

export const E5Ejemplo: React.FC = () => {
  const f = useF();
  const fin = escena("e5").hasta;
  const k = {
    ejemplo: cuadro("x1"),
    fideos: cuadro("x1", "fideos"),
    lentejas: cuadro("x1", "lentejas"),
    arroz: cuadro("x1", "arroz"),
    baratos: cuadro("x2", "baratos"),
    casi: cuadro("x2", "casi"),
    arma: cuadro("x2", "arma"),
    eje: cuadro("x2", "eje"),
    punto: cuadro("x3"),
    compra: cuadro("x3", "compra"),
    pedimos: cuadro("x4"),
    kcal: cuadro("x4", "1.900"),
    franja: cuadro("x4", "franja"),
    p60: cuadro("x5", "60"),
    afuera: cuadro("x5", "afuera"),
    corto: cuadro("x5", "corto"),
    region: cuadro("x5", "región"),
    costo: cuadro("x6"),
    baja: cuadro("x6", "baja"),
    esquina: cuadro("x6", "esquina"),
    todo: cuadro("x6", "todo"),
    sombra: cuadro("x7"),
    sube: cuadro("x7", "sube"),
    gramo: cuadro("x7", "gramo"),
    p21: cuadro("x7", "$21"),
    p300: cuadro("x8", "300"),
    desaparece: cuadro("x8", "desaparece"),
    rompe: cuadro("x9"),
    p150: cuadro("x9", "150"),
    falta: cuadro("x9", "falta"),
  };
  const inicioPaso = [k.ejemplo, k.pedimos, k.costo, k.sombra, cuadro("x8"), fin + 100];
  const hechoPaso = [k.pedimos - 6, k.region + 12, k.todo, k.p21, k.falta];

  // --- Estado del plano
  const lleva300 = ap(f, k.p300 + 4, 44, MUEVE);
  const xm = 700 + 600 * lleva300;
  const masUno = f >= k.gramo && f < k.p300 ? ap(f, k.gramo, 18, MUEVE) : 0; // la meta pasa de 60 a 61 g
  const prot = 60 + masUno + 240 * lleva300;
  const px = (x: number, y: number): P => [OX + (x / xm) * AN, OY - (y / YMAX) * AL];
  const ejes = ap(f, k.eje - 4, 14, ENTRA);
  const energia = ap(f, k.kcal, 16, MUEVE);
  const lineaProt = ap(f, k.p60, 16, MUEVE);

  // Franja de energía (desde "franja"), lo que se queda corto (rojo, un momento) y la región factible (desde "región")
  const banda = recortar(recortar([[0, 0], [xm, 0], [xm, YMAX], [0, YMAX]], 3.5, 3.5, 1900), 3.5, 3.5, 2100, false);
  const muestraBanda = ap(f, k.franja, 10) * (1 - ap(f, k.region, 10));
  const cortos = recortar(banda, 0.25, 0.07, 60, false);
  const muestraCortos = ap(f, k.afuera, 10) * (1 - ap(f, k.region, 10));
  const region = recortar(banda, 0.25, 0.07, prot);
  const hayRegion = region.length >= 3;
  const muestraRegion = ap(f, k.region, 12);

  // La recta de costo baja hasta el vértice
  const [v60x, v60y] = vertice(60);
  const cIso = 2900 - (2900 - costo(v60x, v60y)) * ap(f, k.baja, 50, MUEVE);
  const muestraIso = f >= k.costo && f < k.p300;

  // El punto: una compra que recorre el plano
  const [vx, vy] = vertice(60 + masUno);
  const camino: [number, number, number][] = [
    [0, 300, 250],
    [k.compra - 10, 120, 640],
    [k.compra + 22, 430, 380],
    [k.franja, 260, 300], // dentro de la franja
    [k.corto - 8, 70, 480], // en la franja, pero corta de proteína
    [k.region, 260, 300],
    [k.baja, v60x, v60y], // baja junto con la recta de costo
    [k.rompe + 6, 600, 0], // lo máximo posible con 300 g
  ];
  let [dx, dy] = porClaves(f, camino, 26);
  if (f >= k.gramo && f < k.p300) [dx, dy] = [vx, vy];
  const enRegion = (x: number, y: number) => {
    const kc = 3.5 * (x + y);
    const okE = f < k.franja || (kc >= 1899 && kc <= 2101);
    const okP = f < k.p60 || proteina(x, y) >= prot - 0.5;
    return okE && okP;
  };
  const fase5 = f >= k.rompe;
  const okPunto = f >= k.p300 ? false : enRegion(dx, dy);
  const muestraPunto = f >= k.punto;

  // Cámara del plano: se acerca al óptimo para el precio sombra y vuelve para el pedido de 300 g
  const zoom = 1 + 0.35 * ap(f, k.sombra + 6, 18, MUEVE) * (1 - ap(f, k.p300 - 6, 16, MUEVE));
  const [VX, VY] = px(v60x, v60y);

  const linea = (s: [P, P] | null, color: string, prog: number, grosor = 8, punteada = false) => {
    if (!s || prog <= 0) return null;
    const [a, b] = s;
    const [x1, y1] = px(...a);
    const [x2, y2] = px(a[0] + (b[0] - a[0]) * prog, a[1] + (b[1] - a[1]) * prog);
    return <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={grosor} strokeLinecap="round" strokeDasharray={punteada ? "18 14" : undefined} />;
  };
  const poli = (pts: P[], color: string, op: number) =>
    pts.length >= 3 && op > 0 ? <polygon points={pts.map((p) => px(...p).join(",")).join(" ")} fill={color} fillOpacity={op} stroke="none" /> : null;

  // Las tarjetas de lentejas y arroz vuelan a los ejes
  const vuela = ap(f, k.arma, 22, MUEVE);
  const desvanece = ap(f, k.arma + 14, 10);
  const rojo300 = f >= k.p300;

  const prote = proteina(dx, dy);
  const cuesta = costo(dx, dy);

  return (
    <AbsoluteFill>
      <Fondo />
      <Marcador f={f} en={k.ejemplo + 4} inicio={inicioPaso} hecho={hechoPaso} />

      {/* ============ La oferta: las tres tarjetas; lentejas y arroz se vuelven los ejes ============ */}
      <Parte desde={k.ejemplo} hasta={k.arma + 24} mudo>
        {[
          { en: k.fideos, el: <Fideos />, n: "Fideos", p: "2 g", $: "$20", x: 45, destino: null as P | null },
          { en: k.lentejas, el: <Lentejas />, n: "Lentejas", p: "25 g", $: "$80", x: 390, destino: [OX + 160, OY + 70] as P },
          { en: k.arroz, el: <Arroz />, n: "Arroz", p: "7 g", $: "$25", x: 735, destino: [OX + 110, OY - AL - 26] as P },
        ].map((c, i) => {
          const sale = i === 0 ? ap(f, k.arma, 12, SALE) : 0;
          const cx = c.x + 150;
          const cy = 545 + 175;
          const tx = c.destino ? (c.destino[0] - cx) * vuela : 0;
          const ty = c.destino ? (c.destino[1] - cy) * vuela : sale * 120;
          const esc = c.destino ? 1 - 0.7 * vuela : 1;
          return (
            <div
              key={c.n}
              style={{
                position: "absolute",
                left: c.x,
                top: 545,
                width: 300,
                height: 350,
                transform: `translate(${tx}px,${ty}px) scale(${esc})`,
                opacity: i === 0 ? 1 - sale : 1 - desvanece,
              }}
            >
              <Pop en={c.en} style={{ left: 0, top: 0 }} desde="abajo">
                <Producto
                  icono={c.el}
                  nombre={c.n}
                  prot={c.p}
                  precio={c.$}
                  resalta={i === 0 ? ap(f, k.baratos, 8) : 0}
                  apagado={i === 0 ? ap(f, k.casi, 10) : 0}
                />
              </Pop>
            </div>
          );
        })}
        <Pop en={k.arroz + 8} sale={k.arma} style={{ top: 920, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
          <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 34, color: C.tintaSuave }}>los tres: 350 kcal cada 100 g</div>
        </Pop>
        <Lienzo>
          <AparecG en={k.ejemplo + 4} sale={k.arma}>
            <Stickman
              x={540}
              y={1235}
              escala={0.95}
              f={f}
              pose={poseEn(f, [[0, "parada"], [k.baratos, "señala"], [k.casi + 6, "piensa"]])}
              cara={f >= k.casi + 6 ? "pensando" : "feliz"}
              color={C.violeta}
              extras={["cola"]}
              semilla={3}
            />
          </AparecG>
        </Lienzo>
      </Parte>

      {/* ============ Lo que pedimos (izquierda) ============ */}
      <Parte desde={k.pedimos} hasta={k.sombra}>
        <Pop en={k.pedimos} style={{ top: 535, left: 50 }} desde="abajo">
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 36, color: C.tinta }}>Pedimos, por día</div>
        </Pop>
        <Pop en={k.kcal} style={{ top: 590, left: 50 }} desde="abajo">
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: TITULO, fontWeight: 600, fontSize: 30, color: C.tinta }}>
            <div style={{ width: 40, height: 9, borderRadius: 5, background: C.verde }} />
            energía: 1.900 a 2.100 kcal
          </div>
        </Pop>
        <Pop en={k.p60} style={{ top: 638, left: 50 }} desde="abajo">
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: TITULO, fontWeight: 600, fontSize: 30, color: C.tinta }}>
            <div style={{ width: 40, height: 9, borderRadius: 5, background: C.azul }} />
            proteína: 60 g o más
          </div>
        </Pop>
      </Parte>
      {/* El precio sombra, explicado (izquierda) */}
      <Parte desde={k.sombra + 8} hasta={k.p300 - 6}>
        <Pop en={k.sombra + 8} style={{ top: 530, left: 50 }} desde="abajo" sonido="brillo" vol={0.3}>
          <div style={{ width: 470, padding: "14px 22px", background: C.azulClaro, border: `5px solid ${C.azul}`, borderRadius: 24, boxSizing: "border-box" }}>
            <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 30, color: C.azul }}>Precio sombra</div>
            <div style={{ fontFamily: TITULO, fontWeight: 600, fontSize: 25, color: C.tinta, lineHeight: 1.12, opacity: ap(f, k.sube - 4, 10) }}>
              cuánto sube el costo si una meta pide un poco más
            </div>
            <div style={{ fontFamily: FORMULA, fontWeight: 700, fontSize: 27, color: C.azul, marginTop: 2, whiteSpace: "nowrap", opacity: ap(f, k.gramo, 10) }}>
              +1 g de proteína → +$21 / sem
            </div>
          </div>
        </Pop>
      </Parte>
      {/* Pedido de 300 g (izquierda) */}
      <Parte desde={k.p300 - 2} hasta={fin - 2} mudo>
        <Pop en={k.p300 - 2} style={{ top: 540, left: 50 }} desde="abajo">
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 36, color: C.tinta }}>Pedimos, por día</div>
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: TITULO, fontWeight: 600, fontSize: 30, color: C.tinta, marginTop: 8 }}>
            <div style={{ width: 40, height: 9, borderRadius: 5, background: C.verde }} />
            energía: 1.900 a 2.100 kcal
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: TITULO, fontWeight: 700, fontSize: 30, color: C.rojo, marginTop: 6 }}>
            <div style={{ width: 40, height: 9, borderRadius: 5, background: C.rojo }} />
            proteína: 300 g o más
          </div>
        </Pop>
      </Parte>

      {/* ============ Tu compra (derecha): la compra del punto, en vivo ============ */}
      <Parte desde={k.punto} hasta={fin - 2} mudo>
        <Pop en={k.punto} style={{ top: 530, left: 560 }} desde="abajo">
          <div
            style={{
              width: 480,
              padding: "12px 22px",
              background: C.papel,
              border: `6px solid ${okPunto ? C.verde : f >= k.franja ? C.rojo : C.tinta}`,
              borderRadius: 24,
              boxShadow: SOMBRA,
              boxSizing: "border-box",
              fontFamily: TITULO,
              color: C.tinta,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: 700, fontSize: 30 }}>Tu compra, por día</span>
              <span style={{ fontWeight: 700, fontSize: 26, color: okPunto ? C.verde : C.rojo }}>{f < k.franja ? "" : okPunto ? "cumple" : "no cumple"}</span>
            </div>
            <div style={{ fontWeight: 600, fontSize: 28 }}>
              {Math.round(dx)} g lentejas · {Math.round(dy)} g arroz
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, fontSize: fase5 ? 26 : 28, whiteSpace: "nowrap" }}>
              <span style={{ color: f >= k.p60 && prote < prot - 0.5 ? C.rojo : C.tinta }}>
                proteína {Math.round(prote)}
                {fase5 ? " de 300" : ""} g
              </span>
              {!fase5 && <span style={{ color: C.rojo }}>${miles(cuesta)} / sem</span>}
              {fase5 && f >= k.falta && <span style={{ color: C.rojo }}>falta la mitad</span>}
            </div>
          </div>
        </Pop>
        <Pop en={k.p21 - 2} sale={k.p300 - 6} style={{ top: 690, left: 860 }} sonido="caja" vol={0.3}>
          <div style={{ fontFamily: TITULO, fontWeight: 700, fontSize: 34, color: C.papel, background: C.azul, border: `5px solid ${C.tinta}`, borderRadius: 26, padding: "2px 18px" }}>
            +$21
          </div>
        </Pop>
      </Parte>

      {/* ============ El plano ============ */}
      <Parte desde={k.eje - 4} hasta={fin - 2} mudo>
        {/* recortado debajo de las tarjetas: con el zoom, el plano nunca se mete abajo de ellas */}
        <AbsoluteFill style={{ clipPath: "inset(708px 0 635px 0)" }}>
        <AbsoluteFill
          style={{
            transformOrigin: `${VX}px ${VY}px`,
            transform: `translate(${(420 - VX) * (1 - 1 / zoom)}px,${(960 - VY) * (1 - 1 / zoom)}px) scale(${zoom})`,
          }}
        >
          <Lienzo>
            <g opacity={ejes}>
              {poli(banda, C.verde, 0.22 * muestraBanda)}
              {poli(cortos, C.rojo, 0.3 * muestraCortos)}
              {hayRegion && poli(region, C.amarillo, 0.7 * muestraRegion)}
              <line x1={OX} y1={OY} x2={OX + AN + 20} y2={OY} stroke={C.tintaSuave} strokeWidth={5} />
              <line x1={OX} y1={OY} x2={OX} y2={OY - AL - 20} stroke={C.tintaSuave} strokeWidth={5} />
              {Array.from({ length: Math.floor(xm / 200) }, (_, i) => (i + 1) * 200).map((x) => {
                const [X] = px(x, 0);
                return (
                  <g key={x}>
                    <line x1={X} y1={OY} x2={X} y2={OY + 10} stroke={C.tintaSuave} strokeWidth={3} />
                    <text x={X} y={OY + 38} textAnchor="middle" fontFamily={TITULO} fontWeight={500} fontSize={24} fill={C.tintaSuave}>
                      {miles(x)}
                    </text>
                  </g>
                );
              })}
              {[300, 600, 900].map((y) => {
                const [, Y] = px(0, y);
                return (
                  <g key={y}>
                    <line x1={OX - 10} y1={Y} x2={OX} y2={Y} stroke={C.tintaSuave} strokeWidth={3} />
                    <text x={OX - 16} y={Y + 8} textAnchor="end" fontFamily={TITULO} fontWeight={500} fontSize={24} fill={C.tintaSuave}>
                      {y}
                    </text>
                  </g>
                );
              })}
            </g>
            {/* los nombres de los ejes aparecen cuando llegan las tarjetas */}
            <g opacity={ap(f, k.arma + 16, 8)}>
              <text x={OX} y={OY + 74} fontFamily={TITULO} fontWeight={700} fontSize={30} fill={C.tinta}>
                lentejas (g por día) →
              </text>
              <text x={OX - 10} y={OY - AL - 16} fontFamily={TITULO} fontWeight={700} fontSize={30} fill={C.tinta}>
                ↑ arroz (g por día)
              </text>
            </g>
            {/* restricciones: siempre por encima de las regiones */}
            {linea(segmento(3.5, 3.5, 1900, xm), C.verde, energia)}
            {linea(segmento(3.5, 3.5, 2100, xm), C.verde, energia)}
            {linea(segmento(0.25, 0.07, prot, xm), rojo300 ? C.rojo : C.azul, lineaProt, 8 + 4 * masUno)}
            {f >= k.afuera && f < k.region + 10 && (
              <PopG en={k.afuera + 4} x={px(250, 640)[0]} y={px(250, 640)[1]} sale={k.region} sonido={null}>
                <text fontFamily={TITULO} fontWeight={700} fontSize={28} fill={C.rojo}>
                  ← se queda corto
                </text>
              </PopG>
            )}
            {f >= k.region && f < k.costo + 10 && (
              <PopG en={k.region + 6} x={px(330, 330)[0]} y={px(330, 330)[1]} sale={k.costo} sonido={null}>
                <text fontFamily={TITULO} fontWeight={700} fontSize={32} fill={C.tinta}>
                  región factible
                </text>
              </PopG>
            )}
            {/* recta de costo */}
            {muestraIso && linea(segmento(5.6, 1.75, cIso, xm), C.rojo, ap(f, k.costo, 10), 6, true)}
            {/* el óptimo */}
            {f >= k.esquina && f < k.p300 && (
              <PopG en={k.esquina} x={px(vx, vy)[0]} y={px(vx, vy)[1]} sonido="ding" vol={0.35}>
                <circle r={36} fill="none" stroke={C.rojo} strokeWidth={6} />
              </PopG>
            )}
            {masUno > 0 && (
              <PopG en={k.gramo + 6} x={px(vx, vy)[0] + 34} y={px(vx, vy)[1] - 44} sonido={null}>
                <text fontFamily={TITULO} fontWeight={700} fontSize={26} fill={C.azul}>
                  +1 g de proteína
                </text>
              </PopG>
            )}
            {/* 300 g */}
            {!hayRegion && f >= k.desaparece && f < k.rompe && (
              <PopG en={k.desaparece} x={px(xm * 0.52, 560)[0]} y={px(xm * 0.52, 560)[1]} sonido="error" vol={0.3}>
                <text textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={34} fill={C.rojo}>
                  no queda región factible
                </text>
              </PopG>
            )}
            {f >= k.p150 - 4 && (
              <g>
                {linea(segmento(0.25, 0.07, 150, xm), C.azul, ap(f, k.p150 - 4, 12), 5, true)}
                <PopG en={k.p150 + 4} x={px(150, 780)[0] + 10} y={px(150, 780)[1]} sonido={null}>
                  <text fontFamily={TITULO} fontWeight={700} fontSize={28} fill={C.azul}>
                    150 g: lo máximo posible
                  </text>
                </PopG>
              </g>
            )}
            {f >= k.falta && (
              <g>
                <line x1={px(600, 0)[0]} y1={OY} x2={px(600 + 600 * ap(f, k.falta, 12, MUEVE), 0)[0]} y2={OY} stroke={C.rojo} strokeWidth={14} strokeLinecap="round" />
                <PopG en={k.falta + 8} x={px(900, 0)[0]} y={OY - 28} sonido={null}>
                  <text textAnchor="middle" fontFamily={TITULO} fontWeight={700} fontSize={30} fill={C.rojo}>
                    falta la mitad
                  </text>
                </PopG>
              </g>
            )}
            {/* el punto: la compra de "Tu compra" */}
            {muestraPunto && (
              <PopG en={k.punto} x={px(dx, dy)[0]} y={px(dx, dy)[1]} sonido="pop" vol={0.3}>
                <circle r={17} fill={okPunto ? C.verde : f >= k.franja ? C.rojo : C.tinta} stroke={C.tinta} strokeWidth={5} />
              </PopG>
            )}
          </Lienzo>
        </AbsoluteFill>
        </AbsoluteFill>
      </Parte>

      <Sfx en={k.arma} s="whoosh" vol={0.35} />
      <Sfx en={k.compra - 10} s="swish" vol={0.25} />
      <Sfx en={k.compra + 22} s="swish" vol={0.25} />
      <Sfx en={k.kcal} s="whoosh" vol={0.25} />
      <Sfx en={k.p60} s="whoosh" vol={0.25} />
      <Sfx en={k.corto - 8} s="error" vol={0.25} />
      <Sfx en={k.region} s="brillo" vol={0.3} />
      <Tics desde={k.baja} hasta={k.baja + 50} cada={4} vol={0.15} />
      <Sfx en={k.sombra + 6} s="zoom" vol={0.4} />
      <Sfx en={k.gramo} s="boing" vol={0.25} />
      <Sfx en={k.p300 - 6} s="swish" vol={0.35} />
      <Sfx en={k.p300 + 4} s="whoosh" vol={0.3} />
      <Sfx en={k.falta} s="error" vol={0.3} />
    </AbsoluteFill>
  );
};
