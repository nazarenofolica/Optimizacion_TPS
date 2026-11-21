"""
Canasta saludable: la compra más barata que cubre lo que necesita un hogar, en el supermercado de su zona, con los
precios del modelo estrella de SEPA 2.0 (../datos/sepa/).

    python -m canasta                       # exporta datos/sepa/canasta_local.html con la clave de rutas y la abre
                                            # servida en http://localhost (Ctrl+C para cerrar), con la API del
                                            # texto libre si hay GROQ_API_KEY (canasta/servidor.py)
    python -m canasta --llm-simulado        # lo mismo, con el texto libre simulado (solo para desarrollo)
    python -m canasta --exportar [RUTA]     # solo exporta (por defecto datos/sepa/canasta.html, sin clave)
    python -m canasta --perfil celiaca --direccion "Av Corrientes 1234" --provincia "Ciudad Autónoma de Buenos Aires"
    python -m canasta --perfil oficinista,trabajo_fisico,escolar --lat -32.95 --lon -60.64 --dias 14 --listos
    python -m canasta --perfil oficinista --lat -34.6037 --lon -58.3816 --caminata 15
    python -m canasta --perfil oficinista --lat -34.6037 --lon -58.3816 --caminata 15 --agua compra
    python -m canasta --perfil restricciones_extremas --lat -31.4167 --lon -64.1833 --caminata 15 --listos
    python -m canasta --perfil oficinista --lat -34.60386 --lon -58.38419 --caminata 15 --dos-super
    python -m canasta --perfil oficinista --lat -34.60386 --lon -58.38419 --sin-promos

Con --perfil, la canasta la arma en la consola el motor de Python (la referencia del que corre en la página). Con
--caminata, solo se evalúan las sucursales a las que se llega caminando en esos minutos (rutas de OpenRouteService:
ORS_API_KEY en base_sepa/.env). Con --dos-super, después del resultado se ve si conviene sumar un segundo
supermercado cerca de la elegida (resultado.dos_super). Las promociones que no piden banco ni tarjeta se aplican si
la base las trae (desde la etapa 5); --sin-promos las deja afuera.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

from sepa import config as cfg_sepa

from canasta import config as cfg

logger = logging.getLogger("canasta")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m canasta", description=__doc__.split("\n\n")[0])
    p.add_argument("--exportar", nargs="?", const="", metavar="RUTA",
                   help="Exportar la página a un solo HTML (por defecto datos/sepa/canasta.html) sin abrirlo.")
    p.add_argument("--con-clave", action="store_true",
                   help="Con --exportar: incrustar la clave de OpenRouteService (queda visible en la página).")
    p.add_argument("--puerto", type=int, default=8765, help="Puerto local para servir la página (por defecto 8765).")
    p.add_argument("--caminata", type=float, metavar="MINUTOS",
                   help="Con --perfil: solo las sucursales a las que se llega caminando en esos minutos.")
    p.add_argument("--perfil", help="Armar en la consola la canasta de uno o más perfiles de referencia/perfiles.csv, "
                                    "separados por comas (un hogar).")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--direccion", default="", help="Dirección a ubicar con Georef (en lugar de --lat/--lon).")
    p.add_argument("--provincia", default="")
    p.add_argument("--localidad", default="")
    p.add_argument("--dias", type=int, default=cfg.DIAS_PREDETERMINADO, choices=sorted(cfg.DIAS_PERIODO))
    p.add_argument("--listos", action="store_true", help="Solo alimentos listos para comer.")
    p.add_argument("--agua", choices=list(cfg.AGUA_MODOS), default=cfg.AGUA_MODO_PREDETERMINADO,
                   help="Cómo toma agua el hogar: " + "; ".join(f"{k}, {m['nombre'].lower()}"
                                                              for k, m in cfg.AGUA_MODOS.items())
                        + f" (por defecto, {cfg.AGUA_MODO_PREDETERMINADO}).")
    p.add_argument("--dos-super", action="store_true",
                   help="Con --perfil: después del resultado, ver si conviene sumar un segundo supermercado cerca de "
                        "la sucursal elegida.")
    p.add_argument("--sin-promos", action="store_true",
                   help="Con --perfil: no aplicar las promociones (por defecto se aplican las que no piden banco, "
                        "tarjeta ni el programa de la cadena, si la base las trae).")
    p.add_argument("--llm-simulado", action="store_true",
                   help="Solo para desarrollo: el servidor local responde \"Contalo con tus palabras\" con "
                        "interpretaciones de ejemplo (canasta/llm_simulado.py), sin llamar a Groq; la página lo avisa.")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def _num(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _imprimir_dos_super(ds: dict) -> None:
    num = _num
    print(f"\n{'=' * 64}\n¿Conviene comprar en dos supermercados? ({ds['estado'].replace('_', ' ')})\n{'-' * 64}")
    print(ds["mensaje"])
    if ds["vecinas"]:
        print(f"\nVecinas probadas (a menos de {ds['minutos_entre_max']} min caminando de "
              f"{ds['a']['bandera']} {ds['a']['sucursal']}, estimado):")
        for v in ds["vecinas"]:
            costo = f"${num(v['costo'])}" if v["costo"] is not None else v["estado"]
            marca = "→" if ds["b"] and v["id"] == ds["b"]["id"] else " "
            nada = "" if v["compra_en_b"] else "  (no compra nada ahí)"
            print(f" {marca} {v['bandera'] + ' ' + v['sucursal']:<40} ≈{num(v['minutos_desde_a'], 1):>4} min  "
                  f"A+B {costo}{nada}")
    if not ds["ticket"]:
        return
    m = ds["minutos"]
    tramos = " + ".join(f"{'≈' if t['fuente'] == 'estimado' else ''}{num(t['minutos'], 1)}" for t in m["tramos"])
    print(f"\nSolo A: ${num(ds['costo_a'])}  ·  A + B: ${num(ds['costo_combinado'])}  ·  "
          f"ahorro ${num(ds['ahorro'])} ({num(ds['ahorro_pct'], 1)} %; "
          f"mínimo para proponerlo ${num(ds['ahorro_minimo'])})")
    print(f"Caminata: lugar → A → B → lugar = {tramos} = ≈{num(m['circuito'], 1)} min, contra "
          f"{num(m['solo_a'], 1)} min de ida y vuelta a A: ≈{num(m['extra'], 1)} min más (estimado)")
    antes, despues = ds["metas_antes"], ds["metas_despues"]
    print(f"Metas: {antes['cumple']} de {antes['total']} con A sola → "
          f"{despues['cumple']} de {despues['total']} con A + B")
    if ds["estado"] != "conviene":
        return                                  # el ticket dividido, solo si se propone
    for bloque in ds["ticket"]["sucursales"]:
        t = bloque["tienda"]
        print(f"\n{t['bandera']} — {t['sucursal']} ({t['direccion']})")
        for it in bloque["items"]:
            print(f"{it['cantidad']:>16}  {it['nombre'][:34]:<34} ${num(it['subtotal'], 2):>11}")
            _imprimir_promo(it)
        print(f"{'subtotal':>52} ${num(bloque['subtotal'], 2):>11}")
    if ds["ticket"]["ahorro_promociones"]:
        print(f"{'ahorro por promociones':>52} -${num(ds['ticket']['ahorro_promociones'], 2):>10}")
    print(f"{'-' * 64}\n{'TOTAL':>52} ${num(ds['ticket']['total'], 2):>11}")


def _imprimir_promo(it: dict) -> None:
    """La promoción de un renglón del ticket: aplicada (con el descuento) o no aplicada (con el motivo)."""
    pr = it.get("promo")
    if pr and pr["aplicada"]:
        print(f"{'':>18}{pr['resumen']}: -${_num(it['descuento'], 2)} (lista ${_num(it['subtotal_lista'], 2)})")
    elif pr:
        print(f"{'':>18}Promo {pr['resumen']}, no aplicada ({pr['motivo']})")


def _imprimir(r: dict) -> None:
    def num(x, d=0):
        return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    for persona in r["personas"]:
        q = persona["requerimientos"]
        print(f"\n{persona['datos']['nombre']}: {num(q['energia_kcal'])} kcal/día, proteína "
              f"{num(q['proteina_g_kg'], 2)} g/kg")
        for paso in q["pasos"]:
            print(f"  · {paso['titulo']}: {paso['formula']} = {paso['resultado']}")
        for aviso in q["avisos"]:
            print(f"  ! {aviso}")
    if "error" in r:
        print(f"\n{r['error']}")
        return
    print("\nSucursales evaluadas:")
    caminata = r.get("caminata")
    if caminata and caminata.get("aviso"):
        print(f"  ! {caminata['aviso']}")
    for s in r["sucursales"]:
        costo = f"${num(s['costo'])}" if s["costo"] is not None else s["mensaje"]
        marca = "→" if s.get("elegida") else " "
        falta = f" (no cubre: {'; '.join(s['faltantes'])})" if s["faltantes"] else ""
        tiempo = ""
        if s.get("minutos") is not None:
            tiempo = f"{'≈' if s['fuente_tiempo'] == 'estimado' else ''}{num(s['minutos'])} min  "
        print(f" {marca} {s['bandera']:<28} {s['distancia_km']:>5.2f} km  {tiempo}{costo}{falta}")
    t = r["ticket"]
    print(f"\n{'=' * 64}\n{t['tienda']['bandera']} — {t['tienda']['sucursal']}\n{t['tienda']['direccion']}"
          f"\nPrecios del {t['fecha_precios']} · compra para {r['periodo']}\n{'-' * 64}")
    for it in t["items"]:
        print(f"{it['cantidad']:>16}  {it['nombre'][:34]:<34} ${num(it['subtotal'], 2):>11}")
        _imprimir_promo(it)
    if t["ahorro_promociones"]:
        print(f"{'-' * 64}\n{'subtotal a precio de lista':>52} ${num(t['total_lista'], 2):>11}")
        print(f"{'ahorro por promociones':>52} -${num(t['ahorro_promociones'], 2):>10}")
    print(f"{'-' * 64}\n{'TOTAL':>52} ${num(t['total'], 2):>11}\n{'por día':>52} ${num(t['costo_diario'], 2):>11}")
    print(f"\nAgua ({r['opciones']['agua_nombre'].lower()}):")
    for persona in r["personas"]:
        agua = next(c for c in persona["cobertura"] if c["clave"] == "agua")
        if agua["estado"] == "informativa":
            falta = max(0.0, agua["minimo"] - agua["valor"])
            texto = (f"tomá unos {num(falta / 1000, 1)} L de agua de la canilla por día: los alimentos aportan "
                     f"{num(agua['valor'] / 1000, 1)} L de {num(agua['minimo'] / 1000, 1)} L")
        else:
            texto = (f"{num(agua['valor'] / 1000, 2)} L por día de {num(agua['minimo'] / 1000, 1)} L "
                     f"({num(agua['porcentaje'], 0)} %, {agua['estado']})")
        print(f"  {persona['datos']['nombre']}: {texto}")
    from canasta.resultado import resumen_metas
    m = resumen_metas(r)
    print(f"\nMetas: {m['cumple']} de {m['total']} cubiertas.")
    if m["faltan"]:
        donde = (f"Ninguna de las {m['sucursales']} sucursales evaluadas logra las {m['total']}"
                 if m["sucursales"] > 1 else f"La única sucursal evaluada no logra las {m['total']}")
        print(f"  {donde}: es lo máximo que se puede cubrir con lo que venden.")
        for f in m["faltan"]:
            quien = f"{f['persona']}: " if f["persona"] else ""
            if f["estado"] == "excede":
                cuanto = f"se pasa: {num(f['porcentaje'])} % del máximo"
            elif f["no_lo_vende"]:
                cuanto = "0 %, no vende ninguno apto"
            else:
                cuanto = f"cubre el {num(min(f['porcentaje'], 99))} %"
            print(f"  falta  {quien}{f['nombre']} ({cuanto})")
    for persona in r["personas"]:
        pendientes = [c for c in persona["cobertura"] + persona["reglas"] if c["estado"] not in ("cumple", "no_aplica")]
        if pendientes:
            print(f"\nCobertura de {persona['datos']['nombre']}:")
            for c in pendientes:
                nota = f" ({c['nota']})" if c["nota"] else ""
                valor = num(c["valor"], 1) if isinstance(c["valor"], (int, float)) else c["valor"]
                print(f"  {c['estado']:<11} {c['nombre']}: {valor} {c['unidad']}{nota}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg_sepa.configurar_logging(args.verbose)
    if not args.perfil:
        from canasta import rutas
        if args.exportar is not None:
            from canasta import exportar
            exportar.exportar(Path(args.exportar) if args.exportar else exportar.RUTA_EXPORTACION,
                              clave_rutas=rutas.clave_ors() if args.con_clave else None)
            return 0
        if not rutas.clave_ors():
            logger.warning("Sin ORS_API_KEY (base_sepa/.env): la página va a estimar los tiempos caminando por distancia.")
        # Se exporta en un proceso aparte: los datos (~1 GB) se liberan al terminar y el servidor queda liviano
        # (dentro del mismo proceso, el asignador de Arrow no devuelve la memoria al sistema).
        ruta = cfg.DIR_SALIDA / "canasta_local.html"           # = exportar.RUTA_LOCAL, sin importar los datos
        hijo = subprocess.run([sys.executable, "-m", "canasta", "--exportar", str(ruta), "--con-clave"]
                              + (["--verbose"] if args.verbose else []))
        if hijo.returncode != 0:
            return hijo.returncode
        from canasta import servidor
        servidor.servir(ruta, args.puerto, llm_simulado=args.llm_simulado)
        return 0

    from canasta import resultado, rutas, ubicacion
    from canasta.requerimientos import perfiles, persona_desde
    por_id = {p["id"]: p for p in perfiles()}
    ids = [x.strip() for x in args.perfil.split(",") if x.strip()]
    desconocidos = [x for x in ids if x not in por_id]
    if desconocidos:
        print(f"Perfiles desconocidos: {', '.join(desconocidos)}. Opciones: {', '.join(por_id)}")
        return 2
    lat, lon = args.lat, args.lon
    if lat is None or lon is None:
        lugares = ubicacion.buscar(args.direccion, args.provincia, args.localidad)
        if not lugares:
            print("No se encontró la ubicación: pasá --lat y --lon o una --direccion con --provincia.")
            return 2
        lat, lon = lugares[0]["lat"], lugares[0]["lon"]
        print(f"Ubicación: {lugares[0]['nombre']} ({lugares[0]['precision']})")
    hogar = [persona_desde({**por_id[x], "nombre": por_id[x]["nombre"]}) for x in ids]
    print("Hogar: " + "; ".join(f"{por_id[x]['nombre']} ({por_id[x]['descripcion']})" for x in ids))
    extra, tiempos = {}, None
    if args.caminata:
        tiempos, aviso = rutas.tiempos_caminando(lat, lon, args.caminata)
        extra = {"tiempos": tiempos, "caminata_minutos": args.caminata, "aviso_tiempos": aviso}
    r = resultado.armar(hogar, lat, lon, args.dias, listos=args.listos, agua=args.agua,
                        promos=False if args.sin_promos else None, **extra)
    _imprimir(r)
    if args.dos_super and "ticket" in r:
        _imprimir_dos_super(resultado.dos_super(hogar, r, tiempos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
