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
};
const GRUPOS_RESTRICCIONES = [
  { titulo: "Dieta", claves: ["celiaquia", "vegetariano", "vegano", "sin_lactosa", "sin_ultraprocesados"] },
  { titulo: "Alergias (también sin trazas)", alergia: true },
  { titulo: "Salud", claves: ["hipertension", "diabetes"] },
];
const PERSONA_NUEVA = { nombre: "", sexo: "F", edad: 34, peso_kg: 63, altura_cm: 163, actividad: "liviana",
  objetivo: "mantener", etapa: "general", trimestre: 2, restricciones: [] };

const estado = {
  P: null, perfiles: [], hogar: [{ ...PERSONA_NUEVA }], actual: 0, lugar: null, dias: 7, listos: false,
  listo: false, ocupado: false, resultado: null, vista: 0, mapa: null, marcador: null,
};

// ============================================================
// Motor: Web Worker con el código de motor.js (o, si el navegador no lo permite, en esta misma página)
// ============================================================

const motor = (() => {
  let worker = null, siguiente = 0;
  const pendientes = new Map();
  function iniciar() {
    const codigo = $("#motor-codigo").textContent;
    try {
      // ?motor=pagina lo corre en esta misma página (lo usan los tests: Chrome headless no espera a los workers).
      if (new URLSearchParams(location.search).get("motor") === "pagina") throw new Error("motor en la página");
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
// Guardado local (comodidad: si el navegador no deja, no pasa nada)
// ============================================================

function guardar() {
  try {
    localStorage.setItem(CLAVE_GUARDADO, JSON.stringify({ hogar: estado.hogar, lugar: estado.lugar, dias: estado.dias, listos: estado.listos }));
  } catch (err) { /* sin almacenamiento */ }
}

function recuperar() {
  try {
    const g = JSON.parse(localStorage.getItem(CLAVE_GUARDADO) || "null");
    if (g && Array.isArray(g.hogar) && g.hogar.length) {
      estado.hogar = g.hogar.slice(0, estado.P.PERSONAS_MAXIMAS).map((p) => ({ ...PERSONA_NUEVA, ...p }));
      estado.lugar = g.lugar || null;
      estado.dias = String(g.dias) in estado.P.DIAS_PERIODO ? g.dias : 7;
      estado.listos = Boolean(g.listos);
    }
  } catch (err) { /* sin almacenamiento */ }
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
  if (!(p.edad >= P.EDAD_MINIMA && p.edad <= P.EDAD_MAXIMA)) {
    e.push(`La edad tiene que estar entre ${P.EDAD_MINIMA} y ${P.EDAD_MAXIMA} años (antes de los ${P.EDAD_MINIMA}, la alimentación la indica el pediatra).`);
  }
  if (!(p.peso_kg >= P.PESO_RANGO_KG[0] && p.peso_kg <= P.PESO_RANGO_KG[1])) e.push("Revisá el peso.");
  if (p.altura_cm != null && !(p.altura_cm >= P.ALTURA_RANGO_CM[0] && p.altura_cm <= P.ALTURA_RANGO_CM[1])) e.push("Revisá la altura.");
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
  $("#resumen-hogar").textContent = estado.lugar
    ? `${quienes}, compra para ${periodo}, cerca de ${estado.lugar.corto || estado.lugar.nombre}.`
    : `${quienes}, compra para ${periodo}. Falta elegir dónde comprás.`;
}

function cargarEditor() {
  const p = estado.hogar[estado.actual];
  $("#p-nombre").value = p.nombre;
  $("#p-perfil").value = "";
  form()["p-sexo"].value = p.sexo;
  $("#p-edad").value = p.edad ?? "";
  $("#p-peso").value = p.peso_kg ?? "";
  $("#p-altura").value = p.altura_cm ?? "";
  form()["p-etapa"].value = p.etapa;
  form()["p-trimestre"].value = String(p.trimestre || 2);
  form()["p-actividad"].value = p.actividad;
  form()["p-objetivo"].value = p.objetivo;
  $$('[name="p-restriccion"]').forEach((c) => { c.checked = p.restricciones.includes(c.value); });
  actualizarVisibles();
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
  p.trimestre = Number(form()["p-trimestre"].value);
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
}

function alCambiarEditor(e) {
  if (e.target.name === "p-restriccion" && e.target.checked) {
    if (e.target.value === "vegano") $('[name="p-restriccion"][value="vegetariano"]').checked = false;
    if (e.target.value === "vegetariano") $('[name="p-restriccion"][value="vegano"]').checked = false;
  }
  leerEditor();
  actualizarVisibles();
  dibujarPersonas();
  guardar();
}

function cargarPerfil(id) {
  const f = estado.perfiles.find((x) => x.id === id);
  if (!f) return;
  const p = estado.hogar[estado.actual];
  Object.assign(p, { sexo: f.sexo, edad: f.edad, peso_kg: f.peso_kg, altura_cm: f.altura_cm, actividad: f.actividad,
    objetivo: f.objetivo, etapa: f.etapa, trimestre: f.trimestre || 2, restricciones: [...f.restricciones] });
  if (!p.nombre.trim()) p.nombre = f.nombre;
  cargarEditor();
  dibujarPersonas();
  guardar();
}

function prepararHogar() {
  const P = estado.P;
  $("#p-perfil").innerHTML = `<option value="">Elegí un perfil…</option>` +
    estado.perfiles.map((f) => `<option value="${esc(f.id)}">${esc(f.nombre)}: ${esc(f.descripcion)}</option>`).join("");
  $("#actividades").innerHTML = Object.entries(P.ACTIVIDAD).map(([clave, a], i) =>
    `<label><input type="radio" name="p-actividad" value="${clave}"><span style="--nivel:${i + 1}">${esc(a.nombre)}</span></label>`).join("");
  $("#objetivos").innerHTML = Object.entries(P.OBJETIVO).map(([clave, o]) =>
    `<label><input type="radio" name="p-objetivo" value="${clave}"><span>${esc(o.nombre)}</span></label>`).join("");
  $("#restricciones").innerHTML = GRUPOS_RESTRICCIONES.map((g) => {
    const claves = g.alergia ? Object.keys(P.ALERGIAS) : g.claves;
    return `<div class="grupo-restricciones"><h3>${esc(g.titulo)}</h3><div class="chips">${claves.map((k) =>
      `<label class="chip"><input type="checkbox" name="p-restriccion" value="${k}"><span>${esc(P.RESTRICCIONES[k].replace(/^Alergia (al|a la|a) /, ""))}</span></label>`).join("")}</div></div>`;
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
    $("#p-perfil").focus();
  });
  $("#editor").addEventListener("input", alCambiarEditor);
  $("#editor").addEventListener("change", (e) => {
    if (e.target.id === "p-perfil") { cargarPerfil(e.target.value); return; }
    alCambiarEditor(e);
  });
}

// ============================================================
// Ubicación: Georef, GPS y mapa
// ============================================================

function mostrarLugar(texto, error = false) {
  const el = $("#ubicacion-elegida");
  el.textContent = texto;
  el.classList.toggle("error", error);
}

function elegirLugar(lugar, mover = true) {
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
  guardar();
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
  if (nombre && estado.lugar && estado.lugar.lat === lat) {
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
      nombre: `${l.nombre}, ${l.departamento.nombre}, ${l.provincia.nombre}`, lat: l.centroide.lat, lon: l.centroide.lon,
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
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(estado.mapa);
    estado.mapa.on("click", (e) => puntoDelMapa(e.latlng.lat, e.latlng.lng));
  }
  if (estado.lugar) elegirLugar(estado.lugar);
}

// ============================================================
// Opciones de la compra
// ============================================================

function prepararCompra() {
  $("#periodos").innerHTML = Object.entries(estado.P.DIAS_PERIODO).map(([dias, nombre]) =>
    `<label><input type="radio" name="dias" value="${dias}" ${Number(dias) === estado.dias ? "checked" : ""}><span>${esc(nombre[0].toUpperCase() + nombre.slice(1))}</span></label>`).join("");
  $("#periodos").addEventListener("change", (e) => { estado.dias = Number(e.target.value); dibujarPersonas(); guardar(); });
  $("#listos").checked = estado.listos;
  $("#listos").addEventListener("change", (e) => { estado.listos = e.target.checked; guardar(); });
}

// ============================================================
// Armar la canasta
// ============================================================

function cargando(texto, fraccion) {
  const pct = Math.round(fraccion * 100);
  $("#resultado").innerHTML = `<div class="cargando">
    <div class="ticket" aria-hidden="true"><p class="t-centro">Calculando…</p><hr><p>Comparando los supermercados</p>
      <p>de tu zona y buscando la compra</p><p>más barata que cubre lo que</p><p>necesita cada uno.</p><hr>
      <p class="t-total"><span>TOTAL</span><span>$ …</span></p></div>
    <div class="progreso" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${pct}"><i style="width:${pct}%"></i></div>
    <p>${esc(texto)}</p></div>`;
}

async function armar(e) {
  if (e) e.preventDefault();
  if (estado.ocupado) return;
  const msj = $("#mensaje");
  msj.textContent = "";
  if (!estado.listo) { msj.textContent = "Los precios se están preparando: esperá unos segundos."; return; }
  const conError = estado.hogar.findIndex((p) => erroresPersona(p).length);
  if (conError >= 0) {
    estado.actual = conError;
    cargarEditor();
    dibujarPersonas();
    msj.textContent = `Revisá los datos de ${nombrePersona(estado.hogar[conError], conError)}.`;
    return;
  }
  if (!estado.lugar) { msj.textContent = "Falta elegir dónde comprás (paso 2)."; $("#busqueda").focus(); return; }
  const personas = estado.hogar.map((p, i) => ({ ...p, nombre: nombrePersona(p, i),
    objetivo: p.edad < 18 || p.etapa !== "general" ? "mantener" : p.objetivo,
    trimestre: p.etapa === "embarazo" ? p.trimestre : null }));
  estado.ocupado = true;
  $("#armar").disabled = true;
  cargando("Preparando el cálculo…", 0.03);
  try {
    const pedido = { personas, lat: estado.lugar.lat, lon: estado.lugar.lon, dias: estado.dias, listos: estado.listos };
    const { resultado } = await motor.pedir("armar", { pedido },
      (a) => cargando(a.hechas ? `Sucursales resueltas: ${a.hechas} de ${a.total} (la última, ${a.sucursal})`
        : `Resolviendo la canasta en ${a.total} sucursales cercanas…`, 0.05 + 0.95 * a.hechas / a.total));
    estado.resultado = resultado;
    estado.vista = 0;
    if (resultado.error && !resultado.ticket) {
      $("#resultado").innerHTML = `<div class="vacio"><p class="mensaje">${esc(resultado.error)}</p></div>`;
    } else {
      mostrar(resultado);
    }
    $("#resultado-json").textContent = JSON.stringify(resultado);
  } catch (err) {
    $("#resultado").innerHTML = `<div class="vacio"><p class="mensaje">${esc(err.message)}</p></div>`;
    $("#resultado-json").textContent = JSON.stringify({ error: err.message });
  } finally {
    estado.ocupado = false;
    $("#armar").disabled = false;
  }
}

// ============================================================
// Resultado
// ============================================================

function ticketHTML(d) {
  const t = d.ticket, s = t.tienda, varias = d.personas.length > 1;
  const fecha = t.fecha_precios.split("-").reverse().join("/");
  let grupoActual = "";
  const items = t.items.map((it) => {
    const cabeza = it.grupo !== grupoActual ? `<p class="t-grupo">${esc(it.grupo)}</p>` : "";
    grupoActual = it.grupo;
    const quien = varias
      ? it.por_persona.map((g, i) => (g > 0 ? `<span class="t-quien" style="--c:${colorDe(i)}">${esc(d.personas[i].datos.nombre)} ${fmt(g)} g</span>` : "")).join("") + "por día"
      : `come ${esc(it.consumo_dia_texto)} por día`;
    return `${cabeza}<div class="t-item">
      <p class="t-nombre">${esc(it.nombre)}</p>
      <p class="t-linea"><span>${esc(it.cantidad)} a ${esc(it.precio_unidad_texto)}</span><span>${fmt(it.subtotal, 2)}</span></p>
      <p class="t-detalle">${quien}${it.sobrante_texto ? `; sobran ${esc(it.sobrante_texto)}` : ""}</p>
      ${it.promocion ? `<p class="t-promo">hay promoción: ${pesos(it.promocion)} c/u (con condiciones)</p>` : ""}
    </div>`;
  }).join("");
  const para = d.personas.map((p) => `${esc(p.datos.nombre)} (${p.datos.sexo === "F" ? "mujer" : "varón"}, ${p.datos.edad})`).join(", ");
  return `<div class="ticket" role="document" aria-label="Ticket de la compra">
    <p class="t-marca">${esc(s.bandera)}</p>
    <p class="t-centro">${esc(s.comercio)}${s.cuit ? `<br>CUIT ${esc(cuit(s.cuit))}` : ""}</p>
    <p class="t-centro">Suc. ${esc(s.sucursal)}<br>${esc(s.direccion)}${s.localidad ? `<br>${esc(s.localidad)}` : ""}</p>
    <p class="t-centro">Hoy ${esc(s.hoy.dia)}: ${esc(s.hoy.horario)}</p>
    <hr>
    <p>Canasta saludable para ${esc(d.periodo)}</p>
    <p>Para: ${para}</p>
    ${d.opciones.listos ? "<p>Solo alimentos listos para comer</p>" : ""}
    <p>Precios SEPA del ${fecha}</p>
    <hr>
    ${items}
    <hr>
    <p class="t-total"><span>TOTAL</span><span>${pesos(t.total)}</span></p>
    <p class="t-linea"><span>Por día</span><span>${pesos(t.costo_diario)}</span></p>
    ${varias ? `<p class="t-linea"><span>Por persona y día</span><span>${pesos(t.costo_diario / d.personas.length)}</span></p>` : ""}
    <p class="t-linea"><span>Cada 1.000 kcal</span><span>${pesos(t.costo_1000_kcal)}</span></p>
    <p class="t-linea"><span>Artículos</span><span>${t.items.length}</span></p>
    <hr>
    <p class="t-centro">Precios de lista. Las promociones<br>no se aplican al total.</p>
  </div>`;
}

function barra(c) {
  if (c.valor == null) return "";
  const tope = Math.max(c.maximo ?? 0, (c.minimo ?? 0) * 1.5, c.valor) || 1;
  const ancho = Math.min(100, (c.valor / tope) * 100);
  const marcaMin = c.minimo ? `<b style="left:${(c.minimo / tope) * 100}%" title="mínimo"></b>` : "";
  const marcaMax = c.maximo ? `<b style="left:calc(${(c.maximo / tope) * 100}% - 2px)" title="máximo"></b>` : "";
  return `<div class="barra ${c.estado}"><i style="width:${ancho}%"></i>${marcaMin}${marcaMax}</div>`;
}

const TEXTO_ESTADO = { cumple: "Cumple", falta: "Falta", excede: "Se pasa", informativa: "Informativa", no_aplica: "No aplica" };
const decimales = (x) => (x == null ? 0 : Math.abs(x) < 10 ? 1 : 0);

function filaCobertura(c) {
  const rango = c.minimo != null && c.maximo != null ? `${fmt(c.minimo, decimales(c.minimo))} a ${fmt(c.maximo, decimales(c.maximo))}`
    : c.minimo != null ? `mín. ${fmt(c.minimo, decimales(c.minimo))}` : `máx. ${fmt(c.maximo, decimales(c.maximo))}`;
  return `<tr><td>${esc(c.nombre)}${c.nota ? `<div class="nota">${esc(c.nota)}</div>` : ""}</td>
    <td class="num">${c.valor == null ? "—" : fmt(c.valor, decimales(c.valor))} ${esc(c.unidad)}</td>
    <td class="num">${rango}</td><td>${barra(c)}</td>
    <td class="estado ${c.estado}">${TEXTO_ESTADO[c.estado]}</td></tr>`;
}

function bloquePersona(d, i) {
  const p = d.personas[i], q = p.requerimientos, r = p.restricciones;
  const energia = p.cobertura.find((c) => c.clave === "energia_kcal");
  const listos = d.opciones.listos ? [{ clave: "listos", nombre: estado.P.LISTOS_NOMBRE, criterio: d.opciones.listos_criterio }] : [];
  const datos = `${p.datos.sexo === "F" ? "mujer" : "varón"} de ${p.datos.edad} años, ${fmt(p.datos.peso_kg, 1)} kg, actividad ${p.datos.actividad.toLowerCase()}`;
  return `
    <p class="ayuda">${esc(p.datos.nombre)}: ${esc(datos)}${p.datos.restricciones.length ? `; ${esc(p.datos.restricciones.join(", ").toLowerCase())}` : ""}.
      Necesita ${fmt(q.energia_kcal)} kcal por día y come ${fmt(energia && energia.valor)} kcal de esta compra.</p>
    <ol class="pasos">${q.pasos.map((s) => `<li><div><h3>${esc(s.titulo)}</h3>
      <p class="formula">${esc(s.formula)}</p><p class="res">${esc(s.resultado)}</p>
      ${s.fuente ? `<p class="fuente">${esc(s.fuente)}</p>` : ""}</div></li>`).join("")}</ol>

    <h3 class="subtitulo">Lo que come por día</h3>
    <p class="ayuda">Frente a su meta: la marca vertical es el mínimo (o el máximo, en sodio, saturadas y azúcares).</p>
    <div class="grupos" role="img" aria-label="Calorías por grupo de alimentos">${p.grupos.map((g) =>
      `<div style="width:${g.pct_kcal}%;background:${COLOR_GRUPO[g.grupo] || "#777"}" title="${esc(g.grupo)}: ${fmt(g.kcal_dia)} kcal">${g.pct_kcal >= 9 ? fmt(g.pct_kcal) + " %" : ""}</div>`).join("")}</div>
    <div class="leyenda-grupos">${p.grupos.map((g) => `<span style="--c:${COLOR_GRUPO[g.grupo] || "#777"}">${esc(g.grupo)}: ${fmt(g.gramos_dia)} g, ${fmt(g.kcal_dia)} kcal</span>`).join("")}</div>
    <div class="tabla-envoltorio"><table>
      <thead><tr><th>Nutriente</th><th class="num">Por día</th><th class="num">Meta</th><th>Cobertura</th><th>Estado</th></tr></thead>
      <tbody>${p.cobertura.map(filaCobertura).join("")}</tbody></table></div>

    <h3 class="subtitulo">Guías Alimentarias</h3>
    <p class="ayuda">Además de los nutrientes, la compra respeta las Guías Alimentarias para la Población Argentina; las reglas semanales se cumplen en promedio.</p>
    <div class="tabla-envoltorio"><table>
      <thead><tr><th>Regla</th><th class="num">Cantidad</th><th class="num">Meta</th><th>Cobertura</th><th>Estado</th></tr></thead>
      <tbody>${p.reglas.map(filaCobertura).join("")}</tbody></table></div>

    <h3 class="subtitulo">Restricciones</h3>
    <p class="ayuda">${fmt(r.productos_aptos)} de los ${fmt(d.catalogo.productos_canasta)} productos de la canasta son aptos.
      Un producto sin datos que lo confirmen no se considera apto.</p>
    <dl class="criterios">
      ${r.criterios.concat(listos).map((c) => {
        const ef = r.efecto.find((x) => x.clave === c.clave);
        return `<div><dt>${esc(c.nombre)}${ef ? ` (deja afuera ${fmt(ef.excluye)} productos)` : ""}</dt><dd>${esc(c.criterio)}</dd></div>`;
      }).join("")}
      ${r.criterios.length || listos.length ? "" : "<div><dt>Sin restricciones</dt><dd>Puede comer cualquier producto de la canasta.</dd></div>"}
    </dl>`;
}

function mostrar(d) {
  const t = d.ticket, s = t.tienda, varias = d.personas.length > 1;
  const otras = d.sucursales.filter((x) => !x.elegida && x.costo != null);
  const masBarataOtra = otras.length ? Math.min(...otras.map((x) => x.costo)) : null;
  const energiaHogar = d.personas.reduce((sum, p) => sum + ((p.cobertura.find((c) => c.clave === "energia_kcal") || {}).valor || 0), 0);
  const avisos = d.personas.flatMap((p) => p.requerimientos.avisos.map((a) => (varias ? `${p.datos.nombre}: ${a}` : a)));
  const pestanas = varias ? `<div class="pestanas" role="tablist" aria-label="Persona">${d.personas.map((p, i) =>
    `<button type="button" role="tab" aria-selected="${i === estado.vista}" aria-controls="por-persona" data-vista="${i}" style="--c:${colorDe(i)}">${esc(p.datos.nombre)}</button>`).join("")}</div>` : "";

  $("#resultado").innerHTML = `
  <div class="encabezado-resultado">
    ${ticketHTML(d)}
    <div class="resumen">
      <h2>Tu compra en ${esc(s.bandera)} ${esc(s.sucursal)}</h2>
      <p class="ayuda">${esc(s.direccion)}, a ${fmt(s.distancia_km, 1)} km. Es la sucursal cercana que mejor cubre las metas
        ${varias ? "de todos" : ""} y, entre las que las cubren igual, la más barata.</p>
      <div class="cifras">
        <div class="cifra"><b>${pesos(t.total, 0)}</b><span>para ${esc(d.periodo)}</span></div>
        <div class="cifra"><b>${pesos(t.costo_diario, 0)}</b><span>por día${varias ? `, ${pesos(t.costo_diario / d.personas.length, 0)} por persona` : ""}</span></div>
        <div class="cifra"><b>${fmt(energiaHogar)} kcal</b><span>por día${varias ? " en el hogar" : ""} (meta ${fmt(d.hogar.energia_kcal)})</span></div>
        <div class="cifra"><b>${t.items.length}</b><span>productos</span></div>
      </div>
      ${varias ? `<div class="comensales">${d.personas.map((p, i) => `<span style="--c:${colorDe(i)}">${esc(p.datos.nombre)}</span>`).join("")}</div>` : ""}
      ${masBarataOtra != null ? `<p class="ayuda">La siguiente opción cercana cuesta ${pesos(masBarataOtra, 0)}.</p>` : ""}
      <div class="avisos">${avisos.map((a) => `<p class="aviso">${esc(a)}</p>`).join("")}</div>
    </div>
  </div>

  <section class="bloque"><h2>${varias ? "Lo que necesita cada uno" : "Lo que necesita y lo que come"}</h2>
    <p class="ayuda">${varias ? "Cada persona tiene su propia dieta dentro de la misma compra. Elegí a quién ver." : "Cada paso del cálculo usa el resultado del anterior."}</p>
    ${pestanas}
    <div id="por-persona" role="tabpanel">${bloquePersona(d, estado.vista)}</div>
  </section>

  <section class="bloque"><h2>Sucursales que comparamos</h2>
    <p class="ayuda">La más cercana de cada cadena y, si faltaban, las que siguen. En cada una se resolvió la canasta completa con sus precios.</p>
    <div class="tabla-envoltorio"><table>
      <thead><tr><th>Sucursal</th><th class="num">Distancia</th><th class="num">Costo</th><th>Qué no cubre</th></tr></thead>
      <tbody>${d.sucursales.map((x) => `<tr class="${x.elegida ? "elegida" : ""}">
        <td>${esc(x.bandera)} ${esc(x.sucursal)}<div class="nota">${esc(x.direccion)}</div></td>
        <td class="num">${fmt(x.distancia_km, 1)} km</td>
        <td class="num">${x.costo != null ? pesos(x.costo, 0) : "—"}</td>
        <td>${x.costo == null ? esc(x.mensaje) : x.faltantes.length ? esc(x.faltantes.join("; ")) : "Cubre todo"}</td></tr>`).join("")}</tbody></table></div>
    <div id="mapa" role="img" aria-label="Mapa con el lugar elegido y las sucursales comparadas"></div>
  </section>

  <section class="bloque"><h2>Cómo se elige la compra</h2>
    <p class="ayuda">Es un problema de la dieta (Stigler, 1945) resuelto en cada sucursal con programación lineal entera (HiGHS, el
      mismo solver que usa el motor de Python), en dos etapas. Primero se busca lo mejor que se puede cumplir con lo que vende la
      sucursal: la energía de cada persona dentro del ±5 %, cada nutriente entre su mínimo y su máximo y las reglas de las Guías.
      Después, sin empeorar nada de eso, la compra más barata con envases enteros (lo suelto, de a 100 g). Cada persona come solo lo
      que es apto para ella y ningún alimento pasa de dos porciones por día, para que haya variedad. Lo que sobra de un envase
      queda para después, pero se paga.</p>
    <p class="ayuda">En la sucursal elegida se consideraron ${fmt(d.modelo.productos_considerados)} productos (los más baratos de cada
      tipo para cada persona), con ${fmt(d.modelo.variables)} variables y ${fmt(d.modelo.metas)} metas y una tolerancia de
      ${fmt(d.modelo.gap * 100, 0)} % en el costo. De los ${fmt(d.catalogo.productos_total)} productos comestibles de SEPA,
      ${fmt(d.catalogo.productos_canasta)} sirven para una canasta; siempre quedan afuera: ${esc(d.catalogo.excluidos_siempre)}</p>
  </section>`;

  $$(".pestanas button").forEach((b) => b.addEventListener("click", () => {
    estado.vista = Number(b.dataset.vista);
    $$(".pestanas button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    $("#por-persona").innerHTML = bloquePersona(d, estado.vista);
  }));
  dibujarMapa(d);
  const suave = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  $("#resultado").scrollIntoView({ behavior: suave ? "smooth" : "auto", block: "start" });
}

function dibujarMapa(d) {
  if (typeof L === "undefined") { $("#mapa").hidden = true; return; }
  const mapa = L.map("mapa", { scrollWheelZoom: false });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 19, attribution: "© OpenStreetMap" }).addTo(mapa);
  const puntos = [[d.ubicacion.lat, d.ubicacion.lon]];
  L.circleMarker(puntos[0], { radius: 8, color: "#1f5fbf", fillOpacity: 0.9 }).addTo(mapa).bindTooltip("Dónde comprás");
  for (const x of d.sucursales) {
    puntos.push([x.lat, x.lon]);
    L.circleMarker([x.lat, x.lon], { radius: x.elegida ? 10 : 6, color: x.elegida ? "#2e6a4c" : "#666", fillOpacity: 0.85 })
      .addTo(mapa).bindTooltip(`${x.bandera} ${x.sucursal}: ${x.costo != null ? pesos(x.costo, 0) : "sin canasta"}`);
  }
  mapa.fitBounds(puntos, { padding: [30, 30], maxZoom: 16 });
}

// ============================================================
// Inicio
// ============================================================

// Un enlace como ?perfiles=celiaca,vegano&lat=-34.60&lon=-58.38&dias=14&listos=1 arma esa canasta directamente.
function desdeEnlace() {
  const q = new URLSearchParams(location.search);
  const ids = (q.get("perfiles") || q.get("perfil") || "").split(",").filter(Boolean);
  const perfiles = ids.map((id) => estado.perfiles.find((f) => f.id === id)).filter(Boolean);
  if (perfiles.length) {
    estado.hogar = perfiles.slice(0, estado.P.PERSONAS_MAXIMAS).map((f) => ({ ...PERSONA_NUEVA, nombre: f.nombre, sexo: f.sexo,
      edad: f.edad, peso_kg: f.peso_kg, altura_cm: f.altura_cm, actividad: f.actividad, objetivo: f.objetivo, etapa: f.etapa,
      trimestre: f.trimestre || 2, restricciones: [...f.restricciones] }));
    estado.actual = 0;
  }
  if (q.get("dias") && q.get("dias") in estado.P.DIAS_PERIODO) estado.dias = Number(q.get("dias"));
  if (q.has("listos")) estado.listos = q.get("listos") === "1";
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
  motor.iniciar();
  let resumen;
  try {
    ({ resumen } = await motor.pedir("paquete", { meta: $("#datos-meta").textContent, binario: $("#datos-binario").textContent }));
  } catch (err) {
    aviso.textContent = `No se pudieron leer los datos de la página (${err.message}).`;
    aviso.classList.add("error");
    return;
  }
  estado.P = resumen.parametros;
  estado.perfiles = resumen.perfiles;
  estado.listo = true;
  aviso.textContent = `Precios del ${resumen.fecha.split("-").reverse().join("/")}: ${fmt(resumen.productos)} alimentos en ${fmt(resumen.tiendas)} supermercados.`;
  recuperar();
  const automatico = desdeEnlace();
  prepararHogar();
  prepararUbicacion();
  prepararCompra();
  cargarEditor();
  dibujarPersonas();
  $("#formulario").addEventListener("submit", armar);
  if (automatico) armar();
}

iniciar();
