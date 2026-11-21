# Roadmap: de POC a MVP y a producción

Estado al 21/11/2026. Las herramientas citadas están evaluadas, con enlaces y estrellas, en
[GITHUB_RESEARCH.md](GITHUB_RESEARCH.md). Los pendientes de datos y de nutrición que ya se conocían siguen en
[../base_sepa/PLAN_DE_TRABAJO.md](../base_sepa/PLAN_DE_TRABAJO.md); la lista para tildar, en
[../CHECKLIST.md](../CHECKLIST.md).

## Dónde estamos

### POC estabilizado (14/11/2026)

- Página estática autosuficiente (`datos/sepa/canasta.html`): motor en el navegador (HiGHS en WebAssembly), espejo
  del motor Python, con test de paridad.
- Búsqueda por tiempo caminando con rutas peatonales reales (OpenRouteService, matriz 1 × N), límite configurable
  (15 min por defecto; 15, 30, 45 o 60), "ver si conviene caminar más" que recalcula sucursales y canasta y muestra
  el ahorro, recorrido a pie en el mapa y respaldo con tiempos estimados, avisado como tal.
- Mapas arreglados (teselas, `localhost`, superposición en el celular, mapas que no se liberaban), ticket con minutos
  caminando, columnas alineadas, promociones como "no aplicadas", resumen nutricional e impresión.
- Límites del POC que siguen: la clave de rutas queda visible en la copia local de la página; la cuota gratuita de
  ORS (500 matrices por día) alcanza para pruebas, no para público; datos de un solo día; promociones sin aplicar;
  compra en una sola sucursal; lo más barato no siempre es lo habitual (harina, hígado); 10 a 18 s por cálculo.

### Etapa 1 del MVP (20/11/2026): lo que se pidió después de la presentación

- **Objetivo "Aumentar de peso"**, distinto de "Ganar masa muscular": +500 kcal/día sobre el gasto, proteína
  1,2 g/kg y aviso si el IMC ya es de sobrepeso. Perfil `bajo_peso` (mujer de 22 años, 46 kg, 165 cm, IMC 16,9):
  2.310 kcal/día.
- **El agua como restricción, con tres modos** (`AGUA_MODOS`, `?agua=` en la página y `--agua` en la consola):
  `canilla` (predeterminado; informativo: dice cuánta tomar de la canilla, no cuesta nada y los resultados de antes
  no cambian), `compra` (agua total de NASEM 2004, 2,7 L mujer y 3,7 L varón, contando la de los alimentos; se compra
  agua o soda envasada) y `bebidas` (los 8 vasos ≈ 2 L de las Guías Alimentarias, sin contar la de los alimentos).
  En el caso de la demo (oficinista en el Microcentro, 15 min, rutas reales) la semana pasa de $23.406 a $33.223 con
  el agua comprada y cumple las 38 metas.
- **Un caso que no llega a las 37 metas**, precargado: perfil `restricciones_extremas` (celíaca y alérgica a leche,
  huevo, soja, maní y frutos secos), solo listos para comer, centro de Córdoba, 15 min. Ninguna de las 10 sucursales
  llega; la mejor cubre 35 de 37 (calcio 76 %, lácteos 0 % porque no hay bebida vegetal apta), $205.550 la semana.
  La página lo avisa, muestra cuánto cubre cada meta y sugiere qué probar.
- Tests: 114 en Python y 2 de paridad entre el navegador y Python, con 8 casos (incluidos el agua y el caso que no
  llega a las 37).

### Etapa 2 del MVP (20/11/2026): compra en dos supermercados

El pedido del docente: si dos súper quedan cerca, quizás conviene comprar parte en cada uno (las naranjas más baratas
en B aunque la compra general convenga en A). Se calcula a pedido, después del resultado de siempre, que no cambia:
botón "¿Conviene sumar un segundo súper?" en la página, `&dos=1` en el enlace y `--dos-super` en la consola
(`resultado.dos_super` en Python, `MotorCanasta.dosSuper` en `motor.js`, también por el Worker).

- **Candidatas.** Se parte de la sucursal ganadora A y se le prueba sumar una vecina B: las que quedan a lo sumo
  `DOS_SUPER_MINUTOS_ENTRE` (10 min) caminando de A (estimado por distancia) y dentro del límite de caminata; hasta
  `DOS_SUPER_VECINAS` (4), primero la más cercana de cada otra cadena.
- **Formulación.** El modelo de siempre con binarias de visita, sobre la unión de las ofertas de A y de sus vecinas
  (cada fila es un producto p en una sucursal s(p); el mismo producto en dos sucursales son dos filas):
  - `y_s ∈ {0, 1}` "visito la sucursal s", con `y_A = 1` y `Σ_s y_s ≤ 2` (`DOS_SUPER_MAXIMO`).
  - Etapa 1 (MILP): minimizar el déficit ponderado `Σ peso_k · d_ik` con las restricciones de siempre y
    `c_ip ≤ tope_ip · y_s(p)` (no se come de donde no se compra; `tope_ip`, el de variedad de la subcategoría).
  - Etapa 2 (MILP): minimizar `Σ precio_p · x_p` con el déficit fijo (`d_ik ≤ d*_ik + holgura`), las de siempre y
    `x_p ≤ x_max_p · y_s(p)` (no se compra en una sucursal que no se visita).
- **Se resuelve por pares.** Como `y_A = 1` y se visitan a lo sumo dos, las soluciones son "A sola" o "A y una B_j";
  fijadas las y, cada par (A, B_j) es el modelo de siempre sobre la unión de las dos ofertas, sin binarias, y el óptimo
  con binarias es el mejor par en el mismo orden lexicográfico. Así se resuelve: es equivalente, cada par es un modelo
  que ya se sabe resolver (también con HiGHS en WebAssembly, sin otra formulación en `motor.js`) y es más robusto. El
  MILP con binarias, probado, no fue más rápido y dio compras más caras. Medido con el oficinista en el Microcentro
  (A y 4 vecinas): A sola, 0,9 s; un par, 1 a 3,5 s; los 4 pares, 4 a 10 s en paralelo; el MILP con las 5 binarias,
  4,6 a 5 s y $495 más caro que el mejor par, porque la etapa 2 se arma sobre las subcategorías que usa su relajación
  y con las y fraccionarias esa relajación elige peor. **Dominancia exacta:** en la unión se sacan los
  productos de B que A vende igual o más barato (mismos nutrientes y gramos: nunca son mejores); el óptimo no cambia
  y, entre dos sucursales de una misma cadena, el modelo era 5 veces más lento con esas filas repetidas.
- **Regla de decisión, lexicográfica y sin inventar el valor del minuto.** Conviene si el par cubre mejor las metas
  (aunque cueste más: nunca se cambia nutrición por plata) o, con las mismas metas, si ahorra al menos el 3 % del
  costo de A y al menos $1.000 (`DOS_SUPER_AHORRO_MINIMO_PCT` y `_PESOS`; el 3 % queda bien por encima del 1 % de
  brecha del solver, que es ruido y no un precio mejor). Si no, "no conviene" (con lo que se ahorraría). Se muestra
  "ahorrás $X (Y %) caminando Z min más (estimado)" y la persona decide.
- **Recorrido.** Circuito casa → A → B → casa: los tramos desde y hacia casa salen de la matriz de rutas; el tramo
  A → B es estimado por distancia y se dice estimado. Con clave de OpenRouteService se pide la ruta real A → B → casa
  solo para dibujarla y decir cuánto es por la calle; las cuentas usan el estimado.
- **Página.** La decisión, una tabla "Un súper" vs "Dos súper" (costo, metas, caminata), qué se compra en cada uno,
  el recorrido con los tramos estimados marcados, el ticket dividido por sucursal con subtotales (selector "Un súper"
  / "Dos súper", también al imprimir) y el mapa con el segundo súper.
- **Resultados** (una semana). Oficinista en el Microcentro, 15 min: Coto Mitre $23.406 → con DIA 439
  Monserrat, $21.947: ahorra ~$1.460 (6,2 %) con ~5 min más de caminata (entre $1.460 y $1.549 según la corrida, por
  la brecha del 1 % del solver). Celíaca en el Microcentro, ~11 %; hogar de tres en Caballito, ~7 %. El caso
  `restricciones_extremas` en Córdoba a 15 min: no conviene (las vecinas son de la misma cadena y tampoco venden
  lácteos aptos); a 30 min, conviene porque cubre más metas.
- Tests: 127 en Python y 3 opcionales de paridad entre el navegador y Python, ahora también para dos súper
  (Microcentro, conviene por ahorro; Córdoba a 15 min, no conviene; Córdoba a 30 min, conviene por metas).

### Etapa 3 del MVP (21/11/2026): ETL diario y CI

Hecha en el repositorio; falta que el dueño la active (pushear, `main`, Pages con "GitHub Actions" y una primera
corrida a mano: [DESPLIEGUE.md](DESPLIEGUE.md)). No se probó todavía en GitHub.

- **ETL diario** (`.github/workflows/tpf-diario.yml`, en la raíz del repo): a las 07:30 y a las 18:00 de Argentina
  (SEPA sube el ZIP de cada día a la tarde) pregunta la fecha del último ZIP (`python -m sepa --ultima-fecha`) y, si
  el sitio no la tiene, rearma la base (`python -m sepa --diario`), exporta la página (`python -m canasta --exportar`,
  sin clave) y la publica en **GitHub Pages** (`https://nazarenofolica.github.io/Optimizacion_TPS/`). Sin commitear
  los datos del día: no hay historial y el repo no crece.
- **Modo diario** (`--diario`): `--descargar` sin intervención; con las cachés hace lo mismo y, si faltan los catálogos
  web (un runner nuevo), los recorre en lugar de cortarse. Open Food Facts, los catálogos web, Georef/USIG y USDA
  viajan entre corridas en la caché de Actions, con una huella del contenido en la clave.
- **Controles:** si falla la verificación (o una fuente), no se publica y queda la página del último día bueno; las
  tablas que no pasaron quedan como artefacto, GitHub manda un mail y se abre un issue (uno solo, que se cierra cuando
  vuelve a andar). Si SEPA no publicó un día nuevo, la corrida termina bien, sin cambios.
- **CI** (`.github/workflows/tpf-tests.yml`): la suite de Python en cada push y pull request que toque `TPF/`; la
  paridad con Chrome headless, a mano.
- Tests: 142 en Python (10 nuevos del modo diario) y 3 opcionales de paridad.

### Etapa 4 del MVP (21/11/2026): restricciones nuevas y condiciones médicas

Sin recargar la base entera (en esta máquina no están las cachés del pipeline): lo nuevo sale de columnas que
`dim_producto` ya tiene (nombre, marca, descripción, ingredientes, alimento genérico, NOVA, vegetariano, alcohol).

- **Columnas nuevas** (`sepa/producto/religion.py`, paso 8 del pipeline y aplicable al parquet existente: si no las
  trae, `canasta/oferta.py` las calcula al cargar con la misma función, ~4 s): `contiene_cerdo`, `contiene_carne`,
  `contiene_gelatina`, `contiene_alcohol`, `contiene_vino`, `contiene_carmin` (si / no / desconocido) y
  `rotulo_kosher`, `rotulo_halal`. Reglas en el orden de `composicion.py`: el alimento genérico, el nombre y la lista de
  ingredientes dicen "si" (sin las trazas ni los aromatizantes sintéticos: "aromatizante idéntico al natural
  panceta" no es cerdo; "licor de cacao" no es alcohol; el vinagre tampoco); "no" si hay lista y no lo trae, si no es
  procesado o si ya es vegetariano; si no, "desconocido", que no es apto. Para el alcohol, el vino y el carmín, un
  procesado sin lista solo es dudoso si su alimento los trae seguido sin avisarlo en el nombre (≥ 3 % de los que
  tienen lista, medido en cada corrida: budines, alfajores, yogures, helados, mermeladas light...).
- **Restricciones**, al final de `RESTRICCIONES` (bits 15 a 17 de la aptitud; el binario es un uint32 por producto y
  `exportar.py` corta si pasan de 32):

  | Restricción | Criterio | Excluye (de 19.336) |
  |---|---|---:|
  | Sin cerdo | sin carne, grasa, fiambres ni embutidos de cerdo; sin cerdo, panceta, tocino o jamón en los ingredientes; sin gelatina de origen no declarado | 6.539 (1.548 seguros y ~5.000 procesados sin lista que podrían tenerlo) |
  | Halal | sin cerdo ni alcohol; carnes rojas y aves solo rotuladas halal (no hay ninguna); gelatina solo de origen no porcino declarado; pescado y mariscos sí (la escuela hanafí los excluye: se suma "Alergia a mariscos") | 7.856 |
  | Kosher | sin cerdo, carne ni aves no rotuladas (no hay); sin mariscos, surimi ni pescados sin escamas (cazón, surubí, pez espada); sin gelatina, carmín ni derivados de la uva sin certificar (vino, mosto, jugo de uva) | 8.497 |

  Fuentes: Corán 2:173, 5:3 y 5:90; Levítico 11 y Deuteronomio 14; los criterios de las certificadoras (Centro
  Islámico de la República Argentina, OU). **Rótulos en la base:** "kosher" o "parve" en 2 productos de 28.030 (un
  vino y una milanesa de soja, ninguno de la canasta; una mermelada dice "KOSHBR", un error de lectura del rótulo que
  no se cuenta), "halal" en ninguno (las dos coincidencias eran "chala", una cerveza). **Límites:** sin
  certificaciones en la base, halal y kosher son lo verificable por ingredientes; la faena, el cuajo de los quesos, la
  leche y el pan bajo supervisión no figuran; la mezcla carne-leche por comida no se modela (la canasta es por día; hoy
  no hay carne apta, así que no se presenta).
- **Condiciones médicas** (`referencia/condiciones.csv`: condición → meta → cambio y valor → fuente → requiere
  supervisión → aviso), como restricciones al final (bits 18 a 23) que no filtran productos, igual que la hipertensión
  y la diabetes cambian el sodio y los azúcares: así llegan solas a la persona, los perfiles, `?perfiles=`, la página y
  el pedido de la etapa 6. Cada cambio aparece en "Cómo calculamos lo que necesita" (fórmula, resultado y fuente) y en
  los avisos; ningún mínimo pasa un máximo tolerable (se apunta al máximo y se avisa, como el hierro vegetariano).

  | Condición | Qué cambia | Fuente | Supervisión |
  |---|---|---|---|
  | Anemia por falta de hierro | hierro × 1,8 (sin pasar el UL de 45 mg; no se suma al vegetariano), vitamina C prioritaria | NASEM 2001; FAO/OMS 2004; OMS 2016 (el hierro medicinal lo indica el médico) | sí |
  | Osteoporosis o riesgo de fracturas | calcio ≥ 1.200 mg; vitamina D ≥ 20 µg y prioritaria (sigue informativa) | NASEM 2011; BHOF 2022 | no |
  | Colesterol alto | saturadas < 7 % de la energía; colesterol ≤ 200 mg (meta nueva) | NCEP ATP III (NHLBI 2002) | no |
  | Déficit de vitamina B12 | B12 prioritaria (su déficit pesa el doble) | NASEM 1998 | sí |
  | Déficit de vitamina D | vitamina D prioritaria (informativa: la comida no alcanza) | NASEM 2011 | sí |
  | Enfermedad renal crónica | nada: solo avisa (proteína, potasio, fósforo y sodio dependen de la etapa) | KDOQI 2020 | sí |

  Nunca dosis ni suplementos: las que requieren supervisión lo dicen en el formulario y en el resultado.
- **Página:** el paso 1 agrupa "Dieta y religión", "Alergias" y "Salud"; las condiciones con supervisión llevan la marca
  en el chip y, al elegirlas, su aviso; cada grupo tiene "Qué exige cada una" desplegable. Perfiles ocultos de prueba:
  `kosher`, `halal` (con colesterol alto) y `anemia` (`?perfiles=kosher,halal,anemia`).
- **Canastas reales** (oficinista, una semana, 15 min caminando, tiempos estimados): Microcentro, sin restricciones
  $23.406; sin cerdo $23.406; halal y kosher $24.491; anemia $27.770; colesterol alto $23.866 (38 metas); osteoporosis
  y déficit de B12 $25.274. Córdoba: sin cerdo, halal y kosher $37.494; anemia $41.589; colesterol alto $36.905;
  osteoporosis y B12 $38.070. Todas cubren todas sus metas.
- Tests: 161 en Python (18 nuevos: religión con productos sintéticos y reales, aptos con los datos, canastas reales en
  el Microcentro y Córdoba, cada condición cambia lo que dice la tabla, ningún mínimo pasa un máximo) y un caso más de
  paridad (kosher, halal con colesterol alto y anemia en el Microcentro), que ahora compara también avisos y criterios.

### Etapa 5 del MVP (21/11/2026): promociones con condiciones

Las promociones que no piden banco, tarjeta, billetera ni el programa de la cadena se aplican a la compra, con sus
condiciones (2×1, la 2.ª al 70 %, llevando 3). **Se aplican desde la próxima actualización de la base**: la de hoy
(23/10/2026) no guarda las leyendas, así que con ella nada cambia (los costos de los perfiles dan lo mismo que antes).

- **Fuente: SEPA mismo.** El ZIP diario trae, por producto y sucursal, `productos_precio_unitario_promo1` /
  `productos_leyenda_promo1` y `..._promo2`: el precio por unidad con la promoción (en un 2×1, la mitad del de lista)
  y una leyenda libre. El pipeline leía solo el precio de la promo 1; ahora guarda las dos con su leyenda
  (`sepa/fuentes/sepa.py`). Con el ZIP del 20/11/2026 (14,6 millones de precios, 1.764.944 con promoción, 3.278
  leyendas distintas) se calibró el clasificador.
- **Clasificador** (`sepa/precio/promociones.py`): de cada leyenda, `tipo` (`porcentaje`, `nxm`, `segunda_unidad`,
  `precio_fijo`, `llevando_x` o `desconocida`), sus parámetros (n, m, porcentaje, precio, tope de unidades),
  `condicion_pago` (tarjeta, banco, billetera, fidelidad, efectivo), otra condición (un horario, algunos días,
  jubilados, online), la vigencia y `aplicable` con su `motivo`. Las de DIA empiezan con el descuento promedio
  ("35% de descuento.") y la promoción viene después ("2DO AL 70% YOG POTE"); la de La Anónima "Llevando 2 unidades"
  no dice el precio y se usa el que publica SEPA. Lo que no dice qué promoción es (Carrefour: "Promo A valida desde
  ..."; Coto: "DEL 16/11 AL 22/11"; la mayoría de la Cooperativa Obrera: solo la vigencia) es `desconocida` y no se
  aplica. Si el precio que publica SEPA no coincide con el de la leyenda (más de 3 %), tampoco.

  | Clasificación (ZIP del 20/11/2026, todas las filas con promoción) | Filas | % filas | Leyendas | % leyendas |
  |---|---:|---:|---:|---:|
  | Aplicable | 1.473.850 | 83,5 % | 1.556 | 47,6 % |
  | Desconocida (no dice qué promoción es) | 269.705 | 15,3 % | 1.709 | 52,3 % |
  | No aplicable: otra condición (DIA, "25% PANIF X TARDE") | 21.350 | 1,2 % | 1 | 0,0 % |
  | No aplicable: el tope es menor que lo que pide | 9 | 0,0 % | 2 | 0,1 % |
  | No aplicable: medio de pago | 0 | 0 % | 0 | 0 % |

  Por tipo, las aplicables: porcentaje 1.229.504, segunda unidad 163.659, n×m 42.308, llevando n 37.410, precio fijo
  969. Por cadena: DIA 1.384.125 aplicables (de 1.408.199), La Anónima 53.582 (de 53.584), Cooperativa Obrera 36.143
  (de 110.658); Carrefour (182.776), Coto (8.096) y Toledo (1.601), todas desconocidas. Ese día ninguna leyenda
  pide un banco o una tarjeta: las bancarias (que las cadenas anuncian aparte) no llegan a SEPA con su leyenda, o
  quedan dentro de las desconocidas. Muestra completa de leyendas con su frecuencia por cadena: se arma con
  `sepa/fuentes/sepa.leer_zip` y `promociones.cobertura`.
- **Tabla nueva `promocion`** (y no columnas en `fact_precio`): hasta dos promociones por precio (orden 1 y 2), así que
  no tiene el grano de `fact_precio`; tiene ~20 % de sus filas; y `fact_precio`, que lee la canasta (8 millones de
  filas), no cambia. Columnas: leyenda, precio de lista y publicado, tipo y parámetros, condiciones, vigencia,
  `aplicable`, `motivo`, `resumen` ("2×1", "2.ª al 70 %") y cómo entra al modelo (`forma` precio o grupo, `unidades`,
  `precio_unitario`). Controles en `sepa/verificacion.py` (es de un precio publicado, tipo conocido, una aplicable
  tiene precio menor al de lista y forma, ninguna con condición de pago se aplica) y documentación en `salida.py` y
  el LEEME. Si la base no la trae (la de hoy), la canasta funciona igual que antes, sin promociones.
- **En el modelo** (`canasta/modelo.py`, espejo en `motor.js`), solo en los productos con una promoción aplicable y
  solo en la etapa 2 (la 1, las metas, no cambia: una promoción baja el costo, nunca cambia nutrición por plata). Con
  precio de lista P, precio con la promoción Q < P, n unidades y tope T:
  - porcentaje o precio fijo sin tope: el costo de x es Q·x (sin variables nuevas);
  - con tope: u ≤ min(T, x_max) unidades con la promoción, u ≤ x, costo P·x − (P − Q)·u;
  - llevando n, c/u $Q: además una binaria z con n·z ≤ u ≤ min(T, x_max)·z;
  - n×m, 2.ª al q %, n por $P (grupos de n): k grupos enteros, n·k ≤ x, costo P·x − n·(P − Q)·k (cada grupo cuesta
    n·Q: m·P en un n×m, (2 − q)·P en la 2.ª al q %). Es x = n·k + r con r ≥ 0 a precio de lista (la cota r ≤ n − 1
    no hace falta: el óptimo la cumple).
  x_max sube a n si era menor (se puede llevar el grupo aunque sobre). En la relajación de la etapa 2 cada promoción
  vale Q, así que las subcategorías que pasan al modelo entero ya las tienen en cuenta; la poda de cada sucursal usa
  el precio cada 100 g con la promoción. El costo informado es el de la caja para las unidades compradas (arma todos
  los grupos que puede), que nunca es mayor que el del solver. Si un precio tiene dos promociones, se aplica la de
  menor precio por unidad (no se sabe si se suman); a granel, solo un porcentaje o un precio por kilo.
- **Ticket** (Python y página): el renglón a precio de lista y, debajo, la línea del descuento como en la caja
  ("2.ª al 70 % pagás $1.233,70 −664,30"); antes del total, "Subtotal a precio de lista" y "Ahorro por promociones";
  las que no se aplican dicen por qué ("requiere un banco", "solo en un horario", "la compra no llega a las unidades
  que pide"). Al pie, "Con las promociones que no piden banco ni tarjeta" o "Precios de lista", según el caso.
- **Opción "Aplicar promociones"** en el paso 3 (predeterminada si la base trae alguna aplicable; con la de hoy queda
  apagada y lo dice), `?promos=0|1` en el enlace, `--sin-promos` en la consola. Desactivada, todo es exactamente como
  antes. Dos súper: cada sucursal del par aplica las suyas (en la unión, una fila de B solo se saca si su promoción
  tampoco es mejor que la de A).
- **Con promociones de prueba** (la base no las trae: `oferta.promociones_de_prueba`), oficinista en el Microcentro,
  Coto Mitre: la 2.ª al 70 % en el puré de tomate baja la semana de $23.406,20 a $22.741,90 (−$664,30), con las
  mismas 37 metas; el 2×1 en el aceite empata (llevar 2 cuesta lo mismo que 1) y el "llevando 3 con 20 %" en los
  porotos no conviene: los dos dicen que no se aplicaron y por qué. Los dos motores dan $22.741,90.
- Tests: 193 en Python (32 nuevos: el clasificador con leyendas reales, la tabla y sus controles, la lectura de la
  promo 2, el modelo con cada tipo en ofertas sintéticas, que una promoción nunca empeora las metas, la caja, el
  ticket, dos súper y, con los datos, que la base sin promociones da lo mismo) y un caso más de paridad (2×1, 2.ª al
  70 %, llevando 3 y una bancaria inyectados, con una sucursal y con dos súper).

### Etapa 6 del MVP (21/11/2026): contarlo en texto libre (LLM con Groq)

"Contalo con tus palabras", en el paso 1 de la página local: la persona escribe quiénes comen y qué no pueden comer, o
pega una indicación médica, y un LLM de Groq lo traduce al **pedido estructurado** que ya consume el motor. El
formulario queda prellenado, con lo que falta como preguntas, y nada se calcula hasta "Armar la canasta". El LLM no
elige productos, no inventa precios ni nutrientes y no reemplaza al optimizador. **Todo se probó con respuestas
simuladas: falta probarlo con una clave real** (ver abajo).

- **Módulo `canasta/llm.py`** (lógica pura y cliente, sin servidor):
  - `esquema()`: el JSON Schema de la salida, **derivado de `config.py`** (personas hasta `PERSONAS_MAXIMAS`, con sexo,
    edad, peso, altura, actividad de `ACTIVIDAD`, objetivo de `OBJETIVO`, etapa de `ETAPAS` (nuevo en config), trimestre,
    restricciones y condiciones de `RESTRICCIONES` y `no_reconocidas`; `dias` de `DIAS_PERIODO`, `agua` de `AGUA_MODOS`,
    `caminata_minutos` de `CAMINATA_OPCIONES`, `listos` y `promos`; más `preguntas` y `notas`). Todo obligatorio y
    `null` si el texto no lo dice, como pide el modo estricto.
  - `prompt_sistema()`: en español, con los valores válidos tomados de config; su rol es traducir; no inventar ni
    estimar (lo que no se dice va en `null`), no diagnosticar ni recomendar, "anemia" sin decir que es por falta de
    hierro se pregunta, siglas habituales (DBT, HTA, LDL, ERC), lo que no está en la lista va a `no_reconocidas` y lo
    que la página no modela (1.200 kcal indicadas, fraccionar comidas, picantes) a `notas`. El texto de la persona va
    en el mensaje del usuario entre `<texto>` y `</texto>` (se le quitan esos delimitadores) y el prompt dice que las
    instrucciones que traiga son datos, no órdenes.
  - Cliente con `requests` (sin SDK): `POST https://api.groq.com/openai/v1/chat/completions`, modelo `GROQ_MODELO =
    "openai/gpt-oss-120b"` con `response_format` JSON Schema en **modo estricto** (`GROQ_MODELOS_ESTRICTOS`; con otro
    modelo, `json_object` y el esquema en el prompt), `temperature` 0,1 y 30 s de espera. Errores con mensaje en
    español: sin clave, 401/403 clave inválida, 429 cuota, 400 formato, 5xx, sin conexión, demora y JSON ilegible.
  - `validar(salida) -> (pedido, preguntas, avisos, notas)`: estricto, determinista, sin red. La salida del LLM es un
    dato no confiable: lo desconocido o fuera de rango **nunca entra al pedido**. Los rangos se revisan con
    `requerimientos.persona_desde(...).validar()` (no se escriben dos veces); embarazo o lactancia fuera de 14 a 50
    años o en un varón, objetivo de peso en un menor, una restricción inventada, 150 años, `dias: 10`, un texto donde
    va un número: van a `preguntas` (lo que hay que completar o aclarar) o a `avisos` (lo que se descartó, o "la
    canasta no sabe evitar «frutilla»: revisá el ticket"). Las preguntas y notas se limpian (sin enlaces ni marcas,
    hasta 10 de 300 caracteres). `personas_del_pedido` arma las `Persona` con los valores de siempre del formulario.
  - `canasta/llm_simulado.py`: tres salidas de ejemplo (el hogar de la hija celíaca, el vegano que entrena y una
    prescripción ficticia) para los tests y el modo de desarrollo.
- **Backend: el servidor local de `python -m canasta`, con la biblioteca estándar** (`canasta/servidor.py`), y no
  FastAPI. Para esta etapa alcanza: la página ya se servía con `http.server`, no suma dependencias ni un proceso más, y
  la lógica quedó en `llm.py`, separada, para que un FastAPI la envuelva en producción sin cambiarla.
  - `GET /api/estado` → `{llm, simulado, modelo, texto_maximo}` (`llm` es true si hay `GROQ_API_KEY`).
  - `POST /api/interpretar` `{texto, consentimiento: true}` → `{pedido, preguntas, avisos, notas, simulado}` o
    `{error}` (503 sin clave, 429 cuota, 502 otros errores de Groq, 400 texto vacío o de más de 4.000 caracteres o sin
    consentimiento, 413 cuerpo de más de 64 KB, 415 si no es JSON).
  - Solo esta máquina: escucha en 127.0.0.1, rechaza otra dirección y otro `Host` (también para los archivos, porque
    `canasta_local.html` lleva la clave de rutas), un `Origin` o `Sec-Fetch-Site` de otro sitio; sin CORS. El texto no
    se guarda ni va al log (los tests lo comprueban).
  - `python -m canasta --llm-simulado`, **solo para desarrollo**: responde con las salidas de ejemplo sin llamar a
    Groq, y la página lo dice ("Modo de prueba"). Nunca se activa solo.
- **Página** (paso 1): bloque plegado "Contalo con tus palabras" (solo si `/api/estado` responde, es decir, servida por
  `python -m canasta` en localhost; en la publicada no aparece y no se consulta nada). Texto de hasta 4.000 caracteres
  con contador, aviso de privacidad ("Lo que escribas se envía a Groq... Nosotros no lo guardamos. Si pegás una
  indicación médica, sacale el nombre, el DNI y los datos de contacto"), casilla de confirmación (sin ella el botón no
  se habilita y el servidor tampoco acepta el pedido) y "Interpretar el texto". Al volver: el hogar se reemplaza por
  las personas del texto (lo obligatorio que no dijo, vacío; sexo y trimestre vacíos ahora se piden en el formulario),
  días, agua, listos, promociones y caminata si los dijo; "Lo que entendimos", "Para completar o aclarar", "Atención" y
  "Lo que la canasta no aplica"; los campos que vinieron del texto llevan la marca "del texto" (se va si se cambian).
  Sin clave, una línea dice cómo activarlo; con un error (cuota, red), un mensaje amable y el formulario intacto.
  Probada en Chrome headless a 1.280 y 375 px, en modo oscuro y con "reducir movimiento".
- **Probado con mocks** (42 tests nuevos, 236 en total): el esquema sale de config y cumple el modo estricto; el
  prompt lista los valores y el texto no puede cerrar su delimitador; los tres textos de ejemplo; valores fuera de
  rango, tipos equivocados, restricciones inventadas, instrucciones inyectadas (también de punta a punta: el texto
  viaja como dato y lo que vuelve se valida), JSON roto, 401, 403, 429, 400, 500, 503, sin conexión, demora, sin
  clave (no se llama); el endpoint en un hilo (consentimiento, tamaños, `Origin`, `Host`, errores, nada del texto en
  la consola) y un pedido validado que arma una canasta real (la hija celíaca de 8 años y la madre de 40 para dos
  semanas en el Microcentro). En el navegador, con el modo simulado: interpretar, completar los dos pesos y armar
  (COTO, $80.313 para dos semanas).
- **Falta probar con una clave real**: que `openai/gpt-oss-120b` acepte el esquema en modo estricto tal como está
  (enums con `null`), la calidad de la traducción con textos reales (siglas, prescripciones largas, hogares grandes),
  los tiempos de respuesta y la cuota gratuita. Si el modelo rechaza el esquema (400), cambiar `GROQ_MODELO` o sacarlo
  de `GROQ_MODELOS_ESTRICTOS` (pasa a `json_object` con el esquema en el prompt; la validación es la misma).

## Lógica de negocio: cómo se optimiza

El objetivo es **la compra más barata que cumple lo que necesita cada persona**, y la arquitectura tiene que separar
qué es obligatorio de qué es preferencia.

**Restricciones duras (definen el conjunto factible):** energía de cada persona (±5 %), restricciones alimentarias,
alergias y trazas, disponibilidad en la sucursal, **tiempo caminando ≤ límite elegido**, el agua si el hogar la
compra y, cuando exista, presupuesto máximo.

**Objetivo principal:** minimizar el costo total.

**Metas nutricionales:** ya se resuelven de forma lexicográfica en dos etapas: (1) minimizar el déficit ponderado de
nutrientes y reglas de las Guías; (2) con ese déficit fijo (holgura 1e-4), minimizar el costo. Es *goal programming*
preventivo y conviene mantenerlo: nunca se cambia nutrición por plata.

**Objetivos secundarios (tiempo, variedad, cadena preferida, promociones).** No se suman con pesos arbitrarios. Se
agregan como pasos lexicográficos con **tolerancia de costo** explícita:

1. Pasos 1 y 2 del modelo, como hoy → costo mínimo C*.
2. Paso 3 (opcional, lo elige el usuario): optimizar el criterio secundario sujeto a `costo ≤ (1 + τ) · C*`, con τ
   visible ("hasta 3 % más caro"). Por ejemplo, máxima variedad (mínimo de porciones repetidas) o mínima caminata.

Con eso cada preferencia tiene un precio que se puede mostrar ("más variedad te cuesta $X").

**Distancia.** Es una restricción del espacio de búsqueda, no un objetivo: primero se filtran las sucursales
alcanzables y después se optimiza. "Caminar más" amplía el conjunto factible y se reoptimiza; el resultado se
presenta como un **frente costo vs. minutos** (15, 30, 45 y 60 min con su mejor costo), que es la forma honesta de
mostrar el intercambio sin inventar cuánto vale un minuto para cada persona. Se puede calcular el frente completo
de una vez (una matriz con el radio de 60 min y un modelo por sucursal, cacheado) y mostrarlo como una lista
escalonada: "15 min: $23.406 · 30 min: $21.900 (−6 %)".

**Comprar en varias sucursales.** Hecho para dos (etapa 2, arriba): binarias de visita `y_s` con `y_A = 1` y
`Σ y_s ≤ 2`, que se resuelven enumerando los pares (A, B), cada uno con el modelo de siempre sobre la unión de las
ofertas. No se le pone un costo en pesos a la visita: con el mismo esquema lexicográfico, primero las metas y después
el costo, se propone el segundo súper si cubre mejor las metas o si ahorra al menos 3 % y $1.000, y se muestra el
ahorro junto a los minutos de más para que la persona decida. Con más de dos visitas los pares dejan de alcanzar:
haría falta el MILP con binarias (o enumerar tríos acotados) y, para el orden de las visitas, un problema de ruteo.

## El camino al MVP: etapas 3 a 6 (todas hechas)

Cada etapa se planifica y se cierra por separado, con sus tests y la paridad entre los dos motores.

### Etapa 3 · ETL diario y CI: hecha (21/11/2026, falta activarla)

Ver "Etapa 3 del MVP" arriba y [DESPLIEGUE.md](DESPLIEGUE.md). Lo que queda de lo que se había planeado:

- Detección de cambios contra el día anterior (precios que saltan más de x3, sucursales que desaparecen): el pipeline
  no la tiene todavía; los comercios con archivo viejo ya se excluyen.
- Equivalencias entre cadenas: ya existe por EAN y "gemelos"; documentar y testear el emparejamiento.
- Entorno reproducible con `uv` (hoy hay dos `requirements.txt` con rangos de versiones).
- Paridad en cada push (hoy, a mano), tests de la página con Playwright y del motor JavaScript sin navegador (Node).

### Etapa 4 · Restricciones nuevas y condiciones médicas: hecha (21/11/2026)

Ver "Etapa 4 del MVP" arriba. Lo que se había planeado y queda: pescetariano y exclusión de ingredientes puntuales;
certificaciones kosher y halal de verdad (etiquetas de Open Food Facts, que el pipeline todavía no guarda, o listas de
las certificadoras) para ofrecer carnes y lácteos certificados; más condiciones solo con fuente.

Lo que se había planeado (una tabla de ajustes por condición con fuente y "requiere supervisión"; solo condiciones
con fuente; ningún mínimo por encima de un máximo tolerable; nunca diagnóstico ni suplementación) quedó así. Kosher y
halal se ofrecen con la cobertura medida (0 rotulados en la canasta), por eso sin carnes.

### Etapa 5 · Promociones con condiciones: hecha (21/11/2026)

Ver "Etapa 5 del MVP" arriba. La fuente resultó ser SEPA mismo (las leyendas de las promociones 1 y 2), no los
catálogos web. Lo que queda:

- **Que la base las traiga**: la próxima corrida del pipeline (con el ZIP ya bajado en `base_sepa/datos/entrada/`)
  arma la tabla `promocion`; desde ahí la página y la consola las aplican solas.
- Las desconocidas (15 % de las filas: Carrefour, Coto, la mayoría de la Cooperativa Obrera): sus catálogos web dicen
  qué promoción es cada una; cruzarlos por EAN y sucursal.
- Los días de la semana ("los miércoles") hoy no se aplican; con el día de la compra, sí se podrían.
- Si dos promociones del mismo precio se suman o no: hoy se aplica la mejor.

### Etapa 6 · LLM con Groq: hecha (21/11/2026, probada con respuestas simuladas)

Ver "Etapa 6 del MVP" arriba. Del diseño planeado se hizo todo salvo el backend en FastAPI: el endpoint vive en el
servidor local (`canasta/servidor.py`, biblioteca estándar) y la lógica en `canasta/llm.py`, lista para envolverla. Lo
que queda:

- **Probarlo con una clave real de Groq** (esquema estricto, calidad, tiempos, cuota) y ajustar el prompt con lo que
  salga mal.
- **Producción**: un backend propio (FastAPI) que use `llm.py`, guarde las claves de Groq y de rutas fuera de la
  página y cachee las matrices de rutas; con eso el bloque aparece también en la página publicada. Límite de pedidos
  por persona (la cuota gratuita es compartida).
- Opcional: explicar el resultado en lenguaje simple a partir del JSON del motor (con sus números, sin recalcular).

## Otros pendientes (sin etapa asignada)

- **Frente costo vs. minutos** y objetivos secundarios con tolerancia de costo (ver "Lógica de negocio").
- **Más de dos sucursales:** el MILP con binarias de visita (o tríos acotados) y el orden del recorrido como problema
  de ruteo (OR-Tools); antes, medir el tiempo en el navegador.
- **Rutas para público:** autoalojar OpenRouteService u OSRM con el extracto de Argentina de Geofabrik (un VPS de
  4 a 8 GB alcanza para el perfil peatonal), o pasar a Mapbox/Google detrás del backend. Teselas de un proveedor con
  cuota (las de OpenStreetMap no son para tráfico alto).
- **Experiencia:** autocompletado de direcciones (Photon sobre OSM; Georef no autocompleta), lista de compras para
  compartir, plan de comidas día por día (idea tomada de Mealbird).
- **Velocidad:** 10 a 18 s por cálculo; ideas en [PLAN_DE_TRABAJO.md](../base_sepa/PLAN_DE_TRABAJO.md).

## Producción

| Pieza | Propuesta | Costo orientativo |
|---|---|---|
| Página | Estática en GitHub Pages (hecho, falta activarlo) o Cloudflare Pages | Gratis en repo público |
| ETL diario | GitHub Actions (hecho: `tpf-diario.yml`; Dagster/Prefect si crecen las fuentes) | Gratis en repo público; si no, minutos de Actions |
| Backend + rutas | FastAPI (que envuelva `canasta/llm.py`: hoy el texto libre corre en el servidor local) + ORS/OSRM autoalojado en un VPS (Coolify para desplegar) | USD 10 a 40 por mes |
| Datos | Parquet del último día; Postgres (Supabase) recién cuando haya cuentas | Gratis al inicio |
| Monitoreo | Sentry (backend, job y página) + alerta si el job no publicó | Plan gratis al inicio |
| Entornos | `main` → producción, `develop` → previsualización (Pages las da por rama) | — |

**Cuándo dejar la página 100 % estática:** cuando haya que proteger claves (rutas, Groq), cachear rutas entre
usuarios o tener cuentas de usuario. El motor puede seguir en el navegador (no cuesta servidor) y el backend
ocuparse solo de lo que necesita secreto o estado.

## Fuera de alcance

- **Historial de precios.** Cada corrida del ETL reemplaza el día anterior: son ~8 millones de precios por día y
  nada del producto los usa. Si más adelante hiciera falta mostrar tendencias, alcanzaría con un resumen por
  producto, cadena y día (mediana), no las filas completas.
- **Promociones bancarias** (reintegros y descuentos por banco, billetera o tarjeta de la cadena): dependen de los
  medios de pago de cada persona, cambian por día y por cadena, y SEPA no las publica con sus condiciones. Se
  siguen mostrando como "no aplicadas".
