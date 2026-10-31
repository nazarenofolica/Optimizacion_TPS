# TPF El problema de la dieta — Procedimiento (bitácora de desarrollo)

> **Qué es este archivo.** La bitácora: lo que efectivamente se hizo, en orden, y lo que cambió respecto
> del [plan](plan_de_trabajo.md). El plan no se corrige: los desvíos se anotan acá.

---

## 0. Preparación

Estructura de carpetas igual a la de los TP anteriores (`Consigna/`, `Material/`, `datos/`, `docs/`,
`src/`, `scripts/`, `resultados/`, `informe/`) y receta de compilación de LaTeX en
`.vscode/settings.json`.

## 1. Base de datos (terminada)

### 1.1. Qué se hizo

La base del trabajo se armó con el pipeline de [`../base_sepa/`](../base_sepa/) (proyecto SEPA 2.0)
sobre el archivo de SEPA del viernes 23 de octubre de 2026, y quedó en
[`../datos/sepa/`](../datos/sepa/):

| Tabla | Filas |
|---|---:|
| `dim_producto` | 28.036 |
| `dim_tienda` | 2.666 |
| `fact_precio` | 8.241.172 |

Cómo se arma cada tabla, paso por paso: [`../base_sepa/README.md`](../base_sepa/README.md).

### 1.2. Verificaciones

- Los 52 controles de la base pasan (ninguno crítico falla): claves únicas, integridad referencial,
  nutrientes posibles, composición coherente, precios positivos, coordenadas dentro del país
  ([`../datos/sepa/calidad/verificacion.csv`](../datos/sepa/calidad/verificacion.csv)). Los dos avisos
  no críticos son 10 sucursales sin ficha en SEPA y 5 con ubicación dudosa.
- Los 57 tests del pipeline pasan (`cd base_sepa && python -m unittest discover -s tests`).
- Lo excluido está con su motivo en [`../datos/sepa/calidad/`](../datos/sepa/calidad/).

## 2. Desvíos respecto del plan *(pendiente)*

## 3. Resultados por pregunta *(pendiente)*

## 4. Tests de supuestos *(pendiente)*

## 5. Conclusiones para el informe *(pendiente)*
