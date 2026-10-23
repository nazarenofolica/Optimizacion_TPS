"""
Gráficos del TP3. Cada figura tiene UN trabajo y el mínimo de texto:

- `mapa_asignacion`: qué centro abastece a cada supermercado (tramo 2). Mapa ampliado sobre la
  zona de los súper; color = centro (fijo por centro), grosor = pallets/mes. Sin números: los
  números están en las tablas.
- `tabla_tramo1`: desde qué planta se abastece cada centro (tramo 1), como tabla de calor. Son 15
  flujos de 7 plantas a 3 centros: en un mapa se cruzan; como tabla se leen de una.
- `frontera_costo_co2`: costo mínimo para cada tope de CO2, en escalones.

Paleta de centros validada con el validador de la skill dataviz (todas las parejas, daltonismo
incluido). Como el aqua tiene poco contraste, cada centro lleva su letra escrita.
"""

import math

import matplotlib

matplotlib.use("Agg")
# Los rótulos llevan "$" de pesos: que matplotlib no los lea como fórmulas.
matplotlib.rcParams["text.parse_math"] = False
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import FancyArrowPatch, Rectangle  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
import numpy as np  # noqa: E402

TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_3 = "#8a8983"
GRILLA = "#ebeae6"
FONDO = "#ffffff"
APAGADO = "#c9c7c0"

#: Color fijo por centro (sigue a la entidad: si en otro escenario se abre B, A no cambia de color).
COLOR_CENTRO = {"A": "#2a78d6", "B": "#6250d6", "C": "#eb6834", "D": "#1baf7a"}
COLOR_SERIE = "#2a78d6"
#: Rampa secuencial de un solo tono (azul) para la tabla de calor.
RAMPA = LinearSegmentedColormap.from_list("azul", ["#eef4fc", "#9cc0ee", "#2a78d6", "#174a8c"])

#: Posición del nombre de cada súper respecto del punto [pt] y alineación.
ETIQUETA_SUPER = {
    "S4": ((-8, 0), "right"),
    "S8": ((8, 0), "left"),
    "S9": ((0, -12), "center"),
    "S1": ((8, 0), "left"),
}

HALO = [pe.withStroke(linewidth=3, foreground=FONDO)]


def _miles(x):
    return f"{x:,.0f}".replace(",", ".")


def _titulo(fig, titulo, subtitulo=None):
    fig.text(0.02, 0.97, titulo, fontsize=13, fontweight="bold", color=TINTA, va="top")
    if subtitulo:
        fig.text(0.02, 0.915, subtitulo, fontsize=9.5, color=TINTA_2, va="top")


# ---------------------------------------------------------------------------
# Mapa: qué centro abastece a cada supermercado
# ---------------------------------------------------------------------------


def mapa_asignacion(res, ubic, titulo, archivo):
    """Tramo 2 (centro -> súper) sobre un mapa ampliado a la zona de los supermercados."""
    f2 = res["flujos_tramo2"].groupby(["centro", "super"], as_index=False)["pallets"].sum()
    abiertos = set(res["centros"])
    zona = ubic[ubic["tipo"].isin(["supermercado", "centro"])]
    principal = f2.sort_values("pallets").groupby("super")["centro"].last().to_dict()

    fig, ax = plt.subplots(figsize=(9, 7.6), dpi=150)
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    ax.axis("off")
    ax.set_aspect(1 / math.cos(math.radians(zona["lat"].mean())))
    ax.set_xlim(zona["lon"].min() - 0.025, zona["lon"].max() + 0.035)
    ax.set_ylim(zona["lat"].min() - 0.02, zona["lat"].max() + 0.02)

    maximo = f2["pallets"].max()
    for f in f2.sort_values("pallets").itertuples():  # las gruesas encima
        o, d = ubic.loc[f.centro], ubic.loc[f.super]
        ax.add_patch(FancyArrowPatch(
            (o.lon, o.lat), (d.lon, d.lat), arrowstyle="-", lw=0.8 + 7 * f.pallets / maximo,
            color=COLOR_CENTRO[f.centro], alpha=0.85, shrinkA=10, shrinkB=4, zorder=2,
            capstyle="round",
        ))

    for s, p in ubic[ubic["tipo"] == "supermercado"].iterrows():
        ax.scatter(p.lon, p.lat, s=70, marker="s", color=COLOR_CENTRO[principal[s]],
                   edgecolor=FONDO, lw=1.5, zorder=4)
        (dx, dy), ha = ETIQUETA_SUPER.get(s, ((8, 0), "left"))
        ax.annotate(s, (p.lon, p.lat), xytext=(dx, dy), textcoords="offset points", ha=ha,
                    va="center", fontsize=9.5, fontweight="bold", color=TINTA, path_effects=HALO,
                    zorder=5)

    for j in COLOR_CENTRO:
        p = ubic.loc[j]
        if j in abiertos:
            ax.scatter(p.lon, p.lat, s=520, color=COLOR_CENTRO[j], edgecolor=FONDO, lw=2.5, zorder=6)
            ax.text(p.lon, p.lat, j, color=FONDO, fontsize=11, fontweight="bold", ha="center",
                    va="center", zorder=7)
        else:
            ax.scatter(p.lon, p.lat, s=300, color=FONDO, edgecolor=APAGADO, lw=1.5, zorder=6)
            ax.text(p.lon, p.lat, j, color=TINTA_3, fontsize=10, ha="center", va="center", zorder=7)

    # Barra de escala de 5 km.
    km5 = 5 / (111.32 * math.cos(math.radians(zona["lat"].mean())))
    x0, y0 = ax.get_xlim()[0] + 0.01, ax.get_ylim()[0] + 0.008
    ax.plot([x0, x0 + km5], [y0, y0], color=TINTA_2, lw=2, solid_capstyle="butt")
    ax.text(x0 + km5 / 2, y0 + 0.004, "5 km", ha="center", va="bottom", fontsize=8.5, color=TINTA_2)

    cerrados = [j for j in COLOR_CENTRO if j not in abiertos]
    _titulo(fig, titulo, "Color: centro que abastece · grosor: pallets por mes"
            + (f" · {', '.join(cerrados)} cerrado" if cerrados else ""))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.02)
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Tabla de calor: desde qué planta se abastece cada centro
# ---------------------------------------------------------------------------


def tabla_tramo1(res, titulo, archivo):
    """Pallets/mes de cada planta a cada centro abierto, con lo que recibe cada centro y su uso."""
    centros = res["centros"]
    matriz = res["flujos_tramo1"].pivot_table(
        index="planta", columns="centro", values="pallets", aggfunc="sum", fill_value=0
    ).reindex(columns=centros, fill_value=0)
    matriz = matriz.loc[sorted(matriz.index, key=lambda p: (p.split("_")[1], p))]
    filas = [p.replace("P_", "").replace("_", " ") for p in matriz.index]
    valores = matriz.to_numpy()
    maximo = valores.max()
    ocup = res["ocupacion"].set_index("centro")

    n_f, n_c = len(filas), len(centros)
    alto, ancho, etiq = 0.42, 1.05, 1.5          # pulgadas: alto de fila, ancho de columna, rótulos
    fig_w = etiq + ancho * (n_c + 1) + 0.3
    fig_h = alto * (n_f + 4) + 1.1
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=150)
    fig.patch.set_facecolor(FONDO)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, fig_w)
    ax.set_ylim(fig_h, 0)  # y crece hacia abajo, en pulgadas
    ax.axis("off")

    y0 = 1.0
    x_col = [etiq + ancho * (c + 0.5) for c in range(n_c)]
    x_tot = etiq + ancho * (n_c + 0.5)
    kw = dict(ha="center", va="center", fontsize=9.5)

    for c, j in enumerate(centros):  # encabezado: letra del centro en su color
        ax.scatter(x_col[c], y0 + alto / 2, s=260, color=COLOR_CENTRO[j], zorder=3)
        ax.text(x_col[c], y0 + alto / 2, j, color=FONDO, fontweight="bold", zorder=4, **kw)
    ax.text(x_tot, y0 + alto / 2, "Total", color=TINTA_2, **kw)

    for r, nombre in enumerate(filas):
        yc = y0 + alto * (r + 1.5)
        ax.text(etiq - 0.12, yc, nombre, ha="right", va="center", fontsize=9.5, color=TINTA)
        for c in range(n_c):
            v = valores[r, c]
            if v > 0:
                t = v / maximo
                ax.add_patch(Rectangle((etiq + ancho * c + 0.03, yc - alto / 2 + 0.03),
                                       ancho - 0.06, alto - 0.06, color=RAMPA(0.08 + 0.92 * t), lw=0))
                ax.text(x_col[c], yc, _miles(v), color=FONDO if t > 0.45 else TINTA, **kw)
            else:
                ax.text(x_col[c], yc, "–", color=APAGADO, **kw)
        ax.text(x_tot, yc, _miles(valores[r].sum()), color=TINTA_2, **kw)

    y = y0 + alto * (n_f + 1)
    ax.plot([0.15, x_tot + ancho / 2], [y + 0.02, y + 0.02], color=APAGADO, lw=0.8)
    pie = [
        ("Recibe", [_miles(valores[:, c].sum()) for c in range(n_c)], _miles(valores.sum())),
        ("Capacidad", [_miles(ocup.at[j, "capacidad"]) for j in centros], ""),
        ("Uso", [f"{ocup.at[j, 'uso_pct']:.0f} %" for j in centros], ""),
    ]
    for k, (nombre, celdas, total) in enumerate(pie):
        yc = y + alto * (k + 0.5)
        color, peso = (TINTA, "bold") if k == 0 else (TINTA_2, "normal")
        ax.text(etiq - 0.12, yc, nombre, ha="right", va="center", fontsize=9.5, color=color,
                fontweight=peso)
        for c, texto in enumerate(celdas):
            ax.text(x_col[c], yc, texto, color=color, fontweight=peso, **kw)
        ax.text(x_tot, yc, total, color=color, fontweight=peso, **kw)

    ax.text(0.15, 0.3, titulo, fontsize=12, fontweight="bold", color=TINTA, va="center")
    ax.text(0.15, 0.64, "Pallets por mes, de cada planta a cada centro", fontsize=9,
            color=TINTA_2, va="center")
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Frontera costo–CO2
# ---------------------------------------------------------------------------


def frontera_costo_co2(tabla, archivo):
    """Costo mínimo para cada tope de CO2 (tabla con co2_t, costo_M, conductores), en escalones.

    Con `n` entera no hay soluciones intermedias: para un tope ε entre dos puntos, el costo mínimo
    es el del punto de la izquierda. Cada escalón es un conductor más.
    """
    tabla = tabla.sort_values("co2_t").reset_index(drop=True)
    optimo = tabla.iloc[-1]

    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=150)
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(APAGADO)
    ax.grid(axis="y", color=GRILLA, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TINTA_2, labelsize=9, length=0, pad=6)

    ax.step(tabla["co2_t"], tabla["costo_M"], where="post", color=COLOR_SERIE, lw=2, zorder=2)
    ax.scatter(tabla["co2_t"], tabla["costo_M"], s=45, color=COLOR_SERIE, edgecolor=FONDO, lw=1.8,
               zorder=3)

    # Un rótulo corto por escalón, en su punto más barato.
    for n, grupo in tabla.groupby("conductores"):
        fila = grupo.iloc[-1]
        es_optimo = fila.name == optimo.name
        ax.annotate(f"{n} conductores" + (" · óptimo" if es_optimo else ""),
                    (fila["co2_t"], fila["costo_M"]),
                    xytext=(-10, -2) if es_optimo else (8, 7), textcoords="offset points",
                    ha="right" if es_optimo else "left", va="top" if es_optimo else "bottom",
                    fontsize=9, color=TINTA, fontweight="bold" if es_optimo else "normal",
                    path_effects=HALO)

    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"$ {v:.0f} M"))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
    ax.set_xlabel("Tope de emisiones [t de CO₂ por mes]", color=TINTA_2, fontsize=9.5, labelpad=8)
    ax.set_ylim(tabla["costo_M"].min() - 0.7, tabla["costo_M"].max() + 0.8)
    ax.set_xlim(tabla["co2_t"].min() - 0.2, tabla["co2_t"].max() + 0.25)
    _titulo(fig, "Costo mínimo según el tope de CO₂",
            f"Todas las soluciones abren {optimo['configuracion']}")
    fig.subplots_adjust(left=0.1, right=0.97, top=0.8, bottom=0.14)
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Barridos: ¿cambia la configuración óptima?
# ---------------------------------------------------------------------------


def barridos(tabla, definicion, base, cambios, archivo):
    """Costo total óptimo al barrer cada parámetro (un panel por parámetro).

    `definicion`: [(parametro, valores, etiqueta)]; `base`: {parametro: valor del caso base};
    `cambios`: tabla con parametro, umbral, antes, despues (de 03_sensibilidad.cambios).
    La configuración se rotula como texto sobre cada tramo; donde no hay solución, zona rayada.
    """
    fig, ejes = plt.subplots(2, 2, figsize=(10, 6.6), dpi=150)
    fig.patch.set_facecolor(FONDO)
    for ax, (parametro, _, etiqueta) in zip(ejes.flat, definicion):
        g = tabla[tabla["parametro"] == parametro].sort_values("valor")
        ok = g[g["configuracion"] != "infactible"]
        ax.set_facecolor(FONDO)
        for lado in ("top", "right", "left"):
            ax.spines[lado].set_visible(False)
        ax.spines["bottom"].set_color(APAGADO)
        ax.grid(axis="y", color=GRILLA, lw=0.8)
        ax.set_axisbelow(True)
        ax.tick_params(colors=TINTA_2, labelsize=8.5, length=0, pad=5)

        ax.plot(ok["valor"], ok["costo_total"] / 1e6, color=COLOR_SERIE, lw=2, zorder=3)
        fila_base = ok[np.isclose(ok["valor"], base[parametro])]
        if not fila_base.empty:
            ax.scatter(fila_base["valor"], fila_base["costo_total"] / 1e6, s=55, color=COLOR_SERIE,
                       edgecolor=FONDO, lw=2, zorder=4)
            ax.annotate("caso base", (fila_base["valor"].iloc[0], fila_base["costo_total"].iloc[0] / 1e6),
                        xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8,
                        color=TINTA_2, path_effects=HALO)

        x_min, x_max = g["valor"].min(), g["valor"].max()
        ax.set_xlim(x_min, x_max)
        y_lo, y_hi = ok["costo_total"].min() / 1e6, ok["costo_total"].max() / 1e6
        margen = 0.12 * (y_hi - y_lo or 1)
        ax.set_ylim(y_lo - margen, y_hi + 2.2 * margen)

        # Tramos de configuración: límites = umbrales afinados.
        c = cambios[cambios["parametro"] == parametro] if not cambios.empty else cambios
        limites = [x_min] + list(c["umbral"]) + [x_max]
        nombres = [ok["configuracion"].iloc[0]] + list(c["despues"])
        for (a, b), nombre in zip(zip(limites[:-1], limites[1:]), nombres):
            if nombre == "infactible":  # franja angosta: rótulo vertical adentro
                ax.axvspan(a, b, facecolor=FONDO, hatch="///", edgecolor=APAGADO, lw=0, zorder=1)
                ax.text((a + b) / 2, 0.5, "sin solución", transform=ax.get_xaxis_transform(),
                        rotation=90, ha="center", va="center", fontsize=8, color=TINTA_2,
                        path_effects=HALO, zorder=3)
                continue
            ax.text((a + b) / 2, 0.95, nombre, transform=ax.get_xaxis_transform(), ha="center",
                    va="top", fontsize=8.5, fontweight="bold", color=TINTA)
        for u in list(c["umbral"]):
            ax.axvline(u, color=TINTA_3, lw=0.8, ls=(0, (3, 3)), zorder=2)
            valor = f"×{u:.2f}".replace(".", ",") if parametro.startswith("factor") else f"{u:,.0f}".replace(",", ".")
            ax.text(u, 0.04, valor + " ", transform=ax.get_xaxis_transform(), ha="right",
                    va="bottom", fontsize=8, color=TINTA_2, path_effects=HALO, zorder=3)

        ax.set_title(etiqueta, loc="left", fontsize=9.5, color=TINTA, pad=6)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"$ {v:.0f} M"))
        ax.xaxis.set_major_formatter(FuncFormatter(
            lambda v, _: f"{v:g}".replace(".", ",") if parametro.startswith("factor") else f"{v:,.0f}".replace(",", ".")))
    _titulo(fig, "¿Cambia la configuración óptima?",
            "Costo total mínimo re-resolviendo el modelo entero para cada valor")
    fig.subplots_adjust(left=0.08, right=0.98, top=0.83, bottom=0.07, hspace=0.45, wspace=0.18)
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Pregunta b): dónde va un único centro
# ---------------------------------------------------------------------------

COLOR_SUPER = "#2a78d6"
COLOR_PLANTA = "#1b8a4a"
COLOR_OPTIMO = "#0b0b0b"


def mapa_punto_b(ubic, grilla, puntos, titulo, archivo,
                 cortes=(1, 3, 6, 10), radio_zona=None):
    """Mapa completo (plantas, centros candidatos, supermercados) con los puntos candidatos de la
    etapa 2 de la pregunta b), coloreados según cuánto más caro que el mejor sale ubicar ahí el
    centro (distancias por calle).

    `grilla`: DataFrame con lat, lon y sobrecosto_pct. `puntos`: [(etiqueta, lat, lon, marcador)];
    se identifican en la leyenda para no encimar rótulos.
    """
    from matplotlib.lines import Line2D

    fig, ax = plt.subplots(figsize=(9, 7.6), dpi=150)
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    ax.axis("off")
    ax.set_aspect(1 / math.cos(math.radians(ubic["lat"].mean())))
    ax.set_xlim(ubic["lon"].min() - 0.03, ubic["lon"].max() + 0.03)
    ax.set_ylim(ubic["lat"].min() - 0.025, ubic["lat"].max() + 0.03)

    # Candidatos por calle, en escalones de sobrecosto (más oscuro = más barato).
    limites = [-1e-9, *cortes, float("inf")]
    tonos = [RAMPA(t) for t in np.linspace(0.95, 0.12, len(limites) - 1)]
    rotulos = [f"hasta +{cortes[0]} %"] + [f"+{a} a +{b} %" for a, b in zip(cortes[:-1], cortes[1:])]         + [f"más de +{cortes[-1]} %"]
    manijas = []
    for (a, b), tono, rotulo in zip(zip(limites[:-1], limites[1:]), tonos, rotulos):
        g = grilla[(grilla["sobrecosto_pct"] > a) & (grilla["sobrecosto_pct"] <= b)]
        ax.scatter(g["lon"], g["lat"], s=34, marker="s", color=tono, lw=0, zorder=1)
        manijas.append(Line2D([], [], marker="s", ls="", color=tono, markersize=7, label=rotulo))

    for s, p in ubic[ubic["tipo"] == "supermercado"].iterrows():
        ax.scatter(p.lon, p.lat, s=55, marker="s", color=FONDO, edgecolor=COLOR_SUPER, lw=1.8, zorder=4)
        ax.annotate(s, (p.lon, p.lat), xytext=(7, 0), textcoords="offset points", va="center",
                    fontsize=8.5, color=TINTA, path_effects=HALO, zorder=5)
    for pl, p in ubic[ubic["tipo"] == "planta"].iterrows():
        ax.scatter(p.lon, p.lat, s=70, marker="^", color=COLOR_PLANTA, edgecolor=FONDO, lw=1.2, zorder=4)
        ax.annotate(pl.replace("P_", "").replace("_", " "), (p.lon, p.lat), xytext=(0, 8),
                    textcoords="offset points", ha="center", va="bottom", fontsize=8, color=COLOR_PLANTA,
                    path_effects=HALO, zorder=5)
    for j in COLOR_CENTRO:
        p = ubic.loc[j]
        ax.scatter(p.lon, p.lat, s=260, color=FONDO, edgecolor=APAGADO, lw=1.5, zorder=4)
        ax.text(p.lon, p.lat, j, color=TINTA_3, fontsize=9, ha="center", va="center", zorder=5)

    marcas = []
    for etiqueta, lat, lon, marcador in puntos:
        relleno = FONDO if marcador == "o" else COLOR_OPTIMO
        ax.scatter(lon, lat, s=260 if marcador == "*" else 85, marker=marcador, color=relleno,
                   edgecolor=COLOR_OPTIMO, lw=1.4, zorder=6)
        marcas.append(Line2D([], [], marker=marcador, ls="", markerfacecolor=relleno,
                             markeredgecolor=COLOR_OPTIMO, color=COLOR_OPTIMO,
                             markersize=13 if marcador == "*" else 8, label=etiqueta))

    km5 = 5 / (111.32 * math.cos(math.radians(ubic["lat"].mean())))
    x0, y0 = ax.get_xlim()[0] + 0.01, ax.get_ylim()[0] + 0.01
    ax.plot([x0, x0 + km5], [y0, y0], color=TINTA_2, lw=2, solid_capstyle="butt")
    ax.text(x0 + km5 / 2, y0 + 0.005, "5 km", ha="center", va="bottom", fontsize=8.5, color=TINTA_2)

    ley1 = ax.legend(handles=marcas, loc="lower left", bbox_to_anchor=(0.0, 0.07), frameon=False,
                     fontsize=8.5, title="Ubicaciones", title_fontsize=9, alignment="left")
    ax.add_artist(ley1)
    ax.legend(handles=manijas, loc="lower right", frameon=False, fontsize=8.5,
              title="Candidatos por calle: costo sobre el mejor", title_fontsize=9, alignment="left")

    _titulo(fig, titulo, "▲ plantas · □ supermercados · ○ centros candidatos A–D")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.02)
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Pregunta c): precio de Goyito a partir del cual no conviene el centro propio
# ---------------------------------------------------------------------------


def umbral_goyito(tabla, umbral_global, archivo):
    """Una barra por producto con el precio umbral de Goyito ($ por pallet). El punto marca lo que
    costaría el viaje directo planta -> súper con la tarifa de mercado; la línea, el umbral para
    tercerizar todo a un precio único."""
    from matplotlib.lines import Line2D

    t = tabla.sort_values("umbral").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=150)
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(APAGADO)
    ax.grid(axis="x", color=GRILLA, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TINTA_2, labelsize=9, length=0, pad=6)

    y = np.arange(len(t))
    ax.barh(y, t["umbral"], height=0.55, color=COLOR_SERIE, zorder=2)
    ax.scatter(t["costo_directo_tarifa"], y, s=60, color=FONDO, edgecolor=TINTA, lw=1.6, zorder=3)
    for yi, v in zip(y, t["umbral"]):
        ax.text(v - 15, yi, f"$ {_miles(v)}", ha="right", va="center", fontsize=9, color=FONDO,
                fontweight="bold", zorder=4)
    ax.axvline(umbral_global, color=TINTA_2, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(umbral_global, len(t) - 0.35, f" todo junto: $ {_miles(umbral_global)}", fontsize=8.5,
            color=TINTA_2, va="bottom")
    ax.set_yticks(y, t["producto"])
    ax.set_ylim(-0.6, len(t) - 0.1)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"$ {_miles(v)}"))
    ax.set_xlabel("$ por pallet entregado", color=TINTA_2, fontsize=9.5, labelpad=8)
    ax.legend(handles=[
        Line2D([], [], marker="s", ls="", color=COLOR_SERIE, markersize=9,
               label="Precio de Goyito por debajo del cual conviene tercerizar el producto"),
        Line2D([], [], marker="o", ls="", markerfacecolor=FONDO, markeredgecolor=TINTA, color=TINTA,
               markersize=7, label="Costo del viaje directo a $ 500/km (referencia)"),
    ], loc="lower left", bbox_to_anchor=(-0.01, 1.04), frameon=False, fontsize=8.5)
    _titulo(fig, "¿Desde qué precio conviene dejarle cada producto a Goyito?",
            "Ahorro de la red propia por pallet del producto, con A+C+D abierta")
    fig.subplots_adjust(left=0.13, right=0.97, top=0.7, bottom=0.13)
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Preguntas d) y e): comparación de escenarios
# ---------------------------------------------------------------------------

#: Grupos de rubros del costo, con un color por grupo (categórica, sin rojo/verde juntos).
GRUPOS_COSTO = [
    ("Fijos y operación", ("apertura", "gerente", "operacion"), APAGADO),
    ("Planta → centro", ("tramo1_tercerizado", "tramo1_combustible"), "#2a78d6"),
    ("Centro → súper (combustible)", ("tramo2_combustible",), "#1baf7a"),
    ("Conductores", ("conductores",), "#6250d6"),
    ("Penalidad por km", ("penalidad_km",), "#eb6834"),
]


def comparacion_escenarios(tabla, titulo, subtitulo, archivo):
    """Barras apiladas del costo por grupo de rubros, una por escenario (`tabla` con la columna
    `escenario` y las columnas costo_<rubro> de reportes.fila_resumen), con el total y el CO2."""
    t = tabla.reset_index(drop=True)
    alto = 0.9 + 0.62 * len(t)
    fig, ax = plt.subplots(figsize=(9, alto + 1.5), dpi=150)
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(APAGADO)
    ax.grid(axis="x", color=GRILLA, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TINTA_2, labelsize=9, length=0, pad=6)

    y = np.arange(len(t))[::-1]
    izquierda = np.zeros(len(t))
    for nombre, rubros, color in GRUPOS_COSTO:
        v = sum(t.get(f"costo_{r}", 0) for r in rubros) / 1e6
        if np.allclose(v, 0):
            continue
        ax.barh(y, v, left=izquierda, height=0.56, color=color, label=nombre, edgecolor=FONDO, lw=0.8)
        izquierda = izquierda + np.asarray(v)
    for yi, total, co2 in zip(y, t["costo_total"] / 1e6, t["co2_kg"] / 1000):
        ax.text(total + izquierda.max() * 0.01, yi, f"$ {total:.1f} M · {co2:.1f} t CO₂".replace(".", ","),
                va="center", fontsize=9, color=TINTA, fontweight="bold")
    ax.set_yticks(y, t["escenario"])
    ax.set_xlim(0, izquierda.max() * 1.3)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"$ {v:.0f} M"))
    ax.set_xlabel("Costo por mes", color=TINTA_2, fontsize=9.5, labelpad=8)
    ax.legend(loc="lower left", bbox_to_anchor=(-0.01, 1.02), ncol=3, frameon=False, fontsize=8.5)
    _titulo(fig, titulo, subtitulo)
    fig.subplots_adjust(left=0.2, right=0.97, top=1 - 1.25 / (alto + 1.5), bottom=0.45 / (alto + 1.5) + 0.08)
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Tests de supuestos
# ---------------------------------------------------------------------------


def tests_supuestos(tabla, base, archivo):
    """Variación del costo (sin el término del carbono) de cada test respecto del caso base.
    Las barras de los tests que cambian la configuración óptima llevan su nueva configuración."""
    t = tabla[tabla["test"] != "—"].reset_index(drop=True)
    var = 100 * (t["costo_sin_carbono"] / base["costo"] - 1)
    etiquetas = [f"{f.test} · {f.alternativa}" for f in t.itertuples()]
    alto = 0.32 * len(t) + 1.6
    fig, ax = plt.subplots(figsize=(9, alto), dpi=150)
    fig.patch.set_facecolor(FONDO)
    ax.set_facecolor(FONDO)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(APAGADO)
    ax.grid(axis="x", color=GRILLA, lw=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TINTA_2, labelsize=8.5, length=0, pad=5)

    y = np.arange(len(t))[::-1]
    colores = [COLOR_CENTRO["C"] if c else COLOR_SERIE for c in t["cambia_configuracion"]]
    ax.barh(y, var, height=0.62, color=colores, zorder=2)
    ax.axvline(0, color=TINTA_2, lw=0.8, zorder=3)
    for yi, v, f in zip(y, var, t.itertuples()):
        texto = f"{v:+.1f} %".replace(".", ",") + (f"  → {f.configuracion}" if f.cambia_configuracion else "")
        ax.text(v + (0.6 if v >= 0 else -0.6), yi, texto, va="center", ha="left" if v >= 0 else "right",
                fontsize=8, color=TINTA, path_effects=HALO, zorder=4)
    ax.set_yticks(y, etiquetas)
    lim = max(abs(var.min()), abs(var.max())) * 1.35
    ax.set_xlim(-lim, lim)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:+.0f} %"))
    ax.set_xlabel(f"Variación del costo respecto del caso base ({base['configuracion']}, "
                  f"$ {base['costo'] / 1e6:.1f} M)".replace(".", ","), color=TINTA_2, fontsize=9, labelpad=8)
    _titulo(fig, "¿Cuánto mueve cada supuesto el resultado?",
            f"Azul: sigue óptima {base['configuracion']} · naranja: cambia la configuración")
    fig.subplots_adjust(left=0.33, right=0.97, top=1 - 1.0 / alto, bottom=0.7 / alto)
    fig.savefig(archivo, facecolor=FONDO)
    plt.close(fig)
