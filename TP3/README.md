# TP3 Optimización — "Diseño de Supermercados" (CarroMenos)

Localización de centros de distribución para la cadena CarroMenos: qué centros abrir (A, B, C,
D) y cómo mover los pallets de 5 productos desde 7 plantas hasta 10 supermercados, minimizando
costo e informando consumo de combustible y emisiones de CO₂.

Investigación de Operaciones I · UCA · 2026 2C

---

## Estado: F0 a F3 hechas — modelo, pregunta a) y sensibilidad

**Óptimo: abrir A, C y D** (con gerente, 6 conductores), **$56,1 M por mes**, 95 t de CO₂ por mes.
Le gana a A+C (el más barato en costos fijos) por $1,67 M: el transporte pesa más que los fijos.
La decisión es robusta: solo cambia si la tarifa del tercerizado supera $891/km (→ A+C) y la
demanda no puede crecer más de 25 %. Sigue la fase F4 (preguntas b a e) de [`docs/tareas.md`](docs/tareas.md). Resultados y desvíos en
[`docs/procedimiento.md`](docs/procedimiento.md).

## Orden de lectura

| # | Archivo | Por qué |
|---|---|---|
| 1 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) §0 | Las dos listas a)–e) de la consigna (informe ≠ preguntas) |
| 2 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) §2 y §4 | Los datos y las primeras cuentas: **ningún centro solo alcanza** |
| 3 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) §5 a §8 | Supuestos adoptados y el modelo (variables, funcional, restricciones) |
| 4 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) §12 | Cómo se responde cada pregunta |
| 5 | [`docs/tareas.md`](docs/tareas.md) | **El trabajo dividido en tareas**, en orden, con dependencias |
| 6 | [`docs/procedimiento.md`](docs/procedimiento.md) | La bitácora: valores con fuente, desvíos y resultados |
| 7 | [`docs/lo_que_queda_por_hacer.md`](docs/lo_que_queda_por_hacer.md) | **Para quien sigue:** qué falta, cómo usar el código y qué evitar |

> ⚠️ Igual que en el TP1 y el TP2: una vez planteado, **el plan no se corrige**. Los desvíos van a
> `docs/procedimiento.md` §2.

## Estructura

```
TP3/
├── README.md
├── requirements.txt
├── Ubicaciones link.txt      links del mapa y del portafolio de redes
├── Consigna/                 el enunciado
├── Material/                 clases 09 (redes) y 10 (proyectos y scheduling)
├── datos/                    ubicaciones.kml/.csv (21 puntos), distancias_osrm.csv y _haversine.csv
├── docs/                     plan_de_trabajo.md, tareas.md y procedimiento.md
├── src/                      config, datos, modelo, sensibilidad, reportes, graficos
├── scripts/                  00_verificar_datos, 01_distancias, 02_punto_a, 03_sensibilidad
├── resultados/               tablas/ y graficos/
└── informe/                  informe.tex (se compila con .vscode/settings.json, igual que TP2)
```

## Cómo correrlo

```bash
pip install -r requirements.txt      # pulp, pandas, matplotlib, scipy, requests, highspy
python scripts/01_distancias.py      # solo si falta datos/distancias_osrm.csv (necesita internet)
python scripts/00_verificar_datos.py # siempre primero: 27 chequeos contra la consigna
python scripts/02_punto_a.py         # pregunta a): óptimo, configuraciones, frontera costo–CO₂, mapa
python scripts/03_sensibilidad.py    # informe b): rangos (highspy), control cruzado, barridos
```
