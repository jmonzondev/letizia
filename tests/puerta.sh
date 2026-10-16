#!/usr/bin/env bash
# Puertas del sitio (DEC-L-004). Se corren desde cualquier carpeta; trabajan sobre la raíz de esta copia del repo.
#
#   bash tests/puerta.sh test <ruta>   un test: tests/sitio/<fichero>.py o tests/sitio/<fichero>.py::<test>, o
#                                      tests/test_noticias.py[::<test>] (LET-02, con el juego de pruebas cargado), o
#                                      tests/test_noticias_compilacion.py[::<test>] (LET-02, compila copias de sitio/)
#   bash tests/puerta.sh let-01        los tests de LET-01 y las órdenes de CA-LET-01-01, 07 y 22; mientras tests/sitio/titular.json
#                                      no tenga los cuatro datos de la titular, aparta CA-LET-01-17 y 29 con un aviso (la spec los
#                                      deja en rojo a propósito hasta tener los datos reales)
#   bash tests/puerta.sh let-02        carga el juego de pruebas de LET-02, compila con él y corre tests/test_noticias.py; después
#                                      corre tests/test_noticias_compilacion.py (compilación y gestor de noticias, sin servidor)
#   bash tests/puerta.sh servir        compila y deja el sitio y el buzón en marcha para probarlos a mano
#   bash tests/puerta.sh apagar        apaga lo que dejó «servir»
#
# Compila sitio/ (Astro), levanta el sitio (Apache con PHP) y el buzón de pruebas (Mailpit) en Docker, con un nombre de
# proyecto y unos puertos libres propios de esta carpeta de trabajo, exporta SITIO_URL, BUZON_URL y CORREO_CONTACTO, corre
# lo pedido y lo apaga. Hace falta Docker, Node y uv; el navegador (Chromium) lo instala Playwright si falta.
#
# DOMINIO es la dirección pública que la compilación escribe en canónicas, sitemap y robots.txt (por defecto, un dominio de
# pruebas que no es de nadie). NOTICIAS_DIR, JUEGO y el juego de pruebas solo existen en las puertas de LET-02.

set -u -o pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$RAIZ" || exit 2

SPEC_LET_01="docs/specs/LET-01-estructura-del-sitio-y-paginas-estaticas.md"
PROYECTO="letizia-$(printf '%s' "$RAIZ" | shasum | cut -c1-8)"
COMPOSE=(docker compose -p "$PROYECTO" -f tests/pila/docker-compose.yml)
export CORREO_CONTACTO="${CORREO_CONTACTO:-clienta@archivo.test}"
export DOMINIO="${DOMINIO:-https://www.example.com}"

aviso() { printf 'puerta: %s\n' "$*" >&2; }

puerto_libre() {
  python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'
}

dependencias() {
  (
    cd sitio || exit 1
    if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then
      npm ci --no-audit --no-fund --loglevel=error || exit 1
    fi
  ) || { aviso "no se instalan las dependencias de sitio/"; return 1; }
}

# La compilación de producción: sin NOTICIAS_DIR aunque esté exportada en el shell.
compilar() {
  dependencias || return 1
  (cd sitio && env -u NOTICIAS_DIR npm run build --silent) || { aviso "no compila sitio/"; return 1; }
}

# La compilación de pruebas: con el juego cargado en sitio/.juego (NOTICIAS_DIR la exporta cargar_juego).
compilar_juego() {
  dependencias || return 1
  (cd sitio && npm run build --silent) || { aviso "no compila sitio/ con el juego"; return 1; }
}

esperar() {
  local intento
  for intento in $(seq 1 80); do
    curl -fsS -o /dev/null "$1" 2>/dev/null && return 0
    sleep 0.5
  done
  aviso "$1 no responde"
  return 1
}

apagar() {
  "${COMPOSE[@]}" down --volumes --remove-orphans >/dev/null 2>&1
}

levantar() {
  local puerto_sitio puerto_buzon intento salida
  # puerto_libre suelta el puerto antes de que Docker lo tome: si otra pila se lo lleva mientras, se repite con otros.
  for intento in 1 2 3; do
    puerto_sitio="$(puerto_libre)"
    puerto_buzon="$(puerto_libre)"
    while [ "$puerto_buzon" = "$puerto_sitio" ]; do puerto_buzon="$(puerto_libre)"; done
    export SITIO_PUERTO="$puerto_sitio" BUZON_PUERTO="$puerto_buzon"
    export SITIO_URL="http://127.0.0.1:$puerto_sitio" BUZON_URL="http://127.0.0.1:$puerto_buzon"
    apagar
    if salida="$("${COMPOSE[@]}" up -d 2>&1)"; then
      esperar "$SITIO_URL/" && esperar "$BUZON_URL/api/v1/info" && return 0
    fi
    aviso "la pila de Docker no arranca o no responde (intento $intento de 3)"
    apagar
  done
  printf '%s\n' "$salida" >&2
  return 1
}

# ¿tests/sitio/titular.json trae los cuatro datos de la titular? Hasta entonces CA-LET-01-17 y 29 van en rojo a propósito.
titular_completo() {
  python3 - <<'JSON'
import json, sys
datos = json.load(open("tests/sitio/titular.json", encoding="utf-8"))
sys.exit(0 if all(str(datos.get(k, "")).strip() for k in ("nombre_fiscal", "nif", "domicilio", "correo")) else 1)
JSON
}

pytest_sitio() {
  uv run --no-project --with playwright==1.56.0 playwright install chromium >/dev/null || return 1
  PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with pytest==8.4.2 --with playwright==1.56.0 \
    pytest -p no:cacheprovider -q "$@"
}

# La orden de un criterio sale de la propia spec («→ orden: `…` ⇒ exit 0»): una sola fuente.
orden_de_la_spec() {
  python3 - "$1" "$SPEC_LET_01" <<'PY'
import re
import sys

criterio, spec = sys.argv[1:3]
actual = None
with open(spec, encoding="utf-8") as fichero:
    for linea in fichero:
        inicio = re.match(r"- `(CA-LET-01-\d\d)`", linea)
        if inicio:
            actual = inicio.group(1)
        if actual == criterio:
            orden = re.search(r"→ orden: `(.*)` ⇒ exit 0", linea)
            if orden:
                print(orden.group(1))
                sys.exit(0)
sys.exit(1)
PY
}

correr_orden() {
  local orden
  orden="$(orden_de_la_spec "$1")" || { aviso "la spec no trae la orden de $1"; return 1; }
  if bash -c "$orden"; then
    printf '%s: exit 0\n' "$1"
  else
    printf '%s: FALLA (exit %s)\n' "$1" "$?"
    return 1
  fi
}

puerta_let_01() {
  local resultado=0 criterio seleccion="let_01"
  compilar && levantar || return 1
  if ! titular_completo; then
    aviso "tests/sitio/titular.json no tiene los cuatro datos de la titular: CA-LET-01-17 y 29 quedan apartados hasta tenerlos"
    seleccion="let_01 and not ca_let_01_17 and not ca_let_01_29"
  fi
  pytest_sitio tests/sitio -k "$seleccion" || resultado=1
  for criterio in CA-LET-01-01 CA-LET-01-07 CA-LET-01-22; do
    correr_orden "$criterio" || resultado=1
  done
  return $resultado
}

# LET-02: el cargador del juego (sitio/herramientas/cargar-juego.mjs) crea las noticias A a H con el gestor y deja el registro
# JUEGO; la compilación lee ese juego como NOTICIAS_DIR. El sitio publicado no lo ve nunca: sin NOTICIAS_DIR solo lee
# sitio/contenido/noticias.
cargar_juego() {
  export NOTICIAS_DIR="$RAIZ/sitio/.juego"
  export JUEGO="${JUEGO:-$RAIZ/tests/juego.json}"
  node sitio/herramientas/cargar-juego.mjs "$NOTICIAS_DIR" "$JUEGO" || { aviso "no se pudo cargar el juego de pruebas"; return 1; }
}

# Al acabar con el juego, pase lo que pase (también si la pila no arranca o se corta), sitio/dist vuelve a ser la compilación de
# producción: lo que se subiría al desplegar nunca se queda con el juego dentro (RN-LET-02-19). Lo llama el trap de salida.
recompilar_produccion() {
  (cd sitio && env -u NOTICIAS_DIR npm run build --silent) || { aviso "la compilación de producción tras el juego ha fallado: sitio/dist no es de fiar"; return 1; }
}

# Sin argumentos corre las 23 comprobaciones de tests/test_noticias.py y después las de tests/test_noticias_compilacion.py
# (que compilan sus propias copias de sitio/ con noticias reales); con nombres, solo esas de la primera.
puerta_let_02() {
  local resultado=0
  cargar_juego && compilar_juego && levantar || return 1
  SITIO="$SITIO_URL" PYTHONDONTWRITEBYTECODE=1 python3 tests/test_noticias.py "$@" || resultado=$?
  if [ "$#" -eq 0 ]; then
    PYTHONDONTWRITEBYTECODE=1 python3 tests/test_noticias_compilacion.py || resultado=$?
  fi
  return $resultado
}

case "${1:-}" in
  test)
    ruta="${2:-}"
    case "$ruta" in
      tests/sitio/*)
        trap apagar EXIT
        compilar && levantar || exit 1
        pytest_sitio "$ruta"
        ;;
      tests/test_noticias.py|tests/test_noticias.py::*)
        nombre="${ruta#tests/test_noticias.py}"
        nombre="${nombre#::}"
        trap 'apagar; recompilar_produccion' EXIT
        puerta_let_02 ${nombre:+"$nombre"}
        ;;
      tests/test_noticias_compilacion.py|tests/test_noticias_compilacion.py::*)
        nombre="${ruta#tests/test_noticias_compilacion.py}"
        nombre="${nombre#::}"
        dependencias || exit 1
        PYTHONDONTWRITEBYTECODE=1 python3 tests/test_noticias_compilacion.py ${nombre:+"$nombre"}
        ;;
      *)
        aviso "uso: bash tests/puerta.sh test tests/sitio/<fichero>.py[::<test>] | tests/test_noticias.py[::<test>] | tests/test_noticias_compilacion.py[::<test>]"
        exit 2
        ;;
    esac
    ;;
  let-01)
    trap apagar EXIT
    puerta_let_01
    ;;
  let-02)
    trap 'apagar; recompilar_produccion' EXIT
    puerta_let_02
    ;;
  servir)
    compilar && levantar || exit 1
    printf 'Sitio:  %s\nBuzón:  %s\nApagar: bash tests/puerta.sh apagar\n' "$SITIO_URL" "$BUZON_URL"
    ;;
  apagar)
    apagar
    ;;
  *)
    aviso "uso: bash tests/puerta.sh test <ruta> | let-01 | let-02 | servir | apagar"
    exit 2
    ;;
esac
