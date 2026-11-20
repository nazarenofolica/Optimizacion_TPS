# Checklist: de POC a MVP de la canasta saludable

Estado al 20/11/2026. Detalle del camino a producción en [docs/ROADMAP.md](docs/ROADMAP.md); investigación de
herramientas en [docs/GITHUB_RESEARCH.md](docs/GITHUB_RESEARCH.md).

## Hecho

### Mapas y rutas
- [x] Rutas peatonales reales con OpenRouteService (perfil `foot-walking`), probadas con la clave real.
- [x] Tiempo máximo de caminata configurable (15, 30, 45 o 60 min; 15 por defecto, en `canasta/config.py`).
- [x] Las sucursales fuera del límite quedan afuera antes de optimizar (restricción del espacio de búsqueda).
- [x] "¿Conviene caminar más?": costo con cada límite; cada uno se calcula con un clic y se guarda.
- [x] Recorrido a pie dibujado (animado) hasta la sucursal elegida; las de fuera del límite, atenuadas.
- [x] Sin clave o si el servicio falla: tiempos estimados por distancia, con aviso; nunca un recorrido inventado.
- [x] Mapa gris arreglado: `python -m canasta` sirve la página por `http://localhost`; teselas de OSM actualizadas.
- [x] Otros arreglos del mapa: superposición en el celular, mapas que no se liberaban, respuestas viejas de Georef,
      nombres "null".
- [x] La clave se lee de `base_sepa/.env` (ignorado por git) y nunca va en la página versionada.

### Interfaz
- [x] Portada en tinta con el borde dentado del ticket y un ticket con los datos reales del día que se imprime,
      se mece y sigue al mouse.
- [x] Armado del perfil como asistente horizontal de tres pasos, con resumen en cada pestaña, tilde al completarse
      y transición entre pasos.
- [x] "Armar la canasta" bloqueado hasta completar los pasos 1 y 2 (dice qué falta).
- [x] Ticket conservado y mejorado: sale de la impresora renglón por renglón, se mece, muestra los minutos
      caminando, columnas alineadas, promociones "no aplicadas", energía y metas; se puede imprimir.
- [x] El horario del ticket dice "Horario de hoy (día)" para no confundirse con la fecha de los precios.
- [x] Resultado: el total cuenta hasta su valor; bloque de cómo llegar; tabla de sucursales con minutos y diferencia.
- [x] Calorías por grupo en una dona animada; nutrientes y Guías en gráficos de bala (meta y valor).
- [x] Cálculo de requerimientos en tarjetas con la fórmula desplegable; restricciones desplegables.
- [x] "Cómo se elige la compra" como diagrama en etapas, con las cifras del modelo.
- [x] Respeta "reducir movimiento"; modo oscuro.

### Calidad y documentación
- [x] 101 tests de Python (incluye rutas simuladas, filtro por tiempo y cuentas del ticket).
- [x] Test de paridad entre el motor de Python y el del navegador, también para la búsqueda por tiempo.
- [x] `docs/GITHUB_RESEARCH.md`, `docs/ROADMAP.md`, `CLAUDE.md`, `PRODUCT.md`, README y PLAN_DE_TRABAJO.
- [x] Skills versionadas en `.claude/skills/`: impeccable, systematic-debugging, verification-before-completion y
      canasta-verificar.
- [x] `python -m canasta` exporta en un proceso aparte y no retiene 1 GB de memoria mientras sirve.

### Cierre del POC (15/11/2026)
- [x] Revisado a 375 px el asistente, los gráficos y el ticket. La tabla de sucursales pasa a filas apiladas en el
      celular (antes "Qué no cubre" quedaba fuera de pantalla y las filas eran altísimas).
- [x] Modo oscuro revisado en todas las secciones.
- [x] Impresión del ticket: sale solo el ticket; ningún producto se parte entre páginas.
- [x] Escalera con dos personas (15 → 30 → 45 → 15): calcula, guarda y vuelve sin recalcular. "Más barata" va solo
      en el menor tiempo que logra el precio mínimo, y el mensaje al volver a un límite menor tiene sentido.
- [x] 101 tests y paridad (2/2) después del rediseño.
- [x] Presentación con la demo en vivo: `informe/presentacion.html` (`python informe/presentar.py`).
- [x] Commit en la rama `POC`.

## Etapa 1 (20/11/2026)

Lo que pidieron el docente y un compañero después de la presentación del POC.

- [x] Objetivo "Aumentar de peso", distinto de "Ganar masa muscular": +500 kcal/día sobre el gasto, proteína
      1,2 g/kg y aviso si el IMC es de sobrepeso. Perfil `bajo_peso` (mujer de 22 años, IMC 16,9): 2.310 kcal/día.
- [x] El agua como restricción, con tres modos: `canilla` (predeterminado, informativo y gratis; los resultados de
      antes no cambian), `compra` (agua total de NASEM 2004, contando la de los alimentos) y `bebidas` (los 8 vasos
      de las Guías). Selector en la página, `?agua=` y `--agua`.
- [x] Caso precargado que no llega a las 37 metas (`restricciones_extremas`, solo listos, Córdoba, 15 min): la mejor
      sucursal cubre 35; la página avisa cuánto cubre cada meta y qué probar.
- [x] Arreglos: productos por unidad sin "NaN" en el ticket, contador del total que podía arrancar negativo, dona
      sin grupos de 0 kcal.
- [x] 114 tests de Python y paridad (2/2) con 8 casos, incluidos el agua y el caso que no llega.
- [x] Presentación: casos nuevos en la demo, etiquetas de agua y peso, límites y etapas que siguen.

## Etapa 2 · Compra en varias sucursales

- [ ] MILP con una binaria "visito la sucursal s" y un costo por visita; máximo de dos visitas para empezar.
- [ ] Comparación contra la mejor sucursal sola ("partiendo la compra ahorrás $X").
- [ ] Ticket por sucursal y recorrido a pie entre las dos; paridad Python / navegador.

## Etapa 3 · ETL diario y CI

- [ ] GitHub Actions cada mañana: bajar SEPA, rearmar la base, exportar y publicar la página.
- [ ] Si la verificación falla, no se publica y queda la del día anterior; aviso por mail o issue.
- [ ] Tests de Python y paridad en cada push; tests de la página con Playwright; motor JavaScript con Node.
- [ ] Entorno reproducible con `uv`.

## Etapa 4 · Restricciones nuevas

- [ ] Kosher, halal y sin cerdo (y pescetariano, exclusión de ingredientes); recargar la base.
- [ ] Vitaminas y condiciones médicas con fuente y aviso de supervisión profesional (`referencia/condiciones.csv`).

## Etapa 5 · Promociones con condiciones

- [ ] Fuente de promociones con sus condiciones (catálogos web de las cadenas).
- [ ] 2×1, 2.ª unidad y porcentaje en el modelo; el ticket muestra precio de lista, descuento y precio efectivo.

## Etapa 6 · LLM con Groq

- [ ] Backend chico (FastAPI) que guarde las claves (Groq y rutas) y cachee las consultas de rutas.
- [ ] Texto libre (por ejemplo, una prescripción médica) → restricciones y metas que la persona confirma.

## Otros pendientes

- [ ] Rutas para uso público: autoalojar OpenRouteService u OSRM.
- [ ] Costo con 15, 30, 45 y 60 min de una vez; objetivos secundarios con un tope de costo explícito.
- [ ] Autocompletado de direcciones y lista de compras para compartir.
- [ ] Deploy y monitoreo.

## Fuera de alcance

- Historial de precios.
- Promociones bancarias.
