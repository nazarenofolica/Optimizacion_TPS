"""La fecha de los precios de cada sucursal en la canasta (tolerancia de sepa/config.DIAS_TOLERANCIA_PRECIO): una
cadena que no publicó el día entra con sus últimos precios, con su fecha, y la canasta lo dice ("precios de hace N
días") en la tabla de sucursales y en el ticket (también en el de dos súper). Sin red; los últimos, con los datos."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from canasta import config as cfg
from canasta import oferta, resultado
from sepa import config as cfg_sepa


def _dim_tienda(fechas: list[str] | None) -> pd.DataFrame:
    n = 3
    t = pd.DataFrame({c: [None] * n for c in oferta.COLUMNAS_TIENDA})
    t["id_tienda"] = ["10-1-1", "8-1-1", "20-1-1"]
    t["lat"], t["lon"], t["es_web"] = [-34.6] * n, [-58.4] * n, [False] * n
    if fechas is not None:
        t["fecha_precios"] = pd.to_datetime(fechas)
    return t


class TestFechaPorSucursal(unittest.TestCase):
    def _tiendas(self, fechas, fecha_fact="2026-11-20"):
        with tempfile.TemporaryDirectory() as tmp:
            ruta_t, ruta_f = Path(tmp) / "dim_tienda.parquet", Path(tmp) / "fact_precio.parquet"
            _dim_tienda(fechas).to_parquet(ruta_t, index=False)
            pd.DataFrame({"fecha": pd.to_datetime([fecha_fact])}).to_parquet(ruta_f, index=False)
            with mock.patch.object(cfg, "RUTA_DIM_TIENDA", ruta_t), mock.patch.object(cfg, "RUTA_FACT_PRECIO", ruta_f):
                return oferta._tiendas()

    def test_cada_sucursal_con_su_fecha_y_sus_dias(self):
        t, base = self._tiendas(["2026-11-20", "2026-11-19", "2026-11-05"])
        self.assertEqual(base, "2026-11-20")                                   # la más reciente
        self.assertEqual(t["fecha_precios"].tolist(), ["2026-11-20", "2026-11-19", "2026-11-05"])
        self.assertEqual(t["dias_precios"].tolist(), [0, 1, 15])

    def test_base_anterior_sin_fecha_por_sucursal(self):
        # Una base de antes de la tolerancia (sin dim_tienda.fecha_precios): todas con la fecha de fact_precio.
        t, base = self._tiendas(None, "2026-10-23")
        self.assertEqual(base, "2026-10-23")
        self.assertEqual(set(t["fecha_precios"]), {"2026-10-23"})
        self.assertEqual(set(t["dias_precios"]), {0})

    def test_la_sucursal_del_ticket_dice_su_fecha(self):
        t, _ = self._tiendas(["2026-11-20", "2026-11-19", "2026-11-05"])
        fila = t.loc["8-1-1"]
        self.assertEqual(resultado._fecha_tienda(fila), {"fecha_precios": "2026-11-19", "dias_precios": 1})

    def test_la_tolerancia_del_pipeline(self):
        self.assertEqual(cfg_sepa.DIAS_TOLERANCIA_PRECIO, 15)


@unittest.skipUnless(cfg.RUTA_FACT_PRECIO.exists(), "faltan las tablas de ../datos/sepa/")
class TestFechaConDatos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = oferta.cargar()

    def test_ninguna_sucursal_con_precios_de_mas_de_la_tolerancia(self):
        t = self.d.tiendas
        self.assertEqual(self.d.fecha, max(t["fecha_precios"]))
        self.assertTrue(t["dias_precios"].between(0, cfg_sepa.DIAS_TOLERANCIA_PRECIO).all())

    def test_sucursal_con_precios_de_un_dia_anterior_lo_dice(self):
        # La más cercana de las evaluables con precios de un día anterior (si la base tiene alguna): armada en su
        # puerta, aparece en la tabla con sus días y, si es la elegida, el ticket lleva su fecha.
        t = oferta._evaluables(self.d, -34.60386, -58.38419)
        viejas = t[t["dias_precios"] > 0]
        if viejas.empty:
            self.skipTest("la base no tiene supermercados con precios de días anteriores")
        v = viejas.iloc[0]
        from canasta import requerimientos as rq
        oficinista = next(p for p in rq.perfiles() if p["id"] == "oficinista")
        r = resultado.armar([rq.persona_desde(oficinista)], float(v["lat"]), float(v["lon"]), 7)
        self.assertEqual(r["fecha_precios"], self.d.fecha)
        fila = next(s for s in r["sucursales"] if s["id"] == v.name)
        self.assertEqual((fila["fecha_precios"], fila["dias_precios"]), (v["fecha_precios"], int(v["dias_precios"])))
        ticket = r["ticket"]
        self.assertEqual(ticket["fecha_precios"], ticket["tienda"]["fecha_precios"])
        elegida = next(s for s in r["sucursales"] if s.get("elegida"))
        self.assertEqual(ticket["tienda"]["dias_precios"], elegida["dias_precios"])


if __name__ == "__main__":
    unittest.main()
