"""
Canasta saludable: la compra más barata que cubre lo que necesita un hogar, en el supermercado de su zona, con los
precios del modelo estrella de SEPA 2.0 (salida/).

    python -m canasta                       # exporta salida/canasta.html (funciona sin servidor) y lo abre
    python -m canasta --exportar [RUTA]     # solo exporta
    python -m canasta --perfil celiaca --direccion "Av Corrientes 1234" --provincia "Ciudad Autónoma de Buenos Aires"
    python -m canasta --perfil oficinista,trabajo_fisico,escolar --lat -32.95 --lon -60.64 --dias 14 --listos

Con --perfil, la canasta la arma en la consola el motor de Python (la referencia del que corre en la página).
"""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
from pathlib import Path

from sepa import config as cfg_sepa

from canasta import config as cfg

logger = logging.getLogger("canasta")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m canasta", description=__doc__.split("\n\n")[0])
    p.add_argument("--exportar", nargs="?", const="", metavar="RUTA",
                   help="Exportar la página a un solo HTML (por defecto salida/canasta.html) sin abrirlo.")
    p.add_argument("--perfil", help="Armar en la consola la canasta de uno o más perfiles de referencia/perfiles.csv, "
                                    "separados por comas (un hogar).")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--direccion", default="", help="Dirección a ubicar con Georef (en lugar de --lat/--lon).")
    p.add_argument("--provincia", default="")
    p.add_argument("--localidad", default="")
    p.add_argument("--dias", type=int, default=cfg.DIAS_PREDETERMINADO, choices=sorted(cfg.DIAS_PERIODO))
    p.add_argument("--listos", action="store_true", help="Solo alimentos listos para comer.")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


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
    for s in r["sucursales"]:
        costo = f"${num(s['costo'])}" if s["costo"] is not None else s["mensaje"]
        marca = "→" if s.get("elegida") else " "
        falta = f" (no cubre: {'; '.join(s['faltantes'])})" if s["faltantes"] else ""
        print(f" {marca} {s['bandera']:<28} {s['distancia_km']:>5.2f} km  {costo}{falta}")
    t = r["ticket"]
    print(f"\n{'=' * 64}\n{t['tienda']['bandera']} — {t['tienda']['sucursal']}\n{t['tienda']['direccion']}"
          f"\nPrecios del {t['fecha_precios']} · compra para {r['periodo']}\n{'-' * 64}")
    for it in t["items"]:
        print(f"{it['cantidad']:>16}  {it['nombre'][:34]:<34} ${num(it['subtotal'], 2):>11}")
    print(f"{'-' * 64}\n{'TOTAL':>52} ${num(t['total'], 2):>11}\n{'por día':>52} ${num(t['costo_diario'], 2):>11}")
    for persona in r["personas"]:
        pendientes = [c for c in persona["cobertura"] + persona["reglas"] if c["estado"] not in ("cumple", "no_aplica")]
        if pendientes:
            print(f"\nCobertura de {persona['datos']['nombre']}:")
            for c in pendientes:
                print(f"  {c['estado']:<11} {c['nombre']}: {c['valor']} {c['unidad']} ({c['nota']})")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    cfg_sepa.configurar_logging(args.verbose)
    if not args.perfil:
        from canasta import exportar
        ruta = exportar.exportar(Path(args.exportar) if args.exportar else exportar.RUTA_EXPORTACION)
        if args.exportar is None:
            webbrowser.open(ruta.resolve().as_uri())
        return 0

    from canasta import resultado, ubicacion
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
    _imprimir(resultado.armar(hogar, lat, lon, args.dias, listos=args.listos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
