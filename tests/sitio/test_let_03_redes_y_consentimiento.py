"""SPEC-LET-03 — redes embebidas y consentimiento de cookies (caja negra, Chromium sin ventana, Playwright).

Los tests hablan con el sitio servido en SITIO_URL, como los de LET-01, y no saben si detrás hay WordPress o Astro.
Ninguno sale de verdad a Instagram ni a TikTok: el navegador corta toda petición a otro dominio y la anota. Cuando un
test necesita que las redes «carguen», responde él con un embebido simulado que respeta el ancho mínimo de los
oficiales; cuando necesita que no carguen, las corta al momento o las deja sin respuesta. Así la aceptación del ítem
no depende de Meta ni de TikTok.

Contrato de interfaz (SPEC-LET-03 §6, «Contrato de interfaz»):
- Aviso: `#aviso-cookies` (la caja que se ve), con los botones «Aceptar», «Rechazar» y «Configurar» y un enlace a la
  página de cookies. Los botones se reconocen por su nombre accesible, el que lee un lector de pantalla: da igual que
  se pinten en mayúsculas. Nada más de lo que tenga el aviso puede valer como aceptar: el test pulsa todo elemento
  visible que no sea uno de los tres botones ni un enlace a otra página (así entra el de cerrar, sea un botón, un
  enlace a ninguna parte, un icono sin nombre ni cursor de mano o cualquier elemento que reaccione al clic). Con el
  teclado, el foco se ve porque al enfocar un botón aparece un contorno o una sombra que no tenía en reposo y que no
  es transparente.
- Panel: `#panel-cookies`, con la casilla «Redes sociales» («Analítica» solo si la decisión D3 la incluye) y «Guardar».
  El panel y la página de cookies nombran a Instagram, Meta y TikTok como palabras enteras: «metadatos» no nombra a Meta.
- Cabecera y menú, pie y contenido como en LET-01: `<header>` o role="banner", `<nav>` o role="navigation",
  `<footer>` o role="contentinfo", y `<main>` o role="main". En el pie, «Configurar cookies» abre el panel.
- Huecos: `[data-embed="instagram"|"tiktok"][data-url="<publicación>"]`. Sin consentimiento llevan «Aceptar y ver» y
  «Ver en Instagram» o «Ver en TikTok», que enlaza a data-url; si la red no carga, «No se ha podido cargar» y ese enlace.
- Registro: localStorage «consentimiento» = {"v": 1, "fecha": texto ISO 8601 con zona, "redes": true|false}; caduca a
  los 12 meses (365 días). La página de cookies lo nombra con su nombre exacto, en un <code> o entre comillas.

Un aviso puede entrar con una animación (deslizarse, aparecer): lo que se mide de su posición o su tamaño (CA-LET-03-05 y
CA-LET-03-08) se mide cuando ha dejado de moverse (`caja_quieta`), no a mitad de la entrada.

Antes de abrir el navegador, cada test pide la portada por HTTP: si no hay sitio, falla diciéndolo.
"""

import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import pytest

PAGINAS_FIJAS = ["/", "/quienes-somos/", "/contacto/", "/aviso-legal/", "/privacidad/", "/cookies/", "/noticias/"]
PAGINA_CON_REDES = "/"  # decisión D2: los embebidos van en la portada
PAGINA_COOKIES = "/cookies/"  # dirección fijada por LET-01
OTRA_PAGINA = "/quienes-somos/"  # dirección fijada por LET-01
RUTA_INEXISTENTE = "/no-existe-ca-let-03/"
CLAVE = "consentimiento"
VERSION = 1
CADUCIDAD_DIAS = 365  # decisión D4: 12 meses
VISITA_TARDIA_DIAS = CADUCIDAD_DIAS - 30  # 11 meses: la elección todavía vale (RN-LET-03-11)
CADUCADO_DIAS = CADUCIDAD_DIAS + 7  # 12 meses y una semana: ya no vale (RN-LET-03-12)
BOTONES_DEL_AVISO = ("Aceptar", "Rechazar", "Configurar")
TERCEROS = ("Instagram", "Meta", "TikTok")  # los que nombran el panel y la página de cookies (RN-LET-03-08 y 10)
MOVIL = {"width": 375, "height": 667}
ESCRITORIO = {"width": 1280, "height": 800}
TAMANOS = (("móvil 375×667", MOVIL, True), ("escritorio 1280×800", ESCRITORIO, False))
TOPE_AVISO = 0.40  # parte del alto de la pantalla que puede ocupar el aviso, en los dos tamaños (CA-LET-03-08)
ESPERA_CARGA_MS = 10_000
ESPERA_FALLO_MS = 12_000  # RN-LET-03-17: 10 s, más un margen
ESPERA_AVISO_MS = 5_000  # lo que se le da a un aviso que tarda en salir; y lo que se espera antes de dar por bueno que no sale
REPOSO_MS = 5_000  # «dejar reposar» una página (SPEC-LET-03 §5): lo que el sitio pida tarde también se anota
REPOSO_PORTADA_MS = 15_000
MARGEN_FECHA_S = 300  # la fecha del registro es la del momento de elegir, con este margen

# Zonas comunes de cada página, como en LET-01: por su etiqueta o por su papel ARIA
MENU = 'header, [role="banner"], nav, [role="navigation"]'
PIE = 'footer, [role="contentinfo"]'
MAIN = 'main, [role="main"]'

ISO_CON_ZONA = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")
# El registro, nombrado como tal en la página de cookies: entre comillas o en un <code>, no como palabra de una frase
REGISTRO_NOMBRADO = re.compile("[«\"'`‘“]" + re.escape(CLAVE) + "[»\"'`’”]")

REDES = {
    "instagram": ("instagram.com", "cdninstagram.com", "facebook.com", "facebook.net", "fbcdn.net", "fbsbx.com"),
    "tiktok": (
        "tiktok.com",
        "tiktokcdn.com",
        "tiktokcdn-us.com",
        "tiktokv.com",
        "ttwstatic.com",
        "byteoversea.com",
        "ibytedtos.com",
        "ibyteimg.com",
        "muscdn.com",
    ),
}
NOMBRE_RED = {"instagram": "Instagram", "tiktok": "TikTok"}

# Embebidos simulados: hacen lo mismo que los guiones oficiales (cambian la cita por un marco) con su ancho mínimo
# (326 px Instagram y 325 px TikTok), sin salir a la red.
_GUION_SIMULADO = {
    "instagram": """
(function () {
  function procesar() {
    document.querySelectorAll('blockquote.instagram-media').forEach(function (cita) {
      var enlace = cita.getAttribute('data-instgrm-permalink') || ((cita.querySelector('a[href]') || {}).href) || 'https://www.instagram.com/p/simulada/';
      var marco = document.createElement('iframe');
      marco.src = enlace.split('?')[0].replace(/\\/?$/, '/') + 'embed/';
      marco.className = 'instagram-media instagram-media-rendered';
      marco.setAttribute('style', 'background:#fff;border:0;display:block;margin:0 0 12px;padding:0;min-width:326px;max-width:540px;width:calc(100% - 2px);height:600px');
      cita.parentNode.replaceChild(marco, cita);
    });
  }
  window.instgrm = { Embeds: { process: procesar } };
  procesar();
})();
""",
    "tiktok": """
(function () {
  document.querySelectorAll('blockquote.tiktok-embed').forEach(function (cita) {
    if (cita.querySelector('iframe')) return;
    var marco = document.createElement('iframe');
    marco.src = 'https://www.tiktok.com/embed/v2/' + (cita.getAttribute('data-video-id') || '0');
    marco.setAttribute('style', 'border:0;display:block;width:100%;min-width:325px;max-width:605px;height:740px');
    cita.style.minWidth = '325px';
    cita.style.maxWidth = '605px';
    cita.innerHTML = '';
    cita.appendChild(marco);
  });
})();
""",
}

# Lo que la página referencia de otro dominio aunque no llegue a pedirlo: preconexiones, precargas, iconos, hojas de
# estilo, guiones, marcos, imágenes, vídeos y sonidos. Los enlaces <a> no cuentan: las tarjetas enlazan a las redes.
_REFERENCIAS = """() => {
  const propio = location.hostname;
  const salida = new Set();
  const ajena = u => {
    try {
      const x = new URL(u, location.href);
      return (x.protocol === 'http:' || x.protocol === 'https:') && x.hostname !== propio ? x.href : null;
    } catch (e) { return null; }
  };
  const anota = (e, atributo, u) => { const h = ajena(u); if (h) salida.add('<' + e.tagName.toLowerCase() + ' ' + atributo + '> ' + h); };
  const RELS = /(^|\\s)(preconnect|dns-prefetch|preload|prefetch|prerender|modulepreload|stylesheet|icon|apple-touch-icon|apple-touch-icon-precomposed|mask-icon|manifest|shortcut)(\\s|$)/i;
  document.querySelectorAll('link[href]').forEach(l => { const rel = l.getAttribute('rel') || ''; if (RELS.test(rel)) anota(l, 'rel=' + rel.trim(), l.getAttribute('href')); });
  document.querySelectorAll('script[src], iframe[src], img[src], source[src], video[src], audio[src], embed[src], track[src], input[type=image][src]')
    .forEach(e => anota(e, 'src', e.getAttribute('src')));
  document.querySelectorAll('object[data]').forEach(e => anota(e, 'data', e.getAttribute('data')));
  document.querySelectorAll('video[poster]').forEach(e => anota(e, 'poster', e.getAttribute('poster')));
  document.querySelectorAll('img[srcset], source[srcset]').forEach(e =>
    (e.getAttribute('srcset') || '').split(',').forEach(c => { const u = c.trim().split(/\\s+/)[0]; if (u) anota(e, 'srcset', u); }));
  document.querySelectorAll('meta[http-equiv="refresh" i][content]').forEach(e => {
    const m = /url\\s*=\\s*['"]?([^'";]+)/i.exec(e.getAttribute('content') || '');
    if (m) anota(e, 'http-equiv=refresh', m[1]);
  });
  return [...salida].sort();
}"""

# Lo que se pulsa en el aviso para comprobar que nada vale como aceptar: todo elemento visible que no sea uno de los
# tres botones («Aceptar», «Rechazar» y «Configurar», por su nombre accesible: aria-label, aria-labelledby o su texto,
# al que no le afecta un text-transform de CSS), ni esté dentro de uno ni lo contenga (pulsarlo sería pulsar el botón);
# ni sea un enlace que lleva a otra página, o esté dentro de uno; ni sea el panel #panel-cookies, o esté dentro de él
# (el panel tiene sus propios criterios). No se mira si parece un mando: así entra el de cerrar, se llame como se llame y
# sea un botón, un enlace a ninguna parte («#», «javascript:»), un icono sin nombre ni cursor de mano o cualquier
# elemento que reaccione al clic. Marca cada candidato con data-ca-let-03-09="<n>" y devuelve su descripción.
_MANDOS = """(aviso, conocidos) => {
  const limpia = t => (t || '').replace(/\\s+/g, ' ').trim();
  const nombre = e => {
    const etiqueta = limpia(e.getAttribute('aria-label'));
    if (etiqueta) return etiqueta;
    const ids = limpia(e.getAttribute('aria-labelledby'));
    if (ids) {
      const t = limpia(ids.split(' ').map(i => (document.getElementById(i) || {}).textContent || '').join(' '));
      if (t) return t;
    }
    if (e.tagName === 'INPUT' && !limpia(e.textContent)) return limpia(e.value);
    return limpia(e.textContent) || limpia(e.getAttribute('title')) || limpia(e.getAttribute('alt'));
  };
  const normaliza = t => limpia(t).toLowerCase().normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '');
  const BOTON = 'button, [role="button"], input[type="button"], input[type="submit"], input[type="reset"], input[type="image"]';
  const tresBotones = [...aviso.querySelectorAll(BOTON)].filter(e => conocidos.includes(normaliza(nombre(e))));
  const visible = e => {
    const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  };
  const navega = e => {
    if (!e.matches('a[href], area[href]')) return false;
    const h = limpia(e.getAttribute('href'));
    return !(h.startsWith('#') || /^javascript:/i.test(h));
  };
  const fuera = e => {
    if (tresBotones.some(b => b === e || b.contains(e) || e.contains(b))) return true;
    const enlace = e.closest('a[href], area[href]');
    if (enlace && navega(enlace)) return true;
    return !!e.closest('#panel-cookies');
  };
  const candidatos = [...aviso.querySelectorAll('*')].filter(e => visible(e) && !fuera(e));
  candidatos.forEach((e, i) => e.setAttribute('data-ca-let-03-09', String(i)));
  return candidatos.map(e => '<' + e.tagName.toLowerCase() + '> ' + (nombre(e) || '(sin nombre)'));
}"""

_FOCO = """() => {
  const e = document.activeElement;
  if (!e || e === document.body || e === document.documentElement) return {aviso: false, main: false, descripcion: '(nada)'};
  return {
    aviso: !!e.closest('#aviso-cookies'),
    main: !!e.closest('main, [role="main"]'),
    descripcion: '<' + e.tagName.toLowerCase() + '> ' + (e.textContent || e.getAttribute('aria-label') || e.value || '').replace(/\\s+/g, ' ').trim().slice(0, 60),
  };
}"""

# Cómo se ve el foco de un botón: su contorno (ancho, estilo, color y separación) y su sombra, y si cada uno se ve de
# verdad. Un contorno sin estilo, de 0 px o de color transparente (el «outline-none» de Tailwind deja «2px solid
# transparent») no se ve; una sombra «none», o con todos sus colores transparentes, tampoco. Un color que no es
# rgb()/rgba() ni «transparent» se da por visible.
_ASPECTO_FOCO = """e => {
  const s = getComputedStyle(e);
  const alfa = c => {
    const m = /^rgba?\\(([^)]*)\\)$/.exec(c || '');
    if (!m) return c === 'transparent' ? 0 : 1;
    const p = m[1].split(/[\\s,\\/]+/).filter(Boolean);
    return p.length > 3 ? parseFloat(p[3]) : 1;
  };
  const colores = s.boxShadow.match(/rgba?\\([^)]*\\)|transparent/g) || [];
  return {
    contorno: [s.outlineWidth, s.outlineStyle, s.outlineColor, s.outlineOffset].join(' '),
    contornoVisible: s.outlineStyle !== 'none' && (s.outlineStyle === 'auto' || parseFloat(s.outlineWidth) > 0) && alfa(s.outlineColor) > 0,
    sombra: s.boxShadow,
    sombraVisible: s.boxShadow !== 'none' && (colores.length === 0 || colores.some(c => alfa(c) > 0)),
  };
}"""


def foco_a_la_vista(reposo, enfocado):
    """Si al enfocar el botón aparece un contorno o una sombra que se ven y que no tenía en reposo: un contorno
    transparente, o una sombra que ya llevaba sin foco, no dicen dónde está el foco (RN-LET-03-19)."""
    return (enfocado["contornoVisible"] and enfocado["contorno"] != reposo["contorno"]) or (
        enfocado["sombraVisible"] and enfocado["sombra"] != reposo["sombra"]
    )


# Lo que se ve de un botón: letra, colores, fondo (color, imagen o degradado), sombra, los cuatro bordes y sus esquinas,
# subrayado, sombra del texto, contorno, relleno, tamaño, y la opacidad y los filtros que le llegan de él y de sus
# contenedores (un «Rechazar» medio transparente o sin el degradado de «Aceptar» no cuesta lo mismo).
_ESTILO = """e => {
  const s = getComputedStyle(e);
  const r = e.getBoundingClientRect();
  let opacidad = 1;
  const filtros = [];
  for (let n = e; n && n.nodeType === 1; n = n.parentElement) {
    const c = getComputedStyle(n);
    opacidad *= parseFloat(c.opacity);
    if (c.filter && c.filter !== 'none') filtros.push(c.filter);
  }
  const lado = l => [s['border' + l + 'Width'], s['border' + l + 'Style'], s['border' + l + 'Color']].join(' ');
  return {etiqueta: e.tagName.toLowerCase(),
          letra: [s.fontSize, s.fontWeight, s.fontStyle, s.fontFamily, s.lineHeight, s.letterSpacing, s.textTransform].join(' | '),
          color: s.color, fondo: s.backgroundColor, imagenDeFondo: s.backgroundImage,
          bordes: ['Top', 'Right', 'Bottom', 'Left'].map(lado).join(' | '),
          esquinas: [s.borderTopLeftRadius, s.borderTopRightRadius, s.borderBottomRightRadius, s.borderBottomLeftRadius].join(' '),
          sombra: s.boxShadow, sombraDelTexto: s.textShadow, subrayado: s.textDecorationLine,
          contorno: [s.outlineWidth, s.outlineStyle, s.outlineColor].join(' '),
          relleno: [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft].join(' '),
          visibilidad: s.visibility, opacidad: Math.round(opacidad * 100) / 100, filtros: filtros.join(' | '),
          ancho: r.width, alto: r.height};
}"""
_IGUALES = (
    "etiqueta", "letra", "color", "fondo", "imagenDeFondo", "bordes", "esquinas", "sombra", "sombraDelTexto",
    "subrayado", "contorno", "relleno", "visibilidad", "opacidad", "filtros",
)

_CENTRO_DE_MAIN = """() => {
  const m = document.querySelector('main, [role="main"]');
  if (!m) return 'la página no tiene <main>';
  m.scrollIntoView({block: 'start'});
  const r = m.getBoundingClientRect();
  const arriba = Math.max(r.top, 0), abajo = Math.min(r.bottom, innerHeight);
  const izquierda = Math.max(r.left, 0), derecha = Math.min(r.right, innerWidth);
  if (abajo <= arriba || derecha <= izquierda) return '<main> no queda a la vista';
  const e = document.elementFromPoint((izquierda + derecha) / 2, (arriba + abajo) / 2);
  return e && m.contains(e) ? 'ok' : 'encima de <main> queda: ' + (e ? e.outerHTML.slice(0, 160) : 'nada');
}"""

# Enlaces visibles de un elemento: (nombre accesible, destino)
_ENLACES = """e => [...e.querySelectorAll('a[href]')]
  .filter(a => a.getClientRects().length > 0 && getComputedStyle(a).visibility !== 'hidden')
  .map(a => [(a.getAttribute('aria-label') || a.textContent || '').replace(/\\s+/g, ' ').trim(), a.href])"""


# --- Sitio por HTTP ---------------------------------------------------------------------------------------------


def sitio_url():
    url = os.environ.get("SITIO_URL", "").strip().rstrip("/")
    if not url:
        pytest.fail("SITIO_URL sin definir: no hay ningún sitio en el que comprobar LET-03", pytrace=False)
    return url


def propio():
    return urllib.parse.urlsplit(sitio_url()).hostname


def pedir(ruta):
    url = ruta if ruta.startswith(("http://", "https://")) else sitio_url() + ruta
    peticion = urllib.request.Request(url, headers={"User-Agent": "pruebas-let-03"})
    try:
        with urllib.request.urlopen(peticion, timeout=20) as r:
            return r.status, r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        motivo = getattr(e, "reason", e)
    # fuera del except: el fallo se lee en una línea, sin la cadena de excepciones
    pytest.fail(f"El sitio no responde en {url} ({motivo}): no hay ninguna web servida en la que comprobar LET-03", pytrace=False)


def exigir_sitio():
    estado, _ = pedir(PAGINA_CON_REDES)
    if estado != 200:
        pytest.fail(f"La portada responde {estado}, no 200", pytrace=False)


def a_ruta(url):
    partes = urllib.parse.urlsplit(url)
    return (partes.path or "/") + (f"?{partes.query}" if partes.query else "")


def rutas_del_sitemap():
    """Las páginas del sitemap de LET-02 (los que señala robots.txt o /sitemap.xml), como rutas del sitio servido."""
    estado, robots = pedir("/robots.txt")
    fuentes = []
    if estado == 200:
        fuentes = [linea.split(":", 1)[1].strip() for linea in robots.splitlines() if linea.lower().startswith("sitemap:")]
    pendientes = [a_ruta(f) for f in fuentes] or ["/sitemap.xml"]
    rutas, vistos = [], set()
    while pendientes and len(vistos) < 20:
        sitemap = pendientes.pop(0)
        if sitemap in vistos:
            continue
        vistos.add(sitemap)
        estado, xml = pedir(sitemap)
        if estado != 200:
            continue
        try:
            raiz = ET.fromstring(xml.encode("utf-8"))
        except ET.ParseError:
            continue
        locs = [e.text.strip() for e in raiz.iter() if e.tag.endswith("loc") and e.text]
        if raiz.tag.endswith("sitemapindex"):
            pendientes += [a_ruta(loc) for loc in locs]
        else:
            rutas += [a_ruta(loc) for loc in locs]
    if not rutas:
        pytest.fail("No hay sitemap con direcciones (LET-02): sin él no se pueden recorrer todas las páginas", pytrace=False)
    return rutas


def todas_las_rutas():
    return list(dict.fromkeys(PAGINAS_FIJAS + rutas_del_sitemap()))


def normaliza(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def terceros_que_faltan(texto):
    """Los terceros que el texto (ya normalizado) no nombra como palabra entera: «metadatos» no nombra a Meta."""
    return [tercero for tercero in TERCEROS if not re.search(r"\b" + re.escape(normaliza(tercero)) + r"\b", texto)]


# --- Redes y registro --------------------------------------------------------------------------------------------


def red_de(url):
    anfitrion = (urllib.parse.urlsplit(url or "").hostname or "").lower()
    for red, dominios in REDES.items():
        if any(anfitrion == d or anfitrion.endswith("." + d) for d in dominios):
            return red
    return None


def misma_publicacion(a, b):
    def clave(url):
        partes = urllib.parse.urlsplit(url or "")
        anfitrion = (partes.hostname or "").lower()
        return (anfitrion[4:] if anfitrion.startswith("www.") else anfitrion), partes.path.rstrip("/")

    return clave(a) == clave(b)


def consiente_redes(crudo):
    try:
        return json.loads(crudo).get("redes") is True
    except (TypeError, ValueError, AttributeError):
        return False


def fallos_del_registro(crudo, redes):
    """Lo que no cumple el contrato en el registro recién guardado: {"v": 1, "fecha": ISO 8601 con zona, "redes": bool}."""
    try:
        datos = json.loads(crudo)
    except (TypeError, ValueError):
        return [f"no es JSON: {crudo!r}"]
    if not isinstance(datos, dict):
        return [f"no es un objeto: {crudo!r}"]
    fallos = []
    if datos.get("v") != VERSION:
        fallos.append(f"«v» no es {VERSION}")
    if datos.get("redes") is not redes:
        fallos.append(f"«redes» no es {json.dumps(redes)}")
    fecha = datos.get("fecha")
    if not isinstance(fecha, str) or not ISO_CON_ZONA.match(fecha):
        fallos.append(f"«fecha» no es un texto ISO 8601 con zona ({fecha!r})")
    elif abs((datetime.now(timezone.utc) - datetime.fromisoformat(fecha)).total_seconds()) > MARGEN_FECHA_S:
        fallos.append(f"«fecha» no es la del momento de elegir ({fecha})")
    return fallos


def iso(instante):
    return instante.isoformat(timespec="seconds")


def _registros_que_no_valen():
    ahora = datetime.now(timezone.utc)
    return {
        "caducado_hace_12_meses_y_una_semana": json.dumps({"v": VERSION, "fecha": iso(ahora - timedelta(days=CADUCADO_DIAS)), "redes": True}),
        "json_roto": '{"v": 1, "fecha": "' + iso(ahora) + '", "redes": tru',
        "version_anterior": json.dumps({"v": VERSION - 1, "fecha": iso(ahora), "redes": True}),
        "fecha_futura": json.dumps({"v": VERSION, "fecha": iso(ahora + timedelta(days=30)), "redes": True}),
        "sin_fecha": json.dumps({"v": VERSION, "redes": True}),
        "fecha_como_numero": json.dumps({"v": VERSION, "fecha": int(ahora.timestamp() * 1000), "redes": True}),
        "texto_suelto": "true",
    }


def _envejecer(estado, dias):
    """El estado que guardó el navegador, con la fecha del registro de hace `dias` días: así se vuelve «otro día» de
    verdad, con lo que el navegador guardó entonces, y no en el mismo instante."""
    estado = json.loads(json.dumps(estado))
    tocados = 0
    for origen in estado.get("origins", []):
        for elemento in origen.get("localStorage", []):
            if elemento.get("name") == CLAVE:
                datos = json.loads(elemento["value"])
                datos["fecha"] = iso(datetime.now(timezone.utc) - timedelta(days=dias))
                elemento["value"] = json.dumps(datos)
                tocados += 1
    if tocados == 0:
        pytest.fail(f"El navegador no guardó «{CLAVE}» en localStorage: no hay registro que pueda valer {dias} días", pytrace=False)
    return estado


# --- Navegador ---------------------------------------------------------------------------------------------------


class _Chromium:
    """Un Chromium sin ventana para todo el módulo; se lanza la primera vez que un test lo pide."""

    def __init__(self):
        self._pw = None
        self._navegador = None

    def lanzar(self):
        if self._navegador is None:
            from playwright.sync_api import sync_playwright

            self._pw = sync_playwright().start()
            self._navegador = self._pw.chromium.launch()
        return self._navegador

    def cerrar(self):
        if self._navegador is not None:
            self._navegador.close()
            self._pw.stop()


@pytest.fixture(scope="module")
def chromium():
    navegador = _Chromium()
    yield navegador
    navegador.cerrar()


class Visita:
    """Una pestaña que anota todo lo que pide a otros dominios y no deja salir nada de verdad.

    redes="cortar": corta toda petición ajena al momento (como un bloqueador). redes="colgar": deja sin respuesta las
    de Instagram y TikTok (como una red que no contesta) y corta lo demás. redes="simular": responde a Instagram y
    TikTok con el embebido simulado y corta lo demás. registro: valor que se deja en localStorage antes de cargar.
    """

    def __init__(self, chromium, tamano=ESCRITORIO, movil=False, javascript=True, redes="cortar", estado=None, registro=None):
        self.anfitrion = propio()
        self.tamano = tamano
        opciones = {"viewport": tamano, "locale": "es-ES", "java_script_enabled": javascript}
        if movil:
            opciones.update(is_mobile=True, has_touch=True, device_scale_factor=2)
        if estado is not None:
            opciones["storage_state"] = estado
        self.modo = redes
        self.ajenas = []
        self.errores = []
        self.colgadas = []
        self.contexto = chromium.lanzar().new_context(**opciones)
        self.contexto.set_default_timeout(ESPERA_CARGA_MS)
        if registro is not None:
            self.contexto.add_init_script(
                "try { if (location.hostname === %s) localStorage.setItem(%s, %s); } catch (e) {}"
                % (json.dumps(self.anfitrion), json.dumps(CLAVE), json.dumps(registro))
            )
        self.contexto.route(self._es_ajena, self._encaminar)
        self.contexto.on("request", lambda peticion: self._anotar(peticion.url))
        self.pagina = self.contexto.new_page()
        self.pagina.on("websocket", lambda ws: self._anotar(ws.url))
        self.pagina.on("pageerror", lambda error: self.errores.append(str(error)))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for ruta in self.colgadas:  # se sueltan antes de cerrar, para que el cierre no deje errores sueltos
            try:
                ruta.abort()
            except Exception:
                pass
        self.contexto.close()

    def _es_ajena(self, url):
        partes = urllib.parse.urlsplit(url)
        return partes.scheme in ("http", "https", "ws", "wss") and partes.hostname != self.anfitrion

    def _anotar(self, url):
        if self._es_ajena(url):
            self.ajenas.append(url)

    def _encaminar(self, ruta):
        red = red_de(ruta.request.url)
        if red is not None and self.modo == "colgar":
            self.colgadas.append(ruta)  # sin responder: la petición queda abierta y el sitio no recibe ni carga ni error
        elif self.modo != "simular" or red is None:
            ruta.abort()
        elif ruta.request.resource_type == "script":
            ruta.fulfill(status=200, content_type="application/javascript", body=_GUION_SIMULADO[red])
        elif ruta.request.resource_type == "document":
            cuerpo = f"<!doctype html><meta charset=utf-8><title>{NOMBRE_RED[red]} simulado</title><p>Publicación simulada</p>"
            ruta.fulfill(status=200, content_type="text/html; charset=utf-8", body=cuerpo)
        else:
            ruta.fulfill(status=204, body="")

    # navegación
    def abrir(self, ruta, espera="networkidle"):
        return self.pagina.goto(sitio_url() + ruta, wait_until=espera)

    def reposar(self, ms=REPOSO_MS):
        """Deja reposar la página (SPEC-LET-03 §5): mueve el ratón, baja con la rueda hasta el final y espera ms con la
        red quieta. Así quedan anotados los temporizadores, lo que se carga al moverse y las imágenes diferidas."""
        from playwright.sync_api import Error as ErrorPlaywright

        self.pagina.mouse.move(self.tamano["width"] / 2, self.tamano["height"] / 3)
        for _ in range(8):
            self.pagina.mouse.wheel(0, 2_000)
            self.pagina.wait_for_timeout(100)
        try:
            self.pagina.wait_for_load_state("networkidle", timeout=ESPERA_CARGA_MS)
        except ErrorPlaywright:
            pass
        self.pagina.wait_for_timeout(ms)

    def referencias_ajenas(self):
        """Lo que la página abierta referencia de otro dominio aunque no lo haya pedido (preconnect, dns-prefetch,
        precargas, iconos, hojas de estilo, guiones, marcos, imágenes, vídeos…); funciona también sin JavaScript."""
        return self.pagina.evaluate(_REFERENCIAS)

    def recorrer(self, rutas):
        """Abre cada ruta y la deja reposar (15 s la portada, 5 s las demás); devuelve {ruta: [lo que pide o referencia
        de otros dominios]}."""
        por_ruta = {}
        for ruta in rutas:
            inicio = len(self.ajenas)
            self.abrir(ruta)
            self.reposar(REPOSO_PORTADA_MS if ruta == PAGINA_CON_REDES else REPOSO_MS)
            nuevas = sorted(set(self.ajenas[inicio:]) | set(self.referencias_ajenas()))
            if nuevas:
                por_ruta[ruta] = nuevas
        return por_ruta

    # piezas del contrato
    def aviso(self):
        return self.pagina.locator("#aviso-cookies")

    def boton_aviso(self, nombre):
        return self.aviso().get_by_role("button", name=nombre, exact=True)

    def pulsar_otros_mandos(self):
        """Pulsa, uno a uno, todos los elementos visibles del aviso que no son «Aceptar», «Rechazar» ni «Configurar» ni
        un enlace a otra página (_MANDOS), sin mirar si parecen un mando: así entra el de cerrar, se llame como se llame
        y sea un botón, un enlace a ninguna parte, un icono sin nombre ni cursor de mano o cualquier elemento que
        reaccione al clic. Si al pulsar algo el aviso se cierra, se abre el panel o cambia la página, se vuelve a abrir
        la portada y se sigue con los demás; si el aviso ya no sale, no queda nada que pulsar. Lo que no se deja pulsar
        (tapado por otro elemento) se anota y se sigue. Devuelve lo pulsado."""
        from playwright.sync_api import Error as ErrorPlaywright

        conocidos = [normaliza(nombre) for nombre in BOTONES_DEL_AVISO]
        portada = a_ruta(sitio_url() + PAGINA_CON_REDES)
        pulsados, hechos = [], set()
        for _ in range(80):  # tope de elementos visibles: ningún aviso tiene más
            if a_ruta(self.pagina.url) != portada or self.panel().is_visible() or not self.aviso_visible():
                self.abrir(PAGINA_CON_REDES)
                if not self.aviso_visible():
                    break
            mandos = self.aviso().evaluate(_MANDOS, conocidos)
            pendiente = next((m for m in enumerate(mandos) if m not in hechos), None)
            if pendiente is None:
                break
            hechos.add(pendiente)
            i, descripcion = pendiente
            try:
                self.aviso().locator(f'[data-ca-let-03-09="{i}"]').click(timeout=3_000)
            except ErrorPlaywright as error:
                pulsados.append(f"{descripcion} (no se pudo pulsar: {str(error).splitlines()[0]})")
                continue
            pulsados.append(descripcion)
            self.pagina.wait_for_timeout(300)
        return pulsados

    def panel(self):
        return self.pagina.locator("#panel-cookies")

    def casilla(self, nombre):
        return self.panel().get_by_label(nombre).first

    def guardar_panel(self):
        self.panel().get_by_role("button", name="Guardar", exact=True).click()

    def enlace_del_pie(self):
        return self.pagina.locator(PIE).get_by_text("Configurar cookies", exact=True).first

    def registro(self):
        return self.pagina.evaluate("k => { try { return localStorage.getItem(k); } catch (e) { return null; } }", CLAVE)

    def huecos(self):
        """{red: [(hueco, data-url)]} de la página abierta."""
        from playwright.sync_api import Error as ErrorPlaywright

        encontrados = {}
        todos = self.pagina.locator("[data-embed]")
        try:
            todos.first.wait_for(state="attached", timeout=ESPERA_CARGA_MS)
        except ErrorPlaywright:
            return encontrados
        for i in range(todos.count()):
            hueco = todos.nth(i)
            red = (hueco.get_attribute("data-embed") or "").strip().lower()
            encontrados.setdefault(red, []).append((hueco, hueco.get_attribute("data-url") or ""))
        return encontrados

    def redes_pedidas(self):
        return {red_de(url) for url in self.ajenas} - {None}

    def esperar_redes(self, ms=ESPERA_CARGA_MS):
        """Espera hasta ms a que se haya pedido a las dos redes y deja medio segundo para lo que venga detrás."""
        limite = time.monotonic() + ms / 1000
        while self.redes_pedidas() != set(REDES) and time.monotonic() < limite:
            self.pagina.wait_for_timeout(100)
        self.pagina.wait_for_timeout(500)
        return self.redes_pedidas()

    def ver_aviso(self, que):
        from playwright.sync_api import expect

        expect(self.aviso(), f"No sale el aviso de cookies ({que})").to_be_visible()

    def aviso_visible(self):
        """Espera a que salga el aviso (hasta ESPERA_AVISO_MS, como ver_aviso) y dice si ha salido, sin fallar."""
        from playwright.sync_api import expect

        try:
            expect(self.aviso()).to_be_visible(timeout=ESPERA_AVISO_MS)
        except AssertionError:
            return False
        return True

    def aviso_no_sale(self, que):
        """Le da a un aviso que tarda el mismo tiempo que en CA-LET-03-15 (ESPERA_AVISO_MS) y comprueba que no ha salido:
        comprobarlo nada más abrir la página pasaría con un aviso que sale tarde."""
        from playwright.sync_api import expect

        self.pagina.wait_for_timeout(ESPERA_AVISO_MS)
        expect(self.aviso(), f"El aviso vuelve a salir ({que})").to_be_hidden(timeout=250)


def caja_quieta(elemento):
    """La caja de un elemento (x, y, width, height) una vez que ha dejado de moverse: un aviso que entra con una animación
    se mide ya entrado, no a mitad de camino. Si no se queda quieto en ESPERA_CARGA_MS, el test falla diciéndolo."""
    from playwright.sync_api import Error as ErrorPlaywright

    try:
        elemento.element_handle().wait_for_element_state("stable")
    except ErrorPlaywright as error:
        pytest.fail(f"El elemento no se queda quieto (animación sin fin): no se puede medir ({str(error).splitlines()[0]})", pytrace=False)
    return elemento.bounding_box()


def exigir_huecos(visita):
    huecos = visita.huecos()
    faltan = [NOMBRE_RED[red] for red in REDES if not huecos.get(red)]
    if faltan:
        pytest.fail(
            f"{PAGINA_CON_REDES} no tiene ningún hueco [data-embed] de {', '.join(faltan)} (decisión D2: uno de cada red en la portada)",
            pytrace=False,
        )
    return {red: huecos[red] for red in REDES}


def esperar_marcos(visita, huecos):
    """Espera a que cada hueco tenga su marco de la red que le toca; devuelve los que no lo tienen."""
    from playwright.sync_api import Error as ErrorPlaywright

    sin_marco = []
    for red, lista in huecos.items():
        for hueco, url in lista:
            marco = hueco.locator("iframe").first
            try:
                marco.wait_for(state="attached", timeout=ESPERA_CARGA_MS)
            except ErrorPlaywright:
                sin_marco.append(f"{red} {url}: sin marco")
                continue
            origen = marco.get_attribute("src") or ""
            if red_de(origen) != red:
                sin_marco.append(f"{red} {url}: el marco viene de {origen!r}")
    return sin_marco


def enlace_a(hueco, nombre_enlace, url):
    """Si el hueco tiene un enlace visible con ese nombre accesible (da igual en mayúsculas) a esa publicación."""
    return any(
        normaliza(texto) == normaliza(nombre_enlace) and misma_publicacion(href, url) for texto, href in hueco.evaluate(_ENLACES)
    )


# --- RN-LET-03-01: nada de otro dominio sin consentimiento -------------------------------------------------------


def test_ca_let_03_01_sin_consentimiento_solo_se_pide_al_propio_dominio(chromium):
    # CA-LET-03-01
    exigir_sitio()
    rutas = todas_las_rutas() + [RUTA_INEXISTENTE]
    with Visita(chromium) as visita:
        ajenas = visita.recorrer(rutas)
    assert not ajenas, f"Sin consentimiento se pide o se referencia a otros dominios (redes, analítica, tipografías, mapas, librerías, preconexiones o iconos): {ajenas}"


def test_ca_let_03_03_sin_javascript_tampoco_se_pide_a_otro_dominio(chromium):
    # CA-LET-03-03
    exigir_sitio()
    rutas = todas_las_rutas() + [RUTA_INEXISTENTE]
    with Visita(chromium, javascript=False) as visita:
        ajenas = visita.recorrer(rutas)
    assert not ajenas, f"Con JavaScript desactivado se pide o se referencia a otros dominios (<noscript>, marcos, guiones, preconexiones o iconos en el HTML): {ajenas}"


# --- RN-LET-03-02: nada guardado salvo la elección -----------------------------------------------------------------


def test_ca_let_03_04_antes_de_elegir_nada_guardado_y_al_rechazar_solo_la_eleccion(chromium):
    # CA-LET-03-04
    exigir_sitio()
    almacenes = "() => ({local: Object.keys(localStorage), sesion: Object.keys(sessionStorage)})"
    with Visita(chromium) as visita:
        visita.abrir(PAGINA_CON_REDES)
        visita.reposar(REPOSO_PORTADA_MS)  # también lo que el sitio guarde tarde, al moverse o al bajar
        antes = {"cookies": [c["name"] for c in visita.contexto.cookies()], **visita.pagina.evaluate(almacenes)}
        assert antes == {"cookies": [], "local": [], "sesion": []}, f"Antes de elegir, tras dejar reposar la portada, ya hay algo guardado: {antes}"
        visita.ver_aviso("primera visita")
        visita.boton_aviso("Rechazar").click()
        visita.reposar()
        despues = {"cookies": [c["name"] for c in visita.contexto.cookies()], **visita.pagina.evaluate(almacenes)}
        registro = visita.registro()
    assert despues == {"cookies": [], "local": [CLAVE], "sesion": []}, f"Tras rechazar y dejar reposar la portada se guarda algo más que la elección: {despues}"
    fallos = fallos_del_registro(registro, False)
    assert not fallos, f"El registro de la elección no sigue el contrato ({registro}): {'; '.join(fallos)}"


# --- RN-LET-03-03: aviso con tres opciones a la vista ---------------------------------------------------------------


def test_ca_let_03_05_primera_visita_muestra_aviso_con_tres_opciones_en_movil(chromium):
    # CA-LET-03-05
    exigir_sitio()
    from playwright.sync_api import expect

    fuera = []
    with Visita(chromium, tamano=MOVIL, movil=True) as visita:
        for ruta in PAGINAS_FIJAS:
            visita.abrir(ruta, "load")
            visita.ver_aviso(f"{ruta}, primera visita en un móvil de 375×667")
            for nombre in BOTONES_DEL_AVISO:
                boton = visita.boton_aviso(nombre)
                try:
                    expect(boton).to_be_visible()
                except AssertionError:
                    fuera.append(f"{ruta}: no hay botón «{nombre}» visible")
                    continue
                caja = caja_quieta(boton)
                if not (caja["x"] >= 0 and caja["y"] >= 0 and caja["x"] + caja["width"] <= MOVIL["width"] and caja["y"] + caja["height"] <= MOVIL["height"]):
                    fuera.append(f"{ruta}: «{nombre}» no cabe en la pantalla sin desplazarse ({caja})")
    assert not fuera, "; ".join(fuera)


# --- RN-LET-03-04: rechazar cuesta lo mismo que aceptar -------------------------------------------------------------


def test_ca_let_03_06_rechazar_cuesta_lo_mismo_que_aceptar(chromium):
    # CA-LET-03-06
    exigir_sitio()
    from playwright.sync_api import expect

    diferencias = {}
    for nombre_tamano, tamano, movil in TAMANOS:
        with Visita(chromium, tamano=tamano, movil=movil) as visita:
            visita.abrir(PAGINA_CON_REDES, "load")
            visita.ver_aviso(nombre_tamano)
            aceptar, rechazar = visita.boton_aviso("Aceptar"), visita.boton_aviso("Rechazar")
            if aceptar.count() != 1 or rechazar.count() != 1:
                pytest.fail(f"{nombre_tamano}: el aviso no tiene un botón «Aceptar» y otro «Rechazar»", pytrace=False)
            # sin foco ni ratón encima: se compara el aspecto en reposo de los dos
            visita.pagina.evaluate("() => { const e = document.activeElement; if (e && e.blur) e.blur(); }")
            a, r = aceptar.evaluate(_ESTILO), rechazar.evaluate(_ESTILO)
            distinto = {k: (a[k], r[k]) for k in _IGUALES if a[k] != r[k]}
            distinto.update({k: (a[k], r[k]) for k in ("ancho", "alto") if abs(a[k] - r[k]) > 2})
            if distinto:
                diferencias[nombre_tamano] = distinto
            if movil:
                rechazar.click()
                expect(visita.aviso(), "Un clic en «Rechazar» no cierra el aviso").to_be_hidden(timeout=2_000)
                centro = visita.pagina.evaluate(_CENTRO_DE_MAIN)
                assert centro == "ok", f"Tras rechazar, el contenido sigue tapado: {centro}"
    assert not diferencias, f"«Aceptar» y «Rechazar» no se ven iguales (Aceptar, Rechazar): {diferencias}"


# --- RN-LET-03-05: el aviso no impide leer ni navegar -------------------------------------------------------------


def test_ca_let_03_07_aviso_abierto_no_impide_desplazarse_ni_navegar(chromium):
    # CA-LET-03-07
    exigir_sitio()
    from playwright.sync_api import Error as ErrorPlaywright

    for nombre_tamano, tamano, movil in TAMANOS:
        with Visita(chromium, tamano=tamano, movil=movil) as visita:
            visita.abrir(PAGINA_CON_REDES, "load")
            visita.ver_aviso(nombre_tamano)
            visita.pagina.mouse.move(tamano["width"] / 2, tamano["height"] / 3)
            visita.pagina.mouse.wheel(0, 600)
            try:
                visita.pagina.wait_for_function("() => window.scrollY > 0", timeout=3_000)
            except ErrorPlaywright:
                pytest.fail(f"{nombre_tamano}: con el aviso abierto, la rueda no desplaza la página", pytrace=False)
    with Visita(chromium) as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        visita.ver_aviso("escritorio, antes de navegar")
        # el menú de LET-01: en la cabecera (<header> o role="banner") o en un <nav> (o role="navigation")
        enlaces = visita.pagina.locator(MENU).get_by_role("link", name="Quiénes somos", exact=True).filter(visible=True)
        if enlaces.count() == 0:
            pytest.fail(
                "No hay ningún enlace visible «Quiénes somos» en la cabecera ni en el menú (contrato de LET-01): "
                "no se puede probar que el aviso deje navegar",
                pytrace=False,
            )
        try:
            enlaces.first.click(timeout=5_000)
            visita.pagina.wait_for_url(re.compile(r"/quienes-somos/?$"), timeout=5_000)
        except ErrorPlaywright as error:
            pytest.fail(f"Con el aviso abierto no se puede ir a «Quiénes somos» desde el menú: {str(error).splitlines()[0]}", pytrace=False)


def test_ca_let_03_08_aviso_ocupa_como_mucho_el_40_por_ciento_en_movil_y_escritorio(chromium):
    # CA-LET-03-08
    exigir_sitio()
    demasiado = []
    for nombre_tamano, tamano, movil in TAMANOS:
        with Visita(chromium, tamano=tamano, movil=movil) as visita:
            visita.abrir(PAGINA_CON_REDES, "load")
            visita.ver_aviso(nombre_tamano)
            caja = caja_quieta(visita.aviso())
        alto = min(caja["y"] + caja["height"], tamano["height"]) - max(caja["y"], 0)
        if alto > TOPE_AVISO * tamano["height"]:
            demasiado.append(f"{nombre_tamano}: el aviso ocupa {alto:.0f} px de {tamano['height']} ({alto / tamano['height']:.0%})")
    assert not demasiado, f"El tope es el {TOPE_AVISO:.0%} del alto de la pantalla; " + "; ".join(demasiado)


# --- RN-LET-03-06: navegar o cerrar no es aceptar -----------------------------------------------------------------


def test_ca_let_03_09_navegar_o_cerrar_el_aviso_no_es_aceptar(chromium):
    # CA-LET-03-09
    exigir_sitio()
    from playwright.sync_api import Error as ErrorPlaywright

    with Visita(chromium) as visita:
        visita.abrir(PAGINA_CON_REDES)
        visita.ver_aviso("primera visita")
        visita.pagina.mouse.move(ESCRITORIO["width"] / 2, ESCRITORIO["height"] / 3)
        visita.pagina.mouse.wheel(0, 800)
        try:  # que el desplazamiento ocurra de verdad antes de seguir (si no se puede desplazar, lo mide CA-LET-03-07)
            visita.pagina.wait_for_function("() => window.scrollY > 0", timeout=3_000)
        except ErrorPlaywright:
            pass
        visita.pagina.wait_for_timeout(500)
        visita.pagina.keyboard.press("Escape")
        # cualquier otro mando del aviso (el de cerrar, se llame como se llame y sea botón, enlace, icono o lo que sea)
        # se pulsa: tampoco puede valer como aceptar
        pulsados = visita.pulsar_otros_mandos()
        visita.abrir(OTRA_PAGINA)
        visita.abrir(PAGINA_CON_REDES)
        visita.reposar()
        registro = visita.registro()
        ajenas = sorted(set(visita.ajenas))
    que = "desplazarse, pulsar Escape, " + (f"pulsar {pulsados}, " if pulsados else "") + "navegar y volver"
    assert not consiente_redes(registro), f"Sin elegir ({que}) ha quedado guardado un consentimiento: {registro}"
    assert not ajenas, f"Sin elegir ({que}) se ha pedido a otros dominios: {ajenas}"


# --- RN-LET-03-07 y 08: panel por finalidades -----------------------------------------------------------------------


def test_ca_let_03_10_configurar_muestra_finalidades_apagadas_y_guardar_es_rechazar(chromium):
    # CA-LET-03-10
    exigir_sitio()
    from playwright.sync_api import expect

    with Visita(chromium) as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        visita.ver_aviso("primera visita")
        visita.boton_aviso("Configurar").click()
        expect(visita.panel(), "«Configurar» no abre el panel #panel-cookies").to_be_visible()
        expect(visita.casilla("Redes sociales"), "El panel no tiene la casilla «Redes sociales»").to_be_visible()
        marcadas = []
        casillas = visita.panel().locator("input[type=checkbox], [role=switch], [role=checkbox]")
        for i in range(casillas.count()):
            casilla = casillas.nth(i)
            if casilla.is_checked() and casilla.is_enabled():
                marcadas.append(casilla.evaluate("e => e.closest('label') ? e.closest('label').innerText.trim() : (e.getAttribute('aria-label') || e.id)"))
        assert not marcadas, f"Hay finalidades encendidas de partida: {marcadas}"
        visita.guardar_panel()
        expect(visita.panel(), "«Guardar» no cierra el panel").to_be_hidden()
        expect(visita.aviso(), "«Guardar» no cierra el aviso").to_be_hidden()
        registro = visita.registro()
        visita.ajenas.clear()
        visita.abrir(PAGINA_CON_REDES)
        visita.reposar()
        ajenas = sorted(set(visita.ajenas))
    fallos = fallos_del_registro(registro, False)
    assert not fallos, f"«Guardar» sin tocar nada no guarda un rechazo ({registro}): {'; '.join(fallos)}"
    assert not ajenas, f"Tras guardar sin tocar nada se pide a otros dominios: {ajenas}"


def test_ca_let_03_11_panel_nombra_los_terceros_de_redes(chromium):
    # CA-LET-03-11
    exigir_sitio()
    from playwright.sync_api import expect

    with Visita(chromium) as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        visita.ver_aviso("primera visita")
        visita.boton_aviso("Configurar").click()
        expect(visita.panel(), "«Configurar» no abre el panel #panel-cookies").to_be_visible()
        texto = normaliza(visita.panel().inner_text())
    faltan = terceros_que_faltan(texto)  # como palabra entera: «metadatos» no nombra a Meta
    assert not faltan, f"El panel no nombra a {', '.join(faltan)}"


# --- RN-LET-03-09 y 10: enlace y página de cookies ----------------------------------------------------------------


def test_ca_let_03_12_aviso_enlaza_a_la_pagina_de_cookies(chromium):
    # CA-LET-03-12
    exigir_sitio()
    with Visita(chromium) as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        visita.ver_aviso("primera visita")
        enlaces = visita.aviso().evaluate(_ENLACES)
    destino = [href for _, href in enlaces if urllib.parse.urlsplit(href).hostname == propio() and urllib.parse.urlsplit(href).path.rstrip("/") == PAGINA_COOKIES.rstrip("/")]
    assert destino, f"El aviso no enlaza a {PAGINA_COOKIES}; sus enlaces: {enlaces}"
    estado, _ = pedir(PAGINA_COOKIES)
    assert estado == 200, f"{PAGINA_COOKIES} responde {estado}, no 200"


def test_ca_let_03_13_pagina_de_cookies_nombra_terceros_registro_y_plazo(chromium):
    # CA-LET-03-13
    exigir_sitio()
    estado, _ = pedir(PAGINA_COOKIES)
    assert estado == 200, f"{PAGINA_COOKIES} responde {estado}, no 200"
    with Visita(chromium) as visita:
        visita.abrir(PAGINA_COOKIES, "load")
        contenido = visita.pagina.locator(MAIN)
        if contenido.count() == 0:
            pytest.fail(f"{PAGINA_COOKIES} no tiene <main> (ni role=\"main\") con su contenido", pytrace=False)
        texto = normaliza(" ".join(contenido.evaluate_all("es => es.map(e => e.textContent)")))
        # el registro, nombrado como tal: en un <code> (o <kbd>, <samp>) o entre comillas; «tu consentimiento» no lo nombra
        en_codigo = contenido.evaluate_all(
            "(es, clave) => es.some(e => [...e.querySelectorAll('code, kbd, samp')].some(c => c.textContent.trim() === clave))", CLAVE
        )
    faltan = terceros_que_faltan(texto)  # como palabra entera: «metadatos» no nombra a Meta
    if not (en_codigo or REGISTRO_NOMBRADO.search(texto)):
        faltan.append(f"el registro «{CLAVE}» por su nombre (en un <code> o entre comillas)")
    if not re.search(r"\b(12|doce) meses\b", texto):
        faltan.append("«12 meses»")
    assert not faltan, f"El contenido (<main>) de la página de cookies no nombra: {', '.join(faltan)}"


# --- RN-LET-03-11 y 12: la elección se recuerda y caduca ------------------------------------------------------------


@pytest.mark.parametrize("eleccion", ["Aceptar", "Rechazar"])
def test_ca_let_03_14_la_eleccion_se_recuerda_entre_paginas_y_visitas(chromium, eleccion):
    # CA-LET-03-14
    exigir_sitio()
    from playwright.sync_api import expect

    acepta = eleccion == "Aceptar"
    with Visita(chromium, redes="simular") as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        visita.ver_aviso("primera visita")
        visita.boton_aviso(eleccion).click()
        expect(visita.aviso(), f"«{eleccion}» no cierra el aviso").to_be_hidden()
        fallos = fallos_del_registro(visita.registro(), acepta)
        assert not fallos, f"Tras «{eleccion}», el registro no sigue el contrato: {'; '.join(fallos)}"
        visita.abrir(OTRA_PAGINA, "load")
        visita.aviso_no_sale(f"tras «{eleccion}», en {OTRA_PAGINA}")  # con tiempo: un aviso que sale tarde también cuenta
        estado = visita.contexto.storage_state()
    # otra visita, 11 meses después: lo que guardó el navegador, con la fecha de entonces (la elección dura 12 meses)
    with Visita(chromium, redes="simular", estado=_envejecer(estado, VISITA_TARDIA_DIAS)) as otra:
        otra.abrir(PAGINA_CON_REDES)
        otra.aviso_no_sale(f"tras «{eleccion}», en otra visita 11 meses después")
        if acepta:
            pedidas = otra.esperar_redes()
        else:
            otra.reposar()
            ajenas = sorted(set(otra.ajenas))
    if acepta:
        assert pedidas == {"instagram", "tiktok"}, f"En otra visita 11 meses después de aceptar no se cargan las dos redes: {pedidas or 'ninguna'}"
    else:
        assert not ajenas, f"En otra visita 11 meses después de rechazar se pide a otros dominios: {ajenas}"


@pytest.mark.parametrize("caso", list(_registros_que_no_valen()))
def test_ca_let_03_15_eleccion_caducada_o_ilegible_vuelve_a_preguntar(chromium, caso):
    # CA-LET-03-15
    exigir_sitio()
    registro = _registros_que_no_valen()[caso]
    with Visita(chromium, redes="simular", registro=registro) as visita:
        visita.abrir(PAGINA_CON_REDES)
        visible = visita.aviso_visible()  # espera: un aviso que tarda en salir también vale
        visita.reposar()
        ajenas = sorted(set(visita.ajenas))
        errores = list(visita.errores)
    assert visible, f"Con un registro {caso} ({registro}) no vuelve a salir el aviso"
    assert not ajenas, f"Con un registro {caso} se pide a otros dominios: {ajenas}"
    assert not errores, f"Con un registro {caso} la página da errores: {errores}"


# --- RN-LET-03-13 y 14: cambiar y retirar la elección -------------------------------------------------------------


def test_ca_let_03_16_enlace_del_pie_reabre_el_panel_en_todas_las_paginas(chromium):
    # CA-LET-03-16
    exigir_sitio()
    from playwright.sync_api import expect

    rutas = todas_las_rutas()
    with Visita(chromium, redes="simular") as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        visita.ver_aviso("primera visita")
        visita.boton_aviso("Aceptar").click()
        for ruta in rutas:
            visita.abrir(ruta, "load")
            enlace = visita.enlace_del_pie()
            expect(enlace, f"{ruta}: no hay «Configurar cookies» en el pie (<footer> o role=\"contentinfo\")").to_be_visible()
            enlace.click()
            expect(visita.panel(), f"{ruta}: «Configurar cookies» no abre el panel").to_be_visible()
            expect(visita.casilla("Redes sociales"), f"{ruta}: el panel no muestra marcada la elección actual (redes aceptadas)").to_be_checked()


def test_ca_let_03_17_retirar_redes_corta_los_terceros_en_la_pagina_siguiente(chromium):
    # CA-LET-03-17
    exigir_sitio()
    from playwright.sync_api import expect

    with Visita(chromium, redes="simular") as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        huecos = exigir_huecos(visita)
        visita.ver_aviso("primera visita")
        visita.boton_aviso("Aceptar").click()
        assert visita.esperar_redes() == set(REDES), "Tras aceptar no se cargan las dos redes: no hay nada que retirar"
        enlace = visita.enlace_del_pie()
        expect(enlace, "No hay «Configurar cookies» en el pie").to_be_visible()
        enlace.click()
        expect(visita.panel(), "«Configurar cookies» no abre el panel").to_be_visible()
        casilla = visita.casilla("Redes sociales")
        if casilla.is_checked():
            casilla.click()
        visita.guardar_panel()
        visita.ajenas.clear()
        visita.abrir(PAGINA_CON_REDES)
        visita.reposar()
        pedidas = sorted({u for u in visita.ajenas if red_de(u)})
        huecos = exigir_huecos(visita)
        sin_tarjeta = [f"{red} {url}" for red, lista in huecos.items() for hueco, url in lista if not hueco.get_by_role("button", name="Aceptar y ver", exact=True).is_visible()]
    assert not pedidas, f"Tras retirar el consentimiento, la página siguiente pide a las redes: {pedidas}"
    assert not sin_tarjeta, f"Tras retirar el consentimiento no vuelven las tarjetas en: {sin_tarjeta}"


# --- RN-LET-03-15 a 18: los embebidos ------------------------------------------------------------------------------


def test_ca_let_03_18_sin_consentimiento_cada_embebido_es_una_tarjeta_con_enlace(chromium):
    # CA-LET-03-18
    exigir_sitio()
    problemas = []
    with Visita(chromium) as visita:
        visita.abrir(PAGINA_CON_REDES)
        huecos = exigir_huecos(visita)
        for red, lista in huecos.items():
            nombre = NOMBRE_RED[red]
            for hueco, url in lista:
                donde = f"{nombre} {url or '(sin data-url)'}"
                if red_de(url) != red:
                    problemas.append(f"{donde}: data-url no es una publicación de {nombre}")
                texto = normaliza(hueco.inner_text())
                if normaliza(nombre) not in texto or "cookies" not in texto:
                    problemas.append(f"{donde}: la tarjeta no dice que es de {nombre} ni que puede instalar cookies")
                if not hueco.get_by_role("button", name="Aceptar y ver", exact=True).is_visible():
                    problemas.append(f"{donde}: no hay botón «Aceptar y ver»")
                if not enlace_a(hueco, f"Ver en {nombre}", url):
                    problemas.append(f"{donde}: no hay enlace «Ver en {nombre}» a la publicación ({hueco.evaluate(_ENLACES)})")
                if hueco.locator("iframe").count():
                    problemas.append(f"{donde}: hay un marco antes de consentir")
    assert not problemas, "; ".join(problemas)


def _aceptar_redes(visita, via, huecos):
    from playwright.sync_api import expect

    if via == "aviso":
        visita.ver_aviso("primera visita")
        visita.boton_aviso("Aceptar").click()
    elif via == "panel":
        visita.ver_aviso("primera visita")
        visita.boton_aviso("Configurar").click()
        expect(visita.panel(), "«Configurar» no abre el panel").to_be_visible()
        casilla = visita.casilla("Redes sociales")
        if not casilla.is_checked():
            casilla.click()
        visita.guardar_panel()
    else:
        hueco, _ = huecos["instagram"][0]
        boton = hueco.get_by_role("button", name="Aceptar y ver", exact=True)
        expect(boton, "La tarjeta de Instagram no tiene «Aceptar y ver»").to_be_visible()
        boton.click()


@pytest.mark.parametrize("via", ["aviso", "panel", "tarjeta"])
def test_ca_let_03_19_aceptar_redes_carga_los_embebidos_sin_recargar(chromium, via):
    # CA-LET-03-19
    exigir_sitio()
    with Visita(chromium, redes="simular") as visita:
        visita.abrir(PAGINA_CON_REDES)
        huecos = exigir_huecos(visita)
        visita.pagina.evaluate("() => { window.__ca_let_03_19 = 'misma pagina'; }")
        _aceptar_redes(visita, via, huecos)
        sin_marco = esperar_marcos(visita, huecos)
        pedidas = visita.esperar_redes()
        visita.reposar()
        misma = visita.pagina.evaluate("() => window.__ca_let_03_19 === 'misma pagina'")
        otras = sorted({u for u in visita.ajenas if red_de(u) is None})
        registro = visita.registro()
    assert misma, f"Aceptar desde {via} recarga la página"
    assert not sin_marco, f"Aceptar desde {via} no inserta los embebidos en su hueco: {sin_marco}"
    assert pedidas == {"instagram", "tiktok"}, f"Aceptar desde {via} no pide a las dos redes: {pedidas or 'ninguna'}"
    fallos = fallos_del_registro(registro, True)
    assert not fallos, f"Aceptar desde {via} no guarda la elección como pide el contrato ({registro}): {'; '.join(fallos)}"
    if via != "aviso":  # «Aceptar» del aviso acepta todas las finalidades; el panel y la tarjeta, solo redes
        assert not otras, f"Aceptar solo redes desde {via} pide también a otros dominios: {otras}"


@pytest.mark.parametrize("modo", ["cortadas", "sin_respuesta"])
def test_ca_let_03_20_si_el_embebido_no_carga_queda_el_enlace_a_la_red(chromium, modo):
    # CA-LET-03-20
    exigir_sitio()
    from playwright.sync_api import Error as ErrorPlaywright

    problemas = []
    with Visita(chromium, redes="cortar" if modo == "cortadas" else "colgar") as visita:
        # «domcontentloaded»: con las redes sin respuesta, una portada que las pida al abrir no llegaría nunca a «load»
        visita.abrir(PAGINA_CON_REDES, "domcontentloaded")
        huecos = exigir_huecos(visita)
        visita.ver_aviso("primera visita")
        visita.boton_aviso("Aceptar").click()
        for red, lista in huecos.items():
            for hueco, url in lista:
                donde = f"{NOMBRE_RED[red]} {url}"
                try:
                    hueco.get_by_text("No se ha podido cargar").first.wait_for(state="visible", timeout=ESPERA_FALLO_MS)
                except ErrorPlaywright:
                    problemas.append(f"{donde}: con las peticiones {modo.replace('_', ' ')}, a los {ESPERA_FALLO_MS // 1000} s no dice «No se ha podido cargar»")
                    continue
                if not any(misma_publicacion(href, url) for _, href in hueco.evaluate(_ENLACES)):
                    problemas.append(f"{donde}: no queda a la vista el enlace a la publicación")
    assert not problemas, "; ".join(problemas)


def test_ca_let_03_21_en_movil_los_embebidos_no_desbordan(chromium):
    # CA-LET-03-21
    exigir_sitio()
    with Visita(chromium, tamano=MOVIL, movil=True, redes="simular") as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        huecos = exigir_huecos(visita)
        visita.ver_aviso("primera visita en móvil")
        visita.boton_aviso("Aceptar").click()
        sin_marco = esperar_marcos(visita, huecos)
        visita.esperar_redes()
        ancho = visita.pagina.evaluate("document.documentElement.scrollWidth")
    assert not sin_marco, f"Tras aceptar no se cargan los embebidos: {sin_marco}"
    assert ancho <= MOVIL["width"], f"Con los embebidos cargados la página mide {ancho} px de ancho en un móvil de {MOVIL['width']} px"


# --- RN-LET-03-19: solo con teclado --------------------------------------------------------------------------------


def test_ca_let_03_22_el_aviso_se_usa_solo_con_teclado(chromium):
    # CA-LET-03-22
    exigir_sitio()
    from playwright.sync_api import expect

    faltan = set(BOTONES_DEL_AVISO)
    sin_anillo, antes = [], None
    with Visita(chromium) as visita:
        visita.abrir(PAGINA_CON_REDES, "load")
        visita.ver_aviso("primera visita")
        botones = {nombre: visita.boton_aviso(nombre) for nombre in BOTONES_DEL_AVISO}
        sin_boton = [nombre for nombre, boton in botones.items() if boton.count() != 1]
        if sin_boton:
            pytest.fail(f"El aviso no tiene un botón «{'», «'.join(sin_boton)}» (por su nombre accesible)", pytrace=False)
        # cómo se ve cada botón en reposo, sin foco ni ratón encima: el foco se verá por lo que cambie respecto a esto.
        # Si la página ya había enfocado algo, se le quita el foco para medir y se le devuelve después
        activo = visita.pagina.evaluate_handle("() => document.activeElement")
        visita.pagina.evaluate("() => { const e = document.activeElement; if (e && e.blur) e.blur(); }")
        reposo = {nombre: boton.evaluate(_ASPECTO_FOCO) for nombre, boton in botones.items()}
        activo.evaluate("e => { if (e && e !== document.body && e !== document.documentElement && e.focus) e.focus(); }")
        for pulsacion in range(60):
            if pulsacion:  # lo que la página enfoca de partida también cuenta como alcanzado
                visita.pagina.keyboard.press("Tab")
            visita.pagina.wait_for_timeout(250)  # que acabe cualquier transición del estilo de foco antes de medirlo
            foco = visita.pagina.evaluate(_FOCO)
            # el botón con el foco se reconoce por su nombre accesible, no por cómo se pinte (mayúsculas incluidas)
            con_foco = next((nombre for nombre, boton in botones.items() if boton.evaluate("e => e === document.activeElement")), None)
            if con_foco in faltan:
                faltan.discard(con_foco)
                enfocado = botones[con_foco].evaluate(_ASPECTO_FOCO)
                if not foco_a_la_vista(reposo[con_foco], enfocado):
                    sin_anillo.append(
                        f"«{con_foco}» (en reposo: contorno {reposo[con_foco]['contorno']}, sombra {reposo[con_foco]['sombra']}; "
                        f"con foco: contorno {enfocado['contorno']}, sombra {enfocado['sombra']})"
                    )
            elif foco["main"] and faltan:
                antes = foco["descripcion"]
                break
            if not faltan:
                break
        assert antes is None, f"Con Tab se llega al contenido («{antes}») antes que a {sorted(faltan)} del aviso"
        assert not faltan, f"Con Tab no se llega a {sorted(faltan)} del aviso"
        assert not sin_anillo, (
            "Con el foco en " + "; ".join(sin_anillo) + " no se ve dónde está: al enfocar no aparece ningún contorno ni "
            "sombra de color no transparente que no tuviera ya en reposo"
        )
        visita.boton_aviso("Rechazar").focus()
        visita.pagina.keyboard.press("Enter")
        expect(visita.aviso(), "Enter sobre «Rechazar» no cierra el aviso").to_be_hidden(timeout=2_000)
