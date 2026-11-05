"""
Arma la respuesta completa para un hogar (una o más personas) y un lugar: requerimientos de cada persona con su
cálculo, restricciones aplicadas, comparación de las sucursales cercanas, el ticket de la elegida y la cobertura de
cada nutriente y regla por persona.

La sucursal elegida es la que mejor cumple las metas de todos (menor déficit ponderado, redondeado al 1 %) y, entre
las que cumplen igual, la más barata. Es la referencia del motor de la página (canasta/web/motor.js), que hace lo
mismo en el navegador.
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
    if unidad == "g" and contenido >= 1000:
        envase = f"{_num(contenido / 1000, 3 if contenido % 1000 else 0)} kg"
    elif unidad == "ml" and contenido >= 1000:
        envase = f"{_num(contenido / 1000, 2 if contenido % 1000 else 0)} l"
    else:
        envase = f"{_num(contenido)} {unidad}".strip()
    if pd.notna(fila["unidades"]) and fila["unidades"] and fila["unidades"] > 1:
        unidades = f"{_num(fila['unidades'])} u."
        envase = unidades if fila["subcategoria"] == "Huevos" else f"{envase} ({unidades})"
    return f"{_num(x)} × {envase}"


def _gramos(g: float) -> str:
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


def _evaluar(reqs: list[Requerimientos], d: oferta.Datos, tiendas: pd.DataFrame, aptos: list[np.ndarray],
             dias: int) -> dict:
    ofertas = {i: oferta.oferta_tienda(d, i, aptos) for i in tiendas.index}
    # Sucursales de una misma cadena con los mismos precios dan la misma canasta: se resuelve una vez.
    firmas, unicas = {}, {}
    for i, (o, _) in ofertas.items():
        firma = hash((tuple(o.index), tuple(np.round(o["precio_compra"].to_numpy(), 2))))
        unicas[i] = firmas.setdefault(firma, i)
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


def _ticket(sol: modelo.Solucion, tienda: pd.Series, dias: int, fecha: str) -> dict:
    o = sol.oferta
    consumo = sol.consumo
    items = []
    for j in np.flatnonzero(sol.compra > 0):
        fila = o.iloc[j]
        x = float(sol.compra[j])
        comestible_comprado = x * fila["gramos_comestibles_compra"]
        sobra = comestible_comprado - float(consumo[j]) * dias
        promo = fila["precio_promocion"]
        items.append({
            "id_producto": o.index[j], "nombre": fila["nombre"], "marca": _limpio(fila["marca"]),
            "subcategoria": fila["subcategoria"], "grupo": fila["grupo_alimentario"],
            "cantidad": _cantidad(fila, x), "unidades_compra": x, "granel": bool(fila["granel"]),
            "precio_unitario": round(float(fila["precio"]), 2),
            "precio_unidad_texto": (f"${_num(fila['precio'], 2)} /kg" if fila["granel"]
                                    else f"${_num(fila['precio'], 2)} c/u"),
            "subtotal": round(x * float(fila["precio_compra"]), 2),
            "promocion": _limpio(round(float(promo), 2)) if pd.notna(promo) else None,
            "gramos_dia": round(float(consumo[j]), 1),
            "consumo_dia_texto": _gramos(float(consumo[j])),
            "por_persona": [round(float(dt.consumo[j]), 1) for dt in sol.dietas],
            "sobrante_texto": _gramos(sobra) if sobra > max(20.0, 0.05 * comestible_comprado) else "",
            "fuente_nutrientes": fila["fuente_nutrientes"],
        })
    orden = {g: i for i, g in enumerate(cfg.GRUPOS_CANASTA)}
    items.sort(key=lambda it: (orden.get(it["grupo"], 99), it["subcategoria"], it["nombre"]))
    total = round(sum(it["subtotal"] for it in items), 2)
    energia = float(np.dot(o["energia_kcal"].to_numpy(float) / 100, consumo))
    return {
        "tienda": {"id": tienda.name, "bandera": tienda["bandera"], "comercio": tienda["comercio"],
                   "cuit": _limpio(tienda["cuit"]), "sucursal": tienda["sucursal_nombre"],
                   "direccion": tienda["direccion"], "localidad": _limpio(tienda["localidad"]),
                   "barrio": _limpio(tienda["barrio"]), "provincia": _limpio(tienda["provincia"]),
                   "lat": _limpio(tienda["lat"]), "lon": _limpio(tienda["lon"]),
                   "distancia_km": round(float(tienda["distancia_km"]), 2), "hoy": _horario_hoy(tienda),
                   "tipo": tienda["tipo_sucursal"]},
        "fecha_precios": fecha, "dias": dias, "items": items, "total": total,
        "costo_diario": round(total / dias, 2),
        "costo_1000_kcal": round(total / dias / energia * 1000, 2) if energia else None,
        "promociones_disponibles": sum(1 for it in items if it["promocion"]),
    }


def _datos_persona(p: Persona, nombre: str) -> dict:
    return {"nombre": nombre, "sexo": p.sexo, "edad": p.edad, "peso_kg": p.peso_kg, "altura_cm": p.altura_cm,
            "actividad": cfg.ACTIVIDAD[p.actividad]["nombre"], "objetivo": cfg.OBJETIVO[p.objetivo]["nombre"],
            "etapa": p.etapa, "trimestre": p.trimestre, "restricciones": [cfg.RESTRICCIONES[r] for r in p.restricciones]}


def armar(personas: list[Persona], lat: float, lon: float, dias: int = cfg.DIAS_PREDETERMINADO,
          listos: bool = False) -> dict:
    inicio = time.time()
    if isinstance(personas, Persona):
        personas = [personas]
    if not 1 <= len(personas) <= cfg.PERSONAS_MAXIMAS:
        raise ValueError(f"El hogar tiene que tener entre 1 y {cfg.PERSONAS_MAXIMAS} personas.")
    if dias not in cfg.DIAS_PERIODO:
        raise ValueError(f"El período tiene que ser de {', '.join(map(str, cfg.DIAS_PERIODO))} días.")
    nombres = [p.nombre or f"Persona {i + 1}" for i, p in enumerate(personas)]
    reqs = [calcular(p) for p in personas]
    d = oferta.cargar()
    a_cocinar = d.productos["alimento_id"].isin(cfg.ALIMENTOS_A_COCINAR).to_numpy()
    aptos, efectos, sin_aptos = [], [], []
    for p, req in zip(personas, reqs):
        apto, efecto = oferta.aptos(d.productos, p.restricciones)
        apto = apto.to_numpy()
        if listos:
            efecto.append({"clave": "listos", "nombre": cfg.LISTOS_NOMBRE, "excluye": int((apto & a_cocinar).sum())})
            apto = apto & ~a_cocinar
        aptos.append(apto)
        efectos.append(efecto)
        # Reglas que ningún producto apto (en todo el país) puede cumplir: no aplican por las restricciones.
        sin_aptos.append({m.clave for m in req.metas if m.tipo == "regla" and m.minimo is not None
                          and not modelo.coeficientes(d.productos[apto], m).any()})
    base = {
        "personas": [{"datos": _datos_persona(p, nombre),
                      "requerimientos": {"energia_kcal": r.energia_kcal, "proteina_g_kg": r.proteina_g_kg,
                                         "peso_referencia_kg": round(r.peso_referencia_kg, 1), "pasos": r.pasos,
                                         "avisos": r.avisos},
                      "restricciones": {"criterios": oferta.criterios(p.restricciones), "efecto": ef,
                                        "productos_aptos": int(ap.sum())}}
                     for p, nombre, r, ef, ap in zip(personas, nombres, reqs, efectos, aptos)],
        "hogar": {"personas": len(personas), "energia_kcal": float(sum(r.energia_kcal for r in reqs))},
        "opciones": {"listos": listos, "listos_criterio": cfg.LISTOS_CRITERIO if listos else None},
        "catalogo": {"productos_total": d.total_productos, "productos_canasta": len(d.productos),
                     "excluidos_siempre": EXCLUIDOS_SIEMPRE},
        "ubicacion": {"lat": lat, "lon": lon},
        "dias": dias, "periodo": cfg.DIAS_PERIODO[dias], "fecha_precios": d.fecha,
    }
    tiendas = oferta.sucursales_cercanas(d, lat, lon)
    if tiendas.empty:
        base["error"] = f"No hay supermercados con precios en SEPA a menos de {_num(cfg.RADIO_MAXIMO_KM)} km."
        return base
    soluciones = _evaluar(reqs, d, tiendas, aptos, dias)
    comparacion = []
    for i, t in tiendas.iterrows():
        s = soluciones[i]
        ok = s.estado != "sin_solucion"
        comparacion.append({"id": i, "bandera": t["bandera"], "sucursal": t["sucursal_nombre"],
                            "direccion": t["direccion"], "localidad": _limpio(t["localidad"]),
                            "distancia_km": round(float(t["distancia_km"]), 2), "lat": _limpio(t["lat"]),
                            "lon": _limpio(t["lon"]), "estado": s.estado,
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
