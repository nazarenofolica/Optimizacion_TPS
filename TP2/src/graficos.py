"""
Gráficos del TP2 — Sección Cocinas.

La función recibe una tabla ya calculada (nunca vuelve a resolver el modelo) y
guarda un PNG en resultados/graficos/, pensado para pegarse en el informe.

Criterios, para que se lea como una figura de informe y no como una pantalla:

  - **Adentro de la figura solo van los datos.** Sin título, sin subtítulo y sin
    notas: eso es trabajo del epígrafe (\\caption) del informe, que además es donde
    el lector lo busca. Lo único que queda es el eje, las barras y sus valores.
  - **Tipografía serif**, del tamaño del cuerpo del texto, para que la figura no
    desentone con el LaTeX.
  - **Forma de énfasis**: una sola serie, con el espacio que limita en color y el
    resto en gris. La historia del punto a) es un número —las mesadas—, no siete.
  - **Paleta validada**, no elegida a ojo: el azul #2a78d6 pasa banda de
    luminosidad, piso de croma y contraste >= 3:1 sobre la superficie #fcfcfb; el
    gris #898781 de lo secundario mide 3,5:1 sobre esa misma superficie.
  - **Los textos nunca van del color de la serie**: la identidad la da la marca de
    color al lado, no la tinta de la letra.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventana: los scripts corren en consola

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

CARPETA = Path(__file__).resolve().parents[1] / "resultados" / "graficos"

#: Superficie y tintas.
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRILLA = "#e1e0d9"
EJE = "#c3c2b7"

#: Series: acento para el espacio que limita, gris para el resto, y un paso claro
#: de cada familia para la capacidad todavía sin usar.
ACENTO = "#2a78d6"
ACENTO_TRACK = "#cde2fb"
GRIS = "#898781"
GRIS_TRACK = "#e1e0d9"

#: Ancho de figura en pulgadas: el \textwidth de un article a4 con margen de 3 cm.
ANCHO = 6.3


def _estilo():
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["DejaVu Serif", "Times New Roman"],
            "font.size": 9,
            "figure.facecolor": SUPERFICIE,
            "axes.facecolor": SUPERFICIE,
            "axes.edgecolor": EJE,
            "axes.labelcolor": TINTA_2,
            "text.color": TINTA,
            "xtick.color": EJE,
            "ytick.color": EJE,
            "xtick.labelcolor": TINTA_2,
            "ytick.labelcolor": TINTA,
            "grid.color": GRILLA,
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "legend.frameon": False,
        }
    )


def _guardar(fig, nombre):
    CARPETA.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA / f"{nombre}.png"
    fig.savefig(ruta, dpi=300, bbox_inches="tight", facecolor=SUPERFICIE)
    plt.close(fig)
    return ruta


def ocupacion_deposito(tabla_espacios, nombre_archivo="01_ocupacion_deposito"):
    """Ocupación y capacidad de cada espacio del depósito, en barras.

    Parameters
    ----------
    tabla_espacios : pandas.DataFrame
        Salida de `reportes.tabla_espacios`. Columnas: "Espacio", "Capacidad",
        "Ocupado", "Holgura", "Limita".

    Epígrafe sugerido para el informe: "Ocupación del depósito en el plan óptimo
    del punto a): 21 de 33 lugares. Mesadas es el único espacio sin holgura y es
    lo que limita la oferta a tres combos."
    """
    _estilo()
    t = tabla_espacios.iloc[::-1].reset_index(drop=True)  # el primer espacio, arriba
    limita = [v == "Sí" for v in t["Limita"]]
    y = range(len(t))

    fig, ax = plt.subplots(figsize=(ANCHO, 2.5))
    ax.barh(y, t["Capacidad"], height=0.5, zorder=2,
            color=[ACENTO_TRACK if lim else GRIS_TRACK for lim in limita])
    ax.barh(y, t["Ocupado"], height=0.5, zorder=3,
            color=[ACENTO if lim else GRIS for lim in limita])

    for i, (ocupado, capacidad) in enumerate(zip(t["Ocupado"], t["Capacidad"])):
        ax.text(capacidad + 0.22, i, f"{ocupado}/{capacidad}",
                va="center", fontsize=8, color=TINTA_2)

    ax.set_yticks(list(y))
    ax.set_yticklabels(t["Espacio"])
    ax.set_xlabel("Lugares del depósito")
    ax.set_xlim(0, int(t["Capacidad"].max()) + 1.2)
    ax.set_xticks(range(0, int(t["Capacidad"].max()) + 1, 2))
    ax.grid(axis="x", zorder=1)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)

    # La referencia va debajo del eje, en una sola fila: dentro del área de datos
    # queda flotando y le roba espacio a las barras.
    ax.legend(
        handles=[
            Patch(color=GRIS, label="Ocupado"),
            Patch(color=GRIS_TRACK, label="Capacidad sin usar"),
            Patch(color=ACENTO, label="Espacio que limita"),
        ],
        loc="upper center", bbox_to_anchor=(0.5, -0.30), ncol=3,
        fontsize=7.5, labelcolor=TINTA_2, handlelength=1.2, handleheight=0.9,
        columnspacing=1.6,
    )
    fig.tight_layout()
    return _guardar(fig, nombre_archivo)
