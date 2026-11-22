"""
Estilo compartido de las animaciones: la identidad de la página (tinta sobre papel térmico, el amarillo del resaltador,
IBM Plex), la grilla de cada cuadro, las transiciones y los componentes que se repiten (ticket, sellos, tarjetas).

Grilla (unidades de Manim; el cuadro mide 14,2 x 8):
  - arriba, a la altura CAP_Y: el capítulo a la izquierda y el progreso (seis tramos) a la derecha;
  - al medio, la zona útil: ANCHO_UTIL x ALTO_UTIL centrada en CENTRO. Todo lo que se muestra se arma como un grupo y
    se centra ahí con `encuadrar`, así ningún cuadro queda corrido;
  - abajo queda libre la franja de los subtítulos.

Sincronización: cada escena dura PAUSA_INICIO + audio + fin(escena) segundos (montar.py usa los mismos valores), y
`Escena.hasta("frase")` espera hasta que la voz dice esa frase (salida/voz/<escena>.palabras.json).
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import manimpango
import numpy as np
from manim import (DOWN, LEFT, ORIGIN, RIGHT, UP, DashedLine, FadeIn, FadeOut, GrowFromEdge, Polygon, Rectangle,
                   RoundedRectangle, Scene, Text, VGroup, VMobject, config, rate_functions)

AQUI = Path(__file__).parent
VOZ = AQUI / "salida" / "voz"
for ttf in sorted((AQUI / "fuentes").glob("*.ttf")):
    manimpango.register_font(str(ttf))

# Paleta de la página (canasta/web/estilos.css)
PAPEL = "#F1F1EE"
BLANCO = "#FFFFFE"
TINTA = "#16171A"
SUAVE = "#5C5F64"
TENUE = "#8A8D92"
LINEA = "#D6D6D0"
HUNDIDO = "#E4E4DE"
ACENTO = "#F3D03E"
ACENTO_SUAVE = "#FBF2C8"
VERDE = "#2A6B3C"
VERDE_SUAVE = "#D5E6D9"
ROJO = "#B3362A"
ROJO_SUAVE = "#F5E1DD"
NARANJA = "#9C5A0E"
NARANJA_SUAVE = "#F4E6D2"
AZUL = "#1F5FBF"
AZUL_SUAVE = "#DCE6F5"

SANS = "IBM Plex Sans"
MONO = "IBM Plex Mono"
MONO_NEGRITA = "IBM Plex Mono SemiBold"

PAUSA_INICIO = 0.5
PAUSA_FIN = 1.0
PAUSA_FIN_ULTIMA = 3.5          # la última escena se queda en la placa final

CAPITULOS = ["Los datos", "La página", "El modelo", "Un ejemplo", "Casos", "Sensibilidad"]
CAP_Y = 3.36
CENTRO = np.array([0.0, -0.12, 0.0])
ANCHO_UTIL, ALTO_UTIL = 12.4, 5.7

ENTRA = rate_functions.ease_out_cubic
MUEVE = rate_functions.ease_in_out_cubic

config.background_color = PAPEL


def fin(escena: str) -> float:
    from guion import ESCENAS
    return PAUSA_FIN_ULTIMA if escena == ESCENAS[-1]["id"] else PAUSA_FIN


_TEXTOS: dict = {}


def texto(s: str, tam: float = 36, color: str = TINTA, negrita: bool = False, mono: bool = False, **kw) -> Text:
    """Text con las fuentes del proyecto. tam en puntos de Manim (36 ~ cuerpo grande en 1080p). Se guarda una copia de
    cada texto ya armado: los que se redibujan en cada cuadro (ejes, contadores) no pasan otra vez por Pango."""
    clave = (s, tam, color, negrita, mono, tuple(sorted(kw.items())))
    if clave not in _TEXTOS:
        if mono:
            t = Text(s, font=MONO_NEGRITA if negrita else MONO, font_size=tam, color=color, **kw)
        else:
            t = Text(s, font=SANS, weight="SEMIBOLD" if negrita else "NORMAL", font_size=tam, color=color, **kw)
        _TEXTOS[clave] = t
    return _TEXTOS[clave].copy()


def miles(n: float, decimales: int = 0) -> str:
    """Número con punto de miles y coma decimal, como en Argentina."""
    s = f"{n:,.{decimales}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def encuadrar(m, ancho: float = ANCHO_UTIL, alto: float = ALTO_UTIL, centro=CENTRO):
    """Achica el grupo si no entra en la zona útil y lo centra en ella."""
    k = min(1.0, ancho / max(m.width, 1e-6), alto / max(m.height, 1e-6))
    if k < 1:
        m.scale(k)
    return m.move_to(centro)


def tarjeta(ancho: float, alto: float, color: str = BLANCO, borde: str = LINEA, radio: float = 0.14,
            grosor: float = 1.5) -> RoundedRectangle:
    return RoundedRectangle(width=ancho, height=alto, corner_radius=radio, fill_color=color, fill_opacity=1,
                            stroke_color=borde, stroke_width=grosor)


def en_tarjeta(contenido, color: str = BLANCO, borde: str = LINEA, pad: float = 0.35, ancho: float | None = None,
               alto: float | None = None) -> VGroup:
    """El contenido centrado en una tarjeta que lo envuelve con `pad` de margen (o del tamaño pedido)."""
    t = tarjeta(ancho or contenido.width + 2 * pad, alto or contenido.height + 2 * pad, color, borde)
    contenido.move_to(t)
    g = VGroup(t, contenido)
    g.fondo, g.contenido = t, contenido
    return g


def tilde(color: str = VERDE, tam: float = 0.26, grosor: float = 6) -> VMobject:
    m = VMobject(stroke_color=color, stroke_width=grosor)
    m.set_points_as_corners([[-0.5, 0.02, 0], [-0.15, -0.36, 0], [0.5, 0.38, 0]])
    return m.scale(tam)


def cruz(color: str = ROJO, tam: float = 0.22, grosor: float = 6) -> VGroup:
    a = VMobject(stroke_color=color, stroke_width=grosor)
    a.set_points_as_corners([[-0.5, -0.5, 0], [0.5, 0.5, 0]])
    b = VMobject(stroke_color=color, stroke_width=grosor)
    b.set_points_as_corners([[-0.5, 0.5, 0], [0.5, -0.5, 0]])
    return VGroup(a, b).scale(tam)


def sello(ok: bool, s: str, tam: float = 24) -> VGroup:
    """Una píldora: tilde verde y el texto, o cruz roja y el texto."""
    color, fondo = (VERDE, VERDE_SUAVE) if ok else (ROJO, ROJO_SUAVE)
    icono = tilde(color) if ok else cruz(color)
    t = texto(s, tam, color=color, negrita=True)
    fila = VGroup(icono, t).arrange(RIGHT, buff=0.16)
    caja = RoundedRectangle(width=fila.width + 0.5, height=fila.height + 0.28, corner_radius=(fila.height + 0.28) / 2,
                            fill_color=fondo, fill_opacity=1, stroke_width=0)
    fila.move_to(caja)
    return VGroup(caja, fila)


def ticket(lineas: list, ancho: float = 4.4, tam: float = 21, total: tuple[str, str] | None = None,
           titulo: str | None = None) -> VGroup:
    """Un ticket de papel térmico: papel blanco con el borde de abajo dentado y renglones en mono. Cada renglón es un
    texto centrado, un par (izquierda, derecha) o "---". Devuelve VGroup(sombra, papel, renglones)."""
    interior = ancho - 0.7
    renglones = VGroup()
    if titulo:
        renglones.add(texto(titulo, tam + 5, negrita=True, mono=True))
    for ln in lineas:
        if isinstance(ln, tuple):
            izq, der = texto(ln[0], tam, mono=True), texto(ln[1], tam, mono=True)
            der.next_to(izq, RIGHT, buff=interior - izq.width - der.width).align_to(izq, DOWN)
            renglones.add(VGroup(izq, der))
        elif ln == "---":
            renglones.add(DashedLine(LEFT * interior / 2, RIGHT * interior / 2, color=TENUE, dash_length=0.06,
                                     stroke_width=2))
        else:
            renglones.add(texto(ln, tam, mono=True))
    if total:
        izq, der = texto(total[0], tam + 4, negrita=True, mono=True), texto(total[1], tam + 4, negrita=True, mono=True)
        der.next_to(izq, RIGHT, buff=interior - izq.width - der.width).align_to(izq, DOWN)
        marca = RoundedRectangle(width=der.width + 0.18, height=der.height + 0.14, corner_radius=0.03,
                                 fill_color=ACENTO, fill_opacity=1, stroke_width=0).move_to(der)
        fila = VGroup(marca, izq, der)
        fila.marca = marca
        renglones.add(fila)
    renglones.arrange(DOWN, buff=0.17)
    for r in renglones:                                  # todos centrados en el papel (los pares ya ocupan el ancho)
        r.set_x(0)
    renglones.move_to(ORIGIN)
    alto = renglones.height + 0.75
    n = 22
    paso = ancho / n
    x0, y0 = -ancho / 2, -alto / 2
    dientes = []
    for k in range(n):
        dientes += [[x0 + k * paso, y0, 0], [x0 + (k + 0.5) * paso, y0 - 0.1, 0]]
    papel = Polygon([-ancho / 2, alto / 2, 0], [ancho / 2, alto / 2, 0], [ancho / 2, y0, 0], *reversed(dientes),
                    fill_color=BLANCO, fill_opacity=1, stroke_width=0)
    sombra = papel.copy().set_fill(TINTA, 0.08).set_stroke(width=0).shift(DOWN * 0.07 + RIGHT * 0.05)
    grupo = VGroup(sombra, papel, renglones)
    grupo.papel, grupo.renglones = VGroup(sombra, papel), renglones
    return grupo


def cabecera(n: int) -> VGroup:
    """El capítulo n (1..6) arriba a la izquierda: la marca amarilla, el número y el nombre."""
    num = texto(f"{n:02d}", 22, color=TENUE, negrita=True, mono=True)
    nom = texto(CAPITULOS[n - 1], 26, negrita=True)
    fila = VGroup(num, nom).arrange(RIGHT, buff=0.22)
    nom.align_to(num, DOWN).shift(DOWN * 0.005)
    marca = RoundedRectangle(width=0.1, height=0.36, corner_radius=0.03, fill_color=ACENTO, fill_opacity=1,
                             stroke_width=0)
    g = VGroup(marca, fila).arrange(RIGHT, buff=0.2)
    return g.move_to([-6.5 + g.width / 2, CAP_Y, 0])


def progreso(hasta: int) -> VGroup:
    """Seis tramos arriba a la derecha; los primeros `hasta` en tinta. .tramos y .llenos para animar."""
    tramos = VGroup(*[RoundedRectangle(width=0.46, height=0.07, corner_radius=0.035, fill_color=LINEA, fill_opacity=1,
                                       stroke_width=0) for _ in CAPITULOS]).arrange(RIGHT, buff=0.09)
    tramos.move_to([6.5 - tramos.width / 2, CAP_Y, 0])
    llenos = VGroup(*[t.copy().set_fill(TINTA) for t in tramos[:hasta]])
    g = VGroup(tramos, llenos)
    g.tramos, g.llenos = tramos, llenos
    return g


def _normal(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return re.sub(r"[^a-z0-9ñ ]", "", "".join(c for c in s if unicodedata.category(c) != "Mn"))


class Escena(Scene):
    """Escena sincronizada con su locución. Subclases: ID = id de la escena en guion.py, CAP = número de capítulo."""

    ID = ""
    CAP = 0

    def setup(self):
        self.palabras = json.loads((VOZ / f"{self.ID}.palabras.json").read_text(encoding="utf-8"))
        self.duracion = json.loads((VOZ / "duraciones.json").read_text(encoding="utf-8"))[self.ID]
        self.total = PAUSA_INICIO + self.duracion + fin(self.ID)
        self.barra = None
        self.cab = None

    # --- tiempo ------------------------------------------------------------------------------------------------------
    def cuando(self, frase: str, despues: float = 0.0) -> float:
        """Segundo de la escena en que la voz empieza a decir `frase` (la primera vez, después de `despues`)."""
        objetivo = _normal(frase).split()
        ws = [_normal(p["w"]) for p in self.palabras]
        for i in range(len(ws) - len(objetivo) + 1):
            if ws[i:i + len(objetivo)] == objetivo and self.palabras[i]["t"] + PAUSA_INICIO >= despues:
                return self.palabras[i]["t"] + PAUSA_INICIO
        raise KeyError(f"{self.ID}: no se dice «{frase}»")

    @property
    def ahora(self) -> float:
        return self.renderer.time

    def hasta(self, momento: float | str, antes: float = 0.0):
        """Espera hasta un segundo de la escena o hasta que la voz dice una frase (menos `antes` segundos)."""
        t = self.cuando(momento) if isinstance(momento, str) else momento
        if t - antes > self.ahora + 1e-3:
            self.wait(t - antes - self.ahora)

    # --- capítulos y transiciones ---------------------------------------------------------------------------------
    def entrar(self):
        """El progreso tal como lo dejó la escena anterior, el tramo nuevo que se llena y el nombre del capítulo."""
        self.barra = progreso(self.CAP - 1)
        nuevo = self.barra.tramos[self.CAP - 1].copy().set_fill(TINTA)
        self.cab = cabecera(self.CAP)
        anims = [GrowFromEdge(nuevo, LEFT), FadeIn(self.cab, shift=RIGHT * 0.15)]
        if self.CAP == 1:
            anims.append(FadeIn(self.barra))
        else:
            self.add(self.barra)
        self.play(*anims, run_time=0.6, rate_func=ENTRA)
        self.remove(nuevo)                  # pasa a ser parte de la barra (si no, queda suelto y se va con el resto)
        self.barra.llenos.add(nuevo)
        self.barra.add(nuevo)
        self.add(self.barra)

    def mostrar(self, *ms, rt: float = 0.55, shift=UP * 0.25, lag: float = 0.0):
        if lag:
            from manim import LaggedStart
            self.play(LaggedStart(*[FadeIn(m, shift=shift) for m in ms], lag_ratio=lag), run_time=rt, rate_func=ENTRA)
        else:
            self.play(*[FadeIn(m, shift=shift) for m in ms], run_time=rt, rate_func=ENTRA)

    def cambiar(self, fuera, dentro=None, rt: float = 0.45):
        """La transición de un cuadro al siguiente: lo viejo sube y se va; lo nuevo sube y aparece."""
        fuera = [f for f in (fuera if isinstance(fuera, (list, tuple)) else [fuera]) if f is not None]
        if fuera:
            self.play(*[FadeOut(f, shift=UP * 0.25) for f in fuera], run_time=rt, rate_func=rate_functions.ease_in_cubic)
        if dentro is not None:
            self.mostrar(*(dentro if isinstance(dentro, (list, tuple)) else [dentro]))

    def terminar(self, quedarse: bool = False):
        """Cierra la escena justo a su duración total. Se va todo menos el progreso, que sigue en la escena siguiente."""
        resto = self.total - self.ahora
        quedan = [m for m in self.mobjects if m is not self.barra]
        if not quedarse and quedan and resto > 0.6:
            self.wait(resto - 0.5)
            self.play(*[FadeOut(m) for m in quedan], run_time=0.5)
        elif resto > 0:
            self.wait(resto)


__all__ = [n for n in dir() if not n.startswith("__")]
