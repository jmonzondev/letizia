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


def compilar(sitio, extra=None, cwd=None, root=None, out_dir=None):
    """La compilación de producción: sin NOTICIAS_DIR, con DOMINIO (y lo que traiga extra). Por defecto se lanza desde sitio/;
    con cwd y root se lanza desde otra carpeta con «astro build --root». Devuelve el proceso terminado."""
    entorno = {**os.environ, "DOMINIO": DOMINIO}
    entorno.pop("NOTICIAS_DIR", None)
    entorno.update(extra or {})
    orden = [str(sitio / "node_modules" / ".bin" / "astro"), "build"] + (["--root", str(root)] if root else []) + (["--outDir", out_dir] if out_dir else [])
    return subprocess.run(orden, cwd=cwd or sitio, env=entorno, capture_output=True, text=True, timeout=300)


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
    def marcada(carpeta):
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Noticia de prueba repetida: Año Nuevo en Talavera', entradilla: 'e', texto: 't', prueba: true }));", carpeta)

    def con_direccion_fija(carpeta):
        # el gestor ya no da prueba-a a una noticia real (CA-LET-02-43): se escribe a mano, como alguien con acceso a la carpeta
        (carpeta / "prueba-a.md").write_text('---\ntitular: "Otra"\nentradilla: "e"\nestado: "publicada"\npublicada: "2026-10-12T10:00:00+02:00"\n---\n\nt\n', encoding="utf-8")

    casos = {"marcada como del juego": marcada, "con la dirección prueba-a escrita a mano": con_direccion_fija}
    for caso, prepara in casos.items():
        with copia() as sitio:
            prepara(noticias_de(sitio))
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
            "g.crear(carpeta, { titular: 'Primera', entradilla: 'e', texto: 't', foto: { fichero: 'IMG_0001.jpg', bytes: Buffer.concat([foto, Buffer.from('primera')]) }, fotoAutor: 'x' });",
            carpeta,
        )
        segunda = gestor(
            "g.crear(carpeta, { titular: 'Segunda', entradilla: 'e', texto: 't', foto: { fichero: 'IMG_0001.jpg', bytes: Buffer.concat([foto, Buffer.from('segunda')]) }, fotoAutor: 'x' });",
            carpeta,
        )
        assert segunda.returncode != 0, "el gestor aceptó una segunda foto con el nombre de otra"
        assert (carpeta / "IMG_0001.jpg").read_bytes().endswith(b"primera"), "la segunda noticia pisó la foto de la primera"
        fuera = gestor(
            "g.crear(carpeta, { titular: 'Tercera', entradilla: 'e', texto: 't', foto: { fichero: '../fuera.jpg', bytes: foto }, fotoAutor: 'x' });",
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


# ---------------------------------------------------------------- lo que vio la revisión de la segunda vuelta (16-oct)


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
                f"g.crear(carpeta, {{ titular: 'Con foto', entradilla: 'e', texto: 't', foto: {{ fichero: {json.dumps(nombre)}, bytes: foto }}, fotoAutor: 'x' }});",
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

# ---------------------------------------------------------------- lo que vio la revisión final (16-oct)


def test_rn_let_02_19_noticias_dir_se_resuelve_como_lo_lee_astro():
    # CA-LET-02-39 · RN-LET-02-19: NOTICIAS_DIR se resuelve una sola vez y exactamente como la lee Astro (contra la raíz de sitio/),
    # así que da igual desde qué carpeta se lance la orden, y «#», file:// o un nombre que no existe no apagan las guardas.
    with copia() as sitio:
        real = noticias_de(sitio)
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Noticia colada', entradilla: 'e', texto: 't', prueba: true }));", real)
        casos = {
            "relativo, lanzado desde la carpeta de arriba con --root": ({"NOTICIAS_DIR": "contenido/noticias"}, sitio.parent, sitio),
            "con una almohadilla detrás": ({"NOTICIAS_DIR": "contenido/noticias#x"}, None, None),
            "como dirección file://": ({"NOTICIAS_DIR": real.as_uri()}, None, None),
        }
        for caso, (extra, cwd, root) in casos.items():
            r = compilar(sitio, extra, cwd=cwd, root=root)
            assert r.returncode != 0, f"NOTICIAS_DIR {caso}: la compilación publicó una noticia del juego"
            assert "juego de pruebas" in texto(r), f"NOTICIAS_DIR {caso}: falló por otro motivo: {salida(r)}"
        r = compilar(sitio, {"NOTICIAS_DIR": "no-existe"})
        assert r.returncode != 0 and "no es una carpeta" in texto(r), f"una NOTICIAS_DIR que no existe no se rechaza con claridad: {salida(r)}"


def test_rn_let_02_21_cargador_no_toca_registro_ni_fotos_ajenos():
    # CA-LET-02-40 · RN-LET-02-21: el cargador no escribe el registro JUEGO dentro de las noticias reales, no borra una carpeta que
    # solo tiene fotos ni una foto que no es del juego, y la marca del juego solo cuenta en la cabecera, no en el texto.
    with copia() as sitio:
        real = noticias_de(sitio)
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Pleno municipal', entradilla: 'e', texto: 't' }));", real)
        antes = (real / "pleno-municipal.md").read_text(encoding="utf-8")
        r = subprocess.run(["node", "herramientas/cargar-juego.mjs", ".juego", str(real / "pleno-municipal.md")], cwd=sitio, capture_output=True, text=True, timeout=60)
        assert r.returncode != 0, "el cargador aceptó escribir el registro sobre una noticia real"
        assert (real / "pleno-municipal.md").read_text(encoding="utf-8") == antes, "el cargador sustituyó una noticia real por el registro"
        fotos = sitio / "fotos"
        fotos.mkdir()
        (fotos / "vacaciones.jpg").write_bytes(b"jpg")
        r = subprocess.run(["node", "herramientas/cargar-juego.mjs", "fotos", str(sitio / "juego.json")], cwd=sitio, capture_output=True, text=True, timeout=60)
        assert r.returncode != 0 and (fotos / "vacaciones.jpg").exists(), "el cargador vació una carpeta que solo tenía fotos"
        texto_con_marca = sitio / "texto"
        texto_con_marca.mkdir()
        (texto_con_marca / "ajena.md").write_text('---\ntitular: "Ajena"\n---\n\nprueba: true\n', encoding="utf-8")
        r = subprocess.run(["node", "herramientas/cargar-juego.mjs", "texto", str(sitio / "juego.json")], cwd=sitio, capture_output=True, text=True, timeout=60)
        assert r.returncode != 0 and (texto_con_marca / "ajena.md").exists(), "el cargador tomó por del juego una noticia con la marca en el texto"
        juego = sitio / ".juego"
        r = subprocess.run(["node", "herramientas/cargar-juego.mjs", ".juego", str(sitio / "juego.json")], cwd=sitio, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, f"el cargador no cargó el juego en una carpeta limpia: {r.stderr.strip()[-300:]}"
        (juego / "ajena.jpg").write_bytes(b"jpg")
        r = subprocess.run(["node", "herramientas/cargar-juego.mjs", ".juego", str(sitio / "juego.json")], cwd=sitio, capture_output=True, text=True, timeout=60)
        assert r.returncode != 0 and (juego / "ajena.jpg").exists(), "el cargador borró una foto que no es del juego"


def test_rn_let_02_02_borrador_con_campos_a_medias_no_tumba_la_compilacion():
    # CA-LET-02-41 · RN-LET-02-02 y 07: ningún borrador a medias tumba la compilación (autor de la foto vacío, fecha escrita a mano
    # que no es una fecha), y el gestor no deja corregir a vacío el titular ni la entradilla de una publicada, ni publicar con el
    # autor de la foto en blanco.
    with copia() as sitio:
        carpeta = noticias_de(sitio)
        gestor_ok(
            "g.crear(carpeta, { titular: 'Sin autor', entradilla: 'e', texto: 't', foto: { fichero: 'sin-autor.jpg', bytes: foto }, fotoAutor: '' });"
            "g.publicar(carpeta, g.crear(carpeta, { titular: 'Pleno municipal', entradilla: 'e', texto: 't' }), { fecha: new Date('2026-10-12T10:00:00+02:00') });"
            "g.crear(carpeta, { titular: 'Con foto en blanco', entradilla: 'e', texto: 't', foto: { fichero: 'en-blanco.jpg', bytes: foto }, fotoAutor: '   ' });",
            carpeta,
        )
        (carpeta / "a-mano.md").write_text('---\ntitular: "A mano"\npublicada: "mañana"\n---\n\nt\n', encoding="utf-8")
        for llamada in ("g.corregir(carpeta, 'sin-autor', { titular: '' })", "g.corregir(carpeta, 'pleno-municipal', { entradilla: ' ' })", "g.publicar(carpeta, 'con-foto-en-blanco')"):
            r = gestor(llamada + ";", carpeta)
            assert r.returncode != 0, f"el gestor aceptó {llamada}"
        r = compilar(sitio)
        assert r.returncode == 0, f"un borrador a medias tumbó la compilación ({r.returncode}): {salida(r)}"
        assert (sitio / "dist" / "noticias" / "pleno-municipal" / "index.html").is_file()
        assert not any("sin-autor" in a or "en-blanco" in a or "a-mano" in a for a in archivos(sitio / "dist")), "salió algo de un borrador"


def test_rn_let_02_20_crear_a_la_vez_no_pisa_noticias():
    # CA-LET-02-42 · RN-LET-02-17 y 20: varias altas a la vez con el mismo titular, o con la misma foto, no se pisan: cada noticia
    # que el gestor da por creada está en la carpeta, y las que no caben fallan.
    with tempfile.TemporaryDirectory(prefix="letizia-gestor-") as tmp:
        carpeta = Path(tmp) / "noticias"
        carpeta.mkdir()
        guion = (
            f"import * as g from {json.dumps(GESTOR)}; import {{ readFileSync }} from 'node:fs'; const carpeta = {json.dumps(str(carpeta))};"
            f"const foto = readFileSync({json.dumps(str(FOTO))});"
            "g.crear(carpeta, { titular: 'Pleno', entradilla: 'e', texto: 't', foto: { fichero: 'IMG.jpg', bytes: foto }, fotoAutor: 'x' });"
        )
        procesos = [subprocess.Popen(["node", "--input-type=module", "-e", guion], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True) for _ in range(6)]
        exitos = sum(1 for p in procesos if p.wait(timeout=60) == 0)
        noticias = sorted(p.name for p in carpeta.glob("*.md"))
        assert exitos >= 1, "ninguna de las altas a la vez salió bien"
        assert len(noticias) == exitos, f"{exitos} altas dieron éxito, pero hay {len(noticias)} noticias: {noticias}"
        assert exitos == 1, f"la misma foto IMG.jpg se dio por escrita {exitos} veces"


def test_rn_let_02_19_direccion_fija_del_juego_no_se_pide_para_una_noticia_real():
    # CA-LET-02-43 · RN-LET-02-19: una noticia real no puede pedir una de las seis direcciones fijas del juego (prueba-a a prueba-f);
    # solo el cargador, con la marca del juego, las usa.
    with tempfile.TemporaryDirectory(prefix="letizia-gestor-") as tmp:
        carpeta = Path(tmp) / "noticias"
        r = gestor("g.crear(carpeta, { titular: 'Otra', entradilla: 'e', texto: 't', direccion: 'prueba-a' });", carpeta)
        assert r.returncode != 0 and not (carpeta / "prueba-a.md").exists(), "el gestor dio prueba-a a una noticia real"
        gestor_ok("g.crear(carpeta, { titular: 'Noticia de prueba A', entradilla: 'e', texto: 't', direccion: 'prueba-a', prueba: true });", carpeta)
        assert (carpeta / "prueba-a.md").is_file()


# ---------------------------------------------------------------- lo que vio la cuarta revisión (16-oct)


def cargador(sitio, carpeta, registro):
    return subprocess.run(["node", "herramientas/cargar-juego.mjs", carpeta, registro], cwd=sitio, capture_output=True, text=True, timeout=60)


def test_rn_let_02_19_solo_sitio_juego_es_la_carpeta_de_pruebas():
    # CA-LET-02-45 · RN-LET-02-19: la única carpeta de pruebas es sitio/.juego. Cualquier otra NOTICIAS_DIR (una carpeta con «#» o «?»
    # en el nombre escrita con %23 o %3F, %25 doble, sitio/public, una subcarpeta de las noticias reales u otra carpeta cualquiera) se
    # rechaza antes de compilar, y a Astro nunca le llega una ruta escrita por nadie.
    with copia() as sitio:
        real = noticias_de(sitio)
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Noticia colada', entradilla: 'e', texto: 't', prueba: true }));", real)
        for rara in ("noticias#x", "noticias?x", "noticias/sub"):
            (sitio / "contenido" / rara).mkdir(parents=True)
        (sitio / "otra-carpeta").mkdir()
        casos = {
            "%23 con una carpeta «noticias#x» que existe": "contenido/noticias%23x",
            "%3F con una carpeta «noticias?x» que existe": "contenido/noticias%3Fx",
            "%25 doble": "contenido/%256Eoticias",
            "sitio/public": "public",
            "una subcarpeta de las noticias reales": "contenido/noticias/sub",
            "otra carpeta cualquiera": "otra-carpeta",
        }
        for caso, valor in casos.items():
            r = compilar(sitio, {"NOTICIAS_DIR": valor})
            assert r.returncode != 0, f"NOTICIAS_DIR {caso}: la compilación salió con 0"
            assert "juego de pruebas" in texto(r), f"NOTICIAS_DIR {caso}: falló por otro motivo: {salida(r)}"
        r = cargador(sitio, ".juego", str(sitio / "juego.json"))
        assert r.returncode == 0, f"el cargador no cargó el juego en sitio/.juego: {r.stderr.strip()[-300:]}"
        r = compilar(sitio, {"NOTICIAS_DIR": ".juego"}, out_dir="dist-juego")
        assert r.returncode == 0, f"la compilación de pruebas con sitio/.juego falló: {salida(r)}"
        assert (sitio / "dist-juego" / "noticias" / "prueba-a" / "index.html").is_file(), "la compilación de pruebas no publicó el juego"
        assert not (sitio / "dist-juego" / "noticias" / "noticia-colada").exists(), "la compilación de pruebas leyó las noticias reales"
        assert not (sitio / "dist").exists(), "la compilación de pruebas escribió en sitio/dist, la carpeta que se despliega"


def test_rn_let_02_07_borradores_con_cualquier_cosa_a_medias_no_tumban_la_compilacion():
    # CA-LET-02-46 · RN-LET-02-02 y 07: lo que no está publicado no se valida al compilar, así que ningún borrador, tenga lo que
    # tenga (campos vacíos, nulos, una fecha sin comillas, un estado mal escrito, una foto que no existe, una fuente que no es
    # tal), tumba la compilación; y el gestor no deja crear noticias con campos que no son texto.
    with copia() as sitio:
        carpeta = noticias_de(sitio)
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Pleno municipal', entradilla: 'e', texto: 't' }), { fecha: new Date('2026-10-12T10:00:00+02:00') });", carpeta)
        for llamada in (
            "g.crear(carpeta, { titular: 'Nulo', entradilla: null, texto: 't' })",
            "g.crear(carpeta, { titular: 'Autor nulo', entradilla: 'e', texto: 't', foto: { fichero: 'n.jpg', bytes: foto }, fotoAutor: null })",
            "g.crear(carpeta, { titular: 'Fuente rara', entradilla: 'e', texto: 't', fuente: 3 })",
            "g.crear(carpeta, { titular: 7, entradilla: 'e', texto: 't' })",
        ):
            r = gestor(llamada + ";", carpeta)
            assert r.returncode != 0, f"el gestor aceptó {llamada}"
        a_mano = {
            "autor-vacio.md": '---\ntitular: "Autor vacío"\nfotoAutor:\nfoto: "./no-existe.jpg"\n---\n\nt\n',
            "sin-titular.md": '---\ntitular:\nentradilla: "e"\n---\n\nt\n',
            "fecha-sin-comillas.md": '---\ntitular: "Fecha"\npublicada: 2026-10-20T10:00:00+02:00\n---\n\nt\n',
            "estado-raro.md": '---\ntitular: "Estado"\nentradilla: "e"\nestado: "publicado"\npublicada: "2026-10-12T10:00:00+02:00"\n---\n\nt\n',
            "fuente-numero.md": '---\ntitular: "Fuente"\nfuente: 3\n---\n\nt\n',
            "yaml-roto.md": '---\ntitular: "Roto\nentradilla: [sin cerrar\n---\n\nt\n',
            "Borrador Nuevo.md": '---\ntitular: "Nombre que no es dirección"\n---\n\nt\n',
            "prueba-texto.md": '---\ntitular: "Marca como texto"\nprueba: "true"\n---\n\nt\n',
        }
        for nombre, contenido in a_mano.items():
            (carpeta / nombre).write_text(contenido, encoding="utf-8")
        r = compilar(sitio)
        assert r.returncode == 0, f"un borrador a medias tumbó la compilación ({r.returncode}): {salida(r)}"
        assert (sitio / "dist" / "noticias" / "pleno-municipal" / "index.html").is_file(), "la publicada no tiene página"
        for direccion in ("autor-vacio", "sin-titular", "fecha-sin-comillas", "estado-raro", "fuente-numero", "yaml-roto", "borrador-nuevo", "Borrador Nuevo", "prueba-texto"):
            assert not (sitio / "dist" / "noticias" / direccion).exists(), f"el borrador {direccion} tiene página"
        # Lo mismo mal escrito pero publicado no se compila, y el aviso es el nuestro, no uno de Astro
        (carpeta / "yaml-roto.md").write_text('---\ntitular: "Roto\nestado: "publicada"\n---\n\nt\n', encoding="utf-8")
        r = compilar(sitio)
        assert r.returncode != 0 and "no se puede leer" in texto(r), f"una publicada ilegible no falla con nuestro aviso: {salida(r)}"
        (carpeta / "yaml-roto.md").unlink()
        (carpeta / "prueba-texto.md").write_text('---\ntitular: "Marca como texto"\nentradilla: "e"\nestado: "publicada"\npublicada: "2026-10-12T10:00:00+02:00"\nprueba: "true"\n---\n\nt\n', encoding="utf-8")
        r = compilar(sitio)
        assert r.returncode != 0 and "juego de pruebas" in texto(r), f"una publicada con la marca del juego como texto entró en producción: {salida(r)}"


def test_rn_let_02_21_cargador_solo_trabaja_en_su_carpeta_y_con_su_registro():
    # CA-LET-02-47 · RN-LET-02-21: el cargador solo trabaja en sitio/.juego o fuera de sitio/, nunca en las noticias reales ni en
    # sus subcarpetas ni en public/ o src/; y el registro ha de ser un .json fuera de esas carpetas, que no sea un enlace y que, si
    # existe, sea un registro del juego: ni package.json, ni los datos de la titular, ni un fichero cualquiera.
    with copia() as sitio:
        real = noticias_de(sitio)
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Pleno municipal', entradilla: 'e', texto: 't' }));", real)
        paquete = (sitio / "package.json").read_text(encoding="utf-8")
        titular = (sitio.parent / "tests" / "sitio" / "titular.json").read_text(encoding="utf-8")
        for registro in ("package.json", "../tests/sitio/titular.json", "contenido/noticias/sub/juego.json", "registro.txt"):
            r = cargador(sitio, ".juego", registro)
            assert r.returncode != 0, f"el cargador aceptó el registro {registro!r}"
        assert (sitio / "package.json").read_text(encoding="utf-8") == paquete, "el cargador pisó package.json"
        assert (sitio.parent / "tests" / "sitio" / "titular.json").read_text(encoding="utf-8") == titular, "el cargador pisó los datos de la titular"
        assert not (real / "sub").exists(), "el cargador creó una subcarpeta en las noticias reales"
        (sitio / "enlace.json").symlink_to(real / "nueva.md")
        r = cargador(sitio, ".juego", "enlace.json")
        assert r.returncode != 0 and not (real / "nueva.md").exists(), "el cargador siguió un enlace del registro hasta las noticias reales"
        for carpeta in ("contenido/noticias/sub", "public", "src/noticias", "contenido"):
            r = cargador(sitio, carpeta, str(sitio / "juego.json"))
            assert r.returncode != 0, f"el cargador aceptó la carpeta {carpeta!r}"
        assert not (real / "sub").exists() and not (sitio / "public" / "prueba-a.md").exists() and not (sitio / "contenido" / "prueba-a.md").exists()
        for raro in ('{"x": 1}', "{}", '{"A": "publicada"}'):
            (sitio / "juego.json").write_text(raro, encoding="utf-8")
            r = cargador(sitio, ".juego", str(sitio / "juego.json"))
            assert r.returncode != 0 and (sitio / "juego.json").read_text(encoding="utf-8") == raro, f"el cargador pisó un .json que no es un registro del juego: {raro}"
        (sitio / "juego.json").unlink()
        # .juego que es un enlace a las noticias reales o a public: no se carga nada en ningún sitio
        for destino, nombre in ((real, "las noticias reales"), (sitio / "public", "public")):
            (sitio / ".juego").symlink_to(destino, target_is_directory=True)
            r = cargador(sitio, ".juego", str(sitio / "juego.json"))
            (sitio / ".juego").unlink()
            assert r.returncode != 0, f"el cargador aceptó .juego como enlace a {nombre}"
            assert not (destino / "prueba-a.md").exists(), f"el cargador escribió el juego en {nombre} a través de un enlace .juego"
        # otra grafía de la ruta real (en un disco que no distingue mayúsculas, SITIO/… es la misma carpeta)
        mayusculas = sitio.parent / "SITIO"
        if mayusculas.exists():
            r = cargador(sitio, str(mayusculas / "contenido" / "noticias"), str(sitio.parent / "r.json"))
            assert r.returncode != 0 and not (real / "prueba-a.md").exists(), "el cargador escribió el juego en las noticias reales escritas con mayúsculas"
            r = cargador(sitio, ".juego", str(mayusculas / "contenido" / "noticias" / "r.json"))
            assert r.returncode != 0 and not (real / "r.json").exists(), "el cargador escribió el registro en las noticias reales escritas con mayúsculas"
        fuera = Path(tempfile.mkdtemp(prefix="letizia-juego-"))
        r = cargador(sitio, str(fuera), str(fuera / "juego.json"))
        assert r.returncode == 0 and (fuera / "prueba-a.md").is_file(), f"el cargador no acepta una carpeta fuera de sitio/: {r.stderr.strip()[-300:]}"


def test_rn_let_02_08_corregir_y_retirar_a_la_vez_no_pierden_la_retirada():
    # CA-LET-02-48 · RN-LET-02-08 y 20: publicar, corregir y retirar se turnan con un cerrojo por noticia y escriben de forma atómica:
    # corregir y retirar a la vez no deshacen la retirada; y un .md que es un enlace no se lee ni se escribe.
    with tempfile.TemporaryDirectory(prefix="letizia-gestor-") as tmp:
        carpeta = Path(tmp) / "noticias"
        gestor_ok("for (let i = 0; i < 8; i++) g.publicar(carpeta, g.crear(carpeta, { titular: 'Noticia ' + i, entradilla: 'e', texto: 't' }));", carpeta)
        pares = []
        for i in range(8):
            for codigo in (f"g.corregir(carpeta, 'noticia-{i}', {{ texto: 'z' }});", f"g.retirar(carpeta, 'noticia-{i}');"):
                guion = f"import * as g from {json.dumps(GESTOR)}; const carpeta = {json.dumps(str(carpeta))}; {codigo}"
                pares.append(subprocess.Popen(["node", "--input-type=module", "-e", guion], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True))
        fallos = [p.stderr.read()[-200:] for p in pares if p.wait(timeout=120) != 0]
        assert not fallos, f"operaciones a la vez que fallaron: {fallos}"
        r = gestor_ok("console.log(JSON.stringify([...Array(8).keys()].map((i) => g.estadoDe(carpeta, 'noticia-' + i))));", carpeta)
        estados = json.loads(r.stdout.strip().splitlines()[-1])
        assert estados == ["retirada"] * 8, f"una corrección a la vez deshizo una retirada: {estados}"
        fuera = Path(tmp) / "fuera.md"
        original = '---\ntitular: "Fuera"\nentradilla: "e"\n---\n\nt\n'
        fuera.write_text(original, encoding="utf-8")
        (carpeta / "enlace.md").symlink_to(fuera)
        for llamada in ("g.retirar(carpeta, 'enlace')", "g.estadoDe(carpeta, 'enlace')"):
            r = gestor(llamada + ";", carpeta)
            assert r.returncode != 0, f"el gestor siguió un enlace en {llamada}"
        assert fuera.read_text(encoding="utf-8") == original
        # un cerrojo huérfano (de un proceso que ya no existe) no bloquea la noticia para siempre
        gestor_ok("g.publicar(carpeta, g.crear(carpeta, { titular: 'Con cerrojo', entradilla: 'e', texto: 't' }));", carpeta)
        (carpeta / "con-cerrojo.md.cerrojo").write_text("999999 0", encoding="utf-8")
        r = gestor("g.retirar(carpeta, 'con-cerrojo'); console.log(g.estadoDe(carpeta, 'con-cerrojo'));", carpeta)
        assert r.returncode == 0 and r.stdout.strip().endswith("retirada"), f"un cerrojo huérfano bloqueó la noticia: {r.stderr.strip()[-200:]}"
        assert not (carpeta / "con-cerrojo.md.cerrojo").exists(), "el cerrojo huérfano se quedó"


def test_rn_let_02_04_fechas_imposibles_se_rechazan():
    # CA-LET-02-49 · RN-LET-02-03, 04 y 10: una fecha de nota de prensa que no existe («2026-02-30», «2026-13-01»), una fecha de
    # publicación o de corrección que no es una fecha, las rechaza el gestor; y una publicada escrita a mano con una fuente
    # imposible no se compila (falla cerrada), mientras que la misma noticia con la fecha bien sí.
    with copia() as sitio:
        carpeta = noticias_de(sitio)
        for llamada in (
            "g.crear(carpeta, { titular: 'Fuente mala', entradilla: 'e', texto: 't', fuente: { organismo: 'X', fecha: '2026-02-30' } })",
            "g.crear(carpeta, { titular: 'Fuente mala 2', entradilla: 'e', texto: 't', fuente: { organismo: 'X', fecha: '2026-13-01' } })",
            "g.publicar(carpeta, g.crear(carpeta, { titular: 'Sin fecha', entradilla: 'e', texto: 't' }), { fecha: new Date('x') })",
            "const d = g.crear(carpeta, { titular: 'Corregida', entradilla: 'e', texto: 't' }); g.publicar(carpeta, d); g.corregir(carpeta, d, { texto: 'z' }, { ahora: new Date('x') })",
        ):
            r = gestor(llamada + ";", carpeta)
            assert r.returncode != 0, f"el gestor aceptó {llamada}"
        mala = '---\ntitular: "Pleno"\nentradilla: "e"\nestado: "publicada"\npublicada: "2026-10-12T10:00:00+02:00"\nfuente: {"organismo": "Ayuntamiento", "fecha": "2026-02-30"}\n---\n\nt\n'
        (carpeta / "pleno.md").write_text(mala, encoding="utf-8")
        r = compilar(sitio)
        assert r.returncode != 0, "una publicada con una fecha de nota de prensa imposible se compiló"
        (carpeta / "pleno.md").write_text(mala.replace("2026-02-30", "2026-02-28"), encoding="utf-8")
        r = compilar(sitio)
        assert r.returncode == 0, f"la misma noticia con la fecha bien no compiló: {salida(r)}"
        assert "28 de febrero de 2026" in (sitio / "dist" / "noticias" / "pleno" / "index.html").read_text(encoding="utf-8")


def test_rn_let_02_05_la_foto_tiene_que_ser_una_imagen():
    # CA-LET-02-50 · RN-LET-02-05 y 06: el gestor no acepta como foto unos bytes que no son una imagen (jpg, png, gif, webp o avif):
    # si lo hiciera, publicar esa noticia tumbaría la compilación entera.
    with tempfile.TemporaryDirectory(prefix="letizia-gestor-") as tmp:
        carpeta = Path(tmp) / "noticias"
        r = gestor("g.crear(carpeta, { titular: 'Falsa', entradilla: 'e', texto: 't', foto: { fichero: 'falsa.jpg', bytes: Buffer.from('no soy una imagen, aunque me llame jpg') }, fotoAutor: 'x' });", carpeta)
        assert r.returncode != 0 and not (carpeta / "falsa.jpg").exists() and not (carpeta / "falsa.md").exists(), "el gestor aceptó una foto que no es una imagen"
        cabeceras = {
            "jpg": b"\xff\xd8\xff\xe0" + b"basura que no es un jpeg" * 4,
            "png": b"\x89PNG\r\n\x1a\n" + b"basura" * 8,
            "gif": b"GIF89a" + b"basura" * 8,
            "webp": b"RIFF\x00\x00\x00\x00WEBP" + b"basura" * 8,
        }
        for ext, bytes_ in cabeceras.items():
            r = gestor(f"g.crear(carpeta, {{ titular: 'Cabecera {ext}', entradilla: 'e', texto: 't', foto: {{ fichero: 'cabecera.{ext}', bytes: Buffer.from({list(bytes_)}) }}, fotoAutor: 'x' }});", carpeta)
            assert r.returncode != 0 and not (carpeta / f"cabecera.{ext}").exists(), f"el gestor aceptó una cabecera {ext} seguida de basura"
        gestor_ok("g.crear(carpeta, { titular: 'Buena', entradilla: 'e', texto: 't', foto: { fichero: 'buena.jpg', bytes: foto }, fotoAutor: 'x' });", carpeta)
        assert (carpeta / "buena.jpg").is_file()




def test_rn_let_02_06_publicada_con_foto_fuera_o_ausente_falla_con_aviso_propio():
    # CA-LET-02-51 · RN-LET-02-06 y 20: una publicada escrita a mano cuya foto apunta fuera de su carpeta («../x.jpg», una ruta
    # absoluta) o a un fichero que no existe no se compila, y el aviso es el nuestro, no uno de Astro; la misma con la foto en su
    # sitio compila.
    with copia() as sitio:
        carpeta = noticias_de(sitio)
        shutil.copy(FOTO, carpeta / "buena.jpg")
        shutil.copy(FOTO, sitio / "fuera.jpg")
        plantilla = '---\ntitular: "Pleno"\nentradilla: "e"\nestado: "publicada"\npublicada: "2026-10-12T10:00:00+02:00"\nfoto: "{foto}"\nfotoAutor: "x"\n---\n\nt\n'
        for foto in ("../fuera.jpg", str(sitio / "fuera.jpg"), "./no-existe.jpg", "buena.jpg"):
            (carpeta / "pleno.md").write_text(plantilla.format(foto=foto), encoding="utf-8")
            r = compilar(sitio)
            assert r.returncode != 0, f"una publicada con foto {foto!r} se compiló"
            assert "foto" in texto(r) and "RN-LET-02" in texto(r), f"la foto {foto!r} no falló con nuestro aviso: {salida(r)}"
        (carpeta / "pleno.md").write_text(plantilla.format(foto="./buena.jpg"), encoding="utf-8")
        r = compilar(sitio)
        assert r.returncode == 0, f"la misma noticia con la foto en su sitio no compiló: {salida(r)}"
        assert any("buena" in a for a in archivos(sitio / "dist")), "la foto buena no salió a dist/"


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
