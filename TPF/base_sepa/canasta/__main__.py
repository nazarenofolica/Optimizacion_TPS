"""
Canasta saludable: la compra más barata que cubre lo que necesita un hogar, en el supermercado de su zona, con los
precios del modelo estrella de SEPA 2.0 (../datos/sepa/).

    python -m canasta                       # exporta datos/sepa/canasta_local.html con la clave de rutas y la abre
                                            # servida en http://localhost (Ctrl+C para cerrar)
    python -m canasta --exportar [RUTA]     # solo exporta (por defecto datos/sepa/canasta.html, sin clave)
    python -m canasta --perfil celiaca --direccion "Av Corrientes 1234" --provincia "Ciudad Autónoma de Buenos Aires"
    python -m canasta --perfil oficinista,trabajo_fisico,escolar --lat -32.95 --lon -60.64 --dias 14 --listos
    python -m canasta --perfil oficinista --lat -34.6037 --lon -58.3816 --caminata 15
    python -m canasta --perfil oficinista --lat -34.6037 --lon -58.3816 --caminata 15 --agua compra

Con --perfil, la canasta la arma en la consola el motor de Python (la referencia del que corre en la página). Con
--caminata, solo se evalúan las sucursales a las que se llega caminando en esos minutos (rutas de OpenRouteService:
ORS_API_KEY en base_sepa/.env).
"""

from __future__ import annotations

import argparse
import functools
import http.server
import logging
import subprocess
import sys
import threading
import webbrowser
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
        _servir(ruta, args.puerto)
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
    extra = {}
    if args.caminata:
        tiempos, aviso = rutas.tiempos_caminando(lat, lon, args.caminata)
        extra = {"tiempos": tiempos, "caminata_minutos": args.caminata, "aviso_tiempos": aviso}
    _imprimir(resultado.armar(hogar, lat, lon, args.dias, listos=args.listos, agua=args.agua, **extra))
    return 0


def _servir(ruta: Path, puerto: int) -> None:
    """Sirve la carpeta de la página en http://localhost: desde file:// los mapas de OpenStreetMap pueden no cargar
    (piden el encabezado Referer) y el navegador no comparte la ubicación."""
    manejador = functools.partial(_Silencioso, directory=str(ruta.parent))
    try:
        servidor = http.server.ThreadingHTTPServer(("127.0.0.1", puerto), manejador)
    except OSError:
        servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), manejador)     # el puerto estaba ocupado
    url = f"http://localhost:{servidor.server_address[1]}/{ruta.name}"
    print(f"Canasta en {url}  (Ctrl+C para cerrar)")
    threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # noqa: D102 - sin una línea por pedido en la consola
        pass


if __name__ == "__main__":
    sys.exit(main())
