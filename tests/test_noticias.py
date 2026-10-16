"""Comprobaciones de la sección de noticias (SPEC-LET-02) sobre el sitio servido.

Se corren contra la compilación de producción servida en local con el juego de pruebas de la spec cargado:

    SITIO=http://127.0.0.1:8080 DOMINIO=https://<dominio> JUEGO=tests/juego.json python3 tests/test_noticias.py [test ...]

- SITIO: dónde se sirve esa compilación (por defecto http://127.0.0.1:8080).
- DOMINIO: la dirección pública que la compilación escribe en canónicas, sitemap y robots.txt, sin barra final.
- JUEGO: el registro que deja el cargador del juego (por defecto tests/juego.json): un objeto JSON con una clave por noticia,
  de «A» a «H», y el estado que el gestor devuelve tras cargarla: «publicada», «borrador» o «retirada».

Sin argumentos corre todas; con nombres, solo esas. Sale 0 si todas pasan, 1 si alguna falla, 2 si se pide un test que no
existe y 3 si una comprobación revienta por un error propio o si Python corre con -O o PYTHONOPTIMIZE (sin assert no
comprobaría nada, así que no corre). Solo usa la biblioteca estándar de Python 3.9 o posterior y da lo mismo de 3.9 a 3.14
(las fechas ISO 8601 y robots.txt los lee ella misma: datetime.fromisoformat y urllib.robotparser cambian de una versión
a otra): no depende del gestor de contenidos que se elija. Cada test cita su criterio con un comentario
«# CA-LET-02-NN».
"""

import ipaddress
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

SITIO = os.environ.get("SITIO", "http://127.0.0.1:8080").rstrip("/")
DOMINIO = os.environ.get("DOMINIO", "").rstrip("/")
JUEGO = os.environ.get("JUEGO", "tests/juego.json")
ESPERA = 10

# Juego de pruebas (§5 de la spec): direcciones y textos que se cargan con el sitio.
A, B, C, D, E, F = (f"/noticias/prueba-{x}/" for x in "abcdef")
LISTA = "/noticias/"
TITULAR = {
    A: "Noticia de prueba A",
    B: "Noticia de prueba B",
    C: "Noticia de prueba C corregida",
    D: "Noticia de prueba D",
    E: "Noticia de prueba E",
}
TITULAR_C_ANTES = "Noticia de prueba C"
TITULAR_F = 'Noticia de prueba F: «Año Nuevo», "comillas" & </script>'
TITULAR_F_SIN_ETIQUETA = 'Noticia de prueba F: «Año Nuevo», "comillas" &'
TITULAR_REPETIDO = "Noticia de prueba repetida: Año Nuevo en Talavera"
ENTRADILLA_A = "Entradilla de la prueba A."
TEXTO_A = "Texto de la prueba A."
TEXTO_F_ANTES = "Texto de la prueba F."  # F se corrigió después de publicarla, y antes de corregir C (al revés que se crearon)
TEXTO_F_CORREGIDO = "Texto de la prueba F, corregido."
FECHA_A = "7 de octubre de 2026"
FECHA_A_ENTERA = re.compile(r"(?<![0-9])" + re.escape(FECHA_A) + r"(?![0-9])")  # «17 de octubre de 2026» no vale
FECHA_C = "9 de octubre de 2026"  # C se corrigió después: esta fecha solo puede ser la de publicación
FECHA_C_ENTERA = re.compile(r"(?<![0-9])" + re.escape(FECHA_C) + r"(?![0-9])")
PUBLICADA_A = datetime(2026, 10, 7, 8, 0, tzinfo=timezone.utc)  # 7-10-2026 a las 10:00, hora de Madrid
FUENTE_A = "Fuente: Ayuntamiento de Talavera de la Reina, nota de prensa del 6 de octubre de 2026"
FOTO_A = "Foto: Autora de prueba"
FICHERO_FOTO_A = "foto-prueba-a"
NS_SITEMAP = "http://www.sitemaps.org/schemas/sitemap/0.9"
MADRID = ZoneInfo("Europe/Madrid")


# ---------------------------------------------------------------- peticiones


class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


_ABRIDOR = urllib.request.build_opener(_SinRedirecciones)


class Respuesta:
    def __init__(self, url, codigo, cabeceras, cuerpo):
        self.url, self.codigo, self.cabeceras, self.cuerpo = url, codigo, cabeceras, cuerpo

    @property
    def html(self):
        juego = self.cabeceras.get_content_charset() or "utf-8"
        return self.cuerpo.decode(juego, errors="replace")

    @property
    def texto(self):
        """Como html, sin el BOM UTF-8 del principio: Google lo ignora al leer robots.txt, y con él la primera línea no casaría."""
        return self.html.lstrip("\ufeff")


def pedir(url):
    """GET sin seguir redirecciones: la dirección pedida es la que tiene que responder."""
    url = urllib.parse.quote(url, safe=":/?#[]@!$&'()*+,;=%~")  # una «ñ» en la dirección se pide codificada
    peticion = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (comprobaciones de noticias)"})
    try:
        with _ABRIDOR.open(peticion, timeout=ESPERA) as r:
            return Respuesta(url, r.status, r.headers, r.read())
    except urllib.error.HTTPError as e:
        return Respuesta(url, e.code, e.headers, e.read())
    except (urllib.error.URLError, OSError) as e:
        raise AssertionError(f"no responde {url}: {getattr(e, 'reason', e)} (no hay sitio servido en SITIO={SITIO})")


def _hosts():
    return {urllib.parse.urlsplit(u).netloc for u in (SITIO, DOMINIO) if u}


def local(url, base=None):
    """Lleva al SITIO una dirección del propio sitio (relativa o absoluta con el host de SITIO o DOMINIO)."""
    url = urllib.parse.urljoin(base or SITIO + "/", url)
    p = urllib.parse.urlsplit(url)
    if p.netloc in _hosts():
        return SITIO + urllib.parse.urlunsplit(("", "", p.path or "/", p.query, ""))
    return url


def ruta_de(href, base):
    """Ruta de un enlace del propio sitio, sin codificar (%C3%B1 pasa a ñ), o None si apunta fuera."""
    p = urllib.parse.urlsplit(urllib.parse.urljoin(base, href))
    return urllib.parse.unquote(p.path) if p.netloc in _hosts() else None


def pagina(ruta):
    r = pedir(SITIO + ruta)
    assert r.codigo == 200, f"{ruta} responde {r.codigo}; se esperaba 200"
    return r


def codigo(ruta):
    return pedir(SITIO + ruta).codigo


_NO_PUBLICOS = {"localhost", "localdomain", "local", "test", "example", "invalid", "internal", "intranet", "lan", "home"}


def es_publico(host):
    """¿Un host está en Internet, y no en esta máquina ni en una red privada? Una IP escrita de cualquier forma que el
    sistema entienda («127.1», «0x7f.1» y «2130706433» son 127.0.0.1) cuenta como la IP que es."""
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        pass
    try:
        return ipaddress.IPv4Address(socket.inet_aton(host)).is_global
    except OSError:
        pass
    partes = host.lower().rstrip(".").split(".")
    return len(partes) >= 2 and all(partes) and partes[-1] not in _NO_PUBLICOS


def resueltas_no_publicas(host):
    """Direcciones de esta máquina o de una red privada a las que resuelve un nombre (vacío si todas son públicas).
    Falla si el nombre no se resuelve: entonces no hay sitio publicado al que preguntar."""
    try:
        direcciones = sorted({i[4][0] for i in socket.getaddrinfo(host, None)})
    except OSError as e:
        raise AssertionError(f"el nombre {host} no se resuelve ({e}): no hay sitio publicado al que preguntar")
    return [d for d in direcciones if not ipaddress.ip_address(d.split("%", 1)[0]).is_global]


def dominio(resolver=False):
    """DOMINIO comprobado: una dirección pública. Con resolver, además el nombre tiene que resolverse a IP públicas (uno
    que apunte a esta máquina, como 127.0.0.1.nip.io o una entrada de /etc/hosts, no es el sitio publicado)."""
    assert re.match(r"^https?://[^/]+$", DOMINIO), "falta DOMINIO (la dirección pública del sitio, p. ej. https://ejemplo.es)"
    host = urllib.parse.urlsplit(DOMINIO).hostname or ""
    assert es_publico(host), f"DOMINIO={DOMINIO} no es una dirección pública (localhost, IP de esta máquina o privada, .local, .test…)"
    if resolver:
        locales = resueltas_no_publicas(host)
        assert not locales, f"DOMINIO={DOMINIO} resuelve a direcciones de esta máquina o de una red privada {locales}: no es el sitio publicado"
    return DOMINIO


def registro_del_juego():
    """Lo que el cargador apuntó tras cargar el juego: {letra: estado}, con el estado que el gestor devuelve."""
    try:
        with open(JUEGO, encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError:
        raise AssertionError(f"no existe el registro del juego {JUEGO}: el cargador no lo escribió (variable JUEGO)")
    except (OSError, ValueError) as e:
        raise AssertionError(f"el registro del juego {JUEGO} no se puede leer: {e}")
    assert isinstance(datos, dict), f"{JUEGO}: se esperaba un objeto con una clave por noticia (A a H) y su estado"
    return datos


def estado_en_el_juego(letra):
    datos = registro_del_juego()
    assert letra in datos, f"{JUEGO} no tiene la noticia {letra}: el cargador no la creó"
    return str(datos[letra] or "").strip().lower()


# ---------------------------------------------------------------- lectura del HTML


def limpia(s):
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def comillas(s):
    """Iguala las comillas tipográficas con las rectas (algunos gestores las cambian al mostrar el titular)."""
    return limpia(s).translate(str.maketrans({"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'"}))


_BLOQUES = set(
    "address article aside blockquote br dd div dl dt figcaption figure footer form h1 h2 h3 h4 h5 h6 header hr "
    "li main nav ol p pre section table tbody td th thead tr ul".split()
)
_INVISIBLES = {"script", "style", "template", "noscript"}


class Documento(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.trozos, self.h1, self.enlaces, self.imagenes, self.fuentes = [], [], [], [], []
        self.metas, self.links, self.jsonld = [], [], []
        self._invisible, self._h1, self._a, self._ld, self._picture = 0, None, None, None, 0
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in _INVISIBLES:
            self._invisible += 1
            if tag == "script" and "ld+json" in a.get("type", "").lower():
                self._ld = []
            return
        if tag in _BLOQUES:
            self.trozos.append(" ")
        if tag == "h1":
            self._h1 = []
        elif tag == "a":
            self._a = [a.get("href", ""), []]
        elif tag == "img":
            self.imagenes.append(a)
        elif tag == "picture":
            self._picture += 1
        elif tag == "source" and self._picture:
            self.fuentes.append(a)  # el navegador prefiere estas al <img> del <picture>
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)

    def handle_endtag(self, tag):
        if tag in _INVISIBLES:
            self._invisible = max(0, self._invisible - 1)
            if tag == "script" and self._ld is not None:
                self.jsonld.append("".join(self._ld))
                self._ld = None
            return
        if tag in _BLOQUES:
            self.trozos.append(" ")
        if tag == "h1" and self._h1 is not None:
            self.h1.append(limpia("".join(self._h1)))
            self._h1 = None
        elif tag == "a" and self._a is not None:
            self.enlaces.append((self._a[0], limpia("".join(self._a[1]))))
            self._a = None
        elif tag == "picture":
            self._picture = max(0, self._picture - 1)

    def handle_data(self, data):
        if self._ld is not None:
            self._ld.append(data)
            return
        if self._invisible:
            return
        self.trozos.append(data)
        if self._h1 is not None:
            self._h1.append(data)
        if self._a is not None:
            self._a[1].append(data)

    @property
    def texto(self):
        return limpia("".join(self.trozos))


def documento(ruta):
    return Documento(pagina(ruta).html)


def muestra(html, titulares):
    """Titulares que aparecen en una página: en el código tal cual o en el texto visible, con las entidades resueltas y
    los espacios igualados («prueba&nbsp;D» o un titular partido en dos <span> también cuentan)."""
    texto = Documento(html).texto
    return [t for t in titulares if t in html or t in texto]


def enlaces_a_noticias(doc, base):
    """Rutas /noticias/<dirección>/ enlazadas desde una página, en el orden en que aparecen y sin repetir."""
    vistas = []
    for href, _ in doc.enlaces:
        r = ruta_de(href, base)
        if r and re.fullmatch(r"/noticias/[^/]+/", r) and r not in vistas:
            vistas.append(r)
    return vistas


def candidatas(srcset):
    """Direcciones de un srcset («a.jpg 1x, b.jpg 2x» o «a.jpg 400w»), partido como lo hace el navegador: cada dirección
    llega hasta el primer espacio, así que una coma dentro de ella («…/w_400,h_300/foto.jpg 400w») no la rompe, y los
    descriptores que la siguen van hasta la coma que separa la siguiente. Los datos incrustados (data:) no se piden."""
    direcciones, i, n = [], 0, len(srcset)
    while i < n:
        while i < n and (srcset[i].isspace() or srcset[i] == ","):
            i += 1
        j = i
        while j < n and not srcset[j].isspace():
            j += 1
        url = srcset[i:j]
        if not url:
            break
        if url.endswith(","):  # «a.jpg, b.jpg 2x»: la coma pegada cierra la candidata sin descriptores
            url = url.rstrip(",")
            i = j
        else:
            k = srcset.find(",", j)
            i = n if k < 0 else k + 1
        if url and not url.startswith("data:"):
            direcciones.append(url)
    return direcciones


def noticias_estructuradas(doc, ruta):
    """Nodos NewsArticle de los bloques JSON-LD, estén donde estén (@type en lista, en @graph o anidados en otro nodo,
    como mainEntity de una WebPage). Falla si un bloque no es JSON válido."""
    nodos = []

    def recorre(x):
        if isinstance(x, list):
            for y in x:
                recorre(y)
        elif isinstance(x, dict):
            tipo = x.get("@type")
            tipos = tipo if isinstance(tipo, list) else [tipo]
            if "NewsArticle" in tipos:
                nodos.append(x)
            for v in x.values():
                recorre(v)

    for bloque in doc.jsonld:
        try:
            recorre(json.loads(bloque))
        except json.JSONDecodeError as e:
            raise AssertionError(f"{ruta}: un bloque de datos estructurados no es JSON válido ({e}): {bloque[:120]!r}")
    return nodos


def una_noticia_estructurada(doc, ruta):
    nodos = noticias_estructuradas(doc, ruta)
    assert len(nodos) == 1, f"{ruta}: hay {len(nodos)} bloques NewsArticle; se esperaba exactamente 1"
    return nodos[0]


def nodos_por_id(doc):
    """Nodos JSON-LD con contenido, por su @id, para resolver referencias como {"@id": "…#primaryimage"}."""
    ids = {}

    def recorre(x):
        if isinstance(x, list):
            for y in x:
                recorre(y)
        elif isinstance(x, dict):
            if isinstance(x.get("@id"), str) and len(x) > 1:
                ids.setdefault(x["@id"], x)
            for v in x.values():
                recorre(v)

    for bloque in doc.jsonld:
        try:
            recorre(json.loads(bloque))
        except json.JSONDecodeError:
            pass  # ya lo señala noticias_estructuradas
    return ids


def direcciones_de_imagen(valor, ids, profundidad=0):
    """Direcciones de una propiedad image: texto, lista, ImageObject (url, contentUrl) o referencia @id a un ImageObject."""
    if profundidad > 5:
        return []
    if isinstance(valor, str):
        return [valor]
    if isinstance(valor, list):
        return [u for v in valor for u in direcciones_de_imagen(v, ids, profundidad + 1)]
    if isinstance(valor, dict):
        propias = [valor[k] for k in ("url", "contentUrl") if k in valor]
        if propias:
            return direcciones_de_imagen(propias, ids, profundidad + 1)
        nodo = ids.get(valor.get("@id"))
        if nodo is not None and nodo is not valor:
            return direcciones_de_imagen(nodo, ids, profundidad + 1)
    return []


_DIRECTIVAS = set(
    "all noindex nofollow none nosnippet indexifembedded max-snippet max-image-preview max-video-preview notranslate "
    "noimageindex unavailable_after noarchive nocache".split()
)


def impide_indexar(valor, admite_robot=False):
    """¿Unas directivas robots (contenido de un meta o valor de X-Robots-Tag) impiden a Google indexar?

    Solo cuentan noindex y none como directiva entera: max-image-preview:none sí deja indexar. Con admite_robot, un valor
    «otrorobot: noindex» (prefijo de X-Robots-Tag) solo cuenta si el robot es googlebot."""
    valor = valor.strip().lower()
    if admite_robot:
        m = re.match(r"([a-z][a-z0-9_-]*)\s*:\s*(.*)$", valor, re.S)
        if m and m.group(1) not in _DIRECTIVAS:
            if m.group(1) != "googlebot":
                return False
            valor = m.group(2)
    return any(d.split(":", 1)[0].strip() in ("noindex", "none") for d in valor.split(","))


def reglas_robots(texto, robot="googlebot"):
    """Reglas de robots.txt que aplica un robot, como Google: el grupo con su User-agent (los grupos repetidos se suman) o,
    si no hay, el de «*». Devuelve [(permite, patrón)]."""
    grupos, actual, con_reglas = [], None, False
    for linea in texto.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if ":" not in linea:
            continue
        campo, valor = (x.strip() for x in linea.split(":", 1))
        campo = campo.lower()
        if campo == "user-agent":
            if actual is None or con_reglas:
                actual, con_reglas = ([], []), False
                grupos.append(actual)
            m = re.match(r"\*|[A-Za-z_-]+", valor)
            actual[0].append(m.group(0).lower() if m else "")
        elif campo in ("allow", "disallow") and actual is not None:
            con_reglas = True
            if valor:
                actual[1].append((campo == "allow", valor))
    for agente in (robot, "*"):
        if any(agente in agentes for agentes, _ in grupos):
            return [r for agentes, reglas in grupos if agente in agentes for r in reglas]
    return []


def robots_permite(reglas, ruta):
    """Como Google: gana la regla más larga que casa con la ruta; «*» es cualquier cosa y «$» el final; empate, Allow."""
    mejor = None
    for permite, patron in reglas:
        rx = re.escape(patron).replace("\\*", ".*")
        if rx.endswith("\\$"):
            rx = rx[:-2] + "$"
        if re.match(rx, ruta):
            clave = (len(patron), permite)
            mejor = clave if mejor is None or clave > mejor else mejor
    return mejor is None or mejor[1]


_FECHA_ISO = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d+))?)?\s*(Z|z|[+-]\d{2}(?::?\d{2})?)?$"
)


def fecha_iso(valor, campo, ruta):
    """Fecha ISO 8601 con hora y zona horaria (+02:00, +0200, +02 o Z), leída igual en 3.9 que en 3.14: fromisoformat
    acepta «+0200» solo desde 3.11."""
    assert isinstance(valor, str) and valor, f"{ruta}: falta {campo} en los datos estructurados"
    m = _FECHA_ISO.match(valor.strip())
    assert m, f"{ruta}: {campo}={valor!r} no es una fecha ISO 8601 con hora (AAAA-MM-DDTHH:MM:SS+HH:MM)"
    zona = m.group(8)
    assert zona, f"{ruta}: {campo}={valor!r} no lleva zona horaria"
    try:
        if zona.upper() == "Z":
            tz = timezone.utc
        else:
            cifras = zona[1:].replace(":", "")
            desvio = timedelta(hours=int(cifras[:2]), minutes=int(cifras[2:] or 0))
            tz = timezone(desvio if zona[0] == "+" else -desvio)
        micro = int((m.group(7) or "0")[:6].ljust(6, "0"))
        return datetime(*(int(m.group(i)) for i in range(1, 6)), int(m.group(6) or 0), micro, tzinfo=tz)
    except ValueError as e:
        raise AssertionError(f"{ruta}: {campo}={valor!r} no es una fecha válida ({e})")


def sitemaps(base, mapear=True):
    """Lee los sitemaps que declara robots.txt (o /sitemap.xml si no declara ninguno) y sigue los índices.

    Con mapear, cada sitemap se pide al SITIO por su ruta, sea cual sea el host que lleve su dirección.
    Devuelve [(url_del_fichero, raíz_xml, [loc, ...])]. Falla si un fichero no responde 200 o no es XML bien formado."""
    robots = pedir(base + "/robots.txt")
    declarados = []
    if robots.codigo == 200:
        declarados = [l.split(":", 1)[1].strip() for l in robots.texto.splitlines() if l.strip().lower().startswith("sitemap:")]
    pendientes, vistos, leidos = list(declarados or [base + "/sitemap.xml"]), set(), []
    while pendientes and len(vistos) < 50:
        url = pendientes.pop(0)
        if url in vistos:
            continue
        vistos.add(url)
        r = pedir(SITIO + (urllib.parse.urlsplit(url).path or "/") if mapear else url)
        assert r.codigo == 200, f"el sitemap {url} responde {r.codigo}"
        try:
            raiz = ET.fromstring(r.cuerpo)
        except ET.ParseError as e:
            raise AssertionError(f"el sitemap {url} no es XML bien formado: {e}")
        locs = [limpia(e.text or "") for e in raiz.iter(f"{{{NS_SITEMAP}}}loc")]
        leidos.append((url, raiz, locs))
        if raiz.tag == f"{{{NS_SITEMAP}}}sitemapindex":
            pendientes.extend(locs)
    assert leidos, "no se encontró ningún sitemap"
    return leidos


def direcciones_del_sitemap(base=None, mapear=True):
    """Todas las direcciones (loc) de los sitemaps urlset, tal cual las escribe el sitemap."""
    base = base or SITIO
    return [l for _, raiz, locs in sitemaps(base, mapear) if raiz.tag == f"{{{NS_SITEMAP}}}urlset" for l in locs]


def rutas_de(direcciones):
    return {urllib.parse.unquote(urllib.parse.urlsplit(l).path) for l in direcciones}


def rutas_del_sitemap(base=None, mapear=True):
    return rutas_de(direcciones_del_sitemap(base, mapear))


# ---------------------------------------------------------------- criterios


def test_ca_let_02_01_lista_en_orden():
    # CA-LET-02-01
    doc = documento(LISTA)
    vistas = [r for r in enlaces_a_noticias(doc, SITIO + LISTA) if re.fullmatch(r"/noticias/prueba-[a-z]/", r)]
    assert vistas == [C, B, A, F], (
        f"la lista enlaza {vistas}; se esperaba {[C, B, A, F]} (por fecha de publicación, la más reciente primero, sin D ni E; "
        f"F se corrigió la última y se creó después de C: ordenar por modificación o por creación la adelanta)"
    )


def test_ca_let_02_02_lista_con_titular_y_fecha():
    # CA-LET-02-02
    doc = documento(LISTA)
    assert TITULAR[A] in doc.texto, f"la lista no muestra el titular «{TITULAR[A]}»"
    assert FECHA_A_ENTERA.search(doc.texto), f"la lista no muestra la fecha «{FECHA_A}»"
    assert FECHA_C_ENTERA.search(doc.texto), f"la lista no muestra «{FECHA_C}», la fecha de publicación de C (la de su corrección no vale)"
    destinos = {ruta_de(h, SITIO + LISTA) for h, t in doc.enlaces if TITULAR[A] in t}
    assert A in destinos, f"en la lista, el titular «{TITULAR[A]}» no enlaza a {A} (enlaza a {destinos or 'nada'})"


def test_ca_let_02_03_cada_publicada_tiene_su_pagina():
    # CA-LET-02-03
    codigos = {r: codigo(r) for r in (A, B, C, F)}
    assert all(c == 200 for c in codigos.values()), f"códigos: {codigos}; se esperaba 200 en las cuatro"


def test_ca_let_02_04_titular_corregido_misma_direccion():
    # CA-LET-02-04
    doc = documento(C)
    assert TITULAR[C] in doc.h1, f"{C}: el titular principal es {doc.h1}; se esperaba «{TITULAR[C]}»"
    assert TITULAR_C_ANTES not in doc.h1, f"{C}: sigue mostrando el titular anterior «{TITULAR_C_ANTES}»"
    lista = documento(LISTA)
    destinos = {ruta_de(h, SITIO + LISTA) for h, t in lista.enlaces if TITULAR[C] in t}
    assert destinos == {C}, f"en la lista, «{TITULAR[C]}» enlaza a {destinos or 'nada'}; se esperaba solo {C}"


def test_ca_let_02_05_ficha_completa():
    # CA-LET-02-05
    doc = documento(A)
    assert TITULAR[A] in doc.h1, f"{A}: el titular principal (h1) es {doc.h1}; se esperaba «{TITULAR[A]}»"
    faltan = [t for t in (ENTRADILLA_A, TEXTO_A) if t not in doc.texto]
    faltan += [] if FECHA_A_ENTERA.search(doc.texto) else [FECHA_A]
    assert not faltan, f"{A}: no se ve {faltan}"
    assert FECHA_C_ENTERA.search(documento(C).texto), (
        f"{C}: no se ve «{FECHA_C}», su fecha de publicación (C se corrigió después: la fecha de la corrección no vale)"
    )


def test_ca_let_02_06_fuente_citada():
    # CA-LET-02-06
    doc = documento(A)
    assert FUENTE_A in doc.texto, f"{A}: no se lee «{FUENTE_A}»"


def test_ca_let_02_07_credito_de_la_foto():
    # CA-LET-02-07
    doc = documento(A)
    assert FOTO_A in doc.texto, f"{A}: no se lee «{FOTO_A}»"


def test_ca_let_02_08_imagenes_sin_romper():
    # CA-LET-02-08
    cargadas, foto_a = {}, False
    for ruta in (A, B):
        doc = documento(ruta)
        direcciones = []
        for img in doc.imagenes:
            src = img.get("src", "").strip()
            assert src, f"{ruta}: hay un <img> sin src o con src vacío"
            direcciones += [src] + candidatas(img.get("srcset", ""))
        for fuente in doc.fuentes:
            srcset = fuente.get("srcset", "").strip()
            assert srcset, f"{ruta}: hay un <source> de un <picture> sin srcset o con srcset vacío"
            direcciones += candidatas(srcset)
        if ruta == A and FICHERO_FOTO_A in " ".join(direcciones):
            foto_a = True
        for c in direcciones:
            if c.startswith("data:image/"):
                continue
            url = local(c, SITIO + ruta)
            if url not in cargadas:
                r = pedir(url)
                cargadas[url] = (r.codigo, r.cabeceras.get_content_type())
            cod, tipo = cargadas[url]
            assert cod == 200 and tipo.startswith("image/"), f"{ruta}: la imagen {c} no carga ({cod}, {tipo})"
    assert foto_a, f"{A}: no muestra su foto (ningún <img> ni <source> de un <picture> lleva «{FICHERO_FOTO_A}» en src o srcset)"


def test_ca_let_02_09_sin_rotulos_vacios():
    # CA-LET-02-09
    doc = documento(B)
    assert TITULAR[B] in doc.h1, f"{B}: el titular principal es {doc.h1}; se esperaba «{TITULAR[B]}»"
    rotulos = re.findall(r"(?:fuente|foto):[^.]{0,40}", doc.texto, re.IGNORECASE)  # «FUENTE:» vacío tampoco vale
    assert not rotulos, f"{B} no tiene foto ni nota de prensa y aun así muestra {rotulos}"


def test_ca_let_02_10_borrador_no_existe():
    # CA-LET-02-10
    assert codigo(A) == 200, f"{A} no responde 200: no hay sitio con el juego de pruebas"
    estado = estado_en_el_juego("D")
    assert estado == "borrador", f"D se creó sin tocar su estado y el gestor la dejó en «{estado}»; una noticia nueva nace en borrador"
    cod = codigo(D)
    assert cod == 404, f"{D} (borrador) responde {cod}; se esperaba 404"


def test_ca_let_02_11_borrador_fuera_de_portada_y_lista():
    # CA-LET-02-11
    assert TITULAR[A] in documento(LISTA).texto, "la lista no muestra la noticia A: no hay sitio con el juego de pruebas"
    estado = estado_en_el_juego("D")
    assert estado == "borrador", f"D se creó sin tocar su estado y el gestor la dejó en «{estado}»; sin D en borrador no hay nada que comprobar"
    con_d = [r for r in ("/", LISTA, A) if muestra(pagina(r).html, [TITULAR[D]])]
    assert not con_d, f"el titular del borrador «{TITULAR[D]}» aparece en {con_d} (en el código o en el texto visible)"


def test_ca_let_02_12_retirada_no_se_ve():
    # CA-LET-02-12
    assert codigo(A) == 200, f"{A} no responde 200: no hay sitio con el juego de pruebas"
    estado = estado_en_el_juego("E")
    assert estado == "retirada", f"E se publicó y se retiró después, y el gestor la tiene en «{estado}»"
    cod = codigo(E)
    assert cod in (404, 410), f"{E} (retirada) responde {cod}; se esperaba 404 o 410"
    con_e = [r for r in ("/", LISTA, A) if muestra(pagina(r).html, [TITULAR[E]])]
    assert not con_e, f"el titular de la retirada «{TITULAR[E]}» aparece en {con_e} (en el código o en el texto visible)"


def test_ca_let_02_13_datos_estructurados_de_noticia():
    # CA-LET-02-13
    doc = documento(A)
    n = una_noticia_estructurada(doc, A)
    assert comillas(str(n.get("headline", ""))) == TITULAR[A], f"{A}: headline={n.get('headline')!r}; se ve «{TITULAR[A]}»"
    publicada = str(n.get("datePublished", "")).strip()
    try:
        dia = fecha_iso(publicada, "datePublished", A).astimezone(MADRID).date().isoformat()
    except AssertionError:
        dia = publicada[:10]  # sin hora o sin zona cuenta el día tal cual lo escribe; la zona la exige CA-LET-02-15
    assert dia == "2026-10-07", f"{A}: datePublished={publicada!r}; la fecha que se ve es el 7-10-2026"
    imagenes = direcciones_de_imagen(n.get("image"), nodos_por_id(doc))
    assert imagenes, f"{A}: el NewsArticle no lleva imagen (image={n.get('image')!r}) y la noticia tiene foto"
    assert any(FICHERO_FOTO_A in str(u) for u in imagenes), f"{A}: la imagen del NewsArticle {imagenes} no es su foto ({FICHERO_FOTO_A})"


def test_ca_let_02_14_titular_con_signos():
    # CA-LET-02-14
    doc = documento(F)
    vistos = [comillas(h) for h in doc.h1]
    validos = [h for h in vistos if h in (comillas(TITULAR_F), comillas(TITULAR_F_SIN_ETIQUETA))]
    assert validos, f"{F}: el titular principal es {doc.h1}; se esperaba «{TITULAR_F}»"
    n = una_noticia_estructurada(doc, F)
    assert comillas(str(n.get("headline", ""))) == validos[0], f"{F}: headline={n.get('headline')!r}; se ve «{validos[0]}»"


def test_ca_let_02_15_fechas_con_zona_horaria():
    # CA-LET-02-15
    n = una_noticia_estructurada(documento(A), A)
    publicada = fecha_iso(n.get("datePublished"), "datePublished", A)
    modificada_a = fecha_iso(n.get("dateModified"), "dateModified", A)
    assert publicada == PUBLICADA_A, f"{A}: datePublished={n.get('datePublished')!r}; se esperaba el 7-10-2026 a las 10:00 de Madrid"
    assert modificada_a >= publicada, f"{A}: dateModified es anterior a datePublished"
    doc_f = documento(F)
    assert TEXTO_F_CORREGIDO in doc_f.texto, f"{F}: no se ve «{TEXTO_F_CORREGIDO}»: la corrección de F no llegó al sitio"
    assert TEXTO_F_ANTES not in doc_f.texto, f"{F}: sigue mostrando el texto anterior «{TEXTO_F_ANTES}»"
    modificadas = {}
    for ruta, docx in ((F, doc_f), (C, documento(C))):  # las dos se corrigieron después de publicarlas: primero F, luego C
        nx = una_noticia_estructurada(docx, ruta)
        px = fecha_iso(nx.get("datePublished"), "datePublished", ruta)
        modificadas[ruta] = mx = fecha_iso(nx.get("dateModified"), "dateModified", ruta)
        assert mx > px, f"{ruta} se corrigió después de publicarse y dateModified ({nx.get('dateModified')}) no es posterior a datePublished"
    assert modificadas[C] > modificadas[F], (
        f"C se corrigió después que F y su dateModified ({modificadas[C].isoformat()}) no es posterior al de F "
        f"({modificadas[F].isoformat()}): ¿dateModified es la hora de compilación o de carga (igual en todas) o la de "
        f"creación de cada noticia (F se creó después de C) y no la de cada corrección?"
    )
    # A no se corrigió nunca y se pide la última, después de F y C: una hora de petición o de generar cada página al
    # compilar (en orden de publicación) la dejaría cambiar de una petición a otra o después de F.
    n_al_final = una_noticia_estructurada(documento(A), A)
    modificada_a_al_final = fecha_iso(n_al_final.get("dateModified"), "dateModified", A)
    assert modificada_a_al_final == modificada_a, (
        f"{A} no se corrigió y su dateModified cambia de una petición a otra ({modificada_a.isoformat()} y "
        f"{modificada_a_al_final.isoformat()}): ¿es la hora de cada petición?"
    )
    assert modificada_a_al_final < modificadas[F], (
        f"{A} no se corrigió y su dateModified ({modificada_a_al_final.isoformat()}) no es anterior al de F, que se corrigió "
        f"después ({modificadas[F].isoformat()}): ¿es la hora de cada petición o de generar cada página al compilar?"
    )


def test_ca_let_02_16_sitemap_con_las_publicadas():
    # CA-LET-02-16
    lista = documento(LISTA)
    enlazadas = set(enlaces_a_noticias(lista, SITIO + LISTA))
    assert {A, B, C, F} <= enlazadas, f"la lista no enlaza A, B, C y F ({sorted(enlazadas)}): no hay sitio con el juego"
    repetidas = _repetidas(lista)  # G y H, por las dos direcciones a las que la lista enlaza su titular
    assert len(repetidas) == 2, (
        f"la lista enlaza «{TITULAR_REPETIDO}» (G y H) a {repetidas or 'nada'}; sin sus dos direcciones no se puede "
        f"comprobar que el sitemap lleva las seis publicadas"
    )
    publicadas = {A, B, C, F} | set(repetidas)  # las seis del juego; otros enlaces (paginación, feed) no se exigen
    locs = direcciones_del_sitemap()
    rutas = rutas_de(locs)
    faltan = sorted(publicadas - rutas)
    sobran = sorted({D, E} & rutas)
    assert not faltan, f"el sitemap no lleva estas noticias publicadas: {faltan}"
    assert not sobran, f"el sitemap lleva noticias no publicadas: {sobran}"
    # Un borrador o una retirada también se cuelan con un enlace por número (/?p=104) que no es su ruta: cada dirección tiene
    # que abrir algo. Las de otro dominio no se piden aquí: las rechaza CA-LET-02-18.
    propias = sorted({l for l in locs if urllib.parse.urlsplit(l).netloc in _hosts()})
    rotas = {l: c for l in propias if (c := pedir(local(l)).codigo) != 200}
    assert not rotas, f"el sitemap lleva direcciones que no responden 200 (¿un borrador o una retirada por su número?): {rotas}"


def test_ca_let_02_17_sitemap_bien_formado():
    # CA-LET-02-17
    leidos = sitemaps(SITIO)
    raices = {f"{{{NS_SITEMAP}}}urlset", f"{{{NS_SITEMAP}}}sitemapindex"}
    malos = [url for url, raiz, _ in leidos if raiz.tag not in raices]
    assert not malos, f"no son sitemaps (urlset o sitemapindex del espacio {NS_SITEMAP}): {malos}"
    assert any(raiz.tag == f"{{{NS_SITEMAP}}}urlset" for _, raiz, _ in leidos), "ningún sitemap lista direcciones (urlset)"


def test_ca_let_02_18_sitemap_con_direcciones_publicas():
    # CA-LET-02-18
    locs = [l for _, _, ls in sitemaps(SITIO) for l in ls]
    assert locs, "el sitemap no lleva ninguna dirección"
    base = dominio() + "/"
    ajenas = [l for l in locs if not l.startswith(base)]
    assert not ajenas, f"direcciones del sitemap que no son completas ni de {base}: {ajenas[:5]}"


def test_ca_let_02_19_robots_senala_el_sitemap():
    # CA-LET-02-19
    r = pedir(SITIO + "/robots.txt")
    assert r.codigo == 200, f"/robots.txt responde {r.codigo}"
    lineas = [l.split(":", 1)[1].strip() for l in r.texto.splitlines() if l.strip().lower().startswith("sitemap:")]
    assert lineas, "robots.txt no tiene ninguna línea «Sitemap:»"
    base = dominio() + "/"
    ajenas = [l for l in lineas if not l.startswith(base)]
    assert not ajenas, f"líneas Sitemap que no son direcciones completas de {base}: {ajenas}"
    rotas = [(l, c) for l in lineas if (c := pedir(local(l)).codigo) != 200]
    assert not rotas, f"robots.txt señala sitemaps que no responden 200: {rotas}"


def test_ca_let_02_20_noticia_indexable():
    # CA-LET-02-20
    r = pagina(A)
    cabeceras = r.cabeceras.get_all("X-Robots-Tag") or []
    malas = [c for c in cabeceras if impide_indexar(c, admite_robot=True)]
    assert not malas, f"{A}: cabeceras X-Robots-Tag que impiden indexar: {malas}"
    for m in Documento(r.html).metas:
        if m.get("name", "").strip().lower() in ("robots", "googlebot"):
            contenido = m.get("content", "")
            assert not impide_indexar(contenido), f"{A}: <meta name={m.get('name')!r} content={contenido!r}>"
    robots = pedir(SITIO + "/robots.txt")
    assert robots.codigo == 200, f"/robots.txt responde {robots.codigo}"
    reglas = reglas_robots(robots.texto, "googlebot")
    assert robots_permite(reglas, A), f"robots.txt impide a Googlebot leer {A} (reglas que le aplican: {reglas})"


def test_ca_let_02_21_canonica_propia():
    # CA-LET-02-21
    doc = documento(A)
    canonicas = {l.get("href", "").strip() for l in doc.links if "canonical" in l.get("rel", "").lower().split()}
    esperada = dominio() + A
    assert canonicas == {esperada}, f"{A}: canónicas {sorted(canonicas)}; se esperaba una sola, {esperada!r}"


def _repetidas(lista=None):
    lista = lista or documento(LISTA)
    rutas = {ruta_de(h, SITIO + LISTA) for h, t in lista.enlaces if TITULAR_REPETIDO in t}
    return sorted(r for r in rutas if r)


def test_ca_let_02_22_mismo_titular_direcciones_distintas():
    # CA-LET-02-22
    rutas = _repetidas()
    assert len(rutas) == 2, f"«{TITULAR_REPETIDO}» (G y H) enlaza a {rutas}; se esperaban dos direcciones distintas"
    for r in rutas:
        assert TITULAR_REPETIDO in documento(r).h1, f"{r} no abre una noticia titulada «{TITULAR_REPETIDO}»"


def test_ca_let_02_23_direcciones_limpias():
    # CA-LET-02-23
    rutas = _repetidas()
    assert rutas, f"la lista no enlaza ninguna noticia titulada «{TITULAR_REPETIDO}» (G y H)"
    sucias = [r for r in rutas if not re.fullmatch(r"/noticias/[a-z0-9]+(?:-[a-z0-9]+)*/", r)]
    assert not sucias, f"direcciones con algo más que minúsculas sin tilde, cifras y guiones: {sucias}"


# ---------------------------------------------------------------- ejecución


def ejecutar(espacio, argv):
    if not __debug__:  # con -O o PYTHONOPTIMIZE los assert desaparecen y un sitio roto pasaría: mejor no correr
        print("estas comprobaciones no corren con -O ni PYTHONOPTIMIZE: sin assert no comprobarían nada")
        return 3
    tests = {n: f for n, f in sorted(espacio.items()) if n.startswith("test_") and callable(f)}
    nombres = argv or list(tests)
    desconocidos = [n for n in nombres if n not in tests]
    if desconocidos:
        print(f"no existen: {', '.join(desconocidos)}")
        return 2
    fallos = errores = 0
    for n in nombres:
        try:
            tests[n]()
            print(f"PASA  {n}")
        except AssertionError as e:
            fallos += 1
            print(f"FALLA {n}: {e}")
        except Exception as e:  # error propio de la comprobación, no del sitio
            errores += 1
            print(f"ERROR {n}: {type(e).__name__}: {e}")
    print(f"{len(nombres) - fallos - errores} pasan, {fallos} fallan, {errores} con error (SITIO={SITIO}, DOMINIO={DOMINIO or '—'})")
    return 3 if errores else (1 if fallos else 0)


if __name__ == "__main__":
    sys.exit(ejecutar(globals(), sys.argv[1:]))
