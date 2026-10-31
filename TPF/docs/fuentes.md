# Fuentes

Todo lo que usa el TPF, con su referencia. Las de la sección 1 sostienen la introducción
([`introduccion.md`](introduccion.md)); las de la 2 alimentan la base de datos
([`../datos/sepa/`](../datos/sepa/)); las de la 3 son los requisitos nutricionales que va a usar el
modelo.

---

## 1. El problema de la dieta (historia)

| Referencia | Qué se toma |
|---|---|
| Stigler, G. J. (1945). *The Cost of Subsistence*. Journal of Farm Economics, 27(2), 303–314. | El planteo original: 77 alimentos, 9 nutrientes, raciones del National Research Council de 1943, su dieta de US\$ 39,93 al año (precios de 1939) y la frase "No one recommends these diets for anyone, let alone everyone" |
| Dantzig, G. B. (1990). *The Diet Problem*. Interfaces, 20(4), 43–47. [doi:10.1287/inte.20.4.43](https://doi.org/10.1287/inte.20.4.43) | La primera resolución con el símplex (Laderman, National Bureau of Standards, 9 empleados, ~120 jornadas-hombre, US\$ 39,69) y la anécdota de su propia dieta |
| Dantzig, G. B. (1963). *Linear Programming and Extensions*. Princeton University Press. | El problema de Stigler como primer cálculo "de gran escala" con el símplex |
| Garille, S. G. y Gass, S. I. (2001). *Stigler's Diet Problem Revisited*. Operations Research, 49(1), 1–13. [doi:10.1287/opre.49.1.1.11187](https://doi.org/10.1287/opre.49.1.1.11187) | La comparación entre la heurística de Stigler y el óptimo, la versión sin excedentes (US\$ 49,40), la actualización a precios de 1998 (US\$ 651,27 para un hombre y US\$ 535,27 para una mujer) y los usos posteriores (raciones animales, Thrifty Food Plan, almuerzos escolares) |
| EurekAlert! / INFORMS (2000). [*Updated study shows baseline annual diet costs less for women than men*](https://www.eurekalert.org/news-releases/1024821). | La IBM 701 que en 1953 resolvió el problema en 12 minutos |
| Taylor, T. (2025). [*When George Dantzig Optimized His Personal Diet Problem*](https://conversableeconomist.com/2025/10/07/when-george-dantzig-optimized-his-personal-diet-problem/). Conversable Economist. | Citas textuales del artículo de Dantzig de 1990 (vinagre, cubos de caldo, salvado, melaza) |
| Wikipedia. [*Stigler diet*](https://en.wikipedia.org/wiki/Stigler_diet). | Tabla de mínimos de 1943 y cantidades de la dieta de Stigler (fuente secundaria, contrastada con las anteriores) |
| Google OR-Tools. [*The Stigler diet problem*](https://github.com/google/or-tools/blob/stable/ortools/linear_solver/samples/stigler_diet.py) (licencia Apache 2.0). | La tabla de Stigler de 77 alimentos transcripta, para replicar el problema original |

---

## 2. La base de datos

| Fuente | Qué aporta | Licencia / acceso |
|---|---|---|
| **SEPA — Sistema Electrónico de Publicidad de Precios Argentinos**, Secretaría de Comercio Interior. Conjunto de datos [*Precios Claros - Base SEPA*](https://datos.produccion.gob.ar/dataset/sepa-precios) (id `6f47ec76-d1ce-4e34-a7e1-621fe9b1d0b5`), archivo `sepa_viernes_2026-10-23.zip` | Los precios de cada producto en cada sucursal, las descripciones de los productos y las sucursales (dirección, coordenada, horarios) | Creative Commons Atribución 4.0 |
| **Open Food Facts** ([world.openfoodfacts.org](https://world.openfoodfacts.org)), volcado completo en [static.openfoodfacts.org](https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz) | Rótulos nutricionales, ingredientes, alérgenos, NOVA y fotos de envases | Open Database License (ODbL) |
| **USDA FoodData Central, SR Legacy** (abril de 2018), [fdc.nal.usda.gov](https://fdc.nal.usda.gov/) | Composición de laboratorio de los alimentos genéricos (frescos, carnes, marcas sin rótulo) | Dominio público |
| **Catálogos online de Jumbo, Disco y Vea** ([jumbo.com.ar](https://www.jumbo.com.ar), [disco.com.ar](https://www.disco.com.ar), [vea.com.ar](https://www.vea.com.ar), plataforma VTEX) | Rótulos, ingredientes, certificaciones (sin TACC) y la categoría de góndola con la que se verifica la clasificación | Información pública de los sitios |
| **Fotos de envases** (Open Food Facts) transcriptas a mano: [`../base_sepa/referencia/rotulos_fotos.csv`](../base_sepa/referencia/rotulos_fotos.csv) | Tablas nutricionales de 606 productos sin rótulo en la web | Elaboración propia |
| **API Georef**, Servicio de Normalización de Datos Geográficos de Argentina ([apis.datos.gob.ar/georef](https://apis.datos.gob.ar/georef/api)) | Validación de coordenadas; provincia, departamento y municipio con códigos INDEC | Datos abiertos del Estado nacional |
| **Normalizador de direcciones USIG** del GCBA ([servicios.usig.buenosaires.gob.ar](https://servicios.usig.buenosaires.gob.ar/normalizar/)) | Geocodificación de direcciones en la Ciudad de Buenos Aires | Servicio público del GCBA |
| **Barrios y comunas de CABA**, datos abiertos del GCBA ([barrios.geojson](https://cdn.buenosaires.gob.ar/datosabiertos/datasets/ministerio-de-educacion/barrios/barrios.geojson)) | Barrio y comuna de cada tienda de la Ciudad | Datos abiertos del GCBA |

Cómo se combinan estas fuentes, con qué controles y qué queda afuera: [`../base_sepa/README.md`](../base_sepa/README.md)
y [`../datos/README.md`](../datos/README.md).

---

## 3. Requisitos nutricionales (para el modelo)

| Referencia | Qué se toma |
|---|---|
| **Código Alimentario Argentino, Capítulo V** (rotulado), Anexo A de la **Res. GMC 46/03** del Mercosur. [PDF de ANMAT](https://www.argentina.gob.ar/sites/default/files/anmat_caa_capitulo_v_rotulacion_actualiz_2021-09.pdf) | Valores Diarios de Referencia (2.000 kcal; carbohidratos 300 g; proteínas 75 g; grasas totales 55 g; saturadas 22 g; fibra 25 g; sodio 2.400 mg) e Ingestas Diarias Recomendadas de vitaminas y minerales (vitamina A 600 µg, C 45 mg, D 5 µg, E 10 mg, tiamina 1,2 mg, riboflavina 1,3 mg, niacina 16 mg, B6 1,3 mg, B12 2,4 µg, calcio 1.000 mg, hierro 14 mg, magnesio 260 mg, zinc 7 mg, entre otras) |
| **Res. GMC 31/06** del Mercosur, complementaria de la 46/03. [FAOLEX](https://faolex.fao.org/docs/pdf/mrc107064.pdf) | Corrección del ácido fólico: 240 µg, equivalentes a 400 µg de folato |
| Ministerio de Salud de la Nación (2016). **Guías Alimentarias para la Población Argentina. Documento técnico metodológico.** [Copia en msptucuman.gov.ar](https://msptucuman.gov.ar/wordpress/wp-content/uploads/2016/06/guia_alimentaria.pdf) | La persona de referencia (mujer adulta, 2.000 kcal), las metas por consenso (proteínas 15 %, grasas 30 % y carbohidratos 55 % de la energía; fibra 25 g; calcio 1.000 mg; hierro 18 mg; zinc 8 mg; vitamina A 700 µg; vitamina D 15 µg; B12 2,4 µg; folato 400 µg; sodio: mínimo seguro 500 mg y meta de 5 g de sal; 400 g de frutas y verduras), el **Plan Alimentario Promedio** (leche y yogur 500 cc, queso 30 g, huevo 25 g, carnes 130 g, hortalizas 400 g, frutas 300 g, feculentos cocidos 250 g, pan 120 g, aceite, semillas y frutas secas 30 g, agua 2 l) y el tope de alimentos de consumo opcional (13,5 % de la energía) |
| OMS/FAO (2003). *Diet, Nutrition and the Prevention of Chronic Diseases*. Serie de Informes Técnicos 916. | Grasas saturadas por debajo del 10 % de la energía; base de los VDR del Mercosur |
| FAO/OMS (2001). *Human Vitamin and Mineral Requirements*. Consulta de expertos, Bangkok. | Base de las IDR de vitaminas y minerales del Mercosur |
| Institute of Medicine (1997–2005). *Dietary Reference Intakes*. National Academies Press. | Base de las metas de micronutrientes de las Guías; rangos aceptables de macronutrientes y niveles superiores tolerables |
| INDEC. [*Canasta básica alimentaria y canasta básica total*](https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-43-149) (valorización mensual). | Referencia para comparar el costo de la dieta con la línea de indigencia |
