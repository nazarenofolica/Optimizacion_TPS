"""
Guion del reel: la fuente única. Ocho escenas, con los capítulos del video largo (TPF/video/guion.py) contados en tono
de Instagram, y un capítulo propio para el bolsillo (las tres formas de pagar menos).

Cada "beat" es un bloque de una a tres oraciones que se sintetiza de una sola vez (voz.py): así la voz entona la
oración entera y no suena a frases pegadas. Las animaciones (src/) se enganchan a los beats y a las palabras dichas
(`cuadro("b05", "sucursales")`), así que si cambia la voz o el texto, todo se vuelve a sincronizar solo.

Un beat es (id, texto) o (id, texto, {"velocidad": "+4%", "pausa": 0.5}); una escena puede traer "opciones" con lo
mismo para todos sus beats (el ejemplo va más despacio, para que se entienda).

Dentro de un beat:
  {escrito|dicho}   lo que se lee en los subtítulos y lo que dice la voz, cuando no coinciden: cifras
                    ({8 millones|ocho millones}) o siglas.

Los números son los del informe (informe/informe.tex), los mismos del video largo (TPF/video/escenas.py).
"""

VOZ = "es-AR-TomasNeural"       # rioplatense; se pisa con la variable de entorno VOZ (ver muestras_voz.py)
VELOCIDAD = "+12%"              # más ágil que la voz por defecto: ritmo de reel
TONO = "+0Hz"
PAUSA_BEAT = 0.28               # silencio entre beats de una misma escena
PAUSA_ESCENA = 0.5              # silencio entre escenas (ahí entra la transición)

NOMBRE = "Changuito Sano"
URL = "changuito-sano.pages.dev"

ESCENAS = [
    {
        "id": "e1", "titulo": "La pregunta",
        "beats": [
            ("b01", "En {1945|mil novecientos cuarenta y cinco}, un economista calculó "
                    "la dieta más barata del mundo."),
            ("b02", "¿El resultado? Harina, repollo y espinaca. Todo el año."),
            ("b03", "Barata, sí. Pero nadie la querría comer."),
            ("b04", "Así nació el problema de la dieta. Y nosotros lo llevamos al súper de hoy."),
        ],
    },
    {
        "id": "e2", "titulo": "Los datos",
        "beats": [
            ("b05", "Los súper informan sus precios todos los días: juntamos más de {8 millones|ocho millones}, "
                    "de {2.600|dos mil seiscientas} sucursales."),
            ("b06", "Y la tabla nutricional de casi {28.000|veintiocho mil} productos: "
                    "qué aporta, cuánto cuesta, y para quién es apto."),
        ],
    },
    {
        "id": "e3", "titulo": "La página",
        "beats": [
            ("b07", "Con eso armamos una página. Le contás quiénes comen, dónde comprás, y para cuánto tiempo."),
            ("b08", "Y te arma el ticket: qué comprar, en qué súper, y a cuántos minutos caminando."),
            ("b09", "Para Sofi, que trabaja en el centro, comer bien cuesta unos "
                    "{$24.000|veinticuatro mil pesos} por semana, "
                    "y cumple sus {37|treinta y siete} metas nutricionales."),
        ],
    },
    {
        "id": "e4", "titulo": "El modelo",
        "beats": [
            ("b10", "¿Y cómo decide? Hay dos objetivos que se pelean: comer bien, y gastar poco."),
            ("b11", "Podríamos ponerle un precio a la salud. Pero no: primero la salud, y después el bolsillo."),
            ("b12", "Primero, un programa lineal busca lo mejor que se puede comer. Cada meta tiene un rango: "
                    "quedarse corto, o pasarse, es un desvío, y se minimiza la suma."),
            ("b13", "Después, un programa entero busca lo más barato que logra lo mismo, "
                    "con paquetes enteros. Nadie vende medio paquete de fideos."),
        ],
    },
    {
        # El ejemplo va más despacio y en cinco pasos (la oferta, las metas, el óptimo, el precio sombra y qué pasa si
        # no alcanza), con un marcador que se completa y la compra que se actualiza: el mismo hilo que "Tu bolsillo".
        "id": "e5", "titulo": "Un ejemplo",
        "opciones": {"velocidad": "+6%", "pausa": 0.42},
        "beats": [
            ("x1", "Un ejemplo chico: fideos, lentejas y arroz."),
            ("x2", "Los fideos son baratos, pero casi no tienen proteína. "
                   "Así que la compra se arma con lentejas y arroz, y cada uno es un eje."),
            ("x3", "Cada punto del plano es una compra posible."),
            ("x4", "Pedimos entre {1.900 y 2.100|mil novecientas y dos mil cien} calorías: una franja."),
            ("x5", "Y al menos {60|sesenta} gramos de proteína: otra recta, que deja afuera lo que se queda corto. "
                   "Lo que queda es la región factible."),
            ("x6", "La recta de costo baja hasta tocar una esquina: la compra más barata que cumple todo."),
            ("x7", "¿Y el precio sombra? Es cuánto sube el costo si una meta pide un poco más. "
                   "Un gramo más de proteína: unos {$21|veintiún pesos} por semana."),
            ("x8", "¿Y si pedimos {300|trescientos} gramos? La región desaparece: ninguna compra alcanza."),
            ("x9", "Pero el modelo no se rompe: llega a {150|ciento cincuenta}, lo máximo posible, y avisa qué falta."),
        ],
    },
    {
        "id": "e6", "titulo": "Casos reales",
        "beats": [
            ("b19", "Con datos reales, una familia de cuatro, una persona celíaca, una vegana: "
                    "todos cumplen sus metas."),
            ("b20", "Pero a una persona celíaca y alérgica a la leche, en Córdoba, no le alcanza ninguna sucursal: "
                    "el calcio llega al {74 %|setenta y cuatro por ciento}, y los lácteos, al {67|sesenta y siete}."),
            ("b21", "Y los precios sombra muestran que son justo las metas que más encarecen la canasta."),
        ],
    },
    {
        "id": "e7", "titulo": "Tu bolsillo",
        "beats": [
            ("b22", "¿Y el bolsillo? Hay tres formas de pagar menos por la misma canasta."),
            ("b23", "Una: comprar para el mes. Cada día sale un {26 %|veintiséis por ciento} menos, "
                    "porque se aprovechan mejor los envases."),
            ("b24", "Dos: caminar hasta una hora, en vez de quince minutos: "
                    "sale un {25 %|veinticinco por ciento} menos."),
            ("b25", "Y tres: repartir la compra entre dos súper. En un caso, se ahorra más de la mitad."),
        ],
    },
    {
        "id": "e8", "titulo": "Cierre",
        "beats": [
            ("b26", "Moraleja: dónde comprás importa tanto como qué comprás."),
            ("b27", "Se llama Changuito Sano, y es gratis. Probala, y pasásela a quien dice que comer sano es caro."),
        ],
    },
]
