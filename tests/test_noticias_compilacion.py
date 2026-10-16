"""Comprobaciones de la compilación y del gestor de noticias (SPEC-LET-02, RN-LET-02-02, 07, 08 y 19).

Complementan a tests/test_noticias.py, que mira el sitio ya servido con el juego de pruebas: aquí se compila una copia de
sitio/ con noticias reales («contenido/noticias» de la copia, como el sitio publicado) y se mira qué sale en dist/ y cuándo
la compilación se niega. No necesitan servidor ni Docker; sí Node y las dependencias de sitio/ (npm ci).

    DOMINIO=https://www.example.com python3 tests/test_noticias_compilacion.py [test ...]

Sin argumentos corre todas; con nombres, solo esas. Sale 0 si todas pasan, 1 si alguna falla, 2 si se pide un test que no
existe y 3 si una comprobación revienta por un error propio o si Python corre con -O o PYTHONOPTIMIZE. Solo usa la biblioteca
estándar de Python 3.9 o posterior. Cada test cita la regla de la spec que vigila.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FUENTE = RAIZ / "sitio"
DOMINIO = os.environ.get("DOMINIO", "https://www.example.com").rstrip("/")
GESTOR = (FUENTE / "herramientas" / "gestor-noticias.mjs").as_uri()
FOTO = FUENTE / "herramientas" / "foto-prueba.jpg"


# ---------------------------------------------------------------- una copia de sitio/ con su propio contenido


@contextmanager
def copia():
    """Una copia de sitio/ en una carpeta temporal, sin noticias, con las dependencias de la original."""
    with tempfile.TemporaryDirectory(prefix="letizia-noticias-") as tmp:
        sitio = Path(tmp) / "sitio"
        shutil.copytree(FUENTE, sitio, ignore=shutil.ignore_patterns("node_modules", "dist", ".astro", ".juego"))
        (Path(tmp) / "tests" / "sitio").mkdir(parents=True)  # src/datos/titular.js lee los datos de la titular de aquí
        shutil.copy(RAIZ / "tests" / "sitio" / "titular.json", Path(tmp) / "tests" / "sitio" / "titular.json")
        (sitio / "node_modules").symlink_to(FUENTE / "node_modules")
        (sitio / "contenido" / "noticias").mkdir(parents=True, exist_ok=True)
        yield sitio


def noticias_de(sitio):
    return sitio / "contenido" / "noticias"


def compilar(sitio, extra=None):
    """La compilación de producción: sin NOTICIAS_DIR, con DOMINIO (y lo que traiga extra). Devuelve el proceso terminado."""
    entorno = {**os.environ, "DOMINIO": DOMINIO}
    entorno.pop("NOTICIAS_DIR", None)
    entorno.update(extra or {})
    return subprocess.run(
        [str(sitio / "node_modules" / ".bin" / "astro"), "build"],
        cwd=sitio, env=entorno, capture_output=True, text=True, timeout=300,
    )


def gestor(codigo, carpeta):
    """Corre código del gestor de noticias (g) sobre una carpeta; devuelve el proceso terminado."""
    guion = (
        f"import * as g from {json.dumps(GESTOR)}; import {{ readFileSync }} from 'node:fs';"
        f"const carpeta = {json.dumps(str(carpeta))}; const foto = readFileSync({json.dumps(str(FOTO))});"
        f"{codigo}"
    )
    return subprocess.run(["node", "--input-type=module", "-e", guion], capture_output=True, text=True, timeout=60)


def gestor_ok(codigo, carpeta):
    r = gestor(codigo, carpeta)
    assert r.returncode == 0, f"el gestor falló (exit {r.returncode}): {r.stderr.strip()[-600:]}"
    return r


def texto(r):
    return r.stdout + r.stderr


def salida(r):
    return texto(r).strip()[-900:]


def archivos(raiz):
    return sorted(p.relative_to(raiz).as_posix() for p in raiz.rglob("*") if p.is_file())


# ---------------------------------------------------------------- RN-LET-02-02 y 19: qué entra en el sitio publicado


def test_rn_let_02_02_titular_real_que_empieza_por_prueba():
    # CA-LET-02-25
    # RN-LET-02-02: un titular real como «Prueba de la EvAU en Talavera» da la dirección prueba-de-la-evau-en-talavera, y esa
    # noticia tiene su página y sale en el sitemap; no la confunde con el juego de pruebas (RN-LET-02-19).
    with copia() as sitio:
        gestor_ok(
            "const d = g.crear(carpeta, { titular: 'Prueba de la EvAU en Talavera', entradilla: 'Fechas y sedes.', texto: 'Texto.' });"
            "g.publicar(carpeta, d, { fecha: new Date('2026-10-12T10:00:00+02:00') }); console.log(d);",
            noticias_de(sitio),
        )
        r = compilar(sitio)
        assert r.returncode == 0, f"la compilación de producción salió con {r.returncode}: {salida(r)}"
        direccion = "prueba-de-la-evau-en-talavera"
        assert (sitio / "dist" / "noticias" / direccion / "index.html").is_file(), f"no hay página para /noticias/{direccion}/"
        assert f"{DOMINIO}/noticias/{direccion}/" in (sitio / "dist" / "sitemap.xml").read_text(encoding="utf-8")


def test_rn_let_02_19_el_juego_de_pruebas_no_entra_en_el_sitio_publicado():
    # CA-LET-02-26
    # RN-LET-02-19: la compilación de producción se niega a publicar una noticia del juego (la marca el cargador), aunque
    # tenga otra dirección, y las seis direcciones fijas del juego (prueba-a a prueba-f), aunque no lleven la marca.
    casos = {
        "marcada como del juego": "g.crear(carpeta, { titular: 'Noticia de prueba repetida: Año Nuevo en Talavera', entradilla: 'e', texto: 't', prueba: true })",
        "con la dirección prueba-a": "g.crear(carpeta, { titular: 'Otra', entradilla: 'e', texto: 't', direccion: 'prueba-a' })",
    }
    for caso, crear in casos.items():
        with copia() as sitio:
            gestor_ok(f"const d = {crear}; g.publicar(carpeta, d);", noticias_de(sitio))
            r = compilar(sitio)
            assert r.returncode != 0, f"noticia {caso}: la compilación de producción salió con 0 y publicó el juego"
            assert "juego de pruebas" in texto(r), f"noticia {caso}: la compilación falló, pero no por ser del juego de pruebas: {salida(r)}"
            assert not (sitio / "dist" / "noticias").exists(), f"noticia {caso}: la compilación fallida dejó páginas de noticias"


# ---------------------------------------------------------------- RN-LET-02-07 y 08: lo que no está publicado no se sirve


JS_FOTOS = """
const nueva = (titular, fichero, cuerpo) => g.crear(carpeta, {
  titular, entradilla: 'Entradilla.', texto: `Texto.\\n\\n![](./${cuerpo})`, fotoAutor: 'Autora',
  foto: { fichero, bytes: Buffer.concat([foto, Buffer.from(fichero)]) }, // cada foto con bytes propios: Vite junta las idénticas bajo un solo nombre
});
const p = nueva('Noticia publicada con foto', 'foto-publicada.jpg', 'foto-publicada-cuerpo.jpg');
const r = nueva('Noticia que se retirará', 'foto-retirada.jpg', 'foto-retirada-cuerpo.jpg');
nueva('Noticia en borrador', 'foto-borrador.jpg', 'foto-borrador-cuerpo.jpg');
g.publicar(carpeta, p, { fecha: new Date('2026-10-12T10:00:00+02:00') });
g.publicar(carpeta, r, { fecha: new Date('2026-10-11T10:00:00+02:00') });
console.log(r);
"""


def test_rn_let_02_07_08_las_fotos_de_borradores_y_retiradas_no_salen():
    # CA-LET-02-27
    # RN-LET-02-07 y 08: una noticia que no está publicada deja de verse, y su foto (la de la ficha y las del texto) no se
    # sirve en ninguna dirección: ni la de un borrador, ni la de una retirada que Google ya había leído publicada.
    with copia() as sitio:
        carpeta = noticias_de(sitio)
        for nombre in ("foto-publicada-cuerpo.jpg", "foto-retirada-cuerpo.jpg", "foto-borrador-cuerpo.jpg"):
            (carpeta / nombre).write_bytes(FOTO.read_bytes() + nombre.encode())  # bytes propios, como en JS_FOTOS
        retirada = gestor_ok(JS_FOTOS, carpeta).stdout.strip()

        r = compilar(sitio)
        assert r.returncode == 0, f"la compilación salió con {r.returncode}: {salida(r)}"
        antes = archivos(sitio / "dist")
        assert any("foto-publicada." in a for a in antes), f"la foto de la noticia publicada no está en dist/: {antes}"
        assert any("foto-retirada." in a for a in antes), "la foto de la noticia, aún publicada, no está en dist/ (la comprobación no vale)"
        ajenas = [a for a in antes if "foto-borrador" in a]
        assert not ajenas, f"la compilación publica fotos de un borrador: {ajenas}"

        gestor_ok(f"g.retirar(carpeta, {json.dumps(retirada)});", carpeta)
        r = compilar(sitio)
        assert r.returncode == 0, f"la compilación salió con {r.returncode}: {salida(r)}"
        despues = archivos(sitio / "dist")
        assert any("foto-publicada." in a for a in despues), f"la foto de la noticia publicada ya no está en dist/: {despues}"
        sobran = [a for a in despues if "foto-retirada" in a or "foto-borrador" in a]
        assert not sobran, f"la compilación sigue sirviendo fotos de noticias que no están publicadas: {sobran}"
        assert not (sitio / "dist" / "noticias" / retirada).exists(), f"la noticia retirada {retirada} sigue teniendo página"


# ---------------------------------------------------------------- una noticia se puede corregir antes de publicarla


def test_rn_let_02_11_borrador_corregido_se_publica_sin_romper_la_compilacion():
    # CA-LET-02-28
    # RN-LET-02-11: la fecha de modificación es la de la última corrección de la noticia ya publicada. Corregir un borrador
    # antes de publicarlo (o una retirada antes de volver a publicarla) no puede dejar una corrección anterior a la publicación
    # que impida compilar el sitio; mientras no se corrija después de publicada, su modificación es la de publicación.
    with copia() as sitio:
        gestor_ok(
            "const hora = (s) => new Date(s);"
            "const a = g.crear(carpeta, { titular: 'Borrador corregido y publicado', entradilla: 'e', texto: 't' });"
            "g.corregir(carpeta, a, { texto: 't2' }, { ahora: hora('2026-10-10T09:00:00+02:00') });"
            "g.publicar(carpeta, a, { fecha: hora('2026-10-10T12:00:00+02:00') });"
            "const b = g.crear(carpeta, { titular: 'Retirada, corregida y publicada otra vez', entradilla: 'e', texto: 't' });"
            "g.publicar(carpeta, b, { fecha: hora('2026-10-10T12:00:00+02:00') });"
            "g.retirar(carpeta, b);"
            "g.corregir(carpeta, b, { texto: 't2' }, { ahora: hora('2026-10-11T09:00:00+02:00') });"
            "g.publicar(carpeta, b, { fecha: hora('2026-10-12T12:00:00+02:00') });",
            noticias_de(sitio),
        )
        r = compilar(sitio)
        assert r.returncode == 0, f"la compilación salió con {r.returncode}: {salida(r)}"
        for direccion, publicada in (("borrador-corregido-y-publicado", "2026-10-10T12:00:00+02:00"),
                                      ("retirada-corregida-y-publicada-otra-vez", "2026-10-12T12:00:00+02:00")):
            html = (sitio / "dist" / "noticias" / direccion / "index.html").read_text(encoding="utf-8")
            fechas = dict(re.findall(r'"(datePublished|dateModified)":"([^"]+)"', html))
            assert fechas == {"datePublished": publicada, "dateModified": publicada}, f"{direccion}: {fechas}"


# ---------------------------------------------------------------- el gestor y el cargador no tocan lo que no es suyo


def test_rn_let_02_07_gestor_no_pisa_fotos_ni_escribe_fuera_de_su_carpeta():
    # CA-LET-02-29
    # El gestor guarda la foto de cada noticia en su carpeta: dos noticias con una foto del mismo nombre (IMG_0001.jpg) no se
    # pisan, y un nombre con ruta («../fuera.jpg») no escribe fuera de la carpeta.
    with tempfile.TemporaryDirectory(prefix="letizia-gestor-") as tmp:
        carpeta = Path(tmp) / "a" / "noticias"
        gestor_ok(
            "g.crear(carpeta, { titular: 'Primera', entradilla: 'e', texto: 't', foto: { fichero: 'IMG_0001.jpg', bytes: Buffer.from('primera') }, fotoAutor: 'x' });",
            carpeta,
        )
        segunda = gestor(
            "g.crear(carpeta, { titular: 'Segunda', entradilla: 'e', texto: 't', foto: { fichero: 'IMG_0001.jpg', bytes: Buffer.from('segunda') }, fotoAutor: 'x' });",
            carpeta,
        )
        assert segunda.returncode != 0, "el gestor aceptó una segunda foto con el nombre de otra"
        assert (carpeta / "IMG_0001.jpg").read_bytes() == b"primera", "la segunda noticia pisó la foto de la primera"
        fuera = gestor(
            "g.crear(carpeta, { titular: 'Tercera', entradilla: 'e', texto: 't', foto: { fichero: '../fuera.jpg', bytes: Buffer.from('fuera') }, fotoAutor: 'x' });",
            carpeta,
        )
        assert fuera.returncode != 0, "el gestor aceptó una foto con ruta"
        assert not (Path(tmp) / "a" / "fuera.jpg").exists(), "el gestor escribió una foto fuera de su carpeta"
        assert sorted(p.name for p in carpeta.glob("*.md")) == ["primera.md"], "una noticia rechazada dejó su fichero"


def test_rn_let_02_19_cargador_no_vacia_contenido_noticias_con_otro_nombre():
    # CA-LET-02-30
    # El cargador del juego regenera su carpeta entera: no puede apuntar a contenido/noticias, tampoco por un enlace o con
    # otra grafía (en macOS «Contenido/Noticias» es la misma carpeta), o borraría las noticias reales.
    with copia() as sitio:
        real = noticias_de(sitio)
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Noticia real', entradilla: 'e', texto: 't' }));", real)
        (sitio / "enlace").symlink_to(real, target_is_directory=True)
        r = subprocess.run(
            ["node", "herramientas/cargar-juego.mjs", "enlace", str(sitio / "juego.json")],
            cwd=sitio, capture_output=True, text=True, timeout=60,
        )
        assert r.returncode != 0, "el cargador aceptó cargar el juego donde viven las noticias reales"
        assert (real / "noticia-real.md").is_file(), "el cargador borró una noticia real"


# ---------------------------------------------------------------- lo que vieron los escépticos de la segunda vuelta (16-oct)


def test_rn_let_02_02_titular_prueba_a_no_toma_una_direccion_del_juego():
    # CA-LET-02-31 · RN-LET-02-02: una noticia real titulada «Prueba A» no recibe la dirección fija prueba-a del juego de pruebas
    # (recibe otra, prueba-a-2) y la compilación de producción la publica en vez de caerse.
    with copia() as sitio:
        r = gestor_ok(
            "const d = g.crear(carpeta, { titular: 'Prueba A', entradilla: 'e', texto: 't' });"
            "g.publicar(carpeta, d, { fecha: new Date('2026-10-12T10:00:00+02:00') }); console.log(d);",
            noticias_de(sitio),
        )
        direccion = r.stdout.strip().splitlines()[-1]
        assert direccion != "prueba-a" and direccion.startswith("prueba-a"), f"dirección asignada a «Prueba A»: {direccion!r}"
        c = compilar(sitio)
        assert c.returncode == 0, f"la compilación de producción salió con {c.returncode}: {salida(c)}"
        assert (sitio / "dist" / "noticias" / direccion / "index.html").is_file(), f"no hay página para /noticias/{direccion}/"


def test_rn_let_02_20_gestor_rechaza_una_foto_que_no_es_una_imagen():
    # CA-LET-02-32 · RN-LET-02-20: una «foto» llamada otra.md la leería el cargador como noticia y rompería la compilación entera;
    # el gestor solo acepta nombres de fichero de imagen (jpg, png, webp, avif o gif), sin ruta ni espacios.
    with tempfile.TemporaryDirectory(prefix="letizia-gestor-") as tmp:
        carpeta = Path(tmp) / "noticias"
        for nombre in ("otra.md", "sin-extension", "foto final.jpg", "noticia.md.jpg"):
            r = gestor(
                f"g.crear(carpeta, {{ titular: 'Con foto', entradilla: 'e', texto: 't', foto: {{ fichero: {json.dumps(nombre)}, bytes: Buffer.from('x') }}, fotoAutor: 'x' }});",
                carpeta,
            )
            if nombre == "noticia.md.jpg":
                assert r.returncode == 0, f"el gestor rechazó una foto válida ({nombre!r}): {r.stderr.strip()[-300:]}"
                continue
            assert r.returncode != 0, f"el gestor aceptó una foto llamada {nombre!r}"
            assert not (carpeta / nombre).exists(), f"el gestor escribió {nombre!r}"
        assert sorted(p.name for p in carpeta.glob("*.md")) == ["con-foto.md"], "una noticia rechazada dejó su fichero"


def test_rn_let_02_21_cargador_no_vacia_una_carpeta_con_noticias_ajenas():
    # CA-LET-02-33 · RN-LET-02-21: el cargador regenera su carpeta entera, pero solo si todo lo que hay en ella es del juego; con
    # una noticia sin la marca «prueba: true» o cualquier otro .md (una carpeta de otro, como docs/), se niega y no borra nada.
    with copia() as sitio:
        carpeta = sitio / ".juego"
        gestor_ok("g.crear(carpeta, { titular: 'Noticia ajena', entradilla: 'e', texto: 't' });", carpeta)
        (carpeta / "apunte.md").write_text("# Un apunte que no es una noticia\n", encoding="utf-8")
        r = subprocess.run(
            ["node", "herramientas/cargar-juego.mjs", ".juego", str(sitio / "juego.json")],
            cwd=sitio, capture_output=True, text=True, timeout=60,
        )
        assert r.returncode != 0, "el cargador aceptó una carpeta con noticias que no son del juego"
        assert (carpeta / "noticia-ajena.md").is_file() and (carpeta / "apunte.md").is_file(), "el cargador borró ficheros ajenos"


def test_rn_let_02_19_noticias_dir_a_las_noticias_reales_no_apaga_las_guardas():
    # CA-LET-02-34 · RN-LET-02-19: NOTICIAS_DIR solo convierte la compilación en una de pruebas si apunta a otra carpeta. Apuntando
    # a contenido/noticias, directamente o por un enlace, una noticia marcada del juego sigue tumbando la compilación.
    with copia() as sitio:
        real = noticias_de(sitio)
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Noticia colada', entradilla: 'e', texto: 't', prueba: true }));", real)
        (sitio / "enlace-noticias").symlink_to(real, target_is_directory=True)
        for forma in (str(real), str(sitio / "enlace-noticias")):
            r = compilar(sitio, {"NOTICIAS_DIR": forma})
            assert r.returncode != 0, f"con NOTICIAS_DIR={forma} la compilación publicó una noticia del juego"
            assert "juego de pruebas" in texto(r), f"NOTICIAS_DIR={forma}: la compilación falló por otro motivo: {salida(r)}"


def test_rn_let_02_11_publicada_con_fecha_futura_y_corregida_compila():
    # CA-LET-02-35 · RN-LET-02-11: una noticia publicada con fecha futura (programada) y corregida antes de esa fecha no rompe la
    # compilación: su dateModified es la fecha de publicación, nunca una anterior a ella.
    with copia() as sitio:
        gestor_ok(
            "const d = g.crear(carpeta, { titular: 'Programada', entradilla: 'e', texto: 't' });"
            "g.publicar(carpeta, d, { fecha: new Date('2027-01-05T10:00:00+01:00') });"
            "g.corregir(carpeta, d, { texto: 't2' }, { ahora: new Date('2026-10-16T12:00:00+02:00') });",
            noticias_de(sitio),
        )
        r = compilar(sitio)
        assert r.returncode == 0, f"la compilación salió con {r.returncode}: {salida(r)}"
        html = (sitio / "dist" / "noticias" / "programada" / "index.html").read_text(encoding="utf-8")
        fechas = dict(re.findall(r'"(datePublished|dateModified)":"([^"]+)"', html))
        assert fechas == {"datePublished": "2027-01-05T10:00:00+01:00", "dateModified": "2027-01-05T10:00:00+01:00"}, fechas



def test_rn_let_02_02_un_borrador_a_medias_no_tumba_la_compilacion():
    # CA-LET-02-36 · RN-LET-02-02 y RN-LET-02-07: un borrador incompleto (foto sin autor, sin entradilla) convive con una noticia
    # publicada: la compilación de producción sale 0, la publicada tiene su página y del borrador no sale nada; y publicar ese
    # borrador tal cual se rechaza (RN-LET-02-05: una foto publicada lleva su autor).
    with copia() as sitio:
        gestor_ok(
            "g.crear(carpeta, { titular: 'Borrador a medias', entradilla: '', texto: 't', foto: { fichero: 'a-medias.jpg', bytes: foto } });"
            "g.publicar(carpeta, g.crear(carpeta, { titular: 'Pleno municipal', entradilla: 'e', texto: 't' }), { fecha: new Date('2026-10-12T10:00:00+02:00') });",
            noticias_de(sitio),
        )
        r = compilar(sitio)
        assert r.returncode == 0, f"un borrador a medias tumbó la compilación de producción ({r.returncode}): {salida(r)}"
        assert (sitio / "dist" / "noticias" / "pleno-municipal" / "index.html").is_file(), "la noticia publicada no tiene página"
        assert not (sitio / "dist" / "noticias" / "borrador-a-medias").exists(), "el borrador tiene página"
        assert not any("a-medias" in a for a in archivos(sitio / "dist")), "la foto del borrador salió a dist/"
        r = gestor("g.publicar(carpeta, 'borrador-a-medias');", noticias_de(sitio))
        assert r.returncode != 0, "el gestor publicó una noticia con foto sin autor y sin entradilla"


def test_rn_let_02_11_publicar_dos_veces_no_reinicia_la_fecha_ni_la_correccion():
    # CA-LET-02-37 · RN-LET-02-11 y RN-LET-02-01: publicar() sobre una noticia ya publicada se niega; su fecha de publicación (el
    # orden de la lista) y su última corrección no cambian.
    with tempfile.TemporaryDirectory(prefix="letizia-gestor-") as tmp:
        carpeta = Path(tmp) / "noticias"
        gestor_ok(
            "const d = g.crear(carpeta, { titular: 'Pleno', entradilla: 'e', texto: 't' });"
            "g.publicar(carpeta, d, { fecha: new Date('2026-10-12T10:00:00+02:00') });"
            "g.corregir(carpeta, d, { texto: 't2' }, { ahora: new Date('2026-10-13T10:00:00+02:00') });",
            carpeta,
        )
        antes = (carpeta / "pleno.md").read_text(encoding="utf-8")
        assert 'publicada: "2026-10-12T10:00:00+02:00"' in antes and 'modificada: "2026-10-13T10:00:00+02:00"' in antes, antes
        r = gestor("g.publicar(carpeta, 'pleno');", carpeta)
        assert r.returncode != 0, "el gestor volvió a publicar una noticia ya publicada"
        assert (carpeta / "pleno.md").read_text(encoding="utf-8") == antes, "publicar dos veces cambió la noticia"


def test_rn_let_02_20_el_gestor_no_acepta_direcciones_con_ruta():
    # CA-LET-02-38 · RN-LET-02-20: publicar, corregir, retirar y estadoDe rechazan una dirección que no es de noticia («../x»): ni
    # leen ni escriben fuera de la carpeta, aunque fuera haya un fichero con forma de noticia.
    with tempfile.TemporaryDirectory(prefix="letizia-gestor-") as tmp:
        carpeta = Path(tmp) / "a" / "noticias"
        carpeta.mkdir(parents=True)
        fuera = Path(tmp) / "a" / "x.md"
        original = '---\ntitular: "Fuera"\nentradilla: "e"\n---\n\nt\n'
        fuera.write_text(original, encoding="utf-8")
        for llamada in ("g.publicar(carpeta, '../x')", "g.corregir(carpeta, '../x', { texto: 'z' })", "g.retirar(carpeta, '../x')", "g.estadoDe(carpeta, '../x')"):
            r = gestor(llamada + ";", carpeta)
            assert r.returncode != 0, f"el gestor aceptó la dirección «../x» en {llamada}"
        assert fuera.read_text(encoding="utf-8") == original, "el gestor escribió fuera de su carpeta"

# ---------------------------------------------------------------- ejecución


def ejecutar(espacio, argv):
    if not __debug__:
        print("estas comprobaciones no corren con -O ni PYTHONOPTIMIZE: sin assert no comprobarían nada")
        return 3
    tests = {n: f for n, f in sorted(espacio.items()) if n.startswith("test_") and callable(f)}
    nombres = argv or list(tests)
    desconocidos = [n for n in nombres if n not in tests]
    if desconocidos:
        print(f"no existen: {', '.join(desconocidos)}")
        return 2
    if not (FUENTE / "node_modules").is_dir():
        print("faltan las dependencias de sitio/: corre «npm ci» allí (o bash tests/puerta.sh servir)")
        return 3
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
    print(f"{len(nombres) - fallos - errores} pasan, {fallos} fallan, {errores} con error (DOMINIO={DOMINIO})")
    return 3 if errores else (1 if fallos else 0)


if __name__ == "__main__":
    sys.exit(ejecutar(globals(), sys.argv[1:]))
