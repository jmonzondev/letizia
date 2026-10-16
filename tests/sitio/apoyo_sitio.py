"""Apoyo común de los tests de caja negra del sitio (SPEC-LET-01).

Los tests hablan con el sitio servido en SITIO_URL y con el buzón de pruebas (Mailpit) en BUZON_URL; no saben si
detrás hay WordPress o Astro. Solo usan la biblioteca estándar, salvo los de navegador, que cargan Playwright al
usarlo. Cada test pide primero el sitio: si no hay sitio, falla diciéndolo, antes de tocar el buzón o el navegador.
"""

import http.cookiejar
import json
import os
import re
import time
import unicodedata
import urllib.error
import uuid
import urllib.parse
import urllib.request
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path

import pytest

PAGINAS = {
    "inicio": "/",
    "quienes-somos": "/quienes-somos/",
    "contacto": "/contacto/",
    "aviso-legal": "/aviso-legal/",
    "privacidad": "/privacidad/",
    "cookies": "/cookies/",
}
RUTA_INEXISTENTE = "/no-existe-ca-let-01/"
MARCA = "El Archivo de Talavera"
TITULAR = Path(__file__).with_name("titular.json")
ANCHO_MOVIL = 360
ALTO_MOVIL = 740

_VACIOS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_SIN_TEXTO = {"script", "style", "template", "noscript"}

# Zonas comunes de cada página (contrato de interfaz, SPEC-LET-01 §6): se reconocen por su etiqueta o por su papel ARIA,
# que es como las anuncian los lectores de pantalla.
ZONAS = {
    "cabecera": ("header", "banner"),
    "menu": ("nav", "navigation"),
    "pie": ("footer", "contentinfo"),
}


# --- HTML -------------------------------------------------------------------------------------------------------


class Nodo:
    def __init__(self, tag, attrs, padre=None):
        self.tag = tag
        self.attrs = {k.lower(): ("" if v is None else v) for k, v in attrs}
        self.padre = padre
        self.hijos = []

    def texto(self):
        partes = []
        for hijo in self.hijos:
            if isinstance(hijo, str):
                partes.append(hijo)
            elif hijo.tag not in _SIN_TEXTO:
                partes.append(hijo.texto())
        return " ".join(" ".join(partes).split())

    def todos(self, *tags):
        for hijo in self.hijos:
            if isinstance(hijo, Nodo):
                if not tags or hijo.tag in tags:
                    yield hijo
                yield from hijo.todos(*tags)

    def primero(self, *tags):
        return next(self.todos(*tags), None)

    def por_id(self, ident):
        return next((n for n in self.todos() if n.attrs.get("id") == ident), None)

    def dentro_de_zona(self, *zonas):
        """¿Está dentro de alguna de las zonas («cabecera», «menu», «pie»), por etiqueta o por papel ARIA?"""
        nodo = self.padre
        while nodo is not None:
            papeles = nodo.attrs.get("role", "").lower().split()
            for zona in zonas:
                etiqueta, papel = ZONAS[zona]
                if nodo.tag == etiqueta or papel in papeles:
                    return True
            nodo = nodo.padre
        return False


class _Constructor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = Nodo("#documento", [])
        self.actual = self.raiz

    def handle_starttag(self, tag, attrs):
        nodo = Nodo(tag, attrs, self.actual)
        self.actual.hijos.append(nodo)
        if tag not in _VACIOS:
            self.actual = nodo

    def handle_endtag(self, tag):
        nodo = self.actual
        while nodo is not None and nodo.tag != tag:
            nodo = nodo.padre
        if nodo is not None and nodo.padre is not None:
            self.actual = nodo.padre

    def handle_data(self, data):
        self.actual.hijos.append(data)


def documento(html):
    constructor = _Constructor()
    constructor.feed(html)
    constructor.close()
    return constructor.raiz


def normaliza(texto):
    """Minúsculas, sin tildes ni signos de puntuación y con los espacios juntos: para buscar un dato en una página."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[,.;:()\"'«»·/\-]", " ", texto)
    return " ".join(texto.split())


# --- Sitio ------------------------------------------------------------------------------------------------------


def sitio_url():
    url = os.environ.get("SITIO_URL", "").strip().rstrip("/")
    if not url:
        pytest.fail("SITIO_URL sin definir: no hay ningún sitio de LET-01 que comprobar", pytrace=False)
    return url


def anfitrion():
    return urllib.parse.urlsplit(sitio_url()).hostname


def nuevo_abridor():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


class Respuesta:
    def __init__(self, status, cabeceras, cuerpo, url):
        self.status = status
        self.cabeceras = cabeceras
        self.cuerpo = cuerpo
        self.url = url
        self._doc = None

    @property
    def doc(self):
        if self._doc is None:
            self._doc = documento(self.cuerpo)
        return self._doc


def pedir(ruta, datos=None, cabeceras=None, abridor=None):
    url = ruta if ruta.startswith(("http://", "https://")) else sitio_url() + ruta
    peticion = urllib.request.Request(url, data=datos, headers={"User-Agent": "pruebas-let-01", **(cabeceras or {})})
    abridor = abridor or nuevo_abridor()
    try:
        with abridor.open(peticion, timeout=20) as r:
            juego = r.headers.get_content_charset() or "utf-8"
            return Respuesta(r.status, r.headers, r.read().decode(juego, "replace"), r.geturl())
    except urllib.error.HTTPError as e:
        juego = e.headers.get_content_charset() or "utf-8"
        return Respuesta(e.code, e.headers, e.read().decode(juego, "replace"), e.geturl())
    except (urllib.error.URLError, OSError) as e:
        motivo = getattr(e, "reason", e)
    # fuera del except: el fallo se lee en una línea, sin la cadena de excepciones
    pytest.fail(f"El sitio no responde en {url} ({motivo}): las páginas de LET-01 no están servidas", pytrace=False)


def pagina(ruta, abridor=None):
    """Pide una página que debe existir (200) y la devuelve con su árbol HTML en .doc."""
    respuesta = pedir(ruta, abridor=abridor)
    if respuesta.status != 200:
        pytest.fail(f"{ruta} responde {respuesta.status}, no 200", pytrace=False)
    return respuesta


def todas_las_paginas():
    return {nombre: pagina(ruta) for nombre, ruta in PAGINAS.items()}


def ruta_de(href, base):
    """Ruta normalizada (sin barra final, salvo «/») de un enlace del propio sitio; None si va fuera o no es un enlace."""
    if href is None:
        return None
    href = href.strip()
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    destino = urllib.parse.urlsplit(urllib.parse.urljoin(base, href))
    if destino.hostname and destino.hostname != urllib.parse.urlsplit(base).hostname:
        return None
    return destino.path.rstrip("/") or "/"


def lleva_logotipo(nodo):
    """¿Hay dentro del nodo una imagen o un SVG cuyo texto alternativo nombra la marca?"""
    marca = normaliza(MARCA)
    for img in nodo.todos("img"):
        if marca in normaliza(img.attrs.get("alt", "")):
            return True
    for svg in nodo.todos("svg"):
        etiquetas = [svg.attrs.get("aria-label", "")] + [t.texto() for t in svg.todos("title")]
        if any(marca in normaliza(e) for e in etiquetas):
            return True
    return False


def enlace_a_inicio_con_logotipo(respuesta, zonas=None):
    for enlace in respuesta.doc.todos("a"):
        if zonas and not enlace.dentro_de_zona(*zonas):
            continue
        if ruta_de(enlace.attrs.get("href"), respuesta.url) == "/" and lleva_logotipo(enlace):
            return True
    return False


# --- Titular ----------------------------------------------------------------------------------------------------

CAMPOS_TITULAR = ("nombre_fiscal", "nif", "domicilio", "correo")


def datos_titular():
    datos = json.loads(TITULAR.read_text(encoding="utf-8"))
    vacios = [c for c in CAMPOS_TITULAR if not str(datos.get(c, "")).strip()]
    if vacios:
        pytest.fail(
            f"Faltan los datos de la titular en {TITULAR.name}: {', '.join(vacios)} (cuestionario de la Fase 0, apartado C)",
            pytrace=False,
        )
    return {c: str(datos[c]).strip() for c in CAMPOS_TITULAR}


def nif_valido(nif):
    """DNI, NIE o CIF con su carácter de control correcto."""
    nif = nif.upper().replace("-", "").replace(" ", "")
    letras = "TRWAGMYFPDXBNJZSQVHLCKE"
    if re.fullmatch(r"\d{8}[A-Z]", nif):
        return letras[int(nif[:8]) % 23] == nif[8]
    if re.fullmatch(r"[XYZ]\d{7}[A-Z]", nif):
        return letras[int(str("XYZ".index(nif[0])) + nif[1:8]) % 23] == nif[8]
    if re.fullmatch(r"[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]", nif):
        cifras = [int(c) for c in nif[1:8]]
        pares = sum(cifras[1::2])
        impares = sum(sum(divmod(2 * c, 10)) for c in cifras[0::2])
        control = (10 - (pares + impares) % 10) % 10
        return nif[8] in (str(control), "JABCDEFGHI"[control])
    return False


# --- Formulario de contacto -------------------------------------------------------------------------------------


class FormularioContacto:
    """El formulario de /contacto/, leído como lo leería un navegador sin JavaScript.

    Contrato de interfaz (SPEC-LET-01 §6): campos «nombre», «correo», «mensaje», casilla «privacidad» y campo trampa
    «web»; la página que devuelve el envío lleva #envio-correcto o #envio-error.
    """

    def __init__(self):
        self.abridor = nuevo_abridor()
        self.pagina = pagina(PAGINAS["contacto"], self.abridor)
        self.nodo = None
        for form in self.pagina.doc.todos("form"):
            if any(n.attrs.get("name") == "correo" for n in form.todos("input", "textarea")):
                self.nodo = form
                break
        if self.nodo is None:
            pytest.fail("/contacto/ no tiene un formulario con el campo «correo»", pytrace=False)

    def campo(self, nombre):
        return next((n for n in self.nodo.todos("input", "textarea", "select") if n.attrs.get("name") == nombre), None)

    def enviar(self, valores, quitar=(), ficheros=None):
        """Envía el formulario como lo haría un navegador sin JavaScript. Con «ficheros» ({campo: (nombre, bytes, tipo)})
        lo envía como multipart/form-data con esas partes de fichero: lo que el formulario nunca manda (CA-LET-01-32)."""
        datos = []
        presentes = set()
        boton = None
        for n in self.nodo.todos("input", "textarea", "select", "button"):
            nombre = n.attrs.get("name")
            tipo = n.attrs.get("type", "submit" if n.tag == "button" else "text").lower()
            if tipo == "submit":
                boton = boton or (n if nombre else None)
                continue
            if not nombre or nombre in quitar or tipo in ("button", "reset", "file", "image"):
                continue
            presentes.add(nombre)
            if tipo in ("checkbox", "radio"):
                marcada = valores[nombre] if nombre in valores else ("checked" in n.attrs)
                if marcada:
                    datos.append((nombre, n.attrs.get("value") or "on"))
            elif nombre in valores:
                datos.append((nombre, valores[nombre]))
            else:
                datos.append((nombre, n.texto() if n.tag == "textarea" else n.attrs.get("value", "")))
        for nombre, valor in valores.items():
            if nombre not in presentes and nombre not in quitar and not isinstance(valor, bool):
                datos.append((nombre, valor))
        if boton is not None:
            datos.append((boton.attrs["name"], boton.attrs.get("value", "")))
        accion = urllib.parse.urljoin(self.pagina.url, self.nodo.attrs.get("action") or self.pagina.url)
        origen = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(self.pagina.url))
        if ficheros:
            cuerpo, tipo = _multipart(datos, ficheros)
            cabeceras = {"Content-Type": tipo, "Origin": origen, "Referer": self.pagina.url}
            return pedir(accion, datos=cuerpo, cabeceras=cabeceras, abridor=self.abridor)
        cuerpo = urllib.parse.urlencode(datos).encode("utf-8")
        cabeceras = {"Content-Type": "application/x-www-form-urlencoded", "Origin": origen, "Referer": self.pagina.url}
        if self.nodo.attrs.get("method", "get").lower() != "post":
            separador = "&" if "?" in accion else "?"
            return pedir(accion + separador + cuerpo.decode("ascii"), cabeceras=cabeceras, abridor=self.abridor)
        return pedir(accion, datos=cuerpo, cabeceras=cabeceras, abridor=self.abridor)


def _multipart(datos, ficheros):
    """Cuerpo multipart/form-data con los campos de «datos» y las partes de fichero de «ficheros», y su Content-Type."""
    limite = "----limite-let-01-" + uuid.uuid4().hex
    partes = []
    for nombre, valor in datos:
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{nombre}"\r\n\r\n{valor}\r\n'.encode("utf-8"))
    for nombre, (fichero, contenido, tipo) in ficheros.items():
        cabecera = f'--{limite}\r\nContent-Disposition: form-data; name="{nombre}"; filename="{fichero}"\r\nContent-Type: {tipo}\r\n\r\n'
        partes.append(cabecera.encode("utf-8") + contenido + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode("utf-8"))
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def valores_validos(marca):
    return {
        "nombre": "Ana Prueba",
        "correo": "visitante@ejemplo.es",
        "mensaje": f"Mensaje de prueba {marca}: quiero contaros algo que ha pasado en mi barrio.",
        "privacidad": True,
    }


# --- Buzón de pruebas (Mailpit) ---------------------------------------------------------------------------------


def buzon_url():
    url = os.environ.get("BUZON_URL", "").strip().rstrip("/")
    if not url:
        pytest.fail("BUZON_URL sin definir: falta el buzón de pruebas (Mailpit)", pytrace=False)
    return url


def correo_contacto():
    correo = os.environ.get("CORREO_CONTACTO", "").strip().lower()
    if not correo:
        pytest.fail("CORREO_CONTACTO sin definir: falta la dirección que recibe el formulario (decisión D2)", pytrace=False)
    return correo


def _buzon(metodo, ruta):
    peticion = urllib.request.Request(buzon_url() + ruta, method=metodo)
    try:
        with urllib.request.urlopen(peticion, timeout=10) as r:
            cuerpo = r.read()
    except (urllib.error.URLError, OSError) as e:
        motivo = getattr(e, "reason", e)
    else:
        return json.loads(cuerpo) if metodo == "GET" else None  # el DELETE de Mailpit contesta «ok», no JSON
    pytest.fail(f"El buzón de pruebas no responde en {buzon_url()} ({motivo})", pytrace=False)


def vaciar_buzon():
    _buzon("DELETE", "/api/v1/messages")


def mensajes():
    return (_buzon("GET", "/api/v1/messages?limit=50") or {}).get("messages") or []


def mensaje(ident):
    return _buzon("GET", f"/api/v1/message/{ident}")


def esperar_mensajes(cuantos=1, segundos=10):
    limite = time.monotonic() + segundos
    lista = mensajes()
    while len(lista) < cuantos and time.monotonic() < limite:
        time.sleep(0.5)
        lista = mensajes()
    return lista


def mensajes_tras_espera(segundos=3):
    """Lo que hay en el buzón pasados unos segundos: para comprobar que NO ha llegado nada."""
    time.sleep(segundos)
    return mensajes()


def direcciones(lista):
    return [(d.get("Address") or "").strip().lower() for d in (lista or [])]


def destinatarios(msg):
    return direcciones(msg.get("To")) + direcciones(msg.get("Cc")) + direcciones(msg.get("Bcc"))


# --- Navegador (Playwright, Chromium sin ventana) ---------------------------------------------------------------

# «Se ve en pantalla»: tiene tamaño, no está oculto ni transparente, cae dentro de la pantalla y un toque en su centro le
# llega a él (no a algo que lo tapa ni al contenedor que lo recorta). Así cuenta como oculto un menú plegado con
# display:none, con altura cero o desplazado fuera de la pantalla. Se mira cada trozo del elemento, por si ocupa dos líneas.
SE_VE = """el => {
    if (el.checkVisibility && !el.checkVisibility({opacityProperty: true, visibilityProperty: true})) return false;
    for (const r of el.getClientRects()) {
        if (r.width <= 0 || r.height <= 0) continue;
        const x = r.left + r.width / 2, y = r.top + r.height / 2;
        if (x < 0 || y < 0 || x >= window.innerWidth || y >= window.innerHeight) continue;
        const encima = document.elementFromPoint(x, y);
        if (encima && (encima === el || el.contains(encima))) return true;
    }
    return false;
}"""

# «Se ve en la página»: lo mismo, pero antes desplaza la página hasta donde está el elemento. Un campo visible al final de
# un formulario largo se ve aunque al cargar quede fuera de la pantalla; uno desplazado a la izquierda, a tamaño cero,
# recortado, transparente o sin dibujar sigue sin verse.
SE_VE_EN_LA_PAGINA = f"""el => {{
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) window.scrollTo(window.scrollX + r.left - 10, window.scrollY + r.top - 10);
    return ({SE_VE})(el);
}}"""

# «Fuera del árbol de accesibilidad»: lo que un lector de pantalla no anuncia. No se dibuja (hidden, display:none,
# visibility:hidden, propio o heredado), es un input type=hidden, o lo tapa un aria-hidden="true" propio o de un antecesor.
# Un campo desplazado fuera de la pantalla o transparente SÍ está en el árbol: el lector lo anuncia aunque no se vea.
FUERA_DEL_ARBOL_DE_ACCESIBILIDAD = """el => {
    if (el.type === 'hidden') return true;
    if (!el.checkVisibility({visibilityProperty: true})) return true;
    for (let n = el; n; n = n.parentElement) if (n.getAttribute('aria-hidden') === 'true') return true;
    return false;
}"""

# «Recibe el foco»: se dibuja, no está desactivado y su tabindex no es negativo: el tabulador llega a él.
RECIBE_EL_FOCO = """el => el.checkVisibility({visibilityProperty: true}) && !el.disabled && el.tabIndex >= 0"""


@contextmanager
def movil():
    """Una pestaña de móvil de 360×740 que respeta la etiqueta viewport y admite toques."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        try:
            contexto = navegador.new_context(
                viewport={"width": ANCHO_MOVIL, "height": ALTO_MOVIL},
                is_mobile=True,
                has_touch=True,
                device_scale_factor=2,
                locale="es-ES",
            )
            yield contexto.new_page()
        finally:
            navegador.close()
