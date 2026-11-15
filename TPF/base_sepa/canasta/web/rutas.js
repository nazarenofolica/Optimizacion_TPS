"use strict";

// Rutas peatonales reales con OpenRouteService (perfil foot-walking, datos de OpenStreetMap). Espejo de
// canasta/rutas.py. La clave la incrusta canasta/exportar.py (desde ORS_API_KEY) solo en la página local: la página
// versionada no la lleva. Sin clave o si el servicio falla, los tiempos se estiman con la distancia en línea recta y
// quedan marcados como estimados; nunca se muestran como una ruta real.

const Rutas = (() => {
  function configuracion() {
    try {
      const el = document.getElementById("config-rutas");
      return el ? JSON.parse(el.textContent || "{}") : {};
    } catch (err) {
      return {};
    }
  }
  const cfg = configuracion();
  const clave = () => String(cfg.clave || "").trim();

  class ErrorRutas extends Error {}

  function mensajeError(estado) {
    if (estado === 401 || estado === 403) return "La clave de OpenRouteService no es válida o no tiene permiso para este servicio.";
    if (estado === 429) return "Se agotó la cuota de consultas de OpenRouteService (se renueva cada día).";
    if (estado == null) return "No se pudo conectar con OpenRouteService.";
    return `OpenRouteService respondió con un error (${estado}).`;
  }

  async function pedir(P, recurso, cuerpo) {
    if (!clave()) throw new ErrorRutas("Esta página no tiene una clave de OpenRouteService.");
    const control = new AbortController();
    const reloj = setTimeout(() => control.abort(), P.RUTEO_TIEMPO_ESPERA_S * 1000);
    let r;
    try {
      r = await fetch(`${P.RUTEO_SERVIDOR}/v2/${recurso}`, {
        method: "POST", signal: control.signal,
        headers: { Authorization: clave(), "Content-Type": "application/json", Accept: "application/json, application/geo+json" },
        body: JSON.stringify(cuerpo),
      });
    } catch (err) {
      throw new ErrorRutas(err.name === "AbortError" ? "OpenRouteService tardó demasiado en responder." : mensajeError(null));
    } finally {
      clearTimeout(reloj);
    }
    if (!r.ok) throw new ErrorRutas(mensajeError(r.status));
    try {
      return await r.json();
    } catch (err) {
      throw new ErrorRutas("OpenRouteService devolvió una respuesta inesperada.");
    }
  }

  // Minutos y metros desde origen {lat, lon} a cada candidata [{id, lat, lon}]; null si no hay ruta peatonal.
  async function matriz(P, origen, candidatas) {
    if (!candidatas.length) return [];
    const locations = [[origen.lon, origen.lat], ...candidatas.map((c) => [c.lon, c.lat])];
    const j = await pedir(P, `matrix/${P.RUTEO_PERFIL}`, {
      locations, sources: [0], destinations: candidatas.map((_, k) => k + 1), metrics: ["duration", "distance"],
    });
    const dur = j && j.durations && j.durations[0], dist = j && j.distances && j.distances[0];
    if (!Array.isArray(dur) || !Array.isArray(dist)) throw new ErrorRutas("OpenRouteService devolvió una respuesta inesperada.");
    return dur.map((seg, k) => (seg == null ? null
      : { minutos: Math.round(seg / 60 * 10) / 10, metros: dist[k] == null ? null : Math.round(dist[k]), fuente: "ruta" }));
  }

  // {id: {minutos, metros, fuente}} para las candidatas, y un aviso si hubo que estimar.
  async function tiempos(P, origen, candidatas) {
    try {
      const filas = await matriz(P, origen, candidatas);
      const salida = {};
      candidatas.forEach((c, k) => { if (filas[k]) salida[c.id] = filas[k]; });
      return { tiempos: salida, aviso: null, fuente: "ruta" };
    } catch (err) {
      if (!(err instanceof ErrorRutas)) throw err;
      const salida = {};
      for (const c of candidatas) salida[c.id] = { minutos: Math.round(c.minutos_estimados * 10) / 10, metros: null, fuente: "estimado" };
      return { tiempos: salida, fuente: "estimado",
        aviso: `${err.message} Los tiempos son estimados por distancia en línea recta, no rutas reales.` };
    }
  }

  // Recorrido a pie (GeoJSON) hasta la sucursal: [[lat, lon], ...] con minutos y metros, o null si no se pudo.
  async function recorrido(P, origen, destino) {
    try {
      const j = await pedir(P, `directions/${P.RUTEO_PERFIL}/geojson`, {
        coordinates: [[origen.lon, origen.lat], [destino.lon, destino.lat]],
      });
      const f = j && j.features && j.features[0];
      if (!f || !f.geometry || !Array.isArray(f.geometry.coordinates)) return null;
      const s = (f.properties && f.properties.summary) || {};
      return { puntos: f.geometry.coordinates.map(([lon, lat]) => [lat, lon]),
        minutos: s.duration != null ? s.duration / 60 : null, metros: s.distance ?? null };
    } catch (err) {
      return null;
    }
  }

  return { tiempos, recorrido, matriz, tieneClave: () => Boolean(clave()), ErrorRutas };
})();
