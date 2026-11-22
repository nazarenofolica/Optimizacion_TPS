"""
Guion del video: la fuente única. Siete capítulos; cada uno es una lista de frases.

Cada frase se sintetiza por separado (voz.py) y se une con una pausa medida, así la locución respira donde tiene que
respirar y no corre una oración sobre la otra. Dentro de una frase:

  {escrito|dicho}   lo que se lee en los subtítulos y lo que dice la voz, cuando no coinciden: cifras
                    ({1945|mil novecientos cuarenta y cinco}) o nombres que la voz pronunciaría mal
                    ({George Stigler|Yorch Estígler}).
  " / "             un corte de subtítulo dentro de la frase (la voz no se detiene).

Una frase es un texto o un par (texto, segundos de pausa después). escenas.py espera las frases por lo que dice la
voz (`self.hasta("ocho millones")`), así que las marcas se escriben como se dicen.

Los números salen del informe (informe/informe.tex), que a su vez salen del motor.
"""

VOZ = "es-AR-ElenaNeural"      # rioplatense, femenina
VELOCIDAD = "+0%"
PAUSA = 0.38                   # entre frases de una misma escena, si la frase no dice otra cosa

ESCENAS = [
    {
        "id": "e1_pregunta",
        "titulo": "La pregunta",
        "frases": [
            "En {1945|mil novecientos cuarenta y cinco}, el economista {George Stigler|Yorch Estígler} "
            "se hizo una pregunta simple.",
            ("¿Cuál es la dieta más barata / que cubre todo lo que necesita una persona?", 0.6),
            "Su respuesta se volvió un clásico de la programación lineal.",
            ("Pero era una dieta que nadie querría comer: / harina, repollo y espinaca, todo el año.", 0.7),
            "Nosotros nos hicimos la misma pregunta, con los precios de hoy, / "
            "y la llevamos al supermercado de la esquina.",
        ],
    },
    {
        "id": "e2_datos",
        "titulo": "Los datos",
        "frases": [
            "Todo empieza con los datos.",
            "Los supermercados informan sus precios, todos los días, al sistema {SEPA|Sepa}.",
            "Juntamos más de {8 millones|ocho millones} de precios, / "
            "de más de {2.600|dos mil seiscientas} sucursales de todo el país.",
            ("Y los cruzamos con la información nutricional / de casi {28.000|veintiocho mil} productos.", 0.5),
            "Así, de cada producto sabemos tres cosas: / qué aporta, cuánto cuesta, y para quién es apto.",
        ],
    },
    {
        "id": "e3_pagina",
        "titulo": "La página",
        "frases": [
            "Con todo eso armamos una página web.",
            ("Le contás quiénes comen en tu casa,", 2.6),
            "dónde comprás,",
            ("y para cuánto tiempo.", 1.5),
            "En unos segundos, te devuelve el ticket: / qué comprar, producto por producto,",
            "en qué supermercado, y a cuántos minutos caminando.",
            "Para una oficinista del centro de Buenos Aires, / "
            "la compra más barata cuesta unos {$24.000|veinticuatro mil pesos} por semana,",
            "y cumple sus {37|treinta y siete} metas nutricionales.",
        ],
    },
    {
        "id": "e4_modelo",
        "titulo": "El modelo",
        "frases": [
            ("¿Y cómo decide? Acá entra la optimización.", 0.5),
            "Hay dos objetivos que se pelean: comer bien, y gastar poco.",
            "En lugar de ponerle un precio a la salud, los ordenamos: / primero uno, y después el otro.",
            ("Se llaman metas lexicográficas, y se resuelven en dos etapas.", 0.6),
            "En la primera, un programa lineal busca lo mejor que se puede comer / con lo que vende la sucursal.",
            "Cada meta tiene un rango.",
            "Quedar por debajo o por encima es un desvío, / medido en porcentaje.",
            ("Y se minimiza la suma de los desvíos.", 0.6),
            "En la segunda, un programa entero busca la compra más barata que logra lo mismo: / "
            "con envases enteros, y sin empeorar ninguna meta.",
        ],
    },
    {
        "id": "e5_ejemplo",
        "titulo": "Un ejemplo",
        "frases": [
            "Veámoslo con un ejemplo chico: fideos, lentejas y arroz.",
            ("Los fideos son los más baratos, pero casi no tienen proteína.", 0.5),
            "Pedimos entre {1.900 y 2.100|mil novecientas y dos mil cien} calorías por día, / "
            "y al menos {60|sesenta} gramos de proteína.",
            "Cada restricción recorta el plano. / Lo que queda es la región factible.",
            "El óptimo cae en un vértice: / lentejas y arroz, en la proporción justa.",
            ("Se cumplen todas las metas.", 0.6),
            "Y el precio sombra dice cuánto cuesta cada gramo más de proteína: / "
            "unos {$21|veintiún pesos} por semana.",
            ("¿Y si pedimos {300|trescientos} gramos de proteína?", 0.5),
            "La recta se aleja, y la región factible desaparece: / ninguna compra cumple.",
            ("Pero el modelo no se rompe. / Llega a lo máximo posible, {150|ciento cincuenta} gramos, "
             "y avisa que falta la mitad.", 0.6),
            "Cuando se puede, cumple todo al menor costo. / Cuando no, se acerca lo más posible, y lo dice.",
        ],
    },
    {
        "id": "e6_casos",
        "titulo": "Casos",
        "frases": [
            "Con los datos reales pasa lo mismo.",
            "Una familia de cuatro: cuatro dietas en una sola compra, / "
            "y las {148|ciento cuarenta y ocho} metas cumplidas.",
            ("Una persona celíaca, una vegana, alguien con anemia: / todos cumplen sus metas.", 0.5),
            ("Y para alguien que quiere subir de peso, / quinientas calorías más por día cuestan apenas "
             "{$1.100|mil cien pesos} por semana.", 0.6),
            "Pero a una persona celíaca y alérgica a la leche, en Córdoba, / ninguna sucursal le alcanza.",
            "El calcio llega al {74 %|setenta y cuatro por ciento}, y los lácteos, "
            "al {67 %|sesenta y siete}.",
            ("El modelo da la mejor compra posible, y muestra qué falta.", 0.7),
            "También decide dónde comprar.",
            "Caminando hasta una hora, / la misma canasta cuesta un {25 %|veinticinco por ciento} menos.",
            "Y repartida entre dos supermercados, / en un caso se ahorra más de la mitad.",
        ],
    },
    {
        "id": "e7_cierre",
        "titulo": "Cierre",
        "frases": [
            "Por último, la sensibilidad.",
            "Los precios sombra muestran qué metas encarecen más la canasta: / el calcio y los lácteos.",
            ("Y comprar para un mes, en vez de una semana, / baja el costo por día un "
             "{26 %|veintiséis por ciento}, / porque se aprovechan mejor los envases.", 0.8),
            "En resumen: el problema de la dieta sigue sirviendo, / si se lo completa.",
            ("Y dónde comprás importa tanto como qué comprás.", 0.8),
            "La página está publicada. Probala.",
        ],
    },
]
