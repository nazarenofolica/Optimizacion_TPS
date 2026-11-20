"""
Arma la respuesta completa para un hogar (una o más personas) y un lugar: requerimientos de cada persona con su
cálculo, restricciones aplicadas, comparación de las sucursales cercanas, el ticket de la elegida y la cobertura de
cada nutriente y regla por persona.

La sucursal elegida es la que mejor cumple las metas de todos (menor déficit ponderado, redondeado al 1 %) y, entre
las que cumplen igual, la más barata. Es la referencia del motor de la página (canasta/web/motor.js), que hace lo
mismo en el navegador.

A pedido, después de ese resultado, dos_super() prueba partir la compra entre la elegida y una vecina (ver su
docstring): no cambia ni hace más lento lo de arriba.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import numpy as np
import pandas as pd

from canasta import config as cfg
from canasta import modelo, oferta
from canasta.requerimientos import Meta, Persona, Requerimientos, calcular

logger = logging.getLogger("canasta.resultado")

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
EXCLUIDOS_SIEMPRE = ("Bebidas alcohólicas, gaseosas, jugos en polvo, energizantes, gelatinas, fórmulas infantiles, "
                     "infusiones, condimentos y comidas preparadas; huesos, carcasas y cueros; y precios mal cargados "
                     f"(menos de 1/{round(1 / cfg.FRACCION_PRECIO_MINIMO)} de la mediana de su subcategoría).")


def _num(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _limpio(v):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    return v


def _cantidad(fila: pd.Series, x: float) -> str:
    if fila["granel"]:
        return f"{_num(x * cfg.PASO_GRANEL_G / 1000, 3)} kg"
    contenido = fila["contenido"]
    unidad = {"g": "g", "ml": "ml"}.get(fila["unidad_contenido"], fila["unidad_contenido"] or "")
    hay_unidades = pd.notna(fila["unidades"]) and fila["unidades"] and fila["unidades"] > 1
    if pd.isna(contenido):              # se vende por unidad (frutas, ajo): no hay peso del envase que mostrar
        return f"{_num(x)} × " + (f"{_num(fila['unidades'])} u." if hay_unidades else "unidad")
    if unidad == "g" and contenido >= 1000:
        envase = f"{_num(contenido / 1000, 3 if contenido % 1000 else 0)} kg"
    elif unidad == "ml" and contenido >= 1000:
        envase = f"{_num(contenido / 1000, 2 if contenido % 1000 else 0)} l"
    else:
        envase = f"{_num(contenido)} {unidad}".strip()
    if hay_unidades:
        unidades = f"{_num(fila['unidades'])} u."
        envase = unidades if fila["subcategoria"] == "Huevos" else f"{envase} ({unidades})"
    return f"{_num(x)} × {envase}"


def _gramos(g: float, agua: bool = False) -> str:
    """Cantidad comestible: en litros (g ≈ ml) si es agua."""
    if agua:
        return f"{_num(g / 1000, 2)} l" if g >= 1000 else f"{_num(g)} ml"
    return f"{_num(g / 1000, 2)} kg" if g >= 1000 else f"{_num(g)} g"


def _horario_hoy(tienda: pd.Series) -> dict:
    hoy = DIAS_SEMANA[datetime.now().weekday()]
    h = tienda.get(f"horario_{hoy}")
    texto = "no informado" if h is None or (isinstance(h, float) and np.isnan(h)) else (h or "cerrado")
    return {"dia": hoy.replace("miercoles", "miércoles").replace("sabado", "sábado"), "horario": texto}


def _sin_oferta(dieta: modelo.Dieta, sin_aptos: set[str]) -> list[Meta]:
    """Reglas que la sucursal no puede cumplir porque no vende nada que cuente (frutas frescas): faltan del todo.
    Las que no aplican por las restricciones de la persona (pescado para un vegetariano) no cuentan."""
    return [m for m in dieta.reglas_sin_oferta if m.clave not in sin_aptos]


def _puntaje(sol: modelo.Solucion, sin_aptos: list[set[str]]) -> float:
    """Déficit ponderado de lo que se le exige a la compra, sumado en el hogar (0 = cumple todo)."""
    total = 0.0
    for dieta, sa in zip(sol.dietas, sin_aptos):
        total += sum(m.peso * d for m, d in zip(dieta.metas, dieta.deficit) if m.tipo not in ("energia", "informativa"))
        total += sum(m.peso for m in _sin_oferta(dieta, sa))
    return float(total)


def _faltantes(sol: modelo.Solucion, sin_aptos: list[set[str]], nombres: list[str]) -> list[str]:
    salida = []
    for dieta, sa, nombre in zip(sol.dietas, sin_aptos, nombres):
        prefijo = f"{nombre}: " if len(nombres) > 1 else ""
        salida += [prefijo + m.nombre for m, d in zip(dieta.metas, dieta.deficit)
                   if m.tipo not in ("energia", "informativa") and d > 0.005]
        salida += [f"{prefijo}{m.nombre} (no lo vende)" for m in _sin_oferta(dieta, sa)]
    return salida


def _firma(o: pd.DataFrame) -> int:
    """Mismos productos con los mismos precios (al centavo) = misma firma: dan la misma canasta."""
    return hash((tuple(o.index), tuple(np.round(o["precio_compra"].to_numpy(), 2))))


def _evaluar(reqs: list[Requerimientos], d: oferta.Datos, tiendas: pd.DataFrame, aptos: list[np.ndarray],
             dias: int) -> dict:
    ofertas = {i: oferta.oferta_tienda(d, i, aptos) for i in tiendas.index}
    # Sucursales de una misma cadena con los mismos precios dan la misma canasta: se resuelve una vez.
    firmas, unicas = {}, {}
    for i, (o, _) in ofertas.items():
        unicas[i] = firmas.setdefault(_firma(o), i)
    a_resolver = sorted(set(unicas.values()))

    def resolver(i):
        o, por_persona = ofertas[i]
        return modelo.resolver(list(zip(reqs, por_persona)), o, dias)
    # HiGHS libera el GIL: las sucursales se resuelven en paralelo.
    with ThreadPoolExecutor(max_workers=min(4, len(a_resolver))) as ex:
        resueltas = dict(zip(a_resolver, ex.map(resolver, a_resolver)))
    return {i: resueltas[unicas[i]] for i in tiendas.index}


def _cobertura(dieta: modelo.Dieta, req: Requerimientos, sin_aptos: set[str]) -> tuple[list, list]:
    nutrientes, reglas = [], []
    por_clave = {m.clave: (m, v, dfc) for m, v, dfc in zip(dieta.metas, dieta.valores, dieta.deficit)}

    def periodo(fila: dict, m: Meta) -> dict:
        # Las reglas semanales se muestran por semana (pescado 2 veces, no 0,29 porciones por día).
        f = 7 if m.semanal else 1
        for k in ("valor", "minimo", "maximo"):
            if fila[k] is not None:
                fila[k] = round(fila[k] * f, 2)
        fila["unidad"] = f"{m.unidad} por {'semana' if m.semanal else 'día'}" if m.tipo == "regla" else m.unidad
        return fila

    for m in req.metas:
        if m.clave not in por_clave:
            no_aplica = m.clave in sin_aptos
            motivo = ("no aplica: ningún alimento apto cuenta para esta regla" if no_aplica
                      else "la sucursal no vende ningún alimento apto que cuente para esta regla")
            reglas.append(periodo({"clave": m.clave, "nombre": m.nombre, "unidad": m.unidad,
                                   "valor": None if no_aplica else 0.0, "minimo": _limpio(m.minimo),
                                   "maximo": _limpio(m.maximo), "estado": "no_aplica" if no_aplica else "falta",
                                   "nota": motivo, "fuente": m.fuente, "tipo": m.tipo,
                                   "porcentaje": None if no_aplica else 0.0}, m))
            continue
        m, v, dfc = por_clave[m.clave]
        if m.tipo == "informativa":
            estado = "informativa"
        elif dfc <= 0.005:
            estado = "cumple"
        elif m.minimo and v < m.minimo:
            estado = "falta"
        else:
            estado = "excede"
        referencia = m.minimo if m.minimo else m.maximo
        fila = {"clave": m.clave, "nombre": m.nombre, "unidad": m.unidad, "valor": round(float(v), 2),
                "minimo": _limpio(m.minimo), "maximo": _limpio(m.maximo), "estado": estado, "nota": m.nota,
                "fuente": m.fuente, "tipo": m.tipo,
                "porcentaje": round(float(v) / referencia * 100, 1) if referencia else None}
        (reglas if m.tipo == "regla" else nutrientes).append(periodo(fila, m))
    return nutrientes, reglas


def _grupos(o: pd.DataFrame, consumo: np.ndarray) -> list[dict]:
    kcal = o["energia_kcal"].to_numpy(float) / 100 * consumo
    tabla = pd.DataFrame({"grupo": o["grupo_alimentario"].to_numpy(), "g": consumo, "kcal": kcal})
    t = tabla.groupby("grupo").sum()
    t = t[t["g"] > 0]
    total = t["kcal"].sum() or 1.0
    return [{"grupo": g, "gramos_dia": round(float(r.g)), "kcal_dia": round(float(r.kcal)),
             "pct_kcal": round(float(r.kcal) / total * 100, 1)}
            for g, r in t.sort_values("kcal", ascending=False, kind="stable").iterrows()]


def _caminata(t: pd.Series) -> dict:
    """Minutos y metros caminando hasta la sucursal (solo si se buscó por tiempo)."""
    if "minutos" not in t.index:
        return {"minutos": None, "metros": None, "fuente_tiempo": None}
    return {"minutos": _limpio(t["minutos"]), "metros": _limpio(t["metros"]), "fuente_tiempo": t["fuente_tiempo"]}


def _renglon(sol: modelo.Solucion, j: int, dias: int) -> dict:
    """Un renglón del ticket: el producto j de la oferta, con lo que se compra y lo que come cada persona."""
    fila = sol.oferta.iloc[j]
    consumo = float(sol.consumo[j])
    x = float(sol.compra[j])
    comestible_comprado = x * fila["gramos_comestibles_compra"]
    sobra = comestible_comprado - consumo * dias
    promo = fila["precio_promocion"]
    agua = fila["alimento_id"] in cfg.ALIMENTOS_AGUA
    return {
        "id_producto": sol.oferta.index[j], "nombre": fila["nombre"], "marca": _limpio(fila["marca"]),
        "subcategoria": fila["subcategoria"], "grupo": fila["grupo_alimentario"],
        "cantidad": _cantidad(fila, x), "unidades_compra": x, "granel": bool(fila["granel"]),
        "precio_unitario": round(float(fila["precio"]), 2),
        "precio_unidad_texto": (f"${_num(fila['precio'], 2)} /kg" if fila["granel"]
                                else f"${_num(fila['precio'], 2)} c/u"),
        "subtotal": round(x * float(fila["precio_compra"]), 2),
        "promocion": _limpio(round(float(promo), 2)) if pd.notna(promo) else None,
        "gramos_dia": round(consumo, 1),
        "consumo_dia_texto": _gramos(consumo, agua), "agua": agua,
        "por_persona": [round(float(dt.consumo[j]), 1) for dt in sol.dietas],
        "sobrante_texto": _gramos(sobra, agua) if sobra > max(20.0, 0.05 * comestible_comprado) else "",
        "fuente_nutrientes": fila["fuente_nutrientes"],
    }


def _ordenar(items: list[dict]) -> list[dict]:
    """Orden del ticket: por grupo de la canasta, subcategoría y nombre."""
    orden = {g: i for i, g in enumerate(cfg.GRUPOS_CANASTA)}
    return sorted(items, key=lambda it: (orden.get(it["grupo"], 99), it["subcategoria"], it["nombre"]))


def _datos_tienda(tienda: pd.Series) -> dict:
    """La sucursal como la muestra el ticket (con los minutos caminando desde el lugar, si se buscó por tiempo)."""
    return {"id": tienda.name, "bandera": tienda["bandera"], "comercio": tienda["comercio"],
            "cuit": _limpio(tienda["cuit"]), "sucursal": tienda["sucursal_nombre"],
            "direccion": tienda["direccion"], "localidad": _limpio(tienda["localidad"]),
            "barrio": _limpio(tienda["barrio"]), "provincia": _limpio(tienda["provincia"]),
            "lat": _limpio(tienda["lat"]), "lon": _limpio(tienda["lon"]),
            "distancia_km": round(float(tienda["distancia_km"]), 2), **_caminata(tienda),
            "hoy": _horario_hoy(tienda), "tipo": tienda["tipo_sucursal"]}


def _ticket(sol: modelo.Solucion, tienda: pd.Series, dias: int, fecha: str) -> dict:
    o = sol.oferta
    consumo = sol.consumo
    items = _ordenar([_renglon(sol, j, dias) for j in np.flatnonzero(sol.compra > 0)])
    total = round(sum(it["subtotal"] for it in items), 2)
    energia = float(np.dot(o["energia_kcal"].to_numpy(float) / 100, consumo))
    return {
        "tienda": _datos_tienda(tienda),
        "fecha_precios": fecha, "dias": dias, "items": items, "total": total,
        "costo_diario": round(total / dias, 2),
        "costo_1000_kcal": round(total / dias / energia * 1000, 2) if energia else None,
        "promociones_disponibles": sum(1 for it in items if it["promocion"]),
    }


def metas_cubiertas(persona: dict) -> tuple[int, int]:
    """(cumple, total) de las metas que se le exigen a la compra: sin las informativas ni las que no aplican por las
    restricciones. Es la misma cuenta que muestra la página (metasCubiertas en web/app.js)."""
    exigidas = [c for c in persona["cobertura"] + persona["reglas"] if c["estado"] not in ("informativa", "no_aplica")]
    return sum(c["estado"] == "cumple" for c in exigidas), len(exigidas)


def resumen_metas(r: dict) -> dict:
    """Cuántas metas logra la compra elegida, cuáles faltan (con cuánto cubre cada una) y si ninguna de las sucursales
    evaluadas las logra todas. Con todas cumplidas, faltan queda vacío."""
    cuentas = [metas_cubiertas(p) for p in r["personas"]]
    varias = len(r["personas"]) > 1
    faltan = []
    for p in r["personas"]:
        for c in p["cobertura"] + p["reglas"]:
            if c["estado"] not in ("falta", "excede"):
                continue
            # Lo que se pasa se mide contra el máximo; lo que falta, contra el mínimo.
            pct = (c["valor"] / c["maximo"] * 100 if c["estado"] == "excede" and c["maximo"] else c["porcentaje"]) or 0.0
            faltan.append({"persona": p["datos"]["nombre"] if varias else "", "clave": c["clave"],
                           "nombre": c["nombre"].split(":")[0], "estado": c["estado"], "porcentaje": round(pct, 1),
                           "no_lo_vende": c["valor"] == 0 and "no vende" in c["nota"]})
    validas = [s for s in r.get("sucursales", []) if s["costo"] is not None]
    return {"cumple": sum(c for c, _ in cuentas), "total": sum(t for _, t in cuentas), "faltan": faltan,
            "sucursales": len(validas), "ninguna_las_logra": bool(validas) and all(s["faltantes"] for s in validas)}


def _datos_persona(p: Persona, nombre: str) -> dict:
    return {"nombre": nombre, "sexo": p.sexo, "edad": p.edad, "peso_kg": p.peso_kg, "altura_cm": p.altura_cm,
            "actividad": cfg.ACTIVIDAD[p.actividad]["nombre"], "objetivo": cfg.OBJETIVO[p.objetivo]["nombre"],
            "etapa": p.etapa, "trimestre": p.trimestre, "restricciones": [cfg.RESTRICCIONES[r] for r in p.restricciones]}


def _nombres(personas: list[Persona]) -> list[str]:
    return [p.nombre or f"Persona {i + 1}" for i, p in enumerate(personas)]


def _aptos_hogar(d: oferta.Datos, personas: list[Persona], reqs: list[Requerimientos], listos: bool,
                 agua: str) -> tuple[pd.Series | None, list[np.ndarray], list[list[dict]], list[set[str]]]:
    """Qué puede comer cada persona: (base, aptos, efecto de cada restricción, reglas que no aplican)."""
    a_cocinar = d.productos["alimento_id"].isin(cfg.ALIMENTOS_A_COCINAR).to_numpy()
    compra_agua = cfg.AGUA_MODOS[agua]["compra"]
    base_aptos = None if compra_agua else ~oferta.es_agua(d.productos)        # el agua de la canilla no se compra
    aptos, efectos, sin_aptos = [], [], []
    for p, req in zip(personas, reqs):
        apto, efecto = oferta.aptos(d.productos, p.restricciones, base_aptos)
        apto = apto.to_numpy()
        if listos:
            efecto.append({"clave": "listos", "nombre": cfg.LISTOS_NOMBRE, "excluye": int((apto & a_cocinar).sum())})
            apto = apto & ~a_cocinar
        aptos.append(apto)
        efectos.append(efecto)
        # Reglas que ningún producto apto (en todo el país) puede cumplir: no aplican por las restricciones.
        sin_aptos.append({m.clave for m in req.metas if m.tipo == "regla" and m.minimo is not None
                          and not modelo.coeficientes(d.productos[apto], m).any()})
    return base_aptos, aptos, efectos, sin_aptos


def armar(personas: list[Persona], lat: float, lon: float, dias: int = cfg.DIAS_PREDETERMINADO,
          listos: bool = False, tiempos: dict[str, dict] | None = None, caminata_minutos: float | None = None,
          aviso_tiempos: str | None = None, agua: str = cfg.AGUA_MODO_PREDETERMINADO) -> dict:
    """Con tiempos (id_tienda -> {minutos, metros, fuente}, de canasta/rutas.py) y caminata_minutos, solo se evalúan
    las sucursales a las que se llega caminando dentro de ese límite; sin ellos, las más cercanas en línea recta.
    agua: cómo toma agua el hogar (config.AGUA_MODOS); el agua envasada solo se ofrece si se compra."""
    inicio = time.time()
    if isinstance(personas, Persona):
        personas = [personas]
    if not 1 <= len(personas) <= cfg.PERSONAS_MAXIMAS:
        raise ValueError(f"El hogar tiene que tener entre 1 y {cfg.PERSONAS_MAXIMAS} personas.")
    if dias not in cfg.DIAS_PERIODO:
        raise ValueError(f"El período tiene que ser de {', '.join(map(str, cfg.DIAS_PERIODO))} días.")
    if agua not in cfg.AGUA_MODOS:
        raise ValueError(f"El agua tiene que ser {', '.join(cfg.AGUA_MODOS)}.")
    nombres = _nombres(personas)
    reqs = [calcular(p, agua) for p in personas]
    d = oferta.cargar()
    compra_agua = cfg.AGUA_MODOS[agua]["compra"]
    base_aptos, aptos, efectos, sin_aptos = _aptos_hogar(d, personas, reqs, listos, agua)
    base = {
        "personas": [{"datos": _datos_persona(p, nombre),
                      "requerimientos": {"energia_kcal": r.energia_kcal, "proteina_g_kg": r.proteina_g_kg,
                                         "peso_referencia_kg": round(r.peso_referencia_kg, 1), "pasos": r.pasos,
                                         "avisos": r.avisos},
                      "restricciones": {"criterios": oferta.criterios(p.restricciones), "efecto": ef,
                                        "productos_aptos": int(ap.sum())}}
                     for p, nombre, r, ef, ap in zip(personas, nombres, reqs, efectos, aptos)],
        "hogar": {"personas": len(personas), "energia_kcal": float(sum(r.energia_kcal for r in reqs))},
        "opciones": {"listos": listos, "listos_criterio": cfg.LISTOS_CRITERIO if listos else None, "agua": agua,
                     "agua_nombre": cfg.AGUA_MODOS[agua]["nombre"]},
        "catalogo": {"productos_total": d.total_productos,
                     "productos_canasta": len(d.productos) if compra_agua else int(base_aptos.sum()),
                     "excluidos_siempre": EXCLUIDOS_SIEMPRE},
        "ubicacion": {"lat": lat, "lon": lon},
        "dias": dias, "periodo": cfg.DIAS_PERIODO[dias], "fecha_precios": d.fecha,
    }
    por_tiempo = tiempos is not None
    if por_tiempo:
        limite = cfg.CAMINATA_MINUTOS if caminata_minutos is None else caminata_minutos
        base["caminata"] = {"minutos": limite, "aviso": aviso_tiempos,
                            "fuente": "estimado" if any(v.get("fuente") == "estimado" for v in tiempos.values())
                            else "ruta"}
        tiendas = oferta.sucursales_por_tiempo(d, lat, lon, tiempos, limite)
    else:
        tiendas = oferta.sucursales_cercanas(d, lat, lon)
    if tiendas.empty:
        base["error"] = (f"No hay supermercados con precios en SEPA a menos de {_num(limite)} minutos caminando."
                         if por_tiempo else
                         f"No hay supermercados con precios en SEPA a menos de {_num(cfg.RADIO_MAXIMO_KM)} km.")
        base["sin_sucursales"] = True
        return base
    soluciones = _evaluar(reqs, d, tiendas, aptos, dias)
    comparacion = []
    for i, t in tiendas.iterrows():
        s = soluciones[i]
        ok = s.estado != "sin_solucion"
        comparacion.append({"id": i, "bandera": t["bandera"], "sucursal": t["sucursal_nombre"],
                            "direccion": t["direccion"], "localidad": _limpio(t["localidad"]),
                            "distancia_km": round(float(t["distancia_km"]), 2), **_caminata(t),
                            "lat": _limpio(t["lat"]), "lon": _limpio(t["lon"]), "estado": s.estado,
                            "costo": round(s.costo, 2) if ok else None,
                            "puntaje": round(_puntaje(s, sin_aptos), 3) if ok else None,
                            "faltantes": _faltantes(s, sin_aptos, nombres) if ok else [],
                            "mensaje": "" if ok else s.mensaje, "productos_considerados": len(s.oferta),
                            "segundos": round(s.segundos, 2)})
    validas = [c for c in comparacion if c["costo"] is not None]
    if not validas:
        base["sucursales"] = comparacion
        base["error"] = "Ninguna sucursal cercana tiene alimentos aptos suficientes para armar la canasta."
        return base
    elegida = min(validas, key=lambda c: (round(c["puntaje"], 2), c["costo"]))
    elegida["elegida"] = True
    sol = soluciones[elegida["id"]]
    for persona, dieta, req, sa in zip(base["personas"], sol.dietas, reqs, sin_aptos):
        persona["cobertura"], persona["reglas"] = _cobertura(dieta, req, sa)
        persona["grupos"] = _grupos(sol.oferta, dieta.consumo)
    metas_modelo = sum(len(dt.metas) for dt in sol.dietas)
    n_vars = len(sol.oferta) * (1 + len(personas)) + metas_modelo
    base.update({
        "sucursales": comparacion,
        "ticket": _ticket(sol, tiendas.loc[elegida["id"]], dias, d.fecha),
        "modelo": {"estado": sol.estado, "productos_considerados": len(sol.oferta), "variables": n_vars,
                   "metas": metas_modelo, "segundos_sucursal": round(sol.segundos, 2),
                   "segundos_total": round(time.time() - inicio, 2), "gap": cfg.GAP_RELATIVO},
    })
    return base


# ------------------------------------------------------------
# Compra en dos supermercados
# ------------------------------------------------------------

def _union(oa: tuple[pd.DataFrame, list[np.ndarray]], ob: tuple[pd.DataFrame, list[np.ndarray]], id_a: str,
           id_b: str) -> tuple[pd.DataFrame, list[np.ndarray]]:
    """Las ofertas de A y de B en una sola, con la columna id_tienda: el mismo producto en las dos sucursales son dos
    filas distintas, cada una con su precio. Una fila de B con el mismo producto que A vende al mismo precio o más
    barato se saca: nunca puede ser mejor (mismos nutrientes y gramos), y con ella el modelo tendría dos filas
    idénticas por cada producto que las dos venden igual (dos sucursales de una cadena), que lo hacen lento y dejan
    partir la compra por nada. El óptimo no cambia."""
    o_a, aptos_a = oa
    o_b, aptos_b = ob
    precio_a = dict(zip(o_a.index, o_a["precio_compra"].to_numpy(float)))
    queda = np.array([p not in precio_a or c < precio_a[p]
                      for p, c in zip(o_b.index, o_b["precio_compra"].to_numpy(float))], dtype=bool)
    o = pd.concat([o_a.assign(id_tienda=id_a), o_b[queda].assign(id_tienda=id_b)])
    return o, [np.concatenate([a, b[queda]]) for a, b in zip(aptos_a, aptos_b)]


def _par(reqs: list[Requerimientos], oa: tuple[pd.DataFrame, list[np.ndarray]],
         ob: tuple[pd.DataFrame, list[np.ndarray]], id_a: str, id_b: str, dias: int) -> modelo.Solucion:
    """La compra más barata que mejor cubre las metas comprando en A y en B (el modelo de siempre sobre la unión)."""
    o, por_persona = _union(oa, ob, id_a, id_b)
    return modelo.resolver(list(zip(reqs, por_persona)), o, dias)


def _compra_en(sol: modelo.Solucion, id_tienda: str) -> bool:
    return sol.estado != "sin_solucion" and bool(((sol.compra > 0)
                                                  & (sol.oferta["id_tienda"].to_numpy() == id_tienda)).any())


def ahorro_minimo(costo_a: float) -> float:
    """Lo mínimo que tiene que ahorrar la compra en dos sucursales (con las mismas metas) para proponerla."""
    return round(max(costo_a * cfg.DOS_SUPER_AHORRO_MINIMO_PCT / 100, cfg.DOS_SUPER_AHORRO_MINIMO_PESOS), 2)


def _decidir(costo_a: float, puntaje_a: float, vecinas: list[dict]) -> tuple[str, str | None, dict | None]:
    """(estado, motivo, mejor par) a partir de A sola y de cada par (A, B): {costo, puntaje, compra_en_b}. El mejor
    par es el de menor déficit (redondeado al 1 %, como al elegir la sucursal) y, a igual déficit, el más barato,
    entre los que compran algo en B (si no, es A sola). Conviene si cubre mejor las metas (aunque cueste más) o, si las
    cubre igual, si ahorra al menos ahorro_minimo."""
    if not vecinas:
        return "sin_vecinas", None, None
    con_b = [v for v in vecinas if v["compra_en_b"]]
    if not con_b:
        return "no_conviene", None, None
    mejor = min(con_b, key=lambda v: (round(v["puntaje"], 2), v["costo"]))
    p_a, p_b = round(puntaje_a, 2), round(mejor["puntaje"], 2)
    if p_b < p_a:
        return "conviene", "metas", mejor
    if p_b == p_a and round(costo_a - mejor["costo"], 2) >= ahorro_minimo(costo_a):
        return "conviene", "ahorro", mejor
    return "no_conviene", None, mejor


def _minutos_casa(t: pd.Series) -> tuple[float, str]:
    """Minutos caminando del lugar a la sucursal: los del resultado (ruta o estimado) o, si no se buscó por tiempo,
    estimados con la distancia en línea recta."""
    if "minutos" in t.index and pd.notna(t["minutos"]):
        return round(float(t["minutos"]), 1), t["fuente_tiempo"]
    return round(float(oferta.minutos_estimados(float(t["distancia_km"]))), 1), "estimado"


def _circuito(ta: pd.Series, tb: pd.Series) -> dict:
    """Minutos del circuito lugar → A → B → lugar contra la ida y vuelta lugar → A → lugar, con los tramos redondeados
    a 0,1 min. El tramo A → B siempre es estimado (no se pide la ruta acá), así que los minutos de más también."""
    casa_a, fuente_a = _minutos_casa(ta)
    casa_b, fuente_b = _minutos_casa(tb)
    a_b = round(float(tb["minutos_desde_a"]), 1)
    circuito = round(casa_a + a_b + casa_b, 1)
    solo_a = round(2 * casa_a, 1)
    return {"solo_a": solo_a, "circuito": circuito, "extra": round(max(0.0, circuito - solo_a), 1),
            "fuente": "estimado",
            "tramos": [{"desde": "lugar", "hasta": "a", "minutos": casa_a, "fuente": fuente_a},
                       {"desde": "a", "hasta": "b", "minutos": a_b, "fuente": "estimado",
                        "metros_linea_recta": round(float(tb["km_desde_a"]) * 1000)},
                       {"desde": "b", "hasta": "lugar", "minutos": casa_b, "fuente": fuente_b}]}


def _ticket_dividido(sol: modelo.Solucion, tiendas: list[pd.Series], dias: int, fecha: str) -> dict:
    """El ticket de la compra combinada, un bloque por sucursal (A primero) con su subtotal; cada renglón dice de qué
    sucursal es (id_tienda)."""
    de_tienda = sol.oferta["id_tienda"].to_numpy()
    bloques = []
    for t in tiendas:
        filas = np.flatnonzero((sol.compra > 0) & (de_tienda == t.name))
        items = _ordenar([{**_renglon(sol, j, dias), "id_tienda": t.name} for j in filas])
        bloques.append({"tienda": _datos_tienda(t), "items": items,
                        "subtotal": round(sum(it["subtotal"] for it in items), 2)})
    total = round(sum(b["subtotal"] for b in bloques), 2)
    return {"fecha_precios": fecha, "dias": dias, "sucursales": bloques, "total": total,
            "costo_diario": round(total / dias, 2)}


def _metas(r: dict) -> dict:
    m = resumen_metas(r)
    return {"cumple": m["cumple"], "total": m["total"], "faltan": m["faltan"]}


def _lista(xs: list[str], n: int = 4) -> str:
    """Los nombres separados por punto y coma (los de las subcategorías ya llevan comas): a lo sumo n, y cuántos más."""
    return "; ".join(xs[:n]) + (f" (y {len(xs) - n} más)" if len(xs) > n else "")


def _mensaje(estado: str, motivo: str | None, nombre_a: str, nombre_b: str, productos_b: list[str], ahorro: float,
             pct: float, minimo: float, extra: float, antes: dict, despues: dict) -> str:
    lista = _lista([p.lower() for p in productos_b])
    caminando = (f"caminando unos {_num(extra, 1)} min más (estimado)" if extra >= 1
                 else "casi sin caminar de más (estimado)")
    if motivo == "metas":
        logro = (f"llegás a {despues['cumple']} de {despues['total']} metas (con {nombre_a} sola, {antes['cumple']})"
                 if despues["cumple"] > antes["cumple"]
                 else f"cubrís mejor las que faltan ({despues['cumple']} de {despues['total']} metas, como antes)")
        plata = (f"ahorrás ${_num(ahorro)}" if ahorro > 0 else f"cuesta ${_num(-ahorro)} más" if ahorro < 0
                 else "cuesta lo mismo")
        return (f"Con un segundo súper {logro}: en {nombre_b} conviene comprar {lista}. "
                f"{plata[0].upper() + plata[1:]}, {caminando}.")
    if motivo == "ahorro":
        return f"Comprando en {nombre_b} {lista} ahorrás ${_num(ahorro)} ({_num(pct, 1)} %), {caminando}."
    if ahorro > 0:
        return (f"No conviene dividir la compra: comprando en {nombre_b} {lista} ahorrarías solo ${_num(ahorro)} "
                f"({_num(pct, 1)} %), menos del mínimo de ${_num(minimo)}.")
    return f"No conviene dividir la compra: sumando {nombre_b} no sale más barato ni cubre mejor las metas."


def dos_super(personas: list[Persona], r: dict, tiempos: dict[str, dict] | None = None) -> dict:
    """¿Conviene comprar en dos supermercados? Se calcula a pedido, después del resultado normal r de armar() (no lo
    cambia): parte de la sucursal elegida A y prueba sumarle una vecina B. personas: las mismas que se pasaron a
    armar(); tiempos: los mismos (id_tienda -> {minutos, metros, fuente}) si se buscó por tiempo caminando. El lugar,
    los días, "listos" y el agua salen de r.

    Modelo: el de canasta/modelo.py con binarias de visita, sobre la unión de las ofertas de A y de sus vecinas V (cada
    fila es un producto p en una sucursal s(p): el mismo producto en dos sucursales son dos filas):
      y_s   visito la sucursal s (binaria), con y_A = 1 y  sum_s y_s <= DOS_SUPER_MAXIMO (2)
      Etapa 1 (MILP): minimizar sum peso_k * d_ik con las restricciones de siempre y  c_ip <= tope_ip * y_s(p)
              (tope_ip: el de variedad de la subcategoría de p para la persona i; no se come de donde no se compra)
      Etapa 2 (MILP): minimizar sum precio_p * x_p con cada d_ik <= d*_ik + holgura, las de siempre y
              x_p <= x_max_p * y_s(p)  (no se compra en una sucursal que no se visita)
    Como y_A = 1 y se visitan a lo sumo dos, las soluciones son "A sola" o "A y una B_j": fijadas las y, cada par
    (A, B_j) es el modelo de siempre (modelo.resolver) sobre la unión de las dos ofertas, sin binarias. El óptimo con
    binarias es el mejor par en el mismo orden lexicográfico (menor déficit ponderado, redondeado al 1 %, y después
    menor costo), y cada par contiene a "A sola" (y_B = 0), que ya está resuelta en r. Por eso se resuelve enumerando
    los pares (a lo sumo DOS_SUPER_VECINAS): da lo mismo, cada par es un modelo que ya se sabe resolver (también con
    HiGHS en WebAssembly) y el motor de la página no necesita otra formulación. El MILP con binarias, probado, no fue
    más rápido y dio compras más caras: la etapa 2 se resuelve sobre las subcategorías que usa su relajación, y con
    las y fraccionarias esa relajación elige peor. Medido con el oficinista en el Microcentro (A y 4 vecinas): A sola
    0,9 s; un par, 1 a 3,5 s en serie; los 4 pares, 4 a 10 s en paralelo; el MILP con las 5 binarias, 4,6 a 5 s y
    $495 más caro que el mejor par. En la unión se sacan las filas de B que A vende igual o más barato (_union): no
    cambian el óptimo y, entre dos sucursales de una cadena, lo hacían 5 veces más lento.

    Cada par se resuelve con el mismo GAP_RELATIVO (1 %) que una sucursal sola, así que un par puede salir hasta ~1 %
    más caro que A sola aunque la contenga (pasa en el centro de Córdoba) o ~1 % más barato por ruido del solver: por
    eso el ahorro mínimo en porcentaje (DOS_SUPER_AHORRO_MINIMO_PCT, 3 %) es bastante mayor que el gap.

    Decisión (lexicográfica, como siempre: nunca se cambia nutrición por plata), ver _decidir: "conviene" si cubre
    mejor las metas (motivo "metas", aunque cueste más) o si las cubre igual y ahorra al menos ahorro_minimo (motivo
    "ahorro"); si no, "no_conviene" (con lo que se ahorraría); "sin_vecinas" si no hay vecinas con otros precios. No
    se le pone precio al minuto: se informan los minutos de más del circuito lugar → A → B → lugar (el tramo A → B,
    estimado) y la persona decide."""
    inicio = time.time()
    if isinstance(personas, Persona):
        personas = [personas]
    if "ticket" not in r:
        raise ValueError("Primero hay que armar la canasta: el resultado no tiene una compra.")
    if cfg.DOS_SUPER_MAXIMO != 2:
        raise ValueError("La compra en varias sucursales se resuelve por pares: DOS_SUPER_MAXIMO tiene que ser 2.")
    por_tiempo = r.get("caminata") is not None
    if por_tiempo and tiempos is None:
        raise ValueError("El resultado se armó por tiempo caminando: hacen falta los mismos tiempos.")
    lat, lon = r["ubicacion"]["lat"], r["ubicacion"]["lon"]
    dias, listos, agua = r["dias"], r["opciones"]["listos"], r["opciones"]["agua"]
    nombres = _nombres(personas)
    reqs = [calcular(p, agua) for p in personas]
    d = oferta.cargar()
    _, aptos, _, sin_aptos = _aptos_hogar(d, personas, reqs, listos, agua)

    # Sucursales que pueden ser B: las alcanzables dentro del límite (por tiempo) o las evaluadas.
    elegida = next(s for s in r["sucursales"] if s.get("elegida"))
    id_a = elegida["id"]
    if por_tiempo:
        t = oferta.sucursales_por_tiempo(d, lat, lon, tiempos, r["caminata"]["minutos"], n=len(tiempos))
    else:
        t = oferta.sucursales_por_id(d, lat, lon, [s["id"] for s in r["sucursales"]])
    ta = t.loc[id_a]
    cercanas = oferta.vecinas_de(t, id_a, cfg.DOS_SUPER_MINUTOS_ENTRE)
    # Las que venden lo mismo al mismo precio que A (o que otra más cercana) no suman nada.
    ofertas = {id_a: oferta.oferta_tienda(d, id_a, aptos)}
    vistas, distintas = {_firma(ofertas[id_a][0])}, []
    for i in cercanas.index:
        ofertas[i] = oferta.oferta_tienda(d, i, aptos)
        firma = _firma(ofertas[i][0])
        if firma not in vistas:
            vistas.add(firma)
            distintas.append(i)
    vecinas = oferta.elegir_vecinas(cercanas.loc[distintas], ta["bandera"], cfg.DOS_SUPER_VECINAS)

    # HiGHS libera el GIL: los pares se resuelven en paralelo.
    soluciones = {}
    if not vecinas.empty:
        with ThreadPoolExecutor(max_workers=min(4, len(vecinas))) as ex:
            pares = ex.map(lambda i: _par(reqs, ofertas[id_a], ofertas[i], id_a, i, dias), vecinas.index)
            soluciones = dict(zip(vecinas.index, pares))
    probadas = []
    for i, tb in vecinas.iterrows():
        s = soluciones[i]
        ok = s.estado != "sin_solucion"
        probadas.append({"id": i, "bandera": tb["bandera"], "sucursal": tb["sucursal_nombre"],
                         "direccion": tb["direccion"], "lat": _limpio(tb["lat"]), "lon": _limpio(tb["lon"]),
                         "minutos_desde_a": round(float(tb["minutos_desde_a"]), 1), "estado": s.estado,
                         "costo": round(s.costo, 2) if ok else None,
                         "puntaje": round(_puntaje(s, sin_aptos), 3) if ok else None,
                         "compra_en_b": _compra_en(s, i), "segundos": round(s.segundos, 2)})

    costo_a, puntaje_a = elegida["costo"], elegida["puntaje"]
    estado, motivo, mejor = _decidir(costo_a, puntaje_a, probadas)
    nombre_a = f"{ta['bandera']} {ta['sucursal_nombre']}"
    salida = {"estado": estado, "motivo": motivo, "mensaje": "", "maximo_sucursales": cfg.DOS_SUPER_MAXIMO,
              "minutos_entre_max": cfg.DOS_SUPER_MINUTOS_ENTRE, "a": _datos_tienda(ta), "b": None,
              "costo_a": costo_a, "costo_combinado": None, "ahorro": None, "ahorro_pct": None,
              "ahorro_minimo": ahorro_minimo(costo_a), "puntaje_a": puntaje_a, "puntaje_combinado": None,
              "metas_antes": _metas(r), "metas_despues": None, "minutos": None, "ticket": None, "productos_b": [],
              "personas": None, "vecinas": probadas}
    if mejor is None:
        if estado == "sin_vecinas":
            donde = "dentro de tu límite de caminata" if por_tiempo else "entre las evaluadas"
            salida["mensaje"] = (f"No hay otro supermercado con otros precios a menos de "
                                 f"{cfg.DOS_SUPER_MINUTOS_ENTRE} min caminando de {nombre_a} ({donde}): la compra "
                                 f"queda en uno solo.")
        else:
            cuantas = "la vecina probada" if len(probadas) == 1 else f"las {len(probadas)} vecinas probadas"
            salida["mensaje"] = (f"No conviene dividir la compra: con {cuantas}, lo mejor sigue siendo comprar todo "
                                 f"en {nombre_a}.")
        salida["segundos"] = round(time.time() - inicio, 2)
        return salida

    sol, tb = soluciones[mejor["id"]], vecinas.loc[mejor["id"]]
    ahorro = round(costo_a - mejor["costo"], 2)
    pct = round(ahorro / costo_a * 100, 1)
    ticket = _ticket_dividido(sol, [ta, tb], dias, r["fecha_precios"])
    productos_b = list(dict.fromkeys(it["subcategoria"] for it in ticket["sucursales"][1]["items"]))
    personas_c = []
    for dieta, req, sa, nombre in zip(sol.dietas, reqs, sin_aptos, nombres):
        cobertura, reglas = _cobertura(dieta, req, sa)
        personas_c.append({"datos": {"nombre": nombre}, "cobertura": cobertura, "reglas": reglas,
                           "grupos": _grupos(sol.oferta, dieta.consumo)})
    metas_c = _metas({"personas": personas_c})
    minutos = _circuito(ta, tb)
    salida.update({"mensaje": _mensaje(estado, motivo, nombre_a, f"{tb['bandera']} {tb['sucursal_nombre']}",
                                       productos_b, ahorro, pct, salida["ahorro_minimo"], minutos["extra"],
                                       salida["metas_antes"], metas_c),
                   "b": {**_datos_tienda(tb), "minutos_desde_a": minutos["tramos"][1]["minutos"],
                         "km_desde_a": round(float(tb["km_desde_a"]), 2)},
                   "costo_combinado": mejor["costo"], "ahorro": ahorro, "ahorro_pct": pct,
                   "puntaje_combinado": mejor["puntaje"], "metas_despues": metas_c, "minutos": minutos,
                   "ticket": ticket, "productos_b": productos_b,
                   "personas": personas_c if motivo == "metas" else None,
                   "segundos": round(time.time() - inicio, 2)})
    return salida
