# TP3 Optimización — "Diseño de Supermercados" (CarroMenos)

Localización de centros de distribución para la cadena CarroMenos: qué centros abrir (A, B, C,
D) y cómo mover los pallets de 5 productos desde 7 plantas hasta 10 supermercados, minimizando
costo e informando consumo de combustible y emisiones de CO₂.

Investigación de Operaciones I · UCA · 2026 2C

---

## Estado: terminado, listo para entregar

El informe está en [`informe/informe.pdf`](informe/informe.pdf) (21 páginas con carátula e índice; fuente:
[`informe/informe.tex`](informe/informe.tex)).

| Pregunta | Respuesta |
|---|---|
| **a)** Localización óptima | **Abrir A, C y D** (gerente, 6 conductores): **$56,1 M/mes**, 35.478 l de gasoil y 95,1 t de CO₂ por mes. Es la más barata y la de menos emisiones de las 3 configuraciones posibles |
| **b)** Centro único, capacidad infinita y costo nulo | En el **noroeste de la Ciudad (Villa Urquiza)**, determinado por calle con OSRM. Aun gratis, gasta en transporte $12,5 M más que la red A+C+D |
| **c)** Precio mínimo de Goyito | **$1.081 por pallet** para todo junto; por producto, de $630 (gaseosas) a $1.520 (arroz). El viaje directo recorre 18 % menos km |
| **d)** Flota propia también desde las plantas | **$80,9 M/mes (+44 %)**, 18 conductores; CO₂ −3,3 % |
| **e)** Tope de 500 km por conductor | Variable de desvío con penalidad: **$98,8 M/mes (+76 %)**; el CO₂ **sube** 0,6 % porque el modelo desvía km al tercerizado |

La decisión A+C+D es robusta: solo cambia si la tarifa del tercerizado supera $891/km (→ A+C).

## Orden de lectura

| # | Archivo | Por qué |
|---|---|---|
| 1 | [`informe/informe.pdf`](informe/informe.pdf) | El entregable |
| 2 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) | El plan: consigna (§0), datos, supuestos, modelo, guía por pregunta (§12), tests (§13) |
| 3 | [`docs/procedimiento.md`](docs/procedimiento.md) | La bitácora: datos con fuente (§1.1), **desvíos D1 a D16 (§2)**, resultados (§3), tests (§4), verificaciones y predicciones del plan contra resultados (§5) |
| 4 | [`docs/tareas.md`](docs/tareas.md) | Las 31 tareas, todas hechas |
| 5 | [`docs/lo_que_queda_por_hacer.md`](docs/lo_que_queda_por_hacer.md) | Registro del traspaso a mitad del trabajo (ya completado) |

> ⚠️ Igual que en el TP1 y el TP2: el plan **no se corrigió**. Los desvíos están en
> `docs/procedimiento.md` §2.

## Estructura

```
TP3/
├── README.md
├── requirements.txt
├── Ubicaciones link.txt      links del mapa y del portafolio de redes
├── Consigna/                 el enunciado
├── Material/                 clases 09 (redes) y 10 (proyectos y scheduling)
├── datos/                    ubicaciones.kml/.csv (21 puntos), distancias OSRM y haversine,
│                             consultas OSRM/Nominatim de la pregunta b)
├── docs/                     plan_de_trabajo.md, tareas.md, procedimiento.md, lo_que_queda_por_hacer.md
├── src/                      config, datos, modelo, sensibilidad, weber, reportes, graficos
├── scripts/                  00 a 08 (ver abajo)
├── resultados/               tablas/ (CSV 01 a 17) y graficos/ (PNG 01 a 12)
└── informe/                  informe.tex + informe.pdf (se compila con .vscode/settings.json)
```

## Cómo correrlo

Los scripts resuelven la raíz del proyecto solos: se pueden correr desde cualquier carpeta.

```bash
pip install -r requirements.txt      # pulp, pandas, matplotlib, scipy, requests, highspy
python scripts/01_distancias.py      # solo si falta datos/distancias_osrm.csv (necesita internet)
python scripts/00_verificar_datos.py # siempre primero: 27 chequeos contra la consigna
python scripts/02_punto_a.py         # a): óptimo, configuraciones, frontera costo–CO₂, mapa
python scripts/03_sensibilidad.py    # informe b): rangos (highspy), control cruzado, barridos
python scripts/04_punto_b.py         # b): punto de Weber + grilla por calle (OSRM ya guardado)
python scripts/05_punto_c.py         # c): umbral de Goyito por producto
python scripts/06_punto_d.py         # d): flota propia en los dos tramos
python scripts/07_punto_e.py         # e): tope de 500 km por conductor
python scripts/08_tests_supuestos.py # tests A a G
```

Cada script termina con asserts: si algo cambia en los datos o en el entorno, se detiene. Después
de correrlos, el informe se compila con dos pasadas de `pdflatex` (Ctrl+Alt+B en VS Code).
