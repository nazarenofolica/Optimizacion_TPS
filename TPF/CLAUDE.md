# TPF: canasta saludable al menor precio

- `base_sepa/sepa/`: pipeline de datos (`python -m sepa`) → `datos/sepa/` (dim_producto, dim_tienda, fact_precio).
- `base_sepa/canasta/`: la canasta. Motor Python (`modelo.py`, `oferta.py`, `resultado.py`, `rutas.py`) y página
  estática (`web/`: `motor.js`, `rutas.js`, `app.js`, `estilos.css`, `index.html`), que `exportar.py` arma en un único
  HTML con los datos adentro.
- Documentación: `docs/ROADMAP.md`, `docs/GITHUB_RESEARCH.md`, `base_sepa/PLAN_DE_TRABAJO.md`, `PRODUCT.md`.

## Reglas

- **Dos motores, una lógica.** Todo cambio en la selección de sucursales, las restricciones, el modelo o el ticket se
  hace en Python y en `motor.js`, y se corre el test de paridad. Los parámetros viven en `canasta/config.py` y llegan a
  la página solos (`exportar.parametros()`), salvo los que empiezan con `RUTA_`, `DIR_` o `URL_`.
- El orden de `RESTRICCIONES` define los bits de aptitud de la página: no reordenar.
- La clave de OpenRouteService (`ORS_API_KEY` en `base_sepa/.env`) **nunca** va en `datos/sepa/canasta.html`
  (versionada): solo en `canasta_local.html` (ignorada por git).
- Un tiempo estimado se muestra como estimado; no se dibuja un recorrido que no vino del servicio de rutas.

## Correr y verificar (desde `base_sepa/`)

```bash
python -m canasta                    # página local con rutas reales, en http://localhost:8765
python -m canasta --exportar         # página versionada (sin clave)
python -m canasta --perfil oficinista --lat -34.6037 --lon -58.3816 --caminata 15
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
CANASTA_TEST_PAGINA=1 PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_pagina -v   # paridad, ~5 min
```

No correr dos suites que carguen los datos a la vez: Windows se queda sin memoria virtual. Ver la skill
`.claude/skills/canasta-verificar`. Para UI: `.claude/skills/impeccable` y `PRODUCT.md`.
