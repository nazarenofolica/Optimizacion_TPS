"use strict";

// Página de la canasta saludable. Todo corre en el navegador: los datos vienen comprimidos dentro de la página
// (canasta/exportar.py) y el cálculo lo hace motor.js en un Web Worker. La ubicación se busca con la API Georef
// (apis.datos.gob.ar), con el GPS del navegador o marcando el punto en el mapa.

const GEOREF = "https://apis.datos.gob.ar/georef/api";
const CLAVE_GUARDADO = "canasta-saludable-v2";

const $ = (sel, raiz = document) => raiz.querySelector(sel);
const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];
const fmt = (x, d = 0) => (x == null || Number.isNaN(x) ? "—"
  : Number(x).toLocaleString("es-AR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const pesos = (x, d = 2) => "$" + fmt(x, d);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const cuit = (c) => (/^\d{11}$/.test(c || "") ? `${c.slice(0, 2)}-${c.slice(2, 10)}-${c.slice(10)}` : c);

const COLORES = ["#2e6a4c", "#b5672a", "#4a78b8", "#a8483a", "#7a5ea8", "#2f8585", "#b8508f", "#6b7a2c"];
const COLOR_GRUPO = {
  "Verduras y frutas": "#3f8f4f",
  "Legumbres, cereales, papa, pan y pastas": "#b5832a",
  "Leche, yogur y queso": "#4a78b8",
  "Carnes y huevos": "#a8483a",
  "Aceites, frutas secas y semillas": "#7a6a2c",
  "Alimentos de consumo opcional": "#8a6d9e",
  "Agua e infusiones": "#2f7f9e",
};
// Grupos del paso 1. "Salud" suma, después de la hipertensión y la diabetes, las condiciones médicas (CONDICIONES):
// cambian metas, no filtran productos, y algunas requieren supervisión profesional.
const GRUPOS_RESTRICCIONES = [
  { titulo: "Dieta y religión", claves: ["celiaquia", "vegetariano", "vegano", "sin_lactosa", "sin_ultraprocesados",
    "sin_cerdo", "halal", "kosher"] },
  { titulo: "Alergias (también sin trazas)", alergia: true },
  { titulo: "Salud", claves: ["hipertension", "diabetes"], condiciones: true },
];
const PERSONA_NUEVA = { nombre: "", sexo: "F", edad: 34, peso_kg: 63, altura_cm: 163, actividad: "liviana",
  objetivo: "mantener", etapa: "general", trimestre: 2, restricciones: [] };

const estado = {
  P: null, perfiles: [], criterios: {}, condiciones: {}, hogar: [{ ...PERSONA_NUEVA }], actual: 0, lugar: null, dias: 7, listos: false, agua: null,
  promos: false, promosEnBase: 0,   // aplicar promociones (solo si la base trae alguna aplicable)
  caminata: null, listo: false, ocupado: false, resultado: null, vista: 0, mapa: null, marcador: null,
  mapaResultado: null, tiempos: new Map(), anterior: null, ultimaRuta: null,
  escalera: new Map(),   // minutos -> {resumen, resultado, rutas, pedido}: la mejor compra con cada límite de caminata
  pedido: null,          // el pedido con el que se armó estado.resultado (dosSuper necesita exactamente ese)
  dos: new WeakMap(),    // resultado -> {ds, rutas}: la compra en dos súper calculada sobre ese resultado
  vistaDos: false,       // el ticket muestra la compra en dos súper (si conviene) en lugar de la de uno
  capaDos: null, puntosMapa: null,
  delTexto: {},          // lo que el texto libre completó en los pasos 2 y 3 (dias, agua...), para marcarlo
};
const SIN_MOVIMIENTO = matchMedia("(prefers-reduced-motion: reduce)");
const PARAMETROS = new URLSearchParams(location.search);
// Un enlace con un caso (?perfiles=…&lat=…) arranca de los valores predeterminados más lo que trae: no mezcla nada
// guardado de una sesión anterior.
const CON_CASO = ["perfiles", "perfil", "lat", "lon", "dias", "listos", "agua", "caminata", "promos"]
  .some((k) => PARAMETROS.has(k));
// ?rutas=0 busca como antes (la más cercana de cada cadena, en línea recta): lo usa el test de paridad con Python.
const CON_RUTAS = PARAMETROS.get("rutas") !== "0";

// ============================================================
// Motor: Web Worker con el código de motor.js (o, si el navegador no lo permite, en esta misma página)
// ============================================================

const motor = (() => {
  let worker = null, siguiente = 0;
  const pendientes = new Map();
  function iniciar() {
    const fuente = $("#motor-codigo");
    if (!fuente) throw new Error("esta es la plantilla de la página, sin datos: abrí la exportada (python -m canasta)");
    const codigo = fuente.textContent;
    try {
      // ?motor=pagina lo corre en esta misma página (lo usan los tests: Chrome headless no espera a los workers).
      if (PARAMETROS.get("motor") === "pagina") throw new Error("motor en la página");
      worker = new Worker(URL.createObjectURL(new Blob([codigo], { type: "text/javascript" })));
      worker.onmessage = (e) => {
        const p = pendientes.get(e.data.id);
        if (!p) return;
        if (e.data.tipo === "avance") { p.avance(e.data); return; }
        pendientes.delete(e.data.id);
        if (e.data.tipo === "error") p.mal(new Error(e.data.mensaje)); else p.ok(e.data);
      };
      worker.onerror = (e) => {
        for (const p of pendientes.values()) p.mal(new Error(e.message || "El cálculo se interrumpió"));
        pendientes.clear();
      };
    } catch (err) {
      worker = null;
      const s = document.createElement("script");
      s.textContent = codigo;
      document.head.appendChild(s);
    }
  }
  function pedir(tipo, datos, avance = () => {}) {
    if (!worker) {
      const M = window.MotorCanasta;
      if (tipo === "paquete") return M.cargarPaquete(datos.meta, datos.binario).then((resumen) => ({ resumen }));
      if (tipo === "candidatas") return Promise.resolve({ candidatas: M.candidatasCaminando(datos.lat, datos.lon, datos.minutos) });
      if (tipo === "dos_super") return M.dosSuper(datos.pedido, datos.resultado, avance).then((dos_super) => ({ dos_super }));
      return M.armar(datos.pedido, avance).then((resultado) => ({ resultado }));
    }
    const id = ++siguiente;
    return new Promise((ok, mal) => {
      pendientes.set(id, { ok, mal, avance });
      worker.postMessage({ tipo, id, ...datos });
    });
  }
  return { iniciar, pedir };
})();

// ============================================================
// Guardado local (comodidad: si el navegador no deja, no pasa nada). La página siempre abre limpia; si hay una
// canasta guardada de antes, un aviso ofrece retomarla.
// ============================================================

let guardoEnEstaVisita = false;

function guardar() {
  try {
    localStorage.setItem(CLAVE_GUARDADO, JSON.stringify({ hogar: estado.hogar, lugar: estado.lugar, dias: estado.dias,
      listos: estado.listos, agua: estado.agua, caminata: estado.caminata, promos: estado.promos }));
    guardoEnEstaVisita = true;
  } catch (err) { /* sin almacenamiento */ }
}

// Lo guardado, ya validado, o null si no hay nada (o si es igual a como abre la página).
function leerGuardado() {
  try {
    const g = JSON.parse(localStorage.getItem(CLAVE_GUARDADO) || "null");
    if (!g || !Array.isArray(g.hogar) || !g.hogar.length) return null;
    const P = estado.P;
    const hogar = g.hogar.slice(0, P.PERSONAS_MAXIMAS).map((p) => ({ ...PERSONA_NUEVA, ...p,
      restricciones: Array.isArray(p.restricciones) ? p.restricciones.filter((r) => r in P.RESTRICCIONES) : [] }));
    const lugar = g.lugar && Number.isFinite(g.lugar.lat) && Number.isFinite(g.lugar.lon) ? g.lugar : null;
    const comoNueva = (p) => JSON.stringify(Object.keys(PERSONA_NUEVA).map((k) => p[k])) ===
      JSON.stringify(Object.values(PERSONA_NUEVA));
    if (!lugar && hogar.length === 1 && comoNueva(hogar[0])) return null;
    return { hogar, lugar, dias: String(g.dias) in P.DIAS_PERIODO ? Number(g.dias) : 7, listos: Boolean(g.listos),
      agua: g.agua in P.AGUA_MODOS ? g.agua : P.AGUA_MODO_PREDETERMINADO,
      caminata: P.CAMINATA_OPCIONES.includes(g.caminata) ? g.caminata : P.CAMINATA_MINUTOS,
      promos: estado.promosEnBase > 0 && g.promos !== false };
  } catch (err) {
    return null;   // sin almacenamiento o con algo ilegible
  }
}

function avisoRetomar(g) {
  const el = $("#retomar");
  const n = g.hogar.length;
  const quienes = n === 1 ? nombrePersona(g.hogar[0], 0) : `${n} personas`;
  const donde = g.lugar ? `, cerca de ${g.lugar.corto || g.lugar.nombre}` : "";
  $("#retomar-texto").innerHTML = `Tenés una canasta de la última vez: <b>${esc(quienes + donde)}</b>.`;
  el.hidden = false;
  $("#retomar-si").addEventListener("click", () => {
    Object.assign(estado, { hogar: g.hogar, actual: 0, lugar: g.lugar, dias: g.dias, listos: g.listos, agua: g.agua,
      caminata: g.caminata, promos: g.promos, anterior: null });
    estado.escalera.clear();
    el.hidden = true;
    sincronizarControles();
    guardar();
    $(".persona-boton").focus();
  }, { once: true });
  $("#retomar-no").addEventListener("click", () => {
    // Si en esta visita ya se guardó algo nuevo, lo de antes ya no está: no hay que borrar lo nuevo.
    if (!guardoEnEstaVisita) try { localStorage.removeItem(CLAVE_GUARDADO); } catch (err) { /* sin almacenamiento */ }
    el.hidden = true;
    const primero = $("[data-perfil]");
    if (primero) primero.focus();
  }, { once: true });
}

// Después de cambiar el estado entero (al retomar lo guardado), cada control vuelve a mostrar lo que hay.
function sincronizarControles() {
  $$('[name="caminata"]').forEach((c) => { c.checked = Number(c.value) === estado.caminata; });
  $$('[name="dias"]').forEach((c) => { c.checked = Number(c.value) === estado.dias; });
  $$('[name="agua"]').forEach((c) => { c.checked = c.value === estado.agua; });
  $("#listos").checked = estado.listos;
  $("#promos").checked = estado.promos;
  if (estado.lugar) elegirLugar(estado.lugar, true, false);
  cargarEditor();
  dibujarPersonas();
}

// ============================================================
// Hogar
// ============================================================

const nombrePersona = (p, i) => (p.nombre || "").trim() || `Persona ${i + 1}`;
const colorDe = (i) => COLORES[i % COLORES.length];
const form = () => $("#formulario").elements;

function resumenPersona(p) {
  const partes = [`${p.edad || "?"} años`];
  if (p.etapa === "embarazo") partes.push("embarazo");
  if (p.etapa === "lactancia") partes.push("lactancia");
  const r = p.restricciones.map((k) => estado.P.RESTRICCIONES[k]);
  if (r.length) partes.push(r.length > 1 ? `${r.length} restricciones` : r[0].replace(/^Alergia (al|a la|a) /, "sin "));
  return partes.join(", ");
}

function erroresPersona(p) {
  const P = estado.P, e = [];
  // Sexo y trimestre vacíos solo llegan del texto libre, cuando el texto no los dice: se piden, no se adivinan.
  if (p.sexo !== "F" && p.sexo !== "M") e.push("Elegí el sexo biológico.");
  if (!(p.edad >= P.EDAD_MINIMA && p.edad <= P.EDAD_MAXIMA)) {
    e.push(`La edad tiene que estar entre ${P.EDAD_MINIMA} y ${P.EDAD_MAXIMA} años (antes de los ${P.EDAD_MINIMA}, la alimentación la indica el pediatra).`);
  }
  if (!(p.peso_kg >= P.PESO_RANGO_KG[0] && p.peso_kg <= P.PESO_RANGO_KG[1])) e.push("Revisá el peso.");
  if (p.altura_cm != null && !(p.altura_cm >= P.ALTURA_RANGO_CM[0] && p.altura_cm <= P.ALTURA_RANGO_CM[1])) e.push("Revisá la altura.");
  if (p.etapa === "embarazo" && !(String(p.trimestre) in P.ENERGIA_EMBARAZO)) e.push("Elegí el trimestre del embarazo.");
  return e;
}

function dibujarPersonas() {
  $("#personas").innerHTML = estado.hogar.map((p, i) => `
    <div class="persona ${i === estado.actual ? "activa" : ""}" style="--c:${colorDe(i)}">
      <button type="button" class="persona-boton" role="tab" aria-selected="${i === estado.actual}" aria-controls="editor" data-i="${i}">
        <span class="inicial" aria-hidden="true">${esc(nombrePersona(p, i)[0].toUpperCase())}</span>
        <span><b>${esc(nombrePersona(p, i))}</b><small>${esc(resumenPersona(p))}</small></span>
      </button>
      ${estado.hogar.length > 1 ? `<button type="button" class="quitar" data-quitar="${i}" aria-label="Quitar a ${esc(nombrePersona(p, i))}">×</button>` : ""}
    </div>`).join("");
  $("#agregar-persona").hidden = estado.hogar.length >= estado.P.PERSONAS_MAXIMAS;
  const quienes = estado.hogar.length === 1 ? "1 persona" : `${estado.hogar.length} personas`;
  const periodo = estado.P.DIAS_PERIODO[estado.dias];
  const caminata = CON_RUTAS && estado.caminata ? `, hasta ${estado.caminata} min caminando` : "";
  $("#resumen-hogar").textContent = estado.lugar
    ? `${quienes}, compra para ${periodo}, cerca de ${estado.lugar.corto || estado.lugar.nombre}${caminata}.`
    : `${quienes}, compra para ${periodo}. Falta elegir dónde comprás.`;
  marcarPasos();
  marcarDelTexto();
}

// Las pestañas de los pasos: cada una se marca completa cuando tiene lo necesario y muestra un resumen corto.
function marcarPasos() {
  const listo = { hogar: estado.hogar.every((p) => !erroresPersona(p).length), ubicacion: Boolean(estado.lugar), compra: true };
  $$(".avance-pasos [data-paso]").forEach((b) => b.classList.toggle("completo", listo[b.dataset.paso]));
  // "Armar la canasta" solo se habilita con el hogar válido y el lugar elegido (evita armarla por un clic de más).
  const boton = $("#armar"), puede = listo.hogar && listo.ubicacion;
  if (!estado.ocupado) boton.disabled = !puede;
  boton.title = puede ? "" : !listo.hogar ? "Completá los datos de cada persona (paso 1)" : "Elegí dónde comprás (paso 2)";
  const n = estado.hogar.length;
  $("#sub-hogar").textContent = n === 1 ? nombrePersona(estado.hogar[0], 0) : `${n} personas`;
  $("#sub-ubicacion").textContent = estado.lugar
    ? `${estado.lugar.corto || estado.lugar.nombre}${CON_RUTAS && estado.caminata ? `, ${estado.caminata} min` : ""}` : "Falta elegir";
  $("#sub-compra").textContent = estado.P.DIAS_PERIODO[estado.dias] + (estado.listos ? ", listo para comer" : "")
    + `, ${estado.P.AGUA_MODOS[estado.agua].corto}` + (estado.promosEnBase && !estado.promos ? ", sin promociones" : "");
}

const PASOS = ["hogar", "ubicacion", "compra"];
let pasoActual = "hogar";

// Un paso a la vez; la animación sale hacia el lado en el que se avanza.
function irAPaso(paso, enfocar = false) {
  const desde = PASOS.indexOf(pasoActual), hasta = PASOS.indexOf(paso);
  pasoActual = paso;
  $$(".avance-pasos [data-paso]").forEach((b) => {
    const activo = b.dataset.paso === paso;
    b.setAttribute("aria-selected", String(activo));
    b.tabIndex = activo ? 0 : -1;
  });
  $$(".paso[data-panel]").forEach((s) => {
    const activo = s.dataset.panel === paso;
    s.hidden = !activo;
    if (activo) s.dataset.desde = hasta >= desde ? "derecha" : "izquierda";
  });
  $("#anterior").hidden = hasta === 0;
  $("#siguiente").hidden = hasta === PASOS.length - 1;
  if (paso === "ubicacion" && estado.mapa) {
    // El mapa se creó oculto: al mostrarlo recalcula su tamaño y vuelve a centrarse.
    requestAnimationFrame(() => {
      estado.mapa.invalidateSize();
      if (estado.lugar) estado.mapa.setView([estado.lugar.lat, estado.lugar.lon], estado.lugar.precision === "localidad" ? 13 : 15, { animate: false });
    });
  }
  if (enfocar) $(`.avance-pasos [data-paso="${paso}"]`).focus();
}

function prepararPasos() {
  $(".avance-pasos").addEventListener("click", (e) => {
    const b = e.target.closest("[data-paso]");
    if (b) irAPaso(b.dataset.paso);
  });
  $(".avance-pasos").addEventListener("keydown", (e) => {
    const i = PASOS.indexOf(pasoActual);
    if (e.key === "ArrowRight" && i < PASOS.length - 1) irAPaso(PASOS[i + 1], true);
    if (e.key === "ArrowLeft" && i > 0) irAPaso(PASOS[i - 1], true);
  });
  $("#siguiente").addEventListener("click", () => irAPaso(PASOS[Math.min(PASOS.indexOf(pasoActual) + 1, PASOS.length - 1)]));
  $("#anterior").addEventListener("click", () => irAPaso(PASOS[Math.max(PASOS.indexOf(pasoActual) - 1, 0)]));
  irAPaso("hogar");
}

function cargarEditor() {
  const p = estado.hogar[estado.actual];
  $("#p-nombre").value = p.nombre;
  $$('[name="p-sexo"]').forEach((c) => { c.checked = c.value === p.sexo; });
  $("#p-edad").value = p.edad ?? "";
  $("#p-peso").value = p.peso_kg ?? "";
  $("#p-altura").value = p.altura_cm ?? "";
  form()["p-etapa"].value = p.etapa;
  const trimestre = p.trimestre === null ? "" : String(p.trimestre || 2);    // null: del texto, sin decirlo
  $$('[name="p-trimestre"]').forEach((c) => { c.checked = c.value === trimestre; });
  form()["p-actividad"].value = p.actividad;
  form()["p-objetivo"].value = p.objetivo;
  $$('[name="p-restriccion"]').forEach((c) => { c.checked = p.restricciones.includes(c.value); });
  actualizarVisibles();
  marcarPerfil();
}

function leerEditor() {
  const p = estado.hogar[estado.actual];
  const numero = (v) => (v === "" ? null : Number(v));
  p.nombre = $("#p-nombre").value;
  p.sexo = form()["p-sexo"].value;
  p.edad = numero($("#p-edad").value);
  p.peso_kg = numero($("#p-peso").value);
  p.altura_cm = numero($("#p-altura").value);
  p.etapa = form()["p-etapa"].value;
  p.trimestre = Number(form()["p-trimestre"].value) || null;
  p.actividad = form()["p-actividad"].value;
  p.objetivo = form()["p-objetivo"].value;
  p.restricciones = $$('[name="p-restriccion"]:checked').map((c) => c.value);
}

function actualizarVisibles() {
  const p = estado.hogar[estado.actual];
  const puedeEtapa = p.sexo === "F" && p.edad >= 14 && p.edad <= 50;
  $("#campo-etapa").hidden = !puedeEtapa;
  if (!puedeEtapa && p.etapa !== "general") { p.etapa = "general"; form()["p-etapa"].value = "general"; }
  $(".trimestre").hidden = p.etapa !== "embarazo";
  $("#campo-objetivo").hidden = p.edad < 18 || p.etapa !== "general";
  const act = estado.P.ACTIVIDAD[p.actividad];
  $("#actividad-desc").textContent = act ? act.descripcion : "";
  $("#errores-persona").textContent = erroresPersona(p).join(" ");
  // Las condiciones elegidas que requieren supervisión muestran su aviso ahí mismo, antes de calcular.
  const sup = p.restricciones.filter((r) => estado.condiciones[r] && estado.condiciones[r].supervision);
  $(".avisos-supervision").innerHTML = sup.map((r) => `<p class="aviso-supervision"><i aria-hidden="true">!</i>` +
    `<span><b>${esc(estado.P.RESTRICCIONES[r])}: requiere supervisión profesional.</b> ${esc(estado.condiciones[r].aviso)}</span></p>`).join("");
}

function alCambiarEditor(e) {
  if (e.target.name === "p-restriccion" && e.target.checked) {
    if (e.target.value === "vegano") $('[name="p-restriccion"][value="vegetariano"]').checked = false;
    if (e.target.value === "vegetariano") $('[name="p-restriccion"][value="vegano"]').checked = false;
  }
  leerEditor();
  actualizarVisibles();
  marcarPerfil();
  dibujarPersonas();
  guardar();
}

// Los datos de una persona tal como los carga un perfil de ejemplo (el nombre va aparte).
const datosDePerfil = (f) => ({ sexo: f.sexo, edad: f.edad, peso_kg: f.peso_kg, altura_cm: f.altura_cm,
  actividad: f.actividad, objetivo: f.objetivo, etapa: f.etapa, trimestre: f.trimestre || 2, restricciones: [...f.restricciones] });

// ¿La persona sigue teniendo exactamente los datos del perfil que cargó? El nombre no cuenta.
function sigueIgual(p, f) {
  const d = datosDePerfil(f), lista = (r) => [...r].sort().join("|");
  return ["sexo", "edad", "peso_kg", "altura_cm", "actividad", "objetivo", "etapa"].every((k) => (p[k] ?? null) === (d[k] ?? null))
    && (p.etapa !== "embarazo" || p.trimestre === d.trimestre) && lista(p.restricciones) === lista(d.restricciones);
}

// El perfil de la persona que se está editando queda marcado; si se cambió algún dato, dice "con cambios".
function marcarPerfil() {
  const p = estado.hogar[estado.actual];
  const f = p.perfil ? estado.perfiles.find((x) => x.id === p.perfil) : null;
  const igual = Boolean(f) && sigueIgual(p, f);
  $$("[data-perfil]").forEach((b) => {
    const suyo = Boolean(f) && b.dataset.perfil === f.id;
    b.setAttribute("aria-pressed", String(suyo && igual));
    b.classList.toggle("con-cambios", suyo && !igual);
    $(".perfil-cambios", b).hidden = !(suyo && !igual);
  });
  $("#perfil-estado").textContent = !f ? ""
    : igual ? `Cargaste el perfil ${f.nombre}. Podés cambiar cualquier dato.`
    : `Basado en el perfil ${f.nombre}, con cambios. Tocalo de nuevo para volver a sus datos.`;
}

function cargarPerfil(id) {
  const f = estado.perfiles.find((x) => x.id === id);
  if (!f) return;
  const p = estado.hogar[estado.actual];
  const anterior = p.perfil ? estado.perfiles.find((x) => x.id === p.perfil) : null;
  // El nombre se reemplaza solo si estaba vacío o era el del perfil anterior: no pisa uno escrito a mano.
  if (!p.nombre.trim() || (anterior && p.nombre === anterior.nombre)) p.nombre = f.nombre;
  Object.assign(p, datosDePerfil(f), { perfil: f.id });
  cargarEditor();
  dibujarPersonas();
  guardar();
}

function prepararHogar() {
  const P = estado.P;
  $("#perfiles-ejemplo").innerHTML = estado.perfiles.filter((f) => f.visible).map((f) =>
    `<button type="button" class="perfil" data-perfil="${esc(f.id)}" aria-pressed="false">
      <b>${esc(f.nombre)}<span class="perfil-cambios" hidden>con cambios</span></b><small>${esc(f.descripcion)}</small></button>`).join("");
  $("#perfiles-ejemplo").addEventListener("click", (e) => {
    const b = e.target.closest("[data-perfil]");
    if (b) cargarPerfil(b.dataset.perfil);
  });
  $("#actividades").innerHTML = Object.entries(P.ACTIVIDAD).map(([clave, a], i) =>
    `<label><input type="radio" name="p-actividad" value="${clave}"><span style="--nivel:${i + 1}">${esc(a.nombre)}</span></label>`).join("");
  $("#objetivos").innerHTML = Object.entries(P.OBJETIVO).map(([clave, o]) =>
    `<label><input type="radio" name="p-objetivo" value="${clave}"><span>${esc(o.nombre)}</span></label>`).join("");
  $("#restricciones").innerHTML = GRUPOS_RESTRICCIONES.map((g) => {
    const claves = g.alergia ? Object.keys(P.ALERGIAS) : g.claves.concat(g.condiciones ? P.CONDICIONES : []);
    const nombre = (k) => P.RESTRICCIONES[k].replace(/^Alergia (al|a la|a) /, "");
    const supervision = (k) => Boolean(estado.condiciones[k] && estado.condiciones[k].supervision);
    const chips = claves.map((k) => `<label class="chip"><input type="checkbox" name="p-restriccion" value="${k}"><span>` +
      `${esc(nombre(k))}${supervision(k) ? '<b class="chip-marca" title="Requiere supervisión profesional">con supervisión</b>' : ""}` +
      "</span></label>").join("");
    const criterios = claves.map((k) => `<dt>${esc(P.RESTRICCIONES[k])}</dt><dd>${esc(estado.criterios[k] || "")}</dd>`).join("");
    return `<div class="grupo-restricciones"><h3>${esc(g.titulo)}</h3><div class="chips">${chips}</div>
      ${g.condiciones ? '<div class="avisos-supervision" aria-live="polite"></div>' : ""}
      <details class="criterios-grupo"><summary>Qué exige cada una</summary><dl>${criterios}</dl></details></div>`;
  }).join("");

  $("#personas").addEventListener("click", (e) => {
    const quitar = e.target.closest("[data-quitar]");
    if (quitar) {
      estado.hogar.splice(Number(quitar.dataset.quitar), 1);
      estado.actual = Math.min(estado.actual, estado.hogar.length - 1);
    } else {
      const b = e.target.closest("[data-i]");
      if (!b) return;
      estado.actual = Number(b.dataset.i);
    }
    cargarEditor();
    dibujarPersonas();
    guardar();
  });
  $("#agregar-persona").addEventListener("click", () => {
    estado.hogar.push({ ...PERSONA_NUEVA, restricciones: [] });
    estado.actual = estado.hogar.length - 1;
    cargarEditor();
    dibujarPersonas();
    guardar();
    $("[data-perfil]")?.focus();
  });
  $("#editor").addEventListener("input", alCambiarEditor);
  $("#editor").addEventListener("change", alCambiarEditor);
}

// ============================================================
// Ubicación: Georef, GPS y mapa
// ============================================================

function mostrarLugar(texto, error = false) {
  const el = $("#ubicacion-elegida");
  el.textContent = texto;
  el.classList.toggle("error", error);
}

function elegirLugar(lugar, mover = true, guardarlo = true) {
  estado.lugar = lugar;
  mostrarLugar(`Comprás cerca de: ${lugar.nombre}`);
  $("#lugares").innerHTML = "";
  if (estado.mapa) {
    const punto = [lugar.lat, lugar.lon];
    if (!estado.marcador) {
      estado.marcador = L.marker(punto, { draggable: true, keyboard: true, title: "Dónde comprás" }).addTo(estado.mapa);
      estado.marcador.on("dragend", () => { const ll = estado.marcador.getLatLng(); puntoDelMapa(ll.lat, ll.lng); });
    } else {
      estado.marcador.setLatLng(punto);
    }
    if (mover) estado.mapa.setView(punto, lugar.precision === "localidad" ? 13 : 15);
  }
  dibujarPersonas();
  if (guardarlo) guardar();
}

async function georef(recurso, params) {
  const r = await fetch(`${GEOREF}/${recurso}?${new URLSearchParams(params)}`);
  if (!r.ok) throw new Error(`Georef respondió ${r.status}`);
  return r.json();
}

// Nombre del lugar donde cae un punto (para mostrarlo después de usar el GPS o el mapa).
async function nombreDelPunto(lat, lon) {
  try {
    const u = (await georef("ubicacion", { lat, lon })).ubicacion || {};
    return [u.municipio && u.municipio.nombre, u.departamento && u.departamento.nombre, u.provincia && u.provincia.nombre]
      .filter((v, i, a) => v && a.indexOf(v) === i).join(", ");
  } catch (err) {
    return "";
  }
}

async function puntoDelMapa(lat, lon, origen = "el punto marcado en el mapa") {
  elegirLugar({ lat, lon, nombre: origen, precision: "punto" }, false);
  const nombre = await nombreDelPunto(lat, lon);
  if (nombre && estado.lugar && estado.lugar.lat === lat && estado.lugar.lon === lon) {
    elegirLugar({ lat, lon, nombre: `${origen} (${nombre})`, corto: nombre, precision: "punto" }, false);
  }
}

async function buscarLugar() {
  const q = $("#busqueda").value.trim();
  const provincia = $("#provincia").value;
  const lista = $("#lugares");
  if (!q) { lista.innerHTML = "<p>Escribí una dirección (calle y altura) o una localidad.</p>"; return; }
  const coord = q.match(/^\s*(-?\d{1,2}(?:[.,]\d+)?)\s*[,;\s]\s*(-?\d{1,3}(?:[.,]\d+)?)\s*$/);
  if (coord) {
    const lat = Number(coord[1].replace(",", ".")), lon = Number(coord[2].replace(",", "."));
    const [la0, la1] = estado.P.LAT_ARGENTINA, [lo0, lo1] = estado.P.LON_ARGENTINA;
    if (lat >= la0 && lat <= la1 && lon >= lo0 && lon <= lo1) {
      await puntoDelMapa(lat, lon, "las coordenadas ingresadas");
      if (estado.mapa) estado.mapa.setView([lat, lon], 15);
      return;
    }
    lista.innerHTML = "<p>Esas coordenadas no caen en la Argentina.</p>";
    return;
  }
  lista.innerHTML = "<p>Buscando…</p>";
  const [calle, ...resto] = q.split(",").map((s) => s.trim());
  const localidad = resto.join(" ").trim();
  const filtro = provincia ? { provincia } : {};
  const pedidos = [];
  if (/\d/.test(calle)) {
    pedidos.push(georef("direcciones", { direccion: calle, max: 5, ...filtro, ...(localidad ? { localidad } : {}) })
      .then((j) => (j.direcciones || []).filter((d) => d.ubicacion && d.ubicacion.lat != null).map((d) => ({
        nombre: d.nomenclatura, lat: d.ubicacion.lat, lon: d.ubicacion.lon, precision: "dirección",
        corto: d.localidad_censal ? d.localidad_censal.nombre : "" }))));
  }
  pedidos.push(georef("localidades", { nombre: localidad || calle, max: 5, ...filtro })
    .then((j) => (j.localidades || []).map((l) => ({
      nombre: [l.nombre, l.departamento && l.departamento.nombre, l.provincia && l.provincia.nombre]
        .filter((v, i, a) => v && a.indexOf(v) === i).join(", "), lat: l.centroide.lat, lon: l.centroide.lon,
      precision: "localidad", corto: l.nombre }))));
  const respuestas = await Promise.allSettled(pedidos);
  const lugares = respuestas.filter((r) => r.status === "fulfilled").flatMap((r) => r.value);
  if (!lugares.length) {
    lista.innerHTML = respuestas.every((r) => r.status === "rejected")
      ? "<p>No se pudo consultar el buscador de direcciones (Georef). Revisá la conexión o marcá el punto en el mapa.</p>"
      : "<p>No encontramos ese lugar. Probá con calle y altura (por ejemplo, Corrientes 1234), agregá la localidad después de una coma o elegí la provincia.</p>";
    return;
  }
  lista.innerHTML = lugares.slice(0, 8).map((l, i) =>
    `<button type="button" data-i="${i}">${esc(l.nombre)}<small>${l.precision === "localidad" ? "centro de la localidad" : "dirección exacta"}</small></button>`).join("");
  lista.onclick = (e) => { const b = e.target.closest("button"); if (b) elegirLugar(lugares[Number(b.dataset.i)]); };
}

function usarMiUbicacion() {
  if (!navigator.geolocation) { mostrarLugar("Este navegador no comparte la ubicación: buscá la dirección o marcá el punto en el mapa.", true); return; }
  if (!window.isSecureContext) { mostrarLugar("El navegador solo comparte la ubicación en páginas seguras: buscá la dirección o marcá el punto en el mapa.", true); return; }
  mostrarLugar("Buscando tu ubicación…");
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      await puntoDelMapa(pos.coords.latitude, pos.coords.longitude, `tu ubicación actual (±${fmt(pos.coords.accuracy)} m)`);
      if (estado.mapa) estado.mapa.setView([pos.coords.latitude, pos.coords.longitude], 15);
    },
    (err) => {
      const motivo = err.code === 1
        ? "No hay permiso para usar tu ubicación (o esta página está dentro de otra que no lo permite)."
        : err.code === 3 ? "Tu ubicación tardó demasiado en llegar." : "No se pudo obtener tu ubicación.";
      mostrarLugar(`${motivo} Buscá la dirección o marcá el punto en el mapa.`, true);
    },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 300000 });
}

function prepararUbicacion() {
  $("#provincia").innerHTML = `<option value="">Cualquiera</option>` + [
    "Ciudad Autónoma de Buenos Aires", "Buenos Aires", "Catamarca", "Chaco", "Chubut", "Córdoba", "Corrientes", "Entre Ríos",
    "Formosa", "Jujuy", "La Pampa", "La Rioja", "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta", "San Juan", "San Luis",
    "Santa Cruz", "Santa Fe", "Santiago del Estero", "Tierra del Fuego, Antártida e Islas del Atlántico Sur", "Tucumán",
  ].map((p) => `<option>${esc(p)}</option>`).join("");
  $("#buscar").addEventListener("click", buscarLugar);
  $("#busqueda").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); buscarLugar(); } });
  $("#mi-ubicacion").addEventListener("click", usarMiUbicacion);
  if (typeof L === "undefined") {
    $("#mapa-ubicacion").hidden = true;
    $("#ayuda-mapa").hidden = true;
  } else {
    estado.mapa = L.map("mapa-ubicacion", { scrollWheelZoom: false }).setView([-38.4, -63.6], 4);
    capaBase().addTo(estado.mapa);
    estado.mapa.on("click", (e) => puntoDelMapa(e.latlng.lat, e.latlng.lng));
    // El panel puede cambiar de tamaño (columna sticky, móvil): Leaflet necesita recalcular el suyo.
    if (window.ResizeObserver) new ResizeObserver(() => estado.mapa.invalidateSize()).observe($("#mapa-ubicacion"));
  }
  $("#caminatas").innerHTML = estado.P.CAMINATA_OPCIONES.map((m) =>
    `<label><input type="radio" name="caminata" value="${m}" ${m === estado.caminata ? "checked" : ""}><span>${m} min</span></label>`).join("");
  $("#caminatas").addEventListener("change", (e) => { estado.caminata = Number(e.target.value); estado.anterior = null; dibujarPersonas(); guardar(); });
  if (estado.lugar) elegirLugar(estado.lugar, true, false);   // el lugar del enlace no se guarda hasta que se toque algo
}

// Teselas de OpenStreetMap (la URL actual, sin subdominios). Desde file:// pueden no cargar porque OSM exige el
// encabezado Referer: python -m canasta sirve la página en http://localhost.
// className (TileLayer, Leaflet 1.9): con el tema oscuro, el CSS oscurece solo las teselas; los marcadores y el
// recorrido quedan con sus colores.
function capaBase() {
  return L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, className: "capa-base", attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  });
}

// ============================================================
// Opciones de la compra
// ============================================================

function prepararCompra() {
  $("#periodos").innerHTML = Object.entries(estado.P.DIAS_PERIODO).map(([dias, nombre]) =>
    `<label><input type="radio" name="dias" value="${dias}" ${Number(dias) === estado.dias ? "checked" : ""}><span>${esc(nombre[0].toUpperCase() + nombre.slice(1))}</span></label>`).join("");
  $("#periodos").addEventListener("change", (e) => { estado.dias = Number(e.target.value); dibujarPersonas(); guardar(); });
  $("#listos").checked = estado.listos;
  $("#listos").addEventListener("change", (e) => { estado.listos = e.target.checked; dibujarPersonas(); guardar(); });
  $("#aguas").innerHTML = Object.entries(estado.P.AGUA_MODOS).map(([clave, m]) =>
    `<label><input type="radio" name="agua" value="${clave}" ${clave === estado.agua ? "checked" : ""}>
      <span><b>${esc(m.nombre)}</b><small>${esc(m.descripcion)}</small></span></label>`).join("");
  $("#aguas").addEventListener("change", (e) => { estado.agua = e.target.value; dibujarPersonas(); guardar(); });
  // Promociones: si la base de hoy no trae ninguna que se pueda aplicar, la casilla queda apagada y lo dice.
  const promos = $("#promos");
  promos.checked = estado.promos;
  promos.disabled = !estado.promosEnBase;
  if (!estado.promosEnBase) {
    $("#promos-ayuda").textContent = "Los precios de hoy no traen promociones que se puedan aplicar sin banco ni "
      + "tarjeta: el total va a precio de lista.";
  }
  promos.addEventListener("change", (e) => { estado.promos = e.target.checked; dibujarPersonas(); guardar(); });
}

// ============================================================
// Contalo con tus palabras (etapa 6): el servidor local (python -m canasta) le pasa el texto a Groq y devuelve el
// pedido ya validado (canasta/llm.py). Acá solo se prellena el formulario: nada se calcula hasta "Armar la canasta".
// La clave nunca llega a la página; sin servidor (la página publicada, o abierta como archivo) el bloque no aparece.
// ============================================================

const CAMPOS_TEXTO = ["nombre", "sexo", "edad", "peso_kg", "altura_cm", "actividad", "objetivo", "etapa", "trimestre"];
// Dónde va la marca "del texto" de cada campo (la etiqueta del control).
const ETIQUETA_TEXTO = {
  nombre: () => $("#p-nombre").closest(".campo").querySelector(".etiqueta"),
  sexo: () => $("#l-sexo"),
  edad: () => $("#p-edad").closest(".campo").querySelector(".etiqueta"),
  peso_kg: () => $("#p-peso").closest(".campo").querySelector(".etiqueta"),
  altura_cm: () => $("#p-altura").closest(".campo").querySelector(".etiqueta"),
  etapa: () => $("#l-etapa"),
  actividad: () => $("#l-actividad"),
  objetivo: () => $("#l-objetivo"),
  restricciones: () => $("#l-restricciones"),
  dias: () => $("#l-periodo"),
  agua: () => $("#l-agua"),
  listos: () => $("#listos").closest("label").querySelector("b"),
  promos: () => $("#promos").closest("label").querySelector("b"),
  caminata_minutos: () => $("#l-caminata"),
};
const valorHogar = { dias: () => estado.dias, agua: () => estado.agua, listos: () => estado.listos,
  promos: () => estado.promos, caminata_minutos: () => estado.caminata };
const mismaLista = (a, b) => [...a].sort().join("|") === [...b].sort().join("|");

// Cada campo que vino del texto y sigue con ese valor lleva la marca; si la persona lo cambia, la marca se va.
function marcarDelTexto() {
  if (!estado.P) return;
  const p = estado.hogar[estado.actual] || {};
  const del = p.del_texto || {}, hogar = estado.delTexto || {};
  for (const [campo, etiqueta] of Object.entries(ETIQUETA_TEXTO)) {
    const el = etiqueta();
    if (!el) continue;
    let marca = el.querySelector(".del-texto");
    let vino;
    if (campo in valorHogar) vino = campo in hogar && hogar[campo] === valorHogar[campo]();
    else if (campo === "etapa") vino = "etapa" in del && del.etapa === p.etapa && (p.etapa !== "embarazo" || del.trimestre === p.trimestre);
    else if (campo === "restricciones") vino = "restricciones" in del && mismaLista(del.restricciones, p.restricciones);
    else vino = campo in del && del[campo] === p[campo];
    if (vino && !marca) {
      marca = document.createElement("span");
      marca.className = "del-texto";
      marca.textContent = "del texto";
      marca.title = "Lo completamos con tu texto: revisalo";
      el.appendChild(marca);
    }
    if (marca) marca.hidden = !vino;
  }
}

// Las personas del pedido validado, para el formulario. Lo obligatorio que el texto no dijo queda vacío (el formulario
// lo pide); lo opcional, con el valor de siempre del formulario y sin marca.
function personaDelTexto(x) {
  const p = { ...PERSONA_NUEVA, nombre: x.nombre || "", sexo: "", edad: null, peso_kg: null, altura_cm: null,
    restricciones: [...(x.restricciones || [])] };
  const del = {};
  for (const k of CAMPOS_TEXTO) {
    if (x[k] != null) { p[k] = x[k]; del[k] = x[k]; }
  }
  if (p.etapa === "embarazo" && x.trimestre == null) p.trimestre = null;
  if (p.restricciones.length) del.restricciones = [...p.restricciones];
  p.del_texto = del;
  return p;
}

function aplicarInterpretacion(r) {
  const P = estado.P, ped = r.pedido;
  if (ped.personas.length) {
    estado.hogar = ped.personas.slice(0, P.PERSONAS_MAXIMAS).map(personaDelTexto);
    const conError = estado.hogar.findIndex((p) => erroresPersona(p).length);
    estado.actual = Math.max(conError, 0);
  }
  const hogar = {};
  if (ped.dias != null && String(ped.dias) in P.DIAS_PERIODO) { estado.dias = ped.dias; hogar.dias = ped.dias; }
  if (ped.agua != null && ped.agua in P.AGUA_MODOS) { estado.agua = ped.agua; hogar.agua = ped.agua; }
  if (ped.listos != null) { estado.listos = ped.listos; hogar.listos = ped.listos; }
  if (ped.promos != null && estado.promosEnBase) { estado.promos = ped.promos; hogar.promos = ped.promos; }
  if (ped.caminata_minutos != null && P.CAMINATA_OPCIONES.includes(ped.caminata_minutos)) {
    estado.caminata = ped.caminata_minutos;
    hogar.caminata_minutos = ped.caminata_minutos;
  }
  estado.delTexto = hogar;
  estado.anterior = null;
  estado.escalera.clear();
  $("#retomar").hidden = true;
  sincronizarControles();
  guardar();
}

function listaTexto(titulo, items, clase = "") {
  if (!items.length) return "";
  return `<div class="tl-lista ${clase}"><p class="tl-sub">${esc(titulo)}</p><ul>${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`;
}

function mostrarInterpretacion(r) {
  const P = estado.P, ped = r.pedido;
  const n = ped.personas.length;
  const partes = [];
  if (n) partes.push(`${n === 1 ? "1 persona" : `${n} personas`} (${ped.personas.map((p, i) => nombrePersona(p, i)).join(", ")})`);
  if (ped.dias != null) partes.push(`la compra para ${P.DIAS_PERIODO[ped.dias]}`);
  if (ped.agua != null) partes.push(P.AGUA_MODOS[ped.agua].corto);
  if (ped.listos) partes.push("solo alimentos listos para comer");
  if (ped.caminata_minutos != null) partes.push(`hasta ${ped.caminata_minutos} min caminando`);
  const cargado = partes.length
    ? `Cargamos ${partes.length > 1 ? partes.slice(0, -1).join(", ") + " y " + partes[partes.length - 1] : partes[0]}.`
    : "No cambiamos nada del formulario.";
  const sigue = n ? "Revisá a cada persona y completá lo que falta: nada se calcula hasta que toques «Armar la canasta»." : "";
  const el = $("#tl-resultado");
  el.innerHTML = `<p class="tl-entendimos"><b>Lo que entendimos.</b> ${esc(cargado)} ${esc(sigue)}</p>
    ${r.simulado ? '<p class="tl-simulado">Modo de prueba: no se envió nada a Groq y esta es una respuesta de ejemplo, no la de tu texto.</p>' : ""}
    ${listaTexto("Para completar o aclarar", r.preguntas, "tl-preguntas")}
    ${listaTexto("Atención", r.avisos, "tl-avisos")}
    ${listaTexto("Lo que la canasta no aplica", r.notas, "tl-notas")}`;
  el.hidden = false;
  el.focus({ preventScroll: true });
}

async function interpretarTexto() {
  const texto = $("#tl-texto").value.trim(), boton = $("#tl-interpretar"), aviso = $("#tl-estado");
  if (!texto || !$("#tl-acepto").checked || boton.disabled) return;
  boton.disabled = true;
  boton.classList.add("trabajando");
  $("#tl-texto").readOnly = true;
  aviso.classList.remove("error");
  aviso.textContent = "Interpretando…";
  const corte = new AbortController();
  const reloj = setTimeout(() => corte.abort(), 45000);
  try {
    const resp = await fetch("/api/interpretar", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto, consentimiento: true }), signal: corte.signal, cache: "no-store" });
    let datos = null;
    try { datos = await resp.json(); } catch (err) { /* sin cuerpo JSON */ }
    if (!resp.ok || !datos || !datos.pedido) {
      throw new Error((datos && datos.error) || `El servidor local respondió con un error (${resp.status}).`);
    }
    aplicarInterpretacion(datos);
    mostrarInterpretacion(datos);
    aviso.textContent = "";
  } catch (err) {
    aviso.classList.add("error");
    aviso.textContent = err.name === "AbortError" ? "Tardó demasiado: probá de nuevo en un rato o completá el formulario a mano."
      : err instanceof TypeError ? "No se pudo hablar con el servidor local: ¿sigue abierto python -m canasta?"
      : err.message;
  } finally {
    clearTimeout(reloj);
    $("#tl-texto").readOnly = false;
    boton.classList.remove("trabajando");
    habilitarInterpretar();
  }
}

function habilitarInterpretar() {
  const largo = $("#tl-texto").value.length, maximo = estado.P.LLM_TEXTO_MAXIMO;
  $("#tl-contador").textContent = largo ? `${fmt(largo)} de ${fmt(maximo)} caracteres` : "";
  $("#tl-contador").classList.toggle("cerca", largo > maximo * 0.9);
  $("#tl-interpretar").disabled = !$("#tl-texto").value.trim() || !$("#tl-acepto").checked
    || $("#tl-interpretar").classList.contains("trabajando");
}

// Solo se pregunta al servidor si la página se sirve desde esta máquina: en la publicada no hay backend.
async function prepararTextoLibre() {
  if (!["localhost", "127.0.0.1", "[::1]"].includes(location.hostname)) return;
  let info = null;
  try {
    const corte = new AbortController();
    setTimeout(() => corte.abort(), 3000);
    const resp = await fetch("/api/estado", { cache: "no-store", signal: corte.signal });
    if (resp.ok) info = await resp.json();
  } catch (err) { return; }                     // servidor sin la API (otro servidor de archivos): no se ofrece
  if (!info || typeof info.llm !== "boolean") return;
  $("#texto-libre").hidden = false;
  $("#tl-form").hidden = !info.llm;
  $("#tl-sin-clave").hidden = info.llm;
  const area = $("#tl-texto");
  area.maxLength = estado.P.LLM_TEXTO_MAXIMO;
  area.addEventListener("input", habilitarInterpretar);
  $("#tl-acepto").addEventListener("change", habilitarInterpretar);
  $("#tl-interpretar").addEventListener("click", interpretarTexto);
  if (info.simulado) {
    $("#tl-estado").textContent = "Modo de prueba (--llm-simulado): las respuestas son de ejemplo y no se envía nada a Groq.";
  }
  habilitarInterpretar();
}

// ============================================================
// Armar la canasta
// ============================================================

// Mientras calcula: la impresora "trabajando". Solo se actualizan la barra y el texto para no reiniciar la animación.
function cargando(texto, fraccion) {
  const pct = Math.round(fraccion * 100);
  if (!$("#resultado .cargando")) {
    $("#resultado").innerHTML = `<div class="cargando">
      <div class="impresora" aria-hidden="true"><div class="ranura activa"></div>
        <div class="ticket ticket-cargando"><p class="t-centro">CALCULANDO</p><hr>
          ${Array.from({ length: 7 }, (_, i) => `<p class="t-esqueleto" style="--i:${i};--w:${55 + (i * 37) % 40}%"></p>`).join("")}
          <hr><p class="t-total"><span>TOTAL</span><span>$ …</span></p></div></div>
      <div class="progreso" role="progressbar" aria-valuemin="0" aria-valuemax="100"><i></i></div>
      <p class="cargando-texto" aria-live="polite"></p></div>`;
  }
  const barra = $("#resultado .progreso");
  barra.setAttribute("aria-valuenow", pct);
  barra.firstElementChild.style.width = `${pct}%`;
  $("#resultado .cargando-texto").textContent = texto;
}

// El total cuenta hasta su valor (o aparece directo con "reducir movimiento").
function contar(el) {
  const final = Number(el.dataset.valor);
  if (SIN_MOVIMIENTO.matches || !Number.isFinite(final)) { el.textContent = pesos(final, 0); return; }
  const inicio = performance.now(), dura = 900;
  const paso = (t) => {
    const x = Math.min(1, Math.max(0, (t - inicio) / dura));   // el primer cuadro puede ser anterior al inicio
    el.textContent = pesos(final * (1 - Math.pow(2, -10 * x)) / (1 - Math.pow(2, -10)), 0);
    if (x < 1) requestAnimationFrame(paso); else el.textContent = pesos(final, 0);
  };
  requestAnimationFrame(paso);
}

// Tiempos caminando a las sucursales candidatas (rutas reales de OpenRouteService o, si falla, estimados).
// Se guardan por lugar y límite: volver a un límite ya consultado no gasta cuota.
async function tiemposCaminando(minutos) {
  const { lat, lon } = estado.lugar;
  const clave = `${lat},${lon},${minutos}`;
  if (estado.tiempos.has(clave)) return estado.tiempos.get(clave);
  const { candidatas } = await motor.pedir("candidatas", { lat, lon, minutos });
  const r = await Rutas.tiempos(estado.P, { lat, lon }, candidatas);
  r.candidatas = candidatas;
  if (r.fuente === "ruta") estado.tiempos.set(clave, r);
  return r;
}

function resumenOpcion(r) {
  if (!r || !r.ticket) return null;
  const s = r.ticket.tienda;
  return { minutos: r.caminata ? r.caminata.minutos : null, costo: r.ticket.total, tienda: `${s.bandera} ${s.sucursal}`,
    minutos_tienda: s.minutos, fuente: s.fuente_tiempo, metas: metasHogar(r) };
}

function siguienteCaminata() {
  const ops = estado.P.CAMINATA_OPCIONES;
  return ops.find((m) => m > estado.caminata) ?? null;
}

// Otro límite de caminata: recalcula las sucursales alcanzables y vuelve a optimizar (o muestra lo ya calculado).
async function calcularCaminata(minutos) {
  if (minutos == null || estado.ocupado) return;
  const previo = resumenOpcion(estado.resultado);
  estado.caminata = minutos;
  $$('[name="caminata"]').forEach((c) => { c.checked = Number(c.value) === minutos; });
  dibujarPersonas();
  guardar();
  const hecho = estado.escalera.get(minutos);
  if (hecho) {
    estado.anterior = previo;
    estado.resultado = hecho.resultado;
    estado.pedido = hecho.pedido;
    estado.ultimaRuta = hecho.rutas;
    if (hecho.resultado.ticket) mostrar(hecho.resultado); else mostrarSinResultado(hecho.resultado);
    return;
  }
  await armar(null, previo);
}

const ampliar = () => calcularCaminata(siguienteCaminata());

async function armar(e, anterior = null) {
  if (e) e.preventDefault();
  if (estado.ocupado) return;
  estado.anterior = anterior;
  if (e) estado.escalera.clear();          // nuevo pedido desde el formulario: lo calculado antes ya no vale
  const msj = $("#mensaje");
  msj.textContent = "";
  if (!estado.listo) { msj.textContent = "Los precios se están preparando: esperá unos segundos."; return; }
  const conError = estado.hogar.findIndex((p) => erroresPersona(p).length);
  if (conError >= 0) {
    estado.actual = conError;
    cargarEditor();
    dibujarPersonas();
    irAPaso("hogar");
    msj.textContent = `Revisá los datos de ${nombrePersona(estado.hogar[conError], conError)}.`;
    return;
  }
  if (!estado.lugar) { msj.textContent = "Falta elegir dónde comprás (paso 2)."; irAPaso("ubicacion"); $("#busqueda").focus(); return; }
  const personas = estado.hogar.map((p, i) => ({ ...p, nombre: nombrePersona(p, i),
    objetivo: p.edad < 18 || p.etapa !== "general" ? "mantener" : p.objetivo,
    trimestre: p.etapa === "embarazo" ? p.trimestre : null }));
  estado.ocupado = true;
  $("#armar").disabled = true;
  $("#armar").classList.add("calculando");
  cargando("Preparando el cálculo…", 0.03);
  try {
    const pedido = { personas, lat: estado.lugar.lat, lon: estado.lugar.lon, dias: estado.dias, listos: estado.listos,
      agua: estado.agua, promos: estado.promos };
    let rutas = null;
    if (CON_RUTAS) {
      cargando(`Buscando supermercados a menos de ${estado.caminata} minutos caminando…`, 0.03);
      rutas = await tiemposCaminando(estado.caminata);
      Object.assign(pedido, { tiempos: rutas.tiempos, caminata_minutos: estado.caminata, aviso_tiempos: rutas.aviso });
    }
    const { resultado } = await motor.pedir("armar", { pedido },
      (a) => cargando(a.hechas ? `Sucursales resueltas: ${a.hechas} de ${a.total} (la última, ${a.sucursal})`
        : `Resolviendo la canasta en ${a.total} sucursales ${CON_RUTAS ? "a tu alcance" : "cercanas"}…`, 0.08 + 0.92 * a.hechas / a.total));
    estado.resultado = resultado;
    estado.pedido = pedido;
    estado.ultimaRuta = rutas;
    estado.vista = 0;
    if (resultado.caminata) estado.escalera.set(resultado.caminata.minutos, { resumen: resumenOpcion(resultado), resultado, rutas, pedido });
    if (resultado.error && !resultado.ticket) {
      mostrarSinResultado(resultado);
    } else {
      mostrar(resultado);
    }
    $("#resultado-json").textContent = JSON.stringify(resultado);
  } catch (err) {
    $("#resultado").innerHTML = `<div class="vacio"><p class="mensaje">${esc(err.message)}</p>
      <p>Probá de nuevo en unos segundos. Si sigue pasando, recargá la página.</p></div>`;
    $("#resultado-json").textContent = JSON.stringify({ error: err.message });
  } finally {
    estado.ocupado = false;
    $("#armar").classList.remove("calculando");
    marcarPasos();
  }
}

// ============================================================
// Resultado
// ============================================================

// "12 min caminando (950 m)" o "≈ 12 min caminando (estimado)"; vacío si no se buscó por tiempo.
function textoCaminata(x, corto = false) {
  if (x == null || x.minutos == null) return "";
  const estimado = x.fuente_tiempo === "estimado";
  const min = `${estimado ? "≈ " : ""}${fmt(Math.max(1, Math.round(x.minutos)))} min`;
  if (corto) return min;
  const extra = estimado ? " (estimado)" : x.metros != null ? ` (${x.metros >= 1000 ? `${fmt(x.metros / 1000, 1)} km` : `${fmt(x.metros)} m`})` : "";
  return `${min} caminando${extra}`;
}

// El agua se calcula en gramos (≈ ml) y se muestra en litros.
const enLitros = (c) => (c.unidad !== "ml" ? c : { ...c, unidad: "L", valor: c.valor == null ? null : c.valor / 1000,
  minimo: c.minimo == null ? null : c.minimo / 1000, maximo: c.maximo == null ? null : c.maximo / 1000 });

// Con agua de la canilla: cuánta tomar por día además de la que traen los alimentos de la compra (en litros).
const aguaCanilla = (p) => {
  const c = p.cobertura.find((x) => x.clave === "agua");
  return c && c.estado === "informativa" ? { falta: Math.max(0, c.minimo - c.valor) / 1000, alimentos: c.valor / 1000, meta: c.minimo / 1000 } : null;
};

function metasCubiertas(p) {
  const exigidas = p.cobertura.concat(p.reglas).filter((c) => c.estado !== "informativa" && c.estado !== "no_aplica");
  return { cumple: exigidas.filter((c) => c.estado === "cumple").length, total: exigidas.length };
}

// Las metas de todo el hogar: cuántas se le exigen a la compra (sin las informativas ni las que no aplican) y cuántas cumple.
const metasHogar = (d) => d.personas.map(metasCubiertas)
  .reduce((a, b) => ({ cumple: a.cumple + b.cumple, total: a.total + b.total }), { cumple: 0, total: 0 });

// "Leche, yogur y queso: 3 porciones por día (...)" se nombra "Leche, yogur y queso".
const nombreCorto = (c) => c.nombre.split(":")[0];

// Cuánto cubre una meta que no se cumple: el porcentaje del mínimo o, si se pasa, del máximo.
function coberturaFalta(c) {
  if (c.estado === "excede" && c.maximo) {
    const pct = c.valor / c.maximo * 100;
    return { pct, texto: `se pasa: llega al ${fmt(pct, 0)} % del máximo` };
  }
  const pct = c.porcentaje ?? 0;
  return { pct, texto: c.valor === 0 && /no vende/.test(c.nota || "") ? "0 %: no vende ninguno apto" : `cubre el ${fmt(Math.min(pct, 99), 0)} %` };
}

// La promoción de un renglón: aplicada, como la línea de descuento de la caja (con lo que se paga); no aplicada, con
// el motivo. Una base anterior a la etapa 5 solo trae el precio de promoción, sin condiciones.
function promoHTML(it) {
  const p = it.promo;
  if (p && p.aplicada) {
    return `<p class="t-linea t-descuento"><span>${esc(p.resumen)} <small>pagás ${pesos(it.subtotal)}</small></span>`
      + `<span>−${fmt(it.descuento, 2)}</span></p>`;
  }
  if (p) return `<p class="t-promo">Promo ${esc(p.resumen)}, no aplicada (${esc(p.motivo)})</p>`;
  return it.promocion ? `<p class="t-promo">Promo ${pesos(it.promocion)} c/u: no aplicada (tiene condiciones)</p>` : "";
}

// Las líneas del total cuando hubo promociones: subtotal a precio de lista y el ahorro (antes del TOTAL).
const ahorroHTML = (t) => (t.ahorro_promociones > 0
  ? `<p class="t-linea"><span>Subtotal a precio de lista</span><span>${pesos(t.total_lista)}</span></p>
    <p class="t-linea t-ahorro"><span>Ahorro por promociones</span><span>−${pesos(t.ahorro_promociones)}</span></p>` : "");

// La fecha de los precios de una sucursal (aaaa-mm-dd → dd/mm/aaaa) y, si es de un día anterior al más reciente de
// la base (su cadena no publicó el día: entra con su último archivo, hasta 15 días), "precios de hace N días".
const fechaTexto = (f) => (f || "").split("-").reverse().join("/");
const haceTexto = (s) => (s && s.dias_precios > 0
  ? `precios de hace ${s.dias_precios} día${s.dias_precios === 1 ? "" : "s"}` : "");
const preciosDe = (s) => `Precios SEPA del ${fechaTexto(s.fecha_precios)}${haceTexto(s) ? ` (hace ${s.dias_precios} día${s.dias_precios === 1 ? "" : "s"})` : ""}`;

// La nota del pie: qué precios lleva el total.
function notaPrecios(d, t) {
  if (t.ahorro_promociones > 0) return "Con las promociones que no piden<br>banco ni tarjeta.";
  if (d.opciones.promos_en_base && !d.opciones.promos) return "Precios de lista: desactivaste<br>las promociones.";
  if (d.opciones.promos) return "Precios de lista: ninguna promoción<br>sin condiciones baja esta compra.";
  return "Precios de lista. Las promociones<br>no se aplican al total.";
}

// Los renglones del ticket (agrupados por grupo de alimentos), con quién come cada cosa si son varios. El importe de
// cada renglón es a precio de lista; si tiene una promoción aplicada, la línea de descuento va debajo.
function renglonesHTML(d, lista) {
  const varias = d.personas.length > 1;
  let grupoActual = "";
  return lista.map((it) => {
    const cabeza = it.grupo !== grupoActual ? `<p class="t-grupo">${esc(it.grupo)}</p>` : "";
    grupoActual = it.grupo;
    const quien = varias
      ? it.por_persona.map((g, i) => (g > 0 ? `<span class="t-quien" style="--c:${colorDe(i)}">${esc(d.personas[i].datos.nombre)} ${fmt(g)} ${it.agua ? "ml" : "g"}</span>` : "")).join("") + "por día"
      : `${esc(it.consumo_dia_texto)} por día`;
    return `${cabeza}<div class="t-item">
      <p class="t-linea t-nombre"><span>${esc(it.nombre)}</span><span>${fmt(it.subtotal_lista ?? it.subtotal, 2)}</span></p>
      <p class="t-cantidad">${esc(it.cantidad)} &times; ${esc(it.precio_unidad_texto)}</p>
      <p class="t-detalle">${quien}${it.sobrante_texto ? ` · sobran ${esc(it.sobrante_texto)}` : ""}</p>
      ${promoHTML(it)}
    </div>`;
  }).join("");
}

const paraQuien = (d) => d.personas.map((p) => `${esc(p.datos.nombre)} (${p.datos.sexo === "F" ? "mujer" : "varón"}, ${p.datos.edad})`).join(", ");

function ticketHTML(d) {
  const t = d.ticket, s = t.tienda, varias = d.personas.length > 1;
  const items = renglonesHTML(d, t.items);
  const para = paraQuien(d);
  const energia = d.personas.reduce((sum, p) => sum + ((p.cobertura.find((c) => c.clave === "energia_kcal") || {}).valor || 0), 0);
  const metas = metasHogar(d);
  const caminata = textoCaminata(s);
  return `<div class="ticket" role="document" aria-label="Ticket de la compra">
    <p class="t-marca">${esc(s.bandera)}</p>
    <p class="t-centro">${esc(s.comercio)}${s.cuit ? `<br>CUIT ${esc(cuit(s.cuit))}` : ""}</p>
    <p class="t-centro">Suc. ${esc(s.sucursal)}<br>${esc(s.direccion)}${s.localidad ? `<br>${esc(s.localidad)}` : ""}</p>
    ${caminata ? `<p class="t-centro t-destacado">A ${esc(caminata)}</p>` : ""}
    <p class="t-centro">Horario de hoy (${esc(s.hoy.dia)}): ${esc(s.hoy.horario)}</p>
    <hr>
    <p>Canasta saludable para ${esc(d.periodo)}</p>
    <p>Para: ${para}</p>
    ${d.opciones.listos ? "<p>Solo alimentos listos para comer</p>" : ""}
    <p>${esc(preciosDe(s))}</p>
    <hr>
    <p class="t-linea t-columnas"><span>Descripción</span><span>Importe</span></p>
    ${items}
    <hr>
    <p class="t-linea"><span>${t.items.length} artículos</span><span></span></p>
    ${ahorroHTML(t)}
    <p class="t-total"><span>TOTAL</span><span>${pesos(t.total)}</span></p>
    <p class="t-linea"><span>Por día</span><span>${pesos(t.costo_diario)}</span></p>
    ${varias ? `<p class="t-linea"><span>Por persona y día</span><span>${pesos(t.costo_diario / d.personas.length)}</span></p>` : ""}
    <p class="t-linea"><span>Cada 1.000 kcal</span><span>${pesos(t.costo_1000_kcal)}</span></p>
    <hr>
    <p class="t-linea"><span>Energía por día</span><span>${fmt(energia)} kcal</span></p>
    <p class="t-linea"><span>Meta del hogar</span><span>${fmt(d.hogar.energia_kcal)} kcal</span></p>
    <p class="t-linea"><span>Metas cubiertas</span><span>${metas.cumple} de ${metas.total}</span></p>
    <hr>
    <p class="t-centro">${notaPrecios(d, t)}</p>
    <p class="t-centro t-gracias">*** Gracias por su compra ***</p>
  </div>`;
}

// "≈ 3 min" o "6 min" (los estimados, con ≈).
const minutosTexto = (minutos, fuente) => textoCaminata({ minutos, fuente_tiempo: fuente }, true);
const nombreTienda = (s) => `${s.bandera} ${s.sucursal}`;

// La compra en dos súper en un solo ticket: un tramo por sucursal (encabezado, renglones y subtotal) separados por la
// línea de corte, y al pie el total de las dos y la comparación con comprar todo en la primera.
function ticketDivididoHTML(d, ds) {
  const t = ds.ticket, varias = d.personas.length > 1;
  // Cada súper con la fecha de sus precios; arriba, una sola si las dos son del mismo día.
  const unaFecha = t.sucursales.every((x) => x.tienda.fecha_precios === t.sucursales[0].tienda.fecha_precios);
  const articulos = t.sucursales.reduce((n, x) => n + x.items.length, 0);
  const tramos = t.sucursales.map((x, k) => {
    const s = x.tienda;
    const llegar = k === 0 ? textoCaminata(s)
      : `${minutosTexto(ds.b.minutos_desde_a, "estimado")} caminando desde ${nombreTienda(ds.a)} (estimado)`;
    return `${k ? '<p class="t-corte" aria-hidden="true"><span>✂</span></p>' : ""}
    <p class="t-centro t-paso">Súper ${k + 1} de ${t.sucursales.length}</p>
    <p class="t-marca">${esc(s.bandera)}</p>
    <p class="t-centro">${esc(s.comercio)}${s.cuit ? `<br>CUIT ${esc(cuit(s.cuit))}` : ""}</p>
    <p class="t-centro">Suc. ${esc(s.sucursal)}<br>${esc(s.direccion)}${s.localidad ? `<br>${esc(s.localidad)}` : ""}</p>
    ${llegar ? `<p class="t-centro t-destacado">A ${esc(llegar)}</p>` : ""}
    <p class="t-centro">Horario de hoy (${esc(s.hoy.dia)}): ${esc(s.hoy.horario)}</p>
    <p class="t-centro">${esc(preciosDe(s))}</p>
    <hr>
    <p class="t-linea t-columnas"><span>Descripción</span><span>Importe</span></p>
    ${renglonesHTML(d, x.items)}
    <hr>
    <p class="t-linea t-subtotal"><span>Subtotal ${esc(s.bandera)} (${x.items.length} art.)</span><span>${pesos(x.subtotal)}</span></p>`;
  }).join("");
  const m = ds.metas_despues, circuito = ds.minutos;
  return `<div class="ticket ticket-dividido" role="document" aria-label="Ticket de la compra en dos supermercados">
    <p class="t-marca">CHANGUITO SANO</p>
    <p class="t-centro t-destacado">Compra en dos supermercados</p>
    <hr>
    <p>Canasta saludable para ${esc(d.periodo)}</p>
    <p>Para: ${paraQuien(d)}</p>
    ${d.opciones.listos ? "<p>Solo alimentos listos para comer</p>" : ""}
    ${unaFecha ? `<p>${esc(preciosDe(t.sucursales[0].tienda))}</p>` : "<p>Precios SEPA: los de cada súper</p>"}
    <hr>
    ${tramos}
    <hr class="t-doble">
    ${t.sucursales.map((x, k) => `<p class="t-linea"><span>${k + 1}. ${esc(nombreTienda(x.tienda))}</span><span>${pesos(x.subtotal)}</span></p>`).join("")}
    <p class="t-linea"><span>${articulos} artículos</span><span></span></p>
    ${ahorroHTML(t)}
    <p class="t-total"><span>TOTAL</span><span>${pesos(t.total)}</span></p>
    <p class="t-linea"><span>Por día</span><span>${pesos(t.costo_diario)}</span></p>
    ${varias ? `<p class="t-linea"><span>Por persona y día</span><span>${pesos(t.costo_diario / d.personas.length)}</span></p>` : ""}
    <hr>
    <p class="t-linea"><span>Todo en ${esc(ds.a.bandera)}</span><span>${pesos(ds.costo_a)}</span></p>
    <p class="t-linea t-destacado"><span>${ds.ahorro >= 0 ? "Ahorrás" : "Pagás de más"}</span><span>${pesos(Math.abs(ds.ahorro))}</span></p>
    <p class="t-linea"><span>Metas cubiertas</span><span>${m.cumple} de ${m.total}</span></p>
    <p class="t-linea"><span>Caminata ida y vuelta</span><span>${minutosTexto(circuito.circuito, circuito.fuente)}</span></p>
    ${circuito.fuente === "estimado" ? '<p class="t-centro t-nota">Minutos estimados: el tramo entre<br>los dos súper va en línea recta.</p>' : ""}
    <hr>
    <p class="t-centro">${notaPrecios(d, t)}</p>
    <p class="t-centro t-gracias">*** Gracias por su compra ***</p>
  </div>`;
}

const TEXTO_ESTADO = { cumple: "Cumple", falta: "Falta", excede: "Se pasa", informativa: "Informativa", no_aplica: "No aplica" };
const decimales = (x) => (x == null ? 0 : Math.abs(x) < 10 ? 1 : 0);

const ICONO_ESTADO = { cumple: "✓", falta: "!", excede: "↑", informativa: "i", no_aplica: "–" };

const rangoTexto = (c) => (c.minimo != null && c.maximo != null ? `${fmt(c.minimo, decimales(c.minimo))}–${fmt(c.maximo, decimales(c.maximo))}`
  : c.minimo != null ? `mín. ${fmt(c.minimo, decimales(c.minimo))}` : c.maximo != null ? `máx. ${fmt(c.maximo, decimales(c.maximo))}` : "—");

// Gráfico de bala: la franja es la meta (mínimo a máximo, con una raya en cada borde) y el punto, lo que come. El
// estado va también en el ícono y en texto (no solo en el color).
function bala(c) {
  const tope = Math.max(c.maximo ?? 0, (c.minimo ?? 0) * 1.6, (c.valor ?? 0) * 1.08) || 1;
  const pos = (x) => Math.max(0, Math.min(100, x / tope * 100));
  const desde = c.minimo != null ? pos(c.minimo) : 0, hasta = c.maximo != null ? pos(c.maximo) : 100;
  const marcas = [c.minimo, c.maximo].filter((x) => x != null && x > 0 && pos(x) < 100)
    .map((x) => `<i class="b-marca" style="--x:${pos(x)}%"></i>`).join("");
  const punto = c.valor == null ? "" : `<i class="b-punto" style="--x:${pos(c.valor)}%"></i>`;
  return `<li class="bala ${c.estado}">
    <span class="b-nombre" ${c.nota ? `title="${esc(c.nota)}"` : ""}>${esc(c.nombre)}</span>
    <span class="b-pista" aria-hidden="true"><i class="b-rango" style="left:${desde}%;width:${Math.max(hasta - desde, 1)}%"></i>${marcas}${punto}</span>
    <span class="b-valor"><span>${c.valor == null ? "—" : fmt(c.valor, decimales(c.valor))} <small>${esc(c.unidad)}</small></span><small class="b-meta">meta ${rangoTexto(c)}</small></span>
    <span class="b-estado" title="${TEXTO_ESTADO[c.estado]}"><i aria-hidden="true">${ICONO_ESTADO[c.estado]}</i><span class="b-estado-texto">${TEXTO_ESTADO[c.estado]}</span></span>
  </li>`;
}

// Lo que falta o se pasa va primero (en el orden de siempre); el título dice cuántas metas se cumplen.
const ORDEN_ESTADO = { falta: 0, excede: 1 };
function graficoBalas(titulo, lista) {
  const ordenada = lista.map((c, i) => [c, i])
    .sort(([a, i], [b, j]) => ((ORDEN_ESTADO[a.estado] ?? 2) - (ORDEN_ESTADO[b.estado] ?? 2)) || i - j).map(([c]) => c);
  const evaluadas = lista.filter((c) => c.estado === "cumple" || c.estado === "falta" || c.estado === "excede");
  const cumplen = evaluadas.filter((c) => c.estado === "cumple").length;
  const conteo = evaluadas.length
    ? `<span class="gb-conteo ${cumplen === evaluadas.length ? "todas" : "faltan"}">${cumplen} de ${evaluadas.length} cumplen</span>` : "";
  return `<div class="grafico-balas"><p class="gb-titulo"><span>${esc(titulo)}</span>${conteo}</p><ul>${ordenada.map(bala).join("")}</ul></div>`;
}

// Dona de calorías por grupo de alimentos, con las kcal del día en el centro.
function dona(todos, kcal) {
  const grupos = todos.filter((g) => g.kcal_dia > 0);          // el agua no aporta calorías: no va en la dona
  const r = 54, C = 2 * Math.PI * r;
  let acum = 0;
  const arcos = grupos.map((g, k) => {
    const largo = C * g.pct_kcal / 100;
    const arco = `<circle r="${r}" cx="70" cy="70" fill="none" stroke="${COLOR_GRUPO[g.grupo] || "#777"}" stroke-width="20"
      stroke-dasharray="${largo.toFixed(2)} ${(C - largo).toFixed(2)}" stroke-dashoffset="${(-acum).toFixed(2)}" style="--i:${k}"/>`;
    acum += largo;
    return arco;
  }).join("");
  return `<div class="dona-bloque">
    <div class="dona"><svg viewBox="0 0 140 140" role="img" aria-label="Calorías por grupo de alimentos"><g transform="rotate(-90 70 70)">${arcos}</g></svg>
      <p class="dona-centro"><b>${fmt(kcal)}</b><span>kcal por día</span></p></div>
    <ul class="dona-leyenda">${grupos.map((g) => `<li style="--c:${COLOR_GRUPO[g.grupo] || "#777"}">
      <span class="dl-nombre">${esc(g.grupo)}</span><span class="dl-pct">${fmt(g.pct_kcal)} %</span>
      <span class="dl-dato">${fmt(g.gramos_dia)} g · ${fmt(g.kcal_dia)} kcal</span></li>`).join("")}</ul>
  </div>`;
}

function bloquePersona(d, i) {
  const p = d.personas[i], q = p.requerimientos, r = p.restricciones;
  const energia = p.cobertura.find((c) => c.clave === "energia_kcal");
  const listos = d.opciones.listos ? [{ clave: "listos", nombre: estado.P.LISTOS_NOMBRE, criterio: d.opciones.listos_criterio }] : [];
  const datos = `${p.datos.sexo === "F" ? "mujer" : "varón"} de ${p.datos.edad} años, ${fmt(p.datos.peso_kg, 1)} kg, actividad ${p.datos.actividad.toLowerCase()}`;
  const macro = p.cobertura.filter((c) => c.tipo === "energia" || c.tipo === "macro" || c.clave === "agua").map(enLitros);
  const micro = p.cobertura.filter((c) => c.tipo !== "energia" && c.tipo !== "macro" && c.clave !== "agua");
  const canilla = aguaCanilla(p);
  const problemas = p.cobertura.concat(p.reglas).filter((c) => c.estado === "falta" || c.estado === "excede");
  const m = metasCubiertas(p);
  const restricciones = r.criterios.concat(listos);
  return `
    <div class="persona-cabeza">
      <p><b>${esc(p.datos.nombre)}</b>: ${esc(datos)}${p.datos.restricciones.length ? `; ${esc(p.datos.restricciones.join(", ").toLowerCase())}` : ""}.</p>
      <ul class="cifras-persona">
        <li><b>${fmt(q.energia_kcal)}</b><span>kcal por día que necesita</span></li>
        <li><b>${fmt(energia && energia.valor)}</b><span>kcal por día que come de esta compra</span></li>
        <li><b>${fmt(q.proteina_g_kg, 2)}</b><span>g de proteína por kg</span></li>
        <li class="${problemas.length ? "con-faltas" : "sin-faltas"}"><b>${m.cumple}/${m.total}</b><span>metas cubiertas</span></li>
      </ul>
    </div>

    <h3 class="subtitulo">Cómo calculamos lo que necesita</h3>
    <ol class="calculo">${q.pasos.map((s, k) => `<li style="--i:${k}">
      <p class="c-titulo">${esc(s.titulo)}</p><p class="c-res">${esc(s.resultado)}</p>
      <details><summary>Cómo se calcula</summary><p class="formula">${esc(s.formula)}</p>
        ${s.fuente ? `<p class="fuente">${esc(s.fuente)}</p>` : ""}</details></li>`).join("")}</ol>

    <h3 class="subtitulo">Lo que come por día</h3>
    ${problemas.length
      ? `<p class="estado-metas con-faltas"><i aria-hidden="true">!</i><span>Cubre ${m.cumple} de ${m.total} metas. No llega a: ${problemas.map((c) => `<b>${esc(nombreCorto(c))}</b> (${esc(coberturaFalta(c).texto)})`).join(", ")}. Es lo máximo que se puede con lo que vende esta sucursal.</span></p>`
      : `<p class="estado-metas sin-faltas"><i aria-hidden="true">✓</i><span>Cubre todas las metas que se le exigen a la compra.</span></p>`}
    ${canilla ? `<p class="estado-metas info"><i aria-hidden="true">i</i><span>Agua de la canilla: unos <b>${fmt(canilla.falta, 1)} L por día</b>.
      Los alimentos de esta compra aportan ${fmt(canilla.alimentos, 1)} L de los ${fmt(canilla.meta, 1)} L de agua del día.</span></p>` : ""}
    ${dona(p.grupos, energia && energia.valor)}
    <p class="leyenda-balas"><span class="lb-item"><span class="lb-rango"></span>la meta, de mínimo a máximo</span>
      <span class="lb-item"><span class="lb-punto"></span>lo que come</span></p>
    <div class="balas-grid">
      ${graficoBalas("Energía, macronutrientes y agua", macro)}
      ${graficoBalas("Vitaminas y minerales", micro)}
    </div>

    <h3 class="subtitulo">Guías Alimentarias</h3>
    <p class="ayuda">Además de los nutrientes, la compra respeta las Guías Alimentarias para la Población Argentina; las reglas semanales se cumplen en promedio.</p>
    ${graficoBalas("Reglas de las Guías", p.reglas)}

    <h3 class="subtitulo">Restricciones</h3>
    <p class="ayuda"><b>${fmt(r.productos_aptos)}</b> de los ${fmt(d.catalogo.productos_canasta)} productos de la canasta son aptos. Un producto sin datos que lo confirmen no se considera apto.</p>
    ${restricciones.length ? `<ul class="restricciones-lista">${restricciones.map((c) => {
      const ef = r.efecto.find((x) => x.clave === c.clave);
      const condicion = estado.P.CONDICIONES.includes(c.clave);
      return `<li><details><summary><span>${esc(c.nombre)}</span>${ef ? `<small>deja afuera ${fmt(ef.excluye)} productos</small>` : condicion ? "<small>cambia metas</small>" : ""}</summary>
        <p>${esc(c.criterio)}</p></details></li>`;
    }).join("")}</ul>` : '<p class="estado-metas sin-faltas"><i aria-hidden="true">✓</i><span>Sin restricciones: puede comer cualquier producto de la canasta.</span></p>'}`;
}

// Qué cambió al ampliar el tiempo de caminata (anterior: la mejor opción con el límite previo).
function comparacionHTML(d) {
  const a = estado.anterior, ahora = resumenOpcion(d);
  if (!a || !ahora || a.minutos == null) return "";
  const dif = a.costo - ahora.costo, pct = a.costo ? dif / a.costo * 100 : 0;
  const masMinutos = ahora.minutos_tienda != null && a.minutos_tienda != null ? Math.round(ahora.minutos_tienda - a.minutos_tienda) : null;
  const dondeAntes = `${esc(a.tienda)}${a.minutos_tienda != null ? `, a ${textoCaminata({ minutos: a.minutos_tienda, fuente_tiempo: a.fuente }, true)}` : ""}`;
  let texto;
  if (ahora.minutos != null && ahora.minutos < a.minutos) {
    // Se volvió a un límite menor (por ejemplo, de 45 a 15 min) para comparar.
    texto = ahora.tienda === a.tienda || Math.abs(dif) < 1
      ? `Con hasta ${ahora.minutos} min llegás a la misma compra: no hace falta caminar más.`
      : dif < 0
        ? `Con hasta ${ahora.minutos} min caminás menos, pero pagás <b>${pesos(-dif, 0)}</b> más que en ${dondeAntes} (${pesos(a.costo, 0)}).`
        : `Con hasta ${ahora.minutos} min la compra cuesta ${pesos(dif, 0)} menos que en ${dondeAntes}.`;
  } else if (ahora.tienda === a.tienda) {
    texto = `Con hasta ${ahora.minutos} min no aparece nada mejor: ${dondeAntes} sigue siendo la mejor opción.`;
  } else if (dif >= 1) {
    texto = `Caminando hasta ${ahora.minutos} min ahorrás <b>${pesos(dif, 0)}</b> (${fmt(pct, 0)} %)${masMinutos > 0 ? ` a cambio de ${masMinutos} min más de caminata` : ""}.
      Antes: ${pesos(a.costo, 0)} en ${dondeAntes}.`;
  } else {
    texto = `Con hasta ${ahora.minutos} min la compra elegida cubre mejor las metas, pero cuesta ${pesos(-dif, 0)} más que ${dondeAntes} (${pesos(a.costo, 0)}).`;
  }
  if (a.metas && ahora.metas && a.metas.cumple !== ahora.metas.cumple) {
    texto += ` Logra ${ahora.metas.cumple} de ${ahora.metas.total} metas (antes, ${a.metas.cumple}).`;
  }
  return `<p class="comparacion" role="status">${texto}</p>`;
}

const ICONO = {
  // Íconos de Material Symbols (Apache-2.0): caminar.
  caminar: '<svg class="icono" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M13.5 5.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM9.8 8.9 7 23h2.1l1.8-8 2.1 2v6h2v-7.5l-2.1-2 .6-3C14.8 12 16.8 13 19 13v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1L6 8.3V13h2V9.6l1.8-.7"/></svg>',
  pin: '<svg class="icono" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s-7-6.3-7-11.5A7 7 0 0 1 19 9.5C19 14.7 12 21 12 21z" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="9.5" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
  reloj: '<svg class="icono" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7v5l3 2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  imprimir: '<svg class="icono" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>',
};

// ¿Conviene caminar más? La mejor compra con cada límite; los que faltan se calculan con un toque.
function escaleraHTML(d) {
  if (!d.caminata || !CON_RUTAS) return "";
  const calculados = [...estado.escalera.values()].map((v) => v.resumen).filter((v) => v && v.costo != null);
  const max = Math.max(...calculados.map((v) => v.costo)), min = Math.min(...calculados.map((v) => v.costo));
  // "Más barata" va solo en el menor tiempo que ya consigue el precio mínimo: caminar más no ahorra nada.
  const mejorMin = calculados.length > 1
    ? Math.min(...calculados.filter((v) => v.costo - min < 1).map((v) => v.minutos)) : null;
  const filas = estado.P.CAMINATA_OPCIONES.map((m) => {
    const hecho = estado.escalera.get(m), r = hecho && hecho.resumen, actual = m === d.caminata.minutos;
    const etiqueta = `<span class="p-min">${m} min</span>`;
    if (!hecho) {
      return `<li class="peldano"><button type="button" class="peldano-boton" data-caminata="${m}">${etiqueta}
        <span class="p-barra vacia"></span><span class="p-costo p-calcular">Calcular</span></button></li>`;
    }
    if (!r || r.costo == null) {
      return `<li class="peldano sin ${actual ? "actual" : ""}"><button type="button" class="peldano-boton" data-caminata="${m}">${etiqueta}
        <span class="p-barra vacia"></span><span class="p-costo">Sin súper</span></button></li>`;
    }
    const ancho = 30 + 70 * (r.costo / max);
    const metas = r.metas && r.metas.cumple < r.metas.total ? ` · ${r.metas.cumple}/${r.metas.total} metas` : "";
    const donde = `${esc(r.tienda)}${r.minutos_tienda != null ? `, a ${textoCaminata({ minutos: r.minutos_tienda, fuente_tiempo: r.fuente }, true)}` : ""}${metas}`;
    return `<li class="peldano ${actual ? "actual" : ""} ${m === mejorMin ? "mejor" : ""}">
      <button type="button" class="peldano-boton" data-caminata="${m}" ${actual ? 'aria-current="true"' : ""}>${etiqueta}
        <span class="p-barra"><i style="--ancho:${ancho}%"></i></span><span class="p-costo">${pesos(r.costo, 0)}</span>
        <small class="p-donde">${donde}</small></button></li>`;
  }).join("");
  return `<div class="escalera"><p class="escalera-titulo">¿Conviene caminar más?</p>
    <p class="escalera-ayuda">La compra más barata con cada tiempo máximo. Tocá uno para calcularlo o verlo.</p><ol>${filas}</ol></div>`;
}

// ============================================================
// ¿Conviene sumar un segundo súper? Se calcula a pedido (MotorCanasta.dosSuper) sobre el resultado que se está viendo
// y se guarda con ese resultado: cada límite de caminata tiene el suyo y armar de nuevo lo descarta.
// ============================================================

const TITULO_DOS = '<p class="escalera-titulo">¿Conviene sumar un segundo súper?</p>';

// La compra en dos súper que se propone (la que conviene), o null.
function dosQueConviene(d) {
  const c = d && estado.dos.get(d);
  return c && c.ds && c.ds.estado === "conviene" && c.ds.ticket ? c.ds : null;
}

const conEstimado = (t) => `${minutosTexto(t.minutos, t.fuente)}${t.fuente === "estimado" ? " <small>estimado</small>" : ""}`;

// "caminando ≈ 5 min más (estimado)". No se le pone precio al minuto: se dice cuánto más y la persona decide.
function caminandoMas(ds) {
  const m = ds.minutos, est = m.fuente === "estimado", nota = est ? " <small>(estimado)</small>" : "";
  return m.extra >= 1 ? `caminando ${est ? "≈ " : ""}${fmt(Math.round(m.extra))} min más${nota}` : `casi sin caminar de más${nota}`;
}

function decisionDosHTML(d, ds) {
  if (ds.estado === "conviene" && ds.motivo === "ahorro") {
    return `<p class="dos-decision">Conviene: ahorrás <mark>${pesos(ds.ahorro, 0)}</mark> (${fmt(ds.ahorro_pct, 1)} %) ${caminandoMas(ds)}.</p>`;
  }
  if (ds.estado === "conviene") {
    const a = ds.metas_antes, b = ds.metas_despues;
    const logro = b.cumple > a.cumple ? `llegás a <mark>${b.cumple} de ${b.total}</mark> metas` : "cubrís mejor las metas que faltan";
    const plata = ds.ahorro > 0 ? `Además ahorrás ${pesos(ds.ahorro, 0)}`
      : ds.ahorro < 0 ? `Cuesta ${pesos(-ds.ahorro, 0)} más (${fmt(-ds.ahorro_pct, 1)} %)` : "Cuesta lo mismo";
    return `<p class="dos-decision">Con un segundo súper ${logro}.</p><p class="dos-texto">${plata}, ${caminandoMas(ds)}.</p>`;
  }
  if (ds.estado === "sin_vecinas") {
    return `<p class="dos-decision no">No hay otro súper cerca con otros precios.</p>
      <p class="dos-texto">Buscamos a menos de ${ds.minutos_entre_max} min caminando de ${esc(nombreTienda(ds.a))}${d.caminata ? ", dentro de tu límite de caminata" : ""}: la compra queda en uno solo.</p>`;
  }
  const texto = ds.mensaje.replace(/^No conviene dividir la compra:\s*/, "");
  return `<p class="dos-decision no">No conviene dividir la compra.</p>
    <p class="dos-texto">${esc(texto.charAt(0).toUpperCase() + texto.slice(1))}</p>`;
}

// Un súper contra dos, lado a lado: costo, metas y caminata de ida y vuelta.
function compararDosHTML(ds) {
  const m = ds.minutos, metas = (x) => `${x.cumple} de ${x.total}`;
  const mejor = (a, b, menor = true) => (a === b ? ["", ""] : (menor ? b < a : b > a) ? ["", ' class="dc-mejor"'] : [' class="dc-mejor"', ""]);
  const [c1, c2] = mejor(Math.round(ds.costo_a), Math.round(ds.costo_combinado));
  const [m1, m2] = mejor(ds.metas_antes.cumple, ds.metas_despues.cumple, false);
  return `<table class="dos-comparar">
    <thead><tr><td></td><th scope="col">Un súper</th><th scope="col">Dos súper <span class="marca-elegida">conviene</span></th></tr></thead>
    <tbody>
      <tr><th scope="row">Costo</th><td${c1}>${pesos(ds.costo_a, 0)}</td><td${c2}>${pesos(ds.costo_combinado, 0)}</td></tr>
      <tr><th scope="row">Metas cubiertas</th><td${m1}>${metas(ds.metas_antes)}</td><td${m2}>${metas(ds.metas_despues)}</td></tr>
      <tr><th scope="row">Caminata ida y vuelta</th><td>${minutosTexto(m.solo_a, m.tramos[0].fuente)}</td><td>${minutosTexto(m.circuito, m.fuente)}</td></tr>
    </tbody></table>`;
}

// Con motivo "metas": cómo queda cada meta que faltaba con un súper.
function metasDosHTML(ds) {
  if (ds.motivo !== "metas") return "";
  const pct = (f) => (f.estado === "excede" ? `se pasa (${fmt(f.porcentaje, 0)} % del máx.)` : `${fmt(Math.min(f.porcentaje, 99), 0)} %`);
  const clave = (f) => `${f.persona}|${f.clave}`;
  const antes = new Map(ds.metas_antes.faltan.map((f) => [clave(f), f]));
  const despues = new Map(ds.metas_despues.faltan.map((f) => [clave(f), f]));
  // Solo las que cambian (una que no vende nadie sigue en 0 % con dos súper: no suma nada mostrarla).
  const claves = [...new Set([...antes.keys(), ...despues.keys()])].filter((k) => {
    const a = antes.get(k), b = despues.get(k);
    return !(a && b && a.estado === b.estado && pct(a) === pct(b));
  });
  if (!claves.length) return "";
  const filas = claves.map((k) => {
    const a = antes.get(k), b = despues.get(k), f = a || b;
    return `<li><span>${f.persona ? `<small>${esc(f.persona)}</small> ` : ""}${esc(f.nombre)}</span>
      <span class="dm-dato">${a ? pct(a) : "cumple"} <i aria-hidden="true">→</i><span class="sr-only">ahora</span> <b>${b ? pct(b) : "cumple"}</b></span></li>`;
  }).join("");
  return `<div><p class="dr-titulo">Las metas que faltaban, con un súper y con dos</p><ul class="dos-metas">${filas}</ul></div>`;
}

const numeroSuper = (n) => `<span class="n-super" aria-hidden="true">${n}</span>`;

// Qué se compra en cada sucursal.
function paradasHTML(ds) {
  const [sa, sb] = ds.ticket.sucursales;
  const productos = (n) => (n === 1 ? "1 producto" : `${n} productos`);
  const cuales = ds.productos_b.slice(0, 5).join("; ") + (ds.productos_b.length > 5 ? ` y ${ds.productos_b.length - 5} más` : "");
  return `<ol class="dos-paradas">
    <li>${numeroSuper(1)}<span><b>${esc(nombreTienda(ds.a))}</b> <small>${esc(ds.a.direccion)}${haceTexto(ds.a) ? ` · ${esc(haceTexto(ds.a))}` : ""}</small>
      <span class="dp-que">El resto de la compra: ${productos(sa.items.length)}, <span class="dp-plata">${pesos(sa.subtotal, 0)}</span></span></span></li>
    <li>${numeroSuper(2)}<span><b>${esc(nombreTienda(ds.b))}</b> <small>${esc(ds.b.direccion)}${haceTexto(ds.b) ? ` · ${esc(haceTexto(ds.b))}` : ""}</small>
      <span class="dp-que">${esc(cuales)}: ${productos(sb.items.length)}, <span class="dp-plata">${pesos(sb.subtotal, 0)}</span></span></span></li>
  </ol>`;
}

// La ruta real entre los dos súper (si la página tiene clave), al lado del estimado que usa el cálculo.
function porCalleHTML(r) {
  if (!r || r.minutos == null) return "";
  const metros = r.metros == null ? "" : r.metros >= 1000 ? `, ${fmt(r.metros / 1000, 1)} km` : `, ${fmt(Math.round(r.metros))} m`;
  return `Por la calle: ${fmt(Math.max(1, Math.round(r.minutos)))} min${metros} (OpenRouteService). Las cuentas usan el estimado.`;
}

// Casa → 1 → 2 → casa, con los minutos de cada tramo como los da el motor (los estimados, marcados).
function recorridoDosHTML(ds, c) {
  const [t1, t2, t3] = ds.minutos.tramos;
  const calle = c.recorridos ? porCalleHTML(c.recorridos.ab) : c.rutas ? "Buscando la ruta por la calle…" : "";
  return `<div class="dos-recorrido"><p class="dr-titulo">El recorrido</p><ol>
    <li><span class="dr-tramo">Vos <i aria-hidden="true">→</i> ${numeroSuper(1)} ${esc(ds.a.bandera)}</span><span class="dr-min">${conEstimado(t1)}</span></li>
    <li><span class="dr-tramo">${numeroSuper(1)} <i aria-hidden="true">→</i> ${numeroSuper(2)} ${esc(ds.b.bandera)}</span><span class="dr-min">${conEstimado(t2)}</span>
      <small class="dr-calle" id="dos-por-calle">${calle}</small></li>
    <li><span class="dr-tramo">${numeroSuper(2)} <i aria-hidden="true">→</i> Vos</span><span class="dr-min">${conEstimado(t3)}</span></li>
    <li class="dr-total"><span class="dr-tramo">En total</span><span class="dr-min">${conEstimado({ minutos: ds.minutos.circuito, fuente: ds.minutos.fuente })}</span></li>
  </ol></div>`;
}

// Las vecinas que se probaron, para verificar la decisión.
function vecinasHTML(ds) {
  if (!ds.vecinas.length) return "";
  const propuesta = ds.estado === "conviene" && ds.b ? ds.b.id : null;
  const filas = ds.vecinas.map((v) => {
    const costo = v.costo == null ? "sin compra posible" : !v.compra_en_b ? "no suma nada" : `entre los dos, ${pesos(v.costo, 0)}`;
    return `<li><span>${esc(v.bandera)} ${esc(v.sucursal)}${v.id === propuesta ? ' <span class="marca-elegida">elegido</span>' : ""}
      <small>a ${minutosTexto(v.minutos_desde_a, "estimado")} de ${esc(ds.a.bandera)}</small></span><span class="dv-costo">${costo}</span></li>`;
  }).join("");
  const P = estado.P;
  return `<details class="dos-vecinas"><summary>Qué súper probamos (${ds.vecinas.length})</summary><ul>${filas}</ul>
    <p class="ayuda">Comprando todo en ${esc(nombreTienda(ds.a))} sale ${pesos(ds.costo_a, 0)}. Proponemos dividir la compra si cubre más
      metas o si ahorra al menos ${pesos(ds.ahorro_minimo, 0)} (el ${fmt(P.DOS_SUPER_AHORRO_MINIMO_PCT, 0)} % de la compra, con un piso
      de ${pesos(P.DOS_SUPER_AHORRO_MINIMO_PESOS, 0)}). No le ponemos precio a tus minutos: decidís vos.</p></details>`;
}

function dosInterior(d) {
  const c = estado.dos.get(d);
  if (!c || c.error) {
    return `${TITULO_DOS}
      <p class="escalera-ayuda">Probamos repartir la compra entre ${esc(nombreTienda(d.ticket.tienda))} y otro súper a menos de
        ${estado.P.DOS_SUPER_MINUTOS_ENTRE} min caminando de ahí. Te lo proponemos si sale más barato o cubre más metas.</p>
      ${c ? `<p class="mensaje">No se pudo calcular: ${esc(c.error)}</p>` : ""}
      <button type="button" class="boton-secundario" data-dos>${c ? "Probar de nuevo" : "Probar con un segundo súper"}</button>`;
  }
  const ds = c.ds;
  if (ds.estado !== "conviene") return `${TITULO_DOS}<div class="dos-resultado no">${decisionDosHTML(d, ds)}${vecinasHTML(ds)}</div>`;
  const viendo = estado.vistaDos;
  return `${TITULO_DOS}<div class="dos-resultado">
    ${decisionDosHTML(d, ds)}
    ${compararDosHTML(ds)}
    ${metasDosHTML(ds)}
    ${paradasHTML(ds)}
    ${recorridoDosHTML(ds, c)}
    <button type="button" class="boton-secundario" data-vista="${viendo ? "uno" : "dos"}">${viendo
      ? "Volver a la compra en un solo súper" : "Ver el ticket en dos súper"}</button>
    ${vecinasHTML(ds)}
  </div>`;
}

function pintarDos(d) {
  const caja = $("#dos");
  if (caja) caja.innerHTML = dosInterior(d);
}

// Mientras calcula: la barra y el texto de avance, sin tocar el resto del resultado.
function dosCargando(texto, fraccion) {
  const caja = $("#dos");
  if (!caja) return;
  if (!$(".dos-cargando", caja)) {
    caja.innerHTML = `${TITULO_DOS}<div class="dos-cargando">
      <div class="progreso" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-label="Avance de la compra en dos súper"><i></i></div>
      <p class="cargando-texto" aria-live="polite"></p></div>`;
  }
  const pct = Math.round(fraccion * 100), barra = $(".progreso", caja);
  barra.setAttribute("aria-valuenow", pct);
  barra.firstElementChild.style.width = `${pct}%`;
  $(".cargando-texto", caja).textContent = texto;
}

const bloquearResultado = (si) => $$("#resultado [data-caminata], #resultado [data-ampliar], #resultado [data-dos], #resultado [data-vista]")
  .forEach((b) => { b.disabled = si; });

async function calcularDos(desdeEnlace = false) {
  const d = estado.resultado, pedido = estado.pedido;
  if (!d || !d.ticket || !pedido || estado.ocupado || !$("#dos")) return;
  const previo = estado.dos.get(d);
  if (previo && !previo.error) { pintarDos(d); return; }
  const nombreA = nombreTienda(d.ticket.tienda);
  estado.ocupado = true;
  $("#armar").disabled = true;
  bloquearResultado(true);
  dosCargando(`Buscando súper a menos de ${estado.P.DOS_SUPER_MINUTOS_ENTRE} min caminando de ${nombreA}…`, 0.04);
  let c;
  try {
    // pedido: el mismo con el que se armó d (dosSuper lee las personas y los tiempos caminando de ahí).
    const { dos_super: ds } = await motor.pedir("dos_super", { pedido, resultado: d }, (a) => dosCargando(a.hechas
      ? `Combinaciones resueltas: ${a.hechas} de ${a.total} (la última, con ${a.sucursal})`
      : `Probando ${a.total === 1 ? "un súper" : `${a.total} súper`} junto con ${nombreA}…`, a.total ? 0.1 + 0.9 * a.hechas / a.total : 0.9));
    c = { ds, rutas: null, recorridos: null };
  } catch (err) {
    c = { error: err.message };
  } finally {
    estado.ocupado = false;
    marcarPasos();
  }
  estado.dos.set(d, c);
  if (estado.resultado !== d) return;
  if (dosQueConviene(d) && Rutas.tieneClave()) buscarRecorridosDos(d, c);
  pintarDos(d);
  bloquearResultado(false);
  if (dosQueConviene(d) && !$(".vista-ticket")) $(".columna-ticket").insertAdjacentHTML("afterbegin", selectorVistaHTML());
  dibujarDosEnMapa(d);
  if (desdeEnlace) $("#dos").scrollIntoView({ behavior: SIN_MOVIMIENTO.matches ? "auto" : "smooth", block: "center" });
}

// Con clave de OpenRouteService: la ruta a pie de verdad entre los dos súper y de vuelta a casa (para el mapa y para
// decir cuánto se tarda por la calle). Sin clave o si falla, no hay línea y los minutos quedan como estimados.
function buscarRecorridosDos(d, c) {
  const { a, b } = c.ds;
  c.rutas = Promise.all([Rutas.recorrido(estado.P, a, b), Rutas.recorrido(estado.P, b, d.ubicacion)]).then(([ab, bc]) => {
    c.recorridos = { ab, bc };
    const el = $("#dos-por-calle");
    if (el && estado.resultado === d) el.innerHTML = porCalleHTML(ab);
    return c.recorridos;
  });
}

// Un súper o dos: el ticket, el total y las cifras de arriba cambian juntos.
function cambiarVista(dos, boton) {
  const d = estado.resultado;
  if (!d || estado.ocupado || (dos && !dosQueConviene(d)) || dos === estado.vistaDos) return;
  estado.vistaDos = dos;
  pintarCompra(d);
  pintarDos(d);
  if (boton && boton.closest("#dos")) {
    $("#dos [data-vista]").focus({ preventScroll: true });
    const col = $(".columna-ticket"), r = col.getBoundingClientRect();
    if (r.top < 0 || r.top > innerHeight * 0.5) col.scrollIntoView({ behavior: SIN_MOVIMIENTO.matches ? "auto" : "smooth", block: "start" });
  } else {
    const nuevo = $(`.vista-ticket [data-vista="${dos ? "dos" : "uno"}"]`);
    if (nuevo) nuevo.focus({ preventScroll: true });
  }
}

function selectorVistaHTML() {
  const dos = estado.vistaDos;
  return `<div class="vista-ticket" role="group" aria-label="Qué compra ver">
    <button type="button" data-vista="uno" aria-pressed="${!dos}">Un súper</button>
    <button type="button" data-vista="dos" aria-pressed="${dos}">Dos súper</button></div>`;
}

function columnaTicketHTML(d) {
  const ds = dosQueConviene(d), dos = Boolean(ds && estado.vistaDos);
  return `${ds ? selectorVistaHTML() : ""}<div class="impresora"><div class="ranura"></div>${dos ? ticketDivididoHTML(d, ds) : ticketHTML(d)}</div>
    <button type="button" class="boton-texto con-icono" id="imprimir">${ICONO.imprimir}Imprimir o guardar el ticket</button>`;
}

// Las cifras de arriba del resumen, de la compra en uno o en dos súper.
function cifrasCompra(d, ds) {
  const varias = d.personas.length > 1, t = ds ? ds.ticket : d.ticket;
  const productos = ds ? t.sucursales.reduce((n, x) => n + x.items.length, 0) : t.items.length;
  const m = ds ? ds.metas_despues : metasHogar(d);
  return {
    total: t.total,
    donde: ds ? `en <b>${esc(nombreTienda(ds.a))}</b> y <b>${esc(nombreTienda(ds.b))}</b>` : `en <b>${esc(nombreTienda(t.tienda))}</b>`,
    datos: `<li><span>${pesos(t.costo_diario, 0)}</span>por día${varias ? ` · ${pesos(t.costo_diario / d.personas.length, 0)} por persona` : ""}</li>
      <li><span>${productos}</span>productos</li>
      <li><span>${m.cumple}/${m.total}</span>metas cubiertas</li>`,
  };
}

function animarTicket() {
  const tk = $(".columna-ticket .ticket");
  if (!tk) return;
  [...tk.children].forEach((el, i) => el.style.setProperty("--i", Math.min(i, 60)));
  tk.classList.add("imprimiendo");
}

function pintarCompra(d) {
  $(".columna-ticket").innerHTML = columnaTicketHTML(d);
  animarTicket();
  const k = cifrasCompra(d, estado.vistaDos ? dosQueConviene(d) : null);
  const total = $("#resumen-total");
  total.dataset.valor = k.total;
  contar(total);
  $("#resumen-donde").innerHTML = k.donde;
  $("#datos-compra").innerHTML = k.datos;
}

// Los súper de la compra en dos en el mapa: el segundo resaltado y las vecinas probadas, atenuadas. Las líneas, solo
// si vinieron de OpenRouteService (nunca se dibuja un recorrido inventado).
function dibujarDosEnMapa(d) {
  if (estado.capaDos) { estado.capaDos.remove(); estado.capaDos = null; }
  const mapa = estado.mapaResultado, c = estado.dos.get(d), leyenda = $("#mapa-leyenda-dos");
  if (leyenda) leyenda.textContent = "";
  if (!mapa || !c || !c.ds || !leyenda) return;
  const ds = c.ds, capa = L.layerGroup().addTo(mapa), propuesta = dosQueConviene(d);
  estado.capaDos = capa;
  const yaEstan = new Set(d.sucursales.map((x) => x.id));
  for (const v of ds.vecinas) {
    if ((propuesta && v.id === propuesta.b.id) || yaEstan.has(v.id)) continue;
    L.circleMarker([v.lat, v.lon], { radius: 5, color: color("--tinta-suave"), weight: 1.5, dashArray: "2 3", fillOpacity: 0.15, className: "m-vecina" })
      .addTo(capa).bindTooltip(`Probado para dividir la compra: ${v.bandera} ${v.sucursal}`);
  }
  if (!propuesta) return;
  const a = propuesta.a, b = propuesta.b, nombreA = nombreTienda(a), nombreB = nombreTienda(b);
  L.circleMarker([b.lat, b.lon], { radius: 9, color: color("--tinta"), fillColor: color("--acento"), weight: 3, fillOpacity: 0.85, className: "m-elegida" })
    .addTo(capa).bindTooltip(`2.º súper: ${b.bandera}`, { permanent: true, direction: "right", offset: [8, 0] });
  if (estado.puntosMapa) {
    estado.puntosMapa.push([b.lat, b.lon]);
    mapa.fitBounds(estado.puntosMapa, { padding: [30, 30], maxZoom: 16 });
  }
  if (!c.rutas) {
    leyenda.textContent = `Sin recorrido entre los dos súper: de ${nombreA} a ${nombreB} son ${minutosTexto(b.minutos_desde_a, "estimado")} estimados en línea recta.`;
    return;
  }
  leyenda.textContent = "Buscando el recorrido a pie con los dos súper…";
  c.rutas.then(({ ab, bc }) => {
    if (estado.mapaResultado !== mapa || estado.capaDos !== capa) return;     // ya se armó otra canasta
    mapa.attributionControl.addAttribution('Rutas &copy; <a href="https://openrouteservice.org/">openrouteservice.org</a> by HeiGIT');
    const partes = [[ab, nombreA, nombreB], [bc, nombreB, "vos"]].map(([r, desde, hasta]) => {
      if (!r) return `de ${desde} a ${hasta}, sin ruta (tiempo estimado)`;
      const linea = L.polyline(r.puntos, { color: color("--ruta"), weight: 4, opacity: 0.7, className: "ruta-animada ruta-dos",
        lineCap: "round", lineJoin: "round" }).addTo(capa);
      const trazo = linea.getElement();
      if (trazo) trazo.setAttribute("pathLength", "1");
      return `de ${desde} a ${hasta}, ${textoCaminata({ minutos: r.minutos, metros: r.metros ? Math.round(r.metros) : null, fuente_tiempo: "ruta" })}`;
    });
    leyenda.textContent = ab || bc ? `Con dos súper (rutas de OpenRouteService): ${partes.join("; ")}.`
      : `No se pudo trazar el recorrido entre los dos súper: de ${nombreA} a ${nombreB} son ${minutosTexto(b.minutos_desde_a, "estimado")} estimados.`;
  });
}

function botonAmpliar(texto = null) {
  const sig = siguienteCaminata();
  if (!CON_RUTAS || sig == null) return "";
  return `<button type="button" class="boton-secundario" data-ampliar>${esc(texto || `Buscar hasta ${sig} min caminando`)}</button>`;
}

function enlazarAmpliar() {
  $$("[data-ampliar]").forEach((b) => b.addEventListener("click", ampliar));
  $$("[data-caminata]").forEach((b) => b.addEventListener("click", () => {
    const m = Number(b.dataset.caminata);
    if (m !== estado.caminata || !estado.escalera.has(m)) calcularCaminata(m);
  }));
}

function avisoTiempos(d) {
  return d.caminata && d.caminata.aviso ? `<p class="aviso">${esc(d.caminata.aviso)}</p>` : "";
}

// Ninguna sucursal logra todas las metas: no es un error, es lo máximo que se puede con lo que venden. Se dice cuántas
// logra la mejor, cuánto cubre de cada una que falta y qué se puede probar (caminar más o quitar una restricción).
function avisoMetasHTML(d) {
  const elegida = d.sucursales.find((x) => x.elegida);
  if (!elegida || !elegida.faltantes.length) return "";
  const varias = d.personas.length > 1, m = metasHogar(d);
  const evaluadas = d.sucursales.filter((x) => x.costo != null).length;
  const donde = d.caminata ? `a ${d.caminata.minutos} min caminando` : "cercana";
  const titulo = evaluadas > 1
    ? `Ninguna sucursal ${donde} logra las ${m.total} metas${varias ? " del hogar" : ""}`
    : `La única sucursal ${donde} no logra las ${m.total} metas${varias ? " del hogar" : ""}`;
  const conFaltas = d.personas.filter((p) => metasCubiertas(p).cumple < metasCubiertas(p).total);
  const faltan = conFaltas.flatMap((p) => p.cobertura.concat(p.reglas)
    .filter((c) => c.estado === "falta" || c.estado === "excede")
    .map((c) => ({ c, quien: varias ? p.datos.nombre : "", ...coberturaFalta(c) })));
  const lista = faltan.map((f) => `<li class="${f.c.estado}">
      <span class="am-nombre">${f.quien ? `<small>${esc(f.quien)}</small> ` : ""}${esc(nombreCorto(f.c))}</span>
      <span class="am-pista" aria-hidden="true"><i style="--x:${Math.max(0, Math.min(100, f.pct))}%"></i></span>
      <span class="am-dato">${esc(f.texto)}</span></li>`).join("");

  // Qué probar: caminar más (con lo ya calculado en "¿Conviene caminar más?" o calculándolo) y quitar una restricción.
  const probar = [];
  if (d.caminata && CON_RUTAS) {
    const otros = [...estado.escalera.values()].map((v) => v.resumen)
      .filter((r) => r && r.costo != null && r.metas && r.minutos !== d.caminata.minutos);
    const completa = otros.filter((r) => r.metas.cumple === r.metas.total).sort((a, b) => a.minutos - b.minutos)[0];
    const mayores = otros.filter((r) => r.minutos > d.caminata.minutos).sort((a, b) => a.minutos - b.minutos);
    const sinCalcular = estado.P.CAMINATA_OPCIONES.find((x) => x > d.caminata.minutos && !estado.escalera.has(x));
    if (completa) {
      probar.push(`<li>Caminando hasta ${completa.minutos} min sí se logran todas: ${pesos(completa.costo, 0)} en ${esc(completa.tienda)}.
        <button type="button" class="boton-secundario" data-caminata="${completa.minutos}">Ver esa compra</button></li>`);
    } else {
      const ultima = mayores[mayores.length - 1];
      const hecho = ultima ? `Hasta ${ultima.minutos} min tampoco: la mejor logra ${ultima.metas.cumple} de ${ultima.metas.total}. ` : "";
      probar.push(sinCalcular != null
        ? `<li>${hecho}Caminar más suma sucursales que quizá vendan lo que falta.
            <button type="button" class="boton-secundario" data-caminata="${sinCalcular}">Probar hasta ${sinCalcular} min caminando</button></li>`
        : hecho ? `<li>${hecho}</li>` : "");
    }
  }
  const restricciones = conFaltas.flatMap((p) => p.datos.restricciones.map((r) => r[0].toLowerCase() + r.slice(1))
    .concat(d.opciones.listos ? ["solo listos para comer"] : []));
  const unicas = [...new Set(restricciones)];
  if (unicas.length) {
    const quien = varias ? ` de ${conFaltas.map((p) => esc(p.datos.nombre)).join(" y ")}` : "";
    probar.push(`<li>Quitar alguna restricción${quien} y volver a armar la canasta: ${esc(unicas.join(", "))}.</li>`);
  }
  return `<div class="aviso-metas" role="status">
    <p class="am-titulo"><i aria-hidden="true">${m.cumple}/${m.total}</i><span>${titulo}</span></p>
    <p>La que más se acerca logra <b>${m.cumple} de ${m.total}</b>. Es lo máximo que se puede cubrir con lo que venden estas
      sucursales${unicas.length ? " con estas restricciones" : ""}: la compra es válida, solo que no completa.</p>
    <ul class="am-faltan">${lista}</ul>
    ${probar.filter(Boolean).length ? `<p class="am-probar-titulo">Qué podés probar</p><ul class="am-probar">${probar.join("")}</ul>` : ""}
  </div>`;
}

function mostrarSinResultado(d) {
  const sig = siguienteCaminata();
  $("#resultado").innerHTML = `<div class="vacio">
    <p class="mensaje">${esc(d.error)}</p>
    ${d.sin_sucursales && sig != null && CON_RUTAS
      ? `<p>Ampliá el tiempo de caminata para sumar supermercados más lejanos.</p>${botonAmpliar()}`
      : "<p>Probá con otra ubicación o con menos restricciones.</p>"}
    ${avisoTiempos(d)}
  </div>`;
  enlazarAmpliar();
}

// Aviso discreto si la sucursal elegida tiene precios de un día anterior al más reciente de la base.
function avisoFechaHTML(s, d) {
  if (!haceTexto(s)) return "";
  return `<p class="aviso-fecha"><i aria-hidden="true">i</i><span>${esc(nombreTienda(s))} tiene ${esc(haceTexto(s))}
    (SEPA del ${esc(fechaTexto(s.fecha_precios))}): su cadena no publicó los del ${esc(fechaTexto(d.fecha_precios))}.</span></p>`;
}

// La fecha de los precios en la tabla de sucursales: la de todas o, si alguna es de un día anterior, cuál.
function fechasTablaTexto(d) {
  const viejas = d.sucursales.filter((x) => x.dias_precios > 0).length;
  return viejas ? `Precios SEPA del ${esc(fechaTexto(d.fecha_precios))}, salvo ${viejas === 1 ? "la que dice" : "las que dicen"} otra fecha (su cadena no publicó ese día y se usan sus últimos precios, de hasta 15 días).`
    : `Precios SEPA del ${esc(fechaTexto(d.fecha_precios))}.`;
}

function mostrar(d) {
  const t = d.ticket, s = t.tienda, varias = d.personas.length > 1;
  const elegida = d.sucursales.find((x) => x.elegida);
  const otras = d.sucursales.filter((x) => !x.elegida && x.costo != null);
  const masBarataOtra = otras.length ? otras.reduce((m, x) => (x.costo < m.costo ? x : m)) : null;
  const avisos = d.personas.flatMap((p) => p.requerimientos.avisos.map((a) => (varias ? `${p.datos.nombre}: ${a}` : a)));
  const metas = d.personas.map(metasCubiertas);
  const totalMetas = metasHogar(d).total;
  const porTiempo = Boolean(d.caminata);
  const pestanas = varias ? `<div class="pestanas" role="tablist" aria-label="Persona">${d.personas.map((p, i) =>
    `<button type="button" role="tab" aria-selected="${i === estado.vista}" aria-controls="por-persona" data-vista="${i}" style="--c:${colorDe(i)}">${esc(p.datos.nombre)}</button>`).join("")}</div>` : "";
  const caminata = textoCaminata(s);
  const cubre = metas.length === 1
    ? `cubre ${metas[0].cumple} de sus ${metas[0].total} metas`
    : `cubre ${metas.map((m, i) => `${m.cumple} de ${m.total} metas de ${esc(d.personas[i].datos.nombre)}`).join(", ")}`;
  const canillas = d.personas.map(aguaCanilla).filter(Boolean);
  const agua = canillas.length
    ? `<p class="ayuda">Agua de la canilla: ${varias ? "entre todos, " : ""}unos <b>${fmt(canillas.reduce((s, c) => s + c.falta, 0), 1)} L por día</b>, además de la que traen los alimentos.</p>`
    : "";
  const motivo = elegida && elegida.faltantes.length
    ? `Es la que más se acerca a todas las metas y, entre las que cubren igual, la más barata.`
    : `Es la más barata entre las que cubren todas las metas${varias ? " de todos" : ""}.`;
  estado.vistaDos = false;
  const cifras = cifrasCompra(d, null);

  $("#resultado").innerHTML = `
  <nav class="indice" aria-label="Secciones del resultado">
    <a href="#tu-compra">Tu compra</a><a href="#donde-comprar">Dónde comprar</a><a href="#lo-que-come">${varias ? "Cada persona" : "Lo que come"}</a><a href="#como-se-elige">Cómo se elige</a>
  </nav>
  <div class="encabezado-resultado" id="tu-compra" tabindex="-1">
    <div class="columna-ticket">${columnaTicketHTML(d)}</div>
    <div class="resumen">
      <div class="respuesta">
        <p class="resumen-etiqueta">Tu compra para ${esc(d.periodo)}</p>
        <p class="resumen-total"><b id="resumen-total" data-valor="${cifras.total}">${pesos(cifras.total, 0)}</b></p>
        <p class="resumen-donde" id="resumen-donde">${cifras.donde}</p>
        <ul class="datos-compra" id="datos-compra">${cifras.datos}</ul>
      </div>
      ${avisoFechaHTML(s, d)}
      <p class="sr-only">${cubre}</p>
      ${avisoMetasHTML(d)}
      <div class="llegar">
        <p class="llegar-tiempo">${ICONO.caminar}<span>${caminata ? esc(caminata) : `${fmt(s.distancia_km, 1)} km en línea recta`}</span></p>
        <p class="llegar-dato">${ICONO.pin}<span>${esc(s.direccion)}${s.localidad ? `, ${esc(s.localidad)}` : ""}</span></p>
        <p class="llegar-dato">${ICONO.reloj}<span>Hoy ${esc(s.hoy.dia)}: ${esc(s.hoy.horario)}</span></p>
        <a href="#donde-comprar" class="boton-secundario">Ver el recorrido</a>
      </div>
      <p class="ayuda motivo">${motivo}${masBarataOtra && masBarataOtra.costo < t.total && masBarataOtra.faltantes.length
        ? ` La más barata que encontramos cuesta ${pesos(masBarataOtra.costo, 0)} en ${esc(masBarataOtra.bandera)}, pero no cubre: ${esc(masBarataOtra.faltantes.slice(0, 2).join("; "))}${masBarataOtra.faltantes.length > 2 ? "…" : ""}.`
        : masBarataOtra ? ` La siguiente opción cuesta ${pesos(masBarataOtra.costo, 0)}.` : ""}</p>
      ${agua}
      ${comparacionHTML(d)}
      <section class="ahorrar" aria-labelledby="t-ahorrar">
        <h2 id="t-ahorrar" class="ahorrar-titulo">Para pagar menos</h2>
        ${escaleraHTML(d)}
        <div class="dos" id="dos">${dosInterior(d)}</div>
      </section>
      ${varias ? `<div class="comensales">${d.personas.map((p, i) => `<span style="--c:${colorDe(i)}">${esc(p.datos.nombre)}</span>`).join("")}</div>` : ""}
      <div class="avisos">${avisoTiempos(d)}${avisos.map((a) => `<p class="aviso">${esc(a)}</p>`).join("")}</div>
    </div>
  </div>

  <section class="bloque" id="donde-comprar" tabindex="-1"><h2>Dónde comprar</h2>
    <p class="ayuda">${porTiempo
      ? `Supermercados a menos de ${d.caminata.minutos} min caminando${d.caminata.fuente === "ruta" ? " por la calle (rutas peatonales de OpenRouteService)" : " (tiempo estimado por distancia)"}: la más cercana de cada cadena y, si faltaban, las que siguen. En cada una se resolvió la canasta completa con sus precios.`
      : "La más cercana de cada cadena y, si faltaban, las que siguen. En cada una se resolvió la canasta completa con sus precios."}
      ${fechasTablaTexto(d)}</p>
    <div id="mapa" role="img" aria-label="Mapa con el lugar elegido, las sucursales comparadas y el recorrido a la elegida"></div>
    <p class="ayuda" id="mapa-leyenda"></p>
    <p class="ayuda" id="mapa-leyenda-dos"></p>
    <div class="tabla-envoltorio" role="region" aria-labelledby="t-sucursales" tabindex="0"><table class="tabla-sucursales">
      <caption id="t-sucursales" class="sr-only">Sucursales comparadas: costo de la canasta y qué no cubre cada una</caption>
      <thead><tr><th>Sucursal</th><th class="num">${porTiempo ? "Caminando" : "Distancia"}</th><th class="num">Costo</th><th class="num">Diferencia</th><th>Qué no cubre</th></tr></thead>
      <tbody>${d.sucursales.map((x) => `<tr class="${x.elegida ? "elegida" : ""}">
        <td class="ts-nombre">${esc(x.bandera)} ${esc(x.sucursal)}${x.elegida ? ' <span class="marca-elegida">elegida</span>' : ""}<div class="nota">${esc(x.direccion)}${haceTexto(x) ? ` · <span class="ts-fecha">${esc(`precios del ${fechaTexto(x.fecha_precios)}, ${haceTexto(x).replace("precios de ", "")}`)}</span>` : ""}</div></td>
        <td class="num" data-etiqueta="${porTiempo ? "Caminando" : "Distancia"}">${porTiempo ? esc(textoCaminata(x, true)) : `${fmt(x.distancia_km, 1)} km`}</td>
        <td class="num" data-etiqueta="Costo">${x.costo != null ? pesos(x.costo, 0) : "—"}</td>
        <td class="num" data-etiqueta="Diferencia">${x.costo != null && !x.elegida ? `${x.costo >= t.total ? "+" : "−"}${pesos(Math.abs(x.costo - t.total), 0)}` : "—"}</td>
        <td class="ts-falta">${x.costo == null ? esc(x.mensaje) : x.faltantes.length
          ? `<span class="ts-metas">${totalMetas - x.faltantes.length}/${totalMetas} metas</span> ${esc(x.faltantes.join("; "))}` : "Cubre todo"}</td></tr>`).join("")}</tbody></table></div>
  </section>

  <section class="bloque bloque-largo" id="lo-que-come" tabindex="-1"><h2>${varias ? "Lo que necesita cada uno" : "Lo que necesita y lo que come"}</h2>
    <p class="ayuda">${varias ? "Cada persona tiene su propia dieta dentro de la misma compra. Elegí a quién ver." : "Cada paso del cálculo usa el resultado del anterior."}</p>
    ${pestanas}
    <div id="por-persona" role="tabpanel">${bloquePersona(d, estado.vista)}</div>
  </section>

  <section class="bloque bloque-largo" id="como-se-elige" tabindex="-1"><h2>Cómo se elige la compra</h2>
    <p class="ayuda">Es el problema de la dieta (Stigler, 1945), resuelto en cada sucursal con programación lineal entera y el solver HiGHS.</p>
    <ol class="etapas">
      ${CON_RUTAS && d.caminata ? `<li><p class="e-n">0</p><p class="e-titulo">Filtrar por distancia</p>
        <p>Solo las sucursales a menos de ${d.caminata.minutos} min caminando entran en la comparación.</p></li>` : ""}
      <li><p class="e-n">1</p><p class="e-titulo">Cumplir</p>
        <p>Lo mejor que se puede cubrir con lo que vende la sucursal: energía (±5 %), cada nutriente entre su mínimo y su máximo, y las Guías.</p></li>
      <li><p class="e-n">2</p><p class="e-titulo">Lo más barato</p>
        <p>Sin empeorar nada de lo anterior, la compra de menor costo con envases enteros (lo suelto, de a 100 g).</p></li>
      <li><p class="e-n">3</p><p class="e-titulo">Elegir la sucursal</p>
        <p>Gana la que mejor cumple y, entre las que cumplen igual, la más barata.</p></li>
    </ol>
    <ul class="datos-modelo">
      <li><b>${fmt(d.modelo.productos_considerados)}</b><span>productos considerados en la elegida</span></li>
      <li><b>${fmt(d.modelo.variables)}</b><span>variables</span></li>
      <li><b>${fmt(d.modelo.metas)}</b><span>metas</span></li>
      <li><b>${fmt(d.modelo.gap * 100, 0)} %</b><span>tolerancia en el costo</span></li>
      <li><b>${fmt(d.catalogo.productos_canasta)}</b><span>de ${fmt(d.catalogo.productos_total)} productos de SEPA sirven para una canasta</span></li>
    </ul>
    <details class="detalle-largo"><summary>Más detalle del modelo</summary>
      <p>Cada persona come solo lo que es apto para ella y ningún alimento pasa de dos porciones por día, para que haya variedad${d.opciones.agua === "canilla" ? "" : " (el agua y la soda, hasta la meta de agua del día)"}. Lo que
        sobra de un envase queda para después, pero se paga. En cada sucursal se usan los productos más baratos de cada tipo para cada persona.</p>
      <p>Siempre quedan afuera: ${esc(d.catalogo.excluidos_siempre)}</p>
    </details>
  </section>`;

  $$(".pestanas button").forEach((b) => b.addEventListener("click", () => {
    estado.vista = Number(b.dataset.vista);
    $$(".pestanas button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    $("#por-persona").innerHTML = bloquePersona(d, estado.vista);
  }));
  enlazarAmpliar();
  seguirIndice();
  // El ticket sale de la impresora renglón por renglón; el total cuenta hasta su valor.
  animarTicket();
  contar($("#resumen-total"));
  dibujarMapa(d);
  dibujarDosEnMapa(d);
  const suave = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  $("#resultado").scrollIntoView({ behavior: suave ? "smooth" : "auto", block: "start" });
}

// El índice del resultado marca la sección que se está viendo (la de más arriba entre las visibles). Sin
// IntersectionObserver, queda como una lista de enlaces sin marca.
function seguirIndice() {
  if (estado.indice) { estado.indice.disconnect(); estado.indice = null; }
  const enlaces = $$(".indice a");
  if (!enlaces.length || !window.IntersectionObserver) return;
  const secciones = enlaces.map((a) => document.getElementById(a.hash.slice(1))).filter(Boolean);
  const visibles = new Set();
  const marcar = () => {
    const actual = secciones.find((s) => visibles.has(s)) || null;
    enlaces.forEach((a) => (a.hash.slice(1) === (actual && actual.id) ? a.setAttribute("aria-current", "true") : a.removeAttribute("aria-current")));
  };
  estado.indice = new IntersectionObserver((entradas) => {
    entradas.forEach((e) => (e.isIntersecting ? visibles.add(e.target) : visibles.delete(e.target)));
    marcar();
  }, { rootMargin: "-80px 0px -55% 0px" });
  secciones.forEach((s) => estado.indice.observe(s));
}

const color = (variable) => getComputedStyle(document.documentElement).getPropertyValue(variable).trim();

function dibujarMapa(d) {
  if (estado.mapaResultado) { estado.mapaResultado.remove(); estado.mapaResultado = null; }
  estado.capaDos = null;
  estado.puntosMapa = null;
  if (typeof L === "undefined") { $("#mapa").hidden = true; return; }
  const mapa = L.map("mapa", { scrollWheelZoom: false });
  estado.mapaResultado = mapa;
  capaBase().addTo(mapa);
  const origen = [d.ubicacion.lat, d.ubicacion.lon];
  const puntos = [origen];
  estado.puntosMapa = puntos;      // la compra en dos súper suma el segundo (y el recorrido encuadra todo)
  const comparadas = new Set(d.sucursales.map((x) => x.id));
  // Las que se consultaron pero quedan fuera del límite: atenuadas, para ver qué hay un poco más lejos.
  const r = estado.ultimaRuta;
  if (d.caminata && r && r.candidatas) {
    for (const c of r.candidatas) {
      const tiempo = r.tiempos[c.id];
      if (comparadas.has(c.id) || !tiempo || tiempo.minutos <= d.caminata.minutos) continue;
      L.circleMarker([c.lat, c.lon], { radius: 4, color: color("--tinta-suave"), weight: 1, opacity: 0.6, fillOpacity: 0.25, className: "m-fuera" })
        .addTo(mapa).bindTooltip(`Fuera del límite: ${textoCaminata({ ...tiempo, fuente_tiempo: tiempo.fuente }, true)}`);
    }
  }
  for (const x of d.sucursales) {
    puntos.push([x.lat, x.lon]);
    const etiqueta = `${x.bandera} ${x.sucursal}: ${x.costo != null ? pesos(x.costo, 0) : "sin canasta"}${x.minutos != null ? `, ${textoCaminata(x, true)}` : ""}`;
    L.circleMarker([x.lat, x.lon], { radius: x.elegida ? 10 : 6, color: x.elegida ? color("--tinta") : color("--tinta-suave"),
      fillColor: x.elegida ? color("--acento") : color("--tinta-suave"),
      weight: x.elegida ? 3 : 2, fillOpacity: 0.85, className: x.elegida ? "m-elegida" : "m-sucursal" }).addTo(mapa).bindTooltip(etiqueta, { permanent: Boolean(x.elegida), direction: "top" });
  }
  L.circleMarker(origen, { radius: 8, color: color("--foco"), fillOpacity: 0.9, className: "m-vos" }).addTo(mapa).bindTooltip("Vos");
  mapa.fitBounds(puntos, { padding: [30, 30], maxZoom: 16 });
  // Solo mientras sea el mapa vigente: al cambiar de resultado, el contenedor viejo se achica a cero después de que el
  // mapa ya se quitó, e invalidateSize sobre un mapa quitado rompe Leaflet.
  if (window.ResizeObserver) new ResizeObserver(() => { if (estado.mapaResultado === mapa) mapa.invalidateSize(); }).observe($("#mapa"));

  // Recorrido a pie hasta la elegida, solo con rutas reales (nunca se dibuja una ruta inventada).
  const s = d.ticket.tienda, leyenda = $("#mapa-leyenda");
  if (!d.caminata || d.caminata.fuente !== "ruta") {
    leyenda.textContent = d.caminata ? "Sin recorrido: los tiempos son estimados." : "";
    return;
  }
  mapa.attributionControl.addAttribution('Rutas &copy; <a href="https://openrouteservice.org/">openrouteservice.org</a> by HeiGIT');
  leyenda.textContent = "Buscando el recorrido a pie…";
  Rutas.recorrido(estado.P, d.ubicacion, { lat: s.lat, lon: s.lon }).then((rec) => {
    if (estado.mapaResultado !== mapa) return;            // ya se armó otra canasta
    if (!rec) { leyenda.textContent = "No se pudo trazar el recorrido a pie."; return; }
    const linea = L.polyline(rec.puntos, { color: color("--ruta"), weight: 5, opacity: 0.9, className: "ruta-animada",
      lineCap: "round", lineJoin: "round" }).addTo(mapa);
    const trazo = linea.getElement();
    if (trazo) trazo.setAttribute("pathLength", "1");          // para dibujarlo de punta a punta con CSS
    mapa.fitBounds(L.latLngBounds(puntos).extend(linea.getBounds()), { padding: [30, 30], maxZoom: 17 });
    leyenda.textContent = `Recorrido a pie hasta ${s.bandera} ${s.sucursal}: ${textoCaminata({ minutos: rec.minutos, metros: rec.metros ? Math.round(rec.metros) : null, fuente_tiempo: "ruta" })}.`;
  });
}

// ============================================================
// Inicio
// ============================================================

// Un enlace como ?perfiles=celiaca,vegano&lat=-34.60&lon=-58.38&dias=14&listos=1&agua=compra arma esa canasta
// directamente (agua: compra, bebidas o canilla, la predeterminada); con &dos=1, también la compra en dos súper;
// &promos=0 la arma sin promociones (&promos=1, con ellas, si la base trae alguna).
function desdeEnlace() {
  const q = PARAMETROS;
  const ids = (q.get("perfiles") || q.get("perfil") || "").split(",").filter(Boolean);
  const perfiles = ids.map((id) => estado.perfiles.find((f) => f.id === id)).filter(Boolean);
  if (perfiles.length) {
    estado.hogar = perfiles.slice(0, estado.P.PERSONAS_MAXIMAS).map((f) => ({ ...PERSONA_NUEVA, nombre: f.nombre,
      ...datosDePerfil(f), perfil: f.id }));
    estado.actual = 0;
  }
  if (q.get("dias") && q.get("dias") in estado.P.DIAS_PERIODO) estado.dias = Number(q.get("dias"));
  if (q.has("listos")) estado.listos = q.get("listos") === "1";
  if (q.get("agua") in estado.P.AGUA_MODOS) estado.agua = q.get("agua");
  if (q.has("promos")) estado.promos = estado.promosEnBase > 0 && q.get("promos") === "1";
  const lat = parseFloat(q.get("lat")), lon = parseFloat(q.get("lon"));
  const conLugar = Number.isFinite(lat) && Number.isFinite(lon);
  if (conLugar) estado.lugar = { lat, lon, nombre: `${fmt(lat, 4)}, ${fmt(lon, 4)}`, precision: "punto" };
  return perfiles.length > 0 && conLugar;
}

async function iniciar() {
  const aviso = $("#estado-datos");
  if (!window.DecompressionStream || !window.WebAssembly) {
    aviso.textContent = "Este navegador es muy viejo para calcular la canasta: probá con una versión actual de Chrome, Firefox, Edge o Safari.";
    aviso.classList.add("error");
    return;
  }
  let resumen;
  try {
    motor.iniciar();
    ({ resumen } = await motor.pedir("paquete", { meta: $("#datos-meta").textContent, binario: $("#datos-binario").textContent }));
  } catch (err) {
    aviso.textContent = `No se pudieron leer los datos de la página (${err.message}).`;
    aviso.classList.add("error");
    return;
  }
  estado.P = resumen.parametros;
  estado.perfiles = resumen.perfiles;
  estado.criterios = resumen.criterios;
  estado.condiciones = resumen.condiciones;
  estado.caminata = estado.P.CAMINATA_MINUTOS;
  estado.agua = estado.P.AGUA_MODO_PREDETERMINADO;
  estado.promosEnBase = resumen.promosAplicables || 0;
  estado.promos = estado.promosEnBase > 0;           // por defecto, si la base trae alguna aplicable
  estado.listo = true;
  aviso.innerHTML = `<span><b>${esc(resumen.fecha.split("-").reverse().join("/"))}</b>precios oficiales (SEPA)</span>
    <span><b>${fmt(resumen.productos)}</b>alimentos</span><span><b>${fmt(resumen.tiendas)}</b>supermercados</span>`;
  aviso.classList.add("listo");
  // El ticket de la cabecera, con los datos reales del día.
  const tc = $("#ticket-cabecera");
  tc.innerHTML = `<p class="t-marca">CHANGUITO SANO</p><p class="t-centro">Precios oficiales SEPA</p><hr>
    <p class="t-linea"><span>Fecha de los precios</span><span>${esc(resumen.fecha.split("-").reverse().join("/"))}</span></p>
    <p class="t-linea"><span>Alimentos con nutrientes</span><span>${fmt(resumen.productos)}</span></p>
    <p class="t-linea"><span>Supermercados</span><span>${fmt(resumen.tiendas)}</span></p>
    <p class="t-linea"><span>Nutrientes por alimento</span><span>33</span></p>
    <p class="t-linea"><span>Restricciones</span><span>${Object.keys(estado.P.RESTRICCIONES).length - estado.P.CONDICIONES.length}</span></p>
    <p class="t-linea"><span>Condiciones médicas</span><span>${estado.P.CONDICIONES.length}</span></p><hr>
    <p class="t-total"><span>TOTAL</span><span>EL MÁS BAJO</span></p>
    <p class="t-centro t-gracias">*** a pocos minutos ***</p>`;
  [...tc.children].forEach((el, i) => el.style.setProperty("--i", i));
  tc.classList.add("imprimiendo");
  // El ticket de la portada se inclina un poco hacia donde está el mouse (solo con mouse y sin "reducir movimiento").
  if (!SIN_MOVIMIENTO.matches && matchMedia("(pointer: fine)").matches) {
    const cab = $(".cabecera"), imp = $(".impresora-cabecera");
    cab.addEventListener("pointermove", (e) => {
      const r = cab.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
      imp.style.setProperty("--ry", `${(x * 10).toFixed(2)}deg`);
      imp.style.setProperty("--rx", `${(-y * 8).toFixed(2)}deg`);
    });
    cab.addEventListener("pointerleave", () => { imp.style.setProperty("--ry", "0deg"); imp.style.setProperty("--rx", "0deg"); });
  }
  const guardado = CON_CASO ? null : leerGuardado();
  const pedida = Number(PARAMETROS.get("caminata"));
  if (estado.P.CAMINATA_OPCIONES.includes(pedida)) estado.caminata = pedida;
  $("#campo-caminata").hidden = !CON_RUTAS;
  const automatico = desdeEnlace();
  prepararHogar();
  prepararUbicacion();
  prepararCompra();
  prepararTextoLibre();
  prepararPasos();
  cargarEditor();
  dibujarPersonas();
  if (guardado) avisoRetomar(guardado);
  $("#formulario").addEventListener("submit", armar);
  // Los botones del resultado que no se rehacen con cada vista: imprimir, la compra en dos súper y el selector del ticket.
  $("#resultado").addEventListener("click", (e) => {
    const b = e.target.closest("#imprimir, [data-dos], [data-vista]");
    if (!b || b.disabled) return;
    if (b.id === "imprimir") window.print();
    else if (b.hasAttribute("data-dos")) calcularDos();
    else cambiarVista(b.dataset.vista === "dos", b);
  });
  // ?dos=1: después de armar la canasta, calcula también la compra en dos súper (para mostrarla de una).
  if (automatico) armar().then(() => { if (PARAMETROS.get("dos") === "1") calcularDos(true); });
}

iniciar();
