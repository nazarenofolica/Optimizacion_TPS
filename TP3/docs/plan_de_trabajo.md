# TP3 Optimización — "Diseño de Supermercados" (CarroMenos)
## Plan de trabajo (esquema) — modelo completo

> **Qué es este archivo.** Es el **plan / esquema** del trabajo: qué pide la consigna, qué hay que
> modelar, con qué datos, qué supuestos se adoptan y cómo se van a testear. **No es la bitácora de
> desarrollo.** Lo que efectivamente se haga al codificar (y lo que cambie respecto de este plan)
> va en [`procedimiento.md`](procedimiento.md). El trabajo dividido en tareas está en
> [`tareas.md`](tareas.md) — ver §16.
>
> **Estado:** modelo planteado, **todavía no resuelto**. Los números de §4 son cuentas directas
> sobre los datos de la consigna. Los valores marcados **(Explorar)** son datos que la consigna no
> da: el plan propone un valor por defecto que hay que confirmar con una fuente (tareas F0).
>
> **Regla (la misma del TP1 y el TP2):** desde acá, este documento **no se reescribe** para que
> coincida con lo que termine pasando. Los desvíos se anotan en `procedimiento.md` §2: el contraste
> entre lo planeado y lo que pasó es material para el informe (criterio "Analizar").

---

## 0. Primero, tres aclaraciones sobre la consigna

**(1) Como en el TP1, la consigna tiene DOS listas a)–e) que no son lo mismo.**

| Lista | Dónde está | Qué es |
|---|---|---|
| **"Informe esperable por la cátedra"** a)–d) | página 1 | La **estructura del informe**: modelo (supuestos, variables, funcional, parámetros, restricciones, resolución), sensibilidad, gráfico de flujos, librerías |
| **Preguntas** a)–e) | páginas 2–3 | Lo que hay que **resolver** sobre el caso CarroMenos |

Hay que cumplir las dos: cada pregunta se resuelve y el informe se ordena con la primera lista.
Ojo con la letra repetida: "c) Representación gráfica" (informe) ≠ "c) valor mínimo de Goyito"
(pregunta).

**(2) "Modelo de programación lineal" no quiere decir PL continua.** Abrir o no un centro es una
decisión sí/no, con costo fijo de apertura, y hay una regla lógica (gerente si se abren tres
centros). Es un **problema de localización de instalaciones** (*facility location*, ver el primer
link útil de la consigna): **programación lineal entera mixta** — binarias para los centros,
continuas para los flujos de pallets. Es la continuación natural del TP2.

**(3) Pero la cátedra pide análisis de sensibilidad (informe b).** Con binarias no hay precios
sombra directos (Clase 06). La salida adoptada (§10): **fijar la configuración
óptima de centros y resolver el PL de flujos** (transporte / transbordo, Clase 09), que sí tiene
rangos de costos reducidos y de lados derechos. Más re-resolución de escenarios para lo que
cambie la configuración.

**Las cinco preguntas, ordenadas:**

| Pregunta | Qué pide | Tipo |
|---|---|---|
| **a)** | Localización óptima de los CD minimizando costo total + indicadores ambientales (combustible, CO₂) por configuración | Modelo base (PLEM) |
| **b)** | Un único CD de capacidad infinita, costos de apertura y operación nulos: ¿dónde va en el mapa? | Variante continua (problema de Weber / centro de gravedad) |
| **c)** | Valor unitario mínimo de Goyito, **por producto**, a partir del cual no conviene instalar el CD (viaje directo proveedor → supermercado) | Punto de indiferencia / sensibilidad |
| **d)** | Vehículos propios también en proveedor → CD: nuevo costo operativo y comparación ambiental | Escenario (cambia el costo del primer tramo) |
| **e)** | Tope de 500 km mensuales por conductor, penalidad $1.000 por km excedido: cómo entra en el modelo y cómo afecta costo y ambiente | Extensión del modelo (variable de exceso / programación por metas, Clase 05) |

---

## 1. El problema, en palabras

CarroMenos tiene **10 supermercados** que hoy abastece la logística tercerizada de Goyito. Evalúa
tener **su propio centro de distribución**. La red tiene tres niveles:

```
   PROVEEDORES (7 plantas)  ──camión tercerizado──►  CENTROS DE DISTRIBUCIÓN  ──camión propio──►  SUPERMERCADOS (10)
   5 productos                 $500 por km              A, B, C, D (abrir o no)    diesel + conductores    demanda por producto
                                                        capacidad, apertura,
                                                        costo por pallet
```

Se decide **qué centros abrir** y **cuántos pallets de cada producto viajan por cada tramo**. Se
minimiza el costo total (apertura + operación del CD + transporte + eventual gerente) y además se
reportan indicadores ambientales (litros de diesel, kg de CO₂).

---

## 2. Datos de la consigna, ordenados

### 2.1. Centros de distribución

| Centro | Capacidad mensual [posiciones = pallets] | Apertura [$] | Costo por pallet operado [$] |
|---|---:|---:|---:|
| A | 40.000 | 3.000.000 | 10 |
| B | 35.000 | 2.500.000 | 12 |
| C | 15.000 | 1.200.000 | 5 |
| D | 10.000 | 900.000 | 8 |

Reglas del enunciado:
- *"Debe elegir su centro principal para lo cual cuenta con dos opciones"* → **A o B**.
- *"la posibilidad de abrir los Centros C y D sólo si la demanda de productos supera a la capacidad
  del centro A o B"*.
- *"al abrir tres centros de distribución al mismo tiempo la dirección exige contratar un gerente
  de coordinación logística"* → **$2.000.000 mensuales**.

### 2.2. Transporte

| Tramo | Quién | Costo | Dato |
|---|---|---|---|
| Proveedor → CD | Tercerizado | **$500 por km** (tarifa fija) | dado |
| CD → Supermercado | Propio | diesel **$1.300/l**, rendimiento **4 km/l** → **$325 por km** + conductores | conductores: **no dado** |

### 2.3. Demanda mensual promedio [pallets]

| Producto | S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10 | **Total** |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Fideos | 2000 | 1900 | 1800 | 2100 | 2500 | 3000 | 1200 | 1700 | 2100 | 2000 | **20.300** |
| Arroz | 1000 | 900 | 800 | 1200 | 500 | 400 | 850 | 1200 | 800 | 900 | **8.550** |
| Leche | 750 | 800 | 900 | 1100 | 1200 | 950 | 1000 | 1100 | 950 | 1200 | **9.950** |
| Gaseosas | 300 | 400 | 500 | 540 | 340 | 500 | 450 | 400 | 520 | 600 | **4.550** |
| Galletitas | 800 | 900 | 850 | 750 | 950 | 1000 | 950 | 850 | 800 | 650 | **8.500** |
| **Total** | 4.850 | 4.900 | 4.850 | 5.690 | 5.490 | 5.850 | 4.450 | 5.250 | 5.170 | 5.350 | **51.850** |

### 2.4. Ubicaciones (mapa de Google My Maps)

El mapa del link de la consigna ([`../Ubicaciones link.txt`](../Ubicaciones%20link.txt)) se bajó
como KML y se pasó a tabla:

- [`../datos/ubicaciones.kml`](../datos/ubicaciones.kml) — export crudo del mapa (fuente)
- [`../datos/ubicaciones.csv`](../datos/ubicaciones.csv) — `id, nombre_mapa, tipo, producto, lat, lon`

**21 puntos:** 10 supermercados (S1–S10), 4 centros (A–D) y **7 plantas**.

⚠ **Detalle fácil de pasar por alto: hay dos plantas de Fideos y dos de Leche.** El mapa no dice
nada de su capacidad, así que el modelo también decide **desde qué planta** sale cada pallet de
esos productos. Arroz, Gaseosas y Galletitas tienen una sola planta.

| Producto | Plantas | Ubicación aproximada |
|---|---|---|
| Fideos | P_Fideos_1, P_Fideos_2 | noroeste · norte |
| Arroz | P_Arroz_1 | extremo noroeste |
| Leche | P_Leche_1, P_Leche_2 | extremo sur · norte |
| Gaseosas | P_Gaseosas_1 | CABA sur, muy cerca del Centro D |
| Galletitas | P_Galletitas_1 | norte, cerca de S2 |

*(Las zonas son orientativas, a ojo sobre el mapa; las distancias reales se calculan — ver §5, S1.)*

---

## 3. Material de la cátedra disponible

| Archivo | Qué aporta al TP |
|---|---|
| [`Material/OPTUCA-09-Redes.pdf`](../Material/OPTUCA-09-Redes.pdf) | Clase 09: flujo máximo, **flujo de mínimo costo**, ruta más corta, agente viajante. Base del PL de flujos |
| [`Material/IO51-10-Proyectos y Scheduling.pdf`](../Material/IO51-10-Proyectos%20y%20Scheduling.pdf) | Clase 10: CPM, crashing y **staff scheduling** — posiblemente útil para e) (conductores y tope de km) |
| Clase 05 (TP2/Material) | Programación por metas: el exceso de km con penalidad de e) es una **variable de desvío** |
| Clase 06 (TP2/Material) | Entera y binaria: binarias de apertura, restricciones lógicas, "no hay análisis post-óptimo" |
| Links útiles de la consigna | scipbook *Facility Location* (formulación de referencia), AMPL Supply Chain, Gurobi notebooks |
| Portafolio de redes (`mim.com.ar/redes`) | Link de [`Ubicaciones link.txt`](../Ubicaciones%20link.txt). **Pendiente:** la página carga por JavaScript y no se pudo leer automáticamente; revisarla en el navegador |

---

## 4. Primeras cuentas sobre los datos (sin modelo)

### 4.1. ⚠ Ningún centro solo alcanza

La demanda total es **51.850 pallets/mes** y el centro más grande (A) tiene 40.000. **Siempre hay
que abrir más de un centro**, así que la condición "C y D solo si la demanda supera la capacidad de
A o B" **se cumple siempre**: C y D están habilitados.

### 4.2. Combinaciones de centros que cubren la demanda

| Combinación | Capacidad | ¿Cubre 51.850? | Apertura [$] | Gerente | Fijo total [$] |
|---|---:|:---:|---:|:---:|---:|
| A + C | 55.000 | ✔ | 4.200.000 | — | **4.200.000** |
| A + D | 50.000 | ✘ | — | — | — |
| B + C | 50.000 | ✘ | — | — | — |
| B + D | 45.000 | ✘ | — | — | — |
| A + B | 75.000 | ✔ (si se permite, ver S2) | 5.500.000 | — | 5.500.000 |
| B + C + D | 60.000 | ✔ | 6.600.000 | ✔ | 8.600.000 |
| A + C + D | 65.000 | ✔ | 7.100.000 | ✔ | 9.100.000 |
| A + B + C / A + B + D | 90.000 / 85.000 | ✔ (si se permite) | 8.700.000 / 8.400.000 | ✔ | 10.700.000 / 10.400.000 |
| A + B + C + D | 100.000 | ✔ (si se permite) | 9.600.000 | ✔ (ver S3) | 11.600.000 |

**Lectura:** si el principal es único (A *o* B), con B **obligatoriamente** hay que abrir C y D y
pagar gerente. **A + C** es la única configuración de dos centros válida y la más barata en costos
fijos; las otras sólo ganan si el ahorro en transporte compensa la diferencia. Esto **no** es la
respuesta de a): el transporte puede pesar más que los fijos. Es la cota que el modelo tiene que
respetar y un control para la enumeración (son pocas configuraciones: se pueden resolver todas).

---

## 5. Registro de supuestos

La consigna deja abiertas varias cosas. Cada una se cierra acá con un **valor por defecto
justificado**; la alternativa razonable se prueba como test (§13). Las marcadas **(Explorar)** piden
datos no provistos, que es uno de los cuatro criterios de evaluación: **cada valor lleva fuente** en
la bibliografía.

### 5.1. Supuestos sobre la red y las distancias

#### **S1 — Distancias por calle (OSRM)**
- **Enunciado:** *"Utilice los datos del mapa para cuantificar tanto los costos operativos como los
  impactos ambientales"*.
- **Se adopta:** distancia **por ruta**, calculada con el servicio `table` de OSRM (motor de ruteo
  sobre OpenStreetMap, API pública) para los 21 puntos de [`datos/ubicaciones.csv`](../datos/ubicaciones.csv).
  Se baja una vez y se guarda en `datos/distancias_osrm.csv`, así el resto del trabajo no depende de
  internet.
- **Por qué:** un camión no va en línea recta; la línea recta subestima km, litros y CO₂. Las
  distancias por calle son además lo que mostraría el propio Google Maps.
- **Respaldo:** haversine (línea recta sobre la esfera) × **factor de ruta**. El factor se calcula
  con los mismos datos (mediana de ruta / recta), así que es un número propio y no inventado.
- **Test:** resolver con haversine × factor (§13, test A). Si la configuración óptima no cambia, la
  elección de distancias no es crítica.
- ⚠ OSRM no tiene en cuenta tránsito ni restricciones para camiones. Se declara.

#### **S2 — El centro principal es exactamente uno: A o B**
- **Enunciado:** *"Debe elegir su centro principal para lo cual cuenta con dos opciones"*.
- **Se adopta:** `y_A + y_B = 1`.
- **Por qué:** "elegir" entre "dos opciones" es exclusivo. Abrir los dos sería tener dos principales.
- **Test:** `y_A + y_B ≥ 1` (§13, test B). Habilita A+B, A+B+C, etc.

#### **S3 — El gerente se contrata con 3 o más centros abiertos**
- **Enunciado:** *"al abrir tres centros de distribución al mismo tiempo la dirección exige contratar
  un gerente"*.
- **Se adopta:** `g ≥ Σ y_j − 2` con `g` binaria → gerente si hay 3 **o 4** centros.
- **Por qué:** coordinar cuatro centros no es más fácil que coordinar tres. Con S2 nunca hay 4
  abiertos, así que solo pesa en el test B.

#### **S4 — La condición sobre C y D no restringe nada**
- **Enunciado:** *"abrir los Centros C y D sólo si la demanda de productos supera a la capacidad del
  centro A o B"*.
- **Se adopta:** **no se escribe como restricción**: la demanda (51.850) supera a A (40.000) y a B
  (35.000), así que la condición es siempre cierta (§4.1). Se declara en el informe con la cuenta.

#### **S5 — Capacidad de las plantas ilimitada**
- **Por qué:** la consigna no da producción ni capacidad de los proveedores.
- **Consecuencia:** con dos plantas de Fideos y dos de Leche, cada centro se abastece de la planta
  que le resulte más barata. El modelo lo decide solo.

#### **S6 — La capacidad de un centro es lo que opera en el mes**
- **Enunciado:** *"capacidad de almacenamiento mensual [posiciones]"*, *"costo por pallet operado"*.
- **Se adopta:** todo pallet que entra y sale del centro en el mes ocupa una posición:
  `Σ pallets que salen de j ≤ cap_j`. No se modela stock entre meses (demanda promedio, estacionaria).

#### **S7 — Flujos continuos y por producto**
- **Se adopta:** pallets como variables **continuas** y separados **por producto** (5).
- **Por qué:** son 51.850 pallets por mes, redondear no cambia nada. Por producto es obligatorio: los
  productos salen de plantas distintas y la pregunta c) se pide por producto.

### 5.2. Supuestos sobre el transporte

#### **S8 — Camión de 26 pallets (Explorar)**
- **Se adopta:** `Q = 26` pallets por viaje (semirremolque estándar con pallets de 1,00 × 1,20 m).
- **Por qué:** sin capacidad de camión no se pasa de pallets a viajes, ni de viajes a km. **Es el
  dato que más mueve los costos de transporte.**
- **Test:** Q de 20 a 30 (§13, test C).

#### **S9 — Viajes proporcionales a los pallets, sin consolidar ni rutear**
- **Se adopta:** en cada arco, `viajes = pallets / Q` (continuo). Cada viaje va y vuelve por el mismo
  arco, con un solo destino.
- **Por qué:** mantiene el modelo **lineal** (es lo que pide la consigna) y es la simplificación
  estándar de los modelos de localización. Armar rutas con varias paradas (agente viajante / VRP,
  Clase 09) es otro problema y queda fuera de alcance; se declara como limitación.
- **Consecuencia:** el costo por pallet de un arco es `costo por km × km / Q`.

#### **S10 — Ida y vuelta**
- **Se adopta:**
  - **km físicos** (combustible, CO₂, km de conductores): **ida y vuelta** (`2·d`). El camión vuelve
    vacío y consume igual.
  - **tarifa del tercerizado:** $500 por km **del recorrido** (`d`, solo ida). Es una tarifa por
    servicio: el transportista ya incluye su vuelta en el precio.
- **Test:** tarifa sobre ida y vuelta (`2·d`) (§13, test D).

#### **S11 — Costo del camión propio = combustible + conductores**
- **Enunciado:** *"considerar tanto el precio por litro de diesel (1300) como el rendimiento por
  litro del camión (4 km/l) y agregar el costo mensual de los conductores"*.
- **Combustible:** 1.300 $/l ÷ 4 km/l = **$325 por km físico**.
- **Conductores (Explorar):** sueldo mensual **W** con cargas sociales (convenio de camioneros
  vigente) y un máximo realista de **K_max km por conductor y por mes** (default 9.000 km: unos
  22 días × 400 km). Cantidad de conductores `n` **entera**: `K_max · n ≥ km físicos propios`.
- **Por qué así:** el sueldo es un costo fijo por persona, no por km. Y con esta forma la pregunta e)
  es **el mismo modelo** con el tope cambiado a 500 km y vuelto blando.
- No se modela el costo del camión en sí (compra, mantenimiento, seguro): la consigna solo pide
  combustible y conductores. Se declara.

### 5.3. Supuestos sobre lo ambiental

#### **S12 — Indicadores: litros y CO₂ (Explorar)**
- **Se adopta:** `litros = km físicos / 4` y `kg CO₂ = litros × 2,68` (factor del gasoil; fuente a
  citar: IPCC / Secretaría de Energía).
- El camión tercerizado se supone **igual** al propio (4 km/l): no hay otro dato.
- Se reportan **por tramo** (proveedor → CD, CD → súper) y en total.

#### **S13 — El funcional minimiza costo; lo ambiental se reporta y se explora**
- **Enunciado:** *"minimizando el costo total y considerando, además, indicadores ambientales"*.
- **Se adopta:**
  1. el funcional es el **costo total** en pesos;
  2. se reportan litros y CO₂ de **cada configuración** de centros (§9);
  3. se arma la **frontera costo–CO₂** por ε-restricción (`CO₂ ≤ ε`), igual que la frontera de
     Pareto del TP1.
- **Por qué:** "además" indica un criterio secundario. Ponerle precio al carbono dentro del funcional
  mezcla una decisión de valor con el costo; la frontera muestra el trade-off sin decidir por el
  directorio.
- **Test:** precio del carbono dentro del funcional (§13, test F, opcional).

### 5.4. Supuestos de las preguntas

#### **S14 — Pregunta e): el tope es de 500 km por mes**
- **Enunciado:** *"elevado número de kilómetros recorridos **al día**"* y *"un máximo de 500
  kilómetros **mensuales** para cada conductor"*.
- **Se adopta:** **mensuales** (es el número negociado). La inconsistencia se señala en el informe.
- 500 km por mes es muy poco (un día de trabajo): se espera un salto grande de conductores o de
  penalidad. Ver §12 e).

#### **S15 — Pregunta c): Goyito cobra un precio por pallet entregado, por producto**
- **Enunciado:** *"valor mínimo unitario ofrecido por la empresa Goyito, por producto"* y *"el viaje
  directamente desde los proveedores a los supermercados"*.
- **Se adopta:** Goyito cobra `g_k` $ por pallet del producto k entregado en el supermercado, y lleva
  la mercadería **directo** de la planta al súper (sin CD). Para los indicadores ambientales de
  Goyito se usan los mismos supuestos de camión (S8, S10, S12).

### 5.5. Tabla resumen

| # | Supuesto | Valor adoptado | Alternativa (test) | Tipo |
|---|---|---|---|---|
| S1 | Distancias | Por calle, OSRM | Haversine × factor | Se testea (A) |
| S2 | Centro principal | Exactamente uno (A o B) | Al menos uno | Se testea (B) |
| S3 | Gerente | Con 3 o más centros | — | Se declara |
| S4 | Condición de C y D | Siempre cierta, sin restricción | — | Se declara |
| S5 | Capacidad de plantas | Ilimitada | — | Se declara |
| S6 | Capacidad del centro | Pallets operados por mes | — | Se declara |
| S7 | Flujos | Continuos, por producto | — | Se declara |
| S8 | Camión | 26 pallets **(Explorar)** | 20 a 30 | Se testea (C) |
| S9 | Viajes | Pallets / Q, sin ruteo | — | Se declara (limitación) |
| S10 | Ida y vuelta | Física i+v; tarifa solo ida | Tarifa i+v | Se testea (D) |
| S11 | Conductores | W y K_max **(Explorar)**, `n` entera | W ±30 %, K_max 6.000–12.000 | Se testea (E) |
| S12 | Emisiones | 4 km/l, 2,68 kg CO₂/l **(Explorar)** | — | Se declara |
| S13 | Ambiental | Funcional = costo; frontera costo–CO₂ | Precio del carbono en FO | Se testea (F) |
| S14 | Tope de e) | 500 km por mes | — | Se declara |
| S15 | Goyito | $ por pallet, por producto, viaje directo | — | Se declara |

### 5.6. ¿Sirven para todas las preguntas?

Sí. **Todas las preguntas son el mismo modelo con otros parámetros**, salvo la b), que cambia de
naturaleza (el centro puede ir en cualquier punto del mapa, ver §12 b):

| Pregunta | Qué cambia respecto de a) |
|---|---|
| b) | Un solo centro, sin capacidad, sin costos fijos ni por pallet; la ubicación es continua |
| c) | Se agrega la opción "Goyito lleva el producto k" con precio `g_k` |
| d) | El tramo proveedor → CD pasa a costar combustible + conductores en vez de $500/km |
| e) | El tope de km por conductor pasa a 500 y se vuelve blando, con penalidad |

---

## 6. Conjuntos, parámetros y variables

### 6.1. Conjuntos

| Símbolo | Qué es | Elementos |
|---|---|---|
| `K` | Productos | Fideos, Arroz, Leche, Gaseosas, Galletitas |
| `P` | Plantas | 7; `prod(p)` es el producto de la planta p. `P_k` = plantas del producto k |
| `J` | Centros de distribución | A, B, C, D |
| `I` | Supermercados | S1 … S10 |

### 6.2. Parámetros

| Símbolo | Qué es | Valor | Fuente |
|---|---|---|---|
| `dem_ik` | Demanda del súper i, producto k [pallets/mes] | tabla §2.3 | consigna |
| `cap_j` | Capacidad del centro j [pallets/mes] | 40.000 / 35.000 / 15.000 / 10.000 | consigna |
| `F_j` | Apertura del centro j [$/mes] | 3.000.000 / 2.500.000 / 1.200.000 / 900.000 | consigna |
| `c_j` | Costo por pallet operado en j [$] | 10 / 12 / 5 / 8 | consigna |
| `G` | Sueldo del gerente [$/mes] | 2.000.000 | consigna |
| `d_pj`, `d_ji` | Distancia por calle [km] | OSRM | mapa (S1) |
| `T` | Tarifa del tercerizado [$/km] | 500 | consigna |
| `CK` | Combustible del camión propio [$/km] | 1.300 / 4 = 325 | consigna |
| `Q` | Pallets por camión | 26 | Explorar (S8) |
| `W` | Sueldo mensual de un conductor, con cargas [$] | a definir | Explorar (S11) |
| `K_max` | km máximos por conductor y por mes | 9.000 | Explorar (S11) |
| `φ` | Emisión del gasoil [kg CO₂/l] | 2,68 | Explorar (S12) |
| `r` | Rendimiento [km/l] | 4 | consigna |

**Coeficientes derivados por pallet** (los calcula `datos.py`; dan una lectura directa de cuánto
cuesta mover un pallet por cada arco):

```
costo tramo 1 (tercerizado):  a_pj = T · d_pj / Q                 [$ por pallet]
costo tramo 2 (propio, comb.): b_ji = CK · 2·d_ji / Q              [$ por pallet]
km físicos tramo 1:            2·d_pj / Q                          [km por pallet]
km físicos tramo 2:            2·d_ji / Q                          [km por pallet]
```

Por ejemplo, con Q = 26: un pallet que viaja 30 km en el tramo 1 cuesta 500 × 30 / 26 ≈ **$577**;
en el tramo 2 cuesta 325 × 60 / 26 = **$750** de combustible. Frente a eso, el costo por pallet
operado del centro (5 a 12 $) es **despreciable**: se espera que la ubicación pese mucho más que el
costo de operación. Es una predicción a verificar.

### 6.3. Variables de decisión

| Variable | Tipo | Qué es |
|---|---|---|
| `y_j` | binaria | 1 si se abre el centro j |
| `g` | binaria | 1 si se contrata el gerente |
| `x_pj` | continua ≥ 0 | pallets/mes de la planta p al centro j (producto `prod(p)`) |
| `z_jik` | continua ≥ 0 | pallets/mes del producto k del centro j al súper i |
| `n` | entera ≥ 0 | conductores propios contratados |
| `exc` | continua ≥ 0 | solo en e): km por encima del tope pactado |

Tamaño: 4 + 1 + 28 + 200 + 1 ≈ **234 variables**, 5 enteras. CBC lo resuelve al instante, y además
se puede verificar por enumeración (§9).

**Expresiones auxiliares** (no son variables, se arman con las anteriores):

```
km_1   = Σ_p Σ_j  2·d_pj · x_pj / Q            km físicos proveedor → CD
km_2   = Σ_j Σ_i  2·d_ji · Σ_k z_jik / Q       km físicos CD → súper
km_prop = km_2         (en d: km_1 + km_2)      km que hacen los conductores propios
litros = (km_1 + km_2) / r
CO2    = litros · φ
```

---

## 7. La función objetivo

### 7.1. Caso base (pregunta a)

```
Min  Z =   Σ_j F_j · y_j                                     apertura
         + G · g                                             gerente
         + Σ_j c_j · Σ_i Σ_k z_jik                           operación del centro
         + Σ_p Σ_j (T · d_pj / Q) · x_pj                     tercerizado, proveedor → CD
         + Σ_j Σ_i (CK · 2·d_ji / Q) · Σ_k z_jik             combustible, CD → súper
         + W · n                                             conductores
```

Todo está en **$ por mes**: la apertura se toma como costo mensual, como el sueldo del gerente.
⚠ **Hay que confirmarlo**: si "costo estimado de apertura" fuese una inversión única, habría que
mensualizarla (amortización). Se declara como supuesto en el informe; el test de §13 muestra desde
qué valor de apertura cambia la configuración (barrido de `F_j`).

### 7.2. Variantes (mismo funcional, otros términos)

| Escenario | Cambio en el funcional |
|---|---|
| **d)** flota propia en el tramo 1 | `T · d_pj / Q` → `CK · 2·d_pj / Q`, y los km del tramo 1 suman a `km_prop` (más conductores) |
| **e)** tope de 500 km | `+ 1.000 · exc` |
| **c)** opción Goyito | `+ Σ_k g_k · dem_k · u_k` (ver §12 c) |
| frontera costo–CO₂ | mismo funcional + restricción `CO2 ≤ ε` |

---

## 8. Las restricciones, una por una

| # | Nombre | Restricción | Frase del enunciado / supuesto |
|---|---|---|---|
| R1 | `DEM_i_k` | `Σ_j z_jik = dem_ik` ∀ i, k | *"abastecer la demanda"* (50 restricciones) |
| R2 | `BAL_j_k` | `Σ_{p ∈ P_k} x_pj = Σ_i z_jik` ∀ j, k | Lo que sale de un centro entró desde una planta de ese producto (20) |
| R3 | `CAP_j` | `Σ_i Σ_k z_jik ≤ cap_j · y_j` ∀ j | Capacidad mensual de la tabla (S6). Además **ata el flujo a la apertura**: un centro cerrado no mueve nada |
| R4 | `PRINCIPAL` | `y_A + y_B = 1` | *"Debe elegir su centro principal… dos opciones"* (S2) |
| R5 | `GERENTE` | `g ≥ Σ_j y_j − 2` | *"al abrir tres centros… un gerente"* (S3) |
| R6 | `CONDUCTORES` | `K_max · n ≥ km_prop` | *"agregar el costo mensual de los conductores"* (S11) |
| R7 | `TOPE_KM` (solo e) | `km_prop − 500 · n ≤ exc` | *"máximo de 500 km mensuales… penalidad de 1,000 pesos por km excedido"* |
| R8 | `CO2_MAX` (solo frontera) | `CO2 ≤ ε` | S13 |
| — | dominio | `y, g` binarias · `n` entera · `x, z, exc ≥ 0` | |

Notas:
- **R3 hace dos trabajos** (capacidad y lógica de apertura), es el clásico "big-M" de localización
  con `M = cap_j`. Se puede reforzar con `z_jik ≤ dem_ik · y_j` (formulación fuerte del scipbook):
  no cambia el óptimo pero mejora la relajación. Se prueba si hace falta.
- En e) **R6 se reemplaza por R7**: el tope deja de ser duro (K_max) y pasa a ser blando (500 + exceso
  pagado).
- Todas las restricciones llevan **nombre** para leer holguras y precios sombra en el PL de flujos
  (§10).

---

## 9. Control independiente: enumeración de configuraciones

Igual que la enumeración exhaustiva del TP2 (§8 de aquel plan): son pocas configuraciones, se
pueden resolver **todas** sin el solver entero.

Con S2, las configuraciones que cubren 51.850 pallets son solo **3** (§4.2):

| Configuración | Fijos [$] |
|---|---:|
| A + C | 4.200.000 |
| A + C + D | 9.100.000 (con gerente) |
| B + C + D | 8.600.000 (con gerente) |

Para cada una se **fija `y`** y se resuelve el **PL de flujos** (un problema de transbordo continuo,
Clase 09). Resultado: una tabla con **costo total, desglose de costos, km, litros y CO₂ por
configuración** — que es justamente lo que pide a) (*"los impactos ambientales de cada
configuración"*).

**Controles:**
- El óptimo del modelo entero tiene que coincidir con el mínimo de la tabla.
- La configuración más barata en CO₂ puede no ser la más barata en pesos: si pasa, es la frontera
  de §12 a).
- Con el test B (A y B juntos) la tabla crece a 8 configuraciones y se repite el control.

---

## 10. Análisis de sensibilidad (informe b)

Con binarias no hay precios sombra (Clase 06). La sensibilidad se hace sobre el **PL de flujos con
la configuración óptima fija** (`y = y*`), que sí es un PL continuo, y se complementa con
re-resolución del modelo entero para los cambios que mueven la configuración.

Misma interpretación que en el TP1:

### 10.1. b.i — Rangos de nivel de actividad → rangos de los lados derechos

- Precios sombra de **R1** (cuánto cuesta un pallet más de demanda en cada súper y producto: el
  "costo marginal de servir") y de **R3** (cuánto vale un pallet más de capacidad en un centro).
- Rango de cada lado derecho dentro del cual el precio sombra es válido.
- Holguras: qué centros quedan llenos y cuáles con capacidad ociosa.

### 10.2. b.ii — Rangos de soluciones posibles → rangos de los costos

- Rango de cada coeficiente del funcional (costo por pallet de cada arco, `c_j`) dentro del cual la
  asignación óptima no cambia.
- **Costos reducidos** de los arcos no usados: cuánto tendría que bajar el costo de un arco para que
  convenga usarlo.

### 10.3. Herramienta

PuLP/CBC no devuelve rangos. Se usa **highspy** (`Highs.getRanging()`), que da los rangos de costos
y de lados derechos del PL. **Control cruzado:** re-resolver perturbando un coeficiente hasta que cambie
la solución (lo que hizo el TP1 a mano), al menos para 2 o 3 casos.

### 10.4. Barridos que cambian la configuración (re-resolución del entero)

Los rangos de 10.1–10.2 valen con la configuración fija. Lo que puede **cambiar qué centros se
abren** se barre re-resolviendo el modelo entero:

| Parámetro | Rango | Pregunta que responde |
|---|---|---|
| Tarifa del tercerizado `T` | 250 a 1.000 $/km | ¿desde qué tarifa conviene otra configuración? |
| `Q` | 20 a 30 | (es también el test C) |
| `F_j` (apertura) | ×0,5 a ×2 | ¿qué tan cerca está la configuración de cambiar? |
| Demanda total | ×0,8 a ×1,3 | crecimiento: ¿cuándo deja de alcanzar A + C? (55.000 = +6 %) |

⚠ Fuera del rango, el precio sombra deja de valer: hay que resolver de nuevo (advertencia de la
Clase 3, ya usada en el TP1).

---

## 11. Representación gráfica del flujo de transportes (informe c)

- **Mapa** en matplotlib sobre lat/lon: supermercados en azul, centros en naranja, plantas en verde
  (los colores del mapa de la consigna). Centros cerrados en gris.
- **Flechas** proveedor → CD y CD → súper con **ancho proporcional a los pallets**; colores por
  tramo o por producto.
- Etiquetas con pallets/mes en los arcos principales.
- Una figura por escenario: **a)**, **d)** y **e)**; para **b)** el punto óptimo con los centros
  candidatos y el centroide.
- Opcional: mapa base de calles (`contextily`) o versión interactiva en HTML (`folium`). No es
  necesario para el informe.

---

## 12. Guía por pregunta

### a) Localización óptima + indicadores ambientales

1. Resolver el modelo base (§7.1, §8).
2. Reportar: centros abiertos, flujos (tablas por tramo y por producto), **desglose del costo**
   (apertura, gerente, operación, tramo 1, combustible tramo 2, conductores), km, litros, CO₂.
3. Tabla de **las 3 configuraciones** (§9) con costo y CO₂ de cada una.
4. **Frontera costo–CO₂**: barrer `ε` desde el CO₂ del óptimo de costo hasta el mínimo CO₂ posible
   (minimizar CO₂ sin mirar costo da el extremo). Gráfico costo vs. CO₂.
5. Interpretación: qué plantas abastecen a qué centros (en Fideos y Leche hay elección), qué
   supermercados atiende cada centro, cuáles quedan con capacidad ociosa.

### b) Un único centro de capacidad infinita y costos nulos

Sin capacidad ni costos fijos, el problema se vuelve un **problema de Weber** (ubicar un punto que
minimice la suma de distancias ponderadas):

```
Min  Σ_k (T/Q) · dem_k · min_{p ∈ P_k} d(p, X)  +  Σ_i (2·CK/Q) · dem_i · d(X, i)
       X = (lat, lon)
```

- El `min` sobre plantas (Fideos y Leche tienen dos) hace la función no convexa: se resuelve con una
  **grilla** sobre la zona del mapa + refinamiento local con `scipy.optimize.minimize` desde los
  mejores puntos. El algoritmo de Weiszfeld (con las plantas fijas) sirve de control.
- Distancias: haversine × factor de ruta (S1), porque OSRM no se puede consultar para cada punto de
  la grilla. Al final, se verifica el punto elegido con OSRM.
- **Dos ponderaciones:** económica (los $ por km de cada tramo, como arriba) y ambiental (km físicos
  sin pesos monetarios, que minimiza litros y CO₂). Si dan puntos distintos, se discute.
- Comparar el punto óptimo con: los centros **A–D** (evaluados con la misma función), y el **centro
  de gravedad** (promedio ponderado de coordenadas, la respuesta "ingenua").
- Respuesta: dónde queda en el mapa (zona), cuántos km y CO₂ ahorra frente a A–D.

### c) Precio mínimo de Goyito por producto

Goyito lleva cada producto **directo** planta → súper (S15). Se resuelve en dos niveles:

1. **Umbral global:** con Goyito haciendo todo, CarroMenos paga `Σ_k g_k · dem_k`. Instalar el CD no
   conviene si eso es ≤ `Z*`. Con un precio único por pallet, el umbral es `Z* / 51.850`.
2. **Umbral por producto** (lo que pide la consigna): se agrega la binaria `u_k` = "el producto k lo
   lleva Goyito". Si `u_k = 1`, la demanda de k sale de R1 y se paga `g_k · dem_k`. Para cada
   producto se **barre `g_k`** y se busca el valor en que el modelo pasa de `u_k = 0` a `u_k = 1`.
   - Ese umbral **no es simplemente el costo promedio** del producto: sacar un producto puede liberar
     capacidad y permitir cerrar un centro (por ejemplo, sin Fideos la demanda baja a 31.550 y
     **alcanza A solo**). El barrido lo captura; la cuenta promedio no.
   - Control analítico: el costo incremental del producto, `Z*(con k) − Z*(sin k)`, dividido
     `dem_k`, tiene que coincidir con el umbral del barrido.
3. **Ambiental:** km, litros y CO₂ del viaje directo de Goyito vs. vía CD. El viaje directo puede
   hacer **menos km** (no pasa por el centro) o **más** (no consolida): hay que calcularlo. Si se
   monetiza el CO₂ (test F), se suma al umbral.

### d) Flota propia también en el tramo proveedor → CD

1. Mismo modelo, tramo 1 con costo `CK · 2·d / Q` y sus km sumados a los de conductores (§7.2).
2. Comparar con a): costo total y desglose, **¿cambia la configuración?**, km, litros y CO₂.
3. Cuenta rápida previa: el tramo 1 pasa de 500·d a 650·d por viaje (325 × 2) **más conductores**,
   así que **en $/km la flota propia es más cara** que la tarifa de $500 si se cuenta la vuelta. Los
   km físicos (y el CO₂) **no cambian** si el camión es el mismo (S12): la diferencia ambiental viene
   solo de que **cambien las rutas elegidas**. Es una predicción a verificar.

### e) Tope de 500 km por conductor

1. **Cómo se incorpora** (lo que pregunta la consigna): R6 se reemplaza por R7
   `km_prop − 500 · n ≤ exc`, y el funcional suma `1.000 · exc`. Es una **meta con variable de
   desvío** (Clase 05): `exc` es el desvío por exceso, y la penalidad su peso.
2. **Trade-off:** un conductor más cuesta `W` y "cubre" 500 km; pagar esos 500 km de exceso cuesta
   **$500.000**. Si `W > 500.000`, conviene pagar la penalidad en vez de contratar; si `W < 500.000`,
   conviene contratar. Hay que ver dónde cae el W de la tarea T02.
3. Como el costo marginal del km sube (combustible + penalidad o conductor), el modelo tiene
   incentivo a **acortar km del tramo propio**: puede mover supermercados a centros más cercanos o
   cambiar la configuración. **Eso baja litros y CO₂**: efecto ambiental positivo forzado por la
   regla laboral. Reportarlo.
4. Correrlo sobre el caso base y sobre d) (con flota propia en los dos tramos los km son muchos más).
5. Opcional: barrer el tope (500 a K_max) y la penalidad.

---

## 13. Protocolo de test de supuestos

Cada test: se cambia **un** supuesto, se re-resuelve el modelo entero y se compara con la base.

| Test | Supuesto | Base | Alternativa | Qué se mira |
|---|---|---|---|---|
| A | S1 distancias | OSRM | haversine × factor | ¿cambia la configuración? diferencia de costo y CO₂ |
| B | S2 principal | A xor B | al menos uno | ¿aparece A + B o A + B + algo como óptimo? |
| C | S8 camión | 26 | 20, 22, 24, 28, 30 | costo de transporte; ¿cambia la configuración? |
| D | S10 tarifa | solo ida | ida y vuelta | peso del tramo 1; ¿cambia la configuración? |
| E | S11 conductores | W, 9.000 km | W ±30 %; K_max 6.000 a 12.000 | costo; efecto en e) |
| F | S13 ambiental | sin precio de carbono | con precio de carbono | ¿la configuración cambia por el CO₂? |
| G | §7.1 apertura | mensual | ×0,5 a ×2 | margen antes de cambiar de configuración |

**Cómo se reporta** (igual que el TP2): una tabla con columnas *Test · Base · Alternativa ·
Configuración · Costo · CO₂ · ¿Cambia la conclusión?*

**Propiedades que tienen que cumplirse** (asserts del script de tests):
- Relajar S2 (test B) nunca sube el costo.
- Más pallets por camión nunca suben el costo de transporte.
- Cobrar la tarifa ida y vuelta nunca baja el costo.
- Con precio de carbono, el CO₂ del óptimo nunca sube.

---

## 14. Herramientas

**Stack: Python + PuLP (solver CBC)**, igual que en el TP1 y el TP2.

```python
import pulp                       # modelo entero mixto de localización
import pandas as pd               # tablas de datos y de resultados
import matplotlib.pyplot as plt   # mapa de flujos, frontera costo–CO₂
import highspy                    # rangos de sensibilidad del PL de flujos (§10)
from scipy.optimize import minimize   # punto de Weber (pregunta b)
import requests                   # una sola vez: distancias OSRM → datos/distancias_osrm.csv
```

`highspy` y `requests` se agregan a `requirements.txt` (tarea T16 y T08).

**Requisito de diseño, el mismo de los dos TP anteriores:** el modelo se escribe **una sola vez**:

```python
params = config.construir_params(Q=26, distancias="osrm", principal="exclusivo",
                                 tarifa_ida_vuelta=False, precio_co2=0, ...)
modelo.resolver(params, escenario="a",          # "a" | "d" | "e"
                config_fija=None,               # {"A":1,"C":1,...} → PL de flujos (§9, §10)
                epsilon_co2=None,               # frontera costo–CO₂
                goyito=None)                    # {producto: precio} → pregunta c)
```

- Un supuesto mal escrito falla con `KeyError`; un valor fuera de rango con `ValueError` (para que un
  typo no devuelva el caso base haciéndose pasar por el escenario pedido).
- Restricciones con nombre (`DEM_S1_Fideos`, `CAP_A`, …).
- El resultado es un `dict` con estado, valor, centros, flujos, desglose de costos e indicadores
  ambientales: todos los scripts leen lo mismo.

---

## 15. Estructura del código prevista

```
TP3/
├── README.md
├── requirements.txt
├── Ubicaciones link.txt          links del mapa y del portafolio de redes
├── Consigna/ · Material/
├── datos/
│   ├── ubicaciones.kml           export crudo del mapa (fuente)
│   ├── ubicaciones.csv           los 21 puntos con lat/lon
│   └── distancias_osrm.csv       matriz de distancias por calle (se genera una vez)
├── docs/
│   ├── plan_de_trabajo.md        este archivo
│   ├── tareas.md                 el trabajo dividido en tareas
│   └── procedimiento.md          la bitácora
├── src/
│   ├── config.py                 datos de la consigna + supuestos → params
│   ├── datos.py                  lectura de ubicaciones y distancias, coeficientes por arco
│   ├── modelo.py                 resolver(params, ...) — el único modelo
│   ├── sensibilidad.py           PL de flujos en highspy + rangos
│   ├── weber.py                  pregunta b)
│   ├── reportes.py               tablas de salida
│   └── graficos.py               mapa de flujos, frontera, barridos
├── scripts/
│   ├── 00_verificar_datos.py     asserts contra la consigna y §4
│   ├── 01_distancias.py          baja OSRM y guarda la matriz (una vez)
│   ├── 02_punto_a.py             óptimo, enumeración, frontera costo–CO₂, mapa
│   ├── 03_sensibilidad.py        rangos y barridos (informe b)
│   ├── 04_punto_b.py
│   ├── 05_punto_c.py
│   ├── 06_punto_d.py
│   ├── 07_punto_e.py
│   └── 08_tests_supuestos.py
├── resultados/{tablas,graficos}/
└── informe/                      informe.tex + informe.pdf
```

La carpeta `datos/` es nueva respecto del TP1 y el TP2: allá todos los datos estaban en el
enunciado y vivían en `config.py`; acá las coordenadas y las distancias vienen de afuera.

---

## 16. Los tres documentos del trabajo

| Archivo | Qué es | Cuándo se escribe | ¿Cambia? |
|---|---|---|---|
| **`plan_de_trabajo.md`** (este) | **Esquema / plan.** Datos, supuestos, modelo, tests previstos | Antes de codificar | Solo si cambia una **decisión de modelado**; se registra el cambio |
| **`tareas.md`** | **El plan dividido en tareas**, en orden, con dependencias y criterio de "hecho" | Ahora | Se tildan las tareas a medida que se hacen |
| **`procedimiento.md`** | **Bitácora de ejecución.** Lo que efectivamente se hizo, los resultados, y **en qué se apartó del plan y por qué** | Durante el código | Permanentemente, es un log |

---

## 17. Checklist del informe esperable

Cada ítem del informe apunta a la sección del plan y a las tareas de [`tareas.md`](tareas.md).

| Ítem del informe | Plan | Tareas |
|---|---|---|
| a.i Supuestos | §5 | T24 |
| a.ii Variables | §6.3 | T24 |
| a.iii Función objetivo | §7 | T24 |
| a.iv Parámetros | §2, §6.2 | T24 |
| a.v Restricciones | §8 | T24 |
| a.vi Resolución | §9, §12 a) | T13, T24 |
| b.i Rangos de nivel de actividad | §10.1 | T16, T25 |
| b.ii Rangos de soluciones posibles | §10.2 | T16, T25 |
| c Gráfico de flujos | §11 | T15, T26 |
| d Librerías | §14 | T27 |
| Preguntas a) a e) | §12 | T13–T14, T18–T21, T28 |
| Bibliografía | §5 (Explorar) | T01–T06, T29 |
