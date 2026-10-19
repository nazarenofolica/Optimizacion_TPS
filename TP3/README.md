# TP3 Optimización — "Diseño de Supermercados" (CarroMenos)

Localización de centros de distribución para la cadena CarroMenos: qué centros abrir (A, B, C,
D) y cómo mover los pallets de 5 productos desde 7 plantas hasta 10 supermercados, minimizando
costo e informando consumo de combustible y emisiones de CO₂.

Investigación de Operaciones I · UCA · 2026 2C

---

## Estado: modelo planteado, sin código

Plan de trabajo completo (supuestos, modelo, sensibilidad, guía por pregunta, tests) y dividido en
31 tareas. **Nada resuelto ni codificado todavía.** Se arranca por la fase F0 de
[`docs/tareas.md`](docs/tareas.md) (buscar los datos que la consigna no da).

## Orden de lectura

| # | Archivo | Por qué |
|---|---|---|
| 1 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) §0 | Las dos listas a)–e) de la consigna (informe ≠ preguntas) |
| 2 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) §2 y §4 | Los datos y las primeras cuentas: **ningún centro solo alcanza** |
| 3 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) §5 a §8 | Supuestos adoptados y el modelo (variables, funcional, restricciones) |
| 4 | [`docs/plan_de_trabajo.md`](docs/plan_de_trabajo.md) §12 | Cómo se responde cada pregunta |
| 5 | [`docs/tareas.md`](docs/tareas.md) | **El trabajo dividido en tareas**, en orden, con dependencias |
| 6 | [`docs/procedimiento.md`](docs/procedimiento.md) | La bitácora (por ahora, sólo la preparación) |

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
├── datos/                    ubicaciones.kml (export del mapa) y ubicaciones.csv (21 puntos)
├── docs/                     plan_de_trabajo.md, tareas.md y procedimiento.md
├── src/                      (vacío) config, datos, modelo, reportes, graficos
├── scripts/                  (vacío) 00_verificar_datos.py, uno por pregunta, tests
├── resultados/               tablas/ y graficos/
└── informe/                  informe.tex (se compila con .vscode/settings.json, igual que TP2)
```

## Cómo correrlo

```bash
pip install -r requirements.txt      # pulp, pandas, matplotlib, scipy
```

Los scripts todavía no existen. Como en los TP anteriores, **`00_verificar_datos.py` se corre
siempre primero**.
