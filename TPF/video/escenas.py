"""
Las escenas animadas del video (Manim). La escena 3 (la página) es la grabación de grabar.py, compuesta por montar.py
dentro del marco que dibuja E3Marco.

Render (desde TPF/video):
  python -m manim -qh --media_dir salida/manim escenas.py E1Pregunta E2Datos E3Marco E4Modelo E5Ejemplo E6Casos E7Cierre

Cada escena dura lo mismo que su locución más las pausas (estilo.Escena), y sus animaciones arrancan cuando la voz
dice la frase correspondiente (self.hasta("frase"), escrita como se dice). Todo cuadro se arma como un grupo y se centra
en la zona útil (estilo.encuadrar). Las cifras son las del informe.
"""

from __future__ import annotations

import json

import numpy as np
from manim import (DOWN, LEFT, ORIGIN, PI, RIGHT, UP, UR, AnimationGroup, Arrow, Circle, Create, DashedLine, Dot, FadeIn,
                   FadeOut, GrowFromCenter, GrowFromEdge, Indicate, LaggedStart, Line, MathTex, Polygon, Rectangle,
                   RoundedRectangle, Transform, ValueTracker, VGroup, VMobject, Write, always_redraw, rate_functions,
                   smooth)

from estilo import (ACENTO, ACENTO_SUAVE, AQUI, AZUL, AZUL_SUAVE, BLANCO, CENTRO, ENTRA, HUNDIDO, LINEA, MUEVE,
                    NARANJA, NARANJA_SUAVE, ROJO, ROJO_SUAVE, SUAVE, TENUE, TINTA, VERDE, VERDE_SUAVE, Escena,
                    cabecera, cruz, en_tarjeta, encuadrar, miles, progreso, sello, tarjeta, texto, ticket, tilde)

MathTex.set_default(color=TINTA)


def columna(*ms, buff: float = 0.2, alinear=LEFT) -> VGroup:
    return VGroup(*ms).arrange(DOWN, buff=buff, aligned_edge=alinear)


def barra_h(valor: float, maximo: float, largo: float, color: str, alto: float = 0.46) -> Rectangle:
    return Rectangle(width=max(valor / maximo * largo, 0.02), height=alto, fill_color=color, fill_opacity=1,
                     stroke_width=0)


def tabla_barras(filas: list[tuple[str, float, str, str]], largo: float, tam: float = 26, alto: float = 0.46,
                 buff: float = 0.26, mono_etq: bool = False) -> VGroup:
    """Filas (etiqueta, valor, texto del valor, color) con la etiqueta a la derecha de una columna fija, la barra
    desde el mismo origen y el valor después de la barra. Cada fila es VGroup(etiqueta, barra, valor)."""
    maximo = max(v for _, v, _, _ in filas)
    etqs = [texto(e, tam, mono=mono_etq, negrita=mono_etq) for e, _, _, _ in filas]
    ancho_etq = max(e.width for e in etqs)
    g = VGroup()
    for i, ((_, v, vt, color), etq) in enumerate(zip(filas, etqs)):
        y = -i * (alto + buff)
        barra = barra_h(v, maximo, largo, color, alto)
        barra.move_to([0, y, 0], aligned_edge=LEFT)
        etq.move_to([-0.3, y, 0], aligned_edge=RIGHT)
        val = texto(vt, tam, mono=True).next_to(barra, RIGHT, buff=0.22)
        g.add(VGroup(etq, barra, val))
    g.ancho_etq = ancho_etq
    return g


# ======================================================================================================================
class E1Pregunta(Escena):
    ID = "e1_pregunta"

    def construct(self):
        anio = texto("1945", 170, negrita=True, mono=True)
        quien = texto("George Stigler · economista", 34, color=SUAVE)
        cabeza = columna(anio, quien, buff=0.32, alinear=ORIGIN)
        encuadrar(cabeza)
        arriba = anio.get_center()
        anio.move_to(CENTRO)                                  # solo, el año va al centro; con el nombre, sube
        self.play(FadeIn(anio, shift=UP * 0.3), run_time=0.9, rate_func=ENTRA)
        self.hasta("yorch", antes=0.1)
        self.play(anio.animate.move_to(arriba), FadeIn(quien, shift=UP * 0.15), run_time=0.6, rate_func=MUEVE)

        # La pregunta, debajo del año; después la fórmula, y todo el bloque se recentra.
        pregunta = texto("¿Cuál es la dieta más barata\nque cubre todo lo que necesita una persona?", 44, negrita=True,
                         line_spacing=1.15)
        formula = MathTex(r"\min \sum_j c_j\, x_j", r"\quad\text{sujeto a}\quad", r"\sum_j a_{ij}\, x_j \;\geq\; b_i",
                          font_size=50)
        formula[1].set_color(SUAVE)
        nota = texto("el problema de la dieta, un clásico de la programación lineal", 26, color=SUAVE)
        bloque = columna(formula, nota, buff=0.3, alinear=ORIGIN)

        cabeza_chica = cabeza.copy().scale(0.42)
        paso1 = encuadrar(columna(cabeza_chica, pregunta, buff=0.7, alinear=ORIGIN))
        self.hasta("cual es la dieta", antes=0.35)
        self.play(Transform(cabeza, cabeza_chica), run_time=0.7, rate_func=MUEVE)
        self.play(FadeIn(pregunta, shift=UP * 0.2), run_time=0.7, rate_func=ENTRA)

        self.hasta("su respuesta", antes=0.2)
        destino = columna(cabeza_chica.copy(), pregunta.copy(), bloque, buff=0.7, alinear=ORIGIN)
        encuadrar(destino)
        self.play(cabeza.animate.move_to(destino[0]), pregunta.animate.move_to(destino[1]), run_time=0.7,
                  rate_func=MUEVE)
        self.play(FadeIn(bloque, shift=UP * 0.2), run_time=0.7, rate_func=ENTRA)

        # Harina, repollo y espinaca, todo el año.
        platos = VGroup()
        for nombre in ("harina", "repollo", "espinaca"):
            plato = Circle(radius=1.2, fill_color=BLANCO, fill_opacity=1, stroke_color=LINEA, stroke_width=3)
            borde = Circle(radius=0.9, stroke_color=HUNDIDO, stroke_width=3)
            platos.add(VGroup(plato, borde, texto(nombre, 34, negrita=True)))
        platos.arrange(RIGHT, buff=0.8)
        sello_ = texto("todo el año", 42, negrita=True, color=ROJO)
        marco = RoundedRectangle(width=sello_.width + 0.55, height=sello_.height + 0.4, corner_radius=0.1,
                                 stroke_color=ROJO, stroke_width=5)
        estampa = VGroup(marco, sello_)
        cuadro = encuadrar(columna(platos, estampa, buff=0.6, alinear=ORIGIN))
        estampa.rotate(-0.1)
        self.hasta("pero era una dieta", antes=0.2)
        self.cambiar([cabeza, pregunta, bloque])
        for p, nombre in zip(platos, ("harina", "repollo", "espinaca")):
            self.hasta(nombre, antes=0.15)
            self.play(GrowFromCenter(p), run_time=0.4, rate_func=ENTRA)
        self.hasta("todo el año", antes=0.1)
        self.play(FadeIn(estampa, scale=1.5), run_time=0.35, rate_func=ENTRA)

        # El título, con el ticket que se imprime.
        titulo = texto("Canasta saludable\nal menor precio", 68, negrita=True, line_spacing=1.0)
        bajada = texto("La misma pregunta,\ncon los precios de hoy.", 32, color=SUAVE, line_spacing=1.15)
        izquierda = columna(titulo, bajada, buff=0.45)
        tk = ticket([("Precios", "SEPA, de hoy"), ("Metas por persona", "37"), ("Envases", "enteros"),
                     ("Súper", "a pocas cuadras"), "---"], ancho=4.9, tam=21, titulo="CANASTA SALUDABLE",
                    total=("TOTAL", "EL MÁS BAJO"))
        portada = encuadrar(VGroup(izquierda, tk).arrange(RIGHT, buff=1.3))
        self.hasta("nosotros nos hicimos", antes=0.3)
        self.cambiar([platos, estampa])
        self.play(FadeIn(titulo, shift=UP * 0.25), FadeIn(tk.papel, shift=DOWN * 0.15), run_time=0.6, rate_func=ENTRA)
        self.hasta("con los precios de hoy", antes=0.2)
        self.play(FadeIn(bajada, shift=UP * 0.15),
                  LaggedStart(*[FadeIn(r, shift=DOWN * 0.06) for r in tk.renglones[:-1]], lag_ratio=0.25),
                  run_time=1.8)
        self.hasta("supermercado de la esquina", antes=0.2)
        total = tk.renglones[-1]
        self.play(GrowFromEdge(total.marca, LEFT), FadeIn(total[1], shift=DOWN * 0.06), run_time=0.4, rate_func=ENTRA)
        self.play(FadeIn(total[2]), run_time=0.3)              # el texto, encima del amarillo
        self.terminar()


# ======================================================================================================================
class E2Datos(Escena):
    ID = "e2_datos"
    CAP = 1

    def construct(self):
        self.entrar()

        # El mapa: cada punto es una sucursal real de la base (datos/sepa/dim_tienda.parquet).
        puntos = json.loads((AQUI / "salida" / "datos" / "sucursales.json").read_text())
        escala, lat0 = 0.158, -38.0
        k = np.cos(np.radians(lat0))
        lotes: dict[int, VGroup] = {}
        for lon, lat in puntos:
            lotes.setdefault(int((lat + 56) // 0.9), VGroup()).add(
                Dot([(lon + 64.0) * k * escala, (lat - lat0) * escala, 0], radius=0.03, color=TINTA,
                    fill_opacity=0.85))
        orden = [lotes[c] for c in sorted(lotes, reverse=True)]                    # de norte a sur
        mapa = VGroup(*orden)
        pie = texto("cada punto, una sucursal", 22, color=SUAVE)
        izquierda = columna(mapa, pie, buff=0.25, alinear=ORIGIN)

        filas = [(8309213, "precios", "ocho millones"), (2651, "sucursales", "dos mil seiscientas"),
                 (27949, "productos con información nutricional", "veintiocho mil")]
        bloques = VGroup()
        for valor, etq, _ in filas:
            bloques.add(columna(texto(miles(valor), 64, negrita=True, mono=True), texto(etq, 26, color=SUAVE),
                                buff=0.1))
        bloques.arrange(DOWN, buff=0.55, aligned_edge=LEFT)
        cuadro = encuadrar(VGroup(izquierda, bloques).arrange(RIGHT, buff=1.6))

        self.hasta("sistema sepa", antes=0.4)
        self.play(LaggedStart(*[FadeIn(l, scale=1.5) for l in orden], lag_ratio=0.1), run_time=2.6)
        self.play(FadeIn(pie), run_time=0.4)

        for (valor, _, frase), b in zip(filas, bloques):
            v = ValueTracker(0)
            num, etq = b
            ancla = num.get_left()
            vivo = always_redraw(lambda v=v, ancla=ancla: texto(miles(v.get_value()), 64, negrita=True, mono=True)
                                 .move_to(ancla, aligned_edge=LEFT))
            self.hasta(frase, antes=0.35)
            self.add(vivo)
            self.play(v.animate.set_value(valor), FadeIn(etq, shift=UP * 0.1), run_time=1.1,
                      rate_func=rate_functions.ease_out_cubic)
            vivo.clear_updaters()
            b.vivo = vivo

        # De cada producto, tres cosas.
        nutrientes = VGroup()
        for n, w, c in (("proteína", 0.9, VERDE), ("hierro", 0.55, NARANJA), ("calcio", 0.35, AZUL),
                        ("fibra", 0.75, ACENTO)):
            nom = texto(n, 22, color=SUAVE)
            nom.move_to([0, -len(nutrientes) * 0.4, 0], aligned_edge=LEFT)
            nutrientes.add(VGroup(nom, barra_h(w, 1, 1.5, c, 0.18).move_to([1.25, nom.get_y(), 0],
                                                                         aligned_edge=LEFT)))
        t1 = columna(texto("Qué aporta", 30, negrita=True), nutrientes,
                     texto("33 nutrientes cada 100 g", 21, color=SUAVE), buff=0.32)
        precio = VGroup(RoundedRectangle(width=2.4, height=1.0, corner_radius=0.08, fill_color=ACENTO,
                                         fill_opacity=1, stroke_width=0), texto("$1.499", 44, negrita=True, mono=True))
        precio[1].move_to(precio[0])
        t2 = columna(texto("Cuánto cuesta", 30, negrita=True), precio, texto("en cada sucursal", 21, color=SUAVE),
                     buff=0.32)
        aptos = VGroup()
        for nombre, ok in (("celíacos", True), ("veganos", True), ("alérgicos al maní", False)):
            aptos.add(VGroup(tilde() if ok else cruz(), texto(nombre, 23)).arrange(RIGHT, buff=0.2))
        aptos.arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        t3 = columna(texto("Para quién es apto", 30, negrita=True), aptos, texto("restricciones estrictas", 21,
                                                                                 color=SUAVE), buff=0.32)
        alto = max(t.height for t in (t1, t2, t3)) + 0.9
        ancho = max(t.width for t in (t1, t2, t3)) + 0.9          # el contenido más ancho, con margen
        tarjetas = VGroup(*[en_tarjeta(t, ancho=ancho, alto=alto) for t in (t1, t2, t3)]).arrange(RIGHT, buff=0.3)
        for tj in tarjetas:                                  # el contenido arriba a la izquierda de su tarjeta
            tj.contenido.align_to(tj.fondo, UP).shift(DOWN * 0.45).align_to(tj.fondo, LEFT).shift(RIGHT * 0.4)
        titulo = texto("De cada producto sabemos", 36, negrita=True)
        cuadro2 = encuadrar(columna(titulo, tarjetas, buff=0.55, alinear=ORIGIN))

        self.hasta("asi de cada producto", antes=0.3)
        self.cambiar([izquierda, *[VGroup(b[1], b.vivo) for b in bloques]], titulo)
        for tj, frase in zip(tarjetas, ("que aporta", "cuanto cuesta", "para quien es apto")):
            self.hasta(frase, antes=0.2)
            self.mostrar(tj, rt=0.5)
        self.terminar()


# ======================================================================================================================
# La escena 3: el marco de la página. montar.py pega la grabación en el hueco de la ventana (VENTANA, en píxeles).
VENTANA = {"x": 232, "y": 196, "w": 1456, "h": 818, "barra": 44, "radio": 14}


def px(x: float, y: float) -> np.ndarray:
    """De píxeles de 1920 x 1080 a unidades de Manim."""
    return np.array([(x - 960) / 135, (540 - y) / 135, 0])


class E3Marco(Escena):
    ID = "e3_pagina"
    CAP = 2

    def construct(self):
        v = VENTANA
        x0, y0, w, h, b = v["x"], v["y"], v["w"], v["h"], v["barra"]
        centro = (px(x0, y0 - b) + px(x0 + w, y0 + h)) / 2
        ventana = RoundedRectangle(width=w / 135, height=(h + b) / 135, corner_radius=v["radio"] / 135,
                                   fill_color=BLANCO, fill_opacity=1, stroke_color=LINEA, stroke_width=1.5)
        ventana.move_to(centro)
        sombra = ventana.copy().set_fill(TINTA, 0.07).set_stroke(width=0).shift(DOWN * 0.08)
        barra = Line(px(x0, y0), px(x0 + w, y0), color=LINEA, stroke_width=1.5)
        puntos = VGroup(*[Dot(radius=0.055, color=c) for c in (LINEA, LINEA, LINEA)]).arrange(RIGHT, buff=0.12)
        puntos.move_to(px(x0 + 46, y0 - b / 2))
        url = texto("nazarenofolica.github.io/Optimizacion_TPS", 17, color=SUAVE, mono=True)
        caja_url = RoundedRectangle(width=url.width + 0.5, height=url.height + 0.14, corner_radius=(url.height + 0.14) / 2, fill_color=HUNDIDO,
                                    fill_opacity=1, stroke_width=0).move_to(px(960, y0 - b / 2))
        url.move_to(caja_url)
        marco = VGroup(sombra, ventana, barra, puntos, caja_url, url)
        self.entrar()
        self.play(FadeIn(marco), run_time=0.5)
        self.terminar()


# ======================================================================================================================
class E4Modelo(Escena):
    ID = "e4_modelo"
    CAP = 3

    def construct(self):
        self.entrar()
        pregunta = encuadrar(texto("¿Cómo decide?", 84, negrita=True))
        self.mostrar(pregunta, rt=0.6)

        # --- Dos objetivos que se pelean, y cómo los ordenamos
        def pildora(s, color, fondo):
            t = texto(s, 40, negrita=True, color=color)
            return en_tarjeta(t, fondo, color, ancho=4.3, alto=1.3)

        bien = pildora("comer bien", VERDE, VERDE_SUAVE)
        poco = pildora("gastar poco", NARANJA, NARANJA_SUAVE)
        vs = texto("vs.", 32, color=TENUE, negrita=True)
        duelo = VGroup(bien, vs, poco).arrange(RIGHT, buff=0.55)
        lam = MathTex(r"\min\;\; \text{costo} \;+\; \lambda \cdot \text{(lo que falta)}", font_size=52)
        orden = VGroup(texto("1.º", 30, negrita=True, mono=True, color=VERDE),
                       texto("2.º", 30, negrita=True, mono=True, color=NARANJA))
        lex = MathTex(r"\operatorname{lex\,min}\;\Big(\;", r"\Phi", r",\;\; \sum_p \pi_p\, x_p", r"\;\Big)",
                      font_size=60)
        lex[1].set_color(VERDE)
        lex[2].set_color(NARANJA)
        nombre_lex = texto("metas lexicográficas: primero una, después la otra", 26, color=SUAVE)
        abajo = columna(lex, nombre_lex, buff=0.3, alinear=ORIGIN)
        cuadro = encuadrar(columna(duelo, abajo, buff=1.0, alinear=ORIGIN))
        lam.move_to(abajo)
        for o, p in zip(orden, (bien, poco)):
            o.next_to(p, UP, buff=0.2)

        self.hasta("hay dos objetivos", antes=0.3)
        self.cambiar(pregunta)
        self.hasta("comer bien", antes=0.2)
        self.play(FadeIn(bien, shift=RIGHT * 0.3), run_time=0.5, rate_func=ENTRA)
        self.hasta("gastar poco", antes=0.2)
        self.play(FadeIn(poco, shift=LEFT * 0.3), FadeIn(vs), run_time=0.5, rate_func=ENTRA)
        self.play(bien.animate.shift(LEFT * 0.25), poco.animate.shift(RIGHT * 0.25), run_time=0.5,
                  rate_func=rate_functions.there_and_back)

        self.hasta("en lugar de ponerle", antes=0.2)
        self.play(Write(lam), run_time=1.0)
        tacha = Line(lam.get_left() + LEFT * 0.15, lam.get_right() + RIGHT * 0.15, color=ROJO, stroke_width=7)
        self.hasta("los ordenamos", antes=0.2)
        self.play(Create(tacha), run_time=0.35)
        flecha = Arrow(LEFT * 0.35, RIGHT * 0.35, buff=0, color=TINTA, stroke_width=5,
                       max_tip_length_to_length_ratio=0.35).move_to(vs)
        self.hasta("primero uno", antes=0.1)
        self.play(FadeOut(vs), FadeIn(flecha), FadeIn(orden[0], shift=DOWN * 0.1), run_time=0.45)
        self.hasta("y despues el otro", antes=0.1)
        self.play(FadeIn(orden[1], shift=DOWN * 0.1), run_time=0.4)
        self.hasta("se llaman", antes=0.2)
        self.play(FadeOut(VGroup(lam, tacha), shift=UP * 0.2), run_time=0.4)
        self.play(FadeIn(lex, shift=UP * 0.2), run_time=0.6, rate_func=ENTRA)
        self.play(FadeIn(nombre_lex), run_time=0.4)

        # --- Las dos etapas
        def etapa(n, nombre, como, color):
            c = columna(texto(f"ETAPA {n}", 22, negrita=True, mono=True, color=color), texto(nombre, 38, negrita=True),
                        texto(como, 23, color=SUAVE), buff=0.1)
            return en_tarjeta(c, ancho=5.4, alto=1.85)

        e1 = etapa(1, "Cumplir las metas", "programa lineal, sin mirar precios", VERDE)
        e2 = etapa(2, "Lo más barato", "programa entero, con precios", NARANJA)
        for e in (e1, e2):
            e.contenido.align_to(e.fondo, LEFT).shift(RIGHT * 0.4)
        conecta = Arrow(LEFT * 0.4, RIGHT * 0.4, buff=0, color=TINTA, stroke_width=5,
                        max_tip_length_to_length_ratio=0.3)
        arriba = VGroup(e1, conecta, e2).arrange(RIGHT, buff=0.3)

        # Detalle de la etapa 1: la pista de una meta con su rango y los dos desvíos.
        pista = Line(LEFT * 4.6, RIGHT * 4.6, stroke_width=18, color=HUNDIDO)
        rango = Line(pista.point_from_proportion(0.34), pista.point_from_proportion(0.66), stroke_width=18,
                     color=VERDE_SUAVE)
        marcas = VGroup(*[Line(p + DOWN * 0.26, p + UP * 0.26, color=SUAVE, stroke_width=4)
                          for p in (rango.get_start(), rango.get_end())])
        L = MathTex("L", font_size=42).next_to(marcas[0], UP, buff=0.14)
        U = MathTex("U", font_size=42).next_to(marcas[1], UP, buff=0.14)
        nombre_rango = texto("rango de la meta", 24, color=VERDE).next_to(VGroup(L, U), UP, buff=0.14)
        bajo = Dot(pista.point_from_proportion(0.1), radius=0.17, color=ROJO)
        alto_ = Dot(pista.point_from_proportion(0.86), radius=0.17, color=NARANJA)
        f_def = Arrow(bajo.get_center() + DOWN * 0.55, rango.get_start() + DOWN * 0.55, buff=0, color=ROJO,
                      stroke_width=5, max_tip_length_to_length_ratio=0.2)
        f_exc = Arrow(rango.get_end() + DOWN * 0.55, alto_.get_center() + DOWN * 0.55, buff=0, color=NARANJA,
                      stroke_width=5, max_tip_length_to_length_ratio=0.2)
        d_def = MathTex(r"\Delta^{\mathrm{DEF}}", font_size=44, color=ROJO).next_to(f_def, DOWN, buff=0.28)
        d_exc = MathTex(r"\Delta^{\mathrm{EXC}}", font_size=44, color=NARANJA).next_to(f_exc, DOWN, buff=0.28)
        d_def2 = MathTex(r"\Delta^{\mathrm{DEF}} = 30\,\%", font_size=44, color=ROJO).next_to(f_def, DOWN, buff=0.28)
        d_exc2 = MathTex(r"\Delta^{\mathrm{EXC}} = 20\,\%", font_size=44, color=NARANJA).next_to(f_exc, DOWN,
                                                                                                 buff=0.28)
        phi = MathTex(r"\min\;\; \Phi \;=\; \sum_{\text{metas}} w \left(\Delta^{\mathrm{DEF}} + "
                      r"\Delta^{\mathrm{EXC}}\right)", font_size=50)
        diagrama = VGroup(pista, rango, marcas, L, U, nombre_rango, bajo, alto_, f_def, f_exc, d_def, d_exc)
        det1 = columna(diagrama, phi, buff=0.45, alinear=ORIGIN)

        # Detalle de la etapa 2: tres renglones, fórmula y lo que quiere decir.
        renglones = VGroup()
        for tex, dice in ((r"\min \sum_p \pi_p\, x_p", "la compra más barata"),
                          (r"x_p \in \{0, 1, 2, \dots\}", "envases enteros"),
                          (r"\Delta \;\le\; \Delta^{*}_{\text{etapa 1}}", "ninguna meta queda peor")):
            renglones.add(VGroup(MathTex(tex, font_size=46), texto(dice, 26, color=SUAVE)))
        ancho_f = max(r[0].width for r in renglones)
        for i, r in enumerate(renglones):
            r[0].move_to([0, -i * 0.95, 0], aligned_edge=LEFT)
            r[1].move_to([ancho_f + 0.9, -i * 0.95, 0], aligned_edge=LEFT)
        det2 = renglones

        pantalla = encuadrar(columna(arriba, det1, buff=0.6, alinear=ORIGIN))
        det2.move_to(det1)
        e2.set_opacity(0.3)

        self.hasta("en la primera", antes=0.3)
        self.cambiar([duelo, orden, flecha, lex, nombre_lex])
        self.play(LaggedStart(FadeIn(e1, shift=UP * 0.2), FadeIn(conecta), FadeIn(e2, shift=UP * 0.2),
                              lag_ratio=0.2), run_time=0.8, rate_func=ENTRA)
        self.hasta("cada meta tiene un rango", antes=0.2)
        self.play(Create(pista), run_time=0.4)
        self.play(Create(rango), FadeIn(marcas), FadeIn(L), FadeIn(U), FadeIn(nombre_rango), run_time=0.6)
        self.hasta("quedar por debajo", antes=0.1)
        self.play(FadeIn(bajo, scale=1.6), GrowFromEdge(f_def, LEFT), FadeIn(d_def), run_time=0.6)
        self.hasta("o por encima", antes=0.1)
        self.play(FadeIn(alto_, scale=1.6), GrowFromEdge(f_exc, LEFT), FadeIn(d_exc), run_time=0.6)
        self.hasta("medido en porcentaje", antes=0.1)
        self.play(Transform(d_def, d_def2), Transform(d_exc, d_exc2), run_time=0.6)
        self.hasta("y se minimiza", antes=0.1)
        self.play(Write(phi), run_time=1.1)

        self.hasta("en la segunda", antes=0.3)
        self.play(e1.animate.set_opacity(0.35), e2.animate.set_opacity(1), run_time=0.5)
        self.play(e2.fondo.animate.set_stroke(NARANJA, 3), run_time=0.3)
        self.cambiar(det1)
        self.mostrar(renglones[0])
        self.hasta("con envases enteros", antes=0.15)
        self.mostrar(renglones[1], rt=0.45)
        self.hasta("sin empeorar", antes=0.15)
        self.mostrar(renglones[2], rt=0.45)
        self.terminar()


# ======================================================================================================================
class E5Ejemplo(Escena):
    """Tres productos en el plano lentejas-arroz: cuando las metas se pueden cumplir (60 g de proteína) y cuando no
    (300 g). Las rectas, la región factible y la recta de costo se calculan, no se dibujan a ojo."""

    ID = "e5_ejemplo"
    CAP = 4
    YMAX = 900
    ORIGEN = np.array([-0.85, -2.3, 0])
    ANCHO, ALTO = 6.9, 4.45

    def c2p(self, x, y):
        return self.ORIGEN + np.array([x / self.xmax.get_value() * self.ANCHO, y / self.YMAX * self.ALTO, 0])

    def caja(self):
        xm = self.xmax.get_value()
        return [(0, 0), (xm, 0), (xm, self.YMAX), (0, self.YMAX)]

    @staticmethod
    def recortar(poli, a, b, c, mayor=True):
        """Sutherland-Hodgman: la parte del polígono donde a·x + b·y >= c (o <= c)."""
        f = (lambda p: a * p[0] + b * p[1] - c) if mayor else (lambda p: c - a * p[0] - b * p[1])
        salida = []
        for i in range(len(poli)):
            p, q = poli[i], poli[(i + 1) % len(poli)]
            fp, fq = f(p), f(q)
            if fp >= 0:
                salida.append(p)
            if fp * fq < 0:
                t = fp / (fp - fq)
                salida.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
        return salida

    def region(self, prot: float | None, energia: bool = True):
        poli = self.caja()
        if energia:
            poli = self.recortar(poli, 3.5, 3.5, 1900)
            poli = self.recortar(poli, 3.5, 3.5, 2100, mayor=False)
        if prot is not None:
            poli = self.recortar(poli, 0.25, 0.07, prot)
        return poli

    def poligono(self, poli, color=ACENTO, opacidad=0.6):
        if len(poli) < 3:
            poli = [(600, 0)] * 3
            opacidad = 0
        return Polygon(*[self.c2p(*p) for p in poli], fill_color=color, fill_opacity=opacidad, stroke_color=TINTA,
                       stroke_width=1.5 if opacidad else 0)

    def recta(self, a, b, c, color, ancho=4, punteada=False):
        """La recta a·x + b·y = c recortada al cuadro."""
        xm = self.xmax.get_value()
        pts = []
        for x in (0, xm):
            y = (c - a * x) / b
            if -1e-6 <= y <= self.YMAX + 1e-6:
                pts.append((x, y))
        for y in (0, self.YMAX):
            x = (c - b * y) / a
            if -1e-6 <= x <= xm + 1e-6:
                pts.append((x, y))
        pts = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
        if len(pts) < 2:
            pts = [(xm, 0), (xm, 0.001)]
        cls = DashedLine if punteada else Line
        kw = {"dash_length": 0.1} if punteada else {}
        return cls(self.c2p(*pts[0]), self.c2p(*pts[-1]), color=color, stroke_width=ancho, **kw)

    def ejes(self):
        xm = self.xmax.get_value()
        g = VGroup(Line(self.c2p(0, 0), self.c2p(xm, 0), color=SUAVE, stroke_width=2.5),
                   Line(self.c2p(0, 0), self.c2p(0, self.YMAX), color=SUAVE, stroke_width=2.5))
        for x in range(200, int(xm) + 1, 200):
            p = self.c2p(x, 0)
            g.add(Line(p, p + DOWN * 0.08, color=SUAVE, stroke_width=2))
            g.add(texto(str(x), 17, color=SUAVE, mono=True).next_to(p, DOWN, buff=0.12))
        for y in (300, 600, 900):
            p = self.c2p(0, y)
            g.add(Line(p, p + LEFT * 0.08, color=SUAVE, stroke_width=2))
            g.add(texto(str(y), 17, color=SUAVE, mono=True).next_to(p, LEFT, buff=0.12))
        g.add(texto("lentejas (g por día)", 21, color=SUAVE).next_to(self.c2p(xm, 0), DOWN, buff=0.45)
              .align_to(self.c2p(xm, 0), RIGHT))
        g.add(texto("arroz (g por día)", 21, color=SUAVE).next_to(self.c2p(0, self.YMAX), UP, buff=0.2)
              .align_to(self.c2p(0, 0), LEFT).shift(LEFT * 0.45))
        return g

    def construct(self):
        self.entrar()
        self.xmax = ValueTracker(700)

        # --- La oferta
        prods = VGroup()
        for nombre, prot, precio in (("Fideos", "2 g", "$20"), ("Lentejas", "25 g", "$80"), ("Arroz", "7 g", "$25")):
            c = columna(texto(nombre, 34, negrita=True),
                        texto(f"{prot} de proteína", 24, color=SUAVE),
                        texto(f"{precio} cada 100 g", 24, color=SUAVE, mono=True), buff=0.12)
            prods.add(en_tarjeta(c, ancho=3.4, alto=1.85))
        prods.arrange(RIGHT, buff=0.4)
        nota = texto("los tres: 350 kcal cada 100 g", 24, color=SUAVE)
        oferta = encuadrar(columna(prods, nota, buff=0.45, alinear=ORIGIN))
        self.mostrar(*prods, rt=0.9, lag=0.2)
        self.play(FadeIn(nota), run_time=0.4)
        self.hasta("los fideos son", antes=0.1)
        self.play(prods[0].fondo.animate.set_stroke(ACENTO, 5), run_time=0.4)
        self.hasta("casi no tienen", antes=0.1)
        tacha = Line(prods[0].get_left() + RIGHT * 0.3, prods[0].get_right() + LEFT * 0.3, color=ROJO,
                     stroke_width=6)
        self.play(prods[0].animate.set_opacity(0.35), Create(tacha), run_time=0.5)

        # --- El panel de la izquierda: lo que pedimos y el resultado
        def pide(color, s):
            return VGroup(Line(LEFT * 0.2, RIGHT * 0.2, color=color, stroke_width=6), texto(s, 23)) \
                .arrange(RIGHT, buff=0.2)

        titulo_p = texto("Pedimos, por día", 26, negrita=True)
        p_ener = pide(VERDE, "energía: 1.900 a 2.100 kcal")
        p_prot = pide(AZUL, "proteína: 60 g o más")
        pedidos = columna(titulo_p, p_ener, p_prot, buff=0.22)
        pedidos.move_to([-6.15, 2.45, 0], aligned_edge=UP + LEFT)
        X_PANEL = pedidos.get_left()[0]

        self.hasta("pedimos entre", antes=0.4)
        self.cambiar([prods, nota, tacha])
        ejes = always_redraw(self.ejes)
        self.play(FadeIn(titulo_p, shift=UP * 0.15), FadeIn(ejes), run_time=0.6)
        ener = always_redraw(lambda: VGroup(self.recta(3.5, 3.5, 1900, VERDE), self.recta(3.5, 3.5, 2100, VERDE)))
        self.play(FadeIn(p_ener, shift=UP * 0.15), Create(ener), run_time=0.8)
        self.prot = ValueTracker(60)
        prot = always_redraw(lambda: self.recta(0.25, 0.07, self.prot.get_value(), AZUL))
        self.hasta("y al menos", antes=0.1)
        self.play(FadeIn(p_prot, shift=UP * 0.15), Create(prot), run_time=0.8)

        # Cada restricción recorta: primero el cuadrante, después la franja de energía, después la proteína.
        self.hasta("cada restriccion recorta", antes=0.2)
        zona = self.poligono(self.region(None, energia=False), ACENTO, 0.25)
        self.play(FadeIn(zona), run_time=0.4)
        self.play(Transform(zona, self.poligono(self.region(None), ACENTO, 0.45)), run_time=0.7, rate_func=MUEVE)
        self.play(Transform(zona, self.poligono(self.region(60))), run_time=0.7, rate_func=MUEVE)
        self.remove(zona)
        zona = always_redraw(lambda: self.poligono(self.region(self.prot.get_value())))
        self.add(zona)
        self.bring_to_front(ener, prot)
        self.hasta("lo que queda", antes=0.1)
        lbl_r = texto("región factible", 22, negrita=True).next_to(self.c2p(420, 330), UR, buff=0.05)
        flecha_r = Arrow(lbl_r.get_corner(DOWN + LEFT), self.c2p(340, 215), buff=0.06, color=TINTA, stroke_width=3,
                         max_tip_length_to_length_ratio=0.25)
        self.play(FadeIn(lbl_r), GrowFromEdge(flecha_r, UP), run_time=0.5)

        # --- El óptimo: la recta de costo baja hasta tocar un vértice
        self.hasta("el optimo cae", antes=0.3)
        costo = ValueTracker(2900)
        iso = always_redraw(lambda: self.recta(5.6, 1.75, costo.get_value(), ROJO, 4, punteada=True))
        etq_c = always_redraw(lambda: texto(f"costo ${miles(costo.get_value())}", 22, negrita=True, color=ROJO,
                                            mono=True).next_to(self.c2p(self.xmax.get_value(), self.YMAX), DOWN,
                                                               buff=0.05).align_to(self.c2p(self.xmax.get_value(), 0),
                                                                                   RIGHT))
        self.add(iso, etq_c)
        self.play(costo.animate.set_value(1420.4), run_time=1.8, rate_func=smooth)
        vert = Dot(self.c2p(122.2, 420.6), radius=0.12, color=ROJO)
        anillo = Circle(radius=0.3, stroke_color=ROJO, stroke_width=4).move_to(vert)
        self.play(FadeIn(vert, scale=2), Create(anillo), run_time=0.5)

        res_t = texto("La compra óptima, por día", 26, negrita=True)
        res = columna(texto("122 g de lentejas", 24), texto("421 g de arroz", 24), buff=0.1)
        ok = sello(True, "cumple todas las metas", 22)
        resultado = columna(res_t, res, ok, buff=0.2)
        linea = Line(LEFT * 2.1, RIGHT * 2.1, color=LINEA, stroke_width=2)
        linea.next_to(pedidos, DOWN, buff=0.3).align_to(pedidos, LEFT)
        resultado.next_to(linea, DOWN, buff=0.3).align_to(pedidos, LEFT)
        self.hasta("lentejas y arroz en la", antes=0.2)
        self.play(Create(linea), FadeIn(res_t, shift=UP * 0.1), FadeIn(res, shift=UP * 0.1), run_time=0.6)
        self.hasta("se cumplen todas", antes=0.15)
        self.play(FadeIn(ok, scale=1.2), run_time=0.4, rate_func=ENTRA)

        # --- Precio sombra
        self.hasta("y el precio sombra", antes=0.2)
        sombra = columna(texto("precio sombra de la proteína", 21, color=SUAVE),
                         texto("+1 g = +$21,39 / semana", 25, negrita=True, mono=True, color=AZUL), buff=0.08)
        caja_s = en_tarjeta(sombra, AZUL_SUAVE, AZUL_SUAVE, pad=0.2)
        caja_s.next_to(resultado, DOWN, buff=0.3).align_to(pedidos, LEFT)
        self.play(FadeIn(caja_s, shift=UP * 0.15), Indicate(prot, color=AZUL, scale_factor=1.0), run_time=0.7)

        # --- ¿Y si pedimos 300 g?
        self.hasta("y si pedimos", antes=0.2)
        p_prot300 = pide(ROJO, "proteína: 300 g o más").move_to(p_prot, aligned_edge=LEFT)
        self.play(FadeOut(VGroup(res_t, res, ok, caja_s), shift=UP * 0.2), FadeOut(VGroup(vert, anillo)),
                  FadeOut(iso), FadeOut(etq_c), FadeOut(VGroup(lbl_r, flecha_r)), run_time=0.45)
        self.play(Transform(p_prot, p_prot300), run_time=0.5)
        self.hasta("la recta se aleja", antes=0.1)
        self.remove(prot)
        prot = always_redraw(lambda: self.recta(0.25, 0.07, self.prot.get_value(), ROJO))
        self.add(prot)
        self.play(self.xmax.animate.set_value(1300), self.prot.animate.set_value(300), run_time=2.6, rate_func=MUEVE)
        vacia = texto("no queda región factible", 21, negrita=True, color=ROJO).move_to(self.c2p(720, 330))
        self.hasta("ninguna compra cumple", antes=0.15)
        no = sello(False, "ninguna compra cumple", 22)
        no.next_to(linea, DOWN, buff=0.35).align_to(pedidos, LEFT)
        self.play(FadeIn(vacia), FadeIn(no, scale=1.2), run_time=0.5)

        # --- Lo más cerca posible
        self.hasta("llega a lo maximo", antes=0.2)
        mejor = Dot(self.c2p(600, 0), radius=0.12, color=TINTA)
        anillo2 = Circle(radius=0.3, stroke_color=TINTA, stroke_width=4).move_to(mejor)
        nivel = self.recta(0.25, 0.07, 150, AZUL, 3, punteada=True)
        etq_n = texto("150 g: lo máximo", 20, color=AZUL, negrita=True)
        etq_n.next_to(self.c2p(360, 860), RIGHT, buff=0.1)
        falta = VGroup(Line(self.c2p(600, 0) + DOWN * 0.0, self.c2p(1200, 0), color=ROJO, stroke_width=8))
        mejor_t = texto("La mejor compra posible", 26, negrita=True)
        mejor_r = columna(texto("600 g de lentejas", 24), texto("150 g de proteína", 24), buff=0.1)
        no2 = sello(False, "falta el 50 % de la proteína", 22)
        bloque_m = columna(mejor_t, mejor_r, no2, buff=0.22).next_to(linea, DOWN, buff=0.35).align_to(pedidos, LEFT)
        self.play(FadeOut(no, shift=UP * 0.2), FadeOut(vacia), run_time=0.35)
        self.play(FadeIn(mejor, scale=2), Create(anillo2), Create(nivel), FadeIn(etq_n), run_time=0.7)
        self.play(FadeIn(mejor_t, shift=UP * 0.1), FadeIn(mejor_r, shift=UP * 0.1), run_time=0.5)
        self.hasta("y avisa", antes=0.1)
        etq_f = texto("falta la mitad", 20, color=ROJO, negrita=True).next_to(falta, UP, buff=0.12)
        self.play(Create(falta), FadeIn(etq_f), FadeIn(no2, scale=1.2), run_time=0.6)

        # --- Las dos, una al lado de la otra
        def resumen(ok_, titulo, pide_, pasa, costo_):
            color, fondo = (VERDE, VERDE_SUAVE) if ok_ else (ROJO, ROJO_SUAVE)
            icono = (tilde(color, 0.5, 9) if ok_ else cruz(color, 0.4, 9))
            cab = VGroup(icono, texto(titulo, 34, negrita=True, color=color)).arrange(RIGHT, buff=0.3)
            c = columna(cab, texto(pide_, 26), texto(pasa, 26), texto(costo_, 30, negrita=True, mono=True),
                        buff=0.28)
            return en_tarjeta(c, BLANCO, color, ancho=5.7, alto=3.4)

        a = resumen(True, "Se puede", "Pedimos 60 g de proteína", "Cumple todo, al menor costo", "$1.550 / semana")
        b = resumen(False, "No se puede", "Pedimos 300 g de proteína", "Llega a 150 g y avisa qué falta",
                    "$3.600 / semana")
        for r in (a, b):
            r.contenido.align_to(r.fondo, LEFT).shift(RIGHT * 0.5)
            r.fondo.set_stroke(width=3)
        final = encuadrar(VGroup(a, b).arrange(RIGHT, buff=0.5))
        self.hasta("cuando se puede", antes=0.4)
        plano = VGroup(ejes, ener, prot, zona, mejor, anillo2, nivel, etq_n, falta, etq_f)
        for m in (ejes, ener, prot, zona):
            m.clear_updaters()
        self.cambiar([plano, pedidos, p_prot, linea, mejor_t, mejor_r, no2])
        self.play(FadeIn(a, shift=UP * 0.25), run_time=0.55, rate_func=ENTRA)
        self.hasta("cuando no", antes=0.2)
        self.play(FadeIn(b, shift=UP * 0.25), run_time=0.55, rate_func=ENTRA)
        self.terminar()


# ======================================================================================================================
class E6Casos(Escena):
    ID = "e6_casos"
    CAP = 5

    def construct(self):
        self.entrar()

        # --- Cuatro casos que cumplen todo
        casos = [("familia de cuatro", "Familia de cuatro", "$74.526", "148 / 148"),
                 ("una persona celiaca", "Celíaca", "$29.236", "37 / 37"),
                 ("una vegana", "Vegana", "$35.236", "35 / 35"),
                 ("alguien con anemia", "Anemia", "$26.408", "37 / 37")]
        tarjetas, sellos = VGroup(), VGroup()
        for _, nombre, total, metas in casos:
            plano = texto(f"{metas} metas", 22, color=SUAVE, mono=True)
            c = columna(texto(nombre, 25, negrita=True), texto(total, 42, negrita=True, mono=True),
                        texto("por semana", 21, color=SUAVE), plano, buff=0.16)
            tj = en_tarjeta(c, ancho=2.98, alto=2.75)
            tj.contenido.align_to(tj.fondo, LEFT).shift(RIGHT * 0.3)
            s = sello(True, metas.replace(" ", ""), 20).move_to(plano, aligned_edge=LEFT).shift(LEFT * 0.06)
            tj.plano = plano
            tarjetas.add(tj)
            sellos.add(s)
        tarjetas.arrange(RIGHT, buff=0.16)
        for tj, s in zip(tarjetas, sellos):
            s.move_to(tj.plano, aligned_edge=LEFT).shift(LEFT * 0.06)
        titulo = texto("Compra para una semana, en el centro de Buenos Aires", 28, color=SUAVE)
        cuadro = encuadrar(columna(titulo, tarjetas, buff=0.55, alinear=ORIGIN))
        for tj, s in zip(tarjetas, sellos):
            s.move_to(tj.plano, aligned_edge=LEFT).shift(LEFT * 0.06)
        self.hasta("con los datos reales", antes=0.2)
        self.mostrar(titulo)
        for tj, (frase, *_r) in zip(tarjetas, casos):
            self.hasta(frase, antes=0.25)
            self.mostrar(tj, rt=0.45)
        self.hasta("todos cumplen", antes=0.1)
        self.play(LaggedStart(*[FadeOut(tj.plano) for tj in tarjetas], lag_ratio=0.15), run_time=0.35)
        self.play(LaggedStart(*[FadeIn(s, scale=1.15) for s in sellos], lag_ratio=0.15), run_time=0.7)

        # --- Subir de peso
        filas = tabla_barras([("Mantener el peso", 2290, "2.290 kcal · $23.719", TENUE),
                              ("Aumentar de peso", 2790, "2.790 kcal · $24.848", VERDE)], largo=5.2, tam=26, alto=0.6,
                             buff=0.35)
        dato = VGroup(texto("+500 kcal por día", 32, negrita=True, color=VERDE),
                      texto("= +$1.129 por semana", 32, negrita=True, mono=True)).arrange(RIGHT, buff=0.3)
        t_est = texto("Estudiante de 20 años, con bajo peso", 30, negrita=True)
        peso = encuadrar(columna(t_est, filas, dato, buff=0.6, alinear=ORIGIN))
        self.hasta("y para alguien que quiere", antes=0.3)
        self.cambiar([titulo, tarjetas, sellos], t_est)
        self.play(LaggedStart(*[GrowFromEdge(f[1], LEFT) for f in filas], lag_ratio=0.3),
                  LaggedStart(*[FadeIn(VGroup(f[0], f[2])) for f in filas], lag_ratio=0.3), run_time=1.0)
        self.hasta("quinientas calorias", antes=0.15)
        self.mostrar(dato)

        # --- La meta imposible: los gráficos de bala de la página
        filas_b = VGroup()
        datos = (("Lácteos", 2.0, 3.0, "llega al 67 %"), ("Calcio", 737, 1000, "llega al 74 %"),
                 ("Verduras", 527, 300, "cumple"), ("Hierro", 31, 18, "cumple"))
        for i, (nombre, valor, minimo, estado) in enumerate(datos):
            ok = valor >= minimo
            y = -i * 0.82
            tope = max(minimo * 1.6, valor * 1.15)
            pista = RoundedRectangle(width=5.6, height=0.26, corner_radius=0.13, fill_color=HUNDIDO, fill_opacity=1,
                                     stroke_width=0).move_to([0, y, 0])
            x0 = pista.get_left()[0]
            rango = Rectangle(width=5.6 * (1 - minimo / tope), height=0.26, fill_color=VERDE_SUAVE, fill_opacity=1,
                              stroke_width=0).move_to(pista).align_to(pista, RIGHT)
            marca = Line(UP * 0.22, DOWN * 0.22, color=SUAVE, stroke_width=4).move_to([x0 + 5.6 * minimo / tope, y, 0])
            pto = (Dot(radius=0.15, color=TINTA) if ok else
                   VGroup(Dot(radius=0.15, color=BLANCO), Circle(radius=0.15, stroke_color=ROJO, stroke_width=7)))
            pto.move_to([x0 + 5.6 * valor / tope, y, 0])
            nom = texto(nombre, 26, negrita=not ok).move_to([x0 - 0.45, y, 0], aligned_edge=RIGHT)
            icono = (tilde(VERDE, 0.24) if ok else cruz(ROJO, 0.18))
            icono.move_to([pista.get_right()[0] + 0.45, y, 0])
            est = texto(estado, 24, negrita=True, color=VERDE if ok else ROJO).next_to(icono, RIGHT, buff=0.18)
            fila = VGroup(pista, rango, marca, pto, nom, icono, est)
            if not ok:
                fondo = RoundedRectangle(width=10.6, height=0.68, corner_radius=0.12, fill_color=ROJO_SUAVE,
                                         fill_opacity=1, stroke_width=0).move_to([x0 - 1.85 + 5.3, y, 0])
                fila.add_to_back(fondo)
            filas_b.add(fila)
        quien = texto("Celíaca y alérgica a la leche, en Córdoba", 30, negrita=True)
        estado = sello(False, "35 de 37 metas", 22)
        cabeza = VGroup(quien, estado).arrange(RIGHT, buff=0.45)
        leyenda = texto("la franja verde es la meta; el punto, lo que come", 22, color=SUAVE)
        bala = encuadrar(columna(cabeza, filas_b, leyenda, buff=0.55, alinear=ORIGIN))
        self.hasta("pero a una persona", antes=0.3)
        self.cambiar([t_est, filas, dato], cabeza)
        self.hasta("ninguna sucursal", antes=0.2)
        self.play(LaggedStart(*[FadeIn(f, shift=RIGHT * 0.2) for f in filas_b], lag_ratio=0.2), run_time=1.1)
        self.play(FadeIn(leyenda), run_time=0.4)
        self.hasta("el calcio llega", antes=0.1)
        self.play(Indicate(filas_b[1][-1], color=ROJO, scale_factor=1.15), run_time=0.7)
        self.hasta("y los lacteos", antes=0.1)
        self.play(Indicate(filas_b[0][-1], color=ROJO, scale_factor=1.15), run_time=0.7)

        # --- Caminar más
        esc = tabla_barras([("15 min", 56256, "$56.256", TINTA), ("30 min", 53060, "$53.060", TINTA),
                            ("45 min", 53060, "$53.060", TINTA), ("60 min", 42140, "$42.140", VERDE)], largo=6.4,
                           tam=26, mono_etq=True)
        t_cam = VGroup(texto("Hasta cuánto caminás", 30, negrita=True),
                       texto("· hogar de dos, en Córdoba", 30, color=SUAVE)).arrange(RIGHT, buff=0.2)
        menos25 = sello(True, "25 % menos", 24)
        cuadro_c = encuadrar(columna(t_cam, esc, buff=0.55, alinear=ORIGIN))
        menos25.next_to(esc[3][2], RIGHT, buff=0.35)
        self.hasta("tambien decide", antes=0.3)
        self.cambiar([cabeza, filas_b, leyenda], t_cam)
        self.hasta("caminando hasta una hora", antes=0.2)
        self.play(LaggedStart(*[GrowFromEdge(f[1], LEFT) for f in esc], lag_ratio=0.2),
                  LaggedStart(*[FadeIn(VGroup(f[0], f[2])) for f in esc], lag_ratio=0.2), run_time=1.3)
        self.hasta("veinticinco por ciento", antes=0.2)
        self.play(FadeIn(menos25, scale=1.2), run_time=0.4)

        # --- Dos supermercados
        dos = tabla_barras([("En una sucursal", 288518, "$288.518", TINTA),
                            ("Repartida en dos", 109028, "$109.028", VERDE)], largo=6.0, tam=26, alto=0.6, buff=0.35)
        t_dos = VGroup(texto("Dónde comprás", 30, negrita=True),
                       texto("· celíaca con alergias y nena escolar", 30, color=SUAVE)).arrange(RIGHT, buff=0.2)
        menos62 = sello(True, "62 % menos", 24)
        cuadro_d = encuadrar(columna(t_dos, dos, buff=0.55, alinear=ORIGIN))
        menos62.next_to(dos[1][2], RIGHT, buff=0.35)
        self.hasta("y repartida", antes=0.3)
        self.cambiar([t_cam, esc, menos25], t_dos)
        self.play(LaggedStart(*[GrowFromEdge(f[1], LEFT) for f in dos], lag_ratio=0.3),
                  LaggedStart(*[FadeIn(VGroup(f[0], f[2])) for f in dos], lag_ratio=0.3), run_time=1.0)
        self.hasta("mas de la mitad", antes=0.2)
        self.play(FadeIn(menos62, scale=1.2), run_time=0.4)
        self.terminar()


# ======================================================================================================================
class E7Cierre(Escena):
    ID = "e7_cierre"
    CAP = 6

    def construct(self):
        self.entrar()

        # --- Precios sombra
        metas = [("Calcio", 38.31), ("Lácteos", 22.56), ("Verduras", 21.59), ("Vitamina B6", 15.11),
                 ("Pescado", 9.98), ("Frutas", 9.36)]
        filas = tabla_barras([(n, v, f"${miles(v, 2)}", AZUL if i < 2 else LINEA) for i, (n, v) in enumerate(metas)],
                             largo=6.2, tam=25, alto=0.4, buff=0.2)
        titulo = texto("Cuánto encarece la semana pedir un 1 % más de cada meta", 28, negrita=True)
        nota = texto("precios sombra de la relajación lineal, caso base", 21, color=SUAVE)
        cuadro = encuadrar(columna(titulo, filas, nota, buff=0.45, alinear=ORIGIN))
        self.hasta("los precios sombra", antes=0.3)
        self.mostrar(titulo)
        self.play(LaggedStart(*[GrowFromEdge(f[1], LEFT) for f in filas], lag_ratio=0.1),
                  LaggedStart(*[FadeIn(VGroup(f[0], f[2])) for f in filas], lag_ratio=0.1), run_time=1.3)
        self.play(FadeIn(nota), run_time=0.3)
        self.hasta("el calcio y los lacteos", antes=0.1)
        self.play(*[Indicate(filas[i][0], color=AZUL, scale_factor=1.12) for i in (0, 1)], run_time=0.8)

        # --- Semana contra mes
        alto_max = 3.2
        sem = Rectangle(width=1.9, height=alto_max, fill_color=TINTA, fill_opacity=1, stroke_width=0)
        mes = Rectangle(width=1.9, height=2540 / 3433 * alto_max, fill_color=VERDE, fill_opacity=1, stroke_width=0)
        barras = VGroup(sem, mes).arrange(RIGHT, buff=1.0, aligned_edge=DOWN)
        v_sem = texto("$3.433", 32, negrita=True, mono=True).next_to(sem, UP, buff=0.15)
        v_mes = texto("$2.540", 32, negrita=True, mono=True, color=VERDE).next_to(mes, UP, buff=0.15)
        e_sem = texto("comprando\npor semana", 22, color=SUAVE, line_spacing=1.1).next_to(sem, DOWN, buff=0.2)
        e_mes = texto("comprando\npor mes", 22, color=SUAVE, line_spacing=1.1).next_to(mes, DOWN, buff=0.2)
        grafico = VGroup(barras, v_sem, v_mes, e_sem, e_mes)
        lado = columna(texto("−26 %", 80, negrita=True, color=VERDE),
                       texto("de costo por día,\nporque se aprovechan\nmejor los envases", 26, color=SUAVE,
                             line_spacing=1.15), buff=0.25)
        t_sm = texto("Costo por día de la misma dieta", 30, negrita=True)
        cuerpo = VGroup(grafico, lado).arrange(RIGHT, buff=1.4)
        cuadro2 = encuadrar(columna(t_sm, cuerpo, buff=0.5, alinear=ORIGIN))
        self.hasta("y comprar para un mes", antes=0.3)
        self.cambiar([titulo, filas, nota], t_sm)
        self.play(GrowFromEdge(sem, DOWN), FadeIn(v_sem), FadeIn(e_sem), run_time=0.6, rate_func=ENTRA)
        self.play(GrowFromEdge(mes, DOWN), FadeIn(v_mes), FadeIn(e_mes), run_time=0.6, rate_func=ENTRA)
        self.hasta("baja el costo", antes=0.1)
        self.play(FadeIn(lado[0], shift=LEFT * 0.2), run_time=0.5)
        self.hasta("porque se aprovechan", antes=0.2)
        self.play(FadeIn(lado[1]), run_time=0.5)

        # --- Conclusiones
        def conclusion(n, s):
            num = texto(str(n), 30, negrita=True, mono=True, color=TINTA)
            circ = Circle(radius=0.32, fill_color=ACENTO, fill_opacity=1, stroke_width=0)
            num.move_to(circ)
            return VGroup(VGroup(circ, num), texto(s, 40, negrita=True, line_spacing=1.1)).arrange(RIGHT, buff=0.45)

        c1 = conclusion(1, "El problema de la dieta sigue sirviendo,\nsi se lo completa.")
        c2 = conclusion(2, "Dónde comprás importa\ntanto como qué comprás.")
        concl = encuadrar(columna(c1, c2, buff=0.8))
        self.hasta("en resumen", antes=0.3)
        self.cambiar([t_sm, grafico, lado], c1)
        self.hasta("y donde compras", antes=0.2)
        self.mostrar(c2)

        # --- La placa final
        nombre = texto("Canasta saludable\nal menor precio", 60, negrita=True, line_spacing=1.0)
        url = texto("nazarenofolica.github.io/Optimizacion_TPS", 24, mono=True)
        caja_url = RoundedRectangle(width=url.width + 0.5, height=url.height + 0.34, corner_radius=0.1,
                                    fill_color=ACENTO, fill_opacity=1, stroke_width=0)
        url.move_to(caja_url)
        autores = texto("Martínez Folica · Naón", 28, color=SUAVE)
        materia = texto("Optimización · UCA · 2026", 24, color=SUAVE)
        izquierda = columna(nombre, VGroup(caja_url, url), columna(autores, materia, buff=0.12), buff=0.5)
        tk = ticket([("Sucursales", "2.651"), ("Precios", "8.309.213"), ("Metas por persona", "37"), "---"],
                    ancho=4.8, tam=21, titulo="CANASTA SALUDABLE", total=("TOTAL", "EL MÁS BAJO"))
        placa = encuadrar(VGroup(izquierda, tk).arrange(RIGHT, buff=1.2))
        self.hasta("la pagina esta publicada", antes=0.3)
        barra = self.barra
        self.cambiar([c1, c2, self.cab, barra])
        self.play(FadeIn(nombre, shift=UP * 0.2), FadeIn(tk.papel, shift=DOWN * 0.1), run_time=0.6, rate_func=ENTRA)
        self.play(FadeIn(VGroup(caja_url, url), shift=UP * 0.15),
                  LaggedStart(*[FadeIn(r, shift=DOWN * 0.05) for r in tk.renglones], lag_ratio=0.15), run_time=1.2)
        self.play(FadeIn(izquierda[2]), run_time=0.5)
        self.terminar(quedarse=True)
