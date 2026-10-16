"""SPEC-LET-01 — páginas fijas del sitio, leídas como HTML (sin navegador).

Caja negra contra SITIO_URL: valen igual con WordPress que con Astro.
"""

import re
import subprocess
from pathlib import Path
from urllib.parse import quote

from apoyo_sitio import (
    PAGINAS,
    RUTA_INEXISTENTE,
    datos_titular,
    enlace_a_inicio_con_logotipo,
    movil,
    nif_valido,
    normaliza,
    pagina,
    pedir,
    ruta_de,
    sitio_url,
    todas_las_paginas,
    valores_validos,
)

# Huecos de plantilla que no pueden quedar publicados: cualquier texto entre corchetes («[tu dominio]», «[ ]», «[00.000]»,
# «[Texto de quiénes somos]», «[Pendiente]»), una variable de plantilla sin sustituir («{{ titulo }}»), «lorem ipsum», un
# dominio de ejemplo y el pie de la maqueta. «TODO» y «XXX» no entran: chocan con titulares en mayúsculas y con números
# romanos («XXX Feria de…»).
HUECOS = re.compile(
    r"\[[^\[\]]{0,80}\]|\{\{[^{}]{0,80}\}\}|lorem ipsum|example\.(?:com|org|net)|maqueta ·",
    re.IGNORECASE,
)
# Atributos cuyo valor también se lee: lo muestra el navegador o un buscador, o lo dice un lector de pantalla.
ATRIBUTOS_LEIDOS = ("content", "alt", "title", "placeholder", "aria-label", "value", "href")
# Idioma declarado: «es» o «es-ES», sin distinguir mayúsculas; la misma regla que la orden de CA-LET-01-07 («est» y
# «es-MX» no valen).
LANG_CASTELLANO = re.compile(r"es(-es)?", re.IGNORECASE)


def _texto_publicado(respuesta):
    """Lo que se lee de una página: el texto fuera de scripts y estilos y los atributos de ATRIBUTOS_LEIDOS, con las
    entidades HTML ya decodificadas (&middot;, &nbsp;…) y los espacios, saltos y espacios duros juntos en uno."""
    doc = respuesta.doc
    atributos = [n.attrs[a] for n in doc.todos() for a in ATRIBUTOS_LEIDOS if n.attrs.get(a)]
    return " ".join(" ".join([doc.texto(), *atributos]).split())


def test_ca_let_01_02_cada_pagina_enlaza_a_las_otras_cinco():
    # CA-LET-01-02
    respuestas = todas_las_paginas()
    fallos = []
    for nombre, respuesta in respuestas.items():
        enlaces = [a for a in respuesta.doc.todos("a") if a.dentro_de_zona("cabecera", "menu", "pie")]
        vacios = [a.attrs.get("href", "") for a in enlaces if a.attrs.get("href", "").strip() in ("", "#")]
        if vacios:
            fallos.append(f"{PAGINAS[nombre]}: {len(vacios)} enlace(s) del menú o del pie con href vacío o «#»")
        rutas = {ruta_de(a.attrs.get("href"), respuesta.url) for a in enlaces}
        for otro, ruta in PAGINAS.items():
            if otro != nombre and (ruta.rstrip("/") or "/") not in rutas:
                fallos.append(f"{PAGINAS[nombre]}: no enlaza a {ruta} desde el menú ni desde el pie")
    assert not fallos, "\n".join(fallos)


def test_ca_let_01_04_titulos_propios_y_distintos():
    # CA-LET-01-04
    respuestas = todas_las_paginas()
    titulos = {}
    for nombre, respuesta in respuestas.items():
        titulo = respuesta.doc.primero("title")
        titulos[PAGINAS[nombre]] = titulo.texto() if titulo is not None else ""
    vacios = [ruta for ruta, t in titulos.items() if not t]
    assert not vacios, f"Páginas sin <title>: {vacios}"
    assert len(set(titulos.values())) == len(titulos), f"Hay títulos repetidos: {titulos}"


def test_ca_let_01_05_descripciones_propias_y_distintas():
    # CA-LET-01-05
    respuestas = todas_las_paginas()
    descripciones = {}
    for nombre, respuesta in respuestas.items():
        meta = next(
            (m for m in respuesta.doc.todos("meta") if m.attrs.get("name", "").lower() == "description"),
            None,
        )
        descripciones[PAGINAS[nombre]] = " ".join((meta.attrs.get("content", "") if meta else "").split())
    vacias = [ruta for ruta, d in descripciones.items() if not d]
    assert not vacias, f"Páginas sin <meta name=\"description\">: {vacias}"
    assert len(set(descripciones.values())) == len(descripciones), f"Hay descripciones repetidas: {descripciones}"


def test_ca_let_01_08_sin_huecos_de_plantilla():
    # CA-LET-01-08
    textos = {ruta: _texto_publicado(pagina(ruta)) for ruta in PAGINAS.values()}
    textos[RUTA_INEXISTENTE] = _texto_publicado(pedir(RUTA_INEXISTENTE))
    hallados = {ruta: sorted(set(HUECOS.findall(texto))) for ruta, texto in textos.items() if HUECOS.search(texto)}
    assert not hallados, f"Huecos de plantilla publicados: {hallados}"


def test_ca_let_01_09_logotipo_en_cabecera_enlaza_a_inicio():
    # CA-LET-01-09
    respuestas = todas_las_paginas()
    sin_logo = [PAGINAS[n] for n, r in respuestas.items() if not enlace_a_inicio_con_logotipo(r, zonas=("cabecera",))]
    assert not sin_logo, (
        "Sin logotipo (imagen o SVG con texto alternativo «El Archivo de Talavera») dentro de un enlace a / "
        f"en la cabecera: {sin_logo}"
    )


def _comprueba_titular(ruta):
    texto = normaliza(pagina(ruta).doc.texto())
    titular = datos_titular()
    assert nif_valido(titular["nif"]), f"El NIF de titular.json ({titular['nif']}) no tiene un control válido"
    faltan = [campo for campo, valor in titular.items() if normaliza(valor) not in texto]
    assert not faltan, f"{ruta} no muestra estos datos de la titular: {faltan}"


def test_ca_let_01_17_aviso_legal_identifica_a_la_titular():
    # CA-LET-01-17
    _comprueba_titular(PAGINAS["aviso-legal"])


def test_ca_let_01_18_pagina_404_propia_con_enlace_a_inicio():
    # CA-LET-01-18
    respuesta = pedir(RUTA_INEXISTENTE)
    assert respuesta.status == 404, f"{RUTA_INEXISTENTE} responde {respuesta.status}, no 404"
    html = respuesta.doc.primero("html")
    lang = html.attrs.get("lang", "") if html is not None else ""
    assert LANG_CASTELLANO.fullmatch(lang), f"La página 404 no declara lang=\"es\" ni lang=\"es-ES\" (lleva {lang!r})"
    assert enlace_a_inicio_con_logotipo(respuesta), "La página 404 no lleva el logotipo con enlace a /"


def test_ca_let_01_19_etiqueta_viewport_de_movil():
    # CA-LET-01-19
    respuestas = todas_las_paginas()
    sin_viewport = []
    for nombre, respuesta in respuestas.items():
        meta = next((m for m in respuesta.doc.todos("meta") if m.attrs.get("name", "").lower() == "viewport"), None)
        contenido = re.sub(r"\s", "", meta.attrs.get("content", "")).lower() if meta else ""
        if "width=device-width" not in contenido:
            sin_viewport.append(PAGINAS[nombre])
    assert not sin_viewport, f"Sin <meta name=\"viewport\" content=\"width=device-width…\">: {sin_viewport}"


# Ficheros de trabajo del repositorio que el sitio nunca debe entregar: credenciales, configuración, presupuestos y
# tests. Se sacan del propio repositorio: los .md de la raíz, docs/, tests/ y todo lo que empieza por punto. Las
# credenciales no están versionadas (CA-LET-01-22), así que no salen de git ls-files y se piden siempre por su nombre:
# el .env, los .env.* que leen Astro y otros generadores (.env.local, .env.production) y el wp-config.php de WordPress.
RAIZ = Path(__file__).resolve().parents[2]
SIEMPRE = ("/.env", "/.env.local", "/.env.production", "/wp-config.php", "/.git/config", "/.git/HEAD")
DEL_TALLER = re.compile(r"^(?:[^/]+\.md|docs/.+|tests/.+|\.[^/]+(?:/.+)?)$")


def _ficheros_del_taller():
    salida = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    rutas = ["/" + quote(f) for f in salida.splitlines() if DEL_TALLER.match(f)]
    return list(SIEMPRE) + sorted(set(rutas) - set(SIEMPRE))


def test_ca_let_01_21_no_sirve_ficheros_del_repositorio():
    # CA-LET-01-21
    pagina(PAGINAS["inicio"])  # sin sitio no hay nada que comprobar
    servidos = {}
    for ruta in _ficheros_del_taller():
        status = pedir(ruta).status
        if not 400 <= status < 500:
            servidos[ruta] = status
    assert not servidos, f"El sitio entrega ficheros del repositorio (deben responder 4xx): {servidos}"


def test_ca_let_01_29_privacidad_nombra_a_la_misma_titular():
    # CA-LET-01-29
    _comprueba_titular(PAGINAS["privacidad"])


def test_ca_let_01_33_cookies_nombra_las_que_pone_el_sitio():
    # CA-LET-01-33
    todas_las_paginas()
    base = sitio_url()
    # Las cookies que le quedan a una visitante que recorre las seis páginas y la 404 y envía el formulario. El envío es
    # válido: este test se corre, como los del formulario, contra un sitio cuyo correo va al buzón de pruebas.
    with movil() as pestana:
        for ruta in [*PAGINAS.values(), RUTA_INEXISTENTE]:
            pestana.goto(base + ruta, wait_until="load")
        pestana.goto(base + PAGINAS["contacto"], wait_until="load")
        valores = valores_validos("cookies-ca-let-01-33")
        for campo in ("nombre", "correo", "mensaje"):
            pestana.locator(f'[name="{campo}"]').fill(valores[campo])
        pestana.locator('[name="privacidad"]').check()
        pestana.get_by_role("button", name=re.compile("enviar", re.IGNORECASE)).tap()
        pestana.wait_for_selector("#envio-correcto, #envio-error", timeout=15000)
        cookies = sorted({c["name"] for c in pestana.context.cookies()})
    texto = normaliza(pagina(PAGINAS["cookies"]).doc.texto())
    if cookies:
        # Cada nombre, como palabra entera: «sid» no está nombrada por «consideramos».
        sin_nombrar = [c for c in cookies if not re.search(rf"(?<!\S){re.escape(normaliza(c))}(?!\S)", texto)]
        assert not sin_nombrar, f"El sitio pone cookies que /cookies/ no nombra: {sin_nombrar}"
    else:
        assert "no utiliza cookies" in texto, "El sitio no pone ninguna cookie y /cookies/ no dice «no utiliza cookies»"
