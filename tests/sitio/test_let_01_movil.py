"""SPEC-LET-01 — el sitio en un móvil de 360 px (Chromium sin ventana, Playwright).

Antes de abrir el navegador, cada test pide las seis páginas por HTTP: si no hay sitio, falla diciéndolo.
"""

import re
import time
from urllib.parse import urlsplit

from apoyo_sitio import (
    ALTO_MOVIL,
    ANCHO_MOVIL,
    PAGINAS,
    RUTA_INEXISTENTE,
    SE_VE,
    anfitrion,
    movil,
    sitio_url,
    todas_las_paginas,
)

MENU = re.compile(r"men[uú]", re.IGNORECASE)
ENLACES_DEL_MENU = ("Inicio", "Quiénes somos", "Contacto")
# Un enlace es «del menú» si está dentro de <nav> (o role="navigation") y fuera del pie (<footer> o role="contentinfo").
# Los mismos enlaces repetidos en el pie, o sueltos fuera de un <nav>, no cuentan: ni para «plegado» ni para «aparecen».
DEL_MENU = """el => !!el.closest('nav, [role~="navigation"]') && !el.closest('footer, [role~="contentinfo"]')"""


def _del_menu_que_se_ven(pestana, nombre):
    """Índices de los enlaces «nombre» del menú que se ven ahora. SE_VE (apoyo_sitio): el enlace tiene tamaño, no está
    oculto ni transparente, cae dentro de la pantalla y un toque en su centro le llega a él; se mira cada trozo del
    enlace, por si ocupa dos líneas. Se buscan también los ocultos, para que los índices valgan antes y después de tocar."""
    estados = pestana.get_by_role("link", name=nombre, exact=True, include_hidden=True).evaluate_all(
        f"els => els.map(el => ({DEL_MENU})(el) && ({SE_VE})(el))"
    )
    return [i for i, se_ve in enumerate(estados) if se_ve]


def test_ca_let_01_03_menu_se_abre_y_lleva_a_contacto_a_360px():
    # CA-LET-01-03
    todas_las_paginas()
    from playwright.sync_api import expect

    base = sitio_url()
    with movil() as primera:
        for ruta in PAGINAS.values():
            # Una pestaña nueva por página: en /contacto/, tocar Contacto recarga la misma dirección, y esa recarga no
            # debe cruzarse con la carga de la página siguiente.
            pestana = primera.context.new_page()
            try:
                pestana.goto(base + ruta, wait_until="load")
                boton = pestana.get_by_role("button", name=MENU)
                expect(boton.first, f"{ruta}: no hay botón de menú visible a {ANCHO_MOVIL} px").to_be_visible()
                a_la_vista = [nombre for nombre in ENLACES_DEL_MENU if _del_menu_que_se_ven(pestana, nombre)]
                assert not a_la_vista, (
                    f"{ruta}: {a_la_vista} ya se ven antes de tocar el botón: el menú no está plegado a {ANCHO_MOVIL} px"
                )
                posicion = pestana.evaluate("[window.scrollX, window.scrollY]")
                boton.first.tap()
                limite = time.monotonic() + 5  # margen para la animación del menú
                while True:
                    # Se mide con la página donde estaba al cargar: un botón que solo la desplaza hasta unos enlaces que
                    # ya estaban más abajo no abre ningún menú.
                    pestana.evaluate("p => window.scrollTo(p[0], p[1])", posicion)
                    visibles = {nombre: _del_menu_que_se_ven(pestana, nombre) for nombre in ENLACES_DEL_MENU}
                    if all(visibles.values()) or time.monotonic() > limite:
                        break
                    pestana.wait_for_timeout(100)
                faltan = [nombre for nombre, indices in visibles.items() if not indices]
                assert not faltan, (
                    f"{ruta}: tocar el botón del menú no hace aparecer {faltan} dentro del menú "
                    "(los enlaces del pie o fuera de un <nav> no cuentan, ni desplazar la página hasta ellos)"
                )
                pestana.get_by_role("link", name="Contacto", exact=True, include_hidden=True).nth(visibles["Contacto"][0]).tap()
                pestana.wait_for_url(re.compile(r"/contacto/$"))
            finally:
                pestana.close()


def test_ca_let_01_06_sin_desplazamiento_horizontal_a_360px():
    # CA-LET-01-06
    todas_las_paginas()
    base = sitio_url()
    anchas = {}
    with movil() as pestana:
        for ruta in PAGINAS.values():
            pestana.goto(base + ruta, wait_until="load")
            ancho = pestana.evaluate("document.documentElement.scrollWidth")
            if ancho > ANCHO_MOVIL:
                anchas[ruta] = ancho
    assert not anchas, f"Páginas más anchas que la pantalla de {ANCHO_MOVIL} px: {anchas}"


def _recorre_hasta_el_final(pestana):
    """Desplaza la página de pantalla en pantalla hasta el final y espera a que la red quede en reposo. Lo que se carga al
    llegar a la vista (un iframe, un mapa o una imagen con loading="lazy") no se pide al cargar la página, sino aquí."""
    y = 0
    for _ in range(200):  # tope por si la página crece sin fin
        if y >= pestana.evaluate("document.documentElement.scrollHeight"):
            break
        pestana.evaluate("y => window.scrollTo(0, y)", y)
        pestana.wait_for_timeout(100)
        y += ALTO_MOVIL // 2
    pestana.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
    pestana.wait_for_timeout(300)  # el navegador pide lo perezoso en el cuadro siguiente al desplazamiento
    pestana.wait_for_load_state("networkidle")


def test_ca_let_01_20_nada_se_descarga_de_otro_dominio():
    # CA-LET-01-20
    todas_las_paginas()
    base = sitio_url()
    propio = anfitrion()
    actual = {"ruta": None}
    pedidas = {}
    with movil() as pestana:
        pestana.on("request", lambda peticion: pedidas.setdefault(actual["ruta"], []).append(peticion.url))
        # Las seis páginas y la 404 (RN-LET-01-18 dice «ninguna página»), cada una hasta el final.
        for ruta in [*PAGINAS.values(), RUTA_INEXISTENTE]:
            actual["ruta"] = ruta
            pestana.goto(base + ruta, wait_until="networkidle")
            _recorre_hasta_el_final(pestana)
    ajenas = {}
    for ruta, urls in pedidas.items():
        fuera = sorted({u for u in urls if urlsplit(u).scheme in ("http", "https") and urlsplit(u).hostname != propio})
        if fuera:
            ajenas[ruta] = fuera
    assert not ajenas, f"Descargas de otros dominios sin consentimiento (tipografías, analítica, redes…): {ajenas}"
