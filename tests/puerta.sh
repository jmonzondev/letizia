#!/usr/bin/env bash
# Puertas del sitio (DEC-L-004). Se corren desde cualquier carpeta; trabajan sobre la raíz de esta copia del repo.
#
#   bash tests/puerta.sh test <ruta>   un test: tests/sitio/<fichero>.py o tests/sitio/<fichero>.py::<test>
#   bash tests/puerta.sh let-01        los tests de LET-01 y las órdenes de CA-LET-01-01, 07 y 22; mientras tests/sitio/titular.json
#                                      no tenga los cuatro datos de la titular, aparta CA-LET-01-17 y 29 con un aviso (la spec los
#                                      deja en rojo a propósito hasta tener los datos reales)
#   bash tests/puerta.sh let-02        la añade LET-02 (hoy sale con 1)
#   bash tests/puerta.sh servir        compila y deja el sitio y el buzón en marcha para probarlos a mano
#   bash tests/puerta.sh apagar        apaga lo que dejó «servir»
#
# Compila sitio/ (Astro), levanta el sitio (Apache con PHP) y el buzón de pruebas (Mailpit) en Docker, con un nombre de
# proyecto y unos puertos libres propios de esta carpeta de trabajo, exporta SITIO_URL, BUZON_URL y CORREO_CONTACTO, corre
# lo pedido y lo apaga. Hace falta Docker, Node y uv; el navegador (Chromium) lo instala Playwright si falta.

set -u -o pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$RAIZ" || exit 2

SPEC_LET_01="docs/specs/LET-01-estructura-del-sitio-y-paginas-estaticas.md"
PROYECTO="letizia-$(printf '%s' "$RAIZ" | shasum | cut -c1-8)"
COMPOSE=(docker compose -p "$PROYECTO" -f tests/pila/docker-compose.yml)
export CORREO_CONTACTO="${CORREO_CONTACTO:-clienta@archivo.test}"

aviso() { printf 'puerta: %s\n' "$*" >&2; }

puerto_libre() {
  python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'
}

compilar() {
  (
    cd sitio || exit 1
    if [ ! -f node_modules/.package-lock.json ] || [ package-lock.json -nt node_modules/.package-lock.json ]; then
      npm ci --no-audit --no-fund --loglevel=error || exit 1
    fi
    npm run build --silent
  ) || { aviso "no compila sitio/"; return 1; }
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

case "${1:-}" in
  test)
    ruta="${2:-}"
    case "$ruta" in
      tests/sitio/*) ;;
      *) aviso "uso: bash tests/puerta.sh test tests/sitio/<fichero>.py[::<test>]"; exit 2 ;;
    esac
    trap apagar EXIT
    compilar && levantar || exit 1
    pytest_sitio "$ruta"
    ;;
  let-01)
    trap apagar EXIT
    puerta_let_01
    ;;
  let-02)
    aviso "la puerta let-02 la añade LET-02 (juego de pruebas y su cargador): todavía no existe"
    exit 1
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
