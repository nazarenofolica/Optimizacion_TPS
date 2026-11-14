---
name: canasta-verificar
description: Use after changing anything in TPF/base_sepa/canasta (motor Python o motor.js, rutas, página, estilos) to export the page, run the unit and parity tests, and look at the real page in a browser before claiming it works.
---

# Verificar la canasta

La canasta tiene **dos motores que tienen que dar lo mismo**: Python (`canasta/modelo.py`, `oferta.py`,
`resultado.py`, `rutas.py`) y el de la página (`canasta/web/motor.js`, `rutas.js`). Todo cambio de lógica se hace en
los dos lados. La página es un único HTML estático que genera `canasta/exportar.py`.

Todo se corre desde `TPF/base_sepa/`.

## 1. Tests rápidos (siempre)

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

Incluye `tests/test_rutas.py`: servicio de rutas simulado, selección por tiempo caminando y cuentas del ticket con
los datos reales (sin red).

## 2. Paridad Python vs navegador (si tocaste un motor)

```bash
CANASTA_TEST_PAGINA=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_pagina -v
```

Necesita Chrome o Edge e internet (HiGHS se baja de jsDelivr); tarda unos minutos. Carga los datos (~1 GB) y Chrome:
no lo corras al mismo tiempo que otra suite que cargue los datos, porque Windows se queda sin memoria virtual.

## 3. Mirar la página de verdad

```bash
python -m canasta                 # exporta datos/sepa/canasta_local.html con ORS_API_KEY (.env) y la sirve
python -m canasta --exportar      # datos/sepa/canasta.html, la versionada: nunca lleva la clave
```

Captura sin interacción (armado automático por URL):

```bash
"C:/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu \
  --virtual-time-budget=600000 --window-size=1280,2400 --screenshot=captura.png \
  "http://localhost:8765/canasta_local.html?perfiles=oficinista&lat=-34.60386&lon=-58.38419&caminata=15&motor=pagina"
```

Probá al menos 375 px y 1280 px de ancho. `?rutas=0` busca como antes (línea recta), `?caminata=30` cambia el límite.

## Qué revisar a mano

- Con clave: tiempos reales y recorrido dibujado. Con clave inválida o sin red: aviso visible y tiempos marcados
  "estimado"; nunca un recorrido inventado.
- "Ver si conviene caminar hasta N min" recalcula las sucursales y la canasta, y muestra el ahorro (o que no lo hay).
- El ticket: suma de subtotales = total; las promociones dicen "no aplicada".
- Si algo solo funcionó con datos simulados, decilo así.
