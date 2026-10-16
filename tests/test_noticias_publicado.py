"""Comprobación de la sección de noticias en el sitio ya publicado (SPEC-LET-02), tras cada despliegue.

    DOMINIO=https://<dominio> python3 tests/test_noticias_publicado.py

Pregunta al sitio publicado, no a la compilación local: el juego de pruebas no puede haber llegado ahí. DOMINIO tiene que
ser una dirección pública: ni localhost, ni una IP de esta máquina o de una red privada (escrita como sea: «127.1» es
127.0.0.1), ni un dominio .local o .test, ni un nombre que resuelva a una de esas IP (127.0.0.1.nip.io, una entrada de
/etc/hosts); si no, falla antes de preguntar, porque contra la compilación local no dice nada del sitio publicado. Lee
además cada noticia que lleva su sitemap, porque G y H no tienen una dirección fija (la asigna el gestor). Mismos códigos
de salida que tests/test_noticias.py.
"""

import re
import sys

sys.dont_write_bytecode = True  # importar las comprobaciones locales no deja cachés en tests/

from test_noticias import (
    DOMINIO,
    TITULAR,
    TITULAR_C_ANTES,
    TITULAR_F_SIN_ETIQUETA,
    TITULAR_REPETIDO,
    dominio,
    ejecutar,
    muestra,
    pedir,
    rutas_del_sitemap,
)

PRUEBAS = [f"/noticias/prueba-{x}/" for x in "abcdef"]
TITULARES = sorted(set(TITULAR.values()) | {TITULAR_C_ANTES, TITULAR_F_SIN_ETIQUETA.split(":")[0], TITULAR_REPETIDO})


def test_ca_let_02_24_juego_de_pruebas_fuera_del_publicado():
    # CA-LET-02-24
    assert DOMINIO, "falta DOMINIO: no hay sitio publicado al que preguntar (el dominio está por decidir)"
    publicado = dominio(resolver=True)  # falla si no es pública o resuelve a esta máquina: la compilación local no cuenta
    for ruta in ("/", "/noticias/"):
        r = pedir(publicado + ruta)
        assert r.codigo == 200, f"{publicado}{ruta} responde {r.codigo}; se esperaba 200"
        vistos = muestra(r.html, TITULARES)  # en el código o en el texto visible
        assert not vistos, f"{publicado}{ruta} muestra noticias del juego de pruebas: {vistos}"
    codigos = {ruta: pedir(publicado + ruta).codigo for ruta in PRUEBAS}
    abiertas = {ruta: c for ruta, c in codigos.items() if c not in (404, 410)}
    assert not abiertas, f"direcciones del juego de pruebas que responden en el sitio publicado: {abiertas}"
    rutas = rutas_del_sitemap(publicado, mapear=False)
    en_sitemap = sorted(r for r in rutas if r in PRUEBAS)
    assert not en_sitemap, f"el sitemap publicado lleva direcciones del juego de pruebas: {en_sitemap}"
    con_juego = {}
    for ruta in sorted(r for r in rutas if re.fullmatch(r"/noticias/[^/]+/", r)):
        vistos = muestra(pedir(publicado + ruta).html, TITULARES)
        if vistos:
            con_juego[ruta] = vistos
    assert not con_juego, f"noticias del sitemap publicado que son del juego de pruebas: {con_juego}"


if __name__ == "__main__":
    sys.exit(ejecutar(globals(), sys.argv[1:]))
