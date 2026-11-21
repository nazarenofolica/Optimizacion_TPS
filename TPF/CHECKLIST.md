# Checklist: de POC a MVP de la canasta saludable

Estado al 21/11/2026. Detalle del camino a producción en [docs/ROADMAP.md](docs/ROADMAP.md); investigación de
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

## Etapa 2 (20/11/2026) · Compra en dos supermercados

Lo que pidió el docente: si dos súper quedan cerca, comprar parte en cada uno.

- [x] Formulación con binarias de visita (`y_A = 1`, `Σ y_s ≤ 2`, `x_p ≤ x_max_p · y_s(p)`), resuelta enumerando
      los pares (A, B): equivalente, y el MILP con binarias no fue más rápido y dio compras más caras. Se sacan de B
      los productos que A vende igual o más barato.
- [x] Vecinas a ≤ 10 min caminando de la sucursal elegida, hasta 4, primero de otras cadenas.
- [x] Decisión lexicográfica sin precio al minuto: conviene si cubre mejor las metas o, con las mismas, si ahorra
      ≥ 3 % y ≥ $1.000; "ahorrás $X (Y %) caminando Z min más (estimado)".
- [x] A pedido: botón "¿Conviene sumar un segundo súper?", `&dos=1` en el enlace y `--dos-super` en la consola.
- [x] Página: decisión, tabla un súper vs dos súper, qué se compra en cada uno, recorrido casa → A → B → casa (A → B
      estimado; ruta de ORS solo para dibujar), ticket dividido por sucursal con subtotales y mapa con el 2.º súper.
- [x] 127 tests de Python y paridad (3/3), también para dos súper (Microcentro, Córdoba a 15 y a 30 min).
- [x] Presentación: caso "Dos súper" en la demo, la formulación en la diapositiva del motor, etapa 2 en "Hecho".

## Etapa 3 (21/11/2026) · ETL diario y CI

Hecha en el repo; la activa el dueño una sola vez ([docs/DESPLIEGUE.md](docs/DESPLIEGUE.md)). No se probó todavía en
GitHub.

- [x] GitHub Actions cada día (07:30 y 18:00 de Argentina; SEPA sube el ZIP a la tarde): bajar SEPA, rearmar la base,
      exportar y publicar la página en GitHub Pages, sin commitear los datos del día (`.github/workflows/tpf-diario.yml`).
- [x] Modo diario `python -m sepa --diario` y `--ultima-fecha`; las fuentes que no cambian a diario viajan en la caché
      de Actions. Si SEPA no publicó un día nuevo, termina bien y sin cambios.
- [x] Si la verificación falla, no se publica y queda la del día anterior; mail de GitHub e issue (uno solo).
- [x] Tests de Python en cada push y pull request que toque `TPF/` (`.github/workflows/tpf-tests.yml`); paridad a mano.
- [x] 142 tests de Python (10 del modo diario).
- [ ] Activarlo: push, merge a `main`, Settings → Pages → "GitHub Actions" y la primera corrida a mano.
- [ ] Paridad en cada push; tests de la página con Playwright; motor JavaScript con Node.
- [ ] Controles contra el día anterior (precios que saltan, sucursales que desaparecen).
- [ ] Entorno reproducible con `uv`.

## Etapa 4 (21/11/2026) · Restricciones nuevas y condiciones médicas

- [x] Columnas de dieta y religión (`sepa/producto/religion.py`: cerdo, carne, gelatina, alcohol, vino, carmín y
      rótulos kosher y halal), como paso del pipeline y aplicables al `dim_producto` existente (la canasta las calcula
      al cargar si el parquet no las trae).
- [x] Sin cerdo, halal y kosher al final de `RESTRICCIONES` (bits 15 a 17), con criterio y fuentes en `config.py` y en
      el texto de la página. Sin certificaciones en la base: halal y kosher no ofrecen carnes ni aves (0 rotuladas en la
      canasta; 2 productos kosher o parve en toda la base, ninguno halal).
- [x] Condiciones médicas en `referencia/condiciones.csv` (anemia, osteoporosis, colesterol alto, déficit de B12 y de
      vitamina D, enfermedad renal): cambian metas con su fuente en los dos motores, sin pasar ningún máximo tolerable;
      las que requieren supervisión lo avisan (bits 18 a 23, sin filtrar productos).
- [x] Página: grupos "Dieta y religión", "Alergias" y "Salud", marca "con supervisión" y su aviso al elegirla, "Qué
      exige cada una" desplegable; perfiles ocultos `kosher`, `halal` y `anemia`.
- [x] 161 tests de Python (18 nuevos): religión con productos sintéticos, aptos con los datos reales, canastas reales en el Microcentro y
      Córdoba, cada condición cambia lo que dice la tabla, ningún mínimo pasa un máximo; un caso más de paridad
      (kosher, halal y anemia en el Microcentro) que además compara avisos y criterios.
- [x] Presentación: etapa 4 en "Hecho"; "Dieta y religión" y "Salud" en el modelo.
- [ ] Certificaciones de verdad (etiquetas de Open Food Facts o listas de las certificadoras) para ofrecer carnes y
      lácteos kosher o halal; separar carne y leche por comida (hoy la canasta es por día).
- [ ] Pescetariano y exclusión de ingredientes puntuales.

## Etapa 5 (21/11/2026) · Promociones con condiciones

- [x] Fuente: las leyendas de SEPA (promo 1 y 2), que el pipeline ahora guarda (`sepa/fuentes/sepa.py`).
- [x] Clasificador de leyendas (`sepa/precio/promociones.py`): porcentaje, n×m, 2.ª unidad, precio fijo, llevando n;
      condiciones de pago (no se aplican), horario y días, vigencia, tope. Con el ZIP del 20/11/2026: 83,5 % de las
      filas con promoción aplicables, 15,3 % desconocidas (la leyenda no dice qué promoción es), 1,2 % con horario,
      ninguna con banco o tarjeta.
- [x] Tabla nueva `promocion` en la base, con sus controles en `verificacion.py` y su diccionario en el LEEME.
- [x] En el modelo (los dos motores): precio efectivo, tope, binaria de "llevando n" y grupos enteros para n×m y la
      2.ª unidad; solo en la etapa 2 (las metas no cambian). Opción "Aplicar promociones" (paso 3, `?promos=`,
      `--sin-promos`); dos súper con las promociones de cada sucursal.
- [x] Ticket: renglón a precio de lista, línea de descuento, "Ahorro por promociones" y por qué no se aplicó cada una.
- [x] 193 tests de Python (32 nuevos) y un caso más de paridad con promociones inyectadas (2×1, 2.ª al 70 %, llevando
      3 y una bancaria; una sucursal y dos súper).
- [x] Presentación: etapa 5 en "Hecho".
- [x] Rearmar la base con el pipeline nuevo: hecho con la base del 21/11/2026 (996.184 promociones aplicables).
- [ ] Las desconocidas (Carrefour, Coto, Cooperativa Obrera): cruzar con los catálogos web; promociones por día de la
      semana.

## Etapa 6 (21/11/2026) · Contarlo en texto libre (LLM con Groq)

- [x] `canasta/llm.py`: esquema JSON del pedido derivado de `config.py`, prompt en español, cliente de Groq con
      `requests` (`openai/gpt-oss-120b`, JSON Schema estricto, errores en español) y `validar` estricta y sin red: lo
      desconocido o fuera de rango va a preguntas o avisos, nunca al pedido; lo que el motor no modela, a notas.
- [x] Backend: el servidor local de `python -m canasta` con la biblioteca estándar (`canasta/servidor.py`):
      `GET /api/estado` y `POST /api/interpretar`, solo desde esta máquina, sin CORS, con consentimiento, tope de 4.000
      caracteres y sin guardar el texto. `--llm-simulado` para desarrollo.
- [x] Página: "Contalo con tus palabras" en el paso 1 (solo con el servidor local), aviso de privacidad con casilla,
      formulario prellenado con la marca "del texto", preguntas, avisos y notas; nada se calcula hasta "Armar la canasta".
- [x] `GROQ_API_KEY` en `base_sepa/.env` (en `.env.example`, vacía); ninguna página la lleva (`exportar.py` lo controla).
- [x] 236 tests de Python (42 nuevos, todos con respuestas simuladas: inyección de instrucciones, JSON roto, 401, 429,
      5xx, sin clave, el endpoint en un hilo y un pedido que arma una canasta real).
- [x] Presentación: etapa 6 en "Hecho"; "Sigue" pasa a producción.
- [ ] **Probarlo con una clave real** (esquema estricto, calidad de la traducción, tiempos, cuota).
- [ ] Backend propio (FastAPI) en producción que envuelva `llm.py` y guarde las claves (Groq y rutas): con eso el texto
      libre llega a la página publicada.

## Base del 21/11/2026 y tolerancia de 15 días

- [x] `DIAS_TOLERANCIA_PRECIO = 15` en `sepa/config.py`: una cadena que no publicó el día entra con su último archivo
      si tiene a lo sumo 15 días; si es más viejo, no entra. Estado `anterior` y días en `lectura_comercios.csv`.
- [x] Fecha por sucursal: `fact_precio.fecha` y `dim_tienda.fecha_precios`; controles nuevos en `verificacion.py`
      (ninguna pasa la tolerancia ni es posterior al ZIP, cada precio con la fecha de su sucursal, cuántas usan precios
      de días anteriores). En la base nueva, 51 sucursales del 20/11 (Mariano Max, La Agrícola Regional, DEHEZA,
      Estación Lima).
- [x] Canasta (dos motores, con paridad): "Precios SEPA del ..." de cada sucursal en el ticket (y en el de dos súper),
      la marca en la tabla de sucursales y el aviso "precios de hace N días" si la elegida es de un día anterior.
- [x] Base del 21/11/2026 con `python -m sepa --diario`: 27.949 productos, 2.651 sucursales, 8.309.213 precios,
      1.161.802 promociones (996.184 aplicables), 71 controles. Arreglados en el pipeline: el User-Agent para Open Food
      Facts, las tablas web con los valores de la porción como cada 100 g y la fibra heredada que pasaba los 105 g.
- [x] Tests, paridad, demo y presentación recalibrados con los números nuevos.
- [ ] Rótulos web que cambiaron por otro factor (la mitad, el doble) y no se reconocen como "por porción": revisar.

## Otros pendientes

- [ ] Rutas para uso público: autoalojar OpenRouteService u OSRM.
- [ ] Costo con 15, 30, 45 y 60 min de una vez; objetivos secundarios con un tope de costo explícito.
- [ ] Autocompletado de direcciones y lista de compras para compartir.
- [ ] Monitoreo (Sentry) y backend (el deploy de la página es la etapa 3).

## Fuera de alcance

- Historial de precios.
- Promociones bancarias.
